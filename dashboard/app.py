"""
CareerPilot AI — Executive Web Command Center.
Provides real-time pipeline execution, 1-click browser triggers,
3-step first-run onboarding wizard, commercial license verification,
AI resume upload, match inspection, and application tracking.
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from core.db import get_db, JobApplicationRecord, ApplicationStatus
from config.settings import settings
from config.candidate_profile import CANDIDATE
from core.resume_parser import resume_parser
from core.licensing import licensing

logger = logging.getLogger("Dashboard")

# Global execution state
AGENT_STATE = {
    "is_running": False,
    "current_status": "Idle",
    "last_summary": None,
    "last_run_time": None
}

def update_env_file(key: str, value: str):
    """Safely updates or appends a key-value pair in .env file."""
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n", encoding="utf-8")
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}=") or line.startswith(f"#{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

def create_app() -> FastAPI:
    app = FastAPI(title="CareerPilot AI Command Center")

    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)
    app.mount("/screenshots", StaticFiles(directory=str(screenshots_dir)), name="screenshots")

    def run_agent_task(limit: int, dry_run: bool, auto_submit: bool):
        global AGENT_STATE
        AGENT_STATE["is_running"] = True
        AGENT_STATE["current_status"] = f"Running {'Review Mode (Dry Run)' if dry_run else 'Live Pipeline'} (Limit={limit})..."
        try:
            from agent.orchestrator import orchestrator
            settings.AUTO_SUBMIT = auto_submit
            summary = orchestrator.run_pipeline(max_leads=limit, dry_run=dry_run)
            AGENT_STATE["last_summary"] = summary
            AGENT_STATE["current_status"] = "Completed"
        except Exception as e:
            AGENT_STATE["current_status"] = f"Error: {str(e)}"
        finally:
            AGENT_STATE["is_running"] = False

    @app.post("/api/run-agent")
    def trigger_agent(limit: int = 5, dry_run: bool = True, auto_submit: bool = False, background_tasks: BackgroundTasks = BackgroundTasks()):
        global AGENT_STATE
        if AGENT_STATE["is_running"]:
            return JSONResponse({"status": "error", "message": "Agent is already running a pipeline."}, status_code=400)
        
        # Check license limits for live runs
        if not dry_run:
            lic = licensing.get_license_status()
            if not lic["can_apply"]:
                return JSONResponse({
                    "status": "error",
                    "message": "Free tier limit of 10 applications reached. Please upgrade to CareerPilot Pro to continue."
                }, status_code=403)

        background_tasks.add_task(run_agent_task, limit, dry_run, auto_submit)
        return {"status": "started", "mode": "Dry Run" if dry_run else "Live Apply"}

    @app.get("/api/agent-status")
    def get_status():
        return AGENT_STATE

    @app.get("/api/license-status")
    def get_license():
        return licensing.get_license_status()

    @app.post("/api/verify-license")
    async def verify_license_endpoint(request: Request):
        try:
            body = await request.json()
            key = body.get("license_key", "")
            res = licensing.verify_and_activate(key)
            return res
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @app.post("/api/save-api-key")
    async def save_api_key_endpoint(request: Request):
        try:
            body = await request.json()
            openrouter_key = body.get("openrouter_key", "").strip()
            gemini_key = body.get("gemini_key", "").strip()

            if openrouter_key:
                settings.OPENROUTER_API_KEY = openrouter_key
                os.environ["OPENROUTER_API_KEY"] = openrouter_key
                update_env_file("OPENROUTER_API_KEY", openrouter_key)
                from core.llm_matcher import matcher
                matcher._init_openrouter()

            if gemini_key:
                settings.GEMINI_API_KEY = gemini_key
                os.environ["GEMINI_API_KEY"] = gemini_key
                update_env_file("GEMINI_API_KEY", gemini_key)
                from core.llm_matcher import matcher
                matcher._init_gemini()

            return {"status": "success", "message": "API Key saved and activated successfully!"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @app.get("/api/check-chrome")
    def check_chrome_status():
        import httpx
        try:
            res = httpx.get("http://127.0.0.1:9222/json/version", timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                return {"connected": True, "browser": data.get("Browser", "Chrome"), "port": 9222}
        except Exception:
            pass
        return {"connected": False, "port": 9222}

    @app.get("/api/onboarding-status")
    def onboarding_status():
        profile_file = Path("user_profile.json")
        has_profile = profile_file.exists()
        has_api_key = bool(settings.OPENROUTER_API_KEY or settings.GEMINI_API_KEY)
        
        # Check chrome
        chrome_ok = False
        import httpx
        try:
            res = httpx.get("http://127.0.0.1:9222/json/version", timeout=1.5)
            chrome_ok = (res.status_code == 200)
        except Exception:
            pass

        needs_setup = not has_profile or not has_api_key
        return {
            "needs_setup": needs_setup,
            "has_profile": has_profile,
            "has_api_key": has_api_key,
            "chrome_connected": chrome_ok,
            "license": licensing.get_license_status()
        }

    @app.post("/api/launch-chrome")
    def launch_chrome_session():
        import subprocess
        import shutil
        chrome_paths = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"))
        ]
        chrome_bin = next((p for p in chrome_paths if p.exists()), None) or shutil.which("chrome")
        if not chrome_bin:
            return JSONResponse({"status": "error", "message": "Chrome executable not found."}, status_code=500)

        profile_dir = Path("chrome_debug_profile").resolve()
        profile_dir.mkdir(exist_ok=True)
        urls = ["https://mail.google.com", "https://www.linkedin.com/jobs", "https://www.naukri.com"]
        cmd = [str(chrome_bin), "--remote-debugging-port=9222", f"--user-data-dir={profile_dir}"] + urls
        subprocess.Popen(cmd)
        return {"status": "launched", "port": 9222}

    @app.post("/api/upload-resume")
    async def upload_resume(file: UploadFile = File(...)):
        resumes_dir = Path("resumes")
        resumes_dir.mkdir(exist_ok=True)
        file_path = resumes_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        settings.RESUME_PATH = str(file_path.resolve())
        # Parse profile with AI
        profile = resume_parser.parse_and_save_profile(str(file_path.resolve()))
        return {
            "status": "success",
            "candidate": profile.full_name,
            "current_title": profile.current_title,
            "experience_years": profile.total_experience_years,
            "skills": profile.target_job_titles
        }

    @app.get("/api/export-csv")
    def export_csv():
        import io
        import csv
        from fastapi.responses import Response

        db: Session = get_db()
        records = db.query(JobApplicationRecord).order_by(JobApplicationRecord.id.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Job Title", "Company", "Source", "Match Score (%)", "Fit Category", "Status", "Job URL", "Discovered At", "Applied At"])

        for r in records:
            writer.writerow([
                r.id,
                r.job_title,
                r.company_name or "",
                r.source,
                int(r.match_score),
                r.match_fit_category or "",
                r.status,
                r.job_url,
                r.discovered_at.strftime("%Y-%m-%d %H:%M") if r.discovered_at else "",
                r.applied_at.strftime("%Y-%m-%d %H:%M") if r.applied_at else ""
            ])

        response = Response(content=output.getvalue(), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=careerpilot_applications.csv"
        return response

    @app.get("/", response_class=HTMLResponse)
    def index():
        db: Session = get_db()
        records = db.query(JobApplicationRecord).order_by(JobApplicationRecord.id.desc()).all()
        active_candidate = resume_parser.get_active_profile()
        lic = licensing.get_license_status()

        total = len(records)
        qualified = sum(1 for r in records if r.match_score >= 75)
        applied = sum(1 for r in records if r.status in ["APPLIED", "PENDING_REVIEW"])
        external = sum(1 for r in records if "EXTERNAL" in (r.status or ""))

        rows_html = ""
        for r in records:
            badge_color = (
                "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" if r.match_score >= 80 
                else ("bg-amber-500/10 text-amber-400 border-amber-500/20" if r.match_score >= 65 else "bg-rose-500/10 text-rose-400 border-rose-500/20")
            )
            status_color = (
                "bg-blue-500/10 text-blue-400 border-blue-500/20" if r.status == "APPLIED"
                else ("bg-purple-500/10 text-purple-400 border-purple-500/20" if r.status == "PENDING_REVIEW" 
                else ("bg-amber-500/10 text-amber-400 border-amber-500/20" if "EXTERNAL" in r.status 
                else "bg-slate-500/10 text-slate-400 border-slate-500/20"))
            )
            date_str = r.discovered_at.strftime("%b %d, %H:%M") if r.discovered_at else "-"

            rows_html += f"""
            <tr class="hover:bg-slate-800/50 transition border-b border-slate-800/80 text-sm">
                <td class="py-4 px-5">
                    <p class="font-semibold text-slate-100">{r.job_title}</p>
                    <p class="text-xs text-slate-400 mt-0.5">{r.company_name or 'Company'}</p>
                </td>
                <td class="py-4 px-5">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-slate-800 text-slate-300 border border-slate-700">
                        {r.source.replace('GMAIL_', '')}
                    </span>
                </td>
                <td class="py-4 px-5">
                    <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold border {badge_color}">
                        {int(r.match_score)}%
                    </span>
                </td>
                <td class="py-4 px-5">
                    <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border {status_color}">
                        {r.status}
                    </span>
                </td>
                <td class="py-4 px-5 text-xs text-slate-400">{date_str}</td>
                <td class="py-4 px-5 text-right">
                    <a href="{r.job_url}" target="_blank" class="inline-flex items-center gap-1 text-xs font-medium text-cyan-400 hover:text-cyan-300 hover:underline">
                        Open Job &rarr;
                    </a>
                </td>
            </tr>
            """

        license_badge = (
            '<span class="px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 shadow-md shadow-orange-500/20 cursor-pointer" onclick="openLicenseModal()">⚡ PRO ACTIVE</span>'
            if lic["is_pro"] else
            f'<span class="px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700 cursor-pointer" onclick="openLicenseModal()">FREE: {lic.get("applications_remaining", 10)}/10 left (Upgrade)</span>'
        )

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en" class="dark">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>CareerPilot AI Command Center | {active_candidate.full_name}</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
            <style>
                body {{ font-family: 'Plus Jakarta Sans', sans-serif; background: #0B0F19; color: #F1F5F9; }}
                .glass {{ background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }}
                .step-dot.active {{ background: #06B6D4; box-shadow: 0 0 12px #06B6D4; }}
                .step-dot.completed {{ background: #10B981; }}
            </style>
        </head>
        <body class="min-h-screen relative">
            <!-- Navbar -->
            <header class="glass sticky top-0 z-40 px-8 py-4 border-b border-slate-800">
                <div class="max-w-7xl mx-auto flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-xl shadow-lg shadow-cyan-500/20">
                            ⚡
                        </div>
                        <div>
                            <div class="flex items-center gap-2">
                                <h1 class="text-lg font-bold text-white">CareerPilot AI</h1>
                                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">AUTONOMOUS</span>
                                {license_badge}
                            </div>
                            <p class="text-xs text-slate-400">Candidate: <span id="candidate-name-header" class="font-semibold text-slate-200">{active_candidate.full_name}</span> ({active_candidate.current_title[:38]}...)</p>
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="flex items-center gap-2.5">
                        <button onclick="openWizard()" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-500/30 transition flex items-center gap-1.5 shadow-sm">
                            <span>⚙️</span> Setup Wizard
                        </button>
                        <a href="/api/export-csv" download class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5 shadow-sm">
                            <span>📥</span> Export CSV
                        </a>
                        <button onclick="launchChrome()" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5 shadow-sm">
                            <span>🌐</span> Chrome
                        </button>
                        <button onclick="runAgent(false)" class="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white transition flex items-center gap-1.5 shadow-md shadow-cyan-500/20">
                            <span>🚀</span> Auto-Apply
                        </button>
                        <button onclick="runAgent(true)" class="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5">
                            <span>🛡️</span> Review Mode
                        </button>
                    </div>
                </div>
            </header>

            <main class="max-w-7xl mx-auto px-8 py-8">
                <!-- Status Banner -->
                <div id="status-banner" class="glass rounded-xl p-4 mb-8 flex items-center justify-between border-l-4 border-l-cyan-500">
                    <div class="flex items-center gap-3">
                        <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping"></span>
                        <div>
                            <p class="text-xs font-medium text-slate-400 uppercase tracking-wider">Agent Engine Status</p>
                            <p id="agent-status-text" class="text-sm font-semibold text-slate-100">Ready & Idle — Connected to OpenRouter (Gemini 2.5 Flash)</p>
                        </div>
                    </div>
                    <div class="text-xs text-slate-400 font-mono">
                        Targeting: <span class="text-cyan-400">GenAI, Agentic AI, Lead SDET, Test Automation Architect</span>
                    </div>
                </div>

                <!-- Metrics Grid -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-5 mb-8">
                    <div class="glass rounded-2xl p-6 relative overflow-hidden">
                        <div class="absolute -right-4 -bottom-4 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl"></div>
                        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Scanned</p>
                        <p class="text-3xl font-extrabold text-white mt-2">{total}</p>
                        <p class="text-[11px] text-slate-500 mt-1">Naukri & LinkedIn notifications</p>
                    </div>

                    <div class="glass rounded-2xl p-6 relative overflow-hidden">
                        <div class="absolute -right-4 -bottom-4 w-24 h-24 bg-emerald-500/5 rounded-full blur-xl"></div>
                        <p class="text-xs font-semibold text-emerald-400 uppercase tracking-wider">High Match (>=75%)</p>
                        <p class="text-3xl font-extrabold text-emerald-400 mt-2">{qualified}</p>
                        <p class="text-[11px] text-slate-500 mt-1">Evaluated by OpenRouter LLM</p>
                    </div>

                    <div class="glass rounded-2xl p-6 relative overflow-hidden">
                        <div class="absolute -right-4 -bottom-4 w-24 h-24 bg-blue-500/5 rounded-full blur-xl"></div>
                        <p class="text-xs font-semibold text-blue-400 uppercase tracking-wider">Applied / In Review</p>
                        <p class="text-3xl font-extrabold text-blue-400 mt-2">{applied}</p>
                        <p class="text-[11px] text-slate-500 mt-1">Easy Apply & Company ATS</p>
                    </div>

                    <div class="glass rounded-2xl p-6 relative overflow-hidden">
                        <div class="absolute -right-4 -bottom-4 w-24 h-24 bg-amber-500/5 rounded-full blur-xl"></div>
                        <p class="text-xs font-semibold text-amber-400 uppercase tracking-wider">External ATS Sites</p>
                        <p class="text-3xl font-extrabold text-amber-400 mt-2">{external}</p>
                        <p class="text-[11px] text-slate-500 mt-1">Workday, Greenhouse, Lever</p>
                    </div>
                </div>

                <!-- Job Pipeline Table -->
                <div class="glass rounded-2xl overflow-hidden shadow-2xl">
                    <div class="px-6 py-5 border-b border-slate-800 flex items-center justify-between">
                        <div>
                            <h2 class="text-base font-bold text-white flex items-center gap-2">
                                <span>📋</span> Discovered Jobs & Autonomous Submissions
                            </h2>
                            <p class="text-xs text-slate-400 mt-0.5">Real-time telemetry recorded in SQLite</p>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-mono text-slate-400">Auto-refresh active</span>
                        </div>
                    </div>

                    <div class="overflow-x-auto">
                        <table class="w-full text-left border-collapse">
                            <thead>
                                <tr class="bg-slate-900/60 border-b border-slate-800 text-xs font-bold text-slate-400 uppercase tracking-wider">
                                    <th class="py-3 px-5">Role & Company</th>
                                    <th class="py-3 px-5">Source</th>
                                    <th class="py-3 px-5">AI Fit Score</th>
                                    <th class="py-3 px-5">Status</th>
                                    <th class="py-3 px-5">Discovered</th>
                                    <th class="py-3 px-5 text-right">Direct Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows_html or '<tr><td colspan="6" class="text-center py-12 text-slate-500">No applications recorded yet. Click "Run Auto-Apply" or "Review Mode" to start.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </main>

            <!-- ========================================== -->
            <!-- 3-STEP USER ONBOARDING WIZARD MODAL        -->
            <!-- ========================================== -->
            <div id="wizard-modal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md hidden flex items-center justify-center p-4">
                <div class="glass max-w-xl w-full rounded-2xl p-7 border border-slate-700 shadow-2xl relative">
                    <!-- Close button -->
                    <button onclick="closeWizard()" class="absolute top-5 right-5 text-slate-400 hover:text-white text-lg">✕</button>

                    <!-- Wizard Stepper Indicator -->
                    <div class="flex items-center justify-between mb-6 pb-4 border-b border-slate-800">
                        <div class="flex items-center gap-2.5">
                            <span id="dot-1" class="step-dot active w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-slate-950 bg-cyan-400">1</span>
                            <span class="text-xs font-semibold text-slate-200">Resume PDF</span>
                        </div>
                        <div class="w-8 h-0.5 bg-slate-700"></div>
                        <div class="flex items-center gap-2.5">
                            <span id="dot-2" class="step-dot w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-slate-400 bg-slate-800 border border-slate-700">2</span>
                            <span class="text-xs font-semibold text-slate-400">LLM & License</span>
                        </div>
                        <div class="w-8 h-0.5 bg-slate-700"></div>
                        <div class="flex items-center gap-2.5">
                            <span id="dot-3" class="step-dot w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-slate-400 bg-slate-800 border border-slate-700">3</span>
                            <span class="text-xs font-semibold text-slate-400">Chrome Connect</span>
                        </div>
                    </div>

                    <!-- Step 1: Upload Resume -->
                    <div id="wizard-step-1" class="space-y-4">
                        <div>
                            <h3 class="text-base font-bold text-white">Step 1: Upload Your Candidate Resume</h3>
                            <p class="text-xs text-slate-400 mt-1">CareerPilot's LLM will parse your skills, experience, and target roles to evaluate job fit.</p>
                        </div>
                        
                        <div class="border-2 border-dashed border-slate-700 rounded-xl p-6 text-center hover:border-cyan-500/50 transition bg-slate-900/40">
                            <input type="file" id="resume-file-input" accept=".pdf" class="hidden" onchange="handleFileSelected(this)">
                            <div class="cursor-pointer" onclick="document.getElementById('resume-file-input').click()">
                                <span class="text-3xl">📄</span>
                                <p class="text-sm font-semibold text-slate-200 mt-2">Click to select your Resume PDF</p>
                                <p id="selected-file-name" class="text-xs text-cyan-400 mt-1">Accepts formatted PDF resumes</p>
                            </div>
                        </div>

                        <div id="resume-parse-result" class="hidden glass rounded-xl p-3.5 border border-cyan-500/30 text-xs">
                            <p class="text-emerald-400 font-bold flex items-center gap-1.5"><span>✅</span> Profile Parsed Successfully!</p>
                            <p class="text-slate-200 mt-1">Candidate: <strong id="parsed-name" class="text-white"></strong></p>
                            <p class="text-slate-400">Title: <span id="parsed-title" class="text-slate-300"></span></p>
                        </div>

                        <div class="flex justify-end pt-3">
                            <button onclick="goToStep(2)" class="px-5 py-2 rounded-lg text-xs font-bold bg-cyan-500 hover:bg-cyan-400 text-slate-950 transition">
                                Next: LLM & License &rarr;
                            </button>
                        </div>
                    </div>

                    <!-- Step 2: LLM & License -->
                    <div id="wizard-step-2" class="space-y-4 hidden">
                        <div>
                            <h3 class="text-base font-bold text-white">Step 2: AI Engine & License Key</h3>
                            <p class="text-xs text-slate-400 mt-1">Provide your OpenRouter or Gemini API key. Free users get 10 applications.</p>
                        </div>

                        <div>
                            <label class="block text-xs font-semibold text-slate-300 mb-1">OpenRouter API Key (Recommended - Gemini 2.5 Flash)</label>
                            <input type="password" id="wizard-openrouter-key" placeholder="sk-or-v1-..." class="w-full px-3.5 py-2.5 rounded-lg text-xs bg-slate-900 border border-slate-700 text-slate-100 focus:border-cyan-500 focus:outline-none font-mono">
                            <p class="text-[11px] text-slate-500 mt-1">Get your free key at <a href="https://openrouter.ai/keys" target="_blank" class="text-cyan-400 hover:underline">openrouter.ai/keys</a></p>
                        </div>

                        <div>
                            <div class="flex items-center justify-between mb-1">
                                <label class="text-xs font-semibold text-slate-300">CareerPilot Pro License Key (Optional)</label>
                            </div>
                            <div class="flex gap-2">
                                <input type="text" id="wizard-license-key" placeholder="CAREERPILOT-PRO-..." class="flex-1 px-3.5 py-2.5 rounded-lg text-xs bg-slate-900 border border-slate-700 text-slate-100 focus:border-cyan-500 focus:outline-none font-mono">
                                <button onclick="verifyWizardLicense()" class="px-4 py-2.5 rounded-lg text-xs font-bold bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700">Verify</button>
                            </div>
                            <p id="license-verify-msg" class="text-[11px] text-slate-400 mt-1">Enter your license key, or test key <code class="text-cyan-400 font-mono">CAREERPILOT-PRO-2026</code>.</p>
                        </div>

                        <div class="flex justify-between pt-3">
                            <button onclick="goToStep(1)" class="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300">&larr; Back</button>
                            <button onclick="saveStep2AndProceed()" class="px-5 py-2 rounded-lg text-xs font-bold bg-cyan-500 hover:bg-cyan-400 text-slate-950 transition">Next: Chrome Connect &rarr;</button>
                        </div>
                    </div>

                    <!-- Step 3: Chrome Session Connect -->
                    <div id="wizard-step-3" class="space-y-4 hidden">
                        <div>
                            <h3 class="text-base font-bold text-white">Step 3: Connect Your Real Chrome Browser</h3>
                            <p class="text-xs text-slate-400 mt-1">Connects to your active Chrome browser via CDP (Port 9222) to reuse your logged-in sessions without CAPTCHAs.</p>
                        </div>

                        <div class="glass rounded-xl p-4 border border-slate-700 flex items-center justify-between">
                            <div class="flex items-center gap-3">
                                <span id="chrome-status-icon" class="text-2xl">🌐</span>
                                <div>
                                    <p class="text-xs font-bold text-white">Chrome Debugging Session</p>
                                    <p id="chrome-status-desc" class="text-[11px] text-slate-400">Port 9222 connection check</p>
                                </div>
                            </div>
                            <span id="chrome-status-badge" class="px-2.5 py-1 rounded text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">Checking...</span>
                        </div>

                        <div class="flex gap-2">
                            <button onclick="launchChrome()" class="flex-1 py-2.5 rounded-lg text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700">
                                🚀 Launch Chrome on Port 9222
                            </button>
                            <button onclick="checkChromeConnection()" class="px-4 py-2.5 rounded-lg text-xs font-bold bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700">
                                Re-Test
                            </button>
                        </div>

                        <p class="text-[11px] text-slate-400">
                            💡 <strong>Tip:</strong> In the Chrome window that opens, sign in once to <strong>Gmail</strong>, <strong>LinkedIn</strong>, and <strong>Naukri</strong>. Your session is saved locally in <code class="text-slate-200 font-mono">chrome_debug_profile</code>.
                        </p>

                        <div class="flex justify-between pt-3">
                            <button onclick="goToStep(2)" class="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300">&larr; Back</button>
                            <button onclick="completeWizard()" class="px-5 py-2 rounded-lg text-xs font-bold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white transition shadow-lg shadow-cyan-500/20">
                                Complete Setup & Enter Command Center 🎉
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ========================================== -->
            <!-- LICENSE MODAL                              -->
            <!-- ========================================== -->
            <div id="license-modal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md hidden flex items-center justify-center p-4">
                <div class="glass max-w-md w-full rounded-2xl p-6 border border-slate-700 shadow-2xl relative">
                    <button onclick="closeLicenseModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white">✕</button>
                    <h3 class="text-base font-bold text-white flex items-center gap-2">
                        <span>⚡</span> CareerPilot Pro Licensing
                    </h3>
                    <p class="text-xs text-slate-400 mt-1">Unlock unlimited job applications & Workday/Greenhouse ATS autofill.</p>

                    <div class="my-4 p-3.5 glass rounded-xl border border-slate-700 text-xs space-y-1">
                        <p class="text-slate-300">Status: <strong class="text-white" id="lic-status-val">Loading...</strong></p>
                        <p class="text-slate-400">Applications used: <span id="lic-used-val" class="text-cyan-400 font-mono font-bold"></span></p>
                    </div>

                    <!-- Pro Features Banner -->
                    <div class="mb-4 p-3.5 rounded-xl bg-gradient-to-r from-cyan-950/40 to-blue-950/40 border border-cyan-500/30 text-xs">
                        <p class="font-bold text-white flex items-center gap-1.5">
                            <span>💎</span> CareerPilot Pro
                        </p>
                        <p class="text-slate-400 mt-1">Unlock unlimited job applications, Workday & Greenhouse ATS autofill, and priority updates.</p>
                        {"<a href='" + settings.CHECKOUT_URL + "' target='_blank' id='buy-license-btn' class='mt-2.5 w-full inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-bold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-md shadow-cyan-500/20 transition'><span>💳</span> Get CareerPilot Pro &rarr;</a>" if settings.CHECKOUT_URL else ""}
                    </div>

                    <div>
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Enter Pro License Key</label>
                        <input type="text" id="license-input-field" placeholder="CAREERPILOT-PRO-..." class="w-full px-3.5 py-2.5 rounded-lg text-xs bg-slate-900 border border-slate-700 text-slate-100 font-mono focus:border-cyan-500 focus:outline-none">
                    </div>

                    <div class="mt-4 flex gap-2">
                        <button onclick="activateProLicense()" class="flex-1 py-2.5 rounded-lg text-xs font-bold bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 shadow-md shadow-orange-500/20">
                            Activate Pro License
                        </button>
                    </div>
                    <p id="lic-result-msg" class="text-[11px] text-center mt-2"></p>
                </div>
            </div>

            <!-- Dashboard Scripts -->
            <script>
                // Onboarding Wizard Navigation
                function openWizard() {{
                    document.getElementById("wizard-modal").classList.remove("hidden");
                    goToStep(1);
                    checkChromeConnection();
                }}

                function closeWizard() {{
                    document.getElementById("wizard-modal").classList.add("hidden");
                }}

                function goToStep(step) {{
                    [1, 2, 3].forEach(s => {{
                        document.getElementById(`wizard-step-${{s}}`).classList.add("hidden");
                        const dot = document.getElementById(`dot-${{s}}`);
                        dot.classList.remove("active");
                    }});
                    document.getElementById(`wizard-step-${{step}}`).classList.remove("hidden");
                    document.getElementById(`dot-${{step}}`).classList.add("active");
                }}

                async function handleFileSelected(input) {{
                    const file = input.files[0];
                    if (!file) return;
                    document.getElementById("selected-file-name").innerText = "Uploading & parsing " + file.name + "...";

                    const formData = new FormData();
                    formData.append("file", file);

                    try {{
                        const res = await fetch("/api/upload-resume", {{ method: "POST", body: formData }});
                        const data = await res.json();
                        if (data.status === "success") {{
                            document.getElementById("resume-parse-result").classList.remove("hidden");
                            document.getElementById("parsed-name").innerText = data.candidate;
                            document.getElementById("parsed-title").innerText = data.current_title;
                            document.getElementById("candidate-name-header").innerText = data.candidate;
                        }}
                    }} catch (e) {{
                        alert("Error parsing resume: " + e);
                    }}
                }}

                async function verifyWizardLicense() {{
                    const key = document.getElementById("wizard-license-key").value;
                    const res = await fetch("/api/verify-license", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify({{ license_key: key }})
                    }});
                    const data = await res.json();
                    const msgEl = document.getElementById("license-verify-msg");
                    if (data.status === "success") {{
                        msgEl.innerText = "✅ " + data.message;
                        msgEl.className = "text-[11px] text-emerald-400 mt-1";
                    }} else {{
                        msgEl.innerText = "❌ " + data.message;
                        msgEl.className = "text-[11px] text-rose-400 mt-1";
                    }}
                }}

                async function saveStep2AndProceed() {{
                    const key = document.getElementById("wizard-openrouter-key").value;
                    if (key) {{
                        await fetch("/api/save-api-key", {{
                            method: "POST",
                            headers: {{ "Content-Type": "application/json" }},
                            body: JSON.stringify({{ openrouter_key: key }})
                        }});
                    }}
                    goToStep(3);
                    checkChromeConnection();
                }}

                async function checkChromeConnection() {{
                    const badge = document.getElementById("chrome-status-badge");
                    badge.innerText = "Checking...";
                    badge.className = "px-2.5 py-1 rounded text-xs font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700";

                    try {{
                        const res = await fetch("/api/check-chrome");
                        const data = await res.json();
                        if (data.connected) {{
                            badge.innerText = "🟢 CONNECTED (Port 9222)";
                            badge.className = "px-2.5 py-1 rounded text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
                            document.getElementById("chrome-status-desc").innerText = "Active: " + data.browser;
                        }} else {{
                            badge.innerText = "🟡 NOT DETECTED";
                            badge.className = "px-2.5 py-1 rounded text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20";
                            document.getElementById("chrome-status-desc").innerText = "Click 'Launch Chrome' below to start";
                        }}
                    }} catch (e) {{
                        badge.innerText = "❌ ERROR";
                    }}
                }}

                function completeWizard() {{
                    localStorage.setItem("careerpilot_onboarded", "true");
                    closeWizard();
                    alert("Setup completed successfully! You can now run Review Mode or Auto-Apply.");
                    location.reload();
                }}

                // License Modal
                async function openLicenseModal() {{
                    document.getElementById("license-modal").classList.remove("hidden");
                    const res = await fetch("/api/license-status");
                    const data = await res.json();
                    document.getElementById("lic-status-val").innerText = data.is_pro ? "PRO ACTIVE (Unlimited)" : "FREE TIER";
                    document.getElementById("lic-used-val").innerText = data.applications_used + (data.free_limit ? " / " + data.free_limit : "");
                }}

                function closeLicenseModal() {{
                    document.getElementById("license-modal").classList.add("hidden");
                }}

                async function activateProLicense() {{
                    const key = document.getElementById("license-input-field").value;
                    const res = await fetch("/api/verify-license", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify({{ license_key: key }})
                    }});
                    const data = await res.json();
                    const msgEl = document.getElementById("lic-result-msg");
                    if (data.status === "success") {{
                        msgEl.innerText = "✅ " + data.message;
                        msgEl.className = "text-[11px] text-center text-emerald-400 mt-2";
                        setTimeout(() => location.reload(), 1500);
                    }} else {{
                        msgEl.innerText = "❌ " + data.message;
                        msgEl.className = "text-[11px] text-center text-rose-400 mt-2";
                    }}
                }}

                // Core Agent Controls
                async function runAgent(dryRun) {{
                    const btnText = dryRun ? "Starting Review Mode..." : "Starting Auto-Apply...";
                    document.getElementById("agent-status-text").innerText = btnText;
                    try {{
                        const res = await fetch(`/api/run-agent?dry_run=${{dryRun}}&limit=5`, {{ method: "POST" }});
                        const data = await res.json();
                        if (res.status === 403) {{
                            openLicenseModal();
                            alert(data.message);
                            return;
                        }}
                        alert("Pipeline launched! Watch your terminal or refresh this page in a few seconds.");
                        pollStatus();
                    }} catch (e) {{
                        alert("Error starting agent: " + e);
                    }}
                }}

                async function launchChrome() {{
                    try {{
                        const res = await fetch("/api/launch-chrome", {{ method: "POST" }});
                        alert("Chrome launched with Gmail, LinkedIn, and Naukri tabs on port 9222!");
                        setTimeout(checkChromeConnection, 2000);
                    }} catch (e) {{
                        alert("Failed to launch Chrome: " + e);
                    }}
                }}

                async function pollStatus() {{
                    try {{
                        const res = await fetch("/api/agent-status");
                        const data = await res.json();
                        if (data.is_running) {{
                            document.getElementById("agent-status-text").innerText = data.current_status;
                            setTimeout(pollStatus, 3000);
                        }} else {{
                            document.getElementById("agent-status-text").innerText = "Idle — Last run finished. Refresh to view new jobs.";
                        }}
                    }} catch (e) {{}}
                }}

                // Auto-check first run on startup
                window.addEventListener("DOMContentLoaded", async () => {{
                    try {{
                        const res = await fetch("/api/onboarding-status");
                        const status = await res.json();
                        if (status.needs_setup && localStorage.getItem("careerpilot_onboarded") !== "true") {{
                            openWizard();
                        }}
                    }} catch (e) {{}}
                }});
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    return app

"""
Autonomous Video Demo Generator for CareerPilot AI.
Uses Playwright to record a high-resolution 1280x720 video demonstrating:
1. Job alert notification ingestion
2. Gemini 2.5 Flash Match Scoring (88% on Trintech Lead SDET)
3. LinkedIn 'Apply ↗' click & redirect
4. Workday external portal autofill with Resume PDF
5. CareerPilot Executive Dashboard & Telemetry
6. Outro Call-to-Action
"""
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

import sys

# Configure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VIDEOS_DIR = Path("videos").resolve()
VIDEOS_DIR.mkdir(exist_ok=True)

HTML_STORYBOARD = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <title>CareerPilot AI Live Demo</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #070A12; color: #F1F5F9; overflow: hidden; }
        .glass { background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); }
        .scene { display: none; width: 100vw; height: 100vh; position: absolute; inset: 0; }
        .scene.active { display: flex; animation: fadeIn 0.4s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
        .glow-cyan { box-shadow: 0 0 35px rgba(6, 182, 212, 0.25); }
        .glow-blue { box-shadow: 0 0 35px rgba(37, 99, 235, 0.25); }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    </style>
</head>
<body class="w-screen h-screen relative flex items-center justify-center">

    <!-- SCENE 1: CINEMATIC INTRO (0-4s) -->
    <div id="scene-1" class="scene active flex-col items-center justify-center text-center p-8">
        <div class="w-20 h-20 rounded-3xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-4xl mb-6 shadow-2xl shadow-cyan-500/30">
            ⚡
        </div>
        <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-bold uppercase tracking-wider mb-4">
            Autonomous Career Agent
        </div>
        <h1 class="text-5xl font-black text-white tracking-tight leading-tight">
            CareerPilot <span class="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">AI Pro</span>
        </h1>
        <p class="text-lg text-slate-400 mt-3 max-w-xl">
            Watch an AI Agent autonomously score job fit, craft a tailored pitch, and apply on an external company portal.
        </p>
        <div class="mt-8 flex items-center gap-3 text-xs text-slate-500 font-mono">
            <span>LinkedIn (Easy Apply & External)</span> • <span>Naukri 1-Click</span> • <span>Workday ATS</span>
        </div>
    </div>

    <!-- SCENE 2: GMAIL ALERT HARVESTER (4-9s) -->
    <div id="scene-2" class="scene flex-col justify-center px-16">
        <div class="max-w-4xl w-full mx-auto">
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                    <span class="w-3 h-3 rounded-full bg-cyan-400 animate-ping"></span>
                    <span class="text-xs font-bold text-cyan-400 uppercase tracking-widest">Step 1 • Ingestion</span>
                </div>
                <span class="text-xs text-slate-400 font-mono">from:jobalerts-noreply@linkedin.com</span>
            </div>

            <div class="glass rounded-2xl p-7 border-slate-700 shadow-2xl">
                <div class="flex items-start justify-between">
                    <div class="flex items-start gap-4">
                        <div class="w-12 h-12 rounded-xl bg-blue-700 flex items-center justify-center text-white font-bold text-xl">
                            in
                        </div>
                        <div>
                            <span class="px-2.5 py-0.5 rounded text-[11px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">NEW JOB ALERT</span>
                            <h2 class="text-xl font-bold text-white mt-1">Software Test Automation Engineering Lead (Bangalore)</h2>
                            <p class="text-sm text-slate-300 font-semibold mt-0.5">Trintech • Bengaluru, Karnataka, India (On-site)</p>
                            <p class="text-xs text-slate-400 mt-2">
                                "Trintech is looking for a Lead Test Automation Engineer with strong experience in Playwright, Python, API Automation frameworks, and CI/CD..."
                            </p>
                        </div>
                    </div>
                    <div class="text-right">
                        <span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                            Apply ↗ (Responses off LinkedIn)
                        </span>
                    </div>
                </div>

                <div class="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
                    <span class="text-cyan-400 font-mono">Agent detected 1 high-priority tech lead opportunity</span>
                    <span>Extracting JD snippet for LLM fit evaluation &rarr;</span>
                </div>
            </div>
        </div>
    </div>

    <!-- SCENE 3: GEMINI 2.5 FLASH MATCH ENGINE (9-16s) -->
    <div id="scene-3" class="scene flex-col justify-center px-16">
        <div class="max-w-4xl w-full mx-auto">
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                    <span class="w-3 h-3 rounded-full bg-emerald-400"></span>
                    <span class="text-xs font-bold text-emerald-400 uppercase tracking-widest">Step 2 • LLM Fit Evaluation</span>
                </div>
                <span class="text-xs text-slate-400 font-mono">Engine: Google Gemini 2.5 Flash</span>
            </div>

            <div class="glass rounded-2xl p-7 border-emerald-500/30 shadow-2xl relative overflow-hidden">
                <div class="flex items-center justify-between pb-4 border-b border-slate-800">
                    <div>
                        <h2 class="text-lg font-bold text-white">Software Test Automation Engineering Lead @ Trintech</h2>
                        <p class="text-xs text-slate-400">Candidate: Poorna Chandra Rao J (12 yrs Lead Automation Architect)</p>
                    </div>
                    <div class="text-right">
                        <div class="text-4xl font-black text-emerald-400">88%</div>
                        <div class="text-[10px] font-bold text-emerald-300 uppercase tracking-wider">STRONG MATCH</div>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-4 mt-5 text-xs">
                    <div>
                        <p class="font-bold text-slate-300 mb-2">Matched Core Competencies:</p>
                        <div class="flex flex-wrap gap-1.5">
                            <span class="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">Playwright Frameworks</span>
                            <span class="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">Python 3.11 / FastAPI</span>
                            <span class="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">Enterprise Test Architecture</span>
                            <span class="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">CI/CD & Cloud Quality Gates</span>
                        </div>
                    </div>

                    <div>
                        <p class="font-bold text-slate-300 mb-2">Tailored Executive Pitch:</p>
                        <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-300 leading-relaxed italic">
                            "With 12+ years of enterprise automation architecture and leading open-source Playwright test frameworks at Publicis/Optum, Poorna brings immediate leadership to Trintech's automation vision."
                        </div>
                    </div>
                </div>

                <div class="mt-5 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
                    <span class="text-emerald-400 font-semibold">Score >= 75% Threshold met! Proceeding to autonomous application...</span>
                </div>
            </div>
        </div>
    </div>

    <!-- SCENE 4: LINKEDIN EXTERNAL APPLY CLICK (16-22s) -->
    <div id="scene-4" class="scene flex-col justify-center px-16">
        <div class="max-w-4xl w-full mx-auto">
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                    <span class="w-3 h-3 rounded-full bg-cyan-400"></span>
                    <span class="text-xs font-bold text-cyan-400 uppercase tracking-widest">Step 3 • Autonomous Browser Controller</span>
                </div>
                <span class="text-xs text-slate-400 font-mono">Chrome CDP Port 9222 (Zero-Ban Architecture)</span>
            </div>

            <div class="glass rounded-2xl p-7 border-slate-700 shadow-2xl">
                <div class="flex items-center justify-between mb-6">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white text-lg">T</div>
                        <div>
                            <h3 class="text-base font-bold text-white">Trintech — Bangalore Careers</h3>
                            <p class="text-xs text-slate-400">Responses managed off LinkedIn</p>
                        </div>
                    </div>
                    
                    <button class="px-6 py-2.5 rounded-lg text-sm font-bold bg-blue-600 text-white flex items-center gap-2 shadow-lg shadow-blue-500/30 ring-4 ring-cyan-400/50">
                        <span>Apply ↗</span>
                    </button>
                </div>

                <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono space-y-2 text-slate-300">
                    <p class="text-cyan-400">[CareerPilot] Clicking external Apply ↗ trigger on LinkedIn...</p>
                    <p class="text-slate-400">[CareerPilot] Handled LinkedIn redirect modal: "Proceed to company site"</p>
                    <p class="text-emerald-400">[CareerPilot] Tracking new tab: Redirected to trintech.wd1.myworkdayjobs.com</p>
                </div>
            </div>
        </div>
    </div>

    <!-- SCENE 5: WORKDAY ATS AUTOFILL (22-29s) -->
    <div id="scene-5" class="scene flex-col justify-center px-16">
        <div class="max-w-4xl w-full mx-auto">
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                    <span class="w-3 h-3 rounded-full bg-blue-400"></span>
                    <span class="text-xs font-bold text-blue-400 uppercase tracking-widest">Step 4 • External ATS Portal Fill</span>
                </div>
                <span class="text-xs text-slate-400 font-mono">Portal: Workday Career Portal</span>
            </div>

            <div class="glass rounded-2xl p-6 border-slate-700 shadow-2xl">
                <div class="flex items-center justify-between pb-3 border-b border-slate-800 text-xs">
                    <span class="text-slate-300 font-semibold">Trintech Career Portal &bull; Workday Job #R-1094</span>
                    <span class="px-2.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400">AUTOFILLED</span>
                </div>

                <div class="grid grid-cols-2 gap-4 my-4 text-xs">
                    <div>
                        <label class="text-slate-400 text-[11px]">Full Name</label>
                        <div class="mt-1 p-2 rounded bg-slate-900 border border-slate-700 font-medium text-white">Poorna Chandra Rao J</div>
                    </div>
                    <div>
                        <label class="text-slate-400 text-[11px]">Email Address</label>
                        <div class="mt-1 p-2 rounded bg-slate-900 border border-slate-700 font-medium text-white">poorna.ai.2026@gmail.com</div>
                    </div>
                    <div>
                        <label class="text-slate-400 text-[11px]">Phone Number</label>
                        <div class="mt-1 p-2 rounded bg-slate-900 border border-slate-700 font-medium text-white">+91-8143675811</div>
                    </div>
                    <div>
                        <label class="text-slate-400 text-[11px]">Attached Resume</label>
                        <div class="mt-1 p-2 rounded bg-emerald-950/40 border border-emerald-500/40 font-medium text-emerald-300 flex items-center justify-between">
                            <span>📄 Poorna_Chandra_Rao_Resume.pdf</span>
                            <span class="text-[10px] font-bold text-emerald-400">UPLOADED</span>
                        </div>
                    </div>
                </div>

                <div class="p-3 rounded-lg bg-blue-950/40 border border-blue-500/30 flex items-center justify-between text-xs">
                    <span class="text-blue-300">Application pre-filled and staged for review (Safety Mode ON)</span>
                    <span class="font-bold text-cyan-400">Telemetry Screenshot Captured 📸</span>
                </div>
            </div>
        </div>
    </div>

    <!-- SCENE 6: EXECUTIVE COMMAND CENTER (29-35s) -->
    <div id="scene-6" class="scene flex-col justify-center px-16">
        <div class="max-w-4xl w-full mx-auto">
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                    <span class="w-3 h-3 rounded-full bg-cyan-400"></span>
                    <span class="text-xs font-bold text-cyan-400 uppercase tracking-widest">Step 5 • Web Command Center</span>
                </div>
                <span class="text-xs text-slate-400 font-mono">http://localhost:8000</span>
            </div>

            <div class="glass rounded-2xl p-6 border-slate-700 shadow-2xl">
                <div class="grid grid-cols-4 gap-3 mb-4 text-center">
                    <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                        <div class="text-xs text-slate-400">Total Scanned</div>
                        <div class="text-2xl font-black text-white mt-0.5">28</div>
                    </div>
                    <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                        <div class="text-xs text-emerald-400">High Match (>=75%)</div>
                        <div class="text-2xl font-black text-emerald-400 mt-0.5">14</div>
                    </div>
                    <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                        <div class="text-xs text-blue-400">Applied / Staged</div>
                        <div class="text-2xl font-black text-blue-400 mt-0.5">12</div>
                    </div>
                    <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                        <div class="text-xs text-amber-400">Workday / ATS</div>
                        <div class="text-2xl font-black text-amber-400 mt-0.5">8</div>
                    </div>
                </div>

                <div class="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs flex items-center justify-between">
                    <div>
                        <span class="font-bold text-white">Software Test Automation Engineering Lead</span>
                        <span class="text-slate-400"> @ Trintech</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">88%</span>
                        <span class="px-2 py-0.5 rounded text-[11px] font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30">PENDING_REVIEW</span>
                        <span class="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-800 text-cyan-400">📥 Export CSV</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- SCENE 7: OUTRO CALL-TO-ACTION -->
    <div id="scene-7" class="scene flex-col items-center justify-center text-center p-8">
        <div class="w-16 h-16 rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-3xl mb-4 shadow-xl shadow-cyan-500/20">
            ⚡
        </div>
        <h2 class="text-4xl font-black text-white">CareerPilot AI Pro</h2>
        <p class="text-base text-slate-300 mt-2 max-w-lg">
            Stop spending 15 hours a week on manual job applications. Let AI do the heavy lifting while you sleep.
        </p>

        <div class="mt-6 p-4 rounded-2xl bg-slate-900/80 border border-cyan-500/40 inline-flex flex-col items-center gap-2">
            <span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-500 text-slate-950 uppercase tracking-wider">
                Launch Offer: Unlimited Applications + ATS Autofill
            </span>
            <span class="text-sm font-semibold text-slate-200 mt-1">Available for Windows, Mac & Linux</span>
            <span class="text-xs text-cyan-400 font-mono">100% Private &bull; Chrome CDP &bull; Gemini 2.5 Flash</span>
        </div>
    </div>

    <script>
        window.currentScene = 1;
        window.switchScene = function(n) {
            document.querySelectorAll('.scene').forEach(el => el.classList.remove('active'));
            const target = document.getElementById('scene-' + n);
            if (target) {
                target.classList.add('active');
                window.currentScene = n;
            }
        };
    </script>
</body>
</html>
"""

def record_video():
    output_dir = VIDEOS_DIR
    print(f"Starting Playwright video recording in: {output_dir}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir=str(output_dir),
            record_video_size={"width": 1280, "height": 720},
            viewport={"width": 1280, "height": 720}
        )

        page = context.new_page()
        page.set_content(HTML_STORYBOARD)
        page.wait_for_timeout(1000)

        # Scene timings in milliseconds (Snappy 22s total demo)
        scenes = [
            (1, 3000),  # Scene 1: Cinematic Intro (3.0s)
            (2, 3500),  # Scene 2: Gmail Alert Harvester (3.5s)
            (3, 4000),  # Scene 3: Gemini 2.5 Flash Match Scoring (4.0s)
            (4, 3500),  # Scene 4: LinkedIn External Apply Click (3.5s)
            (5, 4000),  # Scene 5: Workday ATS Autofill (4.0s)
            (6, 3500),  # Scene 6: Executive Command Center Telemetry (3.5s)
            (7, 3500),  # Scene 7: Outro CTA (3.5s)
        ]

        for scene_num, duration in scenes:
            print(f"Recording Scene {scene_num} ({duration/1000:.1f}s)...", flush=True)
            page.evaluate(f"window.switchScene({scene_num})")
            page.wait_for_timeout(duration)

        # In Playwright, reference video object, close context to finalize file, then read path
        video_handle = page.video
        context.close()
        browser.close()

        video_path_str = video_handle.path()
        final_video_name = output_dir / "careerpilot_demo.webm"
        if os.path.exists(video_path_str):
            if final_video_name.exists():
                final_video_name.unlink()
            os.rename(video_path_str, final_video_name)
            print(f"🎉 Demo Video Recorded Successfully: {final_video_name}", flush=True)
            return final_video_name

    return None

if __name__ == "__main__":
    record_video()


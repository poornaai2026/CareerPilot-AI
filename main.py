"""
CareerPilot AI — Autonomous Career & Job Application Agent CLI Entrypoint.
Commands:
  run       - Trigger notification harvesting, LLM matching, and auto-apply
  list      - Display all tracked jobs and application history
  match     - Instant test evaluation of any job title/description against your resume
  dashboard - Launch the local web review command center
  launch-chrome - Launch Chrome with debugging port 9222 and persistent profile
  login     - Guided one-time sign in to Gmail, LinkedIn, and Naukri
"""
import sys
import os
import logging
from typing import Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from config.settings import settings
from config.candidate_profile import CANDIDATE
from core.db import init_db, get_db, JobApplicationRecord
from core.llm_matcher import matcher
from agent.orchestrator import orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
# Silence verbose third party logs
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)

app = typer.Typer(help="CareerPilot AI — Autonomous Career Agent for LinkedIn, Naukri & ATS")
console = Console()

@app.command()
def run(
    limit: int = typer.Option(10, "--limit", "-n", help="Max emails / leads to process"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Evaluate & score only, do not launch browser"),
    auto_submit: bool = typer.Option(False, "--auto-submit", "-a", help="Automatically click submit on high matches")
):
    """
    Harvests job notifications from Gmail/LinkedIn/Naukri, matches JDs with LLM, and applies.
    """
    init_db()
    
    if auto_submit:
        settings.AUTO_SUBMIT = True

    console.print(Panel.fit(
        f"[bold cyan]⚡ CareerPilot AI[/bold cyan] | Autonomous Career Pipeline\n"
        f"Candidate: [bold white]{CANDIDATE.full_name}[/bold white] ({CANDIDATE.current_title})\n"
        f"Mode: {'[yellow]Review Mode (Dry Run Scoring)[/yellow]' if dry_run else '[green]Live Autonomous Browser Execution[/green]'} | Auto-Submit: {settings.AUTO_SUBMIT}",
        box=box.ROUNDED
    ))

    with console.status("[bold green]Executing agent workflow...[/bold green]"):
        summary = orchestrator.run_pipeline(max_leads=limit, dry_run=dry_run)

    # Print Results Table
    table = Table(title="Job Pipeline Execution Summary", box=box.ROUNDED)
    table.add_column("ID", justify="center", style="dim")
    table.add_column("Title", style="bold white")
    table.add_column("Company", style="cyan")
    table.add_column("Score", justify="center")
    table.add_column("Fit Category", justify="center")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for res in summary["results"]:
        score_val = res["score"]
        score_color = "green" if score_val >= 80 else ("yellow" if score_val >= 65 else "red")
        
        status_color = "green" if res["status"] in ["APPLIED", "QUALIFIED"] else ("yellow" if res["status"] == "PENDING_REVIEW" else "dim")

        table.add_row(
            str(res["id"]),
            res["title"],
            res["company"],
            f"[{score_color}]{score_val}%[/{score_color}]",
            res["category"],
            f"[{status_color}]{res['status']}[/{status_color}]",
            res.get("message", "")
        )

    console.print(table)
    console.print(
        f"[bold]Processed:[/bold] {summary['new_leads_count']} new | "
        f"[bold green]Qualified:[/bold green] {summary['qualified_count']} | "
        f"[bold cyan]Applied / Staged:[/bold cyan] {summary['applied_count']}"
    )

@app.command()
def list_jobs(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of records to display")
):
    """
    Lists previously discovered, evaluated, and applied jobs from SQLite.
    """
    init_db()
    db = get_db()
    records = db.query(JobApplicationRecord).order_by(JobApplicationRecord.id.desc()).limit(limit).all()

    if not records:
        console.print("[yellow]No job applications recorded yet. Run 'python main.py run' first.[/yellow]")
        return

    table = Table(title="Tracked Job Applications & Match History", box=box.ROUNDED)
    table.add_column("ID", justify="center", style="dim")
    table.add_column("Source", style="cyan")
    table.add_column("Role", style="bold white")
    table.add_column("Company", style="magenta")
    table.add_column("Score", justify="center")
    table.add_column("Status", style="bold")
    table.add_column("Date", style="dim")

    for r in records:
        score_color = "green" if r.match_score >= 80 else ("yellow" if r.match_score >= 65 else "red")
        date_str = r.discovered_at.strftime("%Y-%m-%d %H:%M") if r.discovered_at else "-"
        table.add_row(
            str(r.id),
            r.source,
            r.job_title,
            r.company_name or "-",
            f"[{score_color}]{int(r.match_score)}%[/{score_color}]",
            r.status,
            date_str
        )

    console.print(table)

@app.command()
def match(
    title: str = typer.Argument(..., help="Job Title (e.g. 'Lead GenAI Quality Engineer')"),
    company: str = typer.Option("Target Company", "--company", "-c", help="Company Name"),
    jd: Optional[str] = typer.Option("", "--jd", help="Job Description snippet")
):
    """
    Tests the LLM match engine against Poorna's resume for any custom job.
    """
    console.print(f"[bold cyan]Evaluating job fit against Poorna's resume...[/bold cyan]")
    eval_result = matcher.evaluate_job(title, company, jd or title)

    color = "green" if eval_result.match_score >= 80 else ("yellow" if eval_result.match_score >= 65 else "red")
    
    console.print(Panel(
        f"[bold white]Title:[/bold white] {title}\n"
        f"[bold white]Company:[/bold white] {company}\n\n"
        f"[bold white]Match Score:[/bold white] [{color}]{eval_result.match_score}% ({eval_result.fit_category})[/{color}]\n\n"
        f"[bold white]Rationale:[/bold white]\n{eval_result.reasoning}\n\n"
        f"[bold green]Matched Skills:[/bold green] {', '.join(eval_result.skills_matched) if eval_result.skills_matched else 'None detected'}\n"
        f"[bold yellow]Missing / Gap Skills:[/bold yellow] {', '.join(eval_result.skills_missing) if eval_result.skills_missing else 'None'}\n\n"
        f"[bold cyan]Tailored Elevator Pitch:[/bold cyan]\n{eval_result.tailored_pitch}",
        title="Candidate Fit Assessment",
        box=box.ROUNDED
    ))

@app.command()
def launch_chrome():
    """
    Launches Google Chrome with remote debugging on port 9222 and dedicated profile.
    Opens Gmail, LinkedIn, and Naukri in a single window.
    """
    import subprocess
    import shutil
    from pathlib import Path

    chrome_paths = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"))
    ]

    chrome_bin = next((p for p in chrome_paths if p.exists()), None)
    if not chrome_bin:
        chrome_bin = shutil.which("chrome")

    if not chrome_bin:
        console.print("[red]Could not locate chrome.exe automatically. Please launch Chrome manually with:[/red]")
        console.print("[bold white]chrome.exe --remote-debugging-port=9222 --user-data-dir=chrome_debug_profile[/bold white]")
        return

    profile_dir = Path("chrome_debug_profile").resolve()
    profile_dir.mkdir(exist_ok=True)

    urls = [
        "https://mail.google.com",
        "https://www.linkedin.com/jobs",
        "https://www.naukri.com"
    ]
    
    cmd = [
        str(chrome_bin),
        "--remote-debugging-port=9222",
        f"--user-data-dir={profile_dir}"
    ] + urls

    console.print(f"[bold green]Launching Chrome from:[/bold green] {chrome_bin}")
    console.print(f"[bold cyan]Using persistent profile:[/bold cyan] {profile_dir}")
    console.print("[bold cyan]Remote debugging port: 9222 (Gmail, LinkedIn, Naukri in 1 window)[/bold cyan]")
    
    subprocess.Popen(cmd)
    console.print("[bold green]Chrome is now running![/bold green]")


@app.command()
def login():
    """
    One-time setup: Opens Chrome so you can sign in to Gmail, LinkedIn, and Naukri once.
    Saves your login sessions permanently in the profile.
    """
    launch_chrome()
    console.print(Panel.fit(
        "[bold cyan]One-Time Account Sign-In Setup[/bold cyan]\n"
        "In the Chrome window that just opened, please sign in to:\n"
        "  1. [bold white]Gmail[/bold white] (poorna.ai.2026@gmail.com)\n"
        "  2. [bold white]LinkedIn[/bold white]\n"
        "  3. [bold white]Naukri[/bold white]\n\n"
        "All login cookies & sessions will be saved in your local [bold yellow]chrome_debug_profile[/bold yellow].\n"
        "Once you finish signing in, press [bold green]ENTER[/bold green] below.",
        box=box.ROUNDED
    ))
    input("\nPress ENTER after you have signed in: ")
    console.print("[bold green]Sessions saved successfully![/bold green]")
    console.print("[bold yellow]You can now run: python main.py run[/bold yellow]")


@app.command()
def dashboard(
    port: int = typer.Option(8000, "--port", "-p", help="Dashboard port")
):
    """
    Starts the local web review dashboard.
    """
    import uvicorn
    from dashboard.app import create_app
    app_instance = create_app()
    console.print(f"[bold green]Starting Web Review Dashboard at http://localhost:{port}[/bold green]")
    uvicorn.run(app_instance, host="127.0.0.1", port=port)

if __name__ == "__main__":
    app()


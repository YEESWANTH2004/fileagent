import shutil
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console

console = Console()
LOG_FILE = Path.home() / ".file-agent-log.json"

def load_log():
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return []

def save_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

def move_files(scan_results: dict, base_folder: str):
    base = Path(base_folder)
    log = load_log()
    session = {
        "timestamp": datetime.now().isoformat(),
        "folder": base_folder,
        "actions": []
    }

    moved = 0
    skipped = 0

    for category, files in scan_results.items():
        if not files:
            continue

        target_dir = base / category
        target_dir.mkdir(exist_ok=True)

        for filename in files:
            src = base / filename
            dst = target_dir / filename

            if not src.exists():
                skipped += 1
                continue

            if dst.exists():
                console.print(f"[yellow]Skipping (exists): {filename}[/yellow]")
                skipped += 1
                continue

            try:
                shutil.move(str(src), str(dst))
                session["actions"].append({
                    "action": "move",
                    "from": str(src),
                    "to": str(dst)
                })
                console.print(f"[green]Moved:[/green] {filename} → {category}/")
                moved += 1
            except Exception as e:
                console.print(f"[red]Error moving {filename}: {e}[/red]")

    log.append(session)
    save_log(log)

    console.print(f"\n[bold green]Done! Moved {moved} files. Skipped {skipped}.[/bold green]")
    console.print(f"[dim]Log saved to {LOG_FILE}[/dim]")

def undo_last():
    log = load_log()

    if not log:
        console.print("[yellow]Nothing to undo.[/yellow]")
        return

    last_session = log[-1]
    actions = last_session["actions"]

    if not actions:
        console.print("[yellow]No actions to undo.[/yellow]")
        return

    console.print(f"\n[bold]Undoing {len(actions)} actions from {last_session['timestamp']}[/bold]\n")

    undone = 0
    for action in reversed(actions):
        src = Path(action["to"])
        dst = Path(action["from"])

        if src.exists():
            shutil.move(str(src), str(dst))
            console.print(f"[green]Restored:[/green] {src.name} → original location")
            undone += 1
        else:
            console.print(f"[yellow]File not found, skipping: {src.name}[/yellow]")

    log.pop()
    save_log(log)
    console.print(f"\n[bold green]Undo complete! Restored {undone} files.[/bold green]")

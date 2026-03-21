import argparse
import subprocess
from pathlib import Path
from rich.console import Console
from agent import run_agent
from mover import undo_last, redo_last

console = Console()

def watch_service(action: str):
    commands = {
        "start":   ["systemctl", "--user", "start",   "file-agent-watch"],
        "stop":    ["systemctl", "--user", "stop",    "file-agent-watch"],
        "restart": ["systemctl", "--user", "restart", "file-agent-watch"],
        "status":  ["systemctl", "--user", "status",  "file-agent-watch"],
        "enable":  ["systemctl", "--user", "enable",  "file-agent-watch"],
        "disable": ["systemctl", "--user", "disable", "file-agent-watch"],
    }

    if action not in commands:
        console.print(f"[red]Unknown action: {action}[/red]")
        return

    result = subprocess.run(commands[action], capture_output=False)

    if action == "start":
        console.print("[bold green]Watch mode started! Auto-organizing ~/Downloads in background.[/bold green]")
    elif action == "stop":
        console.print("[bold yellow]Watch mode stopped.[/bold yellow]")
    elif action == "enable":
        console.print("[bold green]Watch mode will now start automatically on login![/bold green]")
    elif action == "disable":
        console.print("[bold yellow]Watch mode auto-start disabled.[/bold yellow]")

def main():
    parser = argparse.ArgumentParser(
        prog="file-agent",
        description="AI-powered file organizer"
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=str(Path.home() / "Downloads"),
        help="Folder to organize (default: ~/Downloads)"
    )
    parser.add_argument(
        "--undo",
        action="store_true",
        help="Undo the last organization"
    )
    parser.add_argument(
        "--redo",
        action="store_true",
        help="Redo the last undone action"
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Just scan and show files, don't move anything"
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Start chat mode"
    )
    parser.add_argument(
        "--duplicates",
        metavar="FOLDER",
        help="Find and remove duplicate files in a folder"
    )
    parser.add_argument(
        "--watch",
        metavar="FOLDER",
        nargs="?",
        const=str(Path.home() / "Downloads"),
        help="Watch a folder and auto-organize new files (default: ~/Downloads)"
    )
    parser.add_argument(
        "--watch-delay",
        type=int,
        default=5,
        help="Seconds to wait before organizing (default: 5)"
    )
    parser.add_argument(
        "--watch-start",
        action="store_true",
        help="Start watch mode as background service"
    )
    parser.add_argument(
        "--watch-stop",
        action="store_true",
        help="Stop watch mode background service"
    )
    parser.add_argument(
        "--watch-status",
        action="store_true",
        help="Check watch mode status"
    )
    parser.add_argument(
        "--watch-enable",
        action="store_true",
        help="Auto-start watch mode on login"
    )
    parser.add_argument(
        "--watch-disable",
        action="store_true",
        help="Disable auto-start watch mode"
    )

    args = parser.parse_args()

    if args.undo:
        undo_last()
        return

    if args.redo:
        redo_last()
        return

    if args.scan_only:
        from scanner import scan_folder, display_scan
        results = scan_folder(args.folder, recursive=True)
        display_scan(results, args.folder)
        return

    if args.chat:
        from chat import chat
        chat()
        return

    if args.duplicates:
        from duplicates import (find_duplicates, display_duplicates,
                                delete_duplicates, delete_duplicates_selective)
        duplicates = find_duplicates(args.duplicates)
        if duplicates:
            display_duplicates(duplicates)
            console.print("\n[bold]How do you want to delete?[/bold]")
            console.print("  [cyan]a[/cyan] = delete all at once")
            console.print("  [cyan]s[/cyan] = review each group")
            console.print("  [cyan]n[/cyan] = cancel")
            choice = input("\nChoice (a/s/n): ").strip().lower()
            if choice == "a":
                delete_duplicates(duplicates)
            elif choice == "s":
                delete_duplicates_selective(duplicates)
        return

    if args.watch_start:
        watch_service("start")
        return

    if args.watch_stop:
        watch_service("stop")
        return

    if args.watch_status:
        watch_service("status")
        return

    if args.watch_enable:
        watch_service("enable")
        watch_service("start")
        return

    if args.watch_disable:
        watch_service("disable")
        watch_service("stop")
        return

    if args.watch is not None:
        from watcher import watch
        watch(args.watch, args.watch_delay)
        return

    run_agent(args.folder)

if __name__ == "__main__":
    main()

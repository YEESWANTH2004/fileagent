import argparse
from pathlib import Path
from rich.console import Console
from agent import run_agent
from mover import undo_last, redo_last

console = Console()

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
        "--duplicates",
        metavar="FOLDER",
        help="Find and remove duplicate files in a folder"
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

    args = parser.parse_args()

    if args.undo:
        undo_last()
        return

    if args.redo:
        redo_last()
        return
    
    if args.duplicates:
        from duplicates import find_duplicates, display_duplicates, delete_duplicates, delete_duplicates_selective
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

    if args.scan_only:
        from scanner import scan_folder, display_scan
        results = scan_folder(args.folder, recursive=True)
        display_scan(results, args.folder)
        return

    if args.chat:
        from chat import chat
        chat()
        return

    run_agent(args.folder)

if __name__ == "__main__":
    main()

import argparse
from pathlib import Path
from rich.console import Console
from agent import run_agent
from mover import undo_last
from chat import chat 

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
        "--chat",
        action="store_true",
        help="Start chat mode"
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Just scan and show files, don't move anything"
    )

    args = parser.parse_args()

    if args.undo:
        undo_last()
        return
    if args.chat:
        chat()
        return
    if args.scan_only:
        from scanner import scan_folder, display_scan
        results = scan_folder(args.folder, recursive=True)
        display_scan(results, args.folder)
        return

    run_agent(args.folder)

if __name__ == "__main__":
    main()

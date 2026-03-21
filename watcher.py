import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from scanner import scan_folder
from mover import move_files
from rich.console import Console

console = Console()

class FileAgentHandler(FileSystemEventHandler):
    def __init__(self, folder: str, delay: int = 5):
        self.folder = folder
        self.delay = delay
        self.pending = {}

    def on_created(self, event):
        if event.is_directory:
            return

        filepath = Path(event.src_path)

        if filepath.name.startswith("."):
            return
        if filepath.suffix in {".tmp", ".part", ".crdownload", ".download"}:
            return

        if filepath.parent != Path(self.folder):
            return

        console.print(f"\n[bold cyan]New file detected:[/bold cyan] {filepath.name}")
        console.print(f"[dim]Will organize in {self.delay} seconds...[/dim]")
        self.pending[str(filepath)] = time.time()

    def on_moved(self, event):
        if event.is_directory:
            return
        filepath = Path(event.dest_path)
        if filepath.name.startswith("."):
            return
        if filepath.suffix in {".tmp", ".part", ".crdownload", ".download"}:
            return
        if filepath.parent != Path(self.folder):
            return
        console.print(f"\n[bold cyan]New file detected:[/bold cyan] {filepath.name}")
        console.print(f"[dim]Will organize in {self.delay} seconds...[/dim]")
        self.pending[str(filepath)] = time.time()

    def process_pending(self):
        now = time.time()
        to_process = [
            path for path, timestamp in self.pending.items()
            if now - timestamp >= self.delay
        ]

        if not to_process:
            return

        for path in to_process:
            del self.pending[path]

        results = scan_folder(self.folder, recursive=False)
        total = sum(len(v) for v in results.values())

        if total > 0:
            console.print(f"\n[bold yellow]Auto-organizing {total} file(s)...[/bold yellow]")
            move_files(results, self.folder)
            console.print("[bold green]Done! Folder organized.[/bold green]")

def watch(folder: str, delay: int = 5):
    folder = str(Path(folder).expanduser())
    path = Path(folder)

    if not path.exists():
        console.print(f"[red]Folder not found: {folder}[/red]")
        return

    console.print(f"""
[bold cyan]Watch mode started![/bold cyan]
[dim]Watching: {folder}[/dim]
[dim]Delay: {delay} seconds after file lands[/dim]
[dim]Press Ctrl+C to stop[/dim]
""")

    handler = FileAgentHandler(folder, delay)
    observer = Observer()
    observer.schedule(handler, folder, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
            handler.process_pending()
    except KeyboardInterrupt:
        console.print("\n[yellow]Watch mode stopped.[/yellow]")
        observer.stop()

    observer.join()

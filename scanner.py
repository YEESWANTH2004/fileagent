from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

FILE_CATEGORIES = {
    "Images":       [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
    "Documents":    [".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf"],
    "Spreadsheets": [".xlsx", ".xls", ".csv"],
    "Presentations":[".pptx", ".ppt", ".key"],
    "Videos":       [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
    "Audio":        [".mp3", ".wav", ".flac", ".aac"],
    "Archives":     [".zip", ".tar", ".gz", ".rar", ".7z"],
    "Code":         [".py", ".js", ".html", ".css", ".java", ".c", ".cpp"],
    "Installers":   [".exe", ".deb", ".rpm", ".sh", ".vbox-extpack"],
}

def scan_folder(folder_path: str, recursive: bool = False) -> dict:
    path = Path(folder_path)

    if not path.exists():
        console.print(f"[red]Folder not found: {folder_path}[/red]")
        return {}

    results = {category: [] for category in FILE_CATEGORIES}
    results["Others"] = []

    # recursive = full deep scan, non-recursive = root files only
    files = path.rglob("*") if recursive else path.iterdir()

    for file in files:
        if file.is_file():
            ext = file.suffix.lower()
            matched = False
            for category, extensions in FILE_CATEGORIES.items():
                if ext in extensions:
                    results[category].append(file.name)
                    matched = True
                    break
            if not matched:
                results["Others"].append(file.name)

    return results 
def display_scan(results: dict, folder_path: str):
    table = Table(title=f"Scan results: {folder_path}")
    table.add_column("Category", style="cyan", width=15)
    table.add_column("Files", style="white")
    table.add_column("Count", style="green", width=8)

    for category, files in results.items():
        if files:
            table.add_row(
                category,
                ", ".join(files[:5]) + ("..." if len(files) > 5 else ""),
                str(len(files))
            )

    console.print(table)

if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / "Downloads")
    console.print(f"\n[bold]Scanning:[/bold] {folder}\n")
    results = scan_folder(folder)
    display_scan(results, folder)

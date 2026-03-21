import hashlib
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

SKIP_NAMES = {
    "LICENSE", "LICENSE.txt", "ASSEMBLY_EXCEPTION", "NOTICE",
    "ADDITIONAL_LICENSE_INFO", ".vscodeignore",
    "cldr.md", "CHANGELOG.md", "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md", "SECURITY.md", "AUTHORS", "COPYING",
    "INSTALL", "NEWS", "TODO", "ChangeLog"
}

SKIP_EXTENSIONS = {
    ".jar", ".so", ".class", ".dll",
    ".obj", ".o", ".a", ".lib", ".pyc", ".pyo"
}

SKIP_FOLDERS = {
    "node_modules", ".git", "__pycache__",
    "venv", "env", ".venv", "site-packages"
}

SKIP_TOP_LEVEL_PATTERNS = {
    "idea-IU-", "idea-IC-", "idea-", "kotlinc",
    "jsLanguageService", "selfcontained", "jbr",
    "IntelliJ", "jetbrains", "remote-dev-server",
    "android-studio", "eclipse", "netbeans"
}

def get_file_hash(filepath: Path) -> str:
    hasher = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None

def should_skip(file: Path, base_folder: Path) -> bool:
    # Skip by filename
    if file.name in SKIP_NAMES:
        return True

    # Skip by extension
    if file.suffix.lower() in SKIP_EXTENSIONS:
        return True

    # Skip known system folders anywhere in path
    for part in file.parts:
        if part in SKIP_FOLDERS:
            return True

    # Skip known software installation folders at top level
    try:
        relative = file.relative_to(base_folder)
        if len(relative.parts) > 1:
            top_level = relative.parts[0]
            for pattern in SKIP_TOP_LEVEL_PATTERNS:
                if pattern.lower() in top_level.lower():
                    return True
    except ValueError:
        pass

    return False

def find_duplicates(folder: str) -> dict:
    base = Path(folder)
    if not base.exists():
        console.print(f"[red]Folder not found: {folder}[/red]")
        return {}

    console.print(f"\n[bold yellow]Scanning for duplicates in {folder}...[/bold yellow]")

    hash_map = {}
    total = 0
    skipped = 0

    for file in base.rglob("*"):
        if file.is_file():
            if should_skip(file, base):
                skipped += 1
                continue
            total += 1
            file_hash = get_file_hash(file)
            if file_hash:
                if file_hash not in hash_map:
                    hash_map[file_hash] = []
                hash_map[file_hash].append(file)

    console.print(f"[dim]Scanned {total} files, skipped {skipped} system files[/dim]")

    duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}
    return duplicates

def format_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size/1024:.1f}KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size/1024/1024:.1f}MB"
    else:
        return f"{size/1024/1024/1024:.1f}GB"

def display_duplicates(duplicates: dict):
    if not duplicates:
        console.print("\n[bold green]No duplicates found![/bold green]")
        return

    total_duplicates = sum(len(files) - 1 for files in duplicates.values())
    total_size = sum(
        file.stat().st_size
        for files in duplicates.values()
        for file in files[1:]
    )

    table = Table(title=f"Duplicate files — {len(duplicates)} groups")
    table.add_column("Group", style="dim", width=6)
    table.add_column("Status", width=6)
    table.add_column("File", style="yellow")
    table.add_column("Size", style="cyan", width=10)
    table.add_column("Location", style="dim")

    for i, (hash_val, files) in enumerate(duplicates.items(), start=1):
        for j, file in enumerate(files):
            size_str = format_size(file.stat().st_size)
            status = "[green]KEEP[/green]" if j == 0 else "[red]DUPE[/red]"
            location = str(file.parent)
            if len(location) > 35:
                location = "..." + location[-32:]
            table.add_row(
                str(i),
                status,
                file.name[:30] + "..." if len(file.name) > 30 else file.name,
                size_str,
                location
            )

    console.print(table)
    console.print(f"\n[bold]Found {total_duplicates} duplicate files[/bold]")
    console.print(f"[bold yellow]Wasted space: {format_size(total_size)}[/bold yellow]")
    console.print(f"[dim]Note: First file in each group is kept, rest are deleted[/dim]")

def delete_duplicates(duplicates: dict) -> int:
    deleted = 0
    freed = 0

    for hash_val, files in duplicates.items():
        for file in files[1:]:
            try:
                size = file.stat().st_size
                file.unlink()
                console.print(f"[red]Deleted:[/red] {file.name} ({format_size(size)})")
                deleted += 1
                freed += size
            except Exception as e:
                console.print(f"[yellow]Could not delete {file.name}: {e}[/yellow]")

    console.print(f"\n[bold green]Done! Deleted {deleted} files. Freed {format_size(freed)}.[/bold green]")
    return deleted

def delete_duplicates_selective(duplicates: dict) -> int:
    deleted = 0
    freed = 0

    console.print("\n[bold]Selective delete — review each group:[/bold]")
    console.print("[dim]y = delete dupes in this group, n = skip, q = quit[/dim]\n")

    for i, (hash_val, files) in enumerate(duplicates.items(), start=1):
        console.print(f"\n[bold cyan]Group {i}:[/bold cyan]")
        console.print(f"  [green]KEEP:[/green] {files[0].name}")
        console.print(f"  [dim]  at: {files[0].parent}[/dim]")
        for file in files[1:]:
            size_str = format_size(file.stat().st_size)
            console.print(f"  [red]DUPE:[/red] {file.name} ({size_str})")
            console.print(f"  [dim]  at: {file.parent}[/dim]")

        choice = input(f"\nDelete {len(files)-1} dupe(s) in this group? (y/n/q): ").strip().lower()

        if choice == "q":
            console.print("[yellow]Stopped.[/yellow]")
            break
        elif choice == "y":
            for file in files[1:]:
                try:
                    size = file.stat().st_size
                    file.unlink()
                    console.print(f"  [red]Deleted:[/red] {file.name}")
                    deleted += 1
                    freed += size
                except Exception as e:
                    console.print(f"  [yellow]Could not delete: {e}[/yellow]")
        else:
            console.print("  [dim]Skipped.[/dim]")

    console.print(f"\n[bold green]Done! Deleted {deleted} files. Freed {format_size(freed)}.[/bold green]")
    return deleted

import os
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table

console = Console()

def resolve_folder(folder: str) -> Path:
    base = Path(folder)
    if base.exists():
        return base
    # Try case-insensitive match
    if base.parent.exists():
        for d in base.parent.iterdir():
            if d.is_dir() and d.name.lower() == base.name.lower():
                return d
    return base

def preview_renames(renames: list):
    table = Table(title="Rename preview")
    table.add_column("#", style="dim", width=4)
    table.add_column("Before", style="yellow")
    table.add_column("After", style="green")

    for i, (old, new) in enumerate(renames, start=1):
        table.add_row(str(i), old, new)

    console.print(table)
    console.print(f"[dim]Total: {len(renames)} files will be renamed[/dim]")

def apply_renames(folder: str, renames: list) -> int:
    base = resolve_folder(folder)
    done = 0

    for old_name, new_name in renames:
        old_path = base / old_name
        new_path = base / new_name

        if not old_path.exists():
            console.print(f"[yellow]Skipping (not found): {old_name}[/yellow]")
            continue

        if new_path.exists():
            console.print(f"[yellow]Skipping (already exists): {new_name}[/yellow]")
            continue

        old_path.rename(new_path)
        console.print(f"[green]Renamed:[/green] {old_name} → {new_name}")
        done += 1

    console.print(f"\n[bold green]Done! Renamed {done} files.[/bold green]")
    return done

def rename_with_date(folder: str, pattern: str = "*") -> list:
    base = resolve_folder(folder)
    if not base.exists():
        console.print(f"[red]Folder not found: {folder}[/red]")
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    renames = []

    for f in sorted(base.iterdir()):
        if f.is_file() and f.match(pattern):
            new_name = f"{today}_{f.name}"
            renames.append((f.name, new_name))

    return renames

def rename_to_lowercase(folder: str, pattern: str = "*") -> list:
    base = resolve_folder(folder)
    if not base.exists():
        console.print(f"[red]Folder not found: {folder}[/red]")
        return []

    renames = []

    for f in sorted(base.iterdir()):
        if f.is_file() and f.match(pattern):
            new_name = f.name.lower()
            if new_name != f.name:
                renames.append((f.name, new_name))

    return renames

def rename_spaces_to_underscores(folder: str, pattern: str = "*") -> list:
    base = resolve_folder(folder)
    if not base.exists():
        console.print(f"[red]Folder not found: {folder}[/red]")
        return []

    renames = []

    for f in sorted(base.iterdir()):
        if f.is_file() and f.match(pattern):
            new_name = f.name.replace(" ", "_")
            if new_name != f.name:
                renames.append((f.name, new_name))

    return renames

def rename_add_prefix(folder: str, prefix: str, pattern: str = "*") -> list:
    base = resolve_folder(folder)
    if not base.exists():
        console.print(f"[red]Folder not found: {folder}[/red]")
        return []

    renames = []

    for f in sorted(base.iterdir()):
        if f.is_file() and f.match(pattern):
            new_name = f"{prefix}_{f.name}"
            renames.append((f.name, new_name))

    return renames

def rename_add_numbering(folder: str, pattern: str = "*") -> list:
    base = resolve_folder(folder)
    if not base.exists():
        console.print(f"[red]Folder not found: {folder}[/red]")
        return []

    files = sorted([f for f in base.iterdir() if f.is_file() and f.match(pattern)])
    renames = []

    for i, f in enumerate(files, start=1):
        ext = f.suffix
        new_name = f"{i:03d}{ext}"
        renames.append((f.name, new_name))

    return renames

def rename_single(folder: str, old_name: str, new_name: str) -> list:
    base = resolve_folder(folder)
    if not base.exists():
        console.print(f"[red]Folder not found: {folder}[/red]")
        return []

    if not (base / old_name).exists():
        console.print(f"[red]File not found: {old_name}[/red]")
        return []

    return [(old_name, new_name)]

def rename_replace_text(folder: str, find: str, replace: str, pattern: str = "*") -> list:
    base = resolve_folder(folder)
    if not base.exists():
        console.print(f"[red]Folder not found: {folder}[/red]")
        return []

    renames = []

    for f in sorted(base.iterdir()):
        if f.is_file() and f.match(pattern):
            if find in f.name:
                new_name = f.name.replace(find, replace)
                renames.append((f.name, new_name))

    return renames

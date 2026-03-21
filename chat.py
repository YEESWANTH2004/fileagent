import ollama
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from scanner import scan_folder, display_scan
from mover import move_files, undo_last, redo_last

console = Console()
CHAT_LOG = Path.home() / ".file-agent-chat-log.json"

def load_chat_log():
    if CHAT_LOG.exists():
        with open(CHAT_LOG) as f:
            return json.load(f)
    return []

def save_chat_log(log):
    with open(CHAT_LOG, "w") as f:
        json.dump(log, f, indent=2)

def build_system_prompt():
    home = str(Path.home())
    downloads = str(Path.home() / "Downloads")
    return f"""You are a smart file management assistant.
You help users organize, move, rename and manage their files.

IMPORTANT: This system is Linux. The user's home directory is {home}
Default Downloads folder is {downloads}
Always use these exact paths — never use /Users/ or Windows paths.

When the user asks to organize a folder, respond with:
ACTION: ORGANIZE
FOLDER: <folder path>

When the user asks to scan a folder, respond with:
ACTION: SCAN
FOLDER: <folder path>

When the user asks to undo, respond with:
ACTION: UNDO

When the user asks to redo or redo last action, respond with:
ACTION: REDO

When the user says "find duplicates", "remove duplicates", "scan duplicates", "duplicate files", "clean duplicates", respond with EXACTLY:
ACTION: DUPLICATES
FOLDER: <folder path>

IMPORTANT: Always use ACTION: DUPLICATES — never use ACTION: FIND or any other variation.

When the user asks to move all files back to root, restore original state, or flatten a folder, respond with:
ACTION: RESTORE
FOLDER: <folder path>

When the user asks to rename files, respond with:
ACTION: RENAME
FOLDER: <folder path>
MODE: <one of: date, lowercase, underscores, prefix, numbering, single, replace>
PATTERN: <file pattern like *.mp4 or * for all>
PREFIX: <prefix text if mode is prefix>
FIND: <text to find if mode is replace>
REPLACE: <text to replace with if mode is replace>
OLD: <old filename if mode is single>
NEW: <new filename if mode is single>

Rename mode rules:
- "rename with today's date" or "add date" → MODE: date
- "rename to lowercase" → MODE: lowercase
- "replace spaces with underscores" → MODE: underscores
- "add prefix X" → MODE: prefix
- "add numbers" or "number them" → MODE: numbering
- "rename X to Y" → MODE: single
- "replace X with Y in names" → MODE: replace

When the user says "add", "create files", "new file", "make file" with specific filenames, respond with:
ACTION: ADDFILE
FOLDER: <target folder path>
FILES: <comma separated filenames>

IMPORTANT: "add Student, Teacher to src" means ADDFILE not ORGANIZE.
ADDFILE is for creating NEW files inside a folder.
ORGANIZE is ONLY when user says "organize" or "clean up" a folder.
Never use ORGANIZE when user says "add" or lists specific filenames.

When the user asks to create a project or folder, detect the project type and respond with:
ACTION: CREATE
FOLDER: <base path>
STRUCTURE: <comma separated subfolder names>
FILES: <comma separated filenames>

Project type rules — use ONLY relevant folders and files:

WEBSITE project:
STRUCTURE: css, js, images
FILES: index.html, style.css, script.js

JAVA project:
STRUCTURE: src, lib, out, docs
FILES: src/Main.java

PYTHON project:
STRUCTURE: src, tests, docs
FILES: main.py, requirements.txt, README.md

REACT project:
STRUCTURE: src, public
FILES: src/App.js, src/index.js, public/index.html, README.md

DATA SCIENCE project:
STRUCTURE: data, notebooks, models, reports
FILES: main.py, requirements.txt, README.md

ANDROID project:
STRUCTURE: app/src/main/java, app/src/main/res, app/src/test
FILES: README.md

GENERAL/UNKNOWN project (just "create a folder"):
STRUCTURE: (empty — no subfolders)
FILES: README.md

If the user says "create a folder X" without any project type,
just create the folder with only a README.md inside.
If the user says "create a java folder" or "java project folder",
use the JAVA project structure.

IMPORTANT rules:
- Never mix project types — a Java project never gets HTML/CSS/JS
- Always match the project type to the correct structure
- If unsure about project type, ask the user to clarify
- For general questions or conversation, just respond normally.
Always be helpful, concise and friendly."""

STARTER_CONTENT = {
    ".html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Website</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>Hello World</h1>
    <script src="script.js"></script>
</body>
</html>""",

    ".css": """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    line-height: 1.6;
}""",

    ".js": """// JavaScript file
console.log('Hello World');""",

    ".py": """# Python file

def main():
    print('Hello World')

if __name__ == '__main__':
    main()""",

    ".md": """# Project Name

## Description
Add your description here.

## Setup
Add setup instructions here.

## Usage
Add usage instructions here.
""",

    "requirements.txt": """# Add your dependencies here
# example: requests==2.28.0
""",
}

SMART_PLACEMENT = {
    ".css":  "css",
    ".js":   "js",
    ".jpg":  "images",
    ".jpeg": "images",
    ".png":  "images",
    ".gif":  "images",
}

def get_java_class_content(filename: str) -> str:
    classname = Path(filename).stem
    return f"""public class {classname} {{

    // Constructor
    public {classname}() {{
        // Initialize here
    }}

    // Add your methods here
    public static void main(String[] args) {{
        System.out.println("{classname} loaded successfully");
    }}
}}
"""

def get_starter_content(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    name = Path(filename).name
    if ext == ".java":
        return get_java_class_content(filename)
    if name in STARTER_CONTENT:
        return STARTER_CONTENT[name]
    return STARTER_CONTENT.get(ext, "")

def create_files_in_folder(folder: str, files: list) -> int:
    base = Path(folder)
    base.mkdir(parents=True, exist_ok=True)
    created = 0

    for filename in files:
        filename = filename.strip()
        if not filename:
            continue

        if "." not in filename:
            filename = filename + ".java"

        ext = Path(filename).suffix.lower()
        subfolder = SMART_PLACEMENT.get(ext)
        if subfolder and (base / subfolder).exists():
            filepath = base / subfolder / filename
        else:
            filepath = base / filename

        if filepath.exists():
            console.print(f"  [yellow]Already exists:[/yellow] {filename}")
            continue

        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(get_starter_content(filename))
        console.print(f"  [green]✓[/green] Created: {filepath.relative_to(Path(folder).parent)}")
        created += 1

    return created

def handle_action(response_text: str, history: list):
    lines = response_text.strip().split("\n")
    action = None
    folder = None
    folders = []
    files = []
    mode = None
    pattern = "*"
    prefix = ""
    find = ""
    replace_with = ""
    old = ""
    new = ""

    for line in lines:
        line = line.strip()
        if line.startswith("ACTION:"):
            action = line.replace("ACTION:", "").strip().upper()
        elif line.startswith("FOLDER:"):
            folder = str(Path(line.replace("FOLDER:", "").strip()).expanduser())
        elif line.startswith("STRUCTURE:"):
            folders = [f.strip() for f in line.replace("STRUCTURE:", "").strip().split(",") if f.strip()]
        elif line.startswith("FILES:"):
            files = [f.strip() for f in line.replace("FILES:", "").strip().split(",") if f.strip()]
        elif line.startswith("MODE:"):
            mode = line.replace("MODE:", "").strip().lower()
        elif line.startswith("PATTERN:"):
            pattern = line.replace("PATTERN:", "").strip()
        elif line.startswith("PREFIX:"):
            prefix = line.replace("PREFIX:", "").strip()
        elif line.startswith("FIND:"):
            find = line.replace("FIND:", "").strip()
        elif line.startswith("REPLACE:"):
            replace_with = line.replace("REPLACE:", "").strip()
        elif line.startswith("OLD:"):
            old = line.replace("OLD:", "").strip()
        elif line.startswith("NEW:"):
            new = line.replace("NEW:", "").strip()

    # SCAN
    if action == "SCAN" and folder:
        console.print(f"\n[bold yellow]Scanning {folder}...[/bold yellow]\n")
        results = scan_folder(folder, recursive=True)
        display_scan(results, folder)
        return f"Scanned {folder} successfully."

    # ORGANIZE
    elif action == "ORGANIZE" and folder:
        console.print(f"\n[bold yellow]Scanning {folder}...[/bold yellow]\n")
        results = scan_folder(folder)
        display_scan(results, folder)
        total = sum(len(v) for v in results.values())
        if total == 0:
            console.print("[yellow]No files to organize — folder is already clean![/yellow]")
            return "Nothing to organize."
        confirm = input("\nProceed with organization? (y/n): ").strip().lower()
        if confirm == "y":
            move_files(results, folder)
            return f"Organized {folder} successfully."
        else:
            return "Organisation cancelled."

    # UNDO
    elif action == "UNDO":
        undo_last()
        return "Undo completed."

    # REDO
    elif action == "REDO":
        redo_last()
        return "Redo completed."


    # DUPLICATES
    elif action == "DUPLICATES" and folder:
        from duplicates import find_duplicates, display_duplicates, delete_duplicates, delete_duplicates_selective

        duplicates = find_duplicates(folder)

        if not duplicates:
            console.print("\n[bold green]No duplicates found![/bold green]")
            return "No duplicates found."

        display_duplicates(duplicates)

        total_dupes = sum(len(files) - 1 for files in duplicates.values())
        console.print("\n[bold]How do you want to delete?[/bold]")
        console.print("  [cyan]a[/cyan] = delete all duplicates at once")
        console.print("  [cyan]s[/cyan] = review each group one by one")
        console.print("  [cyan]n[/cyan] = cancel")
        choice = input("\nChoice (a/s/n): ").strip().lower()

        if choice == "a":
            count = delete_duplicates(duplicates)
            return f"Deleted {count} duplicate files."
        elif choice == "s":
            count = delete_duplicates_selective(duplicates)
            return f"Deleted {count} duplicate files."
        else:
            console.print("[yellow]Cancelled. No files deleted.[/yellow]")
            return "Duplicate deletion cancelled."

    # RESTORE
    elif action == "RESTORE" and folder:
        base = Path(folder)
        if not base.exists():
            console.print(f"[red]Folder not found: {folder}[/red]")
            return "Folder not found."

        files_to_restore = []
        for subfolder in base.iterdir():
            if subfolder.is_dir():
                for file in subfolder.iterdir():
                    if file.is_file():
                        files_to_restore.append((file, base / file.name))

        if not files_to_restore:
            console.print("[yellow]No files found in subfolders — already flat![/yellow]")
            return "Nothing to restore."

        console.print(f"\n[bold yellow]Files to move back to {folder}:[/bold yellow]")
        for src, dst in files_to_restore[:10]:
            console.print(f"  [dim]├──[/dim] {src.parent.name}/{src.name} → {src.name}")
        if len(files_to_restore) > 10:
            console.print(f"  [dim]... and {len(files_to_restore) - 10} more[/dim]")

        console.print(f"\n[bold]Total: {len(files_to_restore)} files[/bold]")
        confirm = input("\nMove all files back to root? (y/n): ").strip().lower()

        if confirm != "y":
            console.print("[yellow]Cancelled.[/yellow]")
            return "Restore cancelled."

        moved = 0
        skipped = 0
        for src, dst in files_to_restore:
            if dst.exists():
                console.print(f"[yellow]Skipping (exists): {src.name}[/yellow]")
                skipped += 1
                continue
            src.rename(dst)
            console.print(f"[green]Restored:[/green] {src.name}")
            moved += 1

        console.print(f"\n[bold green]Done! Restored {moved} files. Skipped {skipped}.[/bold green]")
        return f"Restored {moved} files back to {folder} root."

    # RENAME
    elif action == "RENAME" and folder:
        from renamer import (rename_with_date, rename_to_lowercase,
                            rename_spaces_to_underscores, rename_add_prefix,
                            rename_add_numbering, rename_single,
                            rename_replace_text, preview_renames, apply_renames)

        if mode == "date":
            renames = rename_with_date(folder, pattern)
        elif mode == "lowercase":
            renames = rename_to_lowercase(folder, pattern)
        elif mode == "underscores":
            renames = rename_spaces_to_underscores(folder, pattern)
        elif mode == "prefix":
            renames = rename_add_prefix(folder, prefix, pattern)
        elif mode == "numbering":
            renames = rename_add_numbering(folder, pattern)
        elif mode == "single":
            renames = rename_single(folder, old, new)
        elif mode == "replace":
            renames = rename_replace_text(folder, find, replace_with, pattern)
        else:
            renames = []

        if not renames:
            console.print("[yellow]No files to rename.[/yellow]")
            return "Nothing to rename."

        preview_renames(renames)
        confirm = input("\nApply these renames? (y/n): ").strip().lower()
        if confirm == "y":
            count = apply_renames(folder, renames)
            return f"Renamed {count} files successfully."
        else:
            console.print("[yellow]Cancelled. No files renamed.[/yellow]")
            return "Rename cancelled."

    # ADDFILE
    elif action == "ADDFILE" and folder and files:
        console.print(f"\n[bold yellow]Files to create in {folder}:[/bold yellow]")
        for f in files:
            fname = f if "." in f else f + ".java"
            console.print(f"  [dim]├──[/dim] {fname}")

        confirm = input("\nCreate these files? (y/n): ").strip().lower()
        if confirm != "y":
            console.print("[yellow]Cancelled. No files created.[/yellow]")
            return "File creation cancelled."

        count = create_files_in_folder(folder, files)
        return f"Created {count} file(s) in {folder}."

    # CREATE
    elif action == "CREATE" and folder:
        console.print(f"\n[bold yellow]Proposed structure:[/bold yellow]")
        console.print(f"  [cyan]{folder}/[/cyan]")
        for f in folders:
            console.print(f"  [dim]├──[/dim] [cyan]{f}/[/cyan]")
        for f in files:
            console.print(f"  [dim]├──[/dim] {f}")

        confirm = input("\nCreate this? (y/n): ").strip().lower()
        if confirm != "y":
            console.print("[yellow]Cancelled. Nothing created.[/yellow]")
            return "Creation cancelled by user."

        base = Path(folder)
        base.mkdir(parents=True, exist_ok=True)

        for subfolder in folders:
            (base / subfolder).mkdir(parents=True, exist_ok=True)
            console.print(f"  [green]✓[/green] Created folder: {subfolder}/")

        for filename in files:
            ext = Path(filename).suffix.lower()
            if "/" in filename:
                filepath = base / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
            else:
                subfolder = SMART_PLACEMENT.get(ext)
                if subfolder and (base / subfolder).exists():
                    filepath = base / subfolder / filename
                else:
                    filepath = base / filename

            filepath.write_text(get_starter_content(filename))
            console.print(f"  [green]✓[/green] Created file: {filepath.relative_to(base)}")

        return f"Created project at {folder} with {len(folders)} folders and {len(files)} files."

    return None

def chat():
    console.print(Panel(
        "[bold cyan]File Agent — Chat Mode[/bold cyan]\n"
        "[dim]Type your request naturally. Type 'exit' to quit.[/dim]\n"
        "[dim]Examples:[/dim]\n"
        "[dim]  'scan my downloads'[/dim]\n"
        "[dim]  'organize my downloads'[/dim]\n"
        "[dim]  'restore all files in downloads to root'[/dim]\n"
        "[dim]  'rename all mp4s with today's date in ~/Downloads/Videos'[/dim]\n"
        "[dim]  'replace spaces with underscores in ~/Downloads'[/dim]\n"
        "[dim]  'create a java project at ~/Desktop/MyApp'[/dim]\n"
        "[dim]  'add Student.java, Teacher.java to ~/Desktop/MyApp/src'[/dim]\n"
        "[dim]  'undo'[/dim]\n"
        "[dim]  'redo'[/dim]"
    ))

    history = []
    chat_log = load_chat_log()
    session = {
        "date": datetime.now().isoformat(),
        "conversations": []
    }

    system_prompt = build_system_prompt()

    while True:
        try:
            user_input = input("\n[You]: ").strip()
        except KeyboardInterrupt:
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "bye"]:
            console.print("[yellow]Goodbye![/yellow]")
            break

        history.append({
            "role": "user",
            "content": user_input
        })

        console.print("[dim]Thinking...[/dim]")

        try:
            response = ollama.chat(
                model="llama3.2",
                messages=[
                    {"role": "system", "content": system_prompt}
                ] + history
            )
            reply = response["message"]["content"]
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            continue

        action_result = handle_action(reply, history)

        if action_result:
            console.print(f"\n[bold green]Agent:[/bold green] {action_result}")
        else:
            console.print(f"\n[bold green]Agent:[/bold green] {reply}")

        history.append({
            "role": "assistant",
            "content": reply
        })

        session["conversations"].append({
            "user": user_input,
            "agent": reply,
            "action_result": action_result
        })

    chat_log.append(session)
    save_chat_log(chat_log)
    console.print(f"\n[dim]Conversation saved to {CHAT_LOG}[/dim]")

if __name__ == "__main__":
    chat()

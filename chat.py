import ollama
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from scanner import scan_folder, display_scan
from mover import move_files, undo_last

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

When the user asks to create a project or folder, detect the project type and respond with:
ACTION: CREATE
FOLDER: <base path>
STRUCTURE: <comma separated subfolder names>
FILES: <comma separated filenames>

When the user says "add", "create files", "new file", "make file" with specific filenames, respond with:
ACTION: ADDFILE
FOLDER: <target folder path>
FILES: <comma separated filenames>

IMPORTANT: "add Student, Teacher to src" means ADDFILE not ORGANIZE.
ADDFILE is for creating NEW files inside a folder.
ORGANIZE is ONLY when user says "organize" or "clean up" a folder.
Never use ORGANIZE when user says "add" or lists specific filenames.

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

GENERAL/UNKNOWN project:
STRUCTURE: src, docs, tests
FILES: README.md

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

        # Add extension if missing for java files
        if "." not in filename:
            filename = filename + ".java"

        ext = Path(filename).suffix.lower()

        # Smart placement for web files
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

    # ADDFILE — add files to existing folder
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

    # CREATE — new project
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
        "[dim]  'create a java project at ~/Desktop/MyApp'[/dim]\n"
        "[dim]  'add Student.java, Teacher.java to ~/Desktop/MyApp/src'[/dim]\n"
        "[dim]  'undo'[/dim]"
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

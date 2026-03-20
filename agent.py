import ollama
from scanner import scan_folder, display_scan
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

def build_prompt(scan_results: dict, folder: str) -> str:
    summary = []
    for category, files in scan_results.items():
        if files:
            summary.append(f"{category} ({len(files)} files): {', '.join(files[:3])}")
    files_summary = "\n".join(summary)

    return f"""You are a file organization assistant. 
A user wants to organize their folder: {folder}

Here is what's in the folder:
{files_summary}

Give a clear, specific plan to organize these files into subfolders.
List each action as: MOVE <filename> -> <subfolder>
Keep it practical and simple."""

def run_agent(folder: str):
    console.print(Panel(f"[bold cyan]File Agent[/bold cyan]\nScanning: {folder}"))

    # Step 1: Scan
    results = scan_folder(folder)
    display_scan(results, folder)

    # Step 2: Ask Llama
    console.print("\n[bold yellow]Thinking...[/bold yellow]\n")
    prompt = build_prompt(results, folder)

    response = ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}]
    )

    plan = response["message"]["content"]

    # Step 3: Show plan
    console.print(Panel(plan, title="[bold green]Organization Plan[/bold green]"))

    # Step 4: Ask user
    confirm = input("\nProceed with this plan? (y/n): ").strip().lower()
    if confirm == "y":
        from mover import move_files
        move_files(results, folder)
    else:
        console.print("[yellow]Cancelled. No files were changed.[/yellow]")

if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / "Downloads")
    run_agent(folder)

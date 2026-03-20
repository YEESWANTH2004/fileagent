# File Agent
AI-powered file organizer using Llama 3.2 running locally.

## Usage
```bash
file-agent ~/Downloads              # organize a folder
file-agent --scan-only ~/Downloads  # just scan
file-agent --undo                   # undo last action
```

## Setup
```bash
git clone https://github.com/YOURNAME/file-agent
cd file-agent
python3 -m venv venv
source venv/bin/activate
pip install ollama rich
ollama pull llama3.2
```

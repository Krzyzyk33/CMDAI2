# CMDAI2 - AI Terminal Assistant

CMDAI2 is a powerful, terminal-based AI coding assistant. It integrates directly into your command-line environment and supports multiple AI models (OpenAI, Nvidia NIM, Groq, local models) to help you code, debug, and execute tasks autonomously.

## Features
- **Auto Mode:** Fully autonomous agent that creates plans, edits code, and runs tests.
- **Multi-Model Support:** Connects to OpenAI, Nvidia NIM, and Groq endpoints. Local inference is supported via Llama (GGUF).
- **Tool-Calling Architecture:** Safely executes system commands, modifies files, and performs web searches.
- **Smart IDE Integration:** Pulls context from your IDE automatically.

## Installation
Ensure you have Python 3.12+ installed.
```bash
pip install -r requirements.txt
```

## Usage
Start the assistant by running:
```bash
python main.py
```
Or simply use the `cmdai2` batch command if configured.

Select your preferred API provider (OpenAI, Nvidia NIM, Groq), input your API key, and begin chatting.

## Contributing
Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute.

## Code of Conduct
Please adhere to the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

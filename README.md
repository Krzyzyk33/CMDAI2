# 🚀 CMDAI CODE: The Fully Autonomous Terminal Assistant

**CMDAI CODE** (formerly CMDAI2) is a next-generation, locally hosted AI coding assistant designed to live natively within your terminal. 

While there are many AI coding assistants out there (like Cursor, Aider, or ChatGPT), CMDAI CODE takes a fundamentally different approach. It is built for developers who want **full control, zero vendor lock-in, and an AI that actually *thinks* and *verifies* its work before handing it to you.**

---

## ✨ Key Features

### 🤖 Autonomous Auto-Testing (Self-Healing Loop)
Your agent will never hand you broken code. Whenever CMDAI CODE writes or edits your `.py` or `.js` scripts and finishes a task, it silently runs the compiler/interpreter in the background. 
* If it works: You get the final result.
* If it fails (e.g., `SyntaxError`): The model is denied control. It receives a strict system reprimand containing the error logs and is forced to autonomously patch the code, trapped in a self-healing loop until it executes perfectly!

### 🧠 Rolling Context (Smart Memory Compaction)
Say goodbye to *Out Of Memory (OOM)* crashes for massive 26B+ models. When your conversation history approaches 90% of your context window limit, CMDAI CODE fires up a dedicated, smaller side-model (`compaction_model`). It generates a concise summary of your work, clears the raw history, and frees up VRAM—allowing your powerful main model to continue writing code indefinitely.

### 🌐 Zero Vendor Lock-in (Local & Cloud Agnostic)
You are completely free. You can instantly switch the "brain" of your assistant between OpenAI, Anthropic, OpenRouter, blazing-fast free models on Groq/Cerebras, or **fully local models via LocalLLMAPI/Ollama**. Native Server-Sent Events (SSE) streaming ensures your local GPU outputs tokens to the terminal in real time.

### 🛡️ Tool Hallucination Prevention
No more broken JSON strings. CMDAI CODE natively parses JSON function calls under the hood and draws an elegant interface using the `Rich` library. It also features a "soft" loop detection: if the model gets stuck and uses a broken tool repeatedly, it receives a severe system prompt forcing it to change its strategy, rather than crashing your session.

### 💻 Native Local Execution
CMDAI CODE lives right in your environment. It automatically grabs context from your active IDE, searches through hundreds of files instantly (`grep_search`), scrapes the web for the latest documentation (`search_web`), and executes Python scripts or Bash commands directly on your machine.

---

## 🚀 Installation

Installing CMDAI CODE is effortless. We have provided an automated setup script that builds the package globally and safely migrates your old CMDAI2 data.

1. Clone or download this repository.
2. Open the project folder.
3. Run the setup script:
   ```cmd
   setup.bat
   ```
*(This script will run `pip install -e .`, add the directory to your PATH, and migrate your `~/.cmdai2` configuration to `~/.cmdai_code`).*

---

## 🛠️ Usage

Once installed, simply open a new Terminal/PowerShell window in any directory on your computer and type:

```cmd
cmdai-code
```
*(Alternatively, you can also use `cmdai code`)*

The beautiful, `Rich`-powered UI will launch right in your terminal, ready to build!

---

## 📂 Project Structure

* `src/main.py` – Entry point of the application.
* `src/agent.py` – The main brain, handling the Auto-Testing loop and tool execution.
* `src/context.py` – Context management, RAG, and Memory Compaction logic.
* `src/providers/` – API connectors for local and cloud AI providers.
* `src/tools/` – The suite of tools the AI can use (filesystem, bash, search, planning).

---
*Clean code, absolute autonomy, and zero limits. Let AI write and test your project completely on its own!*

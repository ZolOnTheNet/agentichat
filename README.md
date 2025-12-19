# agentichat

**Autonomous AI assistant in your terminal** - Talk to your files, the web, and your tasks with agentic AI powered by Ollama.

## ✨ Features

- 🤖 **Agentic AI**: Autonomous assistant with 14 built-in tools
- 📁 **File Operations**: Read, write, search, list files and directories
- 🌐 **Web Access**: Fetch URLs and search the web (DuckDuckGo)
- 📋 **Task Management**: Built-in TODO list with status tracking
- 🔄 **Interactive UX**: Real-time stats, confirmations, model selector
- 🔒 **Secure**: Sandboxed file operations with user confirmations
- ⚡ **Fast**: Optimized for Ollama with streaming support

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai/) installed and running

### Installation

```bash
# Install from source (PyPI coming soon)
git clone <repository>
cd agentichat
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -e .
```

### First Run

```bash
agentichat
```

On first run, the program will:
1. Detect if your configured model is invalid
2. Show an interactive model selector
3. Save your choice to configuration

## 🛠️ Available Tools

The AI assistant has access to 14 tools organized by category:

### 📁 Files
- `read_file` - Read file contents
- `write_file` - Create or modify files
- `list_files` - List directory contents
- `delete_file` - Delete files
- `search_text` - Search text with regex
- `glob_search` - Find files by pattern (e.g., `*.py`, `**/*.js`)

### 📂 Directories
- `create_directory` - Create directories
- `delete_directory` - Remove directories
- `move_file` - Move/rename files or directories
- `copy_file` - Copy files or directories

### 🌐 Web
- `web_fetch` - Fetch content from URLs
- `web_search` - Search the web (DuckDuckGo)

### 💻 System
- `shell_exec` - Execute shell commands

### 📋 Productivity
- `todo_write` - Manage task lists with status tracking

## 💬 Usage

### Interactive Mode

```bash
agentichat
```

Just ask natural language questions:
```
> List all Python files in this directory
> Read the config file and explain what it does
> Search the web for "Ollama function calling"
> Create a TODO list for this project
```

The AI will automatically use the appropriate tools to complete your requests.

### Commands

- `/help` - Show help
- `/quit`, `/exit`, `/q` - Quit
- `/clear` - Reset conversation
- `/config` - Show configuration
- `/models` - Select a different model

### Keyboard Shortcuts

- `Enter` - Send message
- `Alt+Enter` or `Ctrl+J` - New line
- `↑` / `↓` - Navigate history (on first/last line)
- `Esc` - Clear current input
- `Ctrl+D` - Quit

## ⚙️ Configuration

Configuration file locations (in priority order):
1. `.agentichat/config.yaml` (workspace local)
2. `~/.agentichat/config.yaml` (global)

### Basic Configuration (Ollama)

```yaml
default_backend: ollama

backends:
  ollama:
    type: ollama
    url: http://localhost:11434
    model: qwen2.5-coder:7b
    temperature: 0.7
    max_tokens: 4000
    timeout: 300

agent:
  max_iterations: 10
  confirm_destructive: true

logging:
  level: INFO
```

### Using Albert API (Etalab)

Albert is a French public service API providing advanced features:

```yaml
default_backend: albert

backends:
  albert:
    type: albert
    url: https://albert.api.etalab.gouv.fr
    model: AgentPublic/albertlight-7b
    api_key: YOUR_API_KEY  # Get one at albert.api.etalab.gouv.fr
    temperature: 0.7
    max_tokens: 4000
    timeout: 60
```

**Albert-specific tools (4 additional tools):**
- `albert_search` - Semantic search in document collections
- `albert_ocr` - Extract text from images/PDFs
- `albert_transcription` - Convert audio to text
- `albert_embeddings` - Create text embeddings for similarity

## 🏗️ Architecture

```
agentichat/
├── src/agentichat/
│   ├── cli/           # CLI interface (app, editor, confirmations)
│   ├── backends/      # LLM adapters (Ollama, Albert, extensible)
│   ├── config/        # Configuration management
│   ├── core/          # Agent loop and orchestration
│   ├── tools/         # Tool implementations (14 base + 4 Albert)
│   └── utils/         # Sandbox, logging, helpers
└── docs/              # Documentation
```

## 🔐 Security

- **Sandbox**: All file operations are validated against allowed paths
- **Confirmations**: Destructive operations (delete, shell exec) require user approval
- **Transparency**: All tool calls are logged and visible

## 🎯 Comparison with Other Tools

| Tool | Type | Use Case |
|------|------|----------|
| `llm` (Simon Willison) | CLI prompt tool | Quick prompts, scriptable |
| `llama-agents` | Multi-agent framework | Build complex agent systems |
| `agentichat` | **Agentic CLI** | **Ready-to-use autonomous assistant** |

**agentichat** fills the gap between simple prompting and complex frameworks - it's an autonomous assistant that works out of the box.

## 🧪 Development

### Run Tests

```bash
pip install -e ".[dev]"
pytest
```

### Code Quality

```bash
# Linting
ruff check .
ruff format .

# Type checking
mypy src/
```

## 📝 License

MIT

## 🙏 Acknowledgments

Built with:
- [Ollama](https://ollama.ai/) - Local LLM runtime
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) - Interactive CLI

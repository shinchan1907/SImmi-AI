# 🤖 Simmi Agent - V2 Production

Simmi Agent is a production-grade, modular, and extremely polished autonomous AI agent framework designed for high-performance deployment on a Linux VPS.

## ✨ Features

- 💎 **Modern CLI**: Rich, animated interface with beautiful banners, tables, and spinners.
- 👥 **Multi-Agent Teams**: Collaboration between specialized agents (Planner, Coder, Researcher, Debugger, Security, DevOps).
- ⛓️ **DAG Task Graph**: Automatic decomposition of complex goals into Directed Acyclic Graphs.
- 🔄 **Self-Debugging**: Automatic error detection and code correction loop using Docker sandboxes.
- 🎙️ **Voice Interaction**: Support for incoming voice notes (Whisper STT) and realistic spoken replies (ElevenLabs TTS).
- 🧠 **Evolutionary Memory**:
    - **Reflections**: Post-task analysis to extract lessons and inefficiencies.
    - **Experiences**: Structured memory of past tasks, approaches, and results.
- 🛠️ **Prompt Optimization**: Automatic refinement of agent system prompts based on performance feedback.
- 📈 **System Intelligence**: Observability and growth reports accessible via `simmi report`.
- 🩹 **Self-Repair**: Autonomous fault detection and sandboxed patching of system errors.
- 🔒 **Security First**: Fernet encryption for API keys, user whitelisting, and secure sandboxing.
- 🗃️ **Advanced Memory**:
    - **Short-term**: LIFO Redis cache for immediate conversation context.
    - **Long-term**: PostgreSQL with `pgvector` for semantic recall.
- 🛠️ **Modular Tooling**: Registry-based tool system with structured I/O and timeout protection.
- 🐳 **Secure Sandbox**: Docker-based code execution for generating and testing code.
- 📊 **Observability**: Centralized structured JSON logging with terminal-styled output.

## 📁 Repository Structure

```text
simmi-agent/
├── api/             # FastAPI temporary link server
├── cli/             # Advanced CLI (Rich, Questionary)
├── config/          # Encrypted YAML configurations
├── core/            # LLM Logic, Agent Core, Security, Logger
├── execution/       # Docker Sandbox implementation
├── integrations/    # Telegram & microservices
├── logs/            # Centralized structured logs
├── memory/          # PGVector & Redis managers
├── scheduler/       # APScheduler management
├── storage/         # Local file & project storage
├── tools/           # Extensible tool system
└── tests/           # Unit and integration tests
```

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- PostgreSQL + `pgvector`
- Redis
- Docker Engine

### 2. Installation
```bash
git clone https://github.com/your-repo/simmi-agent.git
cd simmi-agent
pip install -r requirements.txt
pip install -e .
```

### 3. Initialization
Run the interactive setup wizard to configure your agent:
```bash
simmi init
```

### 4. Start the Agent
Launch all services (Telegram, Scheduler, API) with a single command:
```bash
simmi start
```

## 🔧 CLI Commands

- `simmi init`: Launch the animated setup wizard.
- `simmi doctor`: Run system health checks (Postgres, Redis, Docker).
- `simmi status`: View real-time service status.
- `simmi start`: Bootstrap the agent and bot services.
- `simmi tools`: List available agent tools.
- `simmi memory`: Search the agent's long-term memory.

## 📄 License
MIT © 2026 Simmi AI Team

# Digital Persona Codespace

Welcome to the dev container for the **Digital Persona** project. This environment installs Python 3.12, Poetry, and the common tooling needed to run the personality interview CLI.

---

## 🔧 Features

- Poetry-based Python setup on top of the official Python dev container image
- VS Code extensions for Python, Jupyter, YAML, Markdown, and Docker
- Libraries for OpenAI, LangChain, HuggingFace, Pandas, and Scikit-learn
- RDF and JSON-LD utilities for semantic formats used by the schemas

---

## Secrets

Provide the following Codespaces secrets so the interviewer can use language models:

- `OPENAI_API_KEY` – required for OpenAI integration
- `HF_API_KEY` – optional, for HuggingFace models

---

## Mounted Folders

- `src/` – your Python code
- `data/` – persistent storage for notes and example documents

---

## Getting Started

1. Open the repository in GitHub Codespaces.
2. The container builds and runs `poetry install` automatically.
3. Open the command palette (**Run Task → Interview**) or run:

   ```bash
   poetry run digital-persona-interview
   ```

  The devcontainer also starts the FastAPI service automatically on port `8000`. It calls `scripts/start-api.sh` via `postStartCommand`, which runs Uvicorn with `nohup` so the process keeps running after startup. You can stop it with `pkill -f uvicorn` and rerun the same script. If the `OPENAI_API_KEY` secret is not provided the server falls back to using an Ollama model, which requires an Ollama service at `http://localhost:11434`. You can visit `http://localhost:8000/docs` to try the API.

   If you launch the devcontainer using the command line instead of VS Code or Codespaces, be sure to map the port explicitly with `-p 8000:8000` so the API is reachable from your host machine.

The `Interview (Dry Run)` task runs the same command with `--dry-run` so you can test without providing real answers.

# Digital Persona Codespace

Welcome to the dev container for the **Digital Persona** project. This environment installs Python 3.12, Poetry, and the common tooling needed to run the personality interview CLI.

---

## 🔧 Features

- Poetry-based Python setup on top of the official Python dev container image
- VS Code extensions for Python, Jupyter, YAML, Markdown, and Docker
- Libraries for OpenAI, LangChain, HuggingFace, Pandas, and Scikit-learn
- RDF and JSON-LD utilities for semantic formats used by the schemas
- Installs `ffmpeg` and the project's optional media dependencies during container setup
- Want local audio transcription? Install the optional `openai-whisper` package with `pip install -e .[speech]` and set `TRANSCRIBE_PROVIDER=whisper`.

---

## Secrets

Provide your API keys via Codespaces secrets or by creating `.devcontainer/.env` (copy the example file). Useful variables include:

- `OPENAI_API_KEY` – required for OpenAI integration
- `HF_API_KEY` – optional, for HuggingFace models

---

## Mounted Folders

- `src/` – your Python code
- `data/` – persistent storage for notes and example documents

---

## Getting Started

1. Open the repository in GitHub Codespaces.
2. The container installs `ffmpeg` and all Python dependencies using `poetry install --with dev --extras media` so image and audio processing works out of the box.
3. Copy `.devcontainer/.env.example` to `.devcontainer/.env` and fill in any API keys you want to use. The container loads this file automatically when it starts.
4. Open the command palette (**Run Task → Interview**) or run:

   ```bash
   poetry run digital-persona-interview
   ```

 The devcontainer also starts the FastAPI service automatically on port `8000`. It calls `scripts/start-services.py` via `poetry run` in the `postStartCommand` using `nohup`, so Uvicorn and the ingest loop run in the background. You can stop the processes with `pkill -f uvicorn` and rerun the same script. If `OPENAI_API_KEY` is not provided, the app falls back to an Ollama model instead. The container is configured to reach an Ollama server on your host machine using `http://host.docker.internal:11434`. Visit `http://localhost:8000/docs` to try the API. Logs are written to `/tmp/uvicorn.log`, `/tmp/ingest.log`, and `/tmp/services.log` for troubleshooting.

   If you launch the devcontainer using the command line instead of VS Code or Codespaces, be sure to map the port explicitly with `-p 8000:8000` so the API is reachable from your host machine.

The `Interview (Dry Run)` task runs the same command with `--dry-run` so you can test without providing real answers.

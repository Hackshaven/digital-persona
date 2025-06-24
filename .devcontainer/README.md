# Digital Persona Codespace

Welcome to the dev container for the **Digital Persona** project. This environment installs Python 3.11, Poetry, and the common tooling needed to run the personality interview CLI.

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

The `Interview (Dry Run)` task runs the same command with `--dry-run` so you can test without providing real answers.

## 📘 AGENTS.md — Instructions for Code Agents (LLMs, Codex, etc.)

This file provides guidance for AI agents (e.g. GitHub Copilot, ChatGPT Codex, or local assistants) on how to interpret and extend the `digital-persona` schema repository.

---

### 🧠 Project Purpose

This repository defines structured formats (JSON-LD contexts, JSON Schemas, examples, and trait vocabularies) for representing:

- Personality trait profiles (Big Five, HEXACO)
- Journal entries, emails, and memories (using ActivityStreams)
- Narrative identity and life goals
- Adaptation-layer metadata (coping style, significance)

This data supports the development of digital personality clones, virtual assistants, and behavioral simulation agents.

See the [mission statement](https://github.com/Hackshaven/digital-persona/wiki/Mission) for the guiding principles. When proposing or reviewing new features, ensure they align with that mission.


### 📚 Research References

When tackling design or architecture questions, consult the research papers stored in the `docs/` directory for guidance: These files are copied from the repository wiki during container setup and remain untracked. Do not delete them; use them for context.
- "Representing Personal Data and Personality Traits: Existing JSON/Semantic Standards"
- "Scientifically Grounded Personality Tests and Their Evolution into Digital Personas"
- "Personal Digital Clones: Ethical, Legal, and Philosophical Implications"
- "Designing User Interfaces for Digital Clones: Research & Best Practices"
Use insights from these documents to inform design decisions.

### 📁 Directory Overview

| Folder | Agent Usage |
|--------|-------------|
| `schema/context/` | Load the `personality-context.jsonld` to expand trait and narrative tags within ActivityStreams objects. Use this when serializing journal entries or content. |
| `schema/schemas/` | Load `personality-traits.json` to validate trait scores (must be 0.0–1.0 normalized floats). Use `jsonschema` or `ajv`. |
| `schema/ontologies/` | Use `trait-vocabulary.md` to interpret meaning of traits. This helps explain or label personality test results. |
| `schema/utils/` | Reuse `trait_helpers.py` to convert raw percentile or score values to normalized trait scores for consistent use. |
| `schema/tests/` | Extend with new test cases for any new traits, schema versions, or example content. |
| `src/` | Location of source code for commandline tool and web site front end.  Additional code and features should be put in this directory. |
| `scripts/` | Helper scripts for container development. |
| `data/` | Sample input data used to test the project JSON output. |
| `docs/` | Contains research papers providing project background and design requirements. The devcontainer copies these files from the repository wiki and leaves them untracked; use them for context and do not delete them. Adjust `.github/workflows/pages.yml` if schema filenames referenced there change. |
| `tests/` | Pytest tests |
| `.github/workflows/` | CI checks will automatically validate schemas and example use cases. Ensure new examples conform. |

---

### ✅ Rules for Trait Representation

- Trait values should be between `0.0` and `1.0` inclusive.
- Traits not in the `schema/schemas/personality-traits.json` file must not be added without extending that schema.
- For narrative-based personality tags, prefer IRI-based tagging via `narrativeTheme`.

---

### 🔍 Agent Capabilities Suggested

If you're an LLM agent working on this repo, you are encouraged to:

- Autocomplete new journal entries with consistent traits and memory significance
- Validate new trait profiles before committing
- Suggest inferred traits for untagged diary text
- Offer conversions: raw score → normalized → narrative label
- Use the JSON-LD context when generating structured personality-aware content

---

### 🛠️ Extend Me

If you create:
- New trait frameworks (e.g. Dark Triad)
- Cognitive biases or coping styles
- Memory embeddings
Add new schema entries or narrative types in a consistent style.

### 📄 License
This project is licensed under the MIT License. See `LICENSE` for details.

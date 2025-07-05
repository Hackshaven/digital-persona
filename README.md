## Digital Persona Project

[![Chat with our Bot](https://img.shields.io/badge/ChatBot-Online-green)](https://chatgpt.com/g/g-6860217d14fc8191b9be6b80e74134fe-digital-persona-helper-bot) [![CI Status](https://github.com/Hackshaven/digital-persona/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/Hackshaven/digital-persona/actions/workflows/test.yml)

This project provides a modular AI system that emulates a user's personality using psychometric modeling, memory streams, and narrative identity. It aims to serve as a personal assistant, memory companion, and expressive interface—all under user control.

For more detailed architecture, schema examples, ethical principles, and tutorials, visit the [GitHub Wiki](https://github.com/Hackshaven/digital-persona/wiki). If you'd prefer to ask questions or get into a philosophical argument check in with the [Digital Persona Helper Bot](https://chatgpt.com/g/g-6860217d14fc8191b9be6b80e74134fe-digital-persona-helper-bot).

---

### Project Mission

See the [Mission Statement](https://github.com/Hackshaven/digital-persona/wiki/Mission) for the project’s guiding principles. New features and pull requests should be checked against this statement to ensure ethical use, user control, and safe handling of personality data.

---

### What is a Digital Persona?

A "Digital Persona" is an AI clone that mirrors your thinking style, goals, and values. It differs from generic chatbots by learning from your actual data—emails, notes, journals—to reflect your true voice and behavior. It can:

- Simulate realistic conversations in your voice
- Recall and reason over memories
- Assist with daily tasks while reflecting your preferences
- Offer psychologically grounded reflections using MBTI, Big Five, Dark Triad, and other validated models

---

### Features and Architecture

- **Ethical Guardrails**: Guided by four principles:
  - Do No Harm
  - Respect User Autonomy
  - Integrity and Self-Protection
  - Honest Identity

- **Directory Structure**:
  - `schema/context/` → JSON-LD context extensions
  - `schema/schemas/` → JSON Schema files for trait and test validation plus interview results
  - `schema/ontologies/` → Markdown definitions for traits and goals
  - `schema/utils/` → Helper utilities for trait conversions
  - `schema/tests/` → Unit tests for schema validation
  - `src/digital_persona/` → Python package containing utilities
  - `src/digital_persona/interview.py` → Interview assistant that derives personality traits from unstructured user data
  - `src/frontend/` → Static HTML and CSS for the basic web interface
  - `scripts/` → Helper scripts like `start-services.py` used by the devcontainer
  - `docs/` → Research papers used as additional prompt context (available in the container, otherwise in the wiki)

- **Prompt Engineering**: Prompts use structured memory, personality traits, and psychological insight to produce deeply personalized responses.

- **Semantic Standards**: Includes trait schemas, tagging ontologies, and alignment to scientific models (MMPIs, BFI, etc).

- **Security & Privacy**:
  - Private vs. Public memory tagging
  - User-controlled memory deletion and editing
  - Output filters to prevent impersonation or data leaks

---

### Development Setup

The project is designed for interactive local development using either OpenAI or Ollama models.

1. **OpenAI Setup**:
   - Set `OPENAI_API_KEY` in your environment.
   - Optionally set `OPENAI_MODEL` (e.g., `gpt-4o`).

2. **Ollama Setup**:
   - Install [Ollama](https://ollama.com/) locally.
   - Run a model (e.g., `ollama run llama3`).
   - Set environment:
     ```bash
     export OLLAMA_BASE_URL=http://localhost:11434
     export OLLAMA_MODEL=llama3
     ```

3. **Run Dev CLI**:
   - Use the CLI directly or within the devcontainer: `digital-persona-interview data/my_notes.txt -p openai` or `-p ollama`
   - Add `--dry-run` to simulate answers from the model.
4. **Devcontainer Notes**:
  - The container automatically runs `scripts/start-services.py` (via `poetry run` and `nohup`) so the API server and ingest loop keep running in the background.
  - If they fail to start, run `~/.local/bin/poetry run python scripts/start-services.py >/tmp/services.log 2>&1 &`.
  - Logs are written to `/tmp/uvicorn.log`, `/tmp/ingest.log`, and `/tmp/services.log`.
    The ingest loop prints a message each time it processes a file so you can
    watch that log to confirm activity.
  - Copy `.devcontainer/.env.example` to `.devcontainer/.env` to provide your API keys and other settings. The container loads this file automatically via a Docker `--env-file` argument.
  - Add your markdown files to `docs/` for inclusion in the runtime prompt context.
5. **Run the Ingest Loop**:
   - Execute `digital-persona-ingest` to poll the `input` folder and convert new files into JSON memories.
   - Place any text, image, audio, or video files you want processed into `PERSONA_DIR/input` (defaults to `./persona/input`).
  - Install optional media dependencies with `pip install -e .[media]` to enable image, audio, and video processing (the devcontainer installs them automatically).
  - Ensure the `ffmpeg` binary is available on your PATH for video extraction (preinstalled in the devcontainer).
   - After cloning the repo run `git lfs install` so the sample media files are fetched correctly.
   - Image files are detected automatically; EXIF metadata is stored and a short caption is generated so they can be used during interviews.
  - Audio files are transcribed using the OpenAI API by default. Set `TRANSCRIBE_PROVIDER=whisper` to use a local Whisper model instead.
  - Video files are processed by extracting a preview frame and audio track. The frame is captioned and the audio is transcribed, summarized, and tagged with sentiment.
  - Captions, summaries, and sentiment defaults to using Ollama models. Set `CAPTION_PROVIDER=openai` to use OpenAI APIs instead. Use `CAPTION_MODEL` to select the model name.
  - Sanitize input text to remove injection phrases and convert HTML or JSON to clean plain text before creating ActivityStreams memories.
  - Non-text inputs are transcribed or captioned by the ingest loop so the interview script can reason over them.
  - Files that fail to process are moved to `PERSONA_DIR/troubleshooting` for manual review.
6. **API Usage**:
   - The `/pending` and `/start_interview` endpoints operate on files in `PERSONA_DIR/memory` produced by the ingest loop.
   - Each memory is a JSON object with a `content` field used for interview questions.
   - The object also stores a relative `source` path to the processed original file so you can reference images or audio later.
   - Non-text media should be ingested first so a text summary is available.
   - Completed memories are moved to `PERSONA_DIR/archive` after `/complete_interview` so they won't be processed twice.

### Sample Data

The `data/` folder contains example files for testing ingestion. Binary media
files aren't stored in the repository. Generate them locally with
`python scripts/generate_samples.py`:

- `my_notes.txt` – snippet of email, journal, and chat messages
- `sample_page.html` – short blog-style page describing a weekend hike
- `sample_data.json` – example daily schedule in JSON form
- `sample_image.jpg` – generated 10×10 sky-blue image
- `sample_audio.wav` – generated one-second sine wave
- `sample_video.mp4` – generated one-second red-square video with audio (uses AAC encoding for broad compatibility)

Copy any of these files into `PERSONA_DIR/input` and run the ingest loop to see how different media types are processed.

---

### Example: Personality Interview

The `interview` script analyzes text (emails, journal entries, etc.), generates reflection questions, and compiles a JSON profile.

```python
from digital_persona.interview import PersonalityInterviewer

data = """Email: I'm looking forward to the team retreat next month.\n
Journal: I've been worried about meeting deadlines but remain optimistic."""

interviewer = PersonalityInterviewer(num_questions=3)
questions = interviewer.generate_questions(data)
print("\n".join(questions))
```

Question sample:
```
Q: How do you manage approaching deadlines?
A: I set priorities and talk with the team.

Q: What steps do you take to resolve conflicts at work?
A: I try to consider everyone’s viewpoint.

Q: What hobbies help you relax?
A: Hiking and reading help me unwind.
```

JSON output:
```json
{
  "unstructuredData": "Email: I'm looking forward to the team retreat next month.\nJournal: I've been worried about meeting deadlines but remain optimistic.",
  "userID": "anon-1234",
  "interview": [
    {"question": "How do you manage approaching deadlines?", "answer": "I set priorities and talk with the team."},
    {"question": "What steps do you take to resolve conflicts at work?", "answer": "I try to consider everyone's viewpoint."},
    {"question": "What hobbies help you relax?", "answer": "Hiking and reading help me unwind."}
  ],
  "traits": {
    "openness": 0.63,
    "conscientiousness": 0.72,
    "extraversion": 0.55,
    "agreeableness": 0.68,
    "neuroticism": 0.40,
    "honestyHumility": 0.59,
    "emotionality": null
  },
  "darkTriad": {
    "narcissism": null,
    "machiavellianism": null,
    "psychopathy": null
  },
  "mbti": {"mbti": null},
  "mmpi": {
    "hypochondriasis": null,
    "depression": null,
    "hysteria": null,
    "psychopathicDeviate": null,
    "masculinityFemininity": null,
    "paranoia": null,
    "psychasthenia": null,
    "schizophrenia": null,
    "hypomania": null,
    "socialIntroversion": null
  },
  "goal": {"description": null, "status": null, "targetDate": null},
  "value": {"valueName": null, "importance": null},
  "narrative": {
    "eventRef": null,
    "narrativeTheme": null,
    "significance": null,
    "copingStyle": null
  },
  "psychologicalSummary": "Assigned openness=0.63 for your interest in new ideas, conscientiousness=0.72 because you plan tasks carefully, extraversion=0.55 since you enjoy team activities, agreeableness=0.68 due to collaborative comments, and neuroticism=0.40 reflecting only mild worry",
  "timestamp": "2024-05-04T15:32:10Z"
}
```

---

### License

MIT — see the [LICENSE](LICENSE) file for details.

---

### Documentation

Explore research and schema docs at [digital-persona GitHub Pages](https://hackshaven.github.io/digital-persona/). Markdown files in `docs/` power the site and help explain schemas, interviews, and integrations.

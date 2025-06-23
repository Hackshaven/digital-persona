# digital-persona

This project provides a schema and context system for representing personality traits, memories, and identity features in ActivityStreams-compatible formats for use in AI and digital clone systems.

## Key Features
- Big Five, HEXACO, MBTI, Dark Triad, and MMPI trait support
- JSON-LD context for semantic personality tagging
- JSON Schema for trait validation
- Sample entries and narrative fragments

## Directory Structure
- `schema/context/` – JSON-LD context extensions
- `schema/schemas/` – JSON Schema files for trait and test validation plus interview results
- `schema/ontologies/` – Markdown definitions for traits and goals
- `schema/utils/` – Helper utilities for trait conversions
- `schema/tests/` – Unit tests for schema validation
- `src/digital_persona/` – Python package containing utilities
- `src/digital_persona/interview.py` – Interview assistant that derives
  personality traits from unstructured user data

## Example: Interview Script

The script can analyze diary entries, emails, or other free-form text. It then
poses follow-up questions and returns a profile matching the
`personality-interview.json` schema, which includes both the interview data and
trait scores.

```python
from digital_persona.interview import PersonalityInterviewer
import json

data = """Email: I'm looking forward to the team retreat next month.
Journal: I've been worried about meeting deadlines but remain optimistic."""

interviewer = PersonalityInterviewer(num_questions=3)
questions = interviewer.generate_questions(data)
print("\n".join(questions))
# Example output:
# How do you manage approaching deadlines?
# What steps do you take to resolve conflicts at work?
# What hobbies help you relax?
# The interviewer may add clarifying follow-ups such as:
# Could you give an example of how you prioritize tasks?

# After answering the questions (including any follow-ups), gather the Q&A pairs
qa_pairs = [
    "Q: " + questions[0] + "\nA: I set priorities and talk with the team.",
    "Q: " + questions[1] + "\nA: I try to consider everyone's viewpoint.",
    "Q: " + questions[2] + "\nA: Hiking and reading help me unwind.",
]
profile = interviewer.profile_from_answers(data, qa_pairs)
print(json.dumps(profile, indent=2))
```

Which outputs JSON similar to:

```json
{
  "unstructuredData": "Email: I'm looking forward to the team retreat next month.\nJournal: I've been worried about meeting deadlines but remain optimistic.",
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
  "mbti": "ENFP",
  "darkTriad": {
    "narcissism": 0.31,
    "machiavellianism": 0.22,
    "psychopathy": 0.18
  },
  "mmpi": {
    "hypochondriasis": 0.20,
    "depression": 0.35,
    "hysteria": 0.25,
    "psychopathicDeviate": 0.40,
    "masculinityFemininity": 0.60,
    "paranoia": 0.15,
    "psychasthenia": 0.30,
    "schizophrenia": 0.10,
    "hypomania": 0.45,
  "socialIntroversion": 0.55
  },
  "psychologicalSummary": "Based on your email about the upcoming retreat and notes about deadline worries, you seem optimistic and cooperative though somewhat anxious about performance",
  "timestamp": "2024-05-04T15:32:10Z"
 }
```

The exact questions and scores will vary depending on the language model and
your responses.
If the interview doesn't provide enough detail for a particular trait, that
trait value will appear as `null` in the JSON output. The profile also includes
an ISO 8601 `timestamp` marking when the interview was completed.

### Command Line Usage

You can run the interviewer directly from the command line. Pass a text
file or `-` to read from standard input, and optionally choose the language model
provider:

```bash
$ digital-persona-interview my_notes.txt -p openai
```

This launches an interactive session where you answer the generated questions
and any clarifying follow-ups, then receive a JSON profile at the end. If you do
not specify `--questions`, the interviewer asks roughly one question per trait
to gather adequate information.

The interviewer defaults to OpenAI's API and reads your `OPENAI_API_KEY` from the
environment. You can instead talk to a local Ollama server by passing
`-p ollama` and setting `OLLAMA_BASE_URL` (default `http://localhost:11434`) and
`OLLAMA_MODEL`.

Environment variables:

- `OPENAI_API_KEY` – API key for OpenAI models when using the `openai` provider.
- `OPENAI_MODEL` – optional model name (e.g., `gpt-4o`).
- `OLLAMA_BASE_URL` – base URL of your Ollama server (default `http://localhost:11434`).
- `OLLAMA_MODEL` – model name served by Ollama (e.g., `llama3`).

## License
MIT - see the [LICENSE](LICENSE) file for details.

## GitHub Pages

This repository publishes the contents of the `docs/` folder via GitHub Pages. The site is deployed from the artifact produced by the `Deploy GitHub Pages` workflow, so Pages should be configured to **build and deploy from GitHub Actions**. You can view the hosted files at [https://hackshaven.github.io/digital-persona/](https://hackshaven.github.io/digital-persona/).

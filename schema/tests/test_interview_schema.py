import json
import jsonschema
from pathlib import Path


def test_valid_interview_profile():
    schema_dir = Path(__file__).parent.parent / "schemas"
    schema_path = schema_dir / "personality-interview.json"
    with open(schema_path) as f:
        schema = json.load(f)

    example = {
        "unstructuredData": "Email snippet...",
        "interview": [
            {"question": "How do you handle stress?", "answer": "I meditate"}
        ],
        "traits": {
            "openness": 0.5,
            "conscientiousness": 0.7,
            "extraversion": 0.6,
            "agreeableness": 0.8,
            "neuroticism": 0.3,
            "honestyHumility": 0.6,
            "emotionality": 0.4
        },
        "psychologicalSummary": "Calm and balanced individual",
        "timestamp": "2024-01-01T12:00:00Z"
    }

    resolver = jsonschema.RefResolver(base_uri=schema_path.as_uri(), referrer=schema)
    jsonschema.Draft202012Validator(schema, resolver=resolver).validate(example)

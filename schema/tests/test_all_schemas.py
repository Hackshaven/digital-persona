import json
from pathlib import Path
import pytest
import jsonschema


# --- Schema/example pairs (update this dict) ---
SCHEMA_EXAMPLES = {
    "dark-triad.json": {
        "narcissism": 0.5,
        "machiavellianism": 0.4,
        "psychopathy": 0.3,
    },
    "mbti-type.json": {
        "mbti": "INTJ",
    },
    "mmpi-scales.json": {
        "hypochondriasis": 0.2,
        "depression": 0.3,
        "hysteria": 0.1,
        "psychopathicDeviate": 0.4,
        "masculinityFemininity": 0.5,
        "paranoia": 0.2,
        "psychasthenia": 0.3,
        "schizophrenia": 0.25,
        "hypomania": 0.45,
        "socialIntroversion": 0.35,
    },
    "personality-traits.json": {
        "openness": 0.88,
        "conscientiousness": 0.75,
        "extraversion": 0.60,
        "agreeableness": 0.70,
        "neuroticism": 0.40,
        "honestyHumility": 0.85,
        "emotionality": 0.50,
    },
    "personality-interview.json": {
        "unstructuredData": "Email snippet...",
        "interview": [{"question": "How do you handle stress?", "answer": "I meditate"}],
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
    },
}


@pytest.mark.parametrize("schema_file,example", SCHEMA_EXAMPLES.items())
def test_schema_allows_valid_example(schema_file, example):
    schema_path = Path(__file__).parent.parent / "schemas" / schema_file
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    jsonschema.Draft202012Validator(schema).validate(example)


@pytest.mark.parametrize("schema_file,example", SCHEMA_EXAMPLES.items())
def test_schema_allows_null_fields(schema_file, example):
    schema_path = Path(__file__).parent.parent / "schemas" / schema_file
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    null_example = {k: None for k in example}
    jsonschema.Draft202012Validator(schema).validate(null_example)

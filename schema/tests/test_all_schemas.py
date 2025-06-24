import json
from pathlib import Path
import pytest
import jsonschema

import warnings

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="jsonschema",
    message="jsonschema.RefResolver is deprecated",
)

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
    "narrative-schema.json": {
        "eventRef": "urn:uuid:1234",
        "narrativeTheme": "http://example.org/theme/resilience",
        "significance": "high",
        "copingStyle": "problem-focused",
    },
    "goal-schema.json": {
        "description": "Finish project",
        "status": "in-progress",
        "targetDate": "2025-12-31",
    },
    "values-schema.json": {
        "valueName": "Curiosity",
        "importance": 0.9,
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
        "interview": [
            {"question": "How do you handle stress?", "answer": "I meditate"}
        ],
        "userID": "anon-sample",
        "traits": {
            "openness": 0.5,
            "conscientiousness": 0.7,
            "extraversion": 0.6,
            "agreeableness": 0.8,
            "neuroticism": 0.3,
            "honestyHumility": 0.6,
            "emotionality": 0.4,
        },
        "darkTriad": {
            "narcissism": 0.5,
            "machiavellianism": 0.4,
            "psychopathy": 0.3,
        },
        "mbti": {"mbti": "INTJ"},
        "mmpi": {
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
        "goal": {
            "description": "Finish project",
            "status": "in-progress",
            "targetDate": "2025-12-31",
        },
        "value": {
            "valueName": "Curiosity",
            "importance": 0.9,
        },
        "narrative": {
            "eventRef": "urn:uuid:1234",
            "narrativeTheme": "http://example.org/theme/resilience",
            "significance": "high",
            "copingStyle": "problem-focused",
        },
        "psychologicalSummary": "Calm and balanced individual",
        "timestamp": "2024-01-01T12:00:00Z",
    },
}


def load_schema_with_resolver(schema_path: Path):
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    resolver = jsonschema.RefResolver(
        base_uri=schema_path.resolve().as_uri(), referrer=schema
    )
    validator_class = jsonschema.validators.validator_for(schema)
    validator = validator_class(schema, resolver=resolver)
    return validator


@pytest.mark.parametrize("schema_file,example", SCHEMA_EXAMPLES.items())
def test_schema_allows_valid_example(schema_file, example):
    schema_path = Path(__file__).parent.parent / "schemas" / schema_file
    validator = load_schema_with_resolver(schema_path)
    validator.validate(example)


@pytest.mark.parametrize("schema_file,example", SCHEMA_EXAMPLES.items())
def test_schema_allows_null_fields(schema_file, example):
    if schema_file in {
        "personality-interview.json",
        "narrative-schema.json",
        "goal-schema.json",
        "values-schema.json",
    }:
        pytest.skip(f"{schema_file} doesn't allow null values in all fields")

    schema_path = Path(__file__).parent.parent / "schemas" / schema_file
    validator = load_schema_with_resolver(schema_path)
    null_example = {k: None for k in example}
    validator.validate(null_example)

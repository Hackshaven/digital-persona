import json
from pathlib import Path
import pytest
import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import SchemaRegistry


SCHEMA_EXAMPLES = {
    "dark-triad.json": { ... },
    "mbti-type.json": { ... },
    "mmpi-scales.json": { ... },
    "personality-traits.json": { ... },
    "personality-interview.json": {
        "unstructuredData": "Email snippet...",
        "interview": [{"question": "How do you handle stress?", "answer": "I meditate"}],
        "traits": { ... },
        "psychologicalSummary": "Calm and balanced individual",
        "timestamp": "2024-01-01T12:00:00Z"
    },
}

def load_schema_with_registry(schema_path: Path) -> SchemaRegistry:
    # Load main schema
    with open(schema_path, encoding="utf-8") as f:
        root_schema = json.load(f)

    # Create registry and preload sibling schemas
    registry = Registry()
    for sibling in schema_path.parent.glob("*.json"):
        with open(sibling, encoding="utf-8") as f:
            schema_data = json.load(f)
        registry = registry.with_resource(
            sibling.resolve().as_uri(),
            Resource.from_contents(schema_data)
        )

    return SchemaRegistry(registry), root_schema


@pytest.mark.parametrize("schema_file,example", SCHEMA_EXAMPLES.items())
def test_schema_allows_valid_example(schema_file, example):
    schema_path = Path(__file__).parent.parent / "schemas" / schema_file
    registry, schema = load_schema_with_registry(schema_path)
    registry.validate(instance=example, schema=schema)


@pytest.mark.parametrize("schema_file,example", SCHEMA_EXAMPLES.items())
def test_schema_allows_null_fields(schema_file, example):
    # SKIP schemas that explicitly don't allow nulls
    if schema_file in {"personality-interview.json"}:
        pytest.skip(f"{schema_file} doesn't allow null values in all fields")

    schema_path = Path(__file__).parent.parent / "schemas" / schema_file
    registry, schema = load_schema_with_registry(schema_path)
    null_example = {k: None for k in example}
    registry.validate(instance=null_example, schema=schema)

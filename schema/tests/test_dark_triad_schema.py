import json
import jsonschema
from pathlib import Path


def test_valid_dark_triad():
    schema_path = Path(__file__).parent.parent / "schemas/dark-triad.json"
    with open(schema_path) as f:
        schema = json.load(f)

    profile = {
        "narcissism": 0.5,
        "machiavellianism": 0.4,
        "psychopathy": 0.3,
    }
    jsonschema.validate(instance=profile, schema=schema)

    null_profile = {"narcissism": None, "machiavellianism": None, "psychopathy": None}
    jsonschema.validate(instance=null_profile, schema=schema)

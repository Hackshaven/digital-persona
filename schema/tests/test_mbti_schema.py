import json
import jsonschema
from pathlib import Path


def test_valid_mbti():
    schema_path = Path(__file__).parent.parent / "schemas/mbti-type.json"
    with open(schema_path) as f:
        schema = json.load(f)

    example = {"mbti": "INTJ"}
    jsonschema.validate(instance=example, schema=schema)
    null_example = {"mbti": None}
    jsonschema.validate(instance=null_example, schema=schema)

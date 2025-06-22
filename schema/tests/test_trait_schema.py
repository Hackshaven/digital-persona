import json
import jsonschema
from pathlib import Path

def test_valid_trait_profile():
    schema_path = Path(__file__).parent.parent / "schemas/personality-traits.json"
    with open(schema_path) as f:
        schema = json.load(f)

    # Valid test case
    profile = {
        "openness": 0.88,
        "conscientiousness": 0.75,
        "extraversion": 0.60,
        "agreeableness": 0.70,
        "neuroticism": 0.40,
        "honestyHumility": 0.85,
        "emotionality": 0.50
    }

    jsonschema.validate(instance=profile, schema=schema)
import json
import jsonschema
from pathlib import Path


def test_valid_mmpi_scales():
    schema_path = Path(__file__).parent.parent / "schemas/mmpi-scales.json"
    with open(schema_path) as f:
        schema = json.load(f)

    profile = {
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
    }
    jsonschema.validate(instance=profile, schema=schema)

    null_profile = {k: None for k in profile}
    jsonschema.validate(instance=null_profile, schema=schema)

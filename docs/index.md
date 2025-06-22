---
title: Digital Persona Schema
---

# Digital Persona Schema

This project standardizes how personality traits, goals, and memories can be stored in JSON. It is built on top of the ActivityStreams format so different systems can share personality data without needing deep knowledge of AI models.

## Available Files

- [context/personality-context.jsonld](schema/context/personality-context.jsonld) – JSON-LD mappings that give short trait names clear identifiers.
- [schemas/personality-traits.json](schema/schemas/personality-traits.json) – A JSON Schema that checks trait scores are valid numbers between 0 and 1.
- [ontologies/trait-vocabulary.md](schema/ontologies/trait-vocabulary.md) – A plain-language glossary describing what each trait represents.

## Reference Documents

- [Representing Personal Data and Personality Traits: Existing JSON/Semantic Standards](Representing%20Personal%20Data%20and%20Personality%20Traits%20-%20Existing%20JSON-Semantic%20Standards.md)
- [Scientifically Grounded Personality Tests and Their Evolution into Digital Personas](Scientifically%20Grounded%20Personality%20Tests%20and%20Their%20Evolution%20into%20Digital%20Personas.md)

These files can be fetched directly via [GitHub Pages](https://hackshaven.github.io/digital-persona/). Ensure the repository's Pages settings use **GitHub Actions** as the build and deploy source so these schema files are included.

---
title: Digital Persona Schema
---

# Digital Persona Schema

This project standardizes how personality traits, goals, and memories can be stored in JSON. It is built on top of the ActivityStreams format so different systems can share personality data without needing deep knowledge of AI models.

## Available Files

- [context/personality-context.jsonld](schema/context/personality-context.jsonld) – JSON-LD mappings that give short trait names clear identifiers.
- [schemas/personality-traits.json](schema/schemas/personality-traits.json) – A JSON Schema that checks trait scores are valid numbers between 0 and 1.
- [schemas/personality-interview.json](schema/schemas/personality-interview.json) – JSON Schema describing complete interview results.
- [schemas/mbti-type.json](schema/schemas/mbti-type.json) – Schema for MBTI four-letter types.
- [schemas/dark-triad.json](schema/schemas/dark-triad.json) – Schema for Dark Triad trait scores.
- [schemas/mmpi-scales.json](schema/schemas/mmpi-scales.json) – Schema for MMPI-2 clinical scale scores.
- [schemas/narrative-schema.json](schema/schemas/narrative-schema.json) – Schema describing memory or event metadata.
- [schemas/goal-schema.json](schema/schemas/goal-schema.json) – Schema for personal goals.
- [schemas/values-schema.json](schema/schemas/values-schema.json) – Schema describing core values and their importance.
- [ontologies/trait-vocabulary.md](schema/ontologies/trait-vocabulary.md) – A plain-language glossary describing what each trait represents.

## Reference Documents

- [research/Representing Personal Data and Personality Traits - Existing JSON-Semantic Standards](research/Representing%20Personal%20Data%20and%20Personality%20Traits%20-%20Existing%20JSON-Semantic%20Standards.md)
- [research/Scientifically Grounded Personality Tests and Their Evolution into Digital Personas](research/Scientifically%20Grounded%20Personality%20Tests%20and%20Their%20Evolution%20into%20Digital%20Personas.md)
- [Designing User Interfaces for Digital Clones](Designing%20User%20Interfaces%20for%20Digital%20Clones.md)

These files can be fetched directly via [GitHub Pages](https://hackshaven.github.io/digital-persona/). Ensure the repository's Pages settings use **GitHub Actions** as the build and deploy source so these schema files are included.

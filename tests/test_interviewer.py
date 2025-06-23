import json
import sys
import types
from pathlib import Path

import pytest

# -------------------------------------------------------------------------
# Stubs for LangChain modules (no dependency on actual installation)
# -------------------------------------------------------------------------
if "langchain" not in sys.modules:

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    # Shared fake message namespace
    schema_mod = types.SimpleNamespace(
        HumanMessage=FakeMessage, SystemMessage=FakeMessage
    )

    # Stub langchain_core.messages
    sys.modules["langchain_core"] = types.SimpleNamespace(messages=schema_mod)
    sys.modules["langchain_core.messages"] = schema_mod

    # Stub langchain_community.chat_models and langchain
    chat_models = types.SimpleNamespace(ChatOpenAI=object)
    sys.modules["langchain"] = types.SimpleNamespace(
        chat_models=chat_models, schema=schema_mod
    )
    sys.modules["langchain.chat_models"] = chat_models
    sys.modules["langchain.schema"] = schema_mod
    sys.modules["langchain_community.chat_models"] = chat_models

    # Stub langchain_ollama
    sys.modules["langchain_ollama"] = types.SimpleNamespace(ChatOllama=object)

# -------------------------------------------------------------------------
# Project import (source assumed in ../src)
# -------------------------------------------------------------------------
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from digital_persona.interview import PersonalityInterviewer


# -------------------------------------------------------------------------
# Stub LLMs
# -------------------------------------------------------------------------
class StubLLM:
    def __init__(self, responses):
        self.responses = list(responses)

    def __call__(self, messages):
        return type("Resp", (), {"content": self.responses.pop(0)})()

    invoke = __call__  # Allow .invoke(...) as well


# -------------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------------
def test_generate_questions_parses_lines():
    llm = StubLLM(["Q1?\nQ2?\nQ3?"])
    interviewer = PersonalityInterviewer(llm=llm, num_questions=3)
    qs = interviewer.generate_questions("notes")
    assert qs == ["Q1?", "Q2?", "Q3?"]


def test_default_question_count_half_traits():
    interviewer = PersonalityInterviewer(llm=StubLLM([]))
    expected = max(3, (len(interviewer.trait_names) + 1) // 2)
    assert interviewer.num_questions == expected


def test_generate_followup_handles_no_followup():
    llm = StubLLM(["NO FOLLOWUP"])
    interviewer = PersonalityInterviewer(llm=llm)
    assert interviewer.generate_followup("Q?", "A") is None


def test_generate_followup_returns_question():
    llm = StubLLM(["Could you clarify?"])
    interviewer = PersonalityInterviewer(llm=llm)
    assert interviewer.generate_followup("Q?", "A") == "Could you clarify?"


def test_profile_from_answers_builds_result():
    response_json = json.dumps(
        {
            "traits": {
                "openness": 0.5,
                "conscientiousness": 0.5,
                "extraversion": 0.5,
                "agreeableness": 0.5,
                "neuroticism": 0.5,
                "honestyHumility": 0.5,
            },
            "darkTriad": {
                "narcissism": 0.1,
                "machiavellianism": 0.2,
                "psychopathy": 0.3,
            },
            "mbti": {"mbti": "INTJ"},
            "mmpi": {"hypochondriasis": 0.2},
            "goal": {"description": "Finish"},
            "value": {"valueName": "Curiosity"},
            "narrative": {"eventRef": "urn:uuid:1"},
            "psychologicalSummary": "Summary text",
        }
    )
    llm = StubLLM([response_json])
    interviewer = PersonalityInterviewer(llm=llm)
    data = "example notes"
    qa_pairs = ["Q: How?\nA: Well"]
    profile = interviewer.profile_from_answers(data, qa_pairs)
    assert profile["unstructuredData"] == data
    assert profile["interview"] == [{"question": "How?", "answer": "Well"}]
    assert profile["traits"]["openness"] == 0.5
    assert profile["psychologicalSummary"] == "Summary text"
    assert profile["traits"]["emotionality"] is None
    assert profile["darkTriad"]["machiavellianism"] == 0.2
    assert profile["mbti"]["mbti"] == "INTJ"
    assert profile["mmpi"]["hypochondriasis"] == 0.2
    assert profile["goal"]["status"] is None
    assert "timestamp" in profile


def test_qa_list_handles_multiline_answers():
    interviewer = PersonalityInterviewer(llm=StubLLM([]))
    qa_pairs = ["Q: Why?\nA: Line one\nLine two"]
    result = interviewer._qa_list(qa_pairs)
    assert result == [{"question": "Why?", "answer": "Line one Line two"}]


def test_profile_summary_references_context():
    class CheckingLLM:
        def __call__(self, messages):
            assert "likes apples" in messages[1].content
            result = {
                "traits": {
                    "openness": 0.1,
                    "conscientiousness": 0.2,
                    "extraversion": 0.3,
                    "agreeableness": 0.4,
                    "neuroticism": 0.5,
                    "honestyHumility": 0.6,
                    "emotionality": 0.7,
                },
                "psychologicalSummary": "Context shows user likes apples",
            }
            return type("Resp", (), {"content": json.dumps(result)})()

        invoke = __call__

    interviewer = PersonalityInterviewer(llm=CheckingLLM())
    data = "The user likes apples"
    profile = interviewer.profile_from_answers(data, ["Q: Hi?\nA: Hello"])
    assert "likes apples" in profile["psychologicalSummary"]


def test_profile_from_answers_invalid_json_error():
    llm = StubLLM(["not valid json"])
    interviewer = PersonalityInterviewer(llm=llm)
    with pytest.raises(ValueError) as exc:
        interviewer.profile_from_answers("ctx", ["Q: ?\nA: ."])
    assert "not valid json" in str(exc.value)

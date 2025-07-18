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

    # Stub langchain_openai.ChatOpenAI and the base langchain module
    chat_models = types.SimpleNamespace(ChatOpenAI=object)
    sys.modules["langchain"] = types.SimpleNamespace(
        chat_models=chat_models, schema=schema_mod
    )
    sys.modules["langchain.chat_models"] = chat_models
    sys.modules["langchain.schema"] = schema_mod
    sys.modules["langchain_openai"] = types.SimpleNamespace(ChatOpenAI=object)

    # Stub langchain_ollama
    sys.modules["langchain_ollama"] = types.SimpleNamespace(ChatOllama=object)

# -------------------------------------------------------------------------
# Project import (source assumed in ../src)
# -------------------------------------------------------------------------
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from digital_persona.interview import MAX_FOLLOWUPS, PersonalityInterviewer


# -------------------------------------------------------------------------
# Stub LLMs
# -------------------------------------------------------------------------
class StubLLM:
    def __init__(self, responses):
        self.responses = list(responses)

    def __call__(self, messages):
        return type("Resp", (), {"content": self.responses.pop(0)})()

    invoke = __call__  # Allow .invoke(...) as well


class RecordingLLM(StubLLM):
    def __init__(self, responses):
        super().__init__(responses)
        self.call_count = 0
        self.last = None

    def __call__(self, messages):
        self.call_count += 1
        self.last = messages
        return super().__call__(messages)

    invoke = __call__


# -------------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------------
def test_generate_questions_parses_lines():
    llm = StubLLM(["Q1?\nQ2?\nQ3?"])
    interviewer = PersonalityInterviewer(llm=llm, num_questions=3)
    qs = interviewer.generate_questions("notes")
    assert qs == ["Q1?", "Q2?", "Q3?"]


def test_generate_questions_chunks_long_notes():
    tmp = PersonalityInterviewer(llm=StubLLM([]))
    long_notes = "x" * (tmp.MAX_NOTES_CHARS + 10)
    responses = ["sum1", "sum2", "Q?"]
    llm = RecordingLLM(responses)
    interviewer = PersonalityInterviewer(llm=llm, num_questions=1)
    qs = interviewer.generate_questions(long_notes)
    assert qs == ["Q?"]
    assert llm.call_count > 1


def test_default_question_count_half_traits():
    interviewer = PersonalityInterviewer(llm=StubLLM([]))
    expected = max(3, (len(interviewer.trait_names) + 1) // 2)
    assert interviewer.num_questions == expected


def test_max_followups_constant():
    assert MAX_FOLLOWUPS == 2


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
            "userID": "anon01",
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
    assert profile["userID"] == "anon01"
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
    assert "Expected JSON object" in str(exc.value)


def test_run_allows_early_finish(monkeypatch):
    responses = [
        "Summary",  # summarize_data
        "Q1?\nQ2?",  # generate_questions
        "Expl",  # explain_question for Q1
        json.dumps(
            {
                "traits": {
                    "openness": 0.1,
                    "conscientiousness": 0.2,
                    "extraversion": 0.3,
                    "agreeableness": 0.4,
                    "neuroticism": 0.5,
                    "honestyHumility": 0.6,
                },
                "userID": "anon02",
                "psychologicalSummary": "Done",
            }
        ),
    ]
    llm = StubLLM(responses)
    interviewer = PersonalityInterviewer(llm=llm, num_questions=2)

    inputs = iter(["/end"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    profile = interviewer.run("notes")
    assert profile["interview"] == []
    assert profile["traits"]["openness"] == 0.1
    assert profile["userID"] == "anon02"


def test_run_simulated_generates_profile(capsys):
    responses = [
        "Summary",  # summarize_data
        "Q1?",  # generate_questions
        "Expl",  # explain_question
        "Auto",  # simulate_answer
        "NO FOLLOWUP",  # generate_followup
        json.dumps(
            {
                "traits": {
                    "openness": 0.1,
                    "conscientiousness": 0.2,
                    "extraversion": 0.3,
                    "agreeableness": 0.4,
                    "neuroticism": 0.5,
                    "honestyHumility": 0.6,
                },
                "userID": "anon03",
                "psychologicalSummary": "Done",
            }
        ),
    ]
    llm = StubLLM(responses)
    interviewer = PersonalityInterviewer(llm=llm, num_questions=1)
    profile = interviewer.run_simulated("notes")
    out = capsys.readouterr().out
    assert "Auto" in out
    assert profile["traits"]["openness"] == 0.1
    assert profile["userID"] == "anon03"


def test_profile_handles_string_sections():
    response_json = json.dumps(
        {
            "traits": {
                "openness": 0.1,
                "conscientiousness": 0.2,
                "extraversion": 0.3,
                "agreeableness": 0.4,
                "neuroticism": 0.5,
                "honestyHumility": 0.6,
                "emotionality": 0.7,
            },
            "goal": "not an object",
            "value": "also bad",
            "narrative": "string",
            "psychologicalSummary": "summary",
        }
    )
    llm = StubLLM([response_json])
    interviewer = PersonalityInterviewer(llm=llm)
    profile = interviewer.profile_from_answers("notes", ["Q: ?\nA: !"])
    assert profile["goal"] == {k: None for k in interviewer.goal_fields}
    assert profile["value"] == {k: None for k in interviewer.value_fields}
    assert profile["narrative"] == {k: None for k in interviewer.narrative_fields}
    assert profile["userID"].startswith("user-")


def test_create_llm_selects_provider(monkeypatch):
    """_create_llm should instantiate the class for the requested provider."""

    class FakeOpenAI:
        def __init__(self, model, temperature):
            self.model = model
            self.temperature = temperature

    class FakeOllama:
        def __init__(self, base_url, model):
            self.base_url = base_url
            self.model = model

    monkeypatch.setattr("digital_persona.interview.ChatOpenAI", FakeOpenAI)
    monkeypatch.setattr("digital_persona.interview.ChatOllama", FakeOllama)

    interviewer = PersonalityInterviewer(llm=None, provider="openai", model="oa")
    assert isinstance(interviewer.llm, FakeOpenAI)
    assert interviewer.llm.model == "oa"

    interviewer = PersonalityInterviewer(llm=None, provider="ollama", model="ol")
    assert isinstance(interviewer.llm, FakeOllama)
    assert interviewer.llm.model == "ol"


def test_conduct_interview_avoids_repeat(monkeypatch):
    """Repeated follow-up questions should be suppressed."""

    interviewer = PersonalityInterviewer(llm=StubLLM([]), num_questions=1)

    monkeypatch.setattr(interviewer, "explain_question", lambda q, d: "ex")
    monkeypatch.setattr(interviewer, "explain_followup", lambda f, q, d: "ex f")
    monkeypatch.setattr(interviewer, "generate_followup", lambda q, a: "Again?")

    qs = ["Q?"]
    qa = interviewer._conduct_interview("notes", qs, lambda q: "A", False)

    # Only one follow-up recorded despite generate_followup always returning text
    assert qa == ["Q: Q?\nA: A", "Q: Again?\nA: A"]


def test_load_schema_fields_reads_file():
    interviewer = PersonalityInterviewer(llm=StubLLM([]))
    fields = interviewer._load_schema_fields("personality-traits.json")
    assert "openness" in fields
    assert "neuroticism" in fields

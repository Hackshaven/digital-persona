import json
import sys
from pathlib import Path
import types

# Provide lightweight stubs so tests don't require the real LangChain package
if 'langchain' not in sys.modules:
    class FakeMessage:
        def __init__(self, content):
            self.content = content

    chat_models = types.SimpleNamespace(ChatOpenAI=object, ChatOllama=object)
    schema_mod = types.SimpleNamespace(HumanMessage=FakeMessage, SystemMessage=FakeMessage)
    langchain_mod = types.SimpleNamespace(chat_models=chat_models, schema=schema_mod)
    sys.modules['langchain'] = langchain_mod
    sys.modules['langchain.chat_models'] = chat_models
    sys.modules['langchain.schema'] = schema_mod
    sys.modules['langchain_community.chat_models'] = chat_models

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from digital_persona.interview import PersonalityInterviewer

class StubLLM:
    def __init__(self, responses):
        self.responses = list(responses)

    def __call__(self, messages):
        return type("Resp", (), {"content": self.responses.pop(0)})()


def test_generate_questions_parses_lines():
    llm = StubLLM(["Q1\nQ2\nQ3"])
    interviewer = PersonalityInterviewer(llm=llm, num_questions=3)
    qs = interviewer.generate_questions("notes")
    assert qs == ["Q1", "Q2", "Q3"]


def test_generate_followup_handles_no_followup():
    llm = StubLLM(["NO FOLLOWUP"])
    interviewer = PersonalityInterviewer(llm=llm)
    assert interviewer.generate_followup("Q?", "A") is None


def test_generate_followup_returns_question():
    llm = StubLLM(["Could you clarify?"])
    interviewer = PersonalityInterviewer(llm=llm)
    assert interviewer.generate_followup("Q?", "A") == "Could you clarify?"


def test_profile_from_answers_builds_result():
    response_json = json.dumps({
        "traits": {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
            "honestyHumility": 0.5
        },
        "psychologicalSummary": "Summary text"
    })
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
    assert "timestamp" in profile


def test_profile_summary_references_context():
    """The psychological summary should include the user's context."""

    class CheckingLLM:
        def __call__(self, messages):
            # ensure the prompt contains the unstructured data
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

    interviewer = PersonalityInterviewer(llm=CheckingLLM())
    data = "The user likes apples"
    profile = interviewer.profile_from_answers(data, ["Q: Hi?\nA: Hello"])
    assert "likes apples" in profile["psychologicalSummary"]

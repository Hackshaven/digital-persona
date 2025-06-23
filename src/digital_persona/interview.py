# Interview assistant for generating personality trait profiles from unstructured data.

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain_community.chat_models import ChatOllama


class PersonalityInterviewer:
    """Chat-based interviewer that asks questions and clarification follow-ups."""

    def __init__(
        self,
        llm: object | None = None,
        num_questions: int | None = None,
        provider: str = "openai",
        model: str | None = None,
    ) -> None:
        self.llm = llm or self._create_llm(provider, model)
        self.research_text = self._load_research_docs()
        self.trait_names = self._load_trait_names()
        self.num_questions = num_questions or max(5, len(self.trait_names))

    def _create_llm(self, provider: str, model: str | None) -> object:
        if provider.lower() == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model_name = model or os.getenv("OLLAMA_MODEL", "llama3")
            return ChatOllama(base_url=base_url, model=model_name)
        else:
            model_name = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            return ChatOpenAI(model=model_name, temperature=0)

    def _load_research_docs(self) -> str:
        docs_dir = Path(__file__).resolve().parents[2] / "docs"
        texts = []
        for p in docs_dir.glob("*.md"):
            if p.name != "index.md":
                texts.append(p.read_text())
        return "\n\n".join(texts)

    def _load_trait_names(self) -> List[str]:
        schema_path = Path(__file__).resolve().parents[2] / "schema" / "schemas" / "personality-traits.json"
        with open(schema_path) as f:
            schema = json.load(f)
        return list(schema["properties"].keys())

    def generate_questions(self, unstructured_data: str) -> List[str]:
        """Generate interview questions to clarify the user's personality."""
        prompt = (
            "You are an expert psychologist using personality research to profile a user. "
            "Based on the following unstructured data:\n{data}\n\n"
            "Using insights from personality research:\n{research}\n\n"
            "Ask {n} interview questions that will help assess these traits: {traits}."
        )
        filled = prompt.format(
            data=unstructured_data,
            research=self.research_text[:2000],
            n=self.num_questions,
            traits=", ".join(self.trait_names),
        )
        msg = [SystemMessage(content="You generate concise interview questions."), HumanMessage(content=filled)]
        response = self.llm(msg).content
        return [q.strip() for q in response.split("\n") if q.strip()]

    def generate_followup(self, question: str, answer: str) -> str | None:
        """Ask the LLM for a clarification follow-up question if needed."""
        prompt = (
            "You are conducting a personality interview. "
            "Given the question and answer, determine if the answer is vague. "
            "If so, provide one short follow-up question. Otherwise respond with 'NO FOLLOWUP'.\n\n"
            "Question: {q}\nAnswer: {a}"
        )
        filled = prompt.format(q=question, a=answer)
        msg = [
            SystemMessage(content="Reply with either a follow-up question or NO FOLLOWUP."),
            HumanMessage(content=filled),
        ]
        response = self.llm(msg).content.strip()
        if response.upper().startswith("NO FOLLOWUP"):
            return None
        return response

    def _qa_list(self, qa_pairs: List[str]) -> List[dict]:
        """Convert Q&A strings into structured dicts."""
        result = []
        for pair in qa_pairs:
            lines = pair.splitlines()
            if len(lines) >= 2:
                q = lines[0].removeprefix("Q: ").strip()
                a = lines[1].removeprefix("A: ").strip()
                result.append({"question": q, "answer": a})
        return result

    def profile_from_answers(self, unstructured_data: str, qa_pairs: List[str]) -> dict:
        """Generate a personality trait profile in JSON."""
        prompt = (
            "You are a psychologist creating a personality profile. "
            "Given the unstructured data and interview Q&A below, output a JSON object "
            "with a 'psychologicalSummary' string that briefly references the user's context "
            "from the unstructured data, and a 'traits' object containing scores between 0.0 "
            "and 1.0 for the traits {traits}. Only output JSON.\n\n"
            "Unstructured data:\n{data}\n\nQ&A:\n{qa}"
        )
        filled = prompt.format(
            traits=", ".join(self.trait_names),
            data=unstructured_data,
            qa="\n".join(qa_pairs),
        )
        msg = [SystemMessage(content="You output JSON only."), HumanMessage(content=filled)]
        response = self.llm(msg).content
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            raise ValueError("LLM did not return valid JSON")

        traits = {name: None for name in self.trait_names}
        for name, value in result.get("traits", {}).items():
            traits[name] = value

        return {
            "unstructuredData": unstructured_data,
            "interview": self._qa_list(qa_pairs),
            "traits": traits,
            "psychologicalSummary": result.get("psychologicalSummary", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def run(self, unstructured_data: str) -> dict:
        """Interactively interview the user and return a trait profile."""
        questions = self.generate_questions(unstructured_data)
        qa_pairs = []
        for q in questions:
            answer = input(f"{q}\n> ")
            qa_pairs.append(f"Q: {q}\nA: {answer}")
            follow = self.generate_followup(q, answer)
            while follow:
                follow_answer = input(f"{follow}\n> ")
                qa_pairs.append(f"Q: {follow}\nA: {follow_answer}")
                answer += " " + follow_answer
                follow = self.generate_followup(q, answer)
        return self.profile_from_answers(unstructured_data, qa_pairs)


__all__ = ["PersonalityInterviewer"]


def _cli() -> None:
    """Run the interviewer from the command line."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Interview a user based on unstructured text and output a personality profile"
    )
    parser.add_argument(
        "file",
        help="Path to a text file with unstructured data or '-' to read from stdin",
    )
    parser.add_argument(
        "-n",
        "--questions",
        type=int,
        help="Number of interview questions to ask (default: based on trait count)",
    )
    parser.add_argument(
        "-p",
        "--provider",
        choices=["openai", "ollama"],
        default="openai",
        help="LLM provider to use (default: openai)",
    )
    parser.add_argument(
        "-m",
        "--model",
        help="Model name for the chosen provider",
    )
    args = parser.parse_args()

    if args.file == "-":
        data = sys.stdin.read()
    else:
        with open(args.file) as f:
            data = f.read()

    interviewer = PersonalityInterviewer(
        num_questions=args.questions,
        provider=args.provider,
        model=args.model,
    )
    profile = interviewer.run(data)
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    _cli()

# Interview assistant for generating personality trait profiles from unstructured data.

from __future__ import annotations

import json
import os
import difflib

from datetime import datetime, timezone
import uuid
from pathlib import Path
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain_community.chat_models import ChatOpenAI


class EarlyFinish(Exception):
    """Raised when the user chooses to end the interview early."""


END_COMMAND = "/end"


class PersonalityInterviewer:
    """Chat-based interviewer that asks questions and clarification follow-ups."""

    def __init__(
        self,
        llm: object | None = None,
        num_questions: int | None = None,
        provider: str = "openai",
        model: str | None = None,
        max_question_len: int = 300,
    ) -> None:
        self.llm = llm or self._create_llm(provider, model)
        self.research_text = self._load_research_docs()
        self.trait_names = self._load_schema_fields("personality-traits.json")
        self.dark_triad_fields = self._load_schema_fields("dark-triad.json")
        self.mbti_fields = self._load_schema_fields("mbti-type.json")
        self.mmpi_fields = self._load_schema_fields("mmpi-scales.json")
        self.goal_fields = self._load_schema_fields("goal-schema.json")
        self.value_fields = self._load_schema_fields("values-schema.json")
        self.narrative_fields = self._load_schema_fields("narrative-schema.json")
        default_qs = (len(self.trait_names) + 1) // 2
        self.num_questions = num_questions or max(3, default_qs)
        self.MAX_QUESTION_LEN = max_question_len

    def _create_llm(self, provider: str, model: str | None) -> object:
        if provider.lower() == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model_name = model or os.getenv("OLLAMA_MODEL", "gemma3:12b")
            return ChatOllama(base_url=base_url, model=model_name)
        else:
            model_name = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            return ChatOpenAI(model=model_name, temperature=0)

    def _load_research_docs(self) -> str:
        docs_dir = Path(__file__).resolve().parents[2] / "docs"
        texts = []
        for p in docs_dir.glob("*.md"):
            if p.name != "index.md":
                try:
                    texts.append(p.read_text(encoding="utf-8"))
                except UnicodeDecodeError:
                    texts.append(p.read_text(encoding="utf-8", errors="replace"))
        return "\n\n".join(texts)

    def _load_schema_fields(self, filename: str) -> List[str]:
        schema_path = (
            Path(__file__).resolve().parents[2] / "schema" / "schemas" / filename
        )
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        return list(schema["properties"].keys())

    def summarize_data(self, unstructured_data: str) -> str:
        """Return a short summary of the user's notes."""
        prompt = (
            "Briefly summarize the following notes in two sentences:\n"
            + unstructured_data
        )
        msg = [
            SystemMessage(content="You provide a short friendly summary."),
            HumanMessage(content=prompt),
        ]
        return self.llm.invoke(msg).content.strip()

    def explain_question(self, question: str, unstructured_data: str) -> str:
        """Explain how the question relates to the user's notes."""
        prompt = (
            "Explain in one personable sentence why the question below relates to these notes."
            "\nNotes:\n{data}\nQuestion: {q}"
        ).format(data=unstructured_data, q=question)
        msg = [
            SystemMessage(content="Friendly explanation."),
            HumanMessage(content=prompt),
        ]
        return self.llm.invoke(msg).content.strip()

    def explain_followup(
        self, followup: str, original_question: str, unstructured_data: str
    ) -> str:
        """Explain why a follow-up question is being asked."""
        prompt = (
            "Explain in one short sentence how this follow-up builds on the original question and the user's notes."
            "\nNotes:\n{data}\nOriginal question: {orig}\nFollow-up: {fup}"
        ).format(data=unstructured_data, orig=original_question, fup=followup)
        msg = [
            SystemMessage(content="Friendly explanation."),
            HumanMessage(content=prompt),
        ]
        return self.llm.invoke(msg).content.strip()

    def generate_questions(self, unstructured_data: str) -> List[str]:
        """Generate interview questions to clarify the user's personality."""
        prompt = (
            "You are an expert psychologist using personality research to profile a user. "
            "Based on the following unstructured data:\n{data}\n\n"
            "Using insights from personality research:\n{research}\n\n"
            "Ask {n} concise interview questions that help assess these traits: {traits}.\n"
            "Combine related traits so each question may address more than one trait when possible.\n"
            "Return only the questions, one per line, without numbering or explanations."
        )
        filled = prompt.format(
            data=unstructured_data,
            research=self.research_text[:2000],
            n=self.num_questions,
            traits=", ".join(self.trait_names),
        )
        msg = [
            SystemMessage(content="You generate only the list of questions."),
            HumanMessage(content=filled),
        ]
        response = self.llm.invoke(msg).content
        return [
            q.strip("-•*1234567890. ").strip()
            for q in response.splitlines()
            if "?" in q and len(q.strip()) < self.MAX_QUESTION_LEN
        ]

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
            SystemMessage(
                content="Reply with either a follow-up question or NO FOLLOWUP."
            ),
            HumanMessage(content=filled),
        ]
        response = self.llm.invoke(msg).content.strip()
        return None if response.upper().startswith("NO FOLLOWUP") else response

    def simulate_answer(self, question: str, unstructured_data: str) -> str:
        """Have the language model play the user and answer a question."""
        prompt = (
            "Answer the interview question in one or two sentences using the notes if relevant.\n"
            "Notes:\n{data}\nQuestion: {q}"
        ).format(data=unstructured_data, q=question)
        msg = [SystemMessage(content="Short answer."), HumanMessage(content=prompt)]
        return self.llm.invoke(msg).content.strip()

    def run_simulated(self, unstructured_data: str) -> dict:
        """Run the interview automatically with LLM-generated answers."""
        summary = self.summarize_data(unstructured_data)
        print("\n📝 Here's a quick summary of what you shared:\n" + summary)

        questions = self.generate_questions(unstructured_data)
        print(f"\n📋 I'll ask {len(questions)} questions:")
        for i, q in enumerate(questions, 1):
            print(f"{i}. {q}")
        qa_pairs = []

        total = len(questions)
        for idx, q in enumerate(questions, 1):
            explanation = self.explain_question(q, unstructured_data)
            print(f"\n[{idx}/{total}] 💡 {explanation}")
            answer = self.simulate_answer(q, unstructured_data)
            print(f"Q: {q}\nA: {answer}")
            qa_pairs.append(f"Q: {q}\nA: {answer}")

            follow_ups = 0
            prev_follow = None
            follow = self.generate_followup(q, answer)

            while follow and follow_ups < 2:
                if prev_follow:
                    similarity = difflib.SequenceMatcher(None, follow, prev_follow).ratio()
                    if similarity > 0.9:
                        break
                expl = self.explain_followup(follow, q, unstructured_data)
                print(f"   ↳ {expl}")
                follow_answer = self.simulate_answer(follow, unstructured_data)
                print(f"Q: {follow}\nA: {follow_answer}")
                qa_pairs.append(f"Q: {follow}\nA: {follow_answer}")
                answer += "\n" + follow_answer
                prev_follow = follow
                follow_ups += 1
                follow = self.generate_followup(q, answer)

        profile = self.profile_from_answers(unstructured_data, qa_pairs)
        print(json.dumps(profile, indent=2))
        return profile

    def _qa_list(self, qa_pairs: List[str]) -> List[dict]:
        result = []
        for pair in qa_pairs:
            lines = pair.splitlines()
            if len(lines) >= 2:
                q = lines[0].removeprefix("Q: ").strip()
                a_lines = [lines[1].removeprefix("A: ").strip()] + [
                    l.strip() for l in lines[2:]
                ]
                a = " ".join(a_lines)
                result.append({"question": q, "answer": a})
        return result

    def profile_from_answers(self, unstructured_data: str, qa_pairs: List[str]) -> dict:
        prompt = (
            "You are a psychologist creating a personality profile. "
            "Given the unstructured data and interview Q&A below, output a JSON object "
            "with a 'psychologicalSummary' that lists each assigned attribute, its value, "
            "and a short explanation for why it was inferred. Include objects for 'traits', "
            "'darkTriad', 'mbti', 'mmpi', 'goal', 'value', and 'narrative'. Scores should be between 0.0 and 1.0 where applicable. "
            "Return null for any attribute you cannot infer. Only output valid JSON.\n\n"
            "Unstructured data:\n{data}\n\nQ&A:\n{qa}"
        )
        filled = prompt.format(
            traits=", ".join(self.trait_names),
            data=unstructured_data,
            qa="\n".join(qa_pairs),
        )
        msg = [SystemMessage(content="Output JSON only."), HumanMessage(content=filled)]
        response = self.llm.invoke(msg).content
        try:
            clean = response.strip()
            if clean.startswith("```json"):
                clean = clean.removeprefix("```json").strip()
            if clean.startswith("```"):
                clean = clean.removeprefix("```").strip()
            if clean.endswith("```"):
                clean = clean.removesuffix("```").strip()

            result = json.loads(clean)

        except json.JSONDecodeError:
            raise ValueError(f"LLM did not return valid JSON: {response!r}")

        traits = {name: None for name in self.trait_names}
        for name, value in result.get("traits", {}).items():
            if name in traits:
                traits[name] = value

        dark_triad = {k: None for k in self.dark_triad_fields}
        dark_data = result.get("darkTriad")
        if isinstance(dark_data, dict):
            for name, value in dark_data.items():
                if name in dark_triad:
                    dark_triad[name] = value

        mbti = {k: None for k in self.mbti_fields}
        mbti_data = result.get("mbti")
        if isinstance(mbti_data, dict):
            for name, value in mbti_data.items():
                if name in mbti:
                    mbti[name] = value

        mmpi = {k: None for k in self.mmpi_fields}
        mmpi_data = result.get("mmpi")
        if isinstance(mmpi_data, dict):
            for name, value in mmpi_data.items():
                if name in mmpi:
                    mmpi[name] = value

        goal = {k: None for k in self.goal_fields}
        goal_data = result.get("goal")
        if isinstance(goal_data, dict):
            for name, value in goal_data.items():
                if name in goal:
                    goal[name] = value

        value_obj = {k: None for k in self.value_fields}
        val_data = result.get("value")
        if isinstance(val_data, dict):
            for name, val in val_data.items():
                if name in value_obj:
                    value_obj[name] = val

        narrative = {k: None for k in self.narrative_fields}
        narr_data = result.get("narrative")
        if isinstance(narr_data, dict):
            for name, val in narr_data.items():
                if name in narrative:
                    narrative[name] = val

        user_id = result.get("userID")
        if not isinstance(user_id, str) or not user_id.strip():
            user_id = f"user-{uuid.uuid4().hex[:8]}"

        return {
            "unstructuredData": unstructured_data,
            "interview": self._qa_list(qa_pairs),
            "userID": user_id,
            "traits": traits,
            "darkTriad": dark_triad,
            "mbti": mbti,
            "mmpi": mmpi,
            "goal": goal,
            "value": value_obj,
            "narrative": narrative,
            "psychologicalSummary": result.get("psychologicalSummary", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _collect_multiline_answer(self, prompt: str) -> str:
        print(f"\n{prompt}")
        lines = []
        while True:
            line = input("> ")
            if line.strip() == END_COMMAND:
                raise EarlyFinish
            if not line.strip():
                break
            lines.append(line)
        return "\n".join(lines)

    def run(self, unstructured_data: str) -> dict:
        """Interactively interview the user and return a trait profile."""
        summary = self.summarize_data(unstructured_data)
        print("\n📝 Here's a quick summary of what you shared:\n" + summary)
        print(f"Type '{END_COMMAND}' on a line by itself at any time to finish early.")

        questions = self.generate_questions(unstructured_data)
        print(f"\n📋 I'll ask {len(questions)} questions:")
        for i, q in enumerate(questions, 1):
            print(f"{i}. {q}")
        print("\nPress Enter twice to finish each answer.\n")
        qa_pairs = []

        total = len(questions)
        for idx, q in enumerate(questions, 1):
            try:
                explanation = self.explain_question(q, unstructured_data)
                print(f"\n[{idx}/{total}] 💡 {explanation}")
                answer = self._collect_multiline_answer(q)
            except EarlyFinish:
                print("\nInterview finished early. Generating profile...\n")
                break
            qa_pairs.append(f"Q: {q}\nA: {answer}")

            follow_ups = 0
            prev_follow = None
            follow = self.generate_followup(q, answer)

            while follow and follow_ups < 2:
                # Fuzzy suppression: check if this follow-up is too similar to the previous
                if prev_follow:
                    similarity = difflib.SequenceMatcher(
                        None, follow, prev_follow
                    ).ratio()
                    if similarity > 0.9:
                        break  # Too similar to the last one
                try:
                    expl = self.explain_followup(follow, q, unstructured_data)
                    print(f"   ↳ {expl}")
                    follow_answer = self._collect_multiline_answer(follow)
                except EarlyFinish:
                    print("\nInterview finished early. Generating profile...\n")
                    return self.profile_from_answers(unstructured_data, qa_pairs)
                qa_pairs.append(f"Q: {follow}\nA: {follow_answer}")
                answer += "\n" + follow_answer
                prev_follow = follow
                follow_ups += 1
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
    parser.add_argument("file", help="Path to a text file or '-' to read from stdin")
    parser.add_argument(
        "-n", "--questions", type=int, help="Number of questions to ask"
    )
    parser.add_argument(
        "-p", "--provider", choices=["openai", "ollama"], default="openai"
    )
    parser.add_argument("-m", "--model", help="Model name for the chosen provider")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the interview with LLM-generated answers",
    )
    args = parser.parse_args()

    data = (
        sys.stdin.read()
        if args.file == "-"
        else Path(args.file).read_text(encoding="utf-8")
    )

    interviewer = PersonalityInterviewer(
        num_questions=args.questions,
        provider=args.provider,
        model=args.model,
    )

    if args.dry_run:
        interviewer.run_simulated(data)
        sys.exit(0)

    profile = interviewer.run(data)
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    _cli()

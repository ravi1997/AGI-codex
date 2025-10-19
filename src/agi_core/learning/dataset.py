"""Dataset loading and formatting utilities for fine-tuning."""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


@dataclass(frozen=True)
class LoRAExample:
    """Single instruction-following example for LoRA style fine-tuning."""

    instruction: str
    input: str
    output: str


@dataclass(frozen=True)
class DPOExample:
    """Pair of responses suitable for Direct Preference Optimisation."""

    prompt: str
    chosen: str
    rejected: str


def load_jsonl_records(path: Path) -> List[Dict[str, Any]]:
    """Read a JSON Lines dataset from disk."""

    if not path.exists():
        return []

    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def render_prompt(record: Dict[str, Any]) -> str:
    """Construct a natural language prompt from a stored execution record."""

    goal = record.get("goal", "")
    context_summary = record.get("context_summary", "")
    plan_steps = record.get("plan", [])
    execution = record.get("execution", [])

    plan_lines = []
    for idx, step in enumerate(plan_steps, start=1):
        description = step.get("description", "")
        tool = step.get("tool", step.get("name", ""))
        plan_lines.append(f"{idx}. [{tool}] {description}")

    execution_lines = []
    for idx, result in enumerate(execution, start=1):
        status = "SUCCESS" if result.get("success") else "FAILED"
        output = result.get("output") or result.get("error") or ""
        execution_lines.append(f"Step {idx} {status}: {output}")

    sections = [
        f"Goal: {goal}".strip(),
        "Context:\n" + context_summary.strip() if context_summary else "",
        "Planned Steps:\n" + "\n".join(plan_lines) if plan_lines else "",
        "Observed Execution:\n" + "\n".join(execution_lines) if execution_lines else "",
        "Compose an updated resolution summary for the goal above.",
    ]
    return "\n\n".join(filter(None, sections))


def format_lora_examples(records: Sequence[Dict[str, Any]]) -> List[LoRAExample]:
    """Convert execution records into LoRA-style instruction tuples."""

    examples: List[LoRAExample] = []
    for record in records:
        prompt = render_prompt(record)
        summary = record.get("summary", "")
        examples.append(
            LoRAExample(
                instruction=record.get("goal", ""),
                input=prompt,
                output=summary,
            )
        )
    return examples


def format_dpo_examples(records: Sequence[Dict[str, Any]]) -> List[DPOExample]:
    """Convert execution records into preference pairs when possible."""

    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(
        lambda: {"success": [], "failure": []}
    )
    for record in records:
        bucket = "success" if record.get("success") else "failure"
        grouped[record.get("goal", "")][bucket].append(record)

    pairs: List[DPOExample] = []
    for goal, variants in grouped.items():
        successes = variants["success"]
        failures = variants["failure"]
        if not successes or not failures:
            continue
        prompt = render_prompt(successes[0])
        chosen_summary = successes[0].get("summary", "")
        rejected_summary = failures[0].get("summary", "")
        pairs.append(
            DPOExample(
                prompt=prompt,
                chosen=chosen_summary,
                rejected=rejected_summary,
            )
        )
    return pairs


def count_non_empty_lines(path: Path) -> int:
    """Utility that counts the number of non-empty lines in a file."""

    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def iter_jsonl_records(path: Path) -> Iterable[Dict[str, Any]]:
    """Stream JSON objects from a JSONL file without loading them all into memory."""

    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

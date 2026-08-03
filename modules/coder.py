import json
import re
import logging
from datetime import datetime
from pathlib import Path

from utils.validators import (
    InterviewJSON,
    Codebook,
    CodingResult,
    FailedCoding,
    DimensionScore,
    LLMConfig,
)
from modules.llm_client import call, LLMError

logger = logging.getLogger(__name__)


def _get_schema_json(codebook: Codebook) -> str:
    dim_ids = [d.id for d in codebook.dimensions]
    dim_schemas = []
    for dim_id in dim_ids:
        dim_schemas.append(
            f'    "{dim_id}": {{\n'
            f'      "score": <int 0-{codebook.scale}>,\n'
            f'      "confidence": <float 0.0-1.0>,\n'
            f'      "evidence": ["<quote>", ...],\n'
            f'      "reason": "<explanation>"\n'
            f"    }}"
        )
    schema = "{\n" + ",\n".join(dim_schemas) + ',\n  "summary": "<2-3 sentence narrative>"\n}'
    return schema


def build_prompt(interview: InterviewJSON, codebook: Codebook) -> str:
    dimensions_list = []
    for d in codebook.dimensions:
        dimensions_list.append({"id": d.id, "label": d.label, "description": d.description})
    codebook_json = json.dumps(dimensions_list, indent=2)

    interview_json = json.dumps(
        {"participant": interview.participant, "questions": interview.questions},
        indent=2,
        ensure_ascii=False,
    )

    schema_json = _get_schema_json(codebook)

    prompt = codebook.prompt_template.format(
        scale=codebook.scale,
        codebook_json=codebook_json,
        interview_json=interview_json,
        schema_json=schema_json,
    )
    return prompt


def extract_json(raw: str) -> str:
    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
    if match:
        return match.group(1).strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start : end + 1]

    return raw


def validate_coding(raw: str, participant: str, codebook: Codebook) -> CodingResult | FailedCoding:
    json_str = extract_json(raw)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        Path("data/failed").mkdir(parents=True, exist_ok=True)
        Path(f"data/failed/{participant}.txt").write_text(raw, encoding="utf-8")
        return FailedCoding(participant=participant, error=f"JSON parse error: {e}", raw_output=raw)

    summary = data.pop("summary", "") if isinstance(data, dict) else ""

    try:
        dimensions = {}
        for dim in codebook.dimensions:
            dim_data = data.get(dim.id)
            if dim_data is None:
                Path("data/failed").mkdir(parents=True, exist_ok=True)
                Path(f"data/failed/{participant}.txt").write_text(raw, encoding="utf-8")
                return FailedCoding(
                    participant=participant,
                    error=f"Missing dimension '{dim.id}' in LLM output",
                    raw_output=raw,
                )
            ds = DimensionScore(**dim_data)
            if ds.score < 0 or ds.score > codebook.scale:
                Path("data/failed").mkdir(parents=True, exist_ok=True)
                Path(f"data/failed/{participant}.txt").write_text(raw, encoding="utf-8")
                return FailedCoding(
                    participant=participant,
                    error=f"Score {ds.score} for '{dim.id}' is out of range [0, {codebook.scale}]",
                    raw_output=raw,
                )
            dimensions[dim.id] = ds
    except Exception as e:
        Path("data/failed").mkdir(parents=True, exist_ok=True)
        Path(f"data/failed/{participant}.txt").write_text(raw, encoding="utf-8")
        return FailedCoding(participant=participant, error=f"Pydantic validation error: {e}", raw_output=raw)

    return CodingResult(
        participant=participant,
        dimensions=dimensions,
        model="",
        prompt_version=codebook.version,
        timestamp=datetime.now().isoformat(),
        summary=summary,
    )


def code_interview(
    interview: InterviewJSON,
    codebook: Codebook,
    llm_config: LLMConfig,
) -> CodingResult | FailedCoding:
    prompt = build_prompt(interview, codebook)
    try:
        raw = call(prompt, llm_config)
    except LLMError as e:
        return FailedCoding(participant=interview.participant, error=f"LLM error: {e.message}", raw_output="")

    result = validate_coding(raw, interview.participant, codebook)
    if isinstance(result, CodingResult):
        result.model = llm_config.model
    return result

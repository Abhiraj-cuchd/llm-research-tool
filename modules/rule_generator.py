import io
import json
import logging

from docx import Document

from utils.validators import Codebook, DimensionConfig, LLMConfig
from modules.llm_client import call, LLMError
from modules.coder import extract_json
from modules.config_loader import load_codebook

logger = logging.getLogger(__name__)


class CodebookGenerationError(Exception):
    pass


def extract_objectives(docx_bytes: bytes) -> str:
    try:
        doc = Document(io.BytesIO(docx_bytes))
    except Exception as e:
        raise CodebookGenerationError(f"Cannot read objectives document: {e}")

    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        raise CodebookGenerationError("Objectives document has no readable text.")

    return "\n\n".join(paragraphs)


def build_generation_prompt(objectives: str, scale: int) -> str:
    return (
        "You are a qualitative research methodologist. Given a research aim and "
        "objectives, design a theory-driven qualitative coding codebook that a "
        "scoring model can apply to interview transcripts.\n\n"
        "## Research Objectives\n"
        f"{objectives}\n\n"
        "## Task\n"
        "Derive a set of scoring dimensions directly from the objectives. Each "
        "objective should map to one dimension (or, if an objective clearly "
        "covers multiple distinct constructs, split it into multiple dimensions).\n\n"
        "Return ONLY a JSON object (no markdown, no prose) with this structure:\n"
        '{"scale": <int>, "dimensions": [{"id": "<snake_case>", "label": '
        '"<short human-readable label>", "weight": <int 0-100>, "description": '
        '"<concise coding guidance>"}]}\n\n'
        "Rules:\n"
        f"- Use scale = {scale}.\n"
        "- Each dimension id must be unique snake_case (lowercase, underscores).\n"
        "- Each dimension label must be short (3-6 words).\n"
        "- Weights indicate relative importance; they will be normalised later, "
        "so they only need to be proportional.\n"
        "- Each description must tell a coder what evidence to look for in a "
        "participant transcript.\n"
        "- Return JSON only."
    )


def generate_codebook(objectives: str, llm_config: LLMConfig, scale: int = 5) -> Codebook:
    prompt = build_generation_prompt(objectives, scale)

    try:
        raw = call(prompt, llm_config)
    except LLMError as e:
        raise CodebookGenerationError(f"LLM call failed: {e.message}")

    try:
        data = json.loads(extract_json(raw))
    except json.JSONDecodeError as e:
        raise CodebookGenerationError(f"LLM returned invalid JSON: {e}")

    if not isinstance(data, dict) or "dimensions" not in data:
        raise CodebookGenerationError("LLM output is missing 'dimensions'.")

    raw_dims = data.get("dimensions")
    if not isinstance(raw_dims, list) or not raw_dims:
        raise CodebookGenerationError("LLM output 'dimensions' must be a non-empty list.")

    try:
        dimensions = [DimensionConfig(**d) for d in raw_dims]
    except Exception as e:
        raise CodebookGenerationError(f"Dimension validation failed: {e}")

    default_codebook = load_codebook("config/default_codebook.yaml")

    return Codebook(
        version="generated-1.0",
        scale=int(data.get("scale", scale)),
        dimensions=dimensions,
        prompt_template=default_codebook.prompt_template,
    )

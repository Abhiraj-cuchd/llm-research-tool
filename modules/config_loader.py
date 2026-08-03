import yaml
from pathlib import Path

from utils.validators import Codebook


class ConfigError(Exception):
    pass


def load_codebook(path: str | Path) -> Codebook:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Codebook file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in codebook: {e}")

    if raw is None:
        raise ConfigError("Codebook file is empty")

    try:
        codebook = Codebook(**raw)
    except Exception as e:
        raise ConfigError(f"Codebook schema validation failed: {e}")

    return codebook

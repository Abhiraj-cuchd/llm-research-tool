import time
import logging
import httpx
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError

from utils.validators import LLMConfig

logger = logging.getLogger(__name__)


class LLMError(Exception):
    def __init__(self, message: str, raw_exception: Exception | None = None):
        self.message = message
        self.raw_exception = raw_exception
        super().__init__(message)


def call(prompt: str, config: LLMConfig) -> str:
    client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=httpx.Timeout(120.0, connect=15.0),
    )

    last_exception = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=config.model,
                messages=[
                    {"role": "system", "content": "You are a precise research assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMError("LLM returned empty response")
            return content
        except (RateLimitError, APITimeoutError, APIConnectionError) as e:
            last_exception = e
            if attempt < 2:
                wait = 2 ** (attempt + 1)
                logger.warning(f"LLM call attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
        except Exception as e:
            last_exception = e
            if attempt < 2:
                wait = 2 ** (attempt + 1)
                logger.warning(f"LLM call attempt {attempt + 1} unexpected error: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise LLMError(str(e), e)

    raise LLMError(
        f"LLM call failed after 3 attempts. Last error: {last_exception}",
        last_exception,
    )

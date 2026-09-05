import time
import logging
import httpx
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError

from utils.validators import LLMConfig

logger = logging.getLogger(__name__)

# Timeouts are riskier than retries for token spend: a timed-out request may
# have already completed server-side, so re-sending the full prompt would pay
# for it twice. Prefer a generous read timeout and no retry on timeout.
MAX_RETRIES = 3
TIMEOUT = 180.0
CONNECT_TIMEOUT = 15.0


class LLMError(Exception):
    def __init__(self, message: str, raw_exception: Exception | None = None):
        self.message = message
        self.raw_exception = raw_exception
        super().__init__(message)


def call(prompt: str, config: LLMConfig) -> str:
    client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=httpx.Timeout(TIMEOUT, connect=CONNECT_TIMEOUT),
    )

    last_exception = None
    for attempt in range(MAX_RETRIES):
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
        except APITimeoutError as e:
            # Do not retry — the request may have completed server-side and the
            # response was simply lost. Retrying would re-spend tokens.
            raise LLMError(
                "LLM request timed out. Re-run this participant; the request "
                "may have completed server-side.",
                e,
            )
        except (RateLimitError, APIConnectionError) as e:
            # Safe to retry: rate limits and connection failures do not imply
            # server-side work was billed.
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                logger.warning(f"LLM call attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise LLMError(str(e), e)
        except Exception as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                logger.warning(f"LLM call attempt {attempt + 1} unexpected error: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise LLMError(str(e), e)

    raise LLMError(
        f"LLM call failed after {MAX_RETRIES} attempts. Last error: {last_exception}",
        last_exception,
    )

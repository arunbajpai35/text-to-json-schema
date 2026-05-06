import logging
from configparser import SectionProxy

import backoff
import openai
from openai import AzureOpenAI

log = logging.getLogger(__name__)

# Errors that are worth retrying. Auth, bad-request, and programmer errors
# are NOT in this list — those should surface immediately.
_TRANSIENT = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
)


class AzureOpenAIClient:
    def __init__(self, config: SectionProxy, max_tokens: int = 4096):
        self.client = AzureOpenAI(
            api_key=config.get("api_key"),
            api_version=config.get("api_version"),
            azure_endpoint=config.get("api_base"),
        )
        self.deployment_name = config.get("deployment_name")
        self.max_tokens = max_tokens

    @backoff.on_exception(backoff.expo, _TRANSIENT, max_tries=3)
    def get_completion(self, system_prompt: str, user_input: str) -> str:
        log.debug("sending request to azure openai")
        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.3,
            max_tokens=self.max_tokens,
            timeout=60,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content.strip()

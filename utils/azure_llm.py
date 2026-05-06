import logging
from configparser import SectionProxy

import backoff
import httpx
from openai import AzureOpenAI

log = logging.getLogger(__name__)


class AzureOpenAIClient:
    def __init__(self, config: SectionProxy):
        try:
            self.client = AzureOpenAI(
                api_key=config.get("api_key"),
                api_version=config.get("api_version"),
                azure_endpoint=config.get("api_base"),
            )
            self.deployment_name = config.get("deployment_name")
        except Exception as e:
            raise ValueError(f"failed to initialize AzureOpenAIClient: {e}")

    @backoff.on_exception(backoff.expo, (Exception, httpx.TimeoutException), max_tries=3)
    def get_completion(self, system_prompt: str, user_input: str) -> str:
        log.debug("sending request to azure openai")
        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.3,
            max_tokens=4096,
            timeout=60,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content.strip()

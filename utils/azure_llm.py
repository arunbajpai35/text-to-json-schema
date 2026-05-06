import time
import backoff  
from configparser import SectionProxy
from openai import AzureOpenAI
import httpx

class AzureOpenAIClient:
    def __init__(self, config: SectionProxy):
        try:
            self.client = AzureOpenAI(
                api_key=config.get("api_key"),
                api_version=config.get("api_version"),
                azure_endpoint=config.get("api_base")
            )
            self.deployment_name = config.get("deployment_name")
        except Exception as e:
            raise ValueError(f"[❌] Failed to initialize AzureOpenAIClient: {e}")

    @backoff.on_exception(backoff.expo, (Exception, httpx.TimeoutException), max_tries=3)
    def get_completion(self, system_prompt: str, user_input: str) -> str:
        try:
            print("[🔁] Sending request to Azure OpenAI...")
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.3,
                max_tokens=4096,
                timeout=60,
                response_format={"type": "json_object"},
            )
            print("[✅] Got response")
            return response.choices[0].message.content.strip()
        except httpx.TimeoutException as e:
            print(f"[⏰] Request timed out after 60 seconds: {e}")
            raise
        except Exception as e:
            print(f"[❌] Error during LLM completion: {e}")
            raise

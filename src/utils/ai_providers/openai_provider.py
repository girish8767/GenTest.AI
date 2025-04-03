from .base import AIProvider
from openai import OpenAI

class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_completion(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a QA automation expert."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
from abc import ABC, abstractmethod

class AIProvider(ABC):
    @abstractmethod
    def generate_completion(self, prompt: str) -> str:
        pass
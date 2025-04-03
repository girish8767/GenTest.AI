from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    HUGGINGFACE_API_KEY: str = ""
    HUGGINGFACE_MODEL: str = "meta-llama/Llama-2-70b-chat-hf"
    API_BASE_URL: str = "https://api-inference.huggingface.co/models/"

settings = Settings()
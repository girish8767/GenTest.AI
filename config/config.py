from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MODEL_NAME: str = "facebook/opt-125m"
    BASE_URL: str = "http://127.0.0.1:8000"
    TIMEOUT: int = 30
    MAX_RETRIES: int = 3

    class Config:
        env_file = ".env"

settings = Settings()
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ai_api_key: str
    ai_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    ai_model_name: str = "gemini-2.0-flash"

    class Config:
        env_file = ".env"


settings = Settings()  # pyright: ignore

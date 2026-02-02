from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ai_api_key: str
    ai_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    # ai_model_name: str = "gemini-2.5-flash-lite"
    ai_model_name: str = "gemini-3-flash-preview"

    langfuse_secret_key: str
    langfuse_public_key: str
    langfuse_host: str

    login_username: str
    login_password: str
    jwt_secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"


settings = Settings()  # pyright: ignore

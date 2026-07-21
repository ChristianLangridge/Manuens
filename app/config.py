from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    extractor: str = "fake"
    anthropic_api_key: str | None = None
    log_level: str = "INFO"
    port: int = 8000

    def validate_ready(self) -> None:
        if self.extractor == "llm" and not self.anthropic_api_key:
            raise RuntimeError("EXTRACTOR=llm requires ANTHROPIC_API_KEY to be set")


settings = Settings()

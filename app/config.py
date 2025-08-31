from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):    
    # Database configuration
    database_url: str
    
    # AWS configuration
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    aws_s3_bucket: str
    
    # OpenAI configuration
    openai_api_key: str
    
    # JWT configuration
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Application configuration
    debug: bool = True
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

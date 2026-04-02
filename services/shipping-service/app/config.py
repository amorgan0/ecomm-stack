"""Configuration module for Shipping Service."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8006
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/shipping_service"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_STREAMS_URL: str = "redis://localhost:6379/0"
    
    # Service Configuration
    SERVICE_NAME: str = "shipping-service"
    SERVICE_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"
    
    # Datadog Configuration
    DD_AGENT_HOST: str = "localhost"
    DD_SERVICE: str = "shipping-service"
    DD_ENV: str = "development"
    DD_VERSION: str = "1.0.0"
    
    # Carrier API Configuration
    CARRIER_API_URL: str = "http://localhost:3002"
    CARRIER_API_TIMEOUT: int = 10
    
    # FedEx Configuration
    FEDEX_API_KEY: str = ""
    FEDEX_API_SECRET: str = ""
    FEDEX_ACCOUNT_NUMBER: str = ""
    
    # UPS Configuration
    UPS_API_KEY: str = ""
    UPS_API_SECRET: str = ""
    UPS_ACCOUNT_NUMBER: str = ""
    
    # USPS Configuration
    USPS_USER_ID: str = ""
    USPS_API_KEY: str = ""
    
    # Shipping Configuration
    DEFAULT_CARRIER: str = "FedEx"
    TRACKING_NUMBER_PREFIX: str = "SHIP"
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

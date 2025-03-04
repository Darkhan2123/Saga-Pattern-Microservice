import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./saga.db")
    PAYMENT_SERVICE_URL: str = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8001")
    INVENTORY_SERVICE_URL: str = os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8002")
    SHIPPING_SERVICE_URL: str = os.getenv("SHIPPING_SERVICE_URL", "http://localhost:8003")

    class Config:
        env_file = ".env"


settings = Settings()

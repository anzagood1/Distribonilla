from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # La URL de conexión a Supabase (PostgreSQL)
    VITE_SUPABASE_URL: str
    VITE_SUPABASE_PUBLISHABLE_KEY: str

    # Pydantic buscará automáticamente estas variables en el archivo .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Instancia global para usar en toda la app
settings = Settings()
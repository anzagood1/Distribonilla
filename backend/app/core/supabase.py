from supabase import Client, create_client

from app.core.config import settings


def create_supabase_client() -> Client:
    return create_client(
        settings.VITE_SUPABASE_URL,
        settings.VITE_SUPABASE_PUBLISHABLE_KEY,
    )

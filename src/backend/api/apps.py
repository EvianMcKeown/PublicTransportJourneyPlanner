from django.apps import AppConfig
from .raptor_engine import get_engine


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        # Preload GTFS into memory once the app registry is ready
        try:
            get_engine()  # trigger load
        except Exception as e:
            print(f"[api.ready] RaptorEngine preload error: {e}")

# app/dashboards/__init__.py
from .router import router  # so main.py can `from app.dashboards import router`

__all__ = ["router"]
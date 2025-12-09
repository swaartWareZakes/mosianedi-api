# app/computation/__init__.py
from .router import router  # so main.py can `from app.computation import router`

__all__ = ["router"]
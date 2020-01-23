from core import handle
from .route import path

pattern = [
    path("^/static/(.+?)$", handle.static)
]

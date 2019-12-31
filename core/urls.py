from core import handle
from .utils import path

pattern = [
    path("^/static/(.+?)$", handle.static)
]

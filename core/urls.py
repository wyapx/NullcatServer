from core import handle
from .utils import path

pattern = [
    path("^/static/(.+?)$", handle.static)
]

def append_url(p: list):
    pattern.extend(p)

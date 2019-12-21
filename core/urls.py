from core import handle
from .utils import path

pattarn = [
    path("^/static/(.+?)$", handle.static)
]

def append_url(p: list):
    pattarn.extend(p)

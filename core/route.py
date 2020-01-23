import re
import importlib
from .config import conf


def path(p_url: str, target: object) -> tuple:
    com = re.compile(p_url)
    return com, target


def get_handler() -> dict:
    result = {}
    for k, v in conf.get("server", "handler").items():
        urls = []
        for module_path in v:
            urls.extend(
                importlib.import_module(module_path).pattern
            )
        result[k] = urls
    return result

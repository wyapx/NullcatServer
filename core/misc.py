import os

FILTER_STRING = ["..", "%", "/", "\\"]

def safe_open(root: str, file: str, mode: str, *args, **kwargs):
    for s in FILTER_STRING:
        file.replace(s, "")
    return open(os.path.join(os.path.abspath(root), file), mode, *args, **kwargs)

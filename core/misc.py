import os


def safe_open(root: str, file: str, mode: str, *args, **kwargs):
    file.replace("..", "")
    return open(os.path.join(os.path.abspath(root), file), mode, *args, **kwargs)

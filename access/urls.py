from . import handle
from core.utils import path

pattarn = [
    path("^/access/login$", handle.user_login),
    path("^/access/register$", handle.user_register)
]
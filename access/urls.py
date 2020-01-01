from . import handle
from core.utils import path

pattern = [
    path("^/access/login$", handle.user_login),
    path("^/access/register$", handle.user_register),
    path("^/access/test$", handle.test)
]

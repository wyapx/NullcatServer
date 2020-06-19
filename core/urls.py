from core import handle
from .route import path, make_response

pattern = [
    path("^/static/(.+?)$", handle.StaticHandler),
    path("^/testpage$", make_response(content="testError", code=400))
]

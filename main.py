from core.logger import main_logger
from core.config import conf
from core.server import FullAsyncServer
from core.urls import append_url
from app.urls import pattarn as p1
from access.urls import pattarn as p2
from tools.urls import pattarn as p3

append_url(p1)
append_url(p2)
append_url(p3)
logger = main_logger.get_logger()


if __name__ == "__main__":
    host = conf.get("server", "host")
    port = conf.get("server", "port")
    https = conf.get("https", "is_enable")
    if https:
        logger.info("HTTPS Enabled")
    else:
        logger.info("HTTPS Disabled")
    try:
        FullAsyncServer(host, port, https=https).run()
    except OSError as e:
        print(e)
        exit(0)

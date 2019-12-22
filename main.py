from core.logger import main_logger
from core.config import conf
from core.server import FullAsyncServer


logger = main_logger.get_logger()
def add_handler():
    result = {}
    for k, v in conf.get("server", "handler").items():
        urls = []
        for path in v:
            urls.extend(
                __import__(path).urls.pattarn
            )
        result[k] = urls
    return result

if __name__ == "__main__":
    if conf.get("server", "daemon"):
        from core import daemon
        daemon.daemon("server.pid")
    handler = add_handler()
    try:
        FullAsyncServer(handler=handler).run()
    except OSError as e:
        print(e)
    exit(0)

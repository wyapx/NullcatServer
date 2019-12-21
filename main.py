from core.logger import main_logger
from core.config import conf
from core.server import FullAsyncServer


logger = main_logger.get_logger()
def add_handler():
    result = []
    for urls in conf.get("server", "handler"):
        result.extend(
            __import__(urls).urls.pattarn
        )
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

#import os
#os.chdir(os.path.abspath(__file__)[:5])
from core.config import conf
from core.server import FullAsyncServer
from core.utils import get_handler


if __name__ == "__main__":
    if conf.get("server", "daemon"):
        from core.ext import daemon
        daemon.daemon("server.pid")
    handler = get_handler()
    try:
        FullAsyncServer(handler=handler).run()
    except OSError as e:
        print(e)
    exit(0)

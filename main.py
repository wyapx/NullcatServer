import os
#os.chdir(os.path.abspath(__file__)[:5])
import sys
import argparse
from core.config import conf

parser = argparse.ArgumentParser()
parser.add_argument("--develop", action="store_true", help="Run app on development mode.")
parser.add_argument("--log", type=int, help="Set log level", default=None)
parser.add_argument("-d", "--daemon", action="store_true", help="Set daemon")
parser.add_argument("-r", "--reload", action="store_true", help="restart server(Daemon)")

if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    if args.reload:
        with open("server.pid", "r") as f:
            os.kill(int(f.read()), 15)  # SIGTERM
    if args.develop:
        conf.set("server", "daemon", False)
        conf.set("server", "loop_debug", True)
        conf.set("logger", "save_log", False)
        conf.set("http", "rewrite_only", False)
    if args.log != None:
        conf.set("logger", "level", args.log)
    if conf.get("server", "daemon") or args.daemon:
        from core.ext import daemon
        daemon.daemon("server.pid")
    from core.route import get_handler
    from core.server import FullAsyncServer
    handler = get_handler()
    try:
        FullAsyncServer(handler=handler).run()
    except OSError as e:
        print(e)
    exit(0)

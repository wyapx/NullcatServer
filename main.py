import os
import sys
import asyncio
import argparse

try:
    import uvloop
except ImportError:
    uvloop = None

if not uvloop:
    asyncio.set_event_loop(
        asyncio.new_event_loop()
    )
else:
    uvloop.install()
    asyncio.set_event_loop(
        uvloop.new_event_loop()
    )

parser = argparse.ArgumentParser()
parser.add_argument("--dev", action="store_true", help="Run app on development mode.")
parser.add_argument("--log", type=int, help="Set log level", default=None)
parser.add_argument("-d", "--daemon", action="store_true", help="Set daemon")
parser.add_argument("-r", "--reload", action="store_true", help="restart server(Daemon)")

if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    from core.config import conf
    if args.reload:
        if os.path.isfile("server.pid"):
            with open("server.pid", "r") as f:
                os.kill(int(f.read()), 15)  # SIGTERM
        else:
            print("no pid file, pass")
    if args.dev:
        conf.set("server", "daemon", False)
        conf.set("server", "loop_debug", True)
        conf.set("logger", "save_log", False)
        conf.set("http", "rewrite_only", False)
    if args.log is not None:
        conf.set("logger", "level", args.log)
    if conf.get("server", "daemon") or args.daemon:
        from core.ext import daemon
        daemon.daemon("server.pid")
    try:
        from core.route import get_handler
        from core.server import Manager
        Manager(get_handler()).run(conf.get("server", "worker_count"))
    except Exception:
        from core.logger import main_logger
        main_logger.logger.exception("Fatal Error:")


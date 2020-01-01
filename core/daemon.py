# Create on 2019/12/19
import os
import sys


def daemon(pidfile_path=None):
    if hasattr(os, "fork"):
        if os.fork():
            sys.exit(0)
        else:
            os.umask(0)
            os.setsid()
            with open(os.devnull, "w") as i, open(os.devnull, "r") as o:
                os.dup2(sys.stdout.fileno(), i.fileno())
                os.dup2(sys.stderr.fileno(), i.fileno())
                os.dup2(sys.stdin.fileno(), o.fileno())
            if pidfile_path:
                import atexit
                with open(pidfile_path, "w") as f:
                    f.write(str(os.getpid()))
                atexit.register(os.remove, pidfile_path)

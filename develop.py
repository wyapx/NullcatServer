import os
from core.server import FullAsyncServer
from core.utils import get_handler

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("Unable to import watchdog module")
    exit(1)

IGNORE_FILE = ("monitor.py")
ACTIVE_END = (".py",)
EXECUTE_PATH = ["py", "python3"]


def slog(*message):
    print("[Monitor]:", *message)


class MainHandler(FileSystemEventHandler):
    def __init__(self, func):
        self.func = func
        self.file_name = ""

    def on_any_event(self, event):
        self.file_name = event.src_path.split(os.sep)[-1]

    def on_modified(self, event):
        if self.file_name in IGNORE_FILE:
            return
        for end in ACTIVE_END:
            if event.src_path.endswith(end):
                slog("source file change >>>", event.src_path)
                self.func()


class Monitor(object):
    def __init__(self, path=os.getcwd()):
        self.path = path

    def init(self):
        self.server = FullAsyncServer(handler=get_handler(), block=False)
        try:
            self.server.run()
        except OSError as e:
            print(e)

    def reload(self):
        try:
            new_pattern = get_handler(reload=True)
        except Exception as e:
            slog(e)
            return
        self.server.handler = new_pattern
        slog("Reload complete")

    def run(self):
        observer = Observer()
        observer.schedule(MainHandler(self.reload), path=self.path, recursive=True)
        observer.start()
        slog("watchdog running...")
        self.init()
        try:
            self.server.loop.run_forever()
        except KeyboardInterrupt:
            pass
        observer.stop()
        slog("stopped")


if __name__ == '__main__':
    Monitor().run()

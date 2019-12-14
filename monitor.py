import os
import sys
import subprocess

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("Unable to import watchdog module")
    exit(1)

process_pid = None
IGNORE_FILE = ("tools.py")
ACTIVE_END = (".py", ".ini")
EXECUTE_PATH = ["py", "python3"]
NORMAL_EXIT = 0


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
    def __init__(self, execute, path=os.getcwd()):
        self.execute = execute
        self.path = path
        self._process = None

    def _run_process(self):
        for i, end in enumerate(EXECUTE_PATH):
            try:
                self._process = subprocess.Popen([end, self.execute],
                                                 shell=False,
                                                 stdout=sys.stdout,
                                                 stderr=sys.stderr)
            except FileNotFoundError:
                EXECUTE_PATH.pop(i)
                continue

    def _stop_process(self):
        return self._process.kill()

    def _restart_process(self):
        if self._process:
            if not self._process.poll():
                self._stop_process()
        self._run_process()
        slog("restart process complete, new pid:", self._process.pid)

    def run(self):
        observer = Observer()
        observer.schedule(MainHandler(self._restart_process), self.path, recursive=True)
        observer.start()
        self._run_process()
        slog("watchdog running...")
        try:
            while True:
                observer.join(1)
                code = self._process.poll()
                if code == 0:
                    break
                elif not code:
                    pass
                else:
                    slog("process fail, restart process")
                    self._restart_process()
        except KeyboardInterrupt:
            pass
        self._stop_process()
        observer.stop()
        slog("stopped")


if __name__ == '__main__':
    Monitor("main.py").run()

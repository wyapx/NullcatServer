import os
import sys
import time
import logging
from .config import conf
from .ext.const import work_directory

try:
    import colorlog
except ImportError:
    colorlog = None

level = conf.get("logger", "level")
log_format = conf.get("logger", "formatter").replace("$", "%")
time_format = conf.get("logger", "time_format").replace("$", "%")
save_path = conf.get("logger", "save_path")
log_colors = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'bold_yellow',
    'ERROR': 'bold_red',
    'CRITICAL': 'bold_red,bg_white',
}


def with_color(raw_format: str) -> str:
    return raw_format % {
        "asctime": "%(thin_white)s%(asctime)s%(reset)s",
        "processName": "%(processName)s",
        "process": "%(process)s",
        "message": "%(bold_blue)s%(message)s",
        "levelname": "%(log_color)s%(levelname)s%(reset)s"
    }


class Logger:
    def __init__(self, name=__name__):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        if not conf.get("server", "daemon") or sys.platform == "win32":
            console = logging.StreamHandler(sys.stdout)
            if colorlog:
                formatter = colorlog.ColoredFormatter(with_color(log_format), datefmt=time_format,
                                                      log_colors=log_colors)
            else:
                formatter = logging.Formatter(log_format, time_format)
            console.setFormatter(formatter)
            console.setLevel(level)
            self.logger.addHandler(console)
        if conf.get("logger", "save_log"):
            if not os.path.exists(save_path):
                os.mkdir(save_path, 655)
            logName = "server_%s.log" % time.strftime("%y%m%d")
            fHandler = logging.FileHandler(os.path.join(work_directory, save_path, logName))
            fHandler.setFormatter(logging.Formatter(log_format, time_format))
            fHandler.setLevel(logging.INFO)
            self.logger.addHandler(fHandler)

    def get_logger(self):
        return self.logger


main_logger = Logger()

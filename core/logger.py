import os
import sys
import time
import logging
from .config import conf
from .const_var import work_directory

level = conf.getint("logger", "level")
log_format = conf.get("logger", "formatter").replace("$", "%")
time_format = conf.get("logger", "time_format").replace("$", "%")
save_path = conf.get("logger", "save_path")


class Logger:
    def __init__(self, name=__name__):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        formatter = logging.Formatter(log_format, time_format)
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        console.setLevel(level)
        self.logger.addHandler(console)
        if conf.getboolean("logger", "is_save"):
            if not os.path.exists(save_path):
                os.mkdir(save_path, 755)
            logName = "server_%s.log" % time.strftime("%y%m%d")
            fHandler = logging.FileHandler(os.path.join(work_directory, save_path, logName))
            fHandler.setFormatter(formatter)
            fHandler.setLevel(logging.INFO)
            self.logger.addHandler(fHandler)

    def get_logger(self):
        return self.logger

main_logger = Logger()

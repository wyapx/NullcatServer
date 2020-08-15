import time
import asyncio
from typing import Callable, Coroutine
from functools import wraps, partial
from concurrent.futures import ThreadPoolExecutor
from .logger import main_logger

logger = main_logger.get_logger()
executor = ThreadPoolExecutor(8)


def async_wrapper(func: Callable):
    async def __inner(*args, **kwargs) -> Coroutine:
        loop = asyncio.get_running_loop()
        if not loop:
            raise OSError("Running loop not detected")
        return await loop.run_in_executor(executor, partial(func, *args, **kwargs))
    return __inner


def timing(func: Callable):
    @wraps(wrapped=func)
    def __inner(*args, **kwargs):
        if logger.level == 10:
            start_time = time.time() * 1000
            result = func(*args, **kwargs)
            logger.debug("".join((
                "function: ",
                func.__name__,
                " used ",
                str(round((time.time() * 1000) - start_time, 2)),
                "ms"
            )))
            return result
        else:
            return func(*args, **kwargs)
    return __inner


def hook_info(func: Callable):
    @wraps(wrapped=func)
    def __inner(*args, **kwargs):
        if logger.level == 10:
            logger.debug("".join((
                "function '",
                func.__name__,
                "' was called.",
                " values:",
                str(args),
                "|",
                str(kwargs)
            )))
        return func(*args, **kwargs)
    return __inner

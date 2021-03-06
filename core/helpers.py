import os
import re
import sys
import time
import asyncio
from functools import partial
from hashlib import sha1
from base64 import b64encode
from typing import Optional, Tuple, Callable
from jinja2 import Environment, FileSystemLoader, FileSystemBytecodeCache
from .errors import UnknownTypeError, TooBigEntityError
from .config import conf
from .ext.const import work_directory, ws_magic_string

template_path = conf.get("template", "template_path")
cache_path = conf.get("template", "cache_path")

loader = FileSystemLoader(template_path)

if conf.get("template", "use_fs_cache"):
    if not os.path.exists(cache_path):
        os.mkdir(cache_path)
    bc_cache = FileSystemBytecodeCache(os.path.join(work_directory, cache_path), "%s.cache")
else:
    bc_cache = None
env = Environment(loader=loader, bytecode_cache=bc_cache, enable_async=False, autoescape=True)


# "--" + self.bound + "\r\n" + http_like_data + "\r\n"
class __PostDataReader:
    def __init__(self, obj, limit: int, reader: asyncio.StreamReader, header: dict, buf_size=16384):
        self.obj = obj
        self.limit = limit
        self.reader = reader
        self.header = header
        self.buf_size = buf_size

    async def _read(self) -> bytes:
        return await self.reader.read(min(self.buf_size, self.limit))

    async def read(self):
        data = self._read()
        if data:
            pass


class __TaskCollector:
    def __init__(self):
        self._queue = []

    def add_task(self, task):
        self._queue.append(task)

    def run_all_task(self, loop: asyncio.AbstractEventLoop):
        for t in self._queue:
            if isinstance(t, Callable):
                loop.create_task(t())
            else:
                loop.create_task(t)
        self._queue.clear()


class PostDataManager:
    def __init__(self, request, reader: asyncio.StreamReader, buf_size=16384, limit=10485760):  # 10M
        if request.body_length > limit:
            raise TooBigEntityError(
                "Max size is %d, but %d got" % (limit, request.body_length)
            )
        self.reader = reader
        self.request = request
        self.buf_size = buf_size
        self.max_size = limit
        self.bound = b""

    async def _read(self) -> bytes:
        data = await self.reader.read(min(self.buf_size, self.request.body_length))
        if data:
            self.request.body_length -= len(data)
        return data

    async def multipart(self):
        buf = bytearray((await self._read()))
        bs = len(self.bound)
        while True:
            if len(buf) < bs + 2:  # 读取大小偏移到结束符
                buf += await self._read()
                if buf:
                    continue
                else:
                    break
            cursor = buf.find(self.bound) + bs  # 搜索bound位置
            if cursor != -1 + bs:  # 游标搜索到bound
                if buf.find(self.bound) == 0 or buf[
                                                buf.find(self.bound) - 2:buf.find(self.bound)] != b"\r\n":  # 到达header
                    try:
                        head, buf = buf[cursor + 2:].split(b"\r\n\r\n", 1)
                    except ValueError:
                        buf += await self._read()
                        continue
                    header = {}
                    for x in head.decode().split("\r\n"):
                        if not x:
                            break
                        k, v = x.split(": ")
                        header[k] = v
                    yield header
                elif buf[cursor:cursor + 2] == b"--":  # 到达结束符
                    yield buf[:buf.find(b"\r\n" + self.bound + b"--")]
                    buf.clear()
                    break
                else:
                    if buf.find(self.bound) == -1:  # 后面没有bound
                        yield buf
                        buf.clear()
                    else:  # 后面还有bound
                        yield buf[:buf.find(self.bound) - 2]  # 返回截止到下一个包
                        buf = buf[buf.find(self.bound):]
            else:  # 没有搜索到，返回整个数据块
                yield buf
                buf.clear()

    async def urlencode(self):
        buf = bytearray()
        result = {}
        while True:
            if self.request.body_length:
                buf += await self._read()
            else:
                break
        for l in buf.split(b"&"):
            try:
                k, v = l.split(b"=")
            except ValueError:
                continue
            result[k] = v
        return result

    def handle(self):
        content_type = self.request.head.get("Content-Type", "").split("; ")
        if content_type[0] == "multipart/form-data":
            for seg in content_type[1:]:
                k, v = seg.split("=")
                if k == "boundary":
                    self.bound = b"--" + v.encode()
            return self.multipart()
        elif content_type[1] == "application/x-www-form-urlencoded":
            return self.urlencode()
        else:
            raise UnknownTypeError(content_type)


class Bio:
    def __init__(self, data: bytes, buf=32768):
        self.data = bytearray(data)
        self.buf = buf

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        count = 0
        while True:
            if len(self.data) > count * self.buf:
                yield self.data[count * self.buf:(count + 1) * self.buf]
            elif len(self.data) < count * self.buf:
                return self.data[count * self.buf:]
            count += 1


class File(object):
    def __init__(self, path, buf_size=65535):
        self.path = path
        self.offset = 0
        self.buf_size = buf_size
        self.chunk_size = None
        if os.path.exists(path):
            self._file = open(path, "rb")
            self.size = os.path.getsize(path)
        else:
            raise FileNotFoundError

    def read(self, size):
        return self._file.read(size)

    def full_read(self):
        return self._file.read()

    def getSize(self):
        return self.size

    def seek(self, offset):
        self._file.seek(offset)

    def mtime(self):
        return os.stat(self.path).st_mtime

    def set_range(self, offset, size):
        if offset < 0:
            raise ValueError
        elif offset + size >= self.size:
            size = self.size - offset
        self.offset = offset
        self.chunk_size = size

    def __iter__(self):
        self.seek(self.offset)
        if self.chunk_size:
            while True:
                if self.chunk_size - self.buf_size > 0:
                    yield self.read(self.buf_size)
                else:
                    yield self.read(self.chunk_size)
                    break
                self.chunk_size -= self.buf_size
        else:
            while True:
                data = self.read(self.buf_size)
                if data:
                    yield data
                else:
                    break

    async def __aiter__(self):
        loop = asyncio.get_event_loop()
        self.seek(self.offset)
        buf = bytearray(self.buf_size)
        if self.chunk_size:
            while True:
                if self.chunk_size <= 0:
                    break
                read = await loop.run_in_executor(None, self._file.readinto, buf)
                if not read:
                    break  # EOF
                yield buf
                self.chunk_size -= self.buf_size
        else:
            while True:
                read = await loop.run_in_executor(None, self._file.readinto, buf)
                if not read:
                    break  # EOF
                yield buf

    def __len__(self) -> int:
        return self.size


def get_best_loop(debug=False):
    if sys.platform == 'win32':
        if conf.get("server", "worker_count") == 1:
            loop = asyncio.ProactorEventLoop()  # Windows IOCP loop
        else:
            loop = asyncio.SelectorEventLoop()  # Selector loop
    elif sys.platform == 'linux':
        loop = asyncio.new_event_loop()  # Linux asyncio default loop
    else:
        loop = asyncio.new_event_loop()  # Default loop
    if debug:
        loop.set_debug(debug)
        print(loop)
    return loop


def cookie_toTimestamp(__ct: str) -> int:
    return int(time.mktime(time.strptime(__ct, "%a, %d %b %Y %H:%M:%S GMT")))


def timestamp_toCookie(__ts=time.time()) -> str:
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(__ts))


def parse_range(origin, max_value=0) -> Optional[Tuple[int, int, int]]:
    result = re.match(r"bytes=(\d*)-(\d*)", origin)
    if result:
        if result.groups()[1]:
            offset, byte = (int(i) for i in result.groups())
        else:
            offset, byte = (int(result.groups()[0]), max_value)  # 4M
        total = byte - offset + 1
        if byte > max_value:
            return offset, max_value, max_value - offset + 1
        return offset, byte, total
    else:
        return None


def render(template, **kwargs):
    template = env.get_template(template)
    return template.render(**kwargs)


def ws_return_key(key) -> bytes:
    if isinstance(key, str):
        return b64encode(sha1(key.encode() + ws_magic_string).digest())
    return b64encode(sha1(key + ws_magic_string).digest())


def make_etag(mtime, file_length):
    return f'"{int(mtime)}-{str(file_length)[-3:]}"'


def run_with_wrapper(func, *args, **kwargs):
    exe = func(*args, **kwargs)
    if asyncio.iscoroutine(exe):
        asyncio.ensure_future(exe)


def interval(delay, func, *args, **kwargs):
    run_with_wrapper(func, *args, **kwargs)
    asyncio.get_event_loop().call_later(delay, partial(interval, delay, func, *args, **kwargs))


def call_later(delay, callback, *args, **kwargs):
    return asyncio.get_event_loop().call_later(delay, partial(run_with_wrapper, callback, *args, **kwargs))


task_runner = __TaskCollector()

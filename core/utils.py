import os
import re
import time
import asyncio
from hashlib import sha1
from base64 import b64encode
from typing import Optional, Tuple
from .config import conf
from .ext.const import work_directory, ws_magic_string
from jinja2 import Environment, FileSystemLoader, FileSystemBytecodeCache

template_path = conf.get("template", "template_path")
cache_path = conf.get("template", "cache_path")

loader = FileSystemLoader(template_path)

if conf.get("template", "use_fs_cache"):
    if not os.path.exists(cache_path):
        os.mkdir(cache_path)
    bc_cache = FileSystemBytecodeCache(os.path.join(work_directory, cache_path), "%s.cache")
else:
    bc_cache = None
env = Environment(loader=loader, bytecode_cache=bc_cache, enable_async=False)

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
            size = self.size-offset
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


def cookie_toTimestamp(cookieTime) -> int:
    return int(time.mktime(time.strptime(cookieTime, "%a, %d %b %Y %H:%M:%S GMT")))


def timestamp_toCookie(Time=time.time()) -> str:
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(Time))


def url_match(url: str, kv: list) -> list or None:
    if not kv:
        return None
    realurl = url.split("?")[0]
    for i in kv:
        result = i[0].search(realurl)
        if result:
            return [i[1], result]
    return None


def parse_range(origin, max_value=0) -> Optional[Tuple[int, int, int]]:
    result = re.match(r"bytes=(\d*)-(\d*)", origin)
    if result:
        if result.groups()[1]:
            offset, byte = (int(i) for i in result.groups())
        else:
            offset, byte = (int(result.groups()[0]), max_value)  # 4M
        total = byte-offset+1
        if byte > max_value:
            return offset, max_value, max_value-offset+1
        return offset, byte, total
    else:
        return None


def render(template, **kwargs):
    template = env.get_template(template)
    return template.render(**kwargs)


def ws_return_key(key: (str, bytes)) -> bytes:
    if isinstance(key, str):
        return b64encode(sha1(key.encode() + ws_magic_string).digest())
    return b64encode(sha1(key + ws_magic_string).digest())


def make_etag(mtime, file_length):
    return f'"{int(mtime)}-{str(file_length)[-3:]}"'

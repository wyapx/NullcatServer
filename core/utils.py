import os
import re
import time
from hashlib import sha3_512, sha1
from base64 import b64encode
from .config import conf
from .const_var import work_directory, ws_magic_string
from jinja2 import Environment, FileSystemLoader, FileSystemBytecodeCache

template_path = conf.get("template", "template_path")
cache_path = conf.get("template", "cache_path")

loader = FileSystemLoader(template_path)

if conf.getboolean("template", "use_fs_cache"):
    if not os.path.exists(cache_path):
        os.mkdir(cache_path)
    cache = FileSystemBytecodeCache(os.path.join(work_directory, cache_path), "%s.cache")
else:
    cache = None
env = Environment(loader=loader, bytecode_cache=cache, enable_async=False)

class File(object):
    def __init__(self, path, buffer=65535):
        self.path = path
        self.buffer = buffer
        self.chunk_range = None
        if os.path.exists(path):
            self.file = open(path, "rb")
            self.size = os.path.getsize(path)
        else:
            raise FileNotFoundError

    def read(self, size):
        return self.file.read(size)

    def full_read(self):
        return self.file.read()

    def getSize(self):
        return self.size

    def seek(self, offset):
        self.file.seek(offset)

    def mtime(self):
        return os.stat(self.path).st_mtime

    def set_range(self, start, end):
        if start < 0 or start >= end:
            raise ValueError("not support value")
        elif end >= self.size:
            end = self.size
        self.seek(start)
        self.chunk_range = end

    def __iter__(self):
        if self.chunk_range:
            while True:
                if self.chunk_range - self.buffer > 0:
                    yield self.read(self.buffer)
                else:
                    yield self.read(self.chunk_range+1)
                    break
                self.chunk_range -= self.buffer
        else:
            while True:
                data = self.read(self.buffer)
                if data:
                    yield data
                else:
                    break


def encrypt_passwd(password):
    if isinstance(password, str):
        password = password.encode()
    return sha3_512(password).hexdigest()

def unescape(content):
    if type(content) == bytes:
        return content.decode('unicode-escape')
    return content.encode().decode('unicode-escape')

def cookie_toTimestamp(cookieTime) -> int:
    return int(time.mktime(time.strptime(cookieTime, "%a, %d %b %Y %H:%M:%S GMT")))

def timestamp_toCookie(Time=time.time()) -> str:
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(Time))

def url_match(url: str, kv: list) -> list or None:
    realurl = url.split("?")[0]
    for i in kv:
        result = i[0].search(realurl)
        if result:
            return [i[1], result]
    return None

def parse_range(origin, max_value=0) -> tuple:
    chunk_size = max_value
    unit, arange = origin.split(b"=", 1)
    if unit != b"bytes":
        raise TypeError("Only support bytes unit")
    start, end = arange.split(b"-")
    if not end:
        end = int(start) + chunk_size
        if end > max_value:
            end = max_value-1
    return int(start), int(end)

def render(template, **kwargs):
    template = env.get_template(template)
    return template.render(**kwargs)

def ws_return_key(key):
    return b64encode(sha1(key+ws_magic_string).digest())

def path(p_url: str, target: object) -> tuple:
    com = re.compile(p_url)
    return com, target

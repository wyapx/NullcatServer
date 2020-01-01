import re
import asyncio
import struct
from .const_var import *
from gzip import compress
from json import dumps
from time import time
from io import BytesIO
from .utils import timestamp_toCookie, File, ws_return_key
from .db import DBSession, mem_db
from urllib.parse import unquote

database = DBSession()

class BaseRequest:
    pass

class HTTPRequest(BaseRequest):
    def __init__(self, origin, ip="0.0.0.0"):
        self.body = b""
        self.remote = ip
        self.head = {}
        self.re_args = ()
        self.GET_data = None
        self.POST_data = None
        info, extra = origin.split(b"\r\n", 1)
        self.method, self.path, self.protocol = re.match(r"(\w{3,7}) (.*) HTTP/(\d\.\d)", info.decode()).groups()
        for kv in extra[:-4].decode().split("\r\n"):
            k, v = kv.split(": ", 1)
            self.head[k] = v

    @property
    def GET(self) -> dict:
        if self.GET_data:
            return self.GET_data
        if self.path.find("?") == -1:
            return {}
        data = self.path.split("?", 1)[1]
        try:
            block = data.split("&")
        except IndexError:
            block = data
        result = {}
        try:
            for i in block:
                k, v = i.split("=", 1)
                result[k] = unquote(v)
            return result
        except ValueError:
            return {}

    @property
    def POST(self) -> dict:
        if not self.body:
            return {}
        try:
            block = self.body.split(b"&")
        except IndexError:
            block = self.body
        result = {}
        try:
            for i in block:
                k, v = i.split(b"=", 1)
                result[k] = v
            return result
        except ValueError:
            return {}

    @property
    def Cookie(self) -> dict:
        cookie = self.head.get("Cookie")
        if not cookie:
            return {}
        buf = cookie.split("; ")
        kv = {}
        for i in buf:
            k, v = i.split("=", 1)
            kv[k] = v
        return kv

    def __repr__(self) -> str:
        return f'Request(method="{self.method}", path="{self.path}", protocol="{self.protocol}")'


class Response(object):
    def __init__(self, content="", code=200, content_type="text/html"):
        self.code = code
        self.protocol = "HTTP/1.1"
        self.header = {"Content-Type": content_type}
        self.content = content
        if isinstance(self.content, (str, bytes)):
            self.length = len(self.content)
        else:
            self.length = 0

    def set_content(self, content):
        self.content = content
        return self

    def status(self, code, protocol="HTTP/1.1"):
        self.code = code
        self.protocol = protocol

    def add_header(self, dict_header):
        self.header.update(dict_header)

    def set_cookie(self, name, value, expire=3600, **kwargs):
        result = f"{name}={value}; expires={timestamp_toCookie(time() + expire)};"
        for k, v in kwargs.items():
            if k and v:
                result += f" {k}={v};"
            elif k:
                result += f" {k};"
        self.header["Set-Cookie"] = result

    def getLen(self) -> int:
        return self.length

    def build(self) -> bytearray:
        header = bytearray()
        header += f"{self.protocol} {self.code} {code_message.get(self.code, 'OK')}\r\n".encode()
        for k, v in self.header.items():
            header += f"{k}: {v}\r\n".encode()
        header += b"\r\n"
        return header

    async def send(self, sendObj: asyncio.StreamWriter.write, drain: asyncio.StreamWriter.drain) -> int:
        data = self.build()
        sendObj(data)
        await self.conn_drain(drain)
        if isinstance(self.content, bytes):
            sendObj(self.content)
        elif isinstance(self.content, File):
            sendObj(self.content.full_read())
        else:
            sendObj(self.content.encode())

    @staticmethod
    async def conn_drain(drain) -> bool:
        try:
            await drain()
        except ConnectionError:
            return True
        return False


class BaseHandler:
    def __init__(self, request: BaseRequest, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.request = request
        self.writer = writer
        self.reader = reader

#    async def auth_check(self) -> bool:
#        cookie = self.request.Cookie.get("session_id")
#        if cookie:
#            #result = database.query(Session).filter(Session.sessionid == cookie).one_or_none()
#            result = mem_db.get(cookie)
#            print(cookie, result)
#            if result:
#                return True
#        return False

    async def run(self):
        pass

    async def loop(self):
        pass


class WebHandler(BaseHandler):
    async def run(self) -> Response:
        if self.request.method == "GET":
            res = await self.get()
        elif self.request.method == "POST":
            res = await self.post()
        else:
            res = Http405()
        if not res:
            raise ValueError("Function no result")
        return res

    async def get(self):
        return Http405()

    async def post(self):
        return Http405()


class WsHandler(BaseHandler):
    keep_alive = True

    async def run(self) -> Response:
        if self.request.head.get("Upgrade") != "websocket":
            return Http405()
        key = self.request.head.get("Sec-WebSocket-Key")
        if not key:
            return Http400()
        res = Response(code=101)
        res.add_header({"Connection": "Upgrade",
                        "Upgrade": "websocket",
                        "Sec-WebSocket-Accept": ws_return_key(key).decode()})
        return res

    async def read(self, timeout=-1) -> tuple:
        try:
            if timeout == -1:
                b1, b2 = await self.reader.read(2)
            else:
                b1, b2 = await asyncio.wait_for(self.reader.read(2), timeout)
        except asyncio.TimeoutError:
            return None, None
        except ValueError:
            return None, OPCODE_CLOSE_CONN
        # fin = b1 & FIN
        opcode = b1 & OPCODE
        masked = b2 & MASKED
        payload_length = b2 & PAYLOAD_LEN
        if opcode == OPCODE_CLOSE_CONN:
            print("close")
            self.close_connection()
            return None, opcode
        if not masked:
            print("must masked")
            return None, OPCODE_CLOSE_CONN
        if payload_length == 126:
            payload_length = struct.unpack(">H", await self.reader.read(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack(">Q", await self.reader.read(8))[0]
        ms = await self.reader.read(4)
        message_bytes = bytearray()
        i = 0
        d = await self.reader.read(payload_length)
        while i != payload_length:
            message_bytes.append(d[i] ^ ms[i % 4])
            i += 1
        return message_bytes, opcode

    def send_text(self, message: (str, bytes, bytearray), opcode=OPCODE_TEXT):
        """
        Important: Fragmented(=continuation) messages are not supported since
        their usage cases are limited - when we don't know the payload length.
        """

        header = bytearray()
        if not isinstance(message, (bytes, bytearray)):
            payload = message.encode()
        else:
            payload = message
        payload_length = len(payload)

        # Normal payload
        if payload_length <= 125:
            header.append(FIN | opcode)
            header.append(payload_length)

        # Extended payload
        elif 126 <= payload_length <= 65535:
            header.append(FIN | opcode)
            header.append(PAYLOAD_LEN_EXT16)
            header.extend(struct.pack(">H", payload_length))

        # Huge extended payload
        elif payload_length < 18446744073709551616:
            header.append(FIN | opcode)
            header.append(PAYLOAD_LEN_EXT64)
            header.extend(struct.pack(">Q", payload_length))

        else:
            raise Exception("Message is too big. Consider breaking it into chunks.")

        self.writer.write(header + payload)

    def close_connection(self, message="Connection close"):
        self.send_text(message, opcode=OPCODE_CLOSE_CONN)
        self.keep_alive = False

    async def write(self, data):
        self.send_text(data)
        await self.writer.drain()

    async def write_nowait(self, data):
        self.send_text(data)

    async def loop(self):
        await self.onInit()
        while self.keep_alive:
            data, opcode = await self.read(30)
            if opcode == OPCODE_TEXT:
                await self.onReceive(data)
            elif opcode == OPCODE_PING:
                await self.onPing()
            elif opcode == OPCODE_PONG:
                pass
            elif opcode == OPCODE_CLOSE_CONN:
                self.close_connection()
                self.keep_alive = False
            else:
                if not opcode:
                    self.send_text("", opcode=OPCODE_PING)
                    continue
                print("Unhandle opcode:", opcode)
                self.close_connection()

    async def onInit(self):
        pass

    async def onReceive(self, data):
        pass

    async def onPing(self):
        self.send_text("", OPCODE_PONG)


class StreamResponse(Response):
    def setLen(self, length):
        self.length = length

    def getLen(self) -> int:
        if isinstance(self.content, File) and not self.length:
            return self.content.getSize()
        return self.length

    @asyncio.coroutine
    def send(self, sendObj: asyncio.StreamWriter.write, drain: asyncio.StreamWriter.drain) -> int:
        data = self.content
        sendObj(self.build())
        for i in data:
            try:
                yield from drain()
            except ConnectionError:
                break
            yield  # Fix "socket.send() raised exception." issue
            sendObj(i)


class JsonResponse(Response):
    def __init__(self, content=dict):
        Response.__init__(self, content=dumps(content), content_type="application/json")


class FileResponse(Response):
    def __init__(self, path, content_type="application/octet-stream"):
        Response.__init__(self, content_type=content_type)
        try:
            self.content = File(os.path.join(work_directory, path))
        except FileNotFoundError:
            self.content = b"404 Not found"

    def getLen(self) -> int:
        if isinstance(self.content, File):
            return self.content.getSize()
        return len(self.content)


class HtmlResponse(Response):
    def __init__(self, content, request: BaseRequest):
        Response.__init__(self, content, content_type="text/html")
        self.request = request
        if self.request.head.get("Accept-Encoding"):
            self.add_header({"Transfer-Encoding": "chunked", "Content-Encoding": "gzip"})

    async def send(self, sendObj: asyncio.StreamWriter.write, drain: asyncio.StreamWriter.drain) -> int:
        if isinstance(self.content, str):
            data = self.content.encode()
        else:
            data = self.content
        send = compress(data=data, compresslevel=5)
        buf = BytesIO(send)
        sendObj(self.build())
        while True:
            if await self.conn_drain(drain):
                break
            s = buf.read(512)
            if s:
                sendObj(format(len(s), "x").encode())
                sendObj(b"\r\n")
                sendObj(s)
                sendObj(b"\r\n")
            else:
                sendObj(b"0")
                sendObj(b"\r\n\r\n")
                break


def Http204():
    return Response(code=204)


def Http404(message="404 Not Found"):
    return Response(message, 404)


def Http400(message="400 Client Error"):
    return Response(message, 400)


def Http301(url):
    res = Response(code=301)
    res.add_header({"Location": url})
    return res


def HttpServerError(message="500 Internet Server Error"):
    return Response(message, 500)


def Http304():
    return Response(code=304)


def Http403(message="Access denied"):
    return Response(message, 403)


def Http405(message="405 Method Not Allow"):
    return Response(message, 405)

import sys
import socket
import asyncio
from .logger import main_logger
from .web import BaseRequest, Http404, HttpServerError, BaseHandler
from .urls import pattern
from .config import conf
from .utils import url_match

try:
    import uvloop
except ImportError:
    uvloop = None


def gethostip(default=""):
    try:
        return socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        return default


def get_best_loop(debug=False):
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()  # Windows IOCP loop
    elif sys.platform == 'linux':
        if uvloop:
            loop = uvloop.new_event_loop()  # Linux uvloop (thirty part loop)
        else:
            loop = asyncio.new_event_loop()  # Linux asyncio default loop
    else:
        loop = asyncio.new_event_loop()  # Default loop
    if debug:
        loop.set_debug(debug)
        print(loop)
    return loop


def get_ssl_context(alpn: list):
    import ssl
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.options |= (ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1)
    support_ciphers = conf.get("https", "https_ciphers")
    context.set_ciphers(support_ciphers)
    context.set_alpn_protocols([*alpn])
    context.load_cert_chain(conf.get("https", "cert_file"),
                            conf.get("https", "key_file"))
    return context


class FullAsyncServer(object):
    log = main_logger.get_logger()

    def __init__(self, host="", port=80, https=False, loop=get_best_loop()):
        self.host = host
        self.port = port
        self.timeout = conf.getint("server", "request_timeout")
        if https:
            self.ssl = get_ssl_context(["http/1.1"])
        else:
            self.ssl = None
        self.loop = loop

    def millis(self):
        return int(self.loop.time() * 1000)

    async def server(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        ip, port = writer.get_extra_info("peername")
        while True:
            try:
                header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), self.timeout)
            except (ConnectionError, asyncio.TimeoutError, asyncio.IncompleteReadError):
                break
            except OSError as e:
                print(e.strerror)
                break
            if header:
                try:
                    req = BaseRequest(header, ip)
                except (ValueError, AttributeError):
                    self.log.warning("Request Unpack Error(from %s)" % ip)
                    self.log.warning(("Origin data: ", header))
                    break
                length = req.head.get("Content-Length")
                if length:
                    req.body = await reader.read(int(length))
                start_time = self.millis()
                match = url_match(req.path, pattern)
                if match:
                    req.head["rest_url"] = match[1].groups()
                    try:
                        obj: BaseHandler = match[0](req, reader, writer)
                        res = await obj.run()
                    except Exception:
                        self.log.exception("Handler Error:")
                        res = HttpServerError()
                else:
                    res = Http404()
                if req.head.get("Connection", "close").lower() == b"keep-alive":
                    state = "keep-alive"
                else:
                    state = "close"
                res.add_header({"Server": "NullcatServer"})
                if res.code != 101:
                    res.add_header({"Content-length": res.getLen(),
                                    "Connection": state})
                code = await res.send(writer.write, writer.drain)
                if code == 101:
                    await obj.loop()
                    req.head["Connection"] = "close"
                self.log.info(f"{req.method} {req.path}:{code} {ip}({self.millis() - start_time}ms)")
                if req.head.get("Connection", "close") == "close":
                    break
            else:
                break
        self.log.debug(f"{ip}:{port} disconnect")
        writer.close()

    def run(self):
        coro = asyncio.start_server(self.server, self.host, self.port, ssl=self.ssl)
        server = self.loop.run_until_complete(coro)
        self.log.info(f"Server start on {gethostip(self.host)}:{self.port}")
        self.log.info("Press Ctrl+C to stop server")
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        self.log.warning("Server closed")
        server.close()


if __name__ == "__main__":
    FullAsyncServer().run()

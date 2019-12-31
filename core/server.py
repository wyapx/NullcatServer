import sys
import socket
import asyncio
from .logger import main_logger
from .web import HTTPRequest, Http404, HttpServerError, BaseHandler
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


def get_ssl_context(alpn: list, cert_path, key_path):
    import ssl
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.options |= (ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1)
    support_ciphers = conf.get("https", "support_ciphers")
    context.set_ciphers(support_ciphers)
    context.set_alpn_protocols([*alpn])
    context.load_cert_chain(cert_path, key_path)
    return context


class FullAsyncServer(object):
    log = main_logger.get_logger()

    def __init__(self, handler, block=True, loop=get_best_loop()):
        self.block = block
        self.handler = handler
        self.timeout = conf.get("server", "request_timeout")
        if conf.get("https", "is_enable"):
            self.ssl = get_ssl_context(["http/1.1"],
                                       conf.get("https", "cert_path"),
                                       conf.get("https", "key_path"))
        else:
            self.ssl = None
        self.loop = loop

    def millis(self):
        return int(self.loop.time() * 1000)

    async def server(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        ip, port = writer.get_extra_info("peername")[0:2]
        while True:
            try:
                header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), self.timeout)
            except (ConnectionError, asyncio.TimeoutError, asyncio.IncompleteReadError):
                break
            except OSError as e:
                print(e)
                break
            if header:
                try:
                    req = HTTPRequest(header, ip)
                except (ValueError, AttributeError):
                    self.log.warning("Request Unpack Error(from %s)" % ip)
                    self.log.warning(("Origin data: ", header))
                    break
                pattern = self.handler.get(req.head.get("Host", "*"), self.handler.get("global"))
                length = req.head.get("Content-Length")
                if length:
                    req.body = await reader.read(int(length))
                start_time = self.millis()
                match = url_match(req.path, pattern)
                if match:
                    req.re_args = match[1].groups()
                    try:
                        obj: BaseHandler = match[0](req, reader, writer)
                        res = await obj.run()
                    except Exception:
                        self.log.exception("Handler Error:")
                        res = HttpServerError()
                else:
                    res = Http404()
                if res.code != 101:
                    if req.head.get("Connection", "close").lower() == "keep-alive":
                        state = "keep-alive"
                    else:
                        state = "close"
                    res.add_header({"Access-Control-Allow-Origin": "*",
                                    "Content-length": res.getLen(),
                                    "Connection": state,
                                    "Server": "NullcatServer"})
                    await res.send(writer.write, writer.drain)
                else:
                    await res.send(writer.write, writer.drain)
                    await obj.loop()
                    req.head["Connection"] = "close"
                self.log.info(f"{req.method} {req.path}:{res.code} {ip}({self.millis() - start_time}ms)")
                if req.head.get("Connection", "close") == "close":
                    break
            else:
                break
        self.log.debug(f"{ip}:{port} disconnect")
        writer.close()

    def signal_handler(self, sig):
        self.log.warning(f"Got signal {sig}, closing...")
        self.loop.stop()
        
    def run(self):
        if sys.platform != "win32":
            from signal import SIGTERM, SIGINT
            for sig in (SIGTERM, SIGINT):
                self.loop.add_signal_handler(sig, self.signal_handler, sig)
        if conf.get("http", "is_enable"):
            http = asyncio.start_server(self.server,
                                        conf.get("http", "host"),
                                        conf.get("http", "port"))
            self.loop.run_until_complete(http)
            self.log.info(f"HTTP is running at {conf.get('http', 'host')}:{conf.get('http', 'port')}")
        if self.ssl:
            https = asyncio.start_server(self.server,
                                         conf.get("https", "host"),
                                         conf.get("https", "port"),
                                         ssl=self.ssl)
            self.loop.run_until_complete(https)
            self.log.info(f"HTTPS is running at {conf.get('https', 'host')}:{conf.get('https', 'port')}")
        if self.block:
            self.log.info("Press Ctrl+C to stop server")
            try:
                self.loop.run_forever()
            except KeyboardInterrupt:
                self.loop.stop()
            self.log.warning("Server closed")


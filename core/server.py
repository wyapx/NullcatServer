import sys
import time
import socket
import asyncio
from asyncio import StreamReader, StreamReaderProtocol
from .helpers import task_runner, get_best_loop
from .logger import main_logger
from .web import HTTPRequest, http404, http500
from .config import conf
from .route import url_match
from .rewrite import Redirect_Handler


async def create_server(client_connected_cb, sock: socket.socket, limit=2 ** 16, loop=None, **kwargs):
    if not loop:
        loop = asyncio.get_event_loop()

    def factory():
        reader = StreamReader(limit=limit, loop=loop)
        protocol = StreamReaderProtocol(reader, client_connected_cb,
                                        loop=loop)
        return protocol

    return await loop.create_server(factory, sock=sock, **kwargs)


def get_local_ip(default=""):
    try:
        return socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        return default


def _run_server(handler, http: socket.socket, https: socket.socket):
    FullAsyncServer(handler, loop_debug=True).run(http, https)


def make_socket(host: str, port: int, reuse_addr=True):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if sys.platform != "nt" and reuse_addr:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    return sock


class Manager:
    def __init__(self, handler, logger=None, **kwargs):
        if not logger:
            logger = main_logger.get_logger()
        self.logger = logger
        self.handler = handler
        self.kwargs = kwargs
        self.workers = []

    def run(self, worker_count: int = 1):
        if conf.get("http", "is_enable"):
            http_sock = make_socket(conf.get("http", "host"), conf.get("http", "port"))
            self.logger.info(f"HTTP is running at {get_local_ip(conf.get('http', 'host'))}:{conf.get('http', 'port')}")
        else:
            http_sock = None
        if conf.get("https", "is_enable"):
            https_sock = make_socket(conf.get("https", "host"), conf.get("https", "port"))
            self.logger.info(f"HTTPS is running at {get_local_ip(conf.get('https', 'host'))}:{conf.get('https', 'port')}")
        else:
            https_sock = None
        if worker_count == 0:
            from multiprocessing import cpu_count
            worker_count = cpu_count()
        if worker_count > 1:
            from multiprocessing import Process
            for no in range(worker_count - 1):
                p = Process(target=_run_server, args=(self.handler, http_sock, https_sock))
                p.name = f"Worker:{no}"
                p.start()
                self.workers.append(p)
        self.logger.info("Press Ctrl+C to stop server")
        _run_server(self.handler, http_sock, https_sock)


class FullAsyncServer(object):
    def __init__(self, handler, block=True, loop=None, log=None, timeout=10, loop_debug=False, backlog=1024):
        if not loop:
            loop = get_best_loop(loop_debug)
        if not log:
            log = main_logger.get_logger()
        self.log = log
        self.block = block
        self.handler = handler
        self.timeout = timeout
        self.backlog = backlog
        if conf.get("https", "is_enable"):
            from .context import get_ssl_context
            self.ssl = get_ssl_context(["http/1.1"], conf.get("https", "support_ciphers"))
        else:
            self.ssl = None
        self.loop = loop

    def millis(self):
        return int(time.time() * 1000)

    async def http1_handler(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, data: tuple) -> bool:
        ip, header = data
        if header:
            start_time = self.millis()
            try:
                req = HTTPRequest(header, ip)
            except (ValueError, AttributeError):
                self.log.warning("Request Unpack Error(from %s)" % ip)
                self.log.warning(("Origin data: ", header))
                return False
            pattern = self.handler.get(req.head.get("Host", "*"), self.handler.get("*", []))
            if isinstance(pattern, str):
                req.head["X-Local"] = pattern
                sender = await Redirect_Handler(req, reader, writer).run()
                sender.add_header({"Connection": "close"})
                await sender.send(writer)
                self.log.info(f"{req.method} {req.head.get('Host')}:{req.path} {ip} Redirect")
                return False
            match = url_match(req.path, pattern)
            obj = None
            if match:
                req.re_args = match[1].groups()
                try:
                    obj = match[0](req, reader, writer)
                    res = await obj.run()
                except Exception:
                    self.log.exception("Handler raise an error:")
                    res = http500()
            else:
                res = http404()
            if res.code != 101:
                res.add_header({"Content-Length": res.getLen(),
                                "Connection": req.head.get("Connection", "close").lower(),
                                "Server": "Apache/2.2.23 (Unix)",
                                "X-Powered-By": "PHP/5.3.12"})
            await res.send(writer)
            if obj:
                await obj.loop()
                req.head["Connection"] = "close"
            self.log.info(f"{req.method} {req.path}:{res.code} {req.head.get('Host')} {req.real_ip}"
                          f"({self.millis() - start_time}ms)")
            if req.head.get("Connection", "close") == "close":
                return False
            return True

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
            if not await self.http1_handler(reader, writer, (ip, header)):
                break
        writer.close()
        self.log.debug(f"[{ip}:{port}]: connect lost")

    def signal_handler(self, sig):
        self.log.warning(f"Got signal {sig}, stopping...")
        self.loop.stop()

    def run(self, http_sock: socket.socket = None, https_sock: socket.socket = None):
        if sys.platform != "win32":
            from signal import SIGTERM, SIGINT
            for sig in (SIGTERM, SIGINT):
                self.loop.add_signal_handler(sig, self.signal_handler, sig)
        if conf.get("http", "is_enable") and http_sock:
            if conf.get("http", "rewrite_only") and self.ssl:
                from .rewrite import server
            else:
                server = self.server
            http = create_server(server, sock=http_sock)
            self.loop.create_task(http)
            self.log.debug("HTTP Enable")
        if self.ssl and https_sock:
            https = create_server(self.server, sock=https_sock, ssl=self.ssl)
            self.loop.create_task(https)
            self.log.debug("HTTPS Enable")

        task_runner.run_all_task(self.loop)

        if self.block:
            try:
                self.loop.run_forever()
            except KeyboardInterrupt:
                self.loop.stop()
            self.log.warning("Server closed")

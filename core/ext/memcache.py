# Create at 2019/12/08
import socket
import re


"""class Memcached:
    def __init__(self, url="127.0.0.1:11211", retry_count=3, debug=False):
        self.host, self.port = url.split(":", 1)
        self.debug = debug
        self.status = True
        self.retry_count = retry_count

    async def _open_connection(self):
        try:
            self._reader, self._writer = await asyncio.open_connection(self.host, int(self.port))
        except ConnectionError as e:
            if self.debug:
                print(e)
            return False
        return True

    def _is_connected(self):
        if hasattr(self, "_writer"):
            if not self._reader.at_eof():
                return True
        return False

    async def _keep_connection(self):
        if not self._is_connected():
            for _ in range(self.retry_count):
                if await self._open_connection():
                    break
            self.status = self._is_connected()
            return self._is_connected()
        return True

    async def _cmd_sender(self, cmd: (bytearray, bytes), value=None):
        if not self._is_connected():
            await self._keep_connection()
        self._writer.write(cmd)
        self._writer.write(b"\r\n")
        await self._writer.drain()
        if value:
            self._writer.write(value)
            self._writer.write(b"\r\n")
            await self._writer.drain()

    async def _store_cmd(self, cmd_type: bytes, key: (str, bytes), value: bytes, expire: int, flags=0):
        if not self.status:
            return -2
        data = bytearray(cmd_type)
        data.append(32)  # space key
        if isinstance(key, str):
            data += key.encode()
        else:
            data += key
        data += f" {flags} {expire} {len(value)}".encode()
        await self._cmd_sender(data, value)
        result = await self._reader.readline()
        if self.debug:
            print(result)
        if result == b"STORED\r\n":
            return 1
        elif result == b"NOT_STORED\r\n":
            return 0
        elif result == b"ERROR\r\n":
            pass
        else:
            print("Unknown result", result)
        return -1

    async def add(self, key: (str, bytes), value: bytes, expire=0, flags=0):
        return await self._store_cmd(b"add", key, value, expire, flags)

    async def set(self, key: (str, bytes), value: bytes, expire=0, flags=0):
        return await self._store_cmd(b"set", key, value, expire, flags)

    async def append(self, key: (str, bytes), value: bytes, expire=0, flags=0):
        return await self._store_cmd(b"append", key, value, expire, flags)

    async def replace(self, key: (str, bytes), value: bytes, expire=0, flags=0):
        return await self._store_cmd(b"replace", key, value, expire, flags)

    async def prepend(self, key: (str, bytes), value: bytes, expire=0, flags=0):
        return await self._store_cmd(b"prepend", key, value, expire, flags)

    async def delete(self, key: (str, bytes)):
        if not self.status:
            return -2
        if isinstance(key, bytes):
            data = b"delete " + key
        else:
            data = b"delete " + key.encode()
        await self._cmd_sender(data)
        result = await self._reader.readline()
        if result == b"DELETED\r\n":
            return True
        elif result == b"NOT_FOUND\r\n":
            return False
        else:
            print("Unknown result", result)

    async def gets(self, key: (tuple, list)):
        if not self.status:
            return -2
        cmd = bytearray(b"get")
        for i in key:
            cmd.append(32)  # space key
            cmd += i.encode()
        await self._cmd_sender(cmd)
        result = {}
        for i in key:
            result[i] = None
        while True:
            buf = await self._reader.readline()
            if buf == b"END\r\n":
                break
            rs = re.match(r"VALUE (.*) (\d*) (\d*)", buf.decode())
            if rs:
                rk, flags, length = rs.groups()
                data = await self._reader.readexactly(int(length))
                result[rk] = (flags, data)
        return result

    async def get(self, key: str):
        if not self.status:
            return -2
        cmd = f"get {key}".encode()
        await self._cmd_sender(cmd)
        while True:
            buf = await self._reader.readline()
            if buf == b"END\r\n":
                break
            if self.debug:
                print(buf)
            rs = re.match(r"VALUE (.*) (\d) (\d{1, 8})", buf.decode())
            if rs:
                _, flags, length = rs.groups()
                data = await self._reader.readexactly(int(length))
        return flags, data


    async def close(self):
        self._writer.close()"""

class Memcached:
    def __init__(self, url="127.0.0.1:11211", retry_count=3, debug=False):
        self.host, self.port = url.split(":", 1)
        self.debug = debug
        self.status = True
        self.retry_count = retry_count

    def _open_connection(self):
        try:
            self._sock = socket.socket()
            self._sock.connect((self.host, int(self.port)))
        except ConnectionError as e:
            self._sock = None
            if self.debug:
                print(e)
            return False
        return True

    def _is_connected(self):
        if hasattr(self, "_sock"):
            if self._sock:
                return True
        return False

    def _keep_connection(self):
        if not self._is_connected():
            for _ in range(self.retry_count):
                if self._open_connection():
                    break
            self.status = self._is_connected()
            return self._is_connected()
        return True

    def _cmd_sender(self, cmd: (bytearray, bytes), value=None):
        if not self._is_connected():
            if not self._open_connection():
                return False
        try:
            self._sock.send(cmd)
            self._sock.send(b"\r\n")
        except ConnectionError as e:
            if self.debug:
                print(e)
            return False
        if value:
            self._sock.send(value)
            self._sock.send(b"\r\n")
        return True

    def _store_cmd(self, cmd_type: bytes, key: (str, bytes), value: bytes, expire: int, flags=0):
        if not self.status:
            return -2
        data = bytearray(cmd_type)
        data.append(32)  # space key
        if isinstance(key, str):
            data += key.encode()
        else:
            data += key
        data.append(32)  # space key
        data += f"{flags} {expire} {len(value)}".encode()
        if not self._cmd_sender(data, value):
            self.status = False
            return -2
        result = self._sock_readline()
        if self.debug:
            print(result)
        if result == b"STORED\r\n":
            return 1
        elif result == b"NOT_STORED\r\n":
            return 0
        elif result == b"ERROR\r\n":
            pass
        else:
            print("Unknown result", result)
        return -1

    def _stats_cmd(self, typ=""):
        if not self.status:
            return -2
        if not self._cmd_sender(f"stats {typ}".encode()):
            self.state = False
            return -2
        result = []
        while True:
            data = self._sock_readline()
            if data == b"END\r\n":
                return result
            if data[:4] == b"STAT":
                result.append(data[5:-2])


    def _sock_readline(self):
        result = bytearray()
        while True:
            buf = self._sock.recv(1)
            if buf == b"\r":
                result += buf
                buf = self._sock.recv(1)
                if buf == b"\n":
                    result += buf
                    return result
            result += buf

    def _sock_readexactly(self, bytes_count):
        result = bytearray()
        for _ in range(bytes_count):
            result.append(self._sock.recv(1)[0])
        return result

    def add(self, key: (str, bytes), value: bytes, expire=0, flags=0):
        return self._store_cmd(b"add", key, value, expire, flags)

    def set(self, key: (str, bytes), value: bytes, expire=0, flags=0):
        return self._store_cmd(b"set", key, value, expire, flags)

    def append(self, key: (str, bytes), value: bytes, expire=0, flags=0):
        return self._store_cmd(b"append", key, value, expire, flags)

    def replace(self, key: (str, bytes), value: bytes, expire=0, flags=0):
        return self._store_cmd(b"replace", key, value, expire, flags)

    def prepend(self, key: (str, bytes), value: bytes, expire=0, flags=0):
        return self._store_cmd(b"prepend", key, value, expire, flags)

    def delete(self, key: (str, bytes)):
        if not self.status:
            return -2
        if isinstance(key, bytes):
            data = b"delete " + key
        else:
            data = b"delete " + key.encode()
        if not self._cmd_sender(data):
            self.state = False
            return -2
        result = self._sock_readline()
        if result == b"DELETED\r\n":
            return True
        elif result == b"NOT_FOUND\r\n":
            return False
        else:
            print("Unknown result", result)

    def gets(self, key: (tuple, list)):
        if not self.status:
            return -2
        cmd = bytearray(b"get")
        for i in key:
            cmd.append(32)  # space key
            cmd += i.encode()
        if not self._cmd_sender(cmd):
            self.state = False
            return -2
        result = {}
        for i in key:
            result[i] = None
        while True:
            buf = self._sock_readline()
            if buf == b"END\r\n":
                break
            rs = re.match(r"VALUE (.*) (\d) (\d*)", buf.decode())
            if rs:
                rk, flags, length = rs.groups()
                data = self._sock_readexactly(int(length))
                result[rk] = (flags, data)
        return result

    def get(self, key: str):
        if not self.status:
            return -2
        if not self._cmd_sender(f"get {key}".encode()):
            self.state = False
            return -2
        while True:
            buf = self._sock_readline()
            if self.debug:
                print(buf)
            if buf == b"END\r\n":
                break
            elif buf == b"\r\n":
                continue
            rs = re.match(r"VALUE (.*) (\d) (\d*)", buf.decode())
            if rs:
                _, flags, length = rs.groups()
                data = self._sock_readexactly(int(length))
        return flags, data

    def flush_all(self, time=0):
        if not self.status:
            return -2
        cmd = f"flush_all {time}"
        if not self._cmd_sender(cmd):
            self.state = False
            return -2
        if self._sock_readline() == b"OK\r\n":
            return True
        return False

    def get_stats(self, typ=""):
        stats = self._stats_cmd(typ)
        if stats == -2:
            return -2
        if stats:
            result = dict()
            for i in stats:
                k, v = i.decode().split(" ", 1)
                result[k] = v
            return result

    def close(self):
        self._sock.close()

def test():
    m = Memcached(debug=True)
    while True:
        cmd = input("CMD: ")
        if cmd == "add":
            key = input("Key: ")
            value = input("Value: ")
            print(m.add(key, value.encode()))
        elif cmd == "get":
            key = input("Key: ")
            print(m.get(key))
        elif cmd == "stats":
            v = input("type")
            print(m.get_stats(v))
        else:
            print("Unknown")

if __name__ == '__main__':
    test()

import json
import secrets
from core.web import WebHandler, WsGroupHandler, HtmlResponse


user_count = 0
session = {}
server_name = "[Server]: "


def pack_message(data: (str, bytes, list)):
    if isinstance(data, list):
        return json.dumps({"t": 0, "m": data}).encode()
    return json.dumps({"t": 0, "m": [data]}).encode()

class chatroom_front(WebHandler):
    async def get(self):
        return HtmlResponse("chatroom.html")

class chatroom_backend(WsGroupHandler):
    join = False
    name = "NoName"
    token = None
    def emit_message(self, data):
        self.emit(pack_message(data))

    def send_message(self, data):
        self.send(pack_message(data))

    def member_join(self, token, name):
        self.name = name
        self.join = True
        self.token = token
        self.add_conn()
        self.send('{"t": 2}')
        self.emit_message(f"{server_name} {name} 加入")
        self.send(pack_message(server_name + "加入成功，获取服务器命令帮助请输入/help"))
        global user_count
        user_count += 1

    async def onInit(self):
        buf, code = await self.read(5)
        if not code or not buf:
            self.close_connection()
            return
        data = json.loads(buf)
        if data["token"] in session:
            self.member_join(data["token"], session.get(data["token"]))
        else:
            self.send(json.dumps({"t": 3, "token": secrets.token_hex(10)}))

    async def onReceive(self, data):
        n = json.loads(data)
        if self.join:
            if n["t"] == 1:  # send message
                if n["m"]:  # message is exist
                    self.emit_message(self.name+"："+n["m"])  # append message
                else:
                    return
            elif n["t"] == 4:
                cmd = n["cmd"].split(" ", 1)
                if cmd[0][0] != "/":
                    return self.send_message("不是一个正确的命令")
                if cmd[0] == "/help":
                    return self.send_message("/online 获取在线用户数量\n/group 切换群组\n/broadcast 广播信息")
                elif cmd[0] == "/online":
                    return self.send_message(f"当前在线用户数: {user_count}")
                elif cmd[0] == "/group":
                    if len(cmd) != 2:
                        return self.send_message("使用方法：/group [群组名]")
                    self.change_group(cmd[1])
                    self.emit_message(f"{server_name} {self.name} 加入")
                    return self.send_message(f"已切换至群组：{cmd[1]}")
                elif cmd[0] == "/broadcast":
                    if len(cmd) != 2:
                        return self.send_message("使用方法：/broadcast [信息]")
                    self.broadcast(pack_message("(broadcast)" + self.name + "：" + cmd[1]))
                else:
                    return self.send(pack_message("未知命令"))
            else:
                pass
                # self.close_connection()
        else:
            if n["n"]:  # get name
                self.member_join(n["token"], n["n"])
                session[n["token"]] = n["n"]

    async def onClose(self):
        if self.token:
            self.emit_message(server_name + self.name + " 离开")
            global user_count
            user_count -= 1
            self.remove_conn()
        self.close_connection()

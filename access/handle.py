from time import time
from core.web import WebHandler, http400, http301, HtmlResponse, JsonResponse
from core.utils import render
from .utils import check_login_info, login, register, encrypt_passwd, auth_require


class user_login(WebHandler):
    async def post(self):
        try:
            user, passwd = self.request.POST.values()
        except ValueError:
            return http400()
        if user or passwd:
            if check_login_info(user, passwd):
                expire = int(time() + 172800)  # 2 days
                key = login(user, expire)
                res = JsonResponse({"status": 200, "redirect_to": "/"})
                res.set_cookie("session_id", key, path="/", HttpOnly="")
            else:
                res = JsonResponse({"status": 400, "message": "用户名或密码错误"})
        else:
            res = JsonResponse({"status": 400, "message": "请输入用户名和密码"})
        return res

    async def get(self):
        return HtmlResponse(render("login.html"), self.request)

class user_register(WebHandler):
    async def post(self):
        try:
            user, passwd = self.request.POST.values()
        except ValueError:
            return http400()
        if user or passwd: 
            if check_login_info(user, passwd) == -1: 
                register(user, encrypt_passwd(passwd)) 
                res = http301("/access/login")
            else: 
                res = JsonResponse({"status": 400, "message": "Username is Exist"})
        else: 
            res = JsonResponse({"status": 400, "message": "Please input username and password"}) 
        return res

    async def get(self):
        return HtmlResponse(render("register.html"), self.request)

class test(WebHandler):
    @auth_require
    async def get(self):
        return JsonResponse({"status": 'OK'})

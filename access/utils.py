import secrets
from hashlib import sha3_512
from .tables import Session, User
from core.db import DBSession
from core.web import http403


database = DBSession()

def encrypt_passwd(password: (str, bytes)) -> bytes:
    if isinstance(password, str): 
        return sha3_512(password.encode()).hexdigest()
    return sha3_512(password).hexdigest()

def check_login_info(username, passwd) -> bool:
    user = database.query(User.password).filter(User.name == username).one_or_none()
    if user:
        if user[0] == encrypt_passwd(passwd):
            return True
    return False

def check_username_exist(username):
    user = database.query(User.password).filter(User.name == username).one_or_none()
    if user:
        return True
    return False

def login(username, expires) -> bytes:
    key = secrets.token_hex(20)
    database.add(Session(name=username, sessionid=key, expire=expires))
    database.commit()
    return key

def register(username, password):
    database.add(User(name=username, password=password))
    database.commit()

def auth_require(func):
    async def decorated(self) -> bool:
        cookie = self.request.Cookie.get("session_id")
        if cookie:
            result = database.query(Session).filter(Session.sessionid == cookie).one_or_none()
            if result:
                return await func(self)
        return http403()
    return decorated

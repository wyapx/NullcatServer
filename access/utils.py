import secrets
from hashlib import sha3_512
from .tables import Session, User
from core.db import DBSession, mem_db
from core.web import Http403


database = DBSession()

def encrypt_passwd(password): 
    if isinstance(password, str): 
        password = password.encode()
    return sha3_512(password).hexdigest()

def check_login_info(username, passwd) -> int:
    user = database.query(User.password).filter(User.name == username).one_or_none()
    if user:
        if user[0] == encrypt_passwd(passwd):
            return 1
        return 0
    else:
        return -1

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
        return Http403()
    return decorated

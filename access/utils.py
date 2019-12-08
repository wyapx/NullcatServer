import secrets
from core.tables import Session, User
from core.db import DBSession, mem_db
from core.utils import encrypt_passwd


database = DBSession()

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
    #database.add(Session(name=username, sessionid=key, expire=expires))
    #database.commit()
    mem_db.add(key, username, expire=expires)
    return key

def register(username, password):
    database.add(User(name=username, password=password))
    database.commit()

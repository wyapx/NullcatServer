from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import SingletonThreadPool

from .config import conf

db_url = conf.get("database", "database_url")
is_debug = conf.get("database", "debug")
mem_db = None

Base = declarative_base()
if db_url.find("sqlite") == 0:
    engine = create_engine(db_url, poolclass=SingletonThreadPool, echo=is_debug,
                           connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url, encoding="utf-8", convert_unicode=True, echo=is_debug, pool_recycle=60)
if conf.get("database", "use_redis"):

    mem_db_url = conf.get("database", "redis_url")
    if not mem_db_url:
        raise ValueError("must define redis_url in config before use redis")
DBSession = sessionmaker(bind=engine)


class Redis:
    pass


class SessionManager:
    def __init__(self):
        self._session_maker = sessionmaker(bind=engine)

    def __enter__(self) -> Session:
        self.session: Session = self._session_maker()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.session.close()
            return
        try:
            self.session.commit()
        finally:
            self.session.close()

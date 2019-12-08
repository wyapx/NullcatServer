from .config import conf
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import SingletonThreadPool

db_url = conf.get("database", "database_url")
is_debug = conf.getboolean("database", "debug")
mem_db = None

Base = declarative_base()
if conf.getboolean("database", "use_sqlite"):
    engine = create_engine(db_url, poolclass=SingletonThreadPool, connect_args={"check_same_thread": False}, echo=is_debug)
else:
    engine = create_engine(db_url, encoding="utf-8", convert_unicode=True, echo=is_debug)
if conf.getboolean("database", "use_memcached"):
    from .memcache import Memcached
    mem_db_url = conf.get("database", "memcached_url")
    if not mem_db_url:
        raise ValueError("must define memcached_url in config before use memcached")
    mem_db = Memcached(mem_db_url, debug=is_debug)
DBSession = sessionmaker(bind=engine)

import os
from configparser import ConfigParser
from .const_var import work_directory

server_conf = [
    "server",
    ["host", "0.0.0.0"],
    ["port", "80"],
    ["request_timeout", "30"]
]

https_conf = [
    "https",
    ["use_https", "False"],
    ["https_ciphers", "ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128"],
    ["cert_file", ""],
    ["key_file", ""],
]

db_conf = [
    "database",
    ["use_sqlite", "True"],
    ["database_url", "sqlite:///database.db"],
    ["use_memcached", "False"],
    ["memcached_url", "127.0.0.1:11211"],
    ["debug", "False"]
]

log_conf = [
    "logger",
    ["level", "20"],
    ["formatter", "$(asctime)s ($(processName)s/$(threadName)s)[$(levelname)s]:$(message)s"],
    ["time_format", "$Y/$m/$d $H:$M:$S"],
    ["is_save", "True"],
    ["save_path", "log/"]
]

template_conf = [
    "template",
    ["template_path", "template/"],
    ["use_fs_cache", "True"],
    ["cache_path", "__pycache__/"],
]

all_config = [server_conf, https_conf, db_conf, log_conf, template_conf]

conf = ConfigParser()
conf_file_path = os.path.join(work_directory, "server.ini")
conf.read(conf_file_path, encoding="utf-8")

if not os.path.exists(conf_file_path):
    for a in all_config:
        config_name = a[0]
        conf.add_section(config_name)
        for k, v in a[1:]:
            conf.set(config_name, k, v)
    conf.write(open(conf_file_path, "w"))

# TODO
# 将configparser模块更换为dict

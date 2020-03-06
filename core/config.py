import os
import json
from .ext.const import work_directory


base_config = {
    "server": {
        "request_timeout": 10,
        "daemon": True,
        "loop_debug": False,
        "handler": {"*": ["core.urls"]}
     },
    "http": {
        "host": "",
        "port": 80,
        "is_enable": True,
        "rewrite_only": False
    },
    "https": {
        "host": "",
        "port": 443,
        "is_enable": False,
        "support_ciphers": "ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128",
        "cert_path": "",
        "key_path": ""
    },
    "database": {
        "database_url": "sqlite:///database.db",
        "use_memcached": False,
        "memcached_url": "",
        "debug": False
    },
    "logger": {
        "level": 20,
        "formatter": "$(asctime)s [$(levelname)s]:$(message)s",
        "time_format": "$Y/$m/$d $H:$M:$S",
        "save_log": True,
        "save_path": "log/"
    },
    "template": {
        "template_path": "template/",
        "use_fs_cache": True,
        "cache_path": "__pycache__/"
    }
}


def dict_sync(source: dict, target: dict):
    for k, v in source.items():
        if isinstance(v, dict):
            dict_sync(v, target[k])
        else:
            target[k] = v


class JsonConfigParser:
    def __init__(self, config: dict):
        self.config = config
    
    def update(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError
        with open(path, "r") as raw:
            data = raw.read()
        try:
            dict_sync(
                json.loads(data),
                base_config
            )
        except json.decoder.JSONDecodeError as e:
            print("Error: ConfigFile is not load")
            print("reason:", e)
            exit(0)

    def get(self, segment, block):
        if segment in self.config:
            result = self.config[segment]
            if block in result:
                return result[block]
            raise KeyError(f"block {block} is not exist")
        raise KeyError(f"segment {segment} is not exist")

    def set(self, segment, block, data):
        if segment in self.config:
            self.config[segment][block] = data
        else:
            raise KeyError(f"block {block} is not exist")


conf = JsonConfigParser(base_config)
conf_path = os.path.join(work_directory, "config.json")
if not os.path.exists(conf_path):
    print(f"Warning: {conf_path} not found, regenerating...")
    with open(conf_path, "w") as f:
        f.write(
           json.dumps(base_config, indent=2)
        )
conf.update(conf_path)

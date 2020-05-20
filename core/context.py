import ssl
from .config import conf

# Load context
server_certs = {"default": None}
for name, value in conf.get("https", "certificates").items():
    server_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    server_context.load_cert_chain(value["cert"], value["key"])
    server_certs[name] = server_context


def sni_callback(sock: ssl.SSLSocket, req_hostname: str, cb_context, as_callback=True):
    req_context = server_certs.get(req_hostname, server_certs.get("default"))
    if req_context:
        sock.context = req_context
    else:
        pass


def get_ssl_context(alpn: list, ciphers: str):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.options |= (ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1)
    support_ciphers = ciphers
    context.set_ciphers(support_ciphers)
    context.set_alpn_protocols([*alpn])
    context.set_servername_callback(sni_callback)
    return context

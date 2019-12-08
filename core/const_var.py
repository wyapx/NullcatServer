import os
work_directory = os.getcwd()
code_message = {
    101: "Switching Protocol",
    200: "OK",
    204: "No Content",
    206: "Partial Content",
    304: "Not Modified",
    400: "Bad Request",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allow",
    411: "Length Required",
    412: "Precondition failed",
    500: "Internet Server Error",
    503: "Service Unavailable"
}


### WebSocket Define ###
ws_magic_string = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
FIN = 0x80
OPCODE = 0x0f
MASKED = 0x80
PAYLOAD_LEN = 0x7f 
PAYLOAD_LEN_EXT16 = 0x7e
PAYLOAD_LEN_EXT64 = 0x7f 
OPCODE_CONTINUATION = 0x0 
OPCODE_TEXT = 0x1 
OPCODE_BINARY = 0x2 
OPCODE_CLOSE_CONN = 0x8 
OPCODE_PING = 0x9 
OPCODE_PONG = 0xA

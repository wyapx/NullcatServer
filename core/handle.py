import os
from .ext.mimetype import get_type
from .web import http404, StreamResponse, http304, http400, WebHandler, Response
from .utils import File, timestamp_toCookie, parse_range
from .ext.const import work_directory

### CONST DEFINE ###
static_path = os.path.join(work_directory, "static/")

### SERVER HANDLERS ###
class static(WebHandler):
    # TODO
    # Fix: Firefox download
    async def get(self):
        request = self.request
        if request.re_args[0].find("..") != -1:
            return http400()
        path = os.path.join(static_path, request.re_args[0])
        if os.path.exists(path):
            f = File(path)
            mtime = timestamp_toCookie(f.mtime()).encode()
            if request.head.get("If-Modified-Since") == mtime:
                return http304()
            else:
                file_type = get_type(path)
                res = StreamResponse(f, content_type=file_type)
                content_range = request.head.get("Range")
                if content_range:
                    offset, byte, total = parse_range(content_range, f.size)
                    f.set_range(offset, total)
                    res.add_header({"Content-Range": f"bytes {offset}-{byte}/{f.size+1}"})
                    if_unmodified_since = request.head.get("If-Unmodified-Since")
                    if if_unmodified_since == mtime:
                        res.code = 200
                    else:
                        res.code = 206
                    res.setLen(total)
                else:
                    res.add_header({"Cache-Control": "no-cache",
                                    "Last-Modified": mtime.decode(),
                                    "Etag": f.mtime(),
                                    "Accept-Ranges": "bytes"})
            return res
        return http404()


import os
from .mimetype import get_type
from .web import Http404, StreamResponse, Http304, Http400, WebHandler, Response
from .utils import File, timestamp_toCookie, parse_range
from .const_var import work_directory

### CONST DEFINE ###
static_path = os.path.join(work_directory, "static/")

### SERVER HANDLERS ###
class static(WebHandler):
    async def get(self):
        request = self.request
        if request.re_args[0].find("..") != -1:
            return Http400()
        path = os.path.join(static_path, request.re_args[0])
        if os.path.exists(path):
            f = File(path)
            mtime = timestamp_toCookie(f.mtime()).encode()
            if request.head.get("If-Modified-Since") == mtime:
                return Http304()
            else:
                file_type = get_type(path)
                res = StreamResponse(f, content_type=file_type)
                content_range = request.head.get("Range")
                if content_range:
                    start, end = parse_range(content_range, f.size)
                    f.set_range(start, end)
                    res.add_header({"Content-Range": f"bytes {start}-{end}/{f.size}"})
                    if_unmodify_since = request.head.get("If-Unmodified-Since")
                    if if_unmodify_since == mtime:
                        res.code = 200
                    elif if_unmodify_since and if_unmodify_since != mtime:
                        return Response(code=412)
                    else:
                        res.code = 206
                    res.setLen(end-start+1)
                else:
                    res.add_header({"Accept-Ranges": "bytes"})
                    res.add_header({"Cache-Control": "no-cache",
                                    "Last-Modified": mtime.decode(),
                                    "Etag": f.mtime()})
            return res
        return Http404()


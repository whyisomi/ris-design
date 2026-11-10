import functools, http.server, socketserver, sys, time
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args)); sys.stderr.flush()
    def do_GET(self):
        if self.path.startswith("/slow"):
            # держим load event ~6 сек, чтобы скриншот дождался lazy-картинок
            time.sleep(6)
            gif = bytes.fromhex("47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b")
            self.send_response(200); self.send_header("Content-Type","image/gif")
            self.send_header("Content-Length",str(len(gif))); self.end_headers(); self.wfile.write(gif); return
        return super().do_GET()
class Threaded(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True; allow_reuse_address = True
root = sys.argv[1] if len(sys.argv)>1 else "."
port = int(sys.argv[2]) if len(sys.argv)>2 else 8080
handler = functools.partial(Handler, directory=root)
with Threaded(("0.0.0.0", port), handler) as httpd:
    print(f"serving {root} on :{port}", flush=True); httpd.serve_forever()

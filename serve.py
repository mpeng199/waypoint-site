"""A preview server that does not let the browser cache anything.

`python3 -m http.server` sends no Cache-Control at all, so the browser decides
for itself — and for a navigation to `index.html#bills` it will happily serve
the copy in memory without asking whether the file changed. That is invisible
and maddening: you edit a page, reload the page you are on and see the change,
click a nav tab, and land on a version from before the edit.

    python3 serve.py [port] [--directory DIR]

Same arguments as http.server, plus no-store on every response.
"""
import functools
import http.server
import sys


class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        # One line per request is useful; the default also prints the date twice.
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    argv = sys.argv[1:]
    directory = "."
    if "--directory" in argv:
        i = argv.index("--directory")
        directory = argv[i + 1]
        del argv[i:i + 2]
    port = int(argv[0]) if argv else 8753
    handler = functools.partial(NoCache, directory=directory)
    print(f"serving {directory} on http://localhost:{port} with no-store", flush=True)
    http.server.ThreadingHTTPServer(("", port), handler).serve_forever()

"""A preview server that does not let the browser cache anything.

`python3 -m http.server` sends no Cache-Control at all, so the browser decides
for itself — and for a navigation to `about.html#bills` it will happily serve
the copy in memory without asking whether the file changed. That is invisible
and maddening: you edit a page, reload the page you are on and see the change,
click a nav tab, and land on a version from before the edit.

    python3 serve.py [port] [--directory DIR]

Same arguments as http.server, plus no-store on every response.
"""
import functools
import http.server
import socket
import sys


# no-store only governs responses fetched from now on. Whatever a browser
# cached before this server existed is still in there and still considered
# fresh — heuristic freshness is a tenth of the file's age, so a month-old copy
# is trusted for days. It gets served with no network request at all, which is
# how one page can look current while the page a nav tab leads to looks a month
# old, and why no header of ours reaches it.
#
# So every HTML response also tells the browser to throw this origin's cache
# away. Every one, not the first: a purge-once flag is consumed by whichever
# client connects first — here, the preview pane — and the browser actually
# holding the stale copy never sees it. With no-store already set there is
# nothing left to purge on a second visit, so repeating it costs nothing.
class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        leaf = self.path.split("?")[0].split("/")[-1]
        if leaf.endswith(".html") or "." not in leaf:
            self.send_header("Clear-Site-Data", '"cache"')
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

    # Dual stack. ThreadingHTTPServer defaults to AF_INET, and macOS Chrome
    # tries ::1 before 127.0.0.1 — an IPv4-only listener makes every request
    # pay for a failed connection first, and makes the browser behave
    # differently from curl, which is a miserable thing to debug on top of a
    # caching problem.
    class DualStack(http.server.ThreadingHTTPServer):
        address_family = socket.AF_INET6

        def server_bind(self):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            super().server_bind()

    print(f"serving {directory} on http://localhost:{port} "
          f"(no-store, IPv4 + IPv6)", flush=True)
    DualStack(("::", port), handler).serve_forever()

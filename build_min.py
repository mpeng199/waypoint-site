#!/usr/bin/env python3
"""Strip the comments out of the CSS and JS the browser downloads.

    python3 build_min.py            # write the .min files
    python3 build_min.py --check    # compare only, write nothing

This repo's stylesheets and scripts are about half prose. That prose is the
reason the site is maintainable and it is why check.py can assert on intent
rather than only on syntax, so none of it is going anywhere — but there is no
reason to send it to a phone on a library's wifi. Measured over the five files
the site serves, brotli'd, which is how Cloudflare delivers them:

    source      60.9KB      what was being shipped
    stripped    25.0KB      what ships now

Brotli alone does not get this. It compresses the comments well; it cannot
know they are unnecessary. A full minifier (esbuild) reaches 22.6KB — 2.4KB
better, for a toolchain this repo has deliberately never needed. Comments are
94% of the prize, and stdlib can take them.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
Newlines are preserved. Collapsing JS onto one line means taking
responsibility for automatic semicolon insertion, and the entire saving from
doing so is a rounding error after brotli. Identifiers are never renamed and
no expression is ever rewritten: the output differs from the input only by
characters that could not have been executed. That is what makes it safe for
check.py to go on reading the readable file and still be describing the file
that ships.

The output is compared, never trusted — see check_minified_is_generated() in
check.py, which regenerates in memory and diffs byte for byte. Run this after
editing any of the five sources, the same way build_help.py is run after
editing data/resources.csv.
"""

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (source, what the browser asks for). Anything added here must also be
# referenced from the HTML, which check.py verifies in both directions.
SOURCES = [
    ("tokens.css", "tokens.min.css"),
    ("styles.css", "styles.min.css"),
    ("help.css", "help.min.css"),
    ("script.js", "script.min.js"),
    ("help.js", "help.min.js"),
]


def strip_css(src):
    """Remove /* */ comments. Quoted strings are copied through untouched, so
    a comment sequence inside content:"..." or a url() survives."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'":
            quote = c
            out.append(c)
            i += 1
            while i < n:
                out.append(src[i])
                if src[i] == "\\":
                    if i + 1 < n:
                        out.append(src[i + 1])
                        i += 2
                        continue
                elif src[i] == quote:
                    i += 1
                    break
                i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            end = src.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


# A '/' opens a regex literal only where a value may begin. After a value —
# an identifier, a literal, a ')' or a ']' — it is division. These are the
# keywords after which a '/' is still a regex, which is the case that a bare
# "previous character" test gets wrong (`return /x/.test(s)`).
_REGEX_OK_WORDS = {
    "return", "typeof", "instanceof", "in", "of", "new", "delete", "void",
    "throw", "case", "do", "else", "yield", "await",
}


def strip_js(src):
    """Remove // and /* */ comments.

    Strings and regex literals are copied through verbatim, so a '//' inside
    "https://..." or a '/*' inside a character class is never mistaken for a
    comment. Newlines are kept exactly as they were: nothing here can change
    where a statement ends.
    """
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]

        if c in "\"'`":
            quote = c
            out.append(c)
            i += 1
            while i < n:
                if src[i] == "\\" and i + 1 < n:
                    out.append(src[i:i + 2])
                    i += 2
                    continue
                out.append(src[i])
                if src[i] == quote:
                    i += 1
                    break
                i += 1
            continue

        if c == "/" and i + 1 < n:
            nxt = src[i + 1]
            if nxt == "/":
                end = src.find("\n", i)
                i = n if end == -1 else end          # keep the newline itself
                continue
            if nxt == "*":
                end = src.find("*/", i + 2)
                # A block comment spanning lines still ends the line it began
                # on, so put back one newline if it swallowed any.
                chunk = src[i:n if end == -1 else end + 2]
                i = n if end == -1 else end + 2
                if "\n" in chunk:
                    out.append("\n")
                continue

            # division or regex? look back at the last meaningful character
            j = len(out) - 1
            while j >= 0 and out[j] in " \t\r\n":
                j -= 1
            prev = out[j] if j >= 0 else ""
            word = ""
            if prev.isalnum() or prev in "_$":
                k = j
                while k >= 0 and (out[k].isalnum() or out[k] in "_$"):
                    k -= 1
                word = "".join(out[k + 1:j + 1])
            is_regex = (
                prev == "" or
                (not (prev.isalnum() or prev in "_$)]") ) or
                word in _REGEX_OK_WORDS
            )
            if is_regex:
                out.append(c)
                i += 1
                in_class = False
                while i < n:
                    ch = src[i]
                    if ch == "\\" and i + 1 < n:
                        out.append(src[i:i + 2])
                        i += 2
                        continue
                    out.append(ch)
                    i += 1
                    if ch == "[":
                        in_class = True
                    elif ch == "]":
                        in_class = False
                    elif ch == "/" and not in_class:
                        break
                    elif ch == "\n":       # unterminated: not a regex after all
                        break
                continue

        out.append(c)
        i += 1
    return "".join(out)


def tidy(text):
    """Drop indentation and blank lines. Newlines themselves stay."""
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln) + "\n"


def build(source):
    """The exact bytes that belong in the .min file for `source`."""
    raw = (ROOT / source).read_text(encoding="utf-8")
    stripped = strip_css(raw) if source.endswith(".css") else strip_js(raw)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    stamp = (f"/* generated by build_min.py from {source} "
             f"[sha256:{digest}] — edit {source}, then run build_min.py */\n")
    return stamp + tidy(stripped)


def main():
    check_only = "--check" in sys.argv
    stale = []
    for source, target in SOURCES:
        want = build(source)
        path = ROOT / target
        have = path.read_text(encoding="utf-8") if path.is_file() else None
        if have == want:
            print(f"  ok    {target}")
            continue
        stale.append(target)
        if check_only:
            print(f"  STALE {target}")
        else:
            path.write_text(want, encoding="utf-8")
            print(f"  wrote {target}  ({len(want):,} bytes from {len(
                (ROOT / source).read_text(encoding='utf-8')):,})")
    if check_only and stale:
        print(f"\n{len(stale)} stale: run python3 build_min.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

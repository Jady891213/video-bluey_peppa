#!/usr/bin/env python3
"""仅用标准库预览一个独立故事，默认只允许本机访问。"""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("story", choices=("gift", "football"))
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    directory = ROOT / "websites" / args.story / "dist"
    if not (directory / "index.html").is_file():
        parser.error(f"缺少网站入口：websites/{args.story}/dist/index.html")
    port = args.port if args.port is not None else (8873 if args.story == "gift" else 8874)
    if not 1 <= port <= 65535:
        parser.error("端口必须在 1–65535 之间")
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    print(f"{args.story}: http://127.0.0.1:{port} （Ctrl+C 退出）", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

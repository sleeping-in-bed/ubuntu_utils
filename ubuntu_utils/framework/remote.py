import os
import pickle
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import request

import requests

from ubuntu_utils import configs

from .lib.file_utils import get_file_paths
from .settings import *


class FileServer:
    RC_DIR = Settings.files_dir
    PORT = configs.FILE_SERVER_PORT

    class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            file_path = FileServer.RC_DIR / self.path.lstrip("/")
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(file_size))
                self.end_headers()

                with open(file_path, "rb") as f:
                    while chunk := f.read(1024 * 1024 * 16):
                        self.wfile.write(chunk)
            else:
                self.send_error(404, "File Not Found")

        def do_POST(self):
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            data = pickle.loads(post_data)

            response = get_file_paths(FileServer.RC_DIR / data, relative=True)

            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(pickle.dumps(response))

    def start(self):
        def _start():
            with HTTPServer(
                ("0.0.0.0", self.PORT), self.SimpleHTTPRequestHandler
            ) as self.httpd:
                print(f"Server Started: http://0.0.0.0:{self.PORT}")
                self.httpd.serve_forever()

        self.server_thread = threading.Thread(target=_start)
        self.server_thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.server_thread.join()
        print("Server Closed")


class Remote:
    DST_DIR = Path("/tmp")
    HOST = configs.FILE_SERVER_HOST
    PORT = configs.FILE_SERVER_PORT
    LOCAL_DIR = configs.LOCAL_FILE_DIR

    def get_file(self, file_path: Path | str) -> Path | None:
        if self.LOCAL_DIR:
            local_path = Path(self.LOCAL_DIR) / file_path
            if local_path.exists():
                return local_path
        if self.HOST and self.PORT:
            url = f"http://{self.HOST}:{self.PORT}/{file_path}"
            print(url)
            with request.urlopen(url) as response:
                dst_path = self.DST_DIR / file_path
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dst_path, "wb") as file:
                    while True:
                        chunk = response.read(1024 * 32)
                        if not chunk:
                            break
                        file.write(chunk)
                print(f"Get file '{dst_path}' successfully")
            return dst_path

    def get_file_paths(self, dir_path: Path | str) -> list[Path]:
        print(self.HOST, self.PORT, self.LOCAL_DIR)
        if self.LOCAL_DIR:
            return get_file_paths(Path(self.LOCAL_DIR) / dir_path, relative=True)

        if self.HOST and self.PORT:
            url = f"http://{self.HOST}:{self.PORT}/"
            print(url)
            response = requests.post(url, data=pickle.dumps(dir_path))
            return pickle.loads(response.content)
        return []

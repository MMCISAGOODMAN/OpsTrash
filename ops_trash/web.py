import json
import threading
import os
import socket
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from io import BytesIO
from .storage import ensure_dirs, METADATA_FILE, FILES_DIR, read_metadata, get_stats, clean_older_than, get_size_and_count, restore_entry

ROOT_DIR = Path(__file__).parent
STATIC_DIR = ROOT_DIR / 'static'
TEMPLATE_DIR = ROOT_DIR / 'templates'


class OpsHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith('/api/'):
            self.handle_api_get(path, parsed.query)
            return
        # serve index or static files
        if path == '/' or path == '/index.html':
            return self.serve_file(TEMPLATE_DIR / 'index.html')
        # static assets: /static/app.js -> STATIC_DIR/app.js
        if path.startswith('/static/'):
            rel = path[len('/static/'):]
            if rel and '..' not in rel:
                fs_path = STATIC_DIR / rel
                if fs_path.exists() and fs_path.is_file():
                    return self.serve_file(fs_path)
        # legacy direct access: /style.css -> STATIC_DIR/style.css
        fs_path = STATIC_DIR / path.lstrip('/')
        if fs_path.exists() and fs_path.is_file():
            return self.serve_file(fs_path)
        # fallback 404
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'Not Found')

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith('/api/'):
            length = int(self.headers.get('Content-Length', '0'))
            body = self.rfile.read(length) if length > 0 else b''
            try:
                data = json.loads(body.decode('utf-8')) if body else {}
            except Exception:
                data = {}
            return self.handle_api_post(path, data)
        self.send_response(404)
        self.end_headers()

    def handle_api_get(self, path, query):
        if path == '/api/list':
            meta = read_metadata()
            files = sorted(meta.get('files', []), key=lambda x: x.get('deleted_at', ''), reverse=True)
            self._send_json({'files': files})
            return
        if path == '/api/stats':
            s = get_stats()
            self._send_json(s)
            return
        if path == '/api/size':
            count, total = get_size_and_count()
            self._send_json({'count': count, 'total': total})
            return
        self._send_json({'error': 'unknown api'}, status=404)

    def handle_api_post(self, path, data):
        if path == '/api/clean':
            days = int(data.get('days', 7))
            removed, freed = clean_older_than(days)
            self._send_json({'removed': removed, 'freed': freed})
            return
        if path == '/api/restore':
            ids = data.get('ids', []) or []
            results = []
            for id_ in ids:
                try:
                    # try restore; if exists, our storage.restore_entry will raise; we catch and attempt rename
                    try:
                        dest = restore_entry(int(id_), overwrite=False, rename_on_conflict=False)
                        results.append({'id': id_, 'restored_to': dest, 'status': 'ok'})
                    except FileExistsError:
                        # try rename_on_conflict
                        dest = restore_entry(int(id_), overwrite=False, rename_on_conflict=True)
                        results.append({'id': id_, 'restored_to': dest, 'status': 'ok_renamed'})
                except Exception as e:
                    results.append({'id': id_, 'error': str(e), 'status': 'error'})
            self._send_json({'results': results})
            return
        self._send_json({'error': 'unknown api'}, status=404)

    def serve_file(self, path: Path):
        try:
            with open(path, 'rb') as f:
                data = f.read()
                self.send_response(200)
                if str(path).endswith('.html'):
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                elif str(path).endswith('.js'):
                    self.send_header('Content-Type', 'application/javascript; charset=utf-8')
                elif str(path).endswith('.css'):
                    self.send_header('Content-Type', 'text/css; charset=utf-8')
                else:
                    self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except Exception:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')


def _try_create_server(host, port):
    """Try to create ThreadingHTTPServer bound to (host, port).
    Returns server instance on success, or raises the original exception.
    """
    return ThreadingHTTPServer((host, port), OpsHandler)


def run_web(host='0.0.0.0', port=8080, daemon=False, max_tries=20):
    ensure_dirs()
    # If port is 0, let OS pick an ephemeral port
    base_port = int(port)
    server = None
    last_err = None
    for i in range(max_tries):
        try_port = base_port + i if base_port != 0 else 0
        try:
            server = _try_create_server(host, try_port)
            bound_port = server.server_address[1]
            url = f'http://{host}:{bound_port}'
            print(f'* 启动服务: {url}')
            try:
                sock = getattr(server, 'socket', None)
                if sock is not None:
                    try:
                        ac = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN)
                    except Exception:
                        ac = None
                    print(f'* server.socket: fileno={sock.fileno()} sockname={sock.getsockname()} acceptconn={ac}')
            except Exception:
                pass
            break
        except OSError as e:
            last_err = e
            # Address already in use -> try next port
            if getattr(e, 'errno', None) in (98, 48):
                # 98: EADDRINUSE on Linux, 48: EADDRINUSE on macOS
                continue
            # other errors, abort
            raise

    if server is None:
        raise RuntimeError(f'无法绑定到端口 (tried {max_tries} ports): {last_err}')

    def serve():
        try:
            print(f"* server.serve_forever running (pid={os.getpid()})")
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"* Web server thread exception: {e}")
            raise

    if daemon:
        t = threading.Thread(target=serve, daemon=True)
        t.start()
        print('* 以后台模式运行')
        return server, t

    try:
        serve()
    finally:
        server.server_close()


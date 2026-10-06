# [NEW v04] Local HTTP server for interactive.html; Python remains the single source of physics truth.
"""Serve the browser UI and expose POST /api/simulate to core.simulate."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import json
import threading
import webbrowser
from plotly.offline import get_plotlyjs
from core import ROOT
from web_bridge import browser_config, simulate_payload

MAX_BODY=1024*1024

class Handler(BaseHTTPRequestHandler):
    server_version='CFRPInteractive/0.4'

    def _headers(self,status=None,content_type=None,length=None):
        self.send_response(status or 200)
        self.send_header('Content-Type',content_type or 'application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        # [NEW v07] Same-origin UI needs no wildcard CORS. Keep file:// (Origin: null) and local-host pages usable, but block arbitrary web origins from driving the local CPU-heavy solver.
        origin=self.headers.get('Origin')
        if origin=='null' or (origin and (origin.startswith('http://127.0.0.1:') or origin.startswith('http://localhost:'))):
            self.send_header('Access-Control-Allow-Origin',origin)
            self.send_header('Vary','Origin')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS')
        if length is not None:self.send_header('Content-Length',str(length))
        self.end_headers()

    def _write(self,data=None,status=None,content_type=None):
        raw=data if isinstance(data,(bytes,bytearray)) else str(data or '').encode('utf-8')
        self._headers(status,content_type,len(raw));self.wfile.write(raw)

    def _json(self,obj=None,status=None):
        raw=json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        self._headers(status,'application/json; charset=utf-8',len(raw));self.wfile.write(raw)

    def do_OPTIONS(self):
        self._headers(204,'text/plain; charset=utf-8',0)

    def do_GET(self):
        path=self.path.split('?',1)[0]
        # [NEW v14] Independent extension routes; original assets/routes remain.
        from integrated_api_v14 import handle_get
        if handle_get(self,path):return
        if path in ('/','/interactive.html'):
            p=ROOT/'interactive.html'
            if not p.exists():return self._json({'ok':False,'error':'interactive.html not found'},404)
            return self._write(p.read_bytes(),200,'text/html; charset=utf-8')
        if path=='/preview.html':
            p=ROOT/'preview.html';return self._write(p.read_bytes(),200,'text/html; charset=utf-8') if p.exists() else self._json({'ok':False,'error':'preview.html not found'},404)
        if path=='/plotly.min.js':
            return self._write(get_plotlyjs(),200,'application/javascript; charset=utf-8')
        if path=='/api/config':
            return self._json({'ok':True,'data':browser_config()})
        if path=='/api/health':
            return self._json({'ok':True,'service':'CFRP physical-model bridge'})
        return self._json({'ok':False,'error':'Not found'},404)

    def do_POST(self):
        path=self.path.split('?',1)[0]
        # [NEW v14] Chat, measured validation, and review extensions.
        from integrated_api_v14 import handle_post
        if handle_post(self,path):return
        # [NEW v14] Apply the same local Origin rule to the original solver API.
        from integrated_api_v14 import local_origin
        if not local_origin(self):return self._json({'ok':False,'error':'허용되지 않는 웹 Origin입니다.'},403)
        if path!='/api/simulate':return self._json({'ok':False,'error':'Not found'},404)
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n<=0 or n>MAX_BODY:raise ValueError('Request body must be 1 byte to 1 MiB')
            body=json.loads(self.rfile.read(n).decode('utf-8'))
            # [NEW v17] Run synchronous calculation and I/O outside the event loop.
            import asyncio
            from async_runtime_v17 import call_sync
            data=asyncio.run(call_sync(simulate_payload, args=(body,)))
            return self._json({'ok':True,'data':data})
        except Exception as e:
            return self._json({'ok':False,'error':str(e)},400)

    def log_message(self,format=None,*args):
        print('[HTML API] '+(format or '')%args)


def run_server(host=None,port=None,open_browser=None):
    host='127.0.0.1' if host is None else str(host)
    port=8765 if port is None else int(port)
    open_browser=True if open_browser is None else bool(open_browser)
    server=ThreadingHTTPServer((host,port),Handler)
    url=f'http://{host}:{server.server_address[1]}/'
    print('CFRP interactive HTML:',url)
    if open_browser:threading.Timer(.7,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


def main():
    p=argparse.ArgumentParser(description='CFRP interactive HTML + local physics API')
    p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8765);p.add_argument('--no-open',action='store_true')
    a=p.parse_args();run_server(a.host,a.port,not a.no_open)

if __name__=='__main__':main()

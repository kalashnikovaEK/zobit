# [NEW v14] Extension routing around the original v11 HTTP server.
import json
from urllib.parse import urlparse
from core import ROOT
from llm_profiles_v14 import profiles,profile_config

# [NEW v19] Serve the independent SVG visualization extension.
ASSETS={'live_view_v19.js','chat_ui.js','temperature_view.js','stack_view_v14.js','workbench_v14.js'}

# [NEW v20] Independent physics result viewer asset.
ASSETS.add('viz3d_live_v20.js')
# [NEW v21] Independent layout extension keeps all existing API routes.
ASSETS.add('studio_layout_v21.js')

def handle_get(handler=None,path=None):
    if path.lstrip('/') in ASSETS:
        handler._write((ROOT/path.lstrip('/')).read_bytes(),200,'application/javascript; charset=utf-8')
        return True
    if path=='/api/models':
        handler._json({'ok':True,'data':profiles()})
        return True
    return False


def local_origin(handler=None):
    origin=handler.headers.get('Origin')
    if origin in (None,'null'):return True
    try:
        u=urlparse(origin)
        return u.scheme=='http' and u.hostname in ('localhost','127.0.0.1') and u.port==handler.server.server_port and not u.username and not u.password and not u.query and not u.fragment and u.path in ('','/')
    except ValueError:return False


def read_body(handler=None):
    if not local_origin(handler):raise ValueError('허용되지 않는 웹 Origin입니다.')
    n=int(handler.headers.get('Content-Length','0'))
    if not 0<n<=1024*1024:raise ValueError('요청 크기는 1 byte~1 MiB여야 합니다.')
    b=json.loads(handler.rfile.read(n).decode('utf-8'))
    if not isinstance(b,dict):raise ValueError('JSON 객체가 필요합니다.')
    return b


def handle_post(handler=None,path=None):
    # [NEW v14] Measured histories and server-bound review actions.
    if path in ('/api/measured','/api/review'):
        try:
            body=read_body(handler)
            if path=='/api/measured':
                from measured_api_v14 import reconstruct
                # [NEW v17] Offload measured calculation and serialization.
                import asyncio
                from async_runtime_v17 import call_sync
                data=asyncio.run(call_sync(reconstruct, args=(body,)))
            else:
                from review_store_v14 import record_review
                # [NEW v17] Offload review disk I/O.
                import asyncio
                from async_runtime_v17 import call_sync
                data=asyncio.run(call_sync(record_review, args=(body,)))
            handler._json({'ok':True,'data':data})
        except Exception as error:handler._json({'ok':False,'error':str(error)},400)
        return True
    if path=='/api/ai/chat':
        from chat_bridge import serve_chat
        serve_chat(handler)
        return True
    if path=='/api/model-health':
        try:
            b=read_body(handler)
            if set(b)!={'profile'}:raise ValueError('profile만 지정하십시오.')
            from AI import ollama_health
            # [NEW v17] Offload synchronous requests.get and config I/O.
            import asyncio
            from async_runtime_v17 import call_sync
            data=asyncio.run(call_sync(ollama_health, args=(profile_config(b['profile']),)))
            handler._json({'ok':True,'data':data})
        except Exception as e:handler._json({'ok':False,'error':str(e)},400)
        return True
    return False

# [NEW v22] Serve the demo display extension through the existing asset handler.
ASSETS.add('demo_view_v22.js')

# [NEW v27] Presentation assets; existing API and demo renderer remain.
ASSETS.update({'collapsible_ui_v22.js','studio_ui_v22.js','menu_ui_v23.js'})

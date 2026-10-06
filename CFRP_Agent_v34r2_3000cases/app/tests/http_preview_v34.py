# [NEW v34] Real local HTTP preview/confirm flow; only LLM extraction is mocked.
import json,sys,threading,copy
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from http.server import ThreadingHTTPServer
from interactive_server import Handler
from core import DEFAULT,LIMITS
from web_bridge import browser_config
SPEC={'action':'simulate_process','target':'balanced','material':'AS4_8552','temperature_unit':'C','condition_patch':{},'limits_patch':{},'search_variables':[],'needs_clarification':False,'clarification_question':None}
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
url='http://127.0.0.1:'+str(server.server_port)
body={'request':'현재 공정 계산','inputs':{'condition':DEFAULT,'options':browser_config()['solver_defaults'],'limits':LIMITS},'profile':'gemma2'}
try:
 assert requests.get(url+'/chat_ui.js').status_code==200
 with patch('AI.extract_request',return_value=SPEC) as llm,patch('AI.simulate',side_effect=AssertionError('premature physics')):
  r=requests.post(url+'/api/ai/chat',json=body,timeout=30)
  result=json.loads(r.text.splitlines()[-1])['data'];assert result['status']=='confirmation_required';token=result['confirmation_token']
  assert llm.call_count==1
 changed=copy.deepcopy(body);changed['inputs']['condition']['thickness']=12
 assert requests.post(url+'/api/ai/chat',json={**changed,'confirmation_token':token},timeout=30).status_code==400
 with patch('AI.extract_request',side_effect=AssertionError('interpretation repeated on confirm')):
  r=requests.post(url+'/api/ai/chat',json={**body,'confirmation_token':token},timeout=90)
  result=json.loads(r.text.splitlines()[-1])['data'];assert result['status']=='completed',result
  assert result['result_guard']['status']=='passed';assert result['display'] is not None
 assert requests.post(url+'/api/ai/chat',json={**body,'confirmation_token':token},timeout=30).status_code==400
 proof={'http_preview':True,'unconfirmed_physics_calls':0,'changed_input_rejected':True,'replayed_token_rejected':True,'confirmed_physics':'real solver','result_guard':result['result_guard']['status'],'llm':'mocked extraction; no actual Ollama'}
 (Path(__file__).resolve().parents[1]/'artifacts/http_preview_v34.json').write_text(json.dumps(proof,indent=2));print(proof)
finally:server.shutdown();server.server_close();thread.join()

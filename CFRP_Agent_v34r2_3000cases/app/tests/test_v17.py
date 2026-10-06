# [NEW v18] Same regression suite under Python 3.14.
# [NEW v17] Regression tests; real physics/HTTP, mocked LLM extraction only.
import asyncio,copy,json,os,subprocess,sys,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import AI
from AI_guard import review_results
from core import simulate,DEFAULT,LIMITS
from integrity_v14 import verify_result
from async_runtime_v17 import call_sync,run_ai_async
from measured_api_v14 import reconstruct
from web_bridge import browser_config,simulate_payload
SPEC=dict(action='simulate_process',target='minimize_time',material='AS4_8552',temperature_unit='C',condition_patch={},limits_patch={},search_variables=[],needs_clarification=False,clarification_question=None)
class Regression(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.result=simulate()
 def test_guard_none(self):
  for state,contract in [(None,None),({},None),(None,{}),({},{}),([],[])]:
   with self.subTest(state=state,contract=contract):self.assertEqual(review_results(state,contract)['status'],'blocked')
 def test_spec_guard(self):
  for request,spec in [('알루미늄 공정 분석',SPEC),('승온속도 2°C/hour로 계산',dict(SPEC,condition_patch={'ramp1':2}))]:
   with self.subTest(request=request),patch.object(AI,'simulate') as solver:
    # [NEW v17] Invalid structured interpretation may fail grounding explicitly.
    if '알루미늄' in request:
     with self.assertRaisesRegex(ValueError,'지원하지 않는 재료'):AI.run_ai(request=request,spec=spec)
    if 'hour' in request:self.assertEqual(AI.run_ai(request=request,spec=spec)['status'],'needs_clarification')
    solver.assert_not_called()
 def test_spec_grounding(self):
  with patch.object(AI,'simulate') as solver:
   with self.assertRaisesRegex(ValueError,'명시하지 않은 숫자'):AI.run_ai(request='현재 공정 분석',spec=dict(SPEC,condition_patch={'T1':112}))
   solver.assert_not_called()
 def test_missing_calculation(self):
  with patch.object(AI,'simulate',return_value=None):
   with self.assertRaisesRegex(ValueError,'unexpected None'):AI.run_ai(request='현재 공정 분석',spec=SPEC)
  with patch('web_bridge.simulate',return_value=None):
   with self.assertRaisesRegex(ValueError,'unexpected None'):simulate_payload({})
  with patch('core._solve_tool',return_value=None):
   with self.assertRaisesRegex(ValueError,'unexpected None'):simulate()
 def test_measured_null(self):
  r=reconstruct({'inputs':{},'boundary_history':[[0,25,25],[1,60,55]]})
  self.assertIsNone(r['summary']['cycle_time']);self.assertEqual(r['result_guard']['status'],'passed');json.dumps(r,allow_nan=False)
 def test_integrity(self):
  verify_result(self.result)
  for key in ['T_tool','T_part_top_surface','T_part_bottom_surface','T_tool_interface_surface','T_tool_outer_surface','q_contact']:
   r=copy.deepcopy(self.result);r[key].flat[0]=np.nan
   with self.subTest(key=key),self.assertRaises(ValueError):verify_result(r)
  for key in ['Tmax','delta_Tmax','tool_Tmax','interface_delta_Tmax','contact_flux_abs_max']:
   r=copy.deepcopy(self.result);r['summary'][key]=-1
   with self.subTest(key=key),self.assertRaises(ValueError):verify_result(r)
 def test_bad_options(self):
  for options in [{'nzz':31},{'nz':31.5},{'heat_scale':-1}]:
   with self.subTest(options=options),self.assertRaises(ValueError):simulate(options=options)
 def test_async_offload(self):
  async def check():
   parent=threading.get_ident();ticks=[]
   def sync():time.sleep(.08);return threading.get_ident()
   task=asyncio.create_task(call_sync(sync))
   while not task.done():ticks.append(time.perf_counter());await asyncio.sleep(.005)
   self.assertNotEqual(await task,parent);self.assertGreater(len(ticks),5)
   with self.assertRaisesRegex(ValueError,'unexpected None'):await call_sync(lambda:None)
   ids=[]
   def transport(payload):ids.append(threading.get_ident());return {'message':{'content':json.dumps(SPEC)}}
   state=await run_ai_async(request='현재 공정 분석',transport=transport)
   self.assertEqual(state['result_guard']['status'],'passed');self.assertTrue(all(i!=parent for i in ids))
  asyncio.run(check())
 def test_native_failure_fallback(self):
  import runtime_v17
  with patch.dict(os.environ,{'CFRP_DISABLE_NUMBA':'0'}),patch('runtime_v17.subprocess.run',return_value=subprocess.CompletedProcess([],-11,'','test crash')):
   selected=runtime_v17.select_njit();self.assertEqual(runtime_v17.STATUS['backend'],'python');self.assertIs(selected,runtime_v17.python_njit)
 def test_training_optimization(self):
  cfg=AI.load_config({'candidate_count':16,'top_k':2,'max_feedback_rounds':1})
  r=AI.run_ai(request='공정시간 최소화 최적화',spec=dict(SPEC,action='optimize_cycle'),config=cfg)
  self.assertIn(r['status'],('completed','no_feasible_candidate'));self.assertEqual(r['result_guard']['status'],'passed');self.assertGreater(r['optimization']['rechecked'],0)
 # [NEW v19] Launcher orchestration is mocked independently of host Python version.
 @patch('sys.version_info',(3,14,0))
 @patch('sysconfig.get_config_var',return_value=None)
 def test_windows_bootstrap_orchestration(self,config_probe=None):
  import tempfile
  import windows_launcher_v17 as launcher
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'requirements-windows-py314-v18.txt').write_text('requests==2.34.2')
   (root/'.venv_windows_py314_v18/Scripts').mkdir(parents=True)
   (root/'.venv_windows_py314_v18/Scripts/python.exe').touch()
   with patch.object(launcher,'ROOT',root),patch.object(launcher.os,'name','nt'),patch.object(launcher,'logged_run',return_value=0) as run,patch.object(launcher.subprocess,'call',return_value=0) as server:
    self.assertEqual(launcher.main(),0);self.assertEqual(run.call_count,2);server.assert_called_once()
    self.assertTrue((root/'.venv_windows_py314_v18/ready_v18.txt').is_file())
   with patch.object(launcher,'ROOT',root),patch.object(launcher.os,'name','nt'),patch.object(launcher,'logged_run',return_value=1),patch.object(launcher.subprocess,'call') as server:
    self.assertEqual(launcher.main(),1);server.assert_not_called()
    self.assertFalse((root/'.venv_windows_py314_v18/ready_v18.txt').exists())
 def test_http_routes(self):
  import requests
  from http.server import ThreadingHTTPServer
  from interactive_server import Handler
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever,daemon=True);t.start();url='http://127.0.0.1:'+str(server.server_port)
  try:
   for path in ['/','/api/config','/api/models','/chat_ui.js','/workbench_v14.js']:self.assertEqual(requests.get(url+path,timeout=10).status_code,200)
   self.assertTrue(requests.post(url+'/api/simulate',json={},timeout=60).json()['ok'])
   r=requests.post(url+'/api/measured',json={'inputs':{},'boundary_history':[[0,25,25],[1,60,55]]},timeout=60).json();self.assertTrue(r['ok']);self.assertIsNone(r['data']['summary']['cycle_time'])
   with patch.object(AI,'extract_request',return_value=SPEC):
    inputs={'condition':DEFAULT,'options':browser_config()['solver_defaults'],'limits':LIMITS}
    r=requests.post(url+'/api/ai/chat',json={'request':'현재 공정 분석','inputs':inputs},timeout=60)
    # [NEW v34] Exercise mandatory preview, then preserve the original result assertions.
    first=json.loads(r.text.splitlines()[-1])['data']
    if first['status']=='confirmation_required':
     r=requests.post(url+'/api/ai/chat',json={'request':'현재 공정 분석','inputs':inputs,'confirmation_token':first['confirmation_token']},timeout=60)
    items=[json.loads(line) for line in r.text.splitlines()];self.assertEqual(items[-1]['type'],'result');self.assertEqual(items[-1]['data']['result_guard']['status'],'passed')
  finally:server.shutdown();server.server_close();t.join()
if __name__=='__main__':unittest.main(verbosity=2)

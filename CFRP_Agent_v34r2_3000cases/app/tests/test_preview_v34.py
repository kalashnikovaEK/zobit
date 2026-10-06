# [NEW v34] Integration tests for extraction, mandatory preview and frozen tokens.
import sys,json,copy,unittest,asyncio
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from AI import run_ai,extract_request,load_config
from request_preview_v34 import issue_preview,consume_preview
from async_runtime_v17 import run_ai_async

SPEC={'action':'simulate_process','target':'balanced','material':'AS4_8552','temperature_unit':'C','condition_patch':{},'limits_patch':{},'search_variables':[],'needs_clarification':False,'clarification_question':None}
class PreviewTests(unittest.TestCase):
 def test_preview_no_solver_or_training(self):
  with patch('AI.simulate',side_effect=AssertionError('physics before confirmation')),patch('surrogate_store_v24.get_trained_bundle_v24',side_effect=AssertionError('model before confirmation')):
   r=asyncio.run(run_ai_async(request='현재 공정 계산',spec=SPEC,preview_only=True))
  self.assertEqual(r['status'],'confirmation_required')
 def test_token_bound_one_use(self):
  body={'request':'현재 공정 계산','inputs':{'a':1},'profile':'gemma2'}
  t=issue_preview(body,SPEC)
  with self.assertRaises(ValueError):consume_preview({**body,'request':'변경'},t)
  self.assertEqual(consume_preview(body,t),SPEC)
  with self.assertRaises(ValueError):consume_preview(body,t)
 def test_expired(self):
  t=issue_preview({},SPEC)
  with patch('request_preview_v34.time.monotonic',return_value=10**20):
   with self.assertRaises(ValueError):consume_preview({},t)
 def test_bad_json_schema(self):
  s={**SPEC,'search_variables':['pressure']}
  with self.assertRaises(ValueError):extract_request('현재 공정 계산',transport=lambda p:{'message':{'content':json.dumps(s)}},config={'json_retries':0})
 def test_bad_number(self):
  s={**SPEC,'condition_patch':{'thickness':float('nan')}}
  with self.assertRaises(ValueError):run_ai('두께 10mm 계산',spec=s)
 def test_bad_range(self):
  s={**SPEC,'condition_patch':{'thickness':100}}
  with self.assertRaises(ValueError):run_ai('두께 100mm 계산',spec=s)
 def test_units(self):
  s={**SPEC,'condition_patch':{'ramp1':2}}
  self.assertEqual(run_ai('1차 승온속도 2도/hour 계산',spec=s,preview_only=True)['status'],'needs_clarification')
 def test_confirmed_physics_result_guard(self):
  cfg=load_config({'solver_options':{'nz':5,'tool_nz':3,'dt':10,'save_seconds':600}})
  r=run_ai('현재 공정 계산',spec=SPEC, config=cfg)
  self.assertEqual(r['status'],'completed');self.assertEqual(r['result_guard']['status'],'passed')
  from AI_guard import review_results
  bad=copy.deepcopy(r);bad['physical']['T'][0,0]=float('nan')
  self.assertEqual(review_results(bad,r['execution_contract'])['status'],'blocked')
 def test_comma_change_fixed_scope(self):
  from request_semantics_v33 import interpretation_context,review
  q='2차 승온속도만 조절해서 최고온도를 최소화해줘, 유지시간과 유지온도는 바꾸지 마'
  ev,s=interpretation_context(q);self.assertFalse(ev['issues']);self.assertEqual(s['search_variables'],['ramp2'])
  bad=copy.deepcopy(s);bad['search_variables']=['ramp1'];self.assertEqual(review(q,bad)['status'],'needs_review')
 def test_joint_comma_stages_preserved(self):
  from request_semantics_v33 import interpretation_context
  ev,s=interpretation_context('1차, 2차 유지시간만 조절해서 온도편차 최소화')
  self.assertFalse(ev['issues']);self.assertEqual(set(s['search_variables']),{'hold1','hold2'})
 def test_decimal_comma_preserved(self):
  from request_semantics_v33 import interpretation_context
  ev,s=interpretation_context('1차 유지온도 110,0도 계산')
  self.assertFalse(ev['issues']);self.assertEqual(s['condition_patch']['T1'],110)
 def test_negated_constraint_blocks_before_llm(self):
  q='최고온도 200도 이하는 아니고 이상으로 공정시간 최소화'
  with patch('AI.simulate',side_effect=AssertionError('solver')),patch('AI.requests.post',side_effect=AssertionError('LLM must not be called')):
   r=run_ai(q,preview_only=True)
  self.assertEqual(r['status'],'needs_clarification')
if __name__=='__main__':unittest.main(verbosity=2)

# [NEW v24r1] New store integrity, fallback, automatic loading and real physics rechecks.
import asyncio,copy,json,shutil,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import ROOT,TARGETS
from surrogate_store_v24r1 import STORE,load_bundle_v24r1,get_trained_bundle_v24r1
from surrogate_store_v24 import get_trained_bundle_v24
from async_runtime_v17 import run_ai_async
from AI import load_config
SPEC={'action':'predict_process','target':'minimize_time','material':'AS4_8552','temperature_unit':'C','condition_patch':{},'limits_patch':{},'search_variables':[],'needs_clarification':False,'clarification_question':None}

class Expanded3000Tests(unittest.TestCase):
    def test_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.assertIsNone(load_bundle_v24r1(path=p))
            for name in ['manifest.json','forest_arrays.npz']:shutil.copyfile(STORE/name,p/name)
            original=(p/'manifest.json').read_text();m=json.loads(original);m['expanded_dataset_sha256']='bad'
            (p/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'fingerprint mismatch'):load_bundle_v24r1(path=p)
            (p/'manifest.json').write_text(original)
            with (p/'forest_arrays.npz').open('ab') as f:f.write(b'corrupt')
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):load_bundle_v24r1(path=p)
    def test_explicit_and_fallback(self):
        old=get_trained_bundle_v24()
        with patch('surrogate_store_v24r1.get_trained_bundle_v24r1',side_effect=AssertionError('explicit replaced')),patch('AI.run_ai',return_value={'ok':True}) as runner:
            asyncio.run(run_ai_async(bundle=old));self.assertIs(runner.call_args.kwargs['bundle'],old)
        with patch('surrogate_store_v24r1.get_trained_bundle_v24r1',return_value=None),patch('AI.run_ai',return_value={'ok':True}) as runner:
            asyncio.run(run_ai_async());self.assertEqual(runner.call_args.kwargs['bundle']['report']['final_fit_rows'],700)
    def test_auto_loaded_prediction(self):
        events=[]
        with patch('pipeline.train_surrogate',side_effect=AssertionError('unexpected training')):
            s=asyncio.run(run_ai_async(request='현재 공정 예측',spec=SPEC,event_sink=events.append))
        self.assertEqual(s['result_guard']['status'],'passed')
        self.assertTrue(any(e.get('detail',{}).get('fit_rows')==3000 for e in events))
        self.assertIs(get_trained_bundle_v24r1(),get_trained_bundle_v24r1())
    def test_three_objectives_actual_physics(self):
        proof=[]
        for target,request in [('minimize_time','공정시간 최소화 최적화'),('minimize_peak','최고온도 최소화 최적화'),('minimize_spread','온도편차 최소화 최적화')]:
            with self.subTest(target=target):
                events=[]
                with patch('pipeline.train_surrogate',side_effect=AssertionError('unexpected training')):
                    s=asyncio.run(run_ai_async(request=request,spec=dict(SPEC,action='optimize_cycle',target=target),config=load_config({'candidate_count':256,'top_k':4,'max_feedback_rounds':1}),event_sink=events.append))
                self.assertIn(s['status'],('completed','no_feasible_candidate'))
                self.assertEqual(s['result_guard']['status'],'passed');self.assertGreater(s['optimization']['rechecked'],0)
                self.assertTrue(any(e.get('detail',{}).get('fit_rows')==3000 for e in events))
                for item in s['optimization']['recommendations']:
                    self.assertEqual(item['actual'],{k:item['result']['summary'][k] for k in item['actual']})
                proof.append({'target':target,'status':s['status'],'result_guard':s['result_guard']['status'],'physics_rechecked':s['optimization']['rechecked'],'recommendations':len(s['optimization']['recommendations']),'fit_rows':3000,'llm_inference':False})
        (STORE/'agent_integration_v24r1.json').write_text(json.dumps(proof,indent=2))

if __name__=='__main__':unittest.main(verbosity=2)

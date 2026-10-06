# [NEW v24] Expanded-data integrity and actual 700-case Agent execution.
import asyncio,json,shutil,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import ROOT,FEATURES,DEFAULT
from surrogate_store_v24 import STORE,DATASET,get_trained_bundle_v24,load_bundle_v24
from surrogate_store_v23 import get_trained_bundle_v23
from async_runtime_v17 import run_ai_async
from AI import load_config
SPEC={'action':'predict_process','target':'minimize_time','material':'AS4_8552','temperature_unit':'C','condition_patch':{},'limits_patch':{},'search_variables':[],'needs_clarification':False,'clarification_question':None}

class ExpandedModelTests(unittest.TestCase):
    def test_700_rows_unique_groups_and_cache(self):
        data=pd.read_csv(DATASET);original=pd.read_csv(ROOT/'artifacts/development_cases.csv')
        self.assertEqual(len(data),700);self.assertEqual(data.group.nunique(),175)
        self.assertFalse(data.duplicated(FEATURES).any())
        np.testing.assert_allclose(data.iloc[:256][FEATURES].to_numpy(),original[FEATURES].to_numpy())
        bundle=get_trained_bundle_v24();self.assertIs(bundle,get_trained_bundle_v24())
        self.assertEqual(bundle['report']['final_fit_rows'],700)
        report=bundle['report'];self.assertFalse(set(report['train_groups'])&set(report['test_groups']))
        self.assertEqual(report['train_rows']+report['test_rows'],700)
        self.assertEqual(get_trained_bundle_v23()['report']['final_fit_rows'],256)

    def test_integrity_and_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);self.assertIsNone(load_bundle_v24(path=path))
            for name in ['manifest.json','forest_arrays.npz']:shutil.copyfile(STORE/name,path/name)
            text=(path/'manifest.json').read_text();m=json.loads(text)
            m['expanded_dataset_sha256']='stale';(path/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'Expanded dataset fingerprint'):load_bundle_v24(path=path)
            (path/'manifest.json').write_text(text)
            with (path/'forest_arrays.npz').open('ab') as stream:stream.write(b'corrupt')
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):load_bundle_v24(path=path)

    def test_explicit_bundle_bypasses_auto_load(self):
        bundle=get_trained_bundle_v23()
        with patch('surrogate_store_v24.get_trained_bundle_v24',side_effect=AssertionError('explicit bundle replaced')),patch('AI.run_ai',return_value={'status':'explicit'}) as runner:
            self.assertEqual(asyncio.run(run_ai_async(bundle=bundle)),{'status':'explicit'})
            self.assertIs(runner.call_args.kwargs['bundle'],bundle)

    # [NEW v34r1] Isolate legacy 700-case fallback; new default is tested separately.
    @patch('surrogate_store_v24r1.get_trained_bundle_v24r1', lambda event_sink=None: None)
    def test_700_prediction_actual_async_physics(self):
        events=[]
        with patch('pipeline.train_surrogate',side_effect=AssertionError('unexpected retraining')):
            state=asyncio.run(run_ai_async(request='현재 공정 예측',spec=SPEC,event_sink=events.append))
        self.assertEqual(state['status'],'completed');self.assertEqual(state['result_guard']['status'],'passed')
        self.assertTrue(any(e['phase']=='surrogate_loading' and e['detail']['fit_rows']==700 for e in events))
        proof={'status':state['status'],'result_guard':state['result_guard']['status'],'fit_rows':700,'actual_physics':True,'llm_inference':'structured request supplied','external_validation_passed':False}
        (ROOT/'artifacts/predict_agent_v24.json').write_text(json.dumps(proof,indent=2))

    # [NEW v34r1] Isolate legacy 700-case fallback; new default is tested separately.
    @patch('surrogate_store_v24r1.get_trained_bundle_v24r1', lambda event_sink=None: None)
    def test_700_optimizer_actual_physics(self):
        spec=dict(SPEC,action='optimize_cycle');events=[]
        with patch('pipeline.train_surrogate',side_effect=AssertionError('unexpected retraining')):
            state=asyncio.run(run_ai_async(request='공정시간 최소화 최적화',spec=spec,config=load_config({'candidate_count':64,'top_k':2,'max_feedback_rounds':1}),event_sink=events.append))
        self.assertIn(state['status'],('completed','no_feasible_candidate'));self.assertEqual(state['result_guard']['status'],'passed')
        self.assertGreater(state['optimization']['rechecked'],0)
        self.assertTrue(any(e['phase']=='surrogate_loading' and e['detail']['fit_rows']==700 for e in events))
        for item in state['optimization']['recommendations']:self.assertEqual(item['actual'],{k:item['result']['summary'][k] for k in item['actual']})
        proof={'status':state['status'],'result_guard':state['result_guard']['status'],'fit_rows':700,'physics_rechecked':state['optimization']['rechecked'],'recommendations':len(state['optimization']['recommendations']),'llm_inference':'structured request supplied','external_validation_passed':False}
        (ROOT/'artifacts/optimizer_agent_v24.json').write_text(json.dumps(proof,indent=2))

if __name__=='__main__':unittest.main(verbosity=2)

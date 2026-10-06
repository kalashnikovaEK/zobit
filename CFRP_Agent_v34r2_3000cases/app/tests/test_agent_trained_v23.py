# [NEW v23] Full optimizer path with the persisted portable model and real physics.
import asyncio,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from async_runtime_v17 import run_ai_async
from AI import load_config

class TrainedOptimizerTests(unittest.TestCase):
    def test_saved_model_optimizer_rechecks_physics(self):
        spec={'action':'optimize_cycle','target':'minimize_time','material':'AS4_8552','temperature_unit':'C','condition_patch':{},'limits_patch':{},'search_variables':[],'needs_clarification':False,'clarification_question':None}
        events=[]
        with patch('pipeline.train_surrogate',side_effect=AssertionError('unexpected retraining')):
            state=asyncio.run(run_ai_async(request='공정시간 최소화 최적화',spec=spec,config=load_config({'candidate_count':64,'top_k':2,'max_feedback_rounds':1}),event_sink=events.append))
        self.assertIn(state['status'],('completed','no_feasible_candidate'))
        self.assertEqual(state['result_guard']['status'],'passed')
        self.assertGreater(state['optimization']['rechecked'],0)
        self.assertTrue(any(e['phase']=='surrogate_loading' for e in events))
        for item in state['optimization']['recommendations']:self.assertEqual(item['actual'],{key:item['result']['summary'][key] for key in item['actual']})
        proof={'status':state['status'],'result_guard':state['result_guard']['status'],'physics_rechecked':state['optimization']['rechecked'],'recommendations':len(state['optimization']['recommendations']),'loaded_pretrained':True,'llm_inference':'not run; structured request supplied','external_validation_passed':False}
        (Path(__file__).resolve().parents[1]/'artifacts/trained_optimizer_v23.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')

if __name__=='__main__':unittest.main(verbosity=2)

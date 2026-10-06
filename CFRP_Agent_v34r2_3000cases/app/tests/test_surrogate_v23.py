# [NEW v23] Saved-model integrity, reuse and actual async Agent integration.
import asyncio
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import DEFAULT,TARGETS
from pipeline import predict_batch
from surrogate_store_v23 import STORE,load_bundle_v23,get_trained_bundle_v23
from async_runtime_v17 import run_ai_async

SPEC={'action':'predict_process','target':'minimize_time','material':'AS4_8552','temperature_unit':'C','condition_patch':{},'limits_patch':{},'search_variables':[],'needs_clarification':False,'clarification_question':None}

class SavedModelTests(unittest.TestCase):
    def test_prediction_and_cache(self):
        first=get_trained_bundle_v23();second=get_trained_bundle_v23()
        self.assertIs(first,second)
        prediction=predict_batch(conditions=[DEFAULT],bundle=first)
        self.assertEqual(prediction.shape,(1,len(TARGETS)))
        self.assertTrue(np.isfinite(prediction).all())
        self.assertEqual(first['report']['final_fit_rows'],256)

    def test_missing_model_is_optional(self):
        with tempfile.TemporaryDirectory() as path:self.assertIsNone(load_bundle_v23(path=path))

    def test_corrupt_and_stale_models_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            for name in ['forest_arrays.npz','manifest.json']:shutil.copyfile(STORE/name,path/name)
            original=(path/'manifest.json').read_text()
            manifest=json.loads(original);manifest['dataset_sha256']='wrong';(path/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'fingerprint mismatch'):load_bundle_v23(path=path)
            (path/'manifest.json').write_text(original)
            with (path/'forest_arrays.npz').open('ab') as stream:stream.write(b'corrupt')
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):load_bundle_v23(path=path)

    def test_async_agent_uses_saved_model_without_training(self):
        events=[]
        with patch('pipeline.train_surrogate',side_effect=AssertionError('unexpected retraining')):
            state=asyncio.run(run_ai_async(request='현재 공정 예측',transport=lambda payload:{'message':{'content':json.dumps(SPEC)}},event_sink=events.append))
        self.assertEqual(state['status'],'completed')
        self.assertEqual(state['result_guard']['status'],'passed')
        self.assertTrue(any(event['phase']=='surrogate_loading' for event in events))
        self.assertIn('predict_process',state['results'])
        self.assertFalse(any(event['phase']=='surrogate_training' for event in events))

if __name__=='__main__':unittest.main(verbosity=2)

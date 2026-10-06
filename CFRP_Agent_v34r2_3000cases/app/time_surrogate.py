# [NEW v01] Learn only cooling lag; exact commanded duration is not approximated by a tree.
import json
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestRegressor

# [NEW v03] Keep the analytical schedule synchronized with config instead of duplicating 25/60/3 literals.
_CONFIG=json.loads((Path(__file__).resolve().parent/'config/material.json').read_text(encoding='utf-8'))

def scheduled_duration(X=None):
    T0=float(_CONFIG['initial']['temperature_c']);release=float(_CONFIG['initial']['release_temperature_c']);cool=float(_CONFIG['initial']['cool_rate'])
    return ((X['T1']-T0)/X['ramp1']+X['hold1']+(X['T2']-X['T1'])/X['ramp2']+X['hold2']+(X['T2']-release)/cool).to_numpy()

class CycleTimeSurrogate:
    def __init__(self):
        self.model=RandomForestRegressor(n_estimators=160,min_samples_leaf=1,random_state=42,n_jobs=1)
    def fit(self,X=None,y=None):
        self.model.fit(X,np.asarray(y)-scheduled_duration(X));return self
    def predict(self,X=None):
        return scheduled_duration(X)+self.model.predict(X)

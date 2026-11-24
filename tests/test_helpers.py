import numpy as np
import pandas as pd

from ml.train_rul_model import nasa_score
from pipeline.export_powerbi_extract import engine_key, health_status


def test_engine_key_matches_sql_function():
    # same format as STAGING.FN_ENGINE_KEY
    df = pd.DataFrame({"fleet_id": ["FD001", "FD004"], "dataset_split": ["train", "test"], "unit_number": [7, 248]})
    assert engine_key(df).tolist() == ["FD001-TRAIN-007", "FD004-TEST-248"]


def test_health_bands():
    rul = pd.Series([0, 30, 31, 75, 76])
    assert list(health_status(rul)) == ["Critical", "Critical", "Warning", "Warning", "Healthy"]


def test_nasa_score_penalizes_late_predictions_more():
    assert nasa_score(np.array([0.0])) == 0
    assert nasa_score(np.array([10.0])) > nasa_score(np.array([-10.0]))

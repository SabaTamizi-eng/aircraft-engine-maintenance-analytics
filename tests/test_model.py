import numpy as np
import pandas as pd

from ml.train_rul_model import add_conditions, add_features, normalize
from pipeline.config import OP_SETTINGS, SENSORS


def make_engine_frame(n_cycles: int = 30) -> pd.DataFrame:
    df = pd.DataFrame({"unit_number": 1, "cycle": np.arange(1, n_cycles + 1)})
    for col in OP_SETTINGS + SENSORS:
        df[col] = 0.0
    return df


def test_slope_feature_recovers_linear_trend():
    df = make_engine_frame()
    df["sensor_2"] = 2.0 * df["cycle"] + 1.0
    out, features = add_features(df, ["sensor_2"])
    assert "sensor_2_slope" in features
    assert np.isclose(out["sensor_2_slope"].iloc[-1], 2.0)
    assert np.isclose(out["sensor_2_mean5"].iloc[-1], out["sensor_2"].iloc[-5:].mean())


def test_single_condition_fleet_gets_one_label():
    train, test = make_engine_frame(), make_engine_frame()
    add_conditions(train, test, 1)
    assert (train["condition"] == 0).all() and (test["condition"] == 0).all()


def test_normalize_removes_condition_offset_and_drops_constant_sensors():
    rng = np.random.default_rng(0)
    train = make_engine_frame(200)
    train["condition"] = np.repeat([0, 1], 100)
    # same noise in both conditions, but condition 1 reads 50 units higher
    train["sensor_2"] = rng.normal(0, 1, 200) + np.where(train["condition"] == 1, 50.0, 0.0)
    test = train.copy()

    kept = normalize(train, test)

    assert kept == ["sensor_2"]   # every other sensor is constant
    by_condition = train.groupby("condition")["sensor_2"].mean()
    assert np.allclose(by_condition, 0.0, atol=1e-9)

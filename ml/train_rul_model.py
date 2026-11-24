"""Baseline RUL model for FD001.

Trained on the run-to-failure engines, evaluated on each test engine's last cycle
(the usual C-MAPSS setup). Writes data/processed/rul_predictions.csv and
ml/metrics_fd001.json.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from pipeline.config import PREDICTION_COLUMNS, PROCESSED_DIR
from pipeline.transform import read_cycles, read_rul_truth

FLEET = "FD001"
MODEL_NAME = "random_forest_baseline"
MODEL_VERSION = "1.0"
RUL_CAP = 125      # little degradation early on, so the target is capped
WINDOW = 10        # rolling mean window (cycles)
RANDOM_STATE = 42

# the other 7 sensors are constant in FD001
FEATURE_SENSORS = [f"sensor_{i}" for i in (2, 3, 4, 7, 8, 9, 11, 12, 13, 14, 15, 17, 20, 21)]


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["unit_number", "cycle"]).copy()
    rolling = (
        df.groupby("unit_number")[FEATURE_SENSORS]
        .rolling(WINDOW, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )
    df[[f"{s}_mean{WINDOW}" for s in FEATURE_SENSORS]] = rolling[FEATURE_SENSORS].to_numpy()
    return df


def feature_columns() -> list[str]:
    return ["cycle"] + FEATURE_SENSORS + [f"{s}_mean{WINDOW}" for s in FEATURE_SENSORS]


def nasa_score(errors: np.ndarray) -> float:
    # PHM08 score: late predictions cost more than early ones
    return float(np.sum(np.where(errors < 0, np.exp(-errors / 13) - 1, np.exp(errors / 10) - 1)))


def main() -> None:
    train = add_features(read_cycles(FLEET, "train"))
    train["rul"] = (train.groupby("unit_number")["cycle"].transform("max") - train["cycle"]).clip(upper=RUL_CAP)

    test = add_features(read_cycles(FLEET, "test"))
    last = test.groupby("unit_number").tail(1).sort_values("unit_number")
    true_rul = read_rul_truth(FLEET).to_numpy()

    model = RandomForestRegressor(
        n_estimators=300, min_samples_leaf=4, max_features=0.33, n_jobs=-1, random_state=RANDOM_STATE
    )
    model.fit(train[feature_columns()], train["rul"])
    predicted = model.predict(last[feature_columns()])
    errors = predicted - true_rul

    metrics = {
        "fleet": FLEET,
        "model": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "test_engines": int(len(last)),
        "rmse_cycles": round(float(np.sqrt(mean_squared_error(true_rul, predicted))), 2),
        "mae_cycles": round(float(mean_absolute_error(true_rul, predicted)), 2),
        "nasa_score": round(nasa_score(errors), 1),
        "share_within_20_cycles": round(float(np.mean(np.abs(errors) <= 20)), 3),
        "notes": f"Target capped at {RUL_CAP} cycles; evaluated against NASA's true RUL (uncapped).",
    }

    predictions = last[["fleet_id", "dataset_split", "unit_number", "cycle"]].copy()
    predictions["predicted_rul"] = predicted.round(1)
    predictions["model_name"] = MODEL_NAME
    predictions["model_version"] = MODEL_VERSION
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    predictions[PREDICTION_COLUMNS].to_csv(PROCESSED_DIR / "rul_predictions.csv", index=False)

    metrics_path = Path(__file__).with_name("metrics_fd001.json")
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

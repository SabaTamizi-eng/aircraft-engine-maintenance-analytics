"""RUL model for all four fleets.

Per fleet: sensors are normalised within each operating condition, trend features are
added, and a LightGBM model is trained on the run-to-failure engines. Model settings are
picked with grouped cross-validation on the training engines only; the test engines are
used once, for the final scores (each test engine scored at its last cycle, the usual
C-MAPSS setup). Writes data/processed/rul_predictions.csv and ml/metrics.json.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.cluster import KMeans
from sklearn.model_selection import GroupKFold

from pipeline.config import FLEETS, OP_SETTINGS, PREDICTION_COLUMNS, PROCESSED_DIR, SENSORS
from pipeline.transform import read_cycles, read_rul_truth

MODEL_NAME = "lightgbm"
MODEL_VERSION = "2.0"
RUL_CAP = 125          # little degradation early on, so the target is capped
RANDOM_STATE = 42
CONDITIONS = {"FD001": 1, "FD002": 6, "FD003": 1, "FD004": 6}
MEAN_WINDOWS = (5, 15, 30)
SLOPE_WINDOW = 20
PARAM_GRID = [
    {"n_estimators": 500, "learning_rate": 0.03, "num_leaves": 7, "min_child_samples": 50},
    {"n_estimators": 700, "learning_rate": 0.03, "num_leaves": 15, "min_child_samples": 80},
    {"n_estimators": 900, "learning_rate": 0.02, "num_leaves": 31, "min_child_samples": 120},
]


def add_conditions(train: pd.DataFrame, test: pd.DataFrame, n_conditions: int) -> None:
    """Label each cycle with its operating condition (FD002/FD004 fly in six)."""
    if n_conditions == 1:
        train["condition"], test["condition"] = 0, 0
        return
    mean, std = train[OP_SETTINGS].mean(), train[OP_SETTINGS].std()
    km = KMeans(n_clusters=n_conditions, n_init=10, random_state=RANDOM_STATE)
    train["condition"] = km.fit_predict((train[OP_SETTINGS] - mean) / std)
    test["condition"] = km.predict((test[OP_SETTINGS] - mean) / std)


def normalize(train: pd.DataFrame, test: pd.DataFrame) -> list[str]:
    """z-score each sensor within its operating condition, using training statistics.
    Returns the sensors that still vary (the rest carry no signal)."""
    stats = train.groupby("condition")[SENSORS].agg(["mean", "std"])
    for df in (train, test):
        mean = stats.xs("mean", axis=1, level=1).loc[df["condition"]].to_numpy()
        std = stats.xs("std", axis=1, level=1).loc[df["condition"]].replace(0, np.nan).to_numpy()
        df[SENSORS] = np.nan_to_num((df[SENSORS].to_numpy() - mean) / std)
    return [s for s in SENSORS if train[s].std() > 1e-3]


def add_features(df: pd.DataFrame, sensors: list[str]) -> tuple[pd.DataFrame, list[str]]:
    df = df.sort_values(["unit_number", "cycle"]).reset_index(drop=True)
    by_unit = df.groupby("unit_number")
    feats = {"cycle": df["cycle"]}
    for w in MEAN_WINDOWS:
        rolled = by_unit[sensors].rolling(w, min_periods=1).mean().reset_index(level=0, drop=True)
        feats.update({f"{s}_mean{w}": rolled[s] for s in sensors})
    rolled_std = by_unit[sensors].rolling(15, min_periods=2).std().reset_index(level=0, drop=True).fillna(0)
    feats.update({f"{s}_std15": rolled_std[s] for s in sensors})
    for s in sensors:
        feats[f"{s}_ewm"] = by_unit[s].transform(lambda x: x.ewm(alpha=0.1).mean())

    # slope of each sensor over the last SLOPE_WINDOW cycles (least squares, from rolling sums)
    t = df["cycle"].astype(float)
    helper = pd.DataFrame({"unit_number": df["unit_number"], "t": t, "tt": t * t})
    for s in sensors:
        helper[f"x_{s}"] = df[s]
        helper[f"tx_{s}"] = t * df[s]
    sums = (helper.groupby("unit_number").rolling(SLOPE_WINDOW, min_periods=2).sum()
            .reset_index(level=0, drop=True))
    n = by_unit["cycle"].rolling(SLOPE_WINDOW, min_periods=2).count().reset_index(level=0, drop=True)
    denom = (n * sums["tt"] - sums["t"] ** 2).replace(0, np.nan)
    for s in sensors:
        feats[f"{s}_slope"] = ((n * sums[f"tx_{s}"] - sums["t"] * sums[f"x_{s}"]) / denom).fillna(0)

    features = pd.DataFrame(feats).drop(columns="cycle")
    return pd.concat([df, features], axis=1), ["cycle"] + list(features.columns)


def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2)))


def nasa_score(errors: np.ndarray) -> float:
    # PHM08 score: late predictions cost more than early ones
    return float(np.sum(np.where(errors < 0, np.exp(-errors / 13) - 1, np.exp(errors / 10) - 1)))


def choose_params(train: pd.DataFrame, features: list[str]) -> tuple[dict, float]:
    """Grouped 5-fold CV on the training engines (an engine never sits in both halves)."""
    scores = []
    for params in PARAM_GRID:
        fold_scores = []
        for fit_idx, val_idx in GroupKFold(n_splits=5).split(train, groups=train["unit_number"]):
            model = LGBMRegressor(**params, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                                  random_state=RANDOM_STATE, verbose=-1)
            model.fit(train.loc[fit_idx, features], train.loc[fit_idx, "rul"])
            pred = np.clip(model.predict(train.loc[val_idx, features]), 0, RUL_CAP)
            fold_scores.append(rmse(train.loc[val_idx, "rul"], pred))
        scores.append(float(np.mean(fold_scores)))
    best = int(np.argmin(scores))
    return PARAM_GRID[best], scores[best]


def summarize(predicted: np.ndarray, truth: np.ndarray) -> dict:
    errors = predicted - truth
    near = truth <= RUL_CAP
    return {
        "rmse_cycles": round(rmse(predicted, truth), 2),
        "mae_cycles": round(float(np.mean(np.abs(errors))), 2),
        "share_within_20_cycles": round(float(np.mean(np.abs(errors) <= 20)), 3),
        "nasa_score": round(nasa_score(errors), 1),
        # engines that can actually be told apart: RUL within the cap
        "rmse_near_failure_cycles": round(rmse(predicted[near], truth[near]), 2),
        "share_within_20_near_failure": round(float(np.mean(np.abs(errors[near]) <= 20)), 3),
        # the convention most papers use for this dataset
        "rmse_vs_capped_truth_cycles": round(rmse(predicted, np.minimum(truth, RUL_CAP)), 2),
    }


def main() -> None:
    predictions, per_fleet, all_pred, all_truth = [], {}, [], []
    for fleet in FLEETS:
        train, test = read_cycles(fleet, "train"), read_cycles(fleet, "test")
        add_conditions(train, test, CONDITIONS[fleet])
        sensors = normalize(train, test)
        train, features = add_features(train, sensors)
        test, _ = add_features(test, sensors)
        train["rul"] = (train.groupby("unit_number")["cycle"].transform("max") - train["cycle"]).clip(upper=RUL_CAP)

        params, cv_rmse = choose_params(train, features)
        model = LGBMRegressor(**params, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                              random_state=RANDOM_STATE, verbose=-1)
        model.fit(train[features], train["rul"])

        last = test.groupby("unit_number").tail(1).sort_values("unit_number")
        predicted = np.clip(model.predict(last[features]), 0, RUL_CAP)
        truth = read_rul_truth(fleet).to_numpy()
        all_pred.append(predicted)
        all_truth.append(truth)
        m = per_fleet[fleet] = {"test_engines": int(len(last)), "cv_rmse_cycles": round(cv_rmse, 2),
                                **summarize(predicted, truth), "params": params}
        print(f"{fleet}: CV {cv_rmse:.1f} | test RMSE {m['rmse_cycles']} (near failure {m['rmse_near_failure_cycles']}) "
              f"| within 20: {m['share_within_20_cycles']:.0%} (near failure {m['share_within_20_near_failure']:.0%})")

        out = last[["fleet_id", "dataset_split", "unit_number", "cycle"]].copy()
        out["predicted_rul"] = predicted.round(1)
        out["model_name"], out["model_version"] = MODEL_NAME, MODEL_VERSION
        predictions.append(out)

    metrics = {
        "model": MODEL_NAME, "model_version": MODEL_VERSION,
        "notes": f"Target capped at {RUL_CAP} cycles; scored against NASA's true RUL (uncapped) "
                 "at each test engine's last cycle. Settings chosen by grouped CV on training engines.",
        "all_fleets": {"test_engines": int(sum(len(t) for t in all_truth)),
                       **summarize(np.concatenate(all_pred), np.concatenate(all_truth))},
        "fleets": per_fleet,
    }
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    pd.concat(predictions)[PREDICTION_COLUMNS].to_csv(PROCESSED_DIR / "rul_predictions.csv", index=False)
    Path(__file__).with_name("metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print("all fleets:", metrics["all_fleets"])


if __name__ == "__main__":
    main()

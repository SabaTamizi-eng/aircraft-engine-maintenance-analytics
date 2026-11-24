"""Parse and validate the NASA files, and write the CSVs that get loaded into Snowflake.

data/processed/
    engine_cycles_initial.csv    train engines + the first 60% of each test engine
    engine_cycles_test_full.csv  all test cycles (simulate_feed.py sends the rest later)
    engine_rul_truth.csv         last cycle and true RUL per engine
"""
import argparse

import pandas as pd

from pipeline.config import (
    CMAPSS_DIR, CYCLE_COLUMNS, FLEET_INFO, FLEETS, INITIAL_TEST_SHARE,
    PROCESSED_DIR, SOURCE_COLUMNS, TRUTH_COLUMNS,
)


def read_cycles(fleet: str, split: str) -> pd.DataFrame:
    df = pd.read_csv(CMAPSS_DIR / f"{split}_{fleet}.txt", sep=r"\s+", header=None, names=SOURCE_COLUMNS)
    df.insert(0, "dataset_split", split)
    df.insert(0, "fleet_id", fleet)
    return df


def read_rul_truth(fleet: str) -> pd.Series:
    # one value per test engine, in engine order: RUL at its last cycle
    return pd.read_csv(CMAPSS_DIR / f"RUL_{fleet}.txt", header=None, names=["rul"])["rul"]


def validate_cycles(df: pd.DataFrame, fleet: str, split: str) -> None:
    errors = []
    expected_units = FLEET_INFO[fleet][f"{split}_units"]
    if df["unit_number"].nunique() != expected_units:
        errors.append(f"expected {expected_units} engines, found {df['unit_number'].nunique()}")
    if df.isna().any().any():
        errors.append("missing values found")
    if df.duplicated(["unit_number", "cycle"]).any():
        errors.append("duplicate engine cycles found")
    per_engine = df.groupby("unit_number")["cycle"].agg(["min", "max", "count"])
    if not ((per_engine["min"] == 1) & (per_engine["max"] == per_engine["count"])).all():
        errors.append("cycles are not continuous from 1 for every engine")
    if errors:
        raise ValueError(f"{split}_{fleet}: " + "; ".join(errors))


def build_truth(train: pd.DataFrame, test: pd.DataFrame, test_rul: pd.Series) -> pd.DataFrame:
    keys = ["fleet_id", "dataset_split", "unit_number"]
    train_last = train.groupby(keys, as_index=False)["cycle"].max()
    train_last["rul_at_final_cycle"] = 0  # train engines run until they fail

    test_last = test.groupby(keys, as_index=False)["cycle"].max().sort_values("unit_number")
    if len(test_last) != len(test_rul) or (test_rul < 0).any():
        raise ValueError("RUL truth file does not match the test engines")
    test_last["rul_at_final_cycle"] = test_rul.to_numpy()

    truth = pd.concat([train_last, test_last], ignore_index=True)
    return truth.rename(columns={"cycle": "final_cycle"})[TRUTH_COLUMNS]


def initial_slice(test: pd.DataFrame, share: float) -> pd.DataFrame:
    max_cycle = test.groupby(["fleet_id", "unit_number"])["cycle"].transform("max")
    cutoff = (max_cycle * share).astype(int).clip(lower=1)
    return test[test["cycle"] <= cutoff]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial-test-share", type=float, default=INITIAL_TEST_SHARE)
    args = parser.parse_args()

    trains, tests, truths = [], [], []
    for fleet in FLEETS:
        train, test = read_cycles(fleet, "train"), read_cycles(fleet, "test")
        validate_cycles(train, fleet, "train")
        validate_cycles(test, fleet, "test")
        trains.append(train)
        tests.append(test)
        truths.append(build_truth(train, test, read_rul_truth(fleet)))

    train_all = pd.concat(trains, ignore_index=True)
    test_all = pd.concat(tests, ignore_index=True)
    truth_all = pd.concat(truths, ignore_index=True)
    initial = pd.concat([train_all, initial_slice(test_all, args.initial_test_share)], ignore_index=True)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    initial[CYCLE_COLUMNS].to_csv(PROCESSED_DIR / "engine_cycles_initial.csv", index=False)
    test_all[CYCLE_COLUMNS].to_csv(PROCESSED_DIR / "engine_cycles_test_full.csv", index=False)
    truth_all.to_csv(PROCESSED_DIR / "engine_rul_truth.csv", index=False)

    summary = (
        pd.concat([train_all, test_all])
        .groupby(["fleet_id", "dataset_split"])
        .agg(engines=("unit_number", "nunique"), cycles=("cycle", "size"))
        .unstack("dataset_split")
    )
    held_back = len(test_all) - (len(initial) - len(train_all))
    print(summary.to_string())
    print(f"\ninitial load: {len(initial):,} rows, held back for the feed: {held_back:,}")


if __name__ == "__main__":
    main()

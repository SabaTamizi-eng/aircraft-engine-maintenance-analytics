"""Parse the raw NASA text files into tidy CSV files for Snowflake, with validation checks.

Outputs (data/processed/):
    engine_cycles_initial.csv    all run-to-failure (train) engines + the first part of each
                                 in-service (test) engine's history
    engine_cycles_test_full.csv  full in-service history, replayed later by simulate_feed.py
    engine_rul_truth.csv         failure reference per engine, used to calculate actual RUL

Usage (from the repository root):
    python -m pipeline.transform
"""
import argparse

import pandas as pd

from pipeline.config import (
    CMAPSS_DIR, CYCLE_COLUMNS, FLEET_INFO, FLEETS, INITIAL_TEST_SHARE,
    PROCESSED_DIR, SOURCE_COLUMNS, TRUTH_COLUMNS,
)


def read_cycles(fleet: str, split: str) -> pd.DataFrame:
    """Read one space-separated NASA file (one row per engine per operating cycle)."""
    df = pd.read_csv(CMAPSS_DIR / f"{split}_{fleet}.txt", sep=r"\s+", header=None, names=SOURCE_COLUMNS)
    df.insert(0, "dataset_split", split)
    df.insert(0, "fleet_id", fleet)
    return df


def read_rul_truth(fleet: str) -> pd.Series:
    """True remaining useful life at the last observed cycle of each test engine (row i = engine i)."""
    return pd.read_csv(CMAPSS_DIR / f"RUL_{fleet}.txt", header=None, names=["rul"])["rul"]


def validate_cycles(df: pd.DataFrame, fleet: str, split: str) -> None:
    """Fail fast if a file does not match the published dataset structure."""
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
    """One row per engine: last cycle in the source file and the RUL at that cycle."""
    keys = ["fleet_id", "dataset_split", "unit_number"]
    train_last = train.groupby(keys, as_index=False)["cycle"].max()
    train_last["rul_at_final_cycle"] = 0  # run-to-failure: the last cycle is the failure

    test_last = test.groupby(keys, as_index=False)["cycle"].max().sort_values("unit_number")
    if len(test_last) != len(test_rul) or (test_rul < 0).any():
        raise ValueError("RUL truth file does not match the test engines")
    test_last["rul_at_final_cycle"] = test_rul.to_numpy()

    truth = pd.concat([train_last, test_last], ignore_index=True)
    return truth.rename(columns={"cycle": "final_cycle"})[TRUTH_COLUMNS]


def initial_slice(test: pd.DataFrame, share: float) -> pd.DataFrame:
    """Keep the first `share` of each test engine's cycles (at least one cycle)."""
    max_cycle = test.groupby(["fleet_id", "unit_number"])["cycle"].transform("max")
    cutoff = (max_cycle * share).astype(int).clip(lower=1)
    return test[test["cycle"] <= cutoff]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
    print("All validation checks passed.\n")
    print(summary.to_string())
    print(
        f"\nInitial load: {len(initial):,} rows "
        f"({len(train_all):,} train + {len(initial) - len(train_all):,} test). "
        f"Held back for the simulated feed: {len(test_all) - (len(initial) - len(train_all)):,} test rows."
    )
    print(f"Files written to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()

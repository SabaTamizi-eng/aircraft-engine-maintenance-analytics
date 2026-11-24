import numpy as np
import pandas as pd
import pytest

from pipeline import transform
from pipeline.config import SOURCE_COLUMNS


def make_cycles(units: dict[int, int], fleet: str = "FD001", split: str = "train") -> pd.DataFrame:
    """units: engine number -> number of cycles"""
    rows = [
        [unit, cycle] + [1.0] * (len(SOURCE_COLUMNS) - 2)
        for unit, n_cycles in units.items()
        for cycle in range(1, n_cycles + 1)
    ]
    df = pd.DataFrame(rows, columns=SOURCE_COLUMNS)
    df.insert(0, "dataset_split", split)
    df.insert(0, "fleet_id", fleet)
    return df


@pytest.fixture(autouse=True)
def two_engine_fleet(monkeypatch):
    monkeypatch.setitem(transform.FLEET_INFO, "FD001", {"train_units": 2, "test_units": 2})


def test_valid_file_passes():
    transform.validate_cycles(make_cycles({1: 5, 2: 3}), "FD001", "train")


def test_wrong_engine_count():
    with pytest.raises(ValueError, match="expected 2 engines"):
        transform.validate_cycles(make_cycles({1: 5}), "FD001", "train")


def test_missing_cycle():
    df = make_cycles({1: 5, 2: 3})
    df = df[~((df["unit_number"] == 1) & (df["cycle"] == 3))]
    with pytest.raises(ValueError, match="not continuous"):
        transform.validate_cycles(df, "FD001", "train")


def test_duplicate_cycle():
    df = make_cycles({1: 5, 2: 3})
    df = pd.concat([df, df.iloc[[0]]])
    with pytest.raises(ValueError, match="duplicate"):
        transform.validate_cycles(df, "FD001", "train")


def test_missing_value():
    df = make_cycles({1: 5, 2: 3})
    df.loc[2, "sensor_4"] = np.nan
    with pytest.raises(ValueError, match="missing values"):
        transform.validate_cycles(df, "FD001", "train")


def test_build_truth():
    train = make_cycles({1: 5, 2: 3})
    test = make_cycles({1: 4, 2: 2}, split="test")
    truth = transform.build_truth(train, test, pd.Series([10, 20]))

    by_key = truth.set_index(["dataset_split", "unit_number"])
    assert by_key.loc[("train", 1), "final_cycle"] == 5
    assert by_key.loc[("train", 2), "rul_at_final_cycle"] == 0
    assert by_key.loc[("test", 1), "final_cycle"] == 4
    assert by_key.loc[("test", 2), "rul_at_final_cycle"] == 20


def test_build_truth_rejects_wrong_rul_count():
    train = make_cycles({1: 5, 2: 3})
    test = make_cycles({1: 4, 2: 2}, split="test")
    with pytest.raises(ValueError):
        transform.build_truth(train, test, pd.Series([10]))


def test_initial_slice_keeps_at_least_one_cycle():
    test = make_cycles({1: 10, 2: 1}, split="test")
    initial = transform.initial_slice(test, 0.6)
    assert initial.loc[initial["unit_number"] == 1, "cycle"].max() == 6
    assert initial.loc[initial["unit_number"] == 2, "cycle"].tolist() == [1]

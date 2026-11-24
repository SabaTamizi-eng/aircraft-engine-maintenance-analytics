"""Create local CSV files that mirror the Snowflake reporting views.

This lets you build the Power BI report before (or without) a Snowflake account.
Later, switch the Power Query source to Snowflake (powerbi/power_query/) and the
report keeps working, because table and column names match the Snowflake views.

Outputs (data/powerbi/):
    DIM_FLEET.csv, DIM_ENGINE.csv, DIM_SENSOR.csv,
    VW_ENGINE_CYCLE_RUL.csv, VW_ENGINE_CURRENT_HEALTH.csv, VW_DATA_QUALITY_CHECKS.csv

Usage (from the repository root, after transform and the model have run):
    python -m pipeline.export_powerbi_extract
"""
from datetime import datetime

import numpy as np
import pandas as pd

from pipeline.config import CRITICAL_RUL, FLEETS, POWERBI_DATA_DIR, PROCESSED_DIR, SENSORS, WARNING_RUL
from pipeline.transform import read_cycles

FLEET_ROWS = [
    ("FD001", "Fleet 1: sea level, HPC wear", 1, "Sea level", "HPC degradation", 1),
    ("FD002", "Fleet 2: six conditions, HPC wear", 6, "Six flight conditions", "HPC degradation", 1),
    ("FD003", "Fleet 3: sea level, HPC and fan wear", 1, "Sea level", "HPC and fan degradation", 2),
    ("FD004", "Fleet 4: six conditions, HPC and fan wear", 6, "Six flight conditions", "HPC and fan degradation", 2),
]
SENSOR_ROWS = [
    (1, "T2", "Total temperature at fan inlet", "deg R", False),
    (2, "T24", "Total temperature at LPC outlet", "deg R", True),
    (3, "T30", "Total temperature at HPC outlet", "deg R", True),
    (4, "T50", "Total temperature at LPT outlet", "deg R", True),
    (5, "P2", "Pressure at fan inlet", "psia", False),
    (6, "P15", "Total pressure in bypass duct", "psia", False),
    (7, "P30", "Total pressure at HPC outlet", "psia", True),
    (8, "Nf", "Physical fan speed", "rpm", True),
    (9, "Nc", "Physical core speed", "rpm", True),
    (10, "epr", "Engine pressure ratio (P50/P2)", "ratio", False),
    (11, "Ps30", "Static pressure at HPC outlet", "psia", True),
    (12, "phi", "Ratio of fuel flow to Ps30", "pps/psi", True),
    (13, "NRf", "Corrected fan speed", "rpm", True),
    (14, "NRc", "Corrected core speed", "rpm", True),
    (15, "BPR", "Bypass ratio", "ratio", True),
    (16, "farB", "Burner fuel-air ratio", "ratio", False),
    (17, "htBleed", "Bleed enthalpy", "index", True),
    (18, "Nf_dmd", "Demanded fan speed", "rpm", False),
    (19, "PCNfR_dmd", "Demanded corrected fan speed", "rpm", False),
    (20, "W31", "HPT coolant bleed", "lbm/s", True),
    (21, "W32", "LPT coolant bleed", "lbm/s", True),
]


def engine_key(df: pd.DataFrame) -> pd.Series:
    return df["fleet_id"] + "-" + df["dataset_split"].str.upper() + "-" + df["unit_number"].astype(str).str.zfill(3)


def health_status(rul: pd.Series) -> np.ndarray:
    return np.select([rul <= CRITICAL_RUL, rul <= WARNING_RUL], ["Critical", "Warning"], "Healthy")


def main() -> None:
    cycles = pd.concat(
        [read_cycles(f, s) for f in FLEETS for s in ("train", "test")], ignore_index=True
    )
    cycles.insert(0, "engine_key", engine_key(cycles))

    truth = pd.read_csv(PROCESSED_DIR / "engine_rul_truth.csv")
    truth["engine_key"] = engine_key(truth)
    truth["failure_cycle"] = truth["final_cycle"] + truth["rul_at_final_cycle"]

    # DIM_ENGINE (same rules as the stored procedure in sql/04)
    engines = cycles[["engine_key", "fleet_id", "dataset_split", "unit_number"]].drop_duplicates()
    engines["engine_serial_number"] = (
        "ESN-" + engines["fleet_id"].str[2:] + "-"
        + np.where(engines["dataset_split"] == "train", "R", "S")
        + engines["unit_number"].astype(str).str.zfill(4)
    )
    engines["engine_lifecycle"] = np.where(engines["dataset_split"] == "train", "Run to failure", "In service")
    engines = engines[["engine_key", "engine_serial_number", "fleet_id", "dataset_split", "unit_number", "engine_lifecycle"]]

    # VW_ENGINE_CYCLE_RUL
    rul = cycles.merge(truth[["engine_key", "failure_cycle"]], on="engine_key")
    rul["actual_rul"] = rul["failure_cycle"] - rul["cycle"]
    rul["health_status"] = health_status(rul["actual_rul"])
    rul = rul[["engine_key", "fleet_id", "cycle", "op_setting_1", "op_setting_2", "op_setting_3",
               *SENSORS, "actual_rul", "health_status"]]

    # VW_ENGINE_CURRENT_HEALTH
    latest = rul.sort_values("cycle").groupby("engine_key").tail(1)
    current = latest[["engine_key", "fleet_id", "cycle", "actual_rul", "health_status"]].rename(
        columns={"cycle": "current_cycle"})
    current = current.merge(engines[["engine_key", "dataset_split", "engine_lifecycle"]], on="engine_key")
    predictions_path = PROCESSED_DIR / "rul_predictions.csv"
    if predictions_path.exists():
        predictions = pd.read_csv(predictions_path)
        predictions["engine_key"] = engine_key(predictions)
        current = current.merge(
            predictions[["engine_key", "cycle", "predicted_rul", "model_name", "model_version"]],
            left_on=["engine_key", "current_cycle"], right_on=["engine_key", "cycle"], how="left",
        ).drop(columns="cycle")
    else:
        current[["predicted_rul", "model_name", "model_version"]] = np.nan
    current["prediction_error"] = current["predicted_rul"] - current["actual_rul"]
    current = current[["engine_key", "fleet_id", "dataset_split", "engine_lifecycle", "current_cycle",
                       "actual_rul", "health_status", "predicted_rul", "model_name", "model_version",
                       "prediction_error"]]

    # VW_DATA_QUALITY_CHECKS (same checks as sql/06, run locally)
    per_engine = rul.groupby("engine_key")["cycle"].agg(["min", "max", "count"])
    checks = [
        ("No duplicate engine cycles", "Uniqueness", int(rul.duplicated(["engine_key", "cycle"]).sum())),
        ("No missing sensor readings", "Completeness", int(rul[SENSORS].isna().any(axis=1).sum())),
        ("Cycles are continuous from 1 for every engine", "Consistency",
         int(((per_engine["min"] != 1) | (per_engine["max"] - per_engine["min"] + 1 != per_engine["count"])).sum())),
        ("Every engine has a failure reference", "Referential integrity",
         int((~engines["engine_key"].isin(truth["engine_key"])).sum())),
        ("No cycle beyond the engine failure point", "Validity", int((rul["actual_rul"] < 0).sum())),
        ("Temperature sensors within physical range", "Validity",
         int((rul[["sensor_1", "sensor_2", "sensor_3", "sensor_4"]] <= 0).any(axis=1).sum())),
    ]
    dq = pd.DataFrame(checks, columns=["check_name", "category", "failing_rows"])
    dq["status"] = np.where(dq["failing_rows"] == 0, "PASS", "FAIL")
    dq["checked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    POWERBI_DATA_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "DIM_FLEET": pd.DataFrame(FLEET_ROWS, columns=["fleet_id", "fleet_name", "operating_conditions",
                                                       "operating_condition_desc", "fault_modes", "fault_mode_count"]),
        "DIM_SENSOR": pd.DataFrame(SENSOR_ROWS, columns=["sensor_id", "sensor_symbol", "sensor_description",
                                                         "unit_of_measure", "used_in_baseline_model"]),
        "DIM_ENGINE": engines,
        "VW_ENGINE_CYCLE_RUL": rul,
        "VW_ENGINE_CURRENT_HEALTH": current,
        "VW_DATA_QUALITY_CHECKS": dq,
    }
    for name, df in outputs.items():
        df.columns = [c.upper() for c in df.columns]  # Snowflake returns upper-case column names
        df.to_csv(POWERBI_DATA_DIR / f"{name}.csv", index=False)
        print(f"{name}.csv: {len(df):,} rows")
    print(f"Files written to {POWERBI_DATA_DIR}")


if __name__ == "__main__":
    main()

"""Paths, dataset URL and column lists used across the pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CMAPSS_DIR = RAW_DIR / "CMAPSSData"
PROCESSED_DIR = DATA_DIR / "processed"
FEED_DIR = PROCESSED_DIR / "feed"
POWERBI_DATA_DIR = DATA_DIR / "powerbi"

DATASET_URL = (
    "https://phm-datasets.s3.amazonaws.com/NASA/"
    "6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip"
)

FLEETS = ["FD001", "FD002", "FD003", "FD004"]

# Expected engine counts. The NASA readme says FD004 has 248 train / 249 test,
# but the files actually have 249 / 248.
FLEET_INFO = {
    "FD001": {"train_units": 100, "test_units": 100},
    "FD002": {"train_units": 260, "test_units": 259},
    "FD003": {"train_units": 100, "test_units": 100},
    "FD004": {"train_units": 249, "test_units": 248},
}

OP_SETTINGS = [f"op_setting_{i}" for i in range(1, 4)]
SENSORS = [f"sensor_{i}" for i in range(1, 22)]

SOURCE_COLUMNS = ["unit_number", "cycle"] + OP_SETTINGS + SENSORS

# CSV column order, has to match the tables in sql/01_raw.sql
CYCLE_COLUMNS = ["fleet_id", "dataset_split"] + SOURCE_COLUMNS
TRUTH_COLUMNS = ["fleet_id", "dataset_split", "unit_number", "final_cycle", "rul_at_final_cycle"]
PREDICTION_COLUMNS = [
    "fleet_id", "dataset_split", "unit_number", "cycle",
    "predicted_rul", "model_name", "model_version",
]

# how much of each test engine goes in the first load; simulate_feed.py sends the rest
INITIAL_TEST_SHARE = 0.6

# health bands (cycles left), same as the SQL views
CRITICAL_RUL = 30
WARNING_RUL = 75

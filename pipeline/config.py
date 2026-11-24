"""Shared settings for the pipeline: paths, dataset source, and column definitions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CMAPSS_DIR = RAW_DIR / "CMAPSSData"
PROCESSED_DIR = DATA_DIR / "processed"
FEED_DIR = PROCESSED_DIR / "feed"
POWERBI_DATA_DIR = DATA_DIR / "powerbi"

# NASA Prognostics Center of Excellence data repository
DATASET_URL = (
    "https://phm-datasets.s3.amazonaws.com/NASA/"
    "6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip"
)

FLEETS = ["FD001", "FD002", "FD003", "FD004"]

# Engine counts used to validate the files.
# Note: the NASA readme lists FD004 as 248 train / 249 test engines, but the files
# contain 249 train / 248 test (the readme has them swapped). These are the real counts.
FLEET_INFO = {
    "FD001": {"train_units": 100, "test_units": 100},
    "FD002": {"train_units": 260, "test_units": 259},
    "FD003": {"train_units": 100, "test_units": 100},
    "FD004": {"train_units": 249, "test_units": 248},
}

OP_SETTINGS = [f"op_setting_{i}" for i in range(1, 4)]
SENSORS = [f"sensor_{i}" for i in range(1, 22)]

# Column order of the raw NASA text files
SOURCE_COLUMNS = ["unit_number", "cycle"] + OP_SETTINGS + SENSORS

# Column order of the CSV files loaded into Snowflake (must match sql/01_raw.sql)
CYCLE_COLUMNS = ["fleet_id", "dataset_split"] + SOURCE_COLUMNS
TRUTH_COLUMNS = ["fleet_id", "dataset_split", "unit_number", "final_cycle", "rul_at_final_cycle"]
PREDICTION_COLUMNS = [
    "fleet_id", "dataset_split", "unit_number", "cycle",
    "predicted_rul", "model_name", "model_version",
]

# Share of each in-service (test) engine's history loaded up front.
# The rest arrives later through simulate_feed.py to demonstrate change data capture.
INITIAL_TEST_SHARE = 0.6

# Health bands used in SQL views and the dashboard (remaining useful life, in cycles)
CRITICAL_RUL = 30
WARNING_RUL = 75

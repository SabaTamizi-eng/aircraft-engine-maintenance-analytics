"""Simulate new sensor data arriving from in-service engines, to demonstrate change data capture.

Each batch appends the next N cycles for every in-service (test) engine to
RAW.ENGINE_CYCLES_RAW. The Snowflake stream captures only the new rows, and the
scheduled task merges them into the star schema (sql/04_cdc_streams_tasks.sql).

Usage (from the repository root, after `python -m pipeline.load_snowflake --initial`):
    python -m pipeline.simulate_feed --batches 3 --cycles-per-batch 10 --interval 60
"""
import argparse
import time
from datetime import datetime

import pandas as pd

from pipeline.config import CYCLE_COLUMNS, FEED_DIR, PROCESSED_DIR
from pipeline.snowflake_utils import connect, put_and_copy


def current_progress(cursor) -> pd.DataFrame:
    """Latest cycle already loaded for each in-service engine."""
    cursor.execute("""
        SELECT fleet_id, unit_number, MAX(cycle) AS loaded_cycle
        FROM RAW.ENGINE_CYCLES_RAW
        WHERE dataset_split = 'test'
        GROUP BY fleet_id, unit_number
    """)
    return pd.DataFrame(cursor.fetchall(), columns=["fleet_id", "unit_number", "loaded_cycle"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--batches", type=int, default=3)
    parser.add_argument("--cycles-per-batch", type=int, default=10)
    parser.add_argument("--interval", type=int, default=60, help="seconds to wait between batches")
    args = parser.parse_args()

    full = pd.read_csv(PROCESSED_DIR / "engine_cycles_test_full.csv")
    FEED_DIR.mkdir(parents=True, exist_ok=True)

    with connect() as conn, conn.cursor() as cursor:
        progress = current_progress(cursor)
        for batch_no in range(1, args.batches + 1):
            merged = full.merge(progress, on=["fleet_id", "unit_number"], how="left")
            merged["loaded_cycle"] = merged["loaded_cycle"].fillna(0)
            batch = merged[
                (merged["cycle"] > merged["loaded_cycle"])
                & (merged["cycle"] <= merged["loaded_cycle"] + args.cycles_per_batch)
            ][CYCLE_COLUMNS]
            if batch.empty:
                print("All in-service engine cycles have been delivered.")
                break

            path = FEED_DIR / f"engine_cycles_batch_{datetime.now():%Y%m%d_%H%M%S}.csv"
            batch.to_csv(path, index=False)
            engines = batch.groupby(["fleet_id", "unit_number"]).ngroups
            print(f"Batch {batch_no}: {len(batch):,} new cycles for {engines} engines")
            put_and_copy(cursor, path, "cycles", "RAW.ENGINE_CYCLES_RAW", CYCLE_COLUMNS, add_source_file=True)

            delivered = batch.rename(columns={"cycle": "loaded_cycle"})[["fleet_id", "unit_number", "loaded_cycle"]]
            progress = (
                pd.concat([progress, delivered])
                .groupby(["fleet_id", "unit_number"], as_index=False)["loaded_cycle"].max()
            )
            if batch_no < args.batches:
                time.sleep(args.interval)


if __name__ == "__main__":
    main()

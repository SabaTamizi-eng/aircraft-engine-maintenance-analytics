"""Load processed files into the Snowflake RAW layer.

Run sql/00 to sql/05 first. New rows in RAW.ENGINE_CYCLES_RAW are picked up by the
stream and merged into the star schema by the scheduled task (sql/04).

Usage (from the repository root):
    python -m pipeline.load_snowflake --initial       # engine cycles (initial batch) + RUL reference
    python -m pipeline.load_snowflake --predictions   # model predictions from ml/train_rul_model.py
"""
import argparse

from pipeline.config import CYCLE_COLUMNS, PREDICTION_COLUMNS, PROCESSED_DIR, TRUTH_COLUMNS
from pipeline.snowflake_utils import connect, put_and_copy


def load_initial(cursor) -> None:
    print("Loading initial engine cycles (append, captured by the stream)...")
    put_and_copy(cursor, PROCESSED_DIR / "engine_cycles_initial.csv", "cycles",
                 "RAW.ENGINE_CYCLES_RAW", CYCLE_COLUMNS, add_source_file=True)

    print("Refreshing the RUL reference table (full reload)...")
    cursor.execute("TRUNCATE TABLE RAW.ENGINE_RUL_TRUTH")
    put_and_copy(cursor, PROCESSED_DIR / "engine_rul_truth.csv", "truth",
                 "RAW.ENGINE_RUL_TRUTH", TRUTH_COLUMNS, force=True)


def load_predictions(cursor) -> None:
    print("Refreshing model predictions (full reload)...")
    cursor.execute("TRUNCATE TABLE RAW.RUL_PREDICTIONS_RAW")
    put_and_copy(cursor, PROCESSED_DIR / "rul_predictions.csv", "predictions",
                 "RAW.RUL_PREDICTIONS_RAW", PREDICTION_COLUMNS, force=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--initial", action="store_true", help="load engine cycles and the RUL reference")
    parser.add_argument("--predictions", action="store_true", help="load model predictions")
    args = parser.parse_args()
    if not (args.initial or args.predictions):
        parser.error("choose --initial and/or --predictions")

    with connect() as conn, conn.cursor() as cursor:
        if args.initial:
            load_initial(cursor)
        if args.predictions:
            load_predictions(cursor)
    print("Done. Run `EXECUTE TASK ANALYTICS.TASK_PROCESS_ENGINE_CYCLES;` or wait for the next scheduled run.")


if __name__ == "__main__":
    main()

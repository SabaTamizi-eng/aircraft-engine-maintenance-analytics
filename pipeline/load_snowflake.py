"""Load the processed CSVs into RAW (run the sql/ scripts first).

    python -m pipeline.load_snowflake --initial        cycles + RUL truth
    python -m pipeline.load_snowflake --predictions    model output
"""
import argparse

from pipeline.config import CYCLE_COLUMNS, PREDICTION_COLUMNS, PROCESSED_DIR, TRUTH_COLUMNS
from pipeline.snowflake_utils import connect, put_and_copy


def load_initial(cursor) -> None:
    put_and_copy(cursor, PROCESSED_DIR / "engine_cycles_initial.csv", "cycles",
                 "RAW.ENGINE_CYCLES_RAW", CYCLE_COLUMNS, add_source_file=True)

    cursor.execute("TRUNCATE TABLE RAW.ENGINE_RUL_TRUTH")
    put_and_copy(cursor, PROCESSED_DIR / "engine_rul_truth.csv", "truth",
                 "RAW.ENGINE_RUL_TRUTH", TRUTH_COLUMNS, force=True)


def load_predictions(cursor) -> None:
    cursor.execute("TRUNCATE TABLE RAW.RUL_PREDICTIONS_RAW")
    put_and_copy(cursor, PROCESSED_DIR / "rul_predictions.csv", "predictions",
                 "RAW.RUL_PREDICTIONS_RAW", PREDICTION_COLUMNS, force=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial", action="store_true")
    parser.add_argument("--predictions", action="store_true")
    args = parser.parse_args()
    if not (args.initial or args.predictions):
        parser.error("choose --initial and/or --predictions")

    with connect() as conn, conn.cursor() as cursor:
        if args.initial:
            load_initial(cursor)
        if args.predictions:
            load_predictions(cursor)
    print("done - the task will merge the new rows on its next run")


if __name__ == "__main__":
    main()

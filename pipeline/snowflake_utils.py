"""Snowflake connection and file-loading helpers shared by the load and feed scripts."""
import os
from pathlib import Path

from dotenv import load_dotenv

from pipeline.config import ROOT

STAGE = "RAW.ENGINE_STAGE"
FILE_FORMAT = "RAW.CSV_FF"


def connect():
    """Open a connection using settings from .env (see .env.example)."""
    import snowflake.connector  # imported here so the rest of the pipeline works without it

    load_dotenv(ROOT / ".env")
    params = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "role": os.getenv("SNOWFLAKE_ROLE", "ENGINE_ENGINEER"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "ENGINE_WH"),
        "database": os.getenv("SNOWFLAKE_DATABASE", "ENGINE_ANALYTICS"),
    }
    auth = os.getenv("SNOWFLAKE_AUTHENTICATOR", "externalbrowser").lower()
    if auth == "snowflake_jwt":  # key-pair authentication
        params["authenticator"] = "SNOWFLAKE_JWT"
        params["private_key_file"] = os.environ["SNOWFLAKE_PRIVATE_KEY_FILE"]
    elif auth == "snowflake":  # user name and password
        params["password"] = os.environ["SNOWFLAKE_PASSWORD"]
    else:  # e.g. externalbrowser (single sign-on in the browser)
        params["authenticator"] = auth
    return snowflake.connector.connect(**params)


def put_and_copy(cursor, csv_path: Path, stage_folder: str, table: str, columns: list[str],
                 *, add_source_file: bool = False, force: bool = False) -> int:
    """Upload a CSV to the internal stage and COPY it into a table. Returns rows loaded.

    COPY keeps load history per file, so re-running with the same file is skipped
    unless force=True. That makes the incremental loads safe to repeat.
    """
    stage_path = f"{STAGE}/{stage_folder}"
    cursor.execute(
        f"PUT 'file://{csv_path.resolve().as_posix()}' @{stage_path} AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
    )

    target_cols = [c.upper() for c in columns]
    select_cols = [f"${i}" for i in range(1, len(columns) + 1)]
    if add_source_file:
        target_cols.append("SOURCE_FILE")
        select_cols.append("METADATA$FILENAME")

    cursor.execute(f"""
        COPY INTO {table} ({', '.join(target_cols)})
        FROM (SELECT {', '.join(select_cols)} FROM @{stage_path})
        FILES = ('{csv_path.name}.gz')
        FILE_FORMAT = (FORMAT_NAME = '{FILE_FORMAT}')
        ON_ERROR = 'ABORT_STATEMENT'
        FORCE = {'TRUE' if force else 'FALSE'}
    """)
    result_cols = [d[0].lower() for d in cursor.description]
    rows = cursor.fetchall()
    if "rows_loaded" not in result_cols:  # e.g. "Copy executed with 0 files processed."
        print(f"  {csv_path.name}: already loaded, skipped")
        return 0
    loaded = sum(row[result_cols.index("rows_loaded")] for row in rows)
    print(f"  {csv_path.name} -> {table}: {loaded:,} rows")
    return loaded

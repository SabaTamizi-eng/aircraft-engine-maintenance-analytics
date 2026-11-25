"""Run the Snowflake scripts in sql/ from Python (instead of pasting them into a worksheet).

    python -m pipeline.run_sql                      # 00 to 06, in order
    python -m pipeline.run_sql sql/05_governance.sql

Connects as ACCOUNTADMIN because 00_setup.sql creates roles; each script switches to the
role it needs with USE ROLE.
"""
import sys

from pipeline.config import ROOT
from pipeline.snowflake_utils import connect

DEFAULT_SCRIPTS = [
    "00_setup.sql", "01_raw.sql", "02_staging.sql", "03_analytics_star_schema.sql",
    "04_cdc_streams_tasks.sql", "05_governance.sql", "06_data_quality.sql",
]


def main() -> None:
    scripts = [ROOT / a for a in sys.argv[1:]] or [ROOT / "sql" / name for name in DEFAULT_SCRIPTS]
    with connect(role="ACCOUNTADMIN", use_defaults=False) as conn:
        for path in scripts:
            print(f"== {path.name}")
            for cursor in conn.execute_string(path.read_text(encoding="utf-8"), remove_comments=True):
                first_line = cursor.query.strip().splitlines()[0][:90]
                result = cursor.fetchone() if cursor.description else None
                print(f"   ok  {first_line}" + (f"  ->  {result[0]}" if result else ""))


if __name__ == "__main__":
    main()

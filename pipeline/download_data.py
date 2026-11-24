"""Download the NASA C-MAPSS turbofan engine dataset into data/raw/.

Usage (from the repository root):
    python -m pipeline.download_data
"""
import io
import shutil
import urllib.request
import zipfile

from pipeline.config import CMAPSS_DIR, DATASET_URL, FLEETS, RAW_DIR

EXPECTED_FILES = ["readme.txt"] + [
    f"{prefix}_{fleet}.txt" for fleet in FLEETS for prefix in ("train", "test", "RUL")
]


def main() -> None:
    if all((CMAPSS_DIR / name).exists() for name in EXPECTED_FILES):
        print(f"Dataset already present in {CMAPSS_DIR}")
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR / "cmapss.zip"
    if not zip_path.exists():
        print(f"Downloading {DATASET_URL}")
        with urllib.request.urlopen(DATASET_URL, timeout=120) as response, open(zip_path, "wb") as out:
            shutil.copyfileobj(response, out)

    # The download is a zip that contains a second zip with the text files.
    with zipfile.ZipFile(zip_path) as outer:
        inner_name = next(n for n in outer.namelist() if n.endswith("CMAPSSData.zip"))
        with zipfile.ZipFile(io.BytesIO(outer.read(inner_name))) as inner:
            CMAPSS_DIR.mkdir(parents=True, exist_ok=True)
            # Extract only the files we expect, by name, so nothing else lands on disk.
            for name in EXPECTED_FILES:
                (CMAPSS_DIR / name).write_bytes(inner.read(name))

    print(f"Extracted {len(EXPECTED_FILES)} files to {CMAPSS_DIR}")


if __name__ == "__main__":
    main()

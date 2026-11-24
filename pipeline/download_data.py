"""Download the NASA C-MAPSS dataset and extract the text files into data/raw/."""
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
        print("already downloaded")
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR / "cmapss.zip"
    if not zip_path.exists():
        print("downloading...")
        with urllib.request.urlopen(DATASET_URL, timeout=120) as response, open(zip_path, "wb") as out:
            shutil.copyfileobj(response, out)

    # the text files are in a zip inside the zip
    with zipfile.ZipFile(zip_path) as outer:
        inner_name = next(n for n in outer.namelist() if n.endswith("CMAPSSData.zip"))
        with zipfile.ZipFile(io.BytesIO(outer.read(inner_name))) as inner:
            CMAPSS_DIR.mkdir(parents=True, exist_ok=True)
            for name in EXPECTED_FILES:
                (CMAPSS_DIR / name).write_bytes(inner.read(name))

    print(f"extracted {len(EXPECTED_FILES)} files to {CMAPSS_DIR}")


if __name__ == "__main__":
    main()

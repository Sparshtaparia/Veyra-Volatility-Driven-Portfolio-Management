"""Download and normalize the official Ken French daily five-factor dataset."""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

from quant_engine.factors.provider import validate_factor_frame

OFFICIAL_DAILY_ZIP_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"
)
DEFAULT_FAMA_FRENCH_PATH = (
    Path(__file__).resolve().parents[2]
    / "data/fama_french/F-F_Research_Data_5_Factors_2x3_daily.csv"
)


def download_fama_french_daily(path: str | Path = DEFAULT_FAMA_FRENCH_PATH) -> Path:
    """Fetch, validate, and store the official dataset as decimal daily returns."""
    destination = Path(path)
    request = Request(OFFICIAL_DAILY_ZIP_URL, headers={"User-Agent": "Veyra/0.2 factor-setup"})
    with urlopen(request, timeout=30.0) as response:
        archive = response.read()
    frame = _parse_official_archive(archive)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index_label="date")
    return destination


def ensure_fama_french_daily(path: str | Path = DEFAULT_FAMA_FRENCH_PATH) -> Path:
    """Return a valid cached file, downloading it only when it is absent."""
    destination = Path(path)
    if destination.is_file():
        existing = pd.read_csv(destination)
        date_column = next(
            (column for column in existing.columns if column.lower() == "date"), None
        )
        if date_column is None:
            raise ValueError("factor CSV must contain a date column")
        dates = pd.to_datetime(existing.pop(date_column), errors="coerce")
        if dates.isna().any() or dates.duplicated().any():
            raise ValueError("factor CSV dates must be valid and unique")
        validate_factor_frame(existing)
        return destination
    return download_fama_french_daily(destination)


def _parse_official_archive(archive: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
        csv_name = next(name for name in zip_file.namelist() if name.lower().endswith(".csv"))
        content = zip_file.read(csv_name).decode("latin-1")
    rows = list(csv.reader(content.splitlines()))
    header_index = next(
        index
        for index, row in enumerate(rows)
        if row and row[0].strip().lower() in {"date", ""} and "Mkt-RF" in row
    )
    header = [value.strip() for value in rows[header_index]]
    data_rows = []
    for row in rows[header_index + 1 :]:
        if not row or not row[0].strip().isdigit():
            break
        data_rows.append([value.strip() for value in row])
    frame = pd.DataFrame(data_rows, columns=header)
    date_column = header[0]
    frame.index = pd.to_datetime(frame.pop(date_column), format="%Y%m%d", errors="coerce")
    normalized = validate_factor_frame(frame)
    if normalized.index.isna().any() or normalized.index.has_duplicates:
        raise ValueError("official factor dataset contains invalid or duplicate dates")
    # Ken French publishes daily returns in percent; Veyra stores decimal returns.
    return normalized.sort_index() / 100.0


if __name__ == "__main__":
    print(ensure_fama_french_daily())

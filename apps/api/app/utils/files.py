from io import BufferedReader
from pathlib import Path
import shutil


def build_unique_destination(root: Path, filename: str) -> Path:
    source_name = Path(filename)
    destination = root / source_name.name
    counter = 1
    while destination.exists():
        destination = root / f"{source_name.stem}-{counter}{source_name.suffix}"
        counter += 1
    return destination


def copy_upload_to_path(*, file_handle: BufferedReader, destination: Path) -> None:
    file_handle.seek(0)
    with destination.open("wb") as output:
        shutil.copyfileobj(file_handle, output)

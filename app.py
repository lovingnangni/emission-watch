"""Streamlit entry point for the Emission Watch iPad ZIP bundle.

The ZIP is already in this public GitHub repository. Download a SHA-256-pinned
copy on the server, unpack only the expected paths, then run the bundled app.
No user data is collected or uploaded.
"""
from __future__ import annotations

import hashlib
import io
import runpy
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

BUNDLE_URL = (
    "https://raw.githubusercontent.com/lovingnangni/emission-watch/main/"
    "emission_watch_ipad_upload.zip"
)
BUNDLE_SHA256 = "466c51cf9492bfa6fdad294bb05500a68b8e112a0dfe1801817f9017859b3e49"
BUNDLE_PREFIX = "emission_watch_ipad_upload/"
FILES = (
    "app.py", "core.py", "README.md", "requirements.txt",
    "demo_2014.csv", "reference_2013.csv", "nox_model.joblib", "metadata.json",
)


def get_bundle() -> Path:
    dest = Path(tempfile.gettempdir()) / ("emission_watch_" + BUNDLE_SHA256[:16])
    if not all((dest / name).is_file() for name in FILES):
        with urllib.request.urlopen(BUNDLE_URL, timeout=45) as response:
            payload = response.read()
        if hashlib.sha256(payload).hexdigest() != BUNDLE_SHA256:
            raise RuntimeError("Downloaded bundle checksum did not match the reviewed version")
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for filename in FILES:
                (dest / filename).write_bytes(archive.read(BUNDLE_PREFIX + filename))
    return dest


bundle_dir = get_bundle()
sys.path.insert(0, str(bundle_dir))
runpy.run_path(str(bundle_dir / "app.py"), run_name="__main__")

"""Streamlit entry point for the verified Emission Watch data/model bundle."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import runpy
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import streamlit as st

# Check the actual app environment before trying to import the model or charts.
# requirements.txt lists all of these packages, but the current Cloud deployment
# reported missing plotly and joblib despite saying dependencies were processed.
NEEDED = ("numpy", "pandas", "plotly", "joblib", "sklearn")
missing = [name for name in NEEDED if importlib.util.find_spec(name) is None]
if missing:
    st.set_page_config(page_title="Emission Watch | 설치 환경 확인", page_icon="🌿")
    st.error("앱 실행 환경에 필수 패키지가 설치되지 않았습니다.")
    st.write("없는 모듈:", ", ".join(missing))
    st.write("실행 중인 Python 버전:", sys.version.split()[0])
    st.info(
        "GitHub의 requirements.txt에는 필요한 패키지가 이미 적혀 있습니다. "
        "Streamlit Community Cloud에서 앱을 Python 3.12로 새로 배포하고 "
        "패키지 설치 로그를 확인해 주세요. GitHub 저장소는 삭제하지 마세요."
    )
    st.stop()

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

"""Launch the verified Emission Watch bundle without an optional Plotly dependency."""
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
source = (bundle_dir / "app.py").read_text(encoding="utf-8")
old_import = "import plotly.graph_objects as go\n"
chart_start = "    figure = go.Figure()"
chart_end = "    st.plotly_chart(figure, use_container_width=True)"
if source.count(old_import) != 1 or source.count(chart_start) != 1 or source.count(chart_end) != 1:
    raise RuntimeError("The bundled app changed; chart compatibility patch needs review")
source = source.replace(old_import, "")
start = source.index(chart_start)
end = source.index(chart_end, start) + len(chart_end)
source = source[:start] + '    st.scatter_chart(sample, x="NOX", y="predicted_NOX", height=450)' + source[end:]
patched_app = bundle_dir / "app_streamlit.py"
patched_app.write_text(source, encoding="utf-8")
runpy.run_path(str(patched_app), run_name="__main__")

"""Evaluate the original 2011-12 model on untouched UCI 2015 records.

Run: python evaluate_2015.py
Uses official UCI dataset 551 ZIP; does not fit or replace the model.
"""
from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parent
URL = "https://archive.ics.uci.edu/static/public/551/gas+turbine+co+and+nox+emission+data+set.zip"
with urllib.request.urlopen(URL, timeout=120) as response:
    payload = response.read()
with zipfile.ZipFile(io.BytesIO(payload)) as archive:
    entries = [name for name in archive.namelist() if name.lower().endswith("gt_2015.csv")]
    if len(entries) != 1:
        raise ValueError(f"Expected exactly one gt_2015.csv in official UCI ZIP, got {entries}")
    data = pd.read_csv(archive.open(entries[0]))
with zipfile.ZipFile(ROOT / "emission_watch_ipad_upload.zip") as archive:
    prefix = "emission_watch_ipad_upload/"
    metadata = json.load(archive.open(prefix + "metadata.json"))
    # This model is a trusted, project-authored artifact, NOT user-uploaded data.
    model = joblib.load(io.BytesIO(archive.read(prefix + "nox_model.joblib")))
features = metadata["features"]
assert len(data) == 7384, f"Unexpected held-out row count: {len(data)}"
assert set(features + ["NOX"]).issubset(data.columns)
assert data[features + ["NOX"]].notna().all().all()
pred = model.predict(data[features])
measured = data["NOX"].to_numpy(dtype=float)
report = {
    "year": 2015,
    "records": len(data),
    "train_years": metadata["training_years"],
    "mae_mg_m3": float(mean_absolute_error(measured, pred)),
    "rmse_mg_m3": float(np.sqrt(mean_squared_error(measured, pred))),
    "r2": float(r2_score(measured, pred)),
    "mean_residual_measured_minus_predicted_mg_m3": float(np.mean(measured - pred)),
    "source": URL,
    "model_retrained": False,
}
print("2015_HELD_OUT_EVALUATION=" + json.dumps(report, ensure_ascii=False))
(ROOT / "evaluation_2015_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

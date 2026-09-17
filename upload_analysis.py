"""CSV investigation for a transparent UCI gas-turbine research demonstration.

No uploaded objects are deserialized; only CSV bytes enter the model. The model
and reference data are fixed, reviewed artifacts bundled with the app.
"""
from __future__ import annotations

from io import BytesIO

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 20_000


def analyze_csv(payload: bytes, model, reference: pd.DataFrame, features: list[str], threshold: float):
    """Validate same-schema CSV and compare against the existing 2013 references."""
    if not payload:
        raise ValueError("CSV 파일이 비어 있습니다.")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise ValueError("CSV 크기는 10 MB 이하여야 합니다.")
    try:
        frame = pd.read_csv(BytesIO(payload), encoding="utf-8-sig")
    except (UnicodeError, pd.errors.ParserError, ValueError) as exc:
        raise ValueError("UTF-8 인코딩의 쉼표 구분 CSV를 올려주세요.") from exc
    if frame.empty:
        raise ValueError("CSV에 분석할 행이 없습니다.")
    if len(frame) > MAX_ROWS:
        raise ValueError("한 번에 최대 20,000행까지만 분석할 수 있습니다.")
    missing = [feature for feature in features if feature not in frame.columns]
    if missing:
        raise ValueError("필수 운전 변수 누락: " + ", ".join(missing))
    measured = "NOX" in frame.columns
    columns = features + (["NOX"] if measured else [])
    numeric = frame[columns].apply(pd.to_numeric, errors="coerce")
    invalid = (~np.isfinite(numeric.to_numpy(dtype=float))).any(axis=1)
    if invalid.any():
        first = np.flatnonzero(invalid)[:5] + 2
        raise ValueError(
            "필수 변수에 빈칸·문자·무한대가 있는 행이 있습니다. "
            "CSV 줄 번호(예시): " + ", ".join(map(str, first))
        )
    reference_numeric = reference[features].to_numpy(dtype=float)
    scale = StandardScaler().fit(reference_numeric)
    nn = NearestNeighbors(n_neighbors=1).fit(scale.transform(reference_numeric))
    distances, indexes = nn.kneighbors(scale.transform(numeric[features].to_numpy(dtype=float)))
    nearest = reference.iloc[indexes[:, 0]].reset_index(drop=True)
    result = numeric.copy()
    result.insert(0, "업로드 행", np.arange(1, len(result) + 1))
    result["예측 NOX"] = model.predict(numeric[features])
    result["가장 가까운 2013년 기록"] = nearest["record_id"].to_numpy(dtype=int)
    result["표준화 거리"] = distances[:, 0]
    result["비교 가능"] = result["표준화 거리"] <= threshold
    result["과거 유사 기록 NOX"] = np.where(result["비교 가능"], nearest["NOX"], np.nan)
    if measured:
        result["예측오차 (실제−예측)"] = result["NOX"] - result["예측 NOX"]
    return result


def render_upload_section(bundle_dir, meta: dict, reference: pd.DataFrame, model):
    """Add a self-contained Streamlit investigation panel below the existing tabs."""
    import streamlit as st

    features = meta["features"]
    threshold = float(meta["matching_distance_threshold"])
    st.divider()
    st.header("📂 CSV 업로드 · 내 기록 조사")
    st.write(
        "가스터빈 운전 변수 9개가 들어 있는 **UTF-8 CSV**를 업로드하면 "
        "기존 공개 데이터 모델로 NOₓ를 예측하고 2013년 유사 기록과 비교합니다. "
        "실제 NOX 열이 있으면 예측오차도 계산합니다."
    )
    st.warning(
        "연구용 시연입니다. 다른 발전소나 다른 측정 단위에서의 정확성은 검증되지 않았습니다. "
        "민감한 설비 데이터·개인정보는 공개 데모에 올리지 마세요. "
        "업로드 결과만으로 고장이나 규제 위반을 판정하지 않습니다."
    )
    st.caption("필수 열: " + ", ".join(features) + " · 선택 열: NOX · UCI 원본과 동일한 변수 정의·단위 필요")
    example = reference[features + ["NOX"]].head(5).to_csv(index=False).encode("utf-8-sig")
    st.download_button("예시 CSV 내려받기 (공개 데이터 5행)", example, "emission_watch_example.csv", "text/csv")
    uploaded = st.file_uploader("CSV 선택 (최대 10 MB · 20,000행)", type=["csv"], key="emission_csv_upload")
    if uploaded is None:
        return
    if uploaded.size > MAX_UPLOAD_BYTES:
        st.error("CSV 크기는 10 MB 이하여야 합니다.")
        return
    try:
        analyzed = analyze_csv(uploaded.getvalue(), model, reference, features, threshold)
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("CSV를 분석하지 못했습니다. 원본 데이터와 열 이름·단위를 확인해 주세요.")
        return

    measured = "NOX" in analyzed.columns
    a, b, c = st.columns(3)
    a.metric("업로드 기록", f"{len(analyzed):,}건")
    b.metric("유사 기록 비교 가능", f"{int(analyzed['비교 가능'].sum()):,}건")
    if measured:
        c.metric("이 파일의 MAE", f"{mean_absolute_error(analyzed['NOX'], analyzed['예측 NOX']):.3f} mg/m³")
        st.caption("파일의 실제 NOX와 예측값으로 계산한 오차입니다. 한 발전소에서 학습한 모델의 다른 설비 정확성을 보장하지 않습니다.")
        st.scatter_chart(analyzed.sample(n=min(2000, len(analyzed)), random_state=42), x="NOX", y="예측 NOX", height=330)
    else:
        c.metric("실제 NOX", "미제공")
        st.info("NOX 측정 열이 없어 예측오차·정확도는 계산하지 않았습니다.")

    view = st.radio("기록 보기", ["전체", "유사 기록 비교 가능", "비교 자료 부족"], horizontal=True)
    subset = analyzed if view == "전체" else analyzed.loc[analyzed["비교 가능"] == (view == "유사 기록 비교 가능")]
    if measured:
        st.caption("아래 정렬은 **예측오차 크기순**이며, 이상·고장 순위가 아닙니다.")
        subset = subset.reindex(subset["예측오차 (실제−예측)"].abs().sort_values(ascending=False).index)
    st.dataframe(subset.drop(columns=features), hide_index=True, use_container_width=True)
    st.download_button(
        "분석 결과 CSV 내려받기",
        analyzed.to_csv(index=False).encode("utf-8-sig"),
        "emission_watch_uploaded_results.csv", "text/csv",
    )
    selected = st.number_input("자세히 볼 업로드 행 번호", min_value=1, max_value=len(analyzed), value=1, step=1)
    row = analyzed.iloc[int(selected) - 1]
    st.write(f"**업로드 {int(selected)}행** · 예측 NOₓ **{row['예측 NOX']:.3f} mg/m³**")
    if measured:
        st.write(f"실제 NOₓ **{row['NOX']:.3f}** / 오차(실제−예측) **{row['예측오차 (실제−예측)']:+.3f} mg/m³**")
    if bool(row["비교 가능"]):
        st.success(
            f"2013년 기록 #{int(row['가장 가까운 2013년 기록'])}과 탐색적 비교 가능 "
            f"(거리 {row['표준화 거리']:.3f} / 기준 {threshold:.3f}). "
            f"그 기록의 NOₓ는 {row['과거 유사 기록 NOX']:.3f} mg/m³입니다."
        )
    else:
        st.warning(
            f"가장 가까운 2013년 기록도 임시 거리 기준을 넘어서 비교를 보류합니다 "
            f"({row['표준화 거리']:.3f} > {threshold:.3f}). 이것은 고장 판정이 아닙니다."
        )
    st.caption("2013년 거리 기준은 탐색용입니다. 업로드한 CSV는 이 페이지에서 분석하며 데이터베이스에 저장하는 기능은 없습니다.")

"""Explain the exploratory nearest-record distance threshold using the bundled data."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st


def render_matching_insights(analyzed: pd.DataFrame, reference: pd.DataFrame, threshold: float):
    """Display coverage/gap tradeoffs; never reclassify or alter existing matches."""
    distances = analyzed["nearest_distance"].to_numpy(dtype=float)
    measured = analyzed["NOX"].to_numpy(dtype=float)
    reference_nox = reference.set_index("record_id")["NOX"]
    neighbor_nox = reference_nox.loc[analyzed["nearest_id"].to_numpy()].to_numpy(dtype=float)
    gaps = np.abs(measured - neighbor_nox)
    with st.expander("🔍 유사 기록 17.8%가 낮은 이유 · 기준별 실제 비교", expanded=False):
        st.write(
            "**17.8%는 예측 정확도가 아니라**, 2014년 기록 중 2013년의 가장 가까운 "
            "운전 조건이 임시 거리 기준 안에 든 비율입니다. 기준을 넓히면 사례는 늘지만 "
            "운전 조건이 덜 비슷한 기록도 포함됩니다."
        )
        rows = []
        for cutoff in (threshold, 0.6, 0.75, 1.0):
            included = distances <= cutoff
            rows.append({
                "표준화 거리 상한": round(cutoff, 3),
                "통과 건수": int(included.sum()),
                "통과율": f"{included.mean():.2%}",
                "측정 NOₓ 평균 절대차이 (mg/m³)": round(float(gaps[included].mean()), 3),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption(
            "2014년 전체 7,158건의 동일한 최근접 2013년 기록을 사용한 사후 민감도 분석. "
            "NOₓ 차이는 두 연도 측정값 간 차이이며, 모델 MAE·고장 탐지 성능이 아닙니다."
        )
        extra = (distances > threshold) & (distances <= 0.75)
        st.info(
            f"**현재 기준은 그대로 유지:** 거리 ≤ {threshold:.3f}인 1,277건만 ‘비교 가능’으로 "
            f"표시합니다. 추가 {int(extra.sum()):,}건은 0.75 이내에 있지만 "
            "검증된 유사 기록이 아닌 **참고 거리대**일 뿐입니다. 기존 ‘비교 보류’ 판정은 바꾸지 않습니다."
        )
        st.markdown(
            "[계산 방법·전체 결과 확인](https://github.com/lovingnangni/emission-watch/blob/main/MATCHING_SENSITIVITY.md)"
        )

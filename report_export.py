"""Plain-text, evidence-only investigation report for one uploaded CSV row."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def make_report(row: pd.Series, reference: pd.DataFrame, features: list[str], threshold: float) -> str:
    """Report observations and comparison distances, not inferred fault causes."""
    matched = bool(row['비교 가능'])
    record_id = int(row['가장 가까운 2013년 기록'])
    neighbor = reference.loc[reference['record_id'] == record_id]
    if len(neighbor) != 1:
        raise ValueError('Reference record is missing or duplicated')
    past = neighbor.iloc[0]
    scaler = StandardScaler().fit(reference[features])
    spread = np.where(scaler.scale_ == 0, 1.0, scaler.scale_)
    comparisons = []
    for feature in features:
        current = float(row[feature]); previous = float(past[feature])
        comparisons.append((abs(current - previous) / spread[features.index(feature)], feature, current, previous))
    comparisons.sort(reverse=True)
    lines = [
        'Emission Watch | 업로드 기록 조사 리포트 (연구용)',
        f"업로드 행: {int(row['업로드 행'])}",
        '[모델 예측 · 관측 자료]',
        f"모델 예측 NOₓ: {float(row['예측 NOX']):.3f} mg/m³",
    ]
    if 'NOX' in row.index:
        lines.extend([
            f"측정 NOₓ: {float(row['NOX']):.3f} mg/m³",
            f"차이 (실제−예측): {float(row['예측오차 (실제−예측)']):+.3f} mg/m³",
        ])
    else:
        lines.append('측정 NOₓ: 미제공 · 예측오차 계산 불가')
    lines.extend([
        '[과거 운전 조건과의 거리]',
        f"2013년 최근접 기록: #{record_id}",
        f"표준화 거리: {float(row['표준화 거리']):.4f} / 탐색적 비교 기준: {threshold:.4f}",
        '상태: 탐색적 비교 가능' if matched else '상태: 비교 보류 (기준 밖)',
        '거리 기여가 큰 변수 3개 (2013년 자료의 표준편차 기준; 원인/영향도 아님):',
    ])
    for scaled_delta, name, current, previous in comparisons[:3]:
        lines.append(f'  {name}: 현재 {current:.4f}, 2013년 {previous:.4f}, 표준화 절대차 {scaled_delta:.3f}')
    if matched:
        lines.append(f"2013년 기록의 측정 NOₓ: {float(past['NOX']):.3f} mg/m³")
        if 'NOX' in row.index:
            lines.append(f"두 기록의 측정 NOₓ 차이: {float(row['NOX']) - float(past['NOX']):+.3f} mg/m³")
    else:
        lines.append('과거 측정 NOₓ는 근거로 제시하지 않습니다: 운전 조건 거리 기준 미통과.')
    lines.extend([
        '[해석 시 주의]',
        '모델은 2011~2012년 자료로 학습했으며 2015년 별도 평가 MAE 12.017 mg/m³, R² -0.466입니다.',
        '변수 차이가 크다는 사실은 NOₓ 변화의 원인이나 모델의 중요도를 뜻하지 않습니다.',
        '예측오차 또는 과거 기록 차이만으로 설비 고장, 배출규제 위반, 이상 원인을 판정할 수 없습니다.',
        '데이터 출처: UCI Gas Turbine CO and NOx Emission Data Set.',
    ])
    return '\n'.join(lines) + '\n'

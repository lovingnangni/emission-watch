"""Streamlit entry point for the verified Emission Watch data/model bundle."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import runpy
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import streamlit as st

NEEDED = ("numpy", "pandas", "plotly", "joblib", "sklearn")
missing = [name for name in NEEDED if importlib.util.find_spec(name) is None]
if missing:
    st.set_page_config(page_title="Emission Watch | 설치 환경 확인", page_icon="🌿")
    st.error("앱 실행 환경에 필수 패키지가 설치되지 않았습니다.")
    st.write("없는 모듈:", ", ".join(missing))
    st.write("실행 중인 Python 버전:", sys.version.split()[0])
    st.info("GitHub requirements.txt에 적힌 패키지가 누락됐습니다. Streamlit 배포 로그를 확인해 주세요.")
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
heldout_2015 = json.loads(Path(__file__).with_name("evaluation_2015_results.json").read_text(encoding="utf-8"))
if heldout_2015.get("year") != 2015 or heldout_2015.get("records") != 7384 or heldout_2015.get("model_retrained") is not False:
    raise RuntimeError("2015년 평가 결과를 확인해야 합니다.")
source = (bundle_dir / "app.py").read_text(encoding="utf-8")
replacements = {
    '    st.write("**2015년:** 사용하지 않음 (최종 평가용 보류)")':
        '    st.write("**2015년:** 학습·모델 선택에 사용하지 않은 별도 최종 평가 (결과 공개)")',
    'st.title("🌿 Emission Watch")': '''st.title("🌿 Emission Watch")
st.markdown("**배출 기록 조사 보조 도구** · 운전 조건으로 NOₓ를 예측하고, 측정값 및 비슷한 과거 기록과 함께 살펴봅니다.")
st.info("**3단계 사용법:** ① 아래 'CSV 업로드 · 내 기록 조사'에서 예시 CSV 다운로드 → ② 업로드해 전체 기록과 예측오차 확인 → ③ 한 행을 선택해 2013년 운전 기록과 비교하세요. 기존 2014년 공개 데이터 사례는 '기록 조사' 탭에서 볼 수 있습니다.")
st.caption("'비교 가능'은 탐색용 운전 변수 거리 기준을 통과했다는 뜻이고, '비교 보류'는 기준을 넘었다는 뜻입니다. 어느 쪽도 고장·안전·배출규제 판정이 아닙니다.")''',
    '    "**모델 상태 점검 필요:** 2014년에는 2013년보다 예측오차가 커지고 평균 오차 방향도 바뀌었습니다. "':
        '    "**모델 상태 점검 필요:** 2014년과 학습에 사용하지 않은 2015년 모두 2013년보다 예측오차가 큽니다. "',
    '    d.metric("유사 기록 기준 통과", f"{matched_ratio:.1%}")': '''    d.metric("유사 기록 기준 통과", f"{matched_ratio:.1%}")
    st.error(
        f"**2015년 최종 평가 (7,384건): MAE {heldout_2015['mae_mg_m3']:.3f} mg/m³, R² {heldout_2015['r2']:.3f}.** "
        "2011–2012년에 학습한 동일 모델이 2015년에서도 불안정했습니다. 새 설비의 정확도나 고장 탐지 성능은 입증되지 않았습니다."
    )''',
    '            {"평가 연도": "2014 · 탐색", "MAE": current["mae"],\n             "R²": current["r2"], "평균 오차(실제−예측)": current["bias"]},': '''            {"평가 연도": "2014 · 탐색", "MAE": current["mae"],
             "R²": current["r2"], "평균 오차(실제−예측)": current["bias"]},
            {"평가 연도": "2015 · 별도 최종 평가", "MAE": heldout_2015["mae_mg_m3"],
             "R²": heldout_2015["r2"], "평균 오차(실제−예측)": heldout_2015["mean_residual_measured_minus_predicted_mg_m3"]},''',
    '    "**읽는 법:** 2014년의 평균 오차가 음수인 것은 모델이 실제 NOₓ를 전반적으로 높게 예측했다는 뜻입니다. "':
        '    "**읽는 법:** 2014년과 2015년의 평균 오차가 음수인 것은 모델이 실제 NOₓ를 전반적으로 높게 예측했다는 뜻입니다. "',
    '- **검증:** 2013년 데이터로 예측 성능 평가. **탐색 시연:** 학습하지 않은 2014년 데이터로 예측오차와 유사 기록을 살펴봄.':
        '- **검증:** 2013년 데이터로 예측 성능 평가. **탐색 시연:** 학습하지 않은 2014년 데이터로 예측오차와 유사 기록을 살펴봄. **최종 평가:** 모델 재학습 없이 2015년 7,384건에서 MAE 12.017 mg/m³, R² -0.466 확인. 새 설비에서의 정확도를 보장하지 않음.',
    '    st.write("**첫 번째 후속 검증:** 보류 중인 2015년 데이터를 최종 평가로 사용하고, 연도별 편향이 반복되는지 확인합니다.")':
        '    st.write("**2015년 최종 평가 완료:** 2011–2012년 모델을 재학습하지 않고 2015년 7,384건에 적용했습니다. MAE 12.017 mg/m³, R² -0.466으로 일반화 한계를 확인했습니다.")',
    '    st.write("**보안:** 공개 데이터와 번들로 제공한 모델만 사용합니다. 외부 파일 업로드나 사용자 데이터 저장 기능은 없습니다.")':
        '    st.write("**보안:** 공개 데이터와 번들로 제공한 모델만 사용합니다. CSV 업로드는 이 페이지에서 분석하며 결과를 데이터베이스에 저장하는 기능은 없습니다. 민감한 설비 정보는 업로드하지 마세요.")',
}
for old, new in replacements.items():
    if source.count(old) != 1:
        raise RuntimeError("앱 원본이 변경되어 설명 패치를 안전하게 적용할 수 없습니다.")
    source = source.replace(old, new)
patched_app = bundle_dir / "app_explained.py"
patched_app.write_text(source, encoding="utf-8")
app_state = runpy.run_path(str(patched_app), run_name="__main__", init_globals={"heldout_2015": heldout_2015})

from core import load_artifacts
from matching_insights import render_matching_insights
from upload_analysis import render_upload_section


render_matching_insights(
    app_state["demo"], app_state["reference"],
    float(app_state["meta"]["matching_distance_threshold"]),
)

@st.cache_resource(show_spinner="CSV 분석용 모델을 준비하는 중입니다…")
def get_upload_model():
    return load_artifacts(bundle_dir)[3]


render_upload_section(bundle_dir, app_state["meta"], app_state["reference"], get_upload_model())

# A downloadable negative-test fixture; the upload validator is intentionally
# unchanged, so this exercises exactly the same path as a user's malformed CSV.
with st.expander("🧪 마지막 점검 · 필수 열이 빠진 CSV 테스트", expanded=False):
    st.write("아래 파일은 필수 운전 변수 **AT** 열을 일부러 제외한 테스트용 CSV입니다. 내려받아 위의 CSV 선택 칸에 업로드해 보세요.")
    feature_names = list(app_state["meta"]["features"])
    missing_feature = feature_names[0]
    remaining = [name for name in feature_names if name != missing_feature]
    fixture_csv = (",".join(remaining) + ",NOX\n" + ",".join("1" for _ in remaining) + ",1\n").encode("utf-8-sig")
    st.download_button(
        "필수 열 누락 테스트 CSV 내려받기",
        data=fixture_csv,
        file_name="emission_watch_missing_column_test.csv",
        mime="text/csv",
    )
    st.info(f"**기대 결과:** 앱이 멈추거나 예측값을 만들지 않고, 빨간 오류 안내에 '필수 운전 변수 누락: {missing_feature}'가 나와야 합니다. 테스트 후에는 정상 예시 CSV를 다시 선택하세요.")

import os
import sys
import subprocess
from datetime import datetime

import pandas as pd
import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium


# ============================================================
# 0. 기본 설정
# ============================================================

st.set_page_config(
    page_title="실시간 응급실 가용병상 지도",
    layout="wide"
)

DATA_PATH = "data/hospital_er_preprocessed_wide.csv"
PREPROCESS_SCRIPT = "03_realtime_data.py"


# ============================================================
# 1. 카테고리 정의
# ============================================================

CATEGORY_GROUPS = {
    "응급실/입원 병상": {
        "응급실 일반 병상": "avail_er_general_beds",
        "소아 병상": "avail_pediatric_beds",
        "일반 입원실": "avail_inpatient_general_beds",
        "응급전용 입원실": "avail_er_dedicated_inpatient_beds",
        "응급전용 소아입원실": "avail_er_dedicated_pediatric_inpatient_beds",
        "외상전용 입원실": "avail_trauma_dedicated_inpatient_beds",
        "정신과 폐쇄병동": "avail_psychiatric_closed_ward_beds",
    },
    "중환자실": {
        "일반 중환자실": "avail_icu_general",
        "내과 중환자실": "avail_icu_internal_medicine",
        "외과 중환자실": "avail_icu_surgery",
        "신경과 중환자실": "avail_icu_neurology",
        "신경외과 중환자실": "avail_icu_neurosurgery",
        "신생아 중환자실": "avail_icu_neonatal",
        "소아 중환자실": "avail_icu_pediatric",
        "심장내과 중환자실": "avail_icu_cardiology",
        "흉부외과 중환자실": "avail_icu_thoracic_surgery",
        "화상 중환자실": "avail_icu_burn",
        "외상 중환자실": "avail_icu_trauma",
        "음압격리 중환자실": "avail_icu_negative_pressure_isolation",
        "응급전용 중환자실": "avail_er_dedicated_icu",
        "응급전용 소아중환자실": "avail_er_dedicated_pediatric_icu",
    },
    "격리 병상": {
        "응급실 음압 격리 병상": "avail_er_negative_pressure_isolation_beds",
        "응급실 일반 격리 병상": "avail_er_general_isolation_beds",
        "격리진료구역 음압격리": "avail_isolation_negative_pressure_area_beds",
        "격리진료구역 일반격리": "avail_isolation_general_area_beds",
        "소아 음압격리": "avail_pediatric_negative_pressure_isolation",
        "소아 일반격리": "avail_pediatric_general_isolation",
        "입원실 음압격리": "avail_inpatient_negative_pressure_isolation",
        "코호트 격리": "avail_cohort_isolation",
    },
    "수술/처치 공간": {
        "수술실": "avail_operating_rooms",
        "외상전용 수술실": "avail_trauma_dedicated_operating_rooms",
        "분만실": "delivery_room_status",
        "화상전용처치실": "avail_burn_treatment_room",
        "외상소생실": "avail_trauma_resuscitation_room",
        "외상환자진료구역": "avail_trauma_patient_care_area",
    },
    "장비": {
        "CT 가능": "available_ct_yn",
        "MRI 가능": "available_mri_yn",
        "혈관촬영기 가능": "available_angio_yn",
        "인공호흡기 가능": "available_ventilator_yn",
        "소아 인공호흡기 가능": "pediatric_ventilator_status",
        "인공호흡기 조산아 가능": "available_ventilator_premature_yn",
        "인큐베이터 가능": "available_incubator_yn",
        "CRRT 가능": "available_crrt_yn",
        "ECMO 가능": "available_ecmo_yn",
        "고압산소치료기 가능": "available_hyperbaric_oxygen_yn",
        "중심체온조절유도기 가능": "available_targeted_temperature_management_yn",
        "구급차 가능": "available_ambulance_yn",
    },
    "중증질환/수술/시술 수용": {
        "심근경색 재관류중재술": "severe_myocardial_infarction_reperfusion_yn",
        "뇌경색 재관류중재술": "severe_cerebral_infarction_reperfusion_yn",
        "거미막하출혈 수술": "severe_subarachnoid_hemorrhage_surgery_yn",
        "기타 뇌출혈 수술": "severe_other_cerebral_hemorrhage_surgery_yn",
        "흉부 대동맥 응급": "severe_thoracic_aortic_emergency_yn",
        "복부 대동맥 응급": "severe_abdominal_aortic_emergency_yn",
        "담낭질환": "severe_gallbladder_disease_yn",
        "담도포함질환": "severe_biliary_tract_disease_yn",
        "비외상 복부응급수술": "severe_nontraumatic_abdominal_emergency_surgery_yn",
        "영유아 장중첩/폐색": "severe_infant_intussusception_obstruction_yn",
        "성인 위장관 응급내시경": "severe_adult_gi_emergency_endoscopy_yn",
        "영유아 위장관 응급내시경": "severe_infant_gi_emergency_endoscopy_yn",
        "성인 기관지 응급내시경": "severe_adult_bronchial_emergency_endoscopy_yn",
        "영유아 기관지 응급내시경": "severe_infant_bronchial_emergency_endoscopy_yn",
        "저체중 출생아 집중치료": "severe_low_birth_weight_infant_intensive_care_yn",
        "산부인과 응급 분만": "severe_obstetric_delivery_yn",
        "산과수술": "severe_obstetric_surgery_yn",
        "부인과수술": "severe_gynecologic_surgery_yn",
        "중증화상 전문치료": "severe_burn_specialized_treatment_yn",
        "수족지접합": "severe_finger_toe_replantation_yn",
        "수족지접합 외": "severe_other_limb_replantation_yn",
        "응급투석 HD": "severe_emergency_dialysis_hd_yn",
        "응급투석 CRRT": "severe_emergency_dialysis_crrt_yn",
        "정신과적 응급 폐쇄병동": "severe_psychiatric_emergency_closed_ward_yn",
        "안과적 응급수술": "severe_ophthalmic_emergency_surgery_yn",
        "성인 영상의학 혈관중재": "severe_adult_interventional_radiology_yn",
        "영유아 영상의학 혈관중재": "severe_infant_interventional_radiology_yn",
    },
}

CATEGORY_TO_COLUMNS = {
    label: cols
    for group in CATEGORY_GROUPS.values()
    for label, cols in group.items()
}


# ============================================================
# 2. 데이터 로드 함수
# ============================================================

@st.cache_data(show_spinner=False)
def load_data(path):
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        dtype={
            "hpid": str,
            "realtime_updated_at": str,
            "collected_at": str,
        }
    )

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])

    return df


def parse_datetime_yyyymmddhhmmss(x):
    if pd.isna(x):
        return pd.NaT

    x = str(x).strip()

    if "e+" in x.lower():
        try:
            x = str(int(float(x)))
        except Exception:
            return pd.NaT

    if x.isdigit() and len(x) == 14:
        return pd.to_datetime(x, format="%Y%m%d%H%M%S", errors="coerce")

    return pd.to_datetime(x, errors="coerce")


# ============================================================
# 3. 조건 필터 함수
# ============================================================

def is_available(series):
    numeric = pd.to_numeric(series, errors="coerce")
    numeric_available = numeric > 0

    text = series.astype(str).str.strip().str.upper()
    yn_available = text.isin(["Y", "가능", "TRUE", "1"])

    return numeric_available | yn_available


def get_condition_for_label(df, label):
    cols = CATEGORY_TO_COLUMNS.get(label)

    if cols is None:
        return pd.Series(False, index=df.index)

    if isinstance(cols, str):
        cols = [cols]

    conditions = []

    for col in cols:
        if col not in df.columns:
            continue

        conditions.append(is_available(df[col]))

    if not conditions:
        return pd.Series(False, index=df.index)

    result = conditions[0]

    for cond in conditions[1:]:
        result = result | cond

    return result


def filter_by_categories(df, selected_labels, mode):
    if not selected_labels:
        return df.copy()

    conditions = [get_condition_for_label(df, label) for label in selected_labels]

    if not conditions:
        return df.iloc[0:0].copy()

    if mode == "모두 충족":
        final_condition = conditions[0]

        for cond in conditions[1:]:
            final_condition = final_condition & cond

    else:
        final_condition = conditions[0]

        for cond in conditions[1:]:
            final_condition = final_condition | cond

    return df[final_condition].copy()


def format_value_for_user(value):
    if pd.isna(value):
        return "-"

    text = str(value).strip()

    if text.upper() == "Y":
        return "가능"

    if text.upper() == "N":
        return "불가능"

    if text.upper() == "UNKNOWN":
        return "정보 미제공"

    numeric = pd.to_numeric(text, errors="coerce")

    if pd.notna(numeric):
        if numeric == int(numeric):
            return f"{int(numeric)}개"

        return f"{numeric}개"

    return text


def build_selected_status_html(row, selected_labels):
    if not selected_labels:
        return "선택된 카테고리가 없어 전체 병원을 표시 중입니다.<br>"

    html = "<b>선택 조건 상태</b><br>"

    for label in selected_labels:
        cols = CATEGORY_TO_COLUMNS.get(label)

        if cols is None:
            continue

        if isinstance(cols, str):
            cols = [cols]

        values = []

        for col in cols:
            if col in row.index:
                values.append(format_value_for_user(row.get(col)))

        if values:
            html += f"- {label}: {', '.join(values)}<br>"

    return html


def calculate_selected_resource_count(row, selected_labels):
    total = 0

    for label in selected_labels:
        cols = CATEGORY_TO_COLUMNS.get(label)

        if cols is None:
            continue

        if isinstance(cols, str):
            cols = [cols]

        for col in cols:
            if col not in row.index:
                continue

            value = pd.to_numeric(row[col], errors="coerce")

            if pd.notna(value):
                total += max(value, 0)

    return int(total)


# ============================================================
# 4. 새로고침 함수
# ============================================================

def run_realtime_update(update_sido, update_sigungu):
    if not os.path.exists(PREPROCESS_SCRIPT):
        st.error(f"{PREPROCESS_SCRIPT} 파일을 찾을 수 없습니다.")
        return False

    before_time = datetime.now()

    if update_sido == "전국":
        update_sigungu = "전체"
        target_text = "전국 전체"
    elif update_sigungu == "전체":
        target_text = f"{update_sido} 전체"
    else:
        target_text = f"{update_sido} {update_sigungu}"

    progress = st.progress(0)
    status = st.empty()

    status.write(f"1/3 {target_text} 실시간 데이터 갱신 중...")
    progress.progress(20)

    command = [
        sys.executable,
        PREPROCESS_SCRIPT,
        "--sido",
        update_sido,
        "--sigungu",
        update_sigungu,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=os.getcwd(),
    )

    progress.progress(70)

    if result.returncode != 0:
        st.error("실시간 업데이트 중 오류가 발생했습니다.")
        st.code(result.stderr[-5000:])
        st.code(result.stdout[-5000:])
        return False

    after_time = datetime.now()
    progress.progress(100)

    status.write("3/3 최신 CSV 저장 완료")

    # 03_realtime_data.py가 남긴 상태 파일 읽기
    status_file = os.path.join("data", "last_update_status.txt")

    if os.path.exists(status_file):
        with open(status_file, "r", encoding="utf-8") as f:
            update_status_text = f.read().strip()
    else:
        update_status_text = "상태 파일 없음"

    st.session_state["last_update_message"] = (
        f"업데이트 실행: {before_time.strftime('%H:%M:%S')} → {after_time.strftime('%H:%M:%S')} "
        f"/ 대상: {target_text}\n\n{update_status_text}"
    )

    st.cache_data.clear()

    return True

# ============================================================
# 5. 화면 구성
# ============================================================

st.title("실시간 응급실 가용병상 지도")
st.caption("공공데이터 API 호출 시점 기준의 응급의료기관 가용자원 지도")

if not os.path.exists(DATA_PATH):
    st.error(f"{DATA_PATH} 파일이 없습니다. 먼저 1단계 전처리 코드를 실행하세요.")
    st.stop()

df = load_data(DATA_PATH)

df["realtime_updated_at_parsed"] = df["realtime_updated_at"].apply(parse_datetime_yyyymmddhhmmss)
df["collected_at_parsed"] = pd.to_datetime(df["collected_at"], errors="coerce")


# ============================================================
# 6. 사이드바
# ============================================================

with st.sidebar:
    st.header("검색 조건")

    sido_options = ["전국"] + sorted(df["sido"].dropna().unique().tolist())
    selected_sido = st.selectbox("시도 선택", sido_options)

    if selected_sido == "전국":
        sigungu_options = ["전체"]
    else:
        sigungu_options = ["전체"] + sorted(
            df.loc[df["sido"] == selected_sido, "sigungu"]
            .dropna()
            .unique()
            .tolist()
        )

    selected_sigungu = st.selectbox("시군구 선택", sigungu_options)


    if st.button("🔄 현재 선택 지역 실시간 데이터 업데이트", width="stretch"):
        # 현재 선택 상태 그대로 업데이트 범위 결정
        if selected_sido == "전국":
            update_sido = "전국"
            update_sigungu = "전체"
            target_text = "전국 전체"

        elif selected_sigungu == "전체":
            update_sido = selected_sido
            update_sigungu = "전체"
            target_text = f"{selected_sido} 전체"

        else:
            update_sido = selected_sido
            update_sigungu = selected_sigungu
            target_text = f"{selected_sido} {selected_sigungu}"

        with st.spinner(f"{target_text} 최신 데이터를 다시 수집하는 중입니다..."):
            ok = run_realtime_update(update_sido, update_sigungu)

        if ok:
            st.success("업데이트 완료")
            st.rerun()

    if "last_update_message" in st.session_state:
        st.info(st.session_state["last_update_message"])

    st.divider()

    condition_mode = st.radio(
        "다중 조건 적용 방식",
        ["모두 충족", "하나라도 충족"],
        index=0,
        help="응급 상황에서 특정 자원이 모두 필요한 경우에는 '모두 충족'이 적합합니다."
    )

    selected_labels = []

    st.subheader("카테고리 선택")

    for group_name, items in CATEGORY_GROUPS.items():
        with st.expander(group_name, expanded=False):
            labels = list(items.keys())
            picked = st.multiselect(
                group_name,
                labels,
                key=f"multi_{group_name}"
            )
            selected_labels.extend(picked)

    st.divider()
    st.write("선택된 조건 수:", len(selected_labels))


# ============================================================
# 7. 지역 필터
# ============================================================

region_filtered = df.copy()

if selected_sido != "전국":
    region_filtered = region_filtered[region_filtered["sido"] == selected_sido]

if selected_sigungu != "전체":
    region_filtered = region_filtered[region_filtered["sigungu"] == selected_sigungu]

# 카테고리 필터 전의 지역 기준 데이터
filtered = region_filtered.copy()

# ============================================================
# 8. 카테고리 필터
# ============================================================

filtered = filter_by_categories(filtered, selected_labels, condition_mode)


# ============================================================
# 9. 요약 지표
# ============================================================

left, mid, right, fourth = st.columns(4)

# 지도에 실제 표시되는 병원 수는 카테고리 필터까지 적용된 filtered 기준
display_df = filtered.copy()

# 시간 정보는 현재 선택 지역 기준으로 계산
# 즉, 카테고리를 바꿔도 선택 지역의 최신 갱신 상태를 확인할 수 있음
metric_df = region_filtered.copy()

valid_update_df = metric_df[
    metric_df["realtime_updated_at_parsed"].notna()
].copy()

valid_collect_df = metric_df[
    metric_df["collected_at_parsed"].notna()
].copy()

# 실시간 데이터가 실제로 있는 병원 판단
important_realtime_cols = [
    "avail_er_general_beds",
    "avail_operating_rooms",
    "avail_icu_general",
    "avail_inpatient_general_beds",
    "delivery_room_status",
    "available_ct_yn",
    "available_mri_yn",
    "realtime_updated_at",
]

existing_realtime_cols = [
    col for col in important_realtime_cols
    if col in metric_df.columns
]

if existing_realtime_cols:
    realtime_available_count = metric_df[existing_realtime_cols].notna().any(axis=1).sum()
else:
    realtime_available_count = 0

with left:
    st.metric("표시 병원 수", f"{len(display_df):,}")

with mid:
    if len(valid_update_df) > 0:
        latest_update = valid_update_df["realtime_updated_at_parsed"].max()
        st.metric(
            "선택 지역 가장 최근 병상 갱신",
            latest_update.strftime("%Y-%m-%d %H:%M")
        )
    else:
        st.metric("선택 지역 가장 최근 병상 갱신", "-")

with right:
    if len(valid_collect_df) > 0:
        latest_collect = valid_collect_df["collected_at_parsed"].max()
        st.metric(
            "선택 지역 데이터 수집 시각",
            latest_collect.strftime("%Y-%m-%d %H:%M")
        )
    else:
        st.metric("선택 지역 데이터 수집 시각", "-")

with fourth:
    st.metric(
        "선택 지역 실시간 정보 보유 병원",
        f"{realtime_available_count:,} / {len(metric_df):,}"
    )

# ============================================================
# 10. 지도 중심 설정
# ============================================================

if len(filtered) > 0:
    center_lat = filtered["lat"].mean()
    center_lon = filtered["lon"].mean()
else:
    center_lat = df["lat"].mean()
    center_lon = df["lon"].mean()

if selected_sido == "전국":
    zoom_start = 7
elif selected_sigungu == "전체":
    zoom_start = 10
else:
    zoom_start = 12


# ============================================================
# 11. 지도 생성
# ============================================================

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=zoom_start,
    tiles="CartoDB positron"
)

marker_cluster = MarkerCluster(name="병원 클러스터").add_to(m)

for _, row in filtered.iterrows():
    hospital_name = row.get("hospital_name", "-")
    addr = row.get("dutyAddr", "-")
    tel_main = row.get("tel_main", "-")
    emergency_tel = row.get("emergency_tel", "-")
    updated_at = row.get("realtime_updated_at_parsed", pd.NaT)

    selected_count = calculate_selected_resource_count(row, selected_labels)
    selected_status_html = build_selected_status_html(row, selected_labels)

    popup_html = f"""
    <div style="width: 320px;">
        <h4>{hospital_name}</h4>

        <b>주소</b><br>{addr}<br><br>

        <b>대표전화</b>: {tel_main}<br>
        <b>응급실 전화</b>: {emergency_tel}<br><br>

        <b>응급실 일반 병상</b>: {format_value_for_user(row.get("avail_er_general_beds", None))}<br>
        <b>수술실</b>: {format_value_for_user(row.get("avail_operating_rooms", None))}<br>
        <b>일반 중환자실</b>: {format_value_for_user(row.get("avail_icu_general", None))}<br>
        <b>일반 입원실</b>: {format_value_for_user(row.get("avail_inpatient_general_beds", None))}<br>
        <b>분만실 가능 여부</b>: {format_value_for_user(row.get("delivery_room_status", None))}<br>
        <b>기준 분만실 수</b>: {format_value_for_user(row.get("standard_delivery_rooms", None))}<br><br>

        {selected_status_html}

        <br>
        <b>병상정보 갱신시각</b><br>
        {updated_at.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(updated_at) else "-"}
    </div>
    """

    tooltip = f"{hospital_name} | 선택 자원 합계: {selected_count}" if selected_labels else hospital_name

    if selected_count > 0:
        radius = min(18, 6 + selected_count ** 0.5)

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius,
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=tooltip,
            fill=True,
            fill_opacity=0.7,
            opacity=0.8,
        ).add_to(marker_cluster)
    else:
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=tooltip,
        ).add_to(marker_cluster)

folium.LayerControl().add_to(m)


# ============================================================
# 12. 지도 출력
# ============================================================

st_folium(
    m,
    width=None,
    height=720,
    returned_objects=["last_clicked", "bounds", "zoom"],
    key="er_map"
)


# ============================================================
# 13. 하단 데이터 테이블
# ============================================================

with st.expander("현재 지도에 표시된 병원 데이터 보기", expanded=False):
    show_cols = [
        "hospital_name",
        "sido",
        "sigungu",
        "dutyAddr",
        "emergency_tel",
        "avail_er_general_beds",
        "avail_operating_rooms",
        "avail_icu_general",
        "avail_inpatient_general_beds",
        "delivery_room_status",
        "standard_delivery_rooms",
        "realtime_updated_at_parsed",
    ]

    show_cols = [col for col in show_cols if col in filtered.columns]

    table_df = filtered[show_cols].copy()

    display_cols = [
        "avail_er_general_beds",
        "avail_operating_rooms",
        "avail_icu_general",
        "avail_inpatient_general_beds",
        "delivery_room_status",
        "standard_delivery_rooms",
    ]

    for col in display_cols:
        if col in table_df.columns:
            table_df[col] = table_df[col].apply(format_value_for_user)

    st.dataframe(
        table_df.sort_values(["sido", "sigungu", "hospital_name"]),
        width="stretch",
        height=350
    )

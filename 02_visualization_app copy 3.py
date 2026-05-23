import os
import sys
import json
import subprocess
from datetime import datetime

import pandas as pd
import streamlit as st
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
from branca.element import MacroElement
from jinja2 import Template


# ============================================================
# 0. 기본 설정
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def project_path(*parts):
    return os.path.join(BASE_DIR, *parts)

st.set_page_config(
    page_title="실시간 응급실 가용병상 지도",
    page_icon="🚑",
    layout="wide"
)

def apply_design_system():
    st.markdown(
        """
        <style>
        :root {
            --er-bg: #f7f9fc;
            --er-primary: #2563eb;
            --er-primary-dark: #1d4ed8;
            --er-success: #059669;
            --er-danger: #dc2626;
            --er-warning: #d97706;
            --er-surface: #ffffff;
            --er-surface-soft: #f1f5f9;
            --er-border: #d8e0ea;
            --er-text: #172033;
            --er-muted: #64748b;
            --er-radius: 8px;
            --er-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
        }

        html, body, [data-testid="stAppViewContainer"] {
            background: var(--er-bg);
            color: var(--er-text);
            font-family: "Pretendard", "Noto Sans KR", "Segoe UI", sans-serif;
        }

        [data-testid="stHeader"] {
            background: rgba(247, 249, 252, 0.86);
            backdrop-filter: blur(10px);
        }

        .block-container {
            padding-top: 2.2rem;
            padding-bottom: 2.6rem;
            max-width: 1440px;
        }

        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--er-border);
        }

        h1, h2, h3 {
            color: var(--er-text);
            letter-spacing: 0;
        }

        .er-hero {
            padding: 1.2rem 0 0.9rem;
        }

        .er-eyebrow {
            color: var(--er-primary);
            font-size: 0.86rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .er-hero h1, h1 {
            font-size: 2.15rem;
            line-height: 1.18;
            margin: 0 0 0.35rem;
            color: var(--er-text);
        }

        .er-subtitle {
            color: var(--er-muted);
            font-size: 1rem;
            line-height: 1.65;
            max-width: 820px;
            margin: 0.25rem 0 0;
        }

        .er-section-title {
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--er-text);
            margin: 0.7rem 0 0.35rem;
        }

        .er-inline-note {
            color: var(--er-muted);
            font-size: 0.9rem;
            line-height: 1.55;
            margin: 0.15rem 0 0.75rem;
        }

        .er-status-strip {
            border: 1px solid var(--er-border);
            background: var(--er-surface);
            border-radius: var(--er-radius);
            padding: 0.85rem 1rem;
            box-shadow: var(--er-shadow);
            color: var(--er-muted);
            font-size: 0.94rem;
            line-height: 1.5;
            margin: 0.35rem 0 1rem;
        }

        .er-status-strip strong {
            color: var(--er-text);
        }

        .er-empty {
            border: 1px dashed #cbd5e1;
            background: #ffffff;
            border-radius: var(--er-radius);
            padding: 1.15rem 1.25rem;
            color: var(--er-muted);
            margin: 0.75rem 0 1rem;
        }

        [data-testid="stMetric"] {
            background: var(--er-surface);
            border: 1px solid var(--er-border);
            border-radius: var(--er-radius);
            padding: 0.95rem 1rem;
            box-shadow: var(--er-shadow);
            min-height: 104px;
        }

        [data-testid="stMetricLabel"] {
            color: var(--er-muted);
            font-size: 0.88rem;
        }

        [data-testid="stMetricValue"] {
            color: var(--er-text);
            font-size: 1.62rem;
            font-weight: 800;
        }

        .stButton > button {
            border-radius: var(--er-radius);
            font-weight: 800;
            border: 1px solid var(--er-border);
        }

        .stButton > button[kind="primary"] {
            background: var(--er-primary);
            border-color: var(--er-primary);
        }

        .stButton > button[kind="primary"]:hover {
            background: var(--er-primary-dark);
            border-color: var(--er-primary-dark);
        }

        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div,
        [data-baseweb="tag"] {
            border-radius: var(--er-radius);
        }

        [data-testid="stExpander"] {
            background: var(--er-surface);
            border: 1px solid var(--er-border);
            border-radius: var(--er-radius);
            box-shadow: none;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--er-border);
            border-radius: var(--er-radius);
            overflow: hidden;
            box-shadow: var(--er-shadow);
        }

        iframe {
            border-radius: var(--er-radius);
            border: 1px solid var(--er-border);
            box-shadow: var(--er-shadow);
        }

        .leaflet-popup-content-wrapper {
            border-radius: 8px;
        }

        .leaflet-popup-content {
            font-family: "Pretendard", "Noto Sans KR", "Segoe UI", sans-serif;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_design_system()

DATA_PATH = project_path("data", "hospital_er_preprocessed_wide.csv")
PREPROCESS_SCRIPT = project_path("03_realtime_data.py")

SIDO_GEOJSON_PATH = project_path("data", "korea_sido.geojson")
SIGUNGU_GEOJSON_PATH = project_path("data", "korea_sigungu.geojson")
UPDATE_STATUS_JSON_PATH = project_path("data", "last_update_status.json")
UPDATE_STATUS_TEXT_PATH = project_path("data", "last_update_status.txt")

EXCLUDE_SIDO = ["제주특별자치도"]

# 줌 단계
ZOOM_SIGUNGU_LEVEL = 9      # 이 이상이면 시군구 도형
ZOOM_HOSPITAL_LEVEL = 11    # 이 이상이면 병원 핀포인트 표시
NATIONWIDE_VALUE = "전국"
ALL_SIGUNGU_VALUE = "전체"
MAX_HOSPITAL_MARKERS = 450

ENGLISH_SIDO_ALIASES = {
    "Seoul": "서울특별시",
    "Busan": "부산광역시",
    "Daegu": "대구광역시",
    "Incheon": "인천광역시",
    "Gwangju": "광주광역시",
    "Daejeon": "대전광역시",
    "Ulsan": "울산광역시",
    "Sejong": "세종특별자치시",
    "Gyeonggi": "경기도",
    "Gyeonggi-do": "경기도",
    "Gangwon": "강원특별자치도",
    "Gangwon-do": "강원특별자치도",
    "Chungbuk": "충청북도",
    "Chungcheongbuk-do": "충청북도",
    "Chungnam": "충청남도",
    "Chungcheongnam-do": "충청남도",
    "Jeonbuk": "전북특별자치도",
    "Jeollabuk-do": "전북특별자치도",
    "Jeonnam": "전라남도",
    "Jeollanam-do": "전라남도",
    "Gyeongbuk": "경상북도",
    "Gyeongsangbuk-do": "경상북도",
    "Gyeongnam": "경상남도",
    "Gyeongsangnam-do": "경상남도",
    "Jeju": "제주특별자치도",
    "Jeju-do": "제주특별자치도",
}

ENGLISH_SIGUNGU_ALIASES = {
    "Buk": "북구",
    "Nam": "남구",
    "Dong": "동구",
    "Seo": "서구",
    "Gangseo": "강서구",
    "Geum-cheon": "금천구",
    "Guro": "구로구",
    "Gwanak": "관악구",
    "Gwang-jin": "광진구",
    "Gangnam": "강남구",
    "Gandong": "강동구",
    "Gangdong": "강동구",
    "Gangbuk": "강북구",
    "Dobong": "도봉구",
    "Dong-daemun": "동대문구",
    "Dongdaemun": "동대문구",
    "Dongjak": "동작구",
    "Eun-pyeong": "은평구",
    "Eunpyeong": "은평구",
    "Jongno": "종로구",
    "Jongro": "종로구",
    "Jung": "중구",
    "Jungnang": "중랑구",
    "Mapo": "마포구",
    "Nowon": "노원구",
    "Seocho": "서초구",
    "Seodaemun": "서대문구",
    "Seongbuk": "성북구",
    "Seongdong": "성동구",
    "Songpa": "송파구",
    "Yangcheon": "양천구",
    "Yeongdeungpo": "영등포구",
    "Yongsan": "용산구",
    "Busanjin": "부산진구",
    "Dongnae": "동래구",
    "Geumjeong": "금정구",
    "Haeundae": "해운대구",
    "Saha": "사하구",
    "Sasang": "사상구",
    "Suyeong": "수영구",
    "Yeonje": "연제구",
    "Yeongdo": "영도구",
    "Gijang": "기장군",
    "Bupyeong": "부평구",
    "Gyeyang": "계양구",
    "Michuhol": "미추홀구",
    "Namdong": "남동구",
    "Yeonsu": "연수구",
    "Ganghwa": "강화군",
    "Ongjin": "옹진군",
    "Suwon": "수원시",
    "Seongnam": "성남시",
    "Goyang": "고양시",
    "Yongin": "용인시",
    "Bucheon": "부천시",
    "Ansan": "안산시",
    "Anyang": "안양시",
    "Namyangju": "남양주시",
    "Hwaseong": "화성시",
    "Pyeongtaek": "평택시",
    "Uijeongbu": "의정부시",
    "Siheung": "시흥시",
    "Gimpo": "김포시",
    "Gwangmyeong": "광명시",
    "Gwangju": "광주시",
    "Gunpo": "군포시",
    "Hanam": "하남시",
    "Osan": "오산시",
    "Icheon": "이천시",
    "Anseong": "안성시",
    "Uiwang": "의왕시",
    "Pocheon": "포천시",
    "Yangju": "양주시",
    "Dongducheon": "동두천시",
    "Gwacheon": "과천시",
    "Yeoju": "여주시",
    "Guri": "구리시",
    "Paju": "파주시",
    "Gapyeong": "가평군",
    "Yangpyeong": "양평군",
    "Yeoncheon": "연천군",
    "Chuncheon": "춘천시",
    "Wonju": "원주시",
    "Gangneung": "강릉시",
    "Donghae": "동해시",
    "Taebaek": "태백시",
    "Sokcho": "속초시",
    "Samcheok": "삼척시",
    "Hongcheon": "홍천군",
    "Hoengseong": "횡성군",
    "Yeongwol": "영월군",
    "Pyeongchang": "평창군",
    "Jeongseon": "정선군",
    "Cheorwon": "철원군",
    "Hwacheon": "화천군",
    "Yanggu": "양구군",
    "Inje": "인제군",
    "Goseong": "고성군",
    "Yangyang": "양양군",
    "Gwangsan": "광산구",
    "Ansoeng": "안성시",
    "Ulju": "울주군",
    "Jeju": "제주시",
    "Seogwipo": "서귀포시",
}

CONTEXTUAL_SIGUNGU_ALIASES = {
    ("인천광역시", "Nam"): "미추홀구",
}


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
# 2. 데이터 로드
# ============================================================

@st.cache_data(show_spinner=False)
def load_data(path, refresh_token=0):
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


@st.cache_data(show_spinner=False)
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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


def format_datetime_short(value):
    if pd.isna(value):
        return "-"

    return value.strftime("%m.%d %H:%M")


def format_datetime_full(value):
    if pd.isna(value):
        return "-"

    return value.strftime("%Y-%m-%d %H:%M")


def load_update_status_json(path=UPDATE_STATUS_JSON_PATH):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def get_nested_value(payload, key_candidates):
    if not isinstance(payload, dict):
        return None

    for key in key_candidates:
        if key in payload and payload[key] not in [None, ""]:
            return payload[key]

    for nested_key in ["status", "summary", "result", "metadata", "data"]:
        nested_payload = payload.get(nested_key)

        if isinstance(nested_payload, dict):
            nested_value = get_nested_value(nested_payload, key_candidates)

            if nested_value not in [None, ""]:
                return nested_value

    return None


def format_status_bool(value):
    if value is True:
        return "성공"

    if value is False:
        return "실패"

    return None


def format_update_status_summary(status_payload):
    if not isinstance(status_payload, dict) or not status_payload:
        return None

    lines = []
    success = get_nested_value(status_payload, ["success", "ok"])
    realtime_success = get_nested_value(status_payload, ["realtime_update_success"])
    severe_success = get_nested_value(status_payload, ["severe_update_success"])
    api_quota_exceeded = get_nested_value(status_payload, ["api_quota_exceeded"])
    run_at = get_nested_value(status_payload, ["run_at", "updated_at", "collected_at"])
    target = get_nested_value(status_payload, ["target", "target_text", "region"])
    latest_source_time = get_nested_value(
        status_payload,
        [
            "current_latest_realtime_source_updated_at",
            "current_latest_updated_at",
            "latest_realtime_source_updated_at",
            "latest_updated_at",
        ],
    )

    success_text = format_status_bool(success)

    if success_text:
        lines.append(f"업데이트 결과: {success_text}")

    if run_at:
        lines.append(f"업데이트 실행 시각: {run_at}")

    if target:
        lines.append(f"업데이트 대상: {target}")

    if latest_source_time:
        lines.append(f"현재 데이터의 최신 병상정보 갱신시각: {latest_source_time}")

    realtime_success_text = format_status_bool(realtime_success)
    severe_success_text = format_status_bool(severe_success)

    if realtime_success_text:
        lines.append(f"실시간 병상 업데이트: {realtime_success_text}")

    if severe_success_text:
        lines.append(f"중증질환 업데이트: {severe_success_text}")

    if api_quota_exceeded is True:
        lines.append("API 호출 제한 또는 할당량 문제가 감지되었습니다.")

    realtime_count = get_nested_value(status_payload, ["realtime_updated_count"])
    severe_count = get_nested_value(status_payload, ["severe_updated_count"])

    if realtime_count is not None:
        lines.append(f"실시간 병상 갱신 병원 수: {realtime_count}")

    if severe_count is not None:
        lines.append(f"중증질환 갱신 병원 수: {severe_count}")

    notes = get_nested_value(status_payload, ["notes", "messages", "message", "error"])

    if isinstance(notes, list):
        for note in notes:
            if note:
                lines.append(str(note))
    elif notes:
        lines.append(str(notes))

    return "\n".join(lines) if lines else None


def load_update_status_text(path=UPDATE_STATUS_TEXT_PATH):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            status_text = f.read().strip()
    except OSError:
        return None

    return status_text or None


def should_limit_hospital_markers(filtered_df, selected_sido, selected_sigungu):
    return (
        len(filtered_df) > MAX_HOSPITAL_MARKERS
        and (
            selected_sido == NATIONWIDE_VALUE
            or selected_sigungu == ALL_SIGUNGU_VALUE
        )
    )


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


# ============================================================
# 4. GeoJSON 행정구역 이름 처리
# ============================================================

def pick_property(props, candidates):
    for key in candidates:
        if key in props and props[key] not in [None, ""]:
            return str(props[key]).strip()

    return None


def has_korean_text(value):
    if value is None:
        return False

    return any("가" <= ch <= "힣" for ch in str(value))


def pick_korean_property(props, korean_candidates, fallback_candidates):
    for key in korean_candidates:
        if key in props and props[key] not in [None, ""]:
            value = str(props[key]).strip()

            if value and has_korean_text(value):
                return value

    for key in korean_candidates:
        if key in props and props[key] not in [None, ""]:
            value = str(props[key]).strip()

            if value:
                return value

    return pick_property(props, fallback_candidates)


def get_sido_name_from_props(props):
    return pick_korean_property(
        props,
        [
            "sido",
            "SIDO",
            "SIDO_NM",
            "sidonm",
            "CTP_KOR_NM",
            "ctprvn_nm",
        ],
        [
            "sido",
            "SIDO",
            "SIDO_NM",
            "sidonm",
            "CTP_KOR_NM",
            "ctprvn_nm",
            "CTP_ENG_NM",
            "NAME_1",
            "name",
            "NAME",
            "adm_nm",
            "adm_nm1",
        ]
    )


def get_sigungu_name_from_props(props):
    return pick_korean_property(
        props,
        [
            "sigungu",
            "SIGUNGU",
            "SIG_KOR_NM",
            "sgg_nm",
        ],
        [
            "sigungu",
            "SIGUNGU",
            "SIG_KOR_NM",
            "sgg_nm",
            "SIG_ENG_NM",
            "NAME_2",
            "name",
            "NAME",
            "adm_nm",
            "adm_nm2",
        ]
    )


def normalize_sido_name(name):
    if pd.isna(name):
        return None

    name = str(name).strip()

    if name in ENGLISH_SIDO_ALIASES:
        return ENGLISH_SIDO_ALIASES[name]

    aliases = {
        "Seoul": "서울특별시",
        "Busan": "부산광역시",
        "Daegu": "대구광역시",
        "Incheon": "인천광역시",
        "Gwangju": "광주광역시",
        "Daejeon": "대전광역시",
        "Ulsan": "울산광역시",
        "Sejong": "세종특별자치시",
        "Gyeonggi-do": "경기도",
        "Gyeonggi": "경기도",
        "Gangwon-do": "강원특별자치도",
        "Gangwon": "강원특별자치도",
        "Chungcheongbuk-do": "충청북도",
        "Chungbuk": "충청북도",
        "Chungcheongnam-do": "충청남도",
        "Chungnam": "충청남도",
        "Jeollabuk-do": "전북특별자치도",
        "Jeonbuk": "전북특별자치도",
        "Jeollanam-do": "전라남도",
        "Jeonnam": "전라남도",
        "Gyeongsangbuk-do": "경상북도",
        "Gyeongbuk": "경상북도",
        "Gyeongsangnam-do": "경상남도",
        "Gyeongnam": "경상남도",
        "Jeju": "제주특별자치도",
        "Jeju-do": "제주특별자치도",

        "서울": "서울특별시",
        "서울특별시": "서울특별시",
        "부산": "부산광역시",
        "부산광역시": "부산광역시",
        "대구": "대구광역시",
        "대구광역시": "대구광역시",
        "인천": "인천광역시",
        "인천광역시": "인천광역시",
        "광주": "광주광역시",
        "광주광역시": "광주광역시",
        "대전": "대전광역시",
        "대전광역시": "대전광역시",
        "울산": "울산광역시",
        "울산광역시": "울산광역시",
        "세종": "세종특별자치시",
        "세종특별자치시": "세종특별자치시",
        "경기": "경기도",
        "경기도": "경기도",
        "강원": "강원특별자치도",
        "강원도": "강원특별자치도",
        "강원특별자치도": "강원특별자치도",
        "충북": "충청북도",
        "충청북도": "충청북도",
        "충남": "충청남도",
        "충청남도": "충청남도",
        "전북": "전북특별자치도",
        "전라북도": "전북특별자치도",
        "전북특별자치도": "전북특별자치도",
        "전남": "전라남도",
        "전라남도": "전라남도",
        "경북": "경상북도",
        "경상북도": "경상북도",
        "경남": "경상남도",
        "경상남도": "경상남도",
        "제주": "제주특별자치도",
        "제주특별자치도": "제주특별자치도",
    }

    return aliases.get(name, name)


def normalize_sigungu_name(name, region_type=None, sido_name=None):
    if pd.isna(name):
        return None

    name = str(name).strip()

    if "?" in name:
        return None

    contextual_key = (sido_name, name)

    if contextual_key in CONTEXTUAL_SIGUNGU_ALIASES:
        return CONTEXTUAL_SIGUNGU_ALIASES[contextual_key]

    if name in ENGLISH_SIGUNGU_ALIASES:
        return ENGLISH_SIGUNGU_ALIASES[name]

    aliases = {
        # 서울
        "Gangseo": "강서구",
        "Geum-cheon": "금천구",
        "Guro": "구로구",
        "Gwanak": "관악구",
        "Gwang-jin": "광진구",
        "Gangnam": "강남구",
        "Gangdong": "강동구",
        "Gangbuk": "강북구",
        "Dobong": "도봉구",
        "Dongdaemun": "동대문구",
        "Dongjak": "동작구",
        "Eunpyeong": "은평구",
        "Jongno": "종로구",
        "Jung": "중구",
        "Jungnang": "중랑구",
        "Mapo": "마포구",
        "Nowon": "노원구",
        "Seocho": "서초구",
        "Seodaemun": "서대문구",
        "Seongbuk": "성북구",
        "Seongdong": "성동구",
        "Songpa": "송파구",
        "Yangcheon": "양천구",
        "Yeongdeungpo": "영등포구",
        "Yongsan": "용산구",

        # 부산
        "Haeundae": "해운대구",
        "Saha": "사하구",
        "Sasang": "사상구",
        "Suyeong": "수영구",
        "Yeonje": "연제구",
        "Yeongdo": "영도구",
        "Gijang": "기장군",

        # 인천
        "Bupyeong": "부평구",
        "Gyeyang": "계양구",
        "Michuhol": "미추홀구",
        "Namdong": "남동구",
        "Yeonsu": "연수구",
        "Ganghwa": "강화군",
        "Ongjin": "옹진군",

        # 경기
        "Suwon": "수원시",
        "Seongnam": "성남시",
        "Goyang": "고양시",
        "Yongin": "용인시",
        "Bucheon": "부천시",
        "Ansan": "안산시",
        "Anyang": "안양시",
        "Namyangju": "남양주시",
        "Hwaseong": "화성시",
        "Pyeongtaek": "평택시",
        "Uijeongbu": "의정부시",
        "Siheung": "시흥시",
        "Gimpo": "김포시",
        "Gwangmyeong": "광명시",
        "Gwangju": "광주시",
        "Gunpo": "군포시",
        "Hanam": "하남시",
        "Osan": "오산시",
        "Icheon": "이천시",
        "Anseong": "안성시",
        "Uiwang": "의왕시",
        "Pocheon": "포천시",
        "Yangju": "양주시",
        "Dongducheon": "동두천시",
        "Gwacheon": "과천시",
        "Yeoju": "여주시",
        "Guri": "구리시",
        "Paju": "파주시",
        "Gapyeong": "가평군",
        "Yangpyeong": "양평군",
        "Yeoncheon": "연천군",

        # 강원
        "Chuncheon": "춘천시",
        "Wonju": "원주시",
        "Gangneung": "강릉시",
        "Donghae": "동해시",
        "Taebaek": "태백시",
        "Sokcho": "속초시",
        "Samcheok": "삼척시",
        "Hongcheon": "홍천군",
        "Hoengseong": "횡성군",
        "Yeongwol": "영월군",
        "Pyeongchang": "평창군",
        "Jeongseon": "정선군",
        "Cheorwon": "철원군",
        "Hwacheon": "화천군",
        "Yanggu": "양구군",
        "Inje": "인제군",
        "Goseong": "고성군",
        "Yangyang": "양양군",

        # 충북
        "Cheongju": "청주시",
        "Chungju": "충주시",
        "Jecheon": "제천시",
        "Boeun": "보은군",
        "Okcheon": "옥천군",
        "Yeongdong": "영동군",
        "Jincheon": "진천군",
        "Goesan": "괴산군",
        "Eumseong": "음성군",
        "Danyang": "단양군",
        "Jeungpyeong": "증평군",

        # 충남
        "Cheonan": "천안시",
        "Gongju": "공주시",
        "Boryeong": "보령시",
        "Asan": "아산시",
        "Seosan": "서산시",
        "Nonsan": "논산시",
        "Gyeryong": "계룡시",
        "Dangjin": "당진시",
        "Geumsan": "금산군",
        "Buyeo": "부여군",
        "Seocheon": "서천군",
        "Cheongyang": "청양군",
        "Hongseong": "홍성군",
        "Yesan": "예산군",
        "Taean": "태안군",

        # 전북
        "Jeonju": "전주시",
        "Gunsan": "군산시",
        "Iksan": "익산시",
        "Jeongeup": "정읍시",
        "Namwon": "남원시",
        "Gimje": "김제시",
        "Wanju": "완주군",
        "Jinan": "진안군",
        "Muju": "무주군",
        "Jangsu": "장수군",
        "Imsil": "임실군",
        "Sunchang": "순창군",
        "Gochang": "고창군",
        "Buan": "부안군",

        # 전남
        "Mokpo": "목포시",
        "Yeosu": "여수시",
        "Suncheon": "순천시",
        "Naju": "나주시",
        "Gwangyang": "광양시",
        "Damyang": "담양군",
        "Gokseong": "곡성군",
        "Gurye": "구례군",
        "Goheung": "고흥군",
        "Boseong": "보성군",
        "Hwasun": "화순군",
        "Jangheung": "장흥군",
        "Gangjin": "강진군",
        "Haenam": "해남군",
        "Yeongam": "영암군",
        "Muan": "무안군",
        "Hampyeong": "함평군",
        "Yeonggwang": "영광군",
        "Jangseong": "장성군",
        "Wando": "완도군",
        "Jindo": "진도군",
        "Sinan": "신안군",

        # 경북
        "Pohang": "포항시",
        "Gyeongju": "경주시",
        "Gimcheon": "김천시",
        "Andong": "안동시",
        "Gumi": "구미시",
        "Yeongju": "영주시",
        "Yeongcheon": "영천시",
        "Sangju": "상주시",
        "Mungyeong": "문경시",
        "Gyeongsan": "경산시",
        "Gunwi": "군위군",
        "Uiseong": "의성군",
        "Cheongsong": "청송군",
        "Yeongyang": "영양군",
        "Yeongdeok": "영덕군",
        "Cheongdo": "청도군",
        "Goryeong": "고령군",
        "Seongju": "성주군",
        "Chilgok": "칠곡군",
        "Yecheon": "예천군",
        "Bonghwa": "봉화군",
        "Uljin": "울진군",
        "Ulleung": "울릉군",

        # 경남
        "Changwon": "창원시",
        "Jinju": "진주시",
        "Tongyeong": "통영시",
        "Sacheon": "사천시",
        "Gimhae": "김해시",
        "Miryang": "밀양시",
        "Geoje": "거제시",
        "Yangsan": "양산시",
        "Uiryeong": "의령군",
        "Haman": "함안군",
        "Changnyeong": "창녕군",
        "Namhae": "남해군",
        "Hadong": "하동군",
        "Sancheong": "산청군",
        "Hamyang": "함양군",
        "Geochang": "거창군",
        "Hapcheon": "합천군",

        # 대구 일부
        "Suseong": "수성구",
        "Dalseo": "달서구",
        "Dalseong": "달성군",

        # 대전 일부
        "Yuseong": "유성구",
        "Daedeok": "대덕구",
    }

    return aliases.get(name, name)


# ============================================================
# 5. GeoJSON 도형 중심 계산
# ============================================================

def iter_coordinates(geometry):
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])

    if gtype == "Polygon":
        for ring in coords:
            for lon, lat in ring:
                yield lon, lat

    elif gtype == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                for lon, lat in ring:
                    yield lon, lat


def get_feature_center(feature):
    coords = list(iter_coordinates(feature.get("geometry", {})))

    if not coords:
        return None

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    return sum(lats) / len(lats), sum(lons) / len(lons)


# ============================================================
# 6. 색상 / 라벨
# ============================================================

def color_for_index(idx):
    palette = [
        "#60a5fa", "#34d399", "#f97316", "#a78bfa", "#f43f5e",
        "#14b8a6", "#eab308", "#38bdf8", "#fb7185", "#22c55e",
        "#818cf8", "#f59e0b", "#06b6d4", "#84cc16", "#c084fc",
        "#ef4444", "#0ea5e9", "#10b981", "#facc15", "#64748b",
    ]

    return palette[idx % len(palette)]


def color_for_count(count, idx):
    if count == 0:
        return "#e5e7eb"

    return color_for_index(idx)


def label_color_for_count(count):
    if count == 0:
        return "#64748b"

    return "#0f172a"


def add_region_number_label(layer, lat, lon, count, tooltip_text):
    html = f"""
    <div style="
        font-size: 15px;
        font-weight: 800;
        color: {label_color_for_count(count)};
        text-shadow:
            -1px -1px 0 rgba(255,255,255,0.95),
             1px -1px 0 rgba(255,255,255,0.95),
            -1px  1px 0 rgba(255,255,255,0.95),
             1px  1px 0 rgba(255,255,255,0.95);
        white-space: nowrap;
        text-align: center;
        pointer-events: none;
    ">
        {count}
    </div>
    """

    folium.Marker(
        location=[lat, lon],
        icon=DivIcon(
            icon_size=(30, 20),
            icon_anchor=(15, 10),
            html=html,
        ),
        tooltip=tooltip_text
    ).add_to(layer)


def make_region_popup_html(region_name, count, latest_time):
    latest_text = format_datetime_full(latest_time)

    return f"""
    <div style="width: 240px; color: #172033; line-height: 1.55;">
        <div style="font-size: 13px; font-weight: 800; color: #2563eb; margin-bottom: 3px;">행정구역 요약</div>
        <h4 style="margin: 0 0 10px; font-size: 17px;">{region_name}</h4>
        <div style="display: flex; justify-content: space-between; border-top: 1px solid #e2e8f0; padding-top: 8px;">
            <span style="color: #64748b;">표시 병원</span>
            <strong>{count:,}개</strong>
        </div>
        <div style="display: flex; justify-content: space-between; gap: 12px; margin-top: 6px;">
            <span style="color: #64748b;">최근 갱신</span>
            <strong style="text-align: right;">{latest_text}</strong>
        </div>
    </div>
    """


def make_hospital_popup_html(row):
    hospital_name = row.get("hospital_name", "-")
    addr = row.get("dutyAddr", "-")
    tel_main = row.get("tel_main", "-")
    emergency_tel = row.get("emergency_tel", "-")
    updated_at = row.get("realtime_updated_at_parsed", pd.NaT)
    updated_at_text = format_datetime_full(updated_at)

    return f"""
    <div style="width: 320px; color: #172033; line-height: 1.55;">
        <div style="font-size: 13px; font-weight: 800; color: #e11d48; margin-bottom: 3px;">응급의료기관</div>
        <h4 style="margin: 0 0 10px; font-size: 17px;">{hospital_name}</h4>

        <div style="color: #64748b; font-size: 12px; font-weight: 800; margin-bottom: 2px;">주소</div>
        <div style="margin-bottom: 10px;">{addr}</div>

        <div style="display: grid; grid-template-columns: 96px 1fr; row-gap: 5px; border-top: 1px solid #e2e8f0; padding-top: 9px;">
            <span style="color: #64748b;">대표전화</span><strong>{tel_main}</strong>
            <span style="color: #64748b;">응급실 전화</span><strong>{emergency_tel}</strong>
            <span style="color: #64748b;">응급실 병상</span><strong>{format_value_for_user(row.get("avail_er_general_beds", None))}</strong>
            <span style="color: #64748b;">수술실</span><strong>{format_value_for_user(row.get("avail_operating_rooms", None))}</strong>
            <span style="color: #64748b;">중환자실</span><strong>{format_value_for_user(row.get("avail_icu_general", None))}</strong>
            <span style="color: #64748b;">입원실</span><strong>{format_value_for_user(row.get("avail_inpatient_general_beds", None))}</strong>
            <span style="color: #64748b;">분만실</span><strong>{format_value_for_user(row.get("delivery_room_status", None))}</strong>
        </div>

        <div style="margin-top: 10px; padding-top: 8px; border-top: 1px solid #e2e8f0;">
            <span style="color: #64748b;">병상정보 갱신</span><br>
            <strong>{updated_at_text}</strong>
        </div>
    </div>
    """


# ============================================================
# 7. 시도 / 시군구 레이어 생성
# ============================================================

def build_sido_layer(sido_geojson, count_df):
    layer = folium.FeatureGroup(name="시도 경계", show=True)

    count_map = {
        row["sido"]: {
            "count": int(row["hospital_count"]),
            "latest": row["latest_update"],
        }
        for _, row in count_df.iterrows()
    }

    all_sido_names = []

    for feature in sido_geojson.get("features", []):
        props = feature.get("properties", {})
        sido_name = normalize_sido_name(get_sido_name_from_props(props))

        if not sido_name:
            continue

        if sido_name in EXCLUDE_SIDO:
            continue

        all_sido_names.append(sido_name)

    all_sido_names = sorted(set(all_sido_names))

    color_map = {
        sido: color_for_index(idx)
        for idx, sido in enumerate(all_sido_names)
    }

    for feature in sido_geojson.get("features", []):
        props = feature.get("properties", {})
        sido_name = normalize_sido_name(get_sido_name_from_props(props))

        if not sido_name:
            continue

        if sido_name in EXCLUDE_SIDO:
            continue

        info = count_map.get(
            sido_name,
            {
                "count": 0,
                "latest": pd.NaT,
            }
        )

        count = info["count"]
        latest = info["latest"]
        color = color_for_count(count, all_sido_names.index(sido_name) if sido_name in all_sido_names else 0)

        gj = folium.GeoJson(
            feature,
            style_function=lambda x, color=color, count=count: {
                "fillColor": color,
                "color": "#334155",
                "weight": 1.1,
                "fillOpacity": 0.28 if count > 0 else 0.55,
                "opacity": 0.78,
            },
            highlight_function=lambda x: {
                "weight": 2.4,
                "color": "#0f172a",
                "fillOpacity": 0.44,
            },
            tooltip=folium.Tooltip(f"{sido_name}: {count:,}개 병원"),
            popup=folium.Popup(
                make_region_popup_html(sido_name, count, latest),
                max_width=260
            ),
        )

        gj.add_to(layer)

        center = get_feature_center(feature)

        if center:
            add_region_number_label(
                layer,
                center[0],
                center[1],
                count,
                f"{sido_name}: {count:,}개 병원"
            )

    return layer


def build_sigungu_layer(sigungu_geojson, count_df, selected_sido):
    layer = folium.FeatureGroup(name="시군구 경계", show=False)

    if selected_sido == NATIONWIDE_VALUE:
        return layer

    count_map = {}

    for _, row in count_df.iterrows():
        key = (row["sido"], row["sigungu"])
        count_map[key] = {
            "count": int(row["hospital_count"]),
            "latest": row["latest_update"],
        }

    region_keys_in_geojson = []

    for feature in sigungu_geojson.get("features", []):
        props = feature.get("properties", {})

        raw_sido = get_sido_name_from_props(props)
        raw_sigungu = get_sigungu_name_from_props(props)

        sido_name = normalize_sido_name(raw_sido)
        sigungu_name = normalize_sigungu_name(raw_sigungu, props.get("TYPE_2"), sido_name)

        if not sido_name or not sigungu_name:
            continue

        if sido_name in EXCLUDE_SIDO:
            continue

        if selected_sido != NATIONWIDE_VALUE and sido_name != selected_sido:
            continue

        region_keys_in_geojson.append((sido_name, sigungu_name))

    region_keys_in_geojson = sorted(set(region_keys_in_geojson))

    color_map = {
        key: color_for_index(idx)
        for idx, key in enumerate(region_keys_in_geojson)
    }

    for feature in sigungu_geojson.get("features", []):
        props = feature.get("properties", {})

        raw_sido = get_sido_name_from_props(props)
        raw_sigungu = get_sigungu_name_from_props(props)

        sido_name = normalize_sido_name(raw_sido)
        sigungu_name = normalize_sigungu_name(raw_sigungu, props.get("TYPE_2"), sido_name)

        if not sido_name or not sigungu_name:
            continue

        if sido_name in EXCLUDE_SIDO:
            continue

        if selected_sido != NATIONWIDE_VALUE and sido_name != selected_sido:
            continue

        key = (sido_name, sigungu_name)

        info = count_map.get(
            key,
            {
                "count": 0,
                "latest": pd.NaT,
            }
        )

        count = info["count"]
        latest = info["latest"]
        color = color_for_count(
            count,
            region_keys_in_geojson.index(key) if key in region_keys_in_geojson else 0
        )

        region_label = f"{sido_name} {sigungu_name}"

        gj = folium.GeoJson(
            feature,
            style_function=lambda x, color=color, count=count: {
                "fillColor": color,
                "color": "#475569",
                "weight": 0.9,
                "fillOpacity": 0.22 if count > 0 else 0.5,
                "opacity": 0.68,
            },
            highlight_function=lambda x: {
                "weight": 2.2,
                "color": "#0f172a",
                "fillOpacity": 0.4,
            },
            tooltip=folium.Tooltip(f"{region_label}: {count:,}개 병원"),
            popup=folium.Popup(
                make_region_popup_html(region_label, count, latest),
                max_width=280
            ),
        )

        gj.add_to(layer)

        center = get_feature_center(feature)

        if center:
            add_region_number_label(
                layer,
                center[0],
                center[1],
                count,
                f"{region_label}: {count:,}개 병원"
            )

    return layer


def build_hospital_layer(filtered_df, selected_sido, selected_sigungu):
    layer = folium.FeatureGroup(name="병원 위치", show=False)

    if should_limit_hospital_markers(filtered_df, selected_sido, selected_sigungu):
        return layer

    for _, row in filtered_df.iterrows():
        if pd.isna(row.get("lat")) or pd.isna(row.get("lon")):
            continue

        hospital_name = row.get("hospital_name", "-")

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=5.5,
            color="#ffffff",
            weight=1.8,
            fill=True,
            fill_color="#e11d48",
            fill_opacity=0.92,
            opacity=0.95,
            tooltip=hospital_name,
            popup=folium.Popup(
                make_hospital_popup_html(row),
                max_width=350
            ),
        ).add_to(layer)

    return layer


# ============================================================
# 8. 줌 레벨에 따른 레이어 자동 전환
# ============================================================

class ZoomLayerSwitcher(MacroElement):
    def __init__(
        self,
        sido_layer,
        sigungu_layer,
        hospital_layer,
        sigungu_threshold,
        hospital_threshold,
        overview_mode=False,
    ):
        super().__init__()
        self._name = "ZoomLayerSwitcher"

        self.sido_layer = sido_layer.get_name()
        self.sigungu_layer = sigungu_layer.get_name()
        self.hospital_layer = hospital_layer.get_name()

        self.sigungu_threshold = sigungu_threshold
        self.hospital_threshold = hospital_threshold
        self.overview_mode = "true" if overview_mode else "false"

        self._template = Template(
            """
            {% macro script(this, kwargs) %}
            var map = {{this._parent.get_name()}};

            var sidoLayer = {{this.sido_layer}};
            var sigunguLayer = {{this.sigungu_layer}};
            var hospitalLayer = {{this.hospital_layer}};

            var sigunguThreshold = {{this.sigungu_threshold}};
            var hospitalThreshold = {{this.hospital_threshold}};
            var overviewMode = {{this.overview_mode}};

            function setLayerVisible(layer, visible) {
                if (visible) {
                    if (!map.hasLayer(layer)) {
                        map.addLayer(layer);
                    }
                } else {
                    if (map.hasLayer(layer)) {
                        map.removeLayer(layer);
                    }
                }
            }

            function switchBoundaryByZoom() {
                if (overviewMode) {
                    setLayerVisible(sidoLayer, true);
                    setLayerVisible(sigunguLayer, false);
                    setLayerVisible(hospitalLayer, false);
                    return;
                }

                var z = map.getZoom();

                if (z < sigunguThreshold) {
                    setLayerVisible(sidoLayer, true);
                    setLayerVisible(sigunguLayer, false);
                    setLayerVisible(hospitalLayer, false);
                } else if (z >= sigunguThreshold && z < hospitalThreshold) {
                    setLayerVisible(sidoLayer, false);
                    setLayerVisible(sigunguLayer, true);
                    setLayerVisible(hospitalLayer, false);
                } else {
                    setLayerVisible(sidoLayer, false);
                    setLayerVisible(sigunguLayer, true);
                    setLayerVisible(hospitalLayer, true);
                }
            }

            map.on('zoomend', switchBoundaryByZoom);
            switchBoundaryByZoom();
            {% endmacro %}
            """
        )


# ============================================================
# 9. 실시간 업데이트 함수
# ============================================================

def run_realtime_update(update_sido, update_sigungu):
    if not os.path.exists(PREPROCESS_SCRIPT):
        st.error(f"{PREPROCESS_SCRIPT} 파일을 찾을 수 없습니다.")
        return False

    before_time = datetime.now()

    if update_sido == NATIONWIDE_VALUE:
        update_sigungu = ALL_SIGUNGU_VALUE
        target_text = f"{NATIONWIDE_VALUE} {ALL_SIGUNGU_VALUE}"
    elif update_sigungu == ALL_SIGUNGU_VALUE:
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
        cwd=BASE_DIR,
    )

    progress.progress(70)

    update_status_text = load_update_status_text() or "상태 파일 없음"
    status_summary = format_update_status_summary(load_update_status_json())

    if result.returncode != 0:
        progress.progress(100)
        status.write("업데이트 실패")
        st.error("실시간 업데이트 중 오류가 발생했습니다.")
        st.session_state["last_update_message"] = (
            f"업데이트 실패: {before_time.strftime('%Y-%m-%d %H:%M:%S')} / 대상: {target_text}\n\n"
            f"종료 코드: {result.returncode}\n\n"
            f"{status_summary + chr(10) + chr(10) if status_summary else ''}"
            f"{update_status_text}"
        )
        if status_summary:
            st.info(status_summary)
        elif update_status_text:
            st.info(update_status_text)

        if result.stderr.strip():
            st.code(result.stderr[-5000:])
        if result.stdout.strip():
            st.code(result.stdout[-5000:])
        return False

    after_time = datetime.now()
    progress.progress(100)

    status.write("3/3 최신 CSV 저장 완료")

    data_mtime_text = "-"

    if os.path.exists(DATA_PATH):
        data_mtime = datetime.fromtimestamp(os.path.getmtime(DATA_PATH))
        data_mtime_text = data_mtime.strftime("%Y-%m-%d %H:%M:%S")

    st.session_state["last_update_message"] = (
        f"업데이트 실행: {before_time.strftime('%Y-%m-%d %H:%M:%S')} → {after_time.strftime('%Y-%m-%d %H:%M:%S')} "
        f"/ 대상: {target_text}\n\n"
        f"통합 데이터 파일 수정 시각: {data_mtime_text}\n\n"
        f"{status_summary + chr(10) + chr(10) if status_summary else ''}"
        f"{update_status_text}"
    )

    st.cache_data.clear()

    return True


# ============================================================
# 10. 화면 구성
# ============================================================

st.markdown(
    """
    <div class="er-hero">
        <div class="er-eyebrow">Emergency Room Capacity Dashboard</div>
        <h1>실시간 응급실 가용병상 지도</h1>
        <p class="er-subtitle">
            전국 응급의료기관의 병상, 중환자실, 수술실, 주요 장비 가용 여부를
            지역 경계와 병원 위치 위에서 빠르게 비교합니다.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not os.path.exists(DATA_PATH):
    st.error(f"{DATA_PATH} 파일이 없습니다. 먼저 전처리 코드를 실행하세요.")
    st.stop()

if not os.path.exists(SIDO_GEOJSON_PATH):
    st.error(f"{SIDO_GEOJSON_PATH} 파일이 없습니다.")
    st.stop()

if not os.path.exists(SIGUNGU_GEOJSON_PATH):
    st.error(f"{SIGUNGU_GEOJSON_PATH} 파일이 없습니다.")
    st.stop()

data_refresh_token = st.session_state.get("data_refresh_token", 0)
df = load_data(DATA_PATH, data_refresh_token)

df["realtime_updated_at_parsed"] = df["realtime_updated_at"].apply(parse_datetime_yyyymmddhhmmss)
df["collected_at_parsed"] = pd.to_datetime(df["collected_at"], errors="coerce")

df = df[~df["sido"].isin(EXCLUDE_SIDO)].copy()

sido_geojson = load_geojson(SIDO_GEOJSON_PATH)
sigungu_geojson = load_geojson(SIGUNGU_GEOJSON_PATH)


# ============================================================
# 11. 사이드바
# ============================================================

with st.sidebar:
    st.header("조건 설정")
    st.caption("지역을 먼저 좁힌 뒤 필요한 진료 자원을 선택하세요.")

    sido_options = [NATIONWIDE_VALUE] + sorted(df["sido"].dropna().unique().tolist())
    selected_sido = st.selectbox(
        "시도",
        sido_options,
        help="전국을 선택하면 시도 단위 요약만 표시합니다."
    )

    if selected_sido == NATIONWIDE_VALUE:
        sigungu_options = [ALL_SIGUNGU_VALUE]
    else:
        sigungu_options = [ALL_SIGUNGU_VALUE] + sorted(
            df.loc[df["sido"] == selected_sido, "sigungu"]
            .dropna()
            .unique()
            .tolist()
        )

    selected_sigungu = st.selectbox(
        "시군구",
        sigungu_options,
        help="시군구를 좁히면 병원 마커 표시 범위가 줄어듭니다."
    )

    st.divider()
    st.subheader("데이터 업데이트")
    st.caption("공공 API를 다시 호출해 현재 선택한 지역의 최신 값을 반영합니다.")

    if st.button("선택 지역 업데이트", use_container_width=True, type="primary"):
        if selected_sido == NATIONWIDE_VALUE:
            update_sido = NATIONWIDE_VALUE
            update_sigungu = ALL_SIGUNGU_VALUE
            target_text = f"{NATIONWIDE_VALUE} {ALL_SIGUNGU_VALUE}"

        elif selected_sigungu == ALL_SIGUNGU_VALUE:
            update_sido = selected_sido
            update_sigungu = ALL_SIGUNGU_VALUE
            target_text = f"{selected_sido} 전체"

        else:
            update_sido = selected_sido
            update_sigungu = selected_sigungu
            target_text = f"{selected_sido} {selected_sigungu}"

        with st.spinner(f"{target_text} 최신 데이터를 다시 수집하는 중입니다..."):
            ok = run_realtime_update(update_sido, update_sigungu)

        if ok:
            st.session_state["data_refresh_token"] = datetime.now().isoformat()
            st.success("업데이트 완료")
            st.rerun()

    status_summary = (
        st.session_state["last_update_message"]
        if "last_update_message" in st.session_state
        else format_update_status_summary(load_update_status_json())
    )

    if not status_summary and os.path.exists(UPDATE_STATUS_TEXT_PATH):
        status_summary = load_update_status_text()

    if status_summary:
        with st.expander("최근 업데이트 상태", expanded=False):
            st.info(status_summary)

    st.divider()
    st.subheader("자원 조건")

    condition_mode = st.radio(
        "조건 적용 방식",
        ["모두 충족", "하나라도 충족"],
        index=0,
        horizontal=True,
        help="특정 자원이 모두 필요한 경우에는 '모두 충족'이 적합합니다."
    )

    selected_labels = []

    st.caption("카테고리를 비워두면 지역 내 모든 병원을 표시합니다.")

    for group_name, items in CATEGORY_GROUPS.items():
        with st.expander(group_name, expanded=False):
            labels = list(items.keys())
            picked = st.multiselect(
                "필요 자원",
                labels,
                placeholder="자원을 선택하세요",
                key=f"multi_{group_name}"
            )
            selected_labels.extend(picked)

    if selected_labels:
        st.success(f"선택한 자원 조건 {len(selected_labels)}개")
    else:
        st.info("자원 조건 없이 지역 전체를 표시합니다.")


# ============================================================
# 12. 지역 필터 + 카테고리 필터
# ============================================================

region_filtered = df.copy()

if selected_sido != NATIONWIDE_VALUE:
    region_filtered = region_filtered[region_filtered["sido"] == selected_sido]

if selected_sigungu != ALL_SIGUNGU_VALUE:
    region_filtered = region_filtered[region_filtered["sigungu"] == selected_sigungu]

filtered = filter_by_categories(region_filtered, selected_labels, condition_mode)

if selected_sido == NATIONWIDE_VALUE:
    selected_region_text = "전국"
elif selected_sigungu == ALL_SIGUNGU_VALUE:
    selected_region_text = f"{selected_sido} 전체"
else:
    selected_region_text = f"{selected_sido} {selected_sigungu}"

category_summary_text = (
    f"{len(selected_labels)}개 자원 조건"
    if selected_labels
    else "자원 조건 없음"
)


# ============================================================
# 13. 상단 지표
# ============================================================

valid_update_df = filtered[
    filtered["realtime_updated_at_parsed"].notna()
].copy()

latest_update_text = "-"
latest_update_full_text = "-"

if len(valid_update_df) > 0:
    latest_update = valid_update_df["realtime_updated_at_parsed"].max()
    latest_update_text = format_datetime_short(latest_update)
    latest_update_full_text = format_datetime_full(latest_update)

st.markdown(
    f"""
    <div class="er-status-strip">
        <strong>{selected_region_text}</strong> 기준으로
        <strong>{category_summary_text}</strong>을 적용했습니다.
        현재 조건에 맞는 병원과 주요 자원 현황만 표시합니다.
    </div>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(3)

with metric_cols[0]:
    st.metric("표시 병원 수", f"{len(filtered):,}")
    if len(region_filtered) != len(filtered):
        st.caption(f"지역 전체 {len(region_filtered):,}개 중")

with metric_cols[1]:
    st.metric("선택 조건", f"{len(selected_labels):,}개")

with metric_cols[2]:
    st.metric("최근 갱신", latest_update_text)
    st.caption(latest_update_full_text)


# ============================================================
# 14. 행정구역별 집계
# ============================================================

sido_count_df = (
    filtered
    .groupby("sido", dropna=False)
    .agg(
        hospital_count=("hpid", "nunique"),
        latest_update=("realtime_updated_at_parsed", "max"),
    )
    .reset_index()
)

sigungu_count_df = (
    filtered
    .groupby(["sido", "sigungu"], dropna=False)
    .agg(
        hospital_count=("hpid", "nunique"),
        latest_update=("realtime_updated_at_parsed", "max"),
    )
    .reset_index()
)


# ============================================================
# 15. 지도 중심 설정
# ============================================================

if len(filtered) > 0:
    center_lat = filtered["lat"].mean()
    center_lon = filtered["lon"].mean()
else:
    center_lat = df["lat"].mean()
    center_lon = df["lon"].mean()

if selected_sido == NATIONWIDE_VALUE:
    zoom_start = 7
elif selected_sigungu == ALL_SIGUNGU_VALUE:
    zoom_start = 9
else:
    zoom_start = 11

hospital_markers_limited = should_limit_hospital_markers(
    filtered,
    selected_sido,
    selected_sigungu,
)


# ============================================================
# 16. 지도 생성
# ============================================================

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=zoom_start,
    tiles="CartoDB positron",
    prefer_canvas=True,
)

sido_layer = build_sido_layer(
    sido_geojson=sido_geojson,
    count_df=sido_count_df,
)

sigungu_layer = build_sigungu_layer(
    sigungu_geojson=sigungu_geojson,
    count_df=sigungu_count_df,
    selected_sido=selected_sido,
)

hospital_layer = build_hospital_layer(filtered, selected_sido, selected_sigungu)

sido_layer.add_to(m)
sigungu_layer.add_to(m)
hospital_layer.add_to(m)

m.add_child(
    ZoomLayerSwitcher(
        sido_layer=sido_layer,
        sigungu_layer=sigungu_layer,
        hospital_layer=hospital_layer,
        sigungu_threshold=ZOOM_SIGUNGU_LEVEL,
        hospital_threshold=ZOOM_HOSPITAL_LEVEL,
        overview_mode=selected_sido == NATIONWIDE_VALUE,
    )
)

folium.LayerControl(collapsed=True).add_to(m)


# ============================================================
# 17. 지도 출력
# ============================================================

st.markdown('<div class="er-section-title">지도 보기</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <p class="er-inline-note">
        지역 숫자는 현재 조건에 맞는 병원 수입니다. 지도를 확대하면 시군구 경계와 병원 위치를 단계적으로 확인할 수 있습니다.
        병원 마커는 {MAX_HOSPITAL_MARKERS:,}개를 초과하는 넓은 범위에서는 성능을 위해 숨깁니다.
    </p>
    """,
    unsafe_allow_html=True,
)

if len(filtered) == 0:
    st.markdown(
        """
        <div class="er-empty">
            현재 조건에 맞는 병원이 없습니다. 지역 범위를 넓히거나 자원 조건을 줄여 다시 확인해 보세요.
        </div>
        """,
        unsafe_allow_html=True,
    )

st_folium(
    m,
    width=None,
    height=760,
    returned_objects=[],
    key="er_boundary_map"
)

if hospital_markers_limited:
    st.warning(
        f"현재 범위에는 병원 {len(filtered):,}개가 포함되어 병원 마커를 한 번에 표시하지 않습니다. "
        "시도 또는 시군구를 더 좁히면 병원 위치가 지도에 표시됩니다.",
        icon="ℹ️",
    )


# ============================================================
# 18. 하단 데이터 테이블
# ============================================================

st.markdown('<div class="er-section-title">병원 데이터</div>', unsafe_allow_html=True)
st.markdown(
    '<p class="er-inline-note">지도에 반영된 병원 목록과 핵심 자원 값을 표로 확인합니다.</p>',
    unsafe_allow_html=True,
)

with st.expander("병원 목록 열기", expanded=False):
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

    sort_cols = [
        col for col in ["sido", "sigungu", "hospital_name"]
        if col in table_df.columns
    ]

    if sort_cols:
        table_df = table_df.sort_values(sort_cols)

    table_df = table_df.rename(
        columns={
            "hospital_name": "병원명",
            "sido": "시도",
            "sigungu": "시군구",
            "dutyAddr": "주소",
            "emergency_tel": "응급실 전화",
            "avail_er_general_beds": "응급실 일반 병상",
            "avail_operating_rooms": "수술실",
            "avail_icu_general": "일반 중환자실",
            "avail_inpatient_general_beds": "일반 입원실",
            "delivery_room_status": "분만실",
            "standard_delivery_rooms": "분만실 기준 수",
            "realtime_updated_at_parsed": "병상정보 갱신시각",
        }
    )

    st.dataframe(
        table_df,
        use_container_width=True,
        height=360,
        hide_index=True,
    )

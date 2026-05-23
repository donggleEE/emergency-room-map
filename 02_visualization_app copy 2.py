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

st.set_page_config(
    page_title="실시간 응급실 가용병상 지도",
    layout="wide"
)

DATA_PATH = "data/hospital_er_preprocessed_wide.csv"
PREPROCESS_SCRIPT = "03_realtime_data.py"

SIDO_GEOJSON_PATH = "data/korea_sido.geojson"
SIGUNGU_GEOJSON_PATH = "data/korea_sigungu.geojson"

EXCLUDE_SIDO = ["제주특별자치도"]

ZOOM_SWITCH_LEVEL = 9


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
# 4. 행정구역 GeoJSON 처리
# ============================================================

def pick_property(props, candidates):
    for key in candidates:
        if key in props and props[key] not in [None, ""]:
            return str(props[key]).strip()

    return None


def get_sido_name_from_props(props):
    return pick_property(
        props,
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
    return pick_property(
        props,
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


def normalize_sigungu_name(name, region_type=None):
    if pd.isna(name):
        return None

    name = str(name).strip()

    # southkorea-maps 계열 GeoJSON에서 한글명이 깨진 경우
    if "?" in name:
        return None

    aliases = {
        # 서울특별시
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
        "Gangseo-gu": "강서구",
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

        # 인천
        "Bupyeong": "부평구",
        "Dong": "동구",
        "Gyeyang": "계양구",
        "Jung": "중구",
        "Michuhol": "미추홀구",
        "Namdong": "남동구",
        "Seo": "서구",
        "Yeonsu": "연수구",
        "Ganghwa": "강화군",
        "Ongjin": "옹진군",

        # 경기 주요
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

        # 부산 일부
        "Haeundae": "해운대구",
        "Saha": "사하구",
        "Sasang": "사상구",
        "Suyeong": "수영구",
        "Yeonje": "연제구",
        "Yeongdo": "영도구",
        "Gijang": "기장군",

        # 대구 일부
        "Suseong": "수성구",
        "Dalseo": "달서구",
        "Dalseong": "달성군",

        # 대전 일부
        "Yuseong": "유성구",
        "Daedeok": "대덕구",
    }

    if name in aliases:
        return aliases[name]

    # fallback: 타입이 Gu/County/City로 있으면 뒤에 구/군/시 붙여보기
    # 단, 영어 이름을 한글로 바꾸는 건 아니므로 실제 매칭률은 낮음.
    return name


def color_for_index(idx):
    palette = [
        "#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3",
        "#fdb462", "#b3de69", "#fccde5", "#d9d9d9", "#bc80bd",
        "#ccebc5", "#ffed6f", "#a6cee3", "#b2df8a", "#fb9a99",
        "#fdbf6f", "#cab2d6", "#ffff99", "#1f78b4", "#33a02c",
        "#e31a1c", "#ff7f00", "#6a3d9a", "#b15928",
    ]

    return palette[idx % len(palette)]


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


def add_region_label(layer, lat, lon, title, count):
    html = f"""
    <div style="
        font-size: 15px;
        font-weight: 800;
        color: #111827;
        background: rgba(255,255,255,0.82);
        border: 1px solid rgba(17,24,39,0.22);
        border-radius: 999px;
        padding: 4px 9px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.18);
        white-space: nowrap;
        text-align: center;
    ">
        {count}
    </div>
    """

    folium.Marker(
        location=[lat, lon],
        icon=DivIcon(
            icon_size=(60, 24),
            icon_anchor=(30, 12),
            html=html,
        ),
        tooltip=f"{title}: {count}개 병원"
    ).add_to(layer)


def make_popup_html(region_name, count, latest_time):
    latest_text = latest_time.strftime("%Y-%m-%d %H:%M") if pd.notna(latest_time) else "-"

    return f"""
    <div style="width: 230px;">
        <h4 style="margin-bottom: 8px;">{region_name}</h4>
        <b>표시 병원 수</b>: {count:,}개<br>
        <b>최근 병상 갱신</b>: {latest_text}<br>
    </div>
    """


def build_sido_layer(sido_geojson, count_df):
    layer = folium.FeatureGroup(name="시도 경계", show=True)

    count_map = {
        row["sido"]: {
            "count": int(row["hospital_count"]),
            "latest": row["latest_update"],
        }
        for _, row in count_df.iterrows()
    }

    sido_names = sorted(count_map.keys())
    color_map = {
        sido: color_for_index(idx)
        for idx, sido in enumerate(sido_names)
    }

    for feature in sido_geojson.get("features", []):
        props = feature.get("properties", {})
        sido_name = normalize_sido_name(get_sido_name_from_props(props))

        if not sido_name:
            continue

        if sido_name in EXCLUDE_SIDO:
            continue

        if sido_name not in count_map:
            continue

        count = count_map[sido_name]["count"]
        latest = count_map[sido_name]["latest"]
        color = color_map.get(sido_name, "#cccccc")

        gj = folium.GeoJson(
            feature,
            style_function=lambda x, color=color: {
                "fillColor": color,
                "color": "#374151",
                "weight": 1.2,
                "fillOpacity": 0.68,
            },
            highlight_function=lambda x: {
                "weight": 3,
                "color": "#111827",
                "fillOpacity": 0.86,
            },
            tooltip=folium.Tooltip(f"{sido_name}: {count:,}개 병원"),
            popup=folium.Popup(
                make_popup_html(sido_name, count, latest),
                max_width=260
            ),
        )

        gj.add_to(layer)

        center = get_feature_center(feature)

        if center:
            add_region_label(
                layer,
                center[0],
                center[1],
                sido_name,
                count
            )

    return layer


def build_sigungu_layer(sigungu_geojson, count_df, selected_sido):
    layer = folium.FeatureGroup(name="시군구 경계", show=False)

    count_map = {}

    for _, row in count_df.iterrows():
        key = (row["sido"], row["sigungu"])
        count_map[key] = {
            "count": int(row["hospital_count"]),
            "latest": row["latest_update"],
        }

    keys = sorted(count_map.keys())
    color_map = {
        key: color_for_index(idx)
        for idx, key in enumerate(keys)
    }

    for feature in sigungu_geojson.get("features", []):
        props = feature.get("properties", {})

        raw_sido = get_sido_name_from_props(props)
        raw_sigungu = get_sigungu_name_from_props(props)

        sido_name = normalize_sido_name(raw_sido)
        region_type = props.get("TYPE_2")
        sigungu_name = normalize_sigungu_name(raw_sigungu, region_type)

        if not sigungu_name:
            continue

        if sido_name in EXCLUDE_SIDO:
            continue

        if selected_sido != "전국" and sido_name != selected_sido:
            continue

        key = (sido_name, sigungu_name)

        # 일부 시군구 GeoJSON은 시도명이 없고 시군구명만 있는 경우가 있다.
        # 그 경우에는 선택 시도가 있을 때만 보조 매칭한다.
        if key not in count_map and selected_sido != "전국":
            key = (selected_sido, sigungu_name)

        if key not in count_map:
            continue

        count = count_map[key]["count"]
        latest = count_map[key]["latest"]
        color = color_map.get(key, "#cccccc")

        region_label = f"{key[0]} {key[1]}"

        gj = folium.GeoJson(
            feature,
            style_function=lambda x, color=color: {
                "fillColor": color,
                "color": "#374151",
                "weight": 0.9,
                "fillOpacity": 0.66,
            },
            highlight_function=lambda x: {
                "weight": 2.6,
                "color": "#111827",
                "fillOpacity": 0.86,
            },
            tooltip=folium.Tooltip(f"{region_label}: {count:,}개 병원"),
            popup=folium.Popup(
                make_popup_html(region_label, count, latest),
                max_width=280
            ),
        )

        gj.add_to(layer)

        center = get_feature_center(feature)

        if center:
            add_region_label(
                layer,
                center[0],
                center[1],
                region_label,
                count
            )

    return layer


class ZoomLayerSwitcher(MacroElement):
    """
    줌 레벨에 따라 시도 경계와 시군구 경계를 자동 전환한다.
    """

    def __init__(self, sido_layer, sigungu_layer, threshold):
        super().__init__()
        self._name = "ZoomLayerSwitcher"
        self.sido_layer = sido_layer.get_name()
        self.sigungu_layer = sigungu_layer.get_name()
        self.threshold = threshold

        self._template = Template(
            """
            {% macro script(this, kwargs) %}
            var map = {{this._parent.get_name()}};
            var sidoLayer = {{this.sido_layer}};
            var sigunguLayer = {{this.sigungu_layer}};
            var threshold = {{this.threshold}};

            function switchBoundaryByZoom() {
                var z = map.getZoom();

                if (z >= threshold) {
                    if (map.hasLayer(sidoLayer)) {
                        map.removeLayer(sidoLayer);
                    }
                    if (!map.hasLayer(sigunguLayer)) {
                        map.addLayer(sigunguLayer);
                    }
                } else {
                    if (map.hasLayer(sigunguLayer)) {
                        map.removeLayer(sigunguLayer);
                    }
                    if (!map.hasLayer(sidoLayer)) {
                        map.addLayer(sidoLayer);
                    }
                }
            }

            map.on('zoomend', switchBoundaryByZoom);
            switchBoundaryByZoom();
            {% endmacro %}
            """
        )


# ============================================================
# 5. 실시간 업데이트 함수
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
# 6. 화면 구성
# ============================================================

st.title("실시간 응급실 가용병상 지도")
st.caption("행정구역 경계 기반으로 응급의료기관 가용자원 분포를 확인하는 지도")

if not os.path.exists(DATA_PATH):
    st.error(f"{DATA_PATH} 파일이 없습니다. 먼저 전처리 코드를 실행하세요.")
    st.stop()

if not os.path.exists(SIDO_GEOJSON_PATH):
    st.error(f"{SIDO_GEOJSON_PATH} 파일이 없습니다.")
    st.info("시도 경계 GeoJSON 파일을 data/korea_sido.geojson 위치에 넣어주세요.")
    st.stop()

if not os.path.exists(SIGUNGU_GEOJSON_PATH):
    st.error(f"{SIGUNGU_GEOJSON_PATH} 파일이 없습니다.")
    st.info("시군구 경계 GeoJSON 파일을 data/korea_sigungu.geojson 위치에 넣어주세요.")
    st.stop()

df = load_data(DATA_PATH)

df["realtime_updated_at_parsed"] = df["realtime_updated_at"].apply(parse_datetime_yyyymmddhhmmss)
df["collected_at_parsed"] = pd.to_datetime(df["collected_at"], errors="coerce")

df = df[~df["sido"].isin(EXCLUDE_SIDO)].copy()

sido_geojson = load_geojson(SIDO_GEOJSON_PATH)
sigungu_geojson = load_geojson(SIGUNGU_GEOJSON_PATH)


# ============================================================
# 7. 사이드바
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

    st.divider()

    if st.button("🔄 현재 선택 지역 실시간 데이터 업데이트", width="stretch"):
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
        help="특정 자원이 모두 필요한 경우에는 '모두 충족'이 적합합니다."
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

    show_hospital_points = st.checkbox(
        "병원 위치 점 함께 보기",
        value=False,
        help="기본 지도는 행정구역 단위입니다. 정확한 병원 위치가 필요할 때만 켜세요."
    )

    st.caption(f"줌 레벨 {ZOOM_SWITCH_LEVEL} 이상부터 시군구 경계로 자동 전환됩니다.")


# ============================================================
# 8. 지역 필터 + 카테고리 필터
# ============================================================

region_filtered = df.copy()

if selected_sido != "전국":
    region_filtered = region_filtered[region_filtered["sido"] == selected_sido]

if selected_sigungu != "전체":
    region_filtered = region_filtered[region_filtered["sigungu"] == selected_sigungu]

filtered = filter_by_categories(region_filtered, selected_labels, condition_mode)


# ============================================================
# 9. 상단 지표 단순화
# ============================================================

left, right = st.columns(2)

valid_update_df = filtered[
    filtered["realtime_updated_at_parsed"].notna()
].copy()

with left:
    st.metric("표시 병원 수", f"{len(filtered):,}")

with right:
    if len(valid_update_df) > 0:
        latest_update = valid_update_df["realtime_updated_at_parsed"].max()
        st.metric("업데이트 시기", latest_update.strftime("%Y-%m-%d %H:%M"))
    else:
        st.metric("업데이트 시기", "-")


# ============================================================
# 10. 행정구역별 집계
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

sido_count_df = sido_count_df[sido_count_df["hospital_count"] > 0].copy()
sigungu_count_df = sigungu_count_df[sigungu_count_df["hospital_count"] > 0].copy()


# ============================================================
# 11. 지도 중심 설정
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
    zoom_start = 9
else:
    zoom_start = 11


# ============================================================
# 12. 지도 생성
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

sido_layer.add_to(m)
sigungu_layer.add_to(m)

m.add_child(
    ZoomLayerSwitcher(
        sido_layer=sido_layer,
        sigungu_layer=sigungu_layer,
        threshold=ZOOM_SWITCH_LEVEL,
    )
)


# ============================================================
# 13. 선택 옵션: 병원 위치 점
# ============================================================

if show_hospital_points:
    hospital_layer = folium.FeatureGroup(name="병원 위치", show=True)

    for _, row in filtered.iterrows():
        hospital_name = row.get("hospital_name", "-")
        addr = row.get("dutyAddr", "-")
        emergency_tel = row.get("emergency_tel", "-")
        updated_at = row.get("realtime_updated_at_parsed", pd.NaT)

        popup_html = f"""
        <div style="width: 300px;">
            <h4>{hospital_name}</h4>
            <b>주소</b><br>{addr}<br><br>
            <b>응급실 전화</b>: {emergency_tel}<br>
            <b>응급실 일반 병상</b>: {format_value_for_user(row.get("avail_er_general_beds", None))}<br>
            <b>수술실</b>: {format_value_for_user(row.get("avail_operating_rooms", None))}<br>
            <b>일반 중환자실</b>: {format_value_for_user(row.get("avail_icu_general", None))}<br>
            <b>일반 입원실</b>: {format_value_for_user(row.get("avail_inpatient_general_beds", None))}<br><br>
            <b>병상정보 갱신시각</b><br>
            {updated_at.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(updated_at) else "-"}
        </div>
        """

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=4,
            color="#111827",
            fill=True,
            fill_color="#111827",
            fill_opacity=0.75,
            opacity=0.9,
            tooltip=hospital_name,
            popup=folium.Popup(popup_html, max_width=340),
        ).add_to(hospital_layer)

    hospital_layer.add_to(m)

folium.LayerControl(collapsed=True).add_to(m)


# ============================================================
# 14. 지도 출력
# ============================================================

st_folium(
    m,
    width=None,
    height=760,
    returned_objects=["last_clicked", "bounds", "zoom"],
    key="er_boundary_map"
)


# ============================================================
# 15. 하단 데이터 테이블
# ============================================================

with st.expander("현재 지도에 반영된 병원 데이터 보기", expanded=False):
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

    st.dataframe(
        table_df,
        width="stretch",
        height=360
    )
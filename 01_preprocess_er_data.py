# 전처리
#pip install requests pandas python-dotenv lxml
## 1. 기본 설정
# %%
import os
import re
import time
import requests
import pandas as pd
import xml.etree.ElementTree as ET

from datetime import datetime
from math import ceil

SERVICE_KEY = "XbJ/wCvO7wXg0t7J4M15OSGv/qjMpwvz514q+KkVnxA+wg2b8WDxULOfIDodI1M7BtKR+eMU7ZCzpsjbGqD7tA=="

BASE_URL = "https://apis.data.go.kr/B552657/ErmctInfoInqireService"

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

COLLECTED_AT = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

print("API 키 설정 완료")
print("수집 시각:", COLLECTED_AT)
## 2. 공통 함수 만들기
# %%
def xml_to_dataframe(xml_text: str) -> pd.DataFrame:
    """
    XML 응답에서 <item> 태그들을 찾아 DataFrame으로 변환
    """
    if not xml_text:
        return pd.DataFrame()

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        print("XML 파싱 실패")
        print(xml_text[:500])
        return pd.DataFrame()

    items = root.findall(".//item")

    rows = []
    for item in items:
        row = {}
        for child in item:
            row[child.tag] = child.text.strip() if child.text else None
        rows.append(row)

    return pd.DataFrame(rows)


def get_total_count(xml_text: str) -> int:
    """
    XML 응답에서 totalCount 추출
    """
    if not xml_text:
        return 0

    try:
        root = ET.fromstring(xml_text)
        total = root.find(".//totalCount")
        if total is not None and total.text is not None:
            return int(total.text)
    except Exception:
        return 0

    return 0


def call_api_once(endpoint: str, params: dict | None = None) -> str | None:
    """
    API 1회 호출
    """
    url = f"{BASE_URL}/{endpoint}"

    request_params = {
        "serviceKey": SERVICE_KEY,
        "pageNo": 1,
        "numOfRows": 1000,
    }

    if params:
        request_params.update(params)

    try:
        res = requests.get(url, params=request_params, timeout=30)

        if res.status_code != 200:
            print("상태코드 오류:", res.status_code)
            print(res.text[:300])
            return None

        return res.text

    except requests.RequestException as e:
        print("요청 오류:", e)
        return None


def call_api_all_pages(
    endpoint: str,
    params: dict | None = None,
    num_of_rows: int = 1000,
    sleep_sec: float = 0.15,
) -> pd.DataFrame:
    """
    totalCount 기준으로 모든 페이지를 수집
    """
    base_params = params.copy() if params else {}
    base_params["pageNo"] = 1
    base_params["numOfRows"] = num_of_rows

    first_xml = call_api_once(endpoint, base_params)

    if not first_xml:
        return pd.DataFrame()

    total_count = get_total_count(first_xml)
    first_df = xml_to_dataframe(first_xml)

    if total_count == 0:
        return first_df

    total_pages = ceil(total_count / num_of_rows)

    dfs = [first_df]

    if total_pages >= 2:
        for page in range(2, total_pages + 1):
            page_params = base_params.copy()
            page_params["pageNo"] = page
            page_params["numOfRows"] = num_of_rows

            xml_text = call_api_once(endpoint, page_params)
            df_page = xml_to_dataframe(xml_text)
            dfs.append(df_page)

            time.sleep(sleep_sec)

    result = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    return result


def to_number(series: pd.Series) -> pd.Series:
    """
    숫자로 바꿀 수 있는 값은 숫자로 변환.
    Y/N 같은 값은 NaN 처리.
    """
    return pd.to_numeric(series, errors="coerce")


def normalize_yn(value):
    """
    Y/N, 가능/불가능, 정보미제공 등을 정리
    """
    if pd.isna(value):
        return None

    value = str(value).strip()

    if value in ["Y", "가능"]:
        return "Y"
    if value in ["N", "불가능"]:
        return "N"
    if value in ["정보미제공", "미제공"]:
        return "UNKNOWN"

    return value


print("공통 함수 준비 완료")
## 3. 컬럼 사전 만들기
# %%
REALTIME_COLUMN_MAP = {
    # 기본
    "hpid": "hpid",
    "phpid": "old_hpid",
    "dutyName": "realtime_hospital_name",
    "dutyname": "realtime_hospital_name",
    "dutyTel3": "realtime_emergency_tel",
    "hvidate": "realtime_updated_at",

    # 대표 실시간 병상
    "hvec": "avail_er_general_beds",
    "hvoc": "avail_operating_rooms",
    "hvcc": "avail_icu_neurology",
    "hvncc": "avail_icu_neonatal",
    "hvccc": "avail_icu_thoracic_surgery",
    "hvicc": "avail_icu_general",
    "hvgc": "avail_inpatient_general_beds",

    # 장비 가능 여부
    "hvctayn": "available_ct_yn",
    "hvmriayn": "available_mri_yn",
    "hvangioayn": "available_angio_yn",
    "hvventiayn": "available_ventilator_yn",
    "hvventisoayn": "available_ventilator_premature_yn",
    "hvincuayn": "available_incubator_yn",
    "hvcrrtayn": "available_crrt_yn",
    "hvecmoayn": "available_ecmo_yn",
    "hvoxyayn": "available_hyperbaric_oxygen_yn",
    "hvhypoayn": "available_targeted_temperature_management_yn",
    "hvamyn": "available_ambulance_yn",

    # hv1 ~ hv61
    "hv1": "er_doctor_direct_phone",
    "hv2": "avail_icu_internal_medicine",
    "hv3": "avail_icu_surgery",
    "hv4": "avail_orthopedic_inpatient_beds",
    "hv5": "ct_status",
    "hv6": "avail_icu_neurosurgery",
    "hv7": "angio_status",
    "hv8": "avail_icu_burn",
    "hv9": "avail_icu_trauma",
    "hv10": "pediatric_ventilator_status",
    "hv11": "incubator_status",
    "hv12": "pediatric_doctor_direct_phone",
    "hv13": "avail_isolation_negative_pressure_area_beds",
    "hv14": "avail_isolation_general_area_beds",
    "hv15": "avail_pediatric_negative_pressure_isolation",
    "hv16": "avail_pediatric_general_isolation",
    "hv17": "avail_er_dedicated_icu_negative_pressure",
    "hv18": "avail_er_dedicated_icu_general_isolation",
    "hv19": "avail_er_dedicated_inpatient_negative_pressure",
    "hv21": "avail_er_dedicated_inpatient_general_isolation",
    "hv22": "avail_infectious_disease_icu_beds",
    "hv23": "avail_infectious_disease_icu_negative_pressure_beds",
    "hv24": "avail_infection_severe_beds",
    "hv25": "avail_infection_semi_severe_beds",
    "hv26": "avail_infection_moderate_beds",
    "hv27": "avail_cohort_isolation",
    "hv28": "avail_pediatric_beds",
    "hv29": "avail_er_negative_pressure_isolation_beds",
    "hv30": "avail_er_general_isolation_beds",
    "hv31": "avail_er_dedicated_icu",
    "hv32": "avail_icu_pediatric",
    "hv33": "avail_er_dedicated_pediatric_icu",
    "hv34": "avail_icu_cardiology",
    "hv35": "avail_icu_negative_pressure_isolation",
    "hv36": "avail_er_dedicated_inpatient_beds",
    "hv37": "avail_er_dedicated_pediatric_inpatient_beds",
    "hv38": "avail_trauma_dedicated_inpatient_beds",
    "hv39": "avail_trauma_dedicated_operating_rooms",
    "hv40": "avail_psychiatric_closed_ward_beds",
    "hv41": "avail_inpatient_negative_pressure_isolation",
    "hv42": "delivery_room_status",
    "hv43": "avail_burn_treatment_room",
    "hv60": "avail_trauma_resuscitation_room",
    "hv61": "avail_trauma_patient_care_area",
}

# hvs01 ~ hvs61: 기준 병상/장비
HVS_COLUMN_MAP = {
    "hvs01": "standard_er_general_beds",
    "hvs02": "standard_pediatric_beds",
    "hvs03": "standard_er_negative_pressure_isolation_beds",
    "hvs04": "standard_er_general_isolation_beds",
    "hvs05": "standard_er_dedicated_icu",
    "hvs06": "standard_icu_internal_medicine",
    "hvs07": "standard_icu_surgery",
    "hvs08": "standard_icu_neonatal",
    "hvs09": "standard_icu_pediatric",
    "hvs10": "standard_er_dedicated_pediatric_icu",
    "hvs11": "standard_icu_neurology",
    "hvs12": "standard_icu_neurosurgery",
    "hvs13": "standard_icu_burn",
    "hvs14": "standard_icu_trauma",
    "hvs15": "standard_icu_cardiology",
    "hvs16": "standard_icu_thoracic_surgery",
    "hvs17": "standard_icu_general",
    "hvs18": "standard_icu_negative_pressure_isolation",
    "hvs19": "standard_er_dedicated_inpatient_beds",
    "hvs20": "standard_er_dedicated_pediatric_inpatient_beds",
    "hvs21": "standard_trauma_dedicated_inpatient_beds",
    "hvs22": "standard_operating_rooms",
    "hvs23": "standard_trauma_dedicated_operating_rooms",
    "hvs24": "standard_psychiatric_closed_ward_beds",
    "hvs25": "standard_inpatient_negative_pressure_isolation",
    "hvs26": "standard_delivery_rooms",
    "hvs27": "standard_ct",
    "hvs28": "standard_mri",
    "hvs29": "standard_angio",
    "hvs30": "standard_ventilator_general",
    "hvs31": "standard_ventilator_premature",
    "hvs32": "standard_incubator",
    "hvs33": "standard_crrt",
    "hvs34": "standard_ecmo",
    "hvs35": "standard_targeted_temperature_management",
    "hvs36": "standard_burn_treatment_room",
    "hvs37": "standard_hyperbaric_oxygen",
    "hvs38": "standard_inpatient_general_beds",
    "hvs46": "standard_isolation_negative_pressure_area_beds",
    "hvs47": "standard_isolation_general_area_beds",
    "hvs48": "standard_pediatric_negative_pressure_isolation",
    "hvs49": "standard_pediatric_general_isolation",
    "hvs50": "standard_er_dedicated_icu_negative_pressure",
    "hvs51": "standard_er_dedicated_icu_general_isolation",
    "hvs52": "standard_er_dedicated_inpatient_negative_pressure",
    "hvs53": "standard_er_dedicated_inpatient_general_isolation",
    "hvs54": "standard_infectious_disease_icu_beds",
    "hvs55": "standard_infectious_disease_icu_negative_pressure_beds",
    "hvs56": "standard_infection_severe_beds",
    "hvs57": "standard_infection_semi_severe_beds",
    "hvs58": "standard_infection_moderate_beds",
    "hvs59": "standard_cohort_isolation",
    "hvs60": "standard_trauma_resuscitation_room",
    "hvs61": "standard_trauma_patient_care_area",
}

REALTIME_COLUMN_MAP.update(HVS_COLUMN_MAP)

SEVERE_COLUMN_MAP = {
    "hpid": "hpid",
    "dutyName": "severe_hospital_name",

    "MKioskTy28": "severe_er_gatekeeper_yn",
    "MKioskTy1": "severe_myocardial_infarction_reperfusion_yn",
    "MKioskTy2": "severe_cerebral_infarction_reperfusion_yn",
    "MKioskTy3": "severe_subarachnoid_hemorrhage_surgery_yn",
    "MKioskTy4": "severe_other_cerebral_hemorrhage_surgery_yn",
    "MKioskTy5": "severe_thoracic_aortic_emergency_yn",
    "MKioskTy6": "severe_abdominal_aortic_emergency_yn",
    "MKioskTy7": "severe_gallbladder_disease_yn",
    "MKioskTy8": "severe_biliary_tract_disease_yn",
    "MKioskTy9": "severe_nontraumatic_abdominal_emergency_surgery_yn",
    "MKioskTy10": "severe_infant_intussusception_obstruction_yn",
    "MKioskTy11": "severe_adult_gi_emergency_endoscopy_yn",
    "MKioskTy12": "severe_infant_gi_emergency_endoscopy_yn",
    "MKioskTy13": "severe_adult_bronchial_emergency_endoscopy_yn",
    "MKioskTy14": "severe_infant_bronchial_emergency_endoscopy_yn",
    "MKioskTy15": "severe_low_birth_weight_infant_intensive_care_yn",
    "MKioskTy16": "severe_obstetric_delivery_yn",
    "MKioskTy17": "severe_obstetric_surgery_yn",
    "MKioskTy18": "severe_gynecologic_surgery_yn",
    "MKioskTy19": "severe_burn_specialized_treatment_yn",
    "MKioskTy20": "severe_finger_toe_replantation_yn",
    "MKioskTy21": "severe_other_limb_replantation_yn",
    "MKioskTy22": "severe_emergency_dialysis_hd_yn",
    "MKioskTy23": "severe_emergency_dialysis_crrt_yn",
    "MKioskTy24": "severe_psychiatric_emergency_closed_ward_yn",
    "MKioskTy25": "severe_ophthalmic_emergency_surgery_yn",
    "MKioskTy26": "severe_adult_interventional_radiology_yn",
    "MKioskTy27": "severe_infant_interventional_radiology_yn",

    "MKioskTy10Msg": "severe_infant_intussusception_obstruction_msg",
    "MKioskTy12Msg": "severe_infant_gi_emergency_endoscopy_msg",
    "MKioskTy14Msg": "severe_infant_bronchial_emergency_endoscopy_msg",
    "MKioskTy15Msg": "severe_low_birth_weight_infant_msg",
    "MKioskTy27Msg": "severe_infant_interventional_radiology_msg",
}

print("컬럼 사전 준비 완료")
print("실시간 병상 관련 컬럼 수:", len(REALTIME_COLUMN_MAP))
print("중증질환 관련 컬럼 수:", len(SEVERE_COLUMN_MAP))
## 4. 병원 기본정보 수집
# %%
SIDO_LIST = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]


def get_hospital_list_by_sido(sido: str) -> pd.DataFrame:
    print(f"[병원 기본정보 수집] {sido}")

    df = call_api_all_pages(
        endpoint="getEgytListInfoInqire",
        params={
            "Q0": sido,
            "ORD": "ADDR",
        },
        num_of_rows=1000,
    )

    if df.empty:
        return pd.DataFrame()

    df["api_sido"] = sido
    return df


hospital_master_raw_list = []

for sido in SIDO_LIST:
    df = get_hospital_list_by_sido(sido)
    hospital_master_raw_list.append(df)
    time.sleep(0.2)

hospital_master_raw = pd.concat(hospital_master_raw_list, ignore_index=True)

hospital_master_raw.to_csv(
    f"{DATA_DIR}/hospital_master_raw.csv",
    index=False,
    encoding="utf-8-sig"
)

print("병원 기본정보 원자료 행 수:", len(hospital_master_raw))
hospital_master_raw.head()
## 5. 병원 기본정보 전처리
# %%
master_cols = [
    "hpid",
    "phpid",
    "dutyName",
    "dutyAddr",
    "api_sido",
    "dutyEmcls",
    "dutyEmclsName",
    "dutyTel1",
    "dutyTel3",
    "wgs84Lat",
    "wgs84Lon",
]

for col in master_cols:
    if col not in hospital_master_raw.columns:
        hospital_master_raw[col] = None

hospital_master = hospital_master_raw[master_cols].copy()

hospital_master = hospital_master.rename(columns={
    "phpid": "old_hpid",
    "dutyName": "hospital_name",
    "api_sido": "sido",
    "dutyEmcls": "emergency_type_code",
    "dutyEmclsName": "emergency_type_name",
    "dutyTel1": "tel_main",
    "dutyTel3": "emergency_tel",
    "wgs84Lat": "lat",
    "wgs84Lon": "lon",
})


# 주소에서 시군구 추출 함수
def extract_sigungu(address):
    if pd.isna(address):
        return None

    parts = str(address).split()

    # 일반 주소 예:
    # 서울특별시 중랑구 신내로 ...
    # 경기도 성남시 분당구 ...
    # 제주특별자치도 제주시 ...
    if len(parts) >= 2:
        return parts[1]

    return None


hospital_master["sigungu"] = hospital_master["dutyAddr"].apply(extract_sigungu)

hospital_master["lat"] = pd.to_numeric(hospital_master["lat"], errors="coerce")
hospital_master["lon"] = pd.to_numeric(hospital_master["lon"], errors="coerce")

hospital_master = hospital_master.dropna(subset=["hpid", "hospital_name"])
hospital_master = hospital_master.drop_duplicates(subset=["hpid"], keep="first")

hospital_master = hospital_master[
    [
        "hpid",
        "old_hpid",
        "hospital_name",
        "dutyAddr",
        "sido",
        "sigungu",
        "emergency_type_code",
        "emergency_type_name",
        "tel_main",
        "emergency_tel",
        "lat",
        "lon",
    ]
]

hospital_master.to_csv(
    f"{DATA_DIR}/hospital_master.csv",
    index=False,
    encoding="utf-8-sig"
)

print("병원 기본정보 전처리 완료:", len(hospital_master))
hospital_master.head()
## 6. 실시간 조회용 지역 조합 만들기
# %%
region_pairs = (
    hospital_master[["sido", "sigungu"]]
    .dropna()
    .drop_duplicates()
    .sort_values(["sido", "sigungu"])
    .reset_index(drop=True)
)

region_pairs.to_csv(
    f"{DATA_DIR}/region_pairs.csv",
    index=False,
    encoding="utf-8-sig"
)

print("지역 조합 수:", len(region_pairs))
region_pairs.head()
## 7. 실시간 가용병상정보 전체 수집
# %%
def get_realtime_beds_by_region(sido: str, sigungu: str) -> pd.DataFrame:
    print(f"[실시간 병상 수집] {sido} {sigungu}")

    df = call_api_all_pages(
        endpoint="getEmrrmRltmUsefulSckbdInfoInqire",
        params={
            "STAGE1": sido,
            "STAGE2": sigungu,
        },
        num_of_rows=1000,
    )

    if df.empty:
        return pd.DataFrame()

    df["query_sido"] = sido
    df["query_sigungu"] = sigungu
    return df


realtime_beds_raw_list = []

for _, row in region_pairs.iterrows():
    df = get_realtime_beds_by_region(row["sido"], row["sigungu"])
    realtime_beds_raw_list.append(df)
    time.sleep(0.2)

realtime_beds_raw = (
    pd.concat(realtime_beds_raw_list, ignore_index=True)
    if realtime_beds_raw_list
    else pd.DataFrame()
)

realtime_beds_raw.to_csv(
    f"{DATA_DIR}/realtime_beds_raw.csv",
    index=False,
    encoding="utf-8-sig"
)

print("실시간 병상 원자료 행 수:", len(realtime_beds_raw))
print("실시간 병상 원자료 컬럼 수:", len(realtime_beds_raw.columns))
realtime_beds_raw.head()
## 8. 실시간 병상정보 wide 전처리
# %%
# 원본 컬럼명을 소문자 기준으로 정리하기 위해 복사
realtime_beds = realtime_beds_raw.copy()

# HVS01처럼 대문자로 오는 경우를 대비해서 컬럼명을 lower 처리한 매핑도 준비
lower_rename_map = {}
for col in realtime_beds.columns:
    col_lower = col.lower()
    if col_lower in REALTIME_COLUMN_MAP:
        lower_rename_map[col] = REALTIME_COLUMN_MAP[col_lower]
    elif col in REALTIME_COLUMN_MAP:
        lower_rename_map[col] = REALTIME_COLUMN_MAP[col]

realtime_beds = realtime_beds.rename(columns=lower_rename_map)

# hpid 없으면 생성
if "hpid" not in realtime_beds.columns:
    raise ValueError("실시간 병상 데이터에 hpid 컬럼이 없습니다.")

# query_sido/query_sigungu는 유지
keep_cols = [
    col for col in realtime_beds.columns
    if col in set(REALTIME_COLUMN_MAP.values()) or col in ["query_sido", "query_sigungu"]
]

realtime_beds_wide = realtime_beds[keep_cols].copy()

# 수집 시각 추가
realtime_beds_wide["collected_at"] = COLLECTED_AT

# 숫자형으로 바꿔야 하는 컬럼
# avail_, standard_ 중에서 전화/상태/yn이 아닌 것 위주
for col in realtime_beds_wide.columns:
    if (
        col.startswith("avail_")
        or col.startswith("standard_")
    ) and not col.endswith("_yn") and "phone" not in col and "status" not in col:
        realtime_beds_wide[col] = pd.to_numeric(realtime_beds_wide[col], errors="coerce")

# Y/N 계열 정리
yn_like_cols = [
    col for col in realtime_beds_wide.columns
    if col.endswith("_yn") or col.endswith("_status")
]

for col in yn_like_cols:
    realtime_beds_wide[col] = realtime_beds_wide[col].apply(normalize_yn)

# 업데이트 시각 정리
if "realtime_updated_at" in realtime_beds_wide.columns:
    realtime_beds_wide["realtime_updated_at"] = realtime_beds_wide["realtime_updated_at"].astype(str)

realtime_beds_wide = realtime_beds_wide.dropna(subset=["hpid"])
realtime_beds_wide = realtime_beds_wide.drop_duplicates(subset=["hpid"], keep="last")

realtime_beds_wide.to_csv(
    f"{DATA_DIR}/realtime_beds_wide.csv",
    index=False,
    encoding="utf-8-sig"
)

print("실시간 병상 wide 데이터 행 수:", len(realtime_beds_wide))
print("실시간 병상 wide 데이터 컬럼 수:", len(realtime_beds_wide.columns))
realtime_beds_wide.head()
## 9. 중증질환자 수용가능정보 수집
# %%
def get_severe_disease_by_region(sido: str, sigungu: str) -> pd.DataFrame:
    print(f"[중증질환 수용정보 수집] {sido} {sigungu}")

    df = call_api_all_pages(
        endpoint="getSrsillDissAceptncPosblInfoInqire",
        params={
            "STAGE1": sido,
            "STAGE2": sigungu,
            # SM_TYPE은 옵션이므로 넣지 않음.
            # 넣지 않으면 해당 지역의 중증질환 수용정보를 넓게 가져오는 방식.
        },
        num_of_rows=1000,
    )

    if df.empty:
        return pd.DataFrame()

    df["query_sido"] = sido
    df["query_sigungu"] = sigungu
    return df


severe_disease_raw_list = []

for _, row in region_pairs.iterrows():
    df = get_severe_disease_by_region(row["sido"], row["sigungu"])
    severe_disease_raw_list.append(df)
    time.sleep(0.2)

severe_disease_raw = (
    pd.concat(severe_disease_raw_list, ignore_index=True)
    if severe_disease_raw_list
    else pd.DataFrame()
)

severe_disease_raw.to_csv(
    f"{DATA_DIR}/severe_disease_raw.csv",
    index=False,
    encoding="utf-8-sig"
)

print("중증질환 원자료 행 수:", len(severe_disease_raw))
print("중증질환 원자료 컬럼 수:", len(severe_disease_raw.columns))
severe_disease_raw.head()
## 10. 중증질환자 수용가능정보 wide 전처리
# %%
severe = severe_disease_raw.copy()

# API 응답에서 MKioskTy 대소문자가 흔들릴 수 있어 보정
severe_rename_map = {}

for col in severe.columns:
    matched = False

    for source_col, target_col in SEVERE_COLUMN_MAP.items():
        if col.lower() == source_col.lower():
            severe_rename_map[col] = target_col
            matched = True
            break

severe = severe.rename(columns=severe_rename_map)

if "hpid" not in severe.columns:
    print("주의: 중증질환 데이터에 hpid가 없을 수 있습니다.")
    print("현재 컬럼:", severe.columns.tolist())

keep_cols = [
    col for col in severe.columns
    if col in set(SEVERE_COLUMN_MAP.values()) or col in ["query_sido", "query_sigungu"]
]

severe_disease_wide = severe[keep_cols].copy()

if "hpid" in severe_disease_wide.columns:
    severe_disease_wide = severe_disease_wide.dropna(subset=["hpid"])
    severe_disease_wide = severe_disease_wide.drop_duplicates(subset=["hpid"], keep="last")

# Y/N/가능/불가능 정리
for col in severe_disease_wide.columns:
    if col.endswith("_yn"):
        severe_disease_wide[col] = severe_disease_wide[col].apply(normalize_yn)

severe_disease_wide["severe_collected_at"] = COLLECTED_AT

severe_disease_wide.to_csv(
    f"{DATA_DIR}/severe_disease_wide.csv",
    index=False,
    encoding="utf-8-sig"
)

print("중증질환 wide 데이터 행 수:", len(severe_disease_wide))
print("중증질환 wide 데이터 컬럼 수:", len(severe_disease_wide.columns))
severe_disease_wide.head()
## 11. 병원 기본정보 + 실시간 병상 + 중증질환 통합
# %%
hospital_er = hospital_master.merge(
    realtime_beds_wide,
    on="hpid",
    how="left"
)

if "hpid" in severe_disease_wide.columns:
    hospital_er = hospital_er.merge(
        severe_disease_wide,
        on="hpid",
        how="left",
        suffixes=("", "_severe")
    )

hospital_er.to_csv(
    f"{DATA_DIR}/hospital_er_preprocessed_wide.csv",
    index=False,
    encoding="utf-8-sig"
)

print("최종 통합 데이터 행 수:", len(hospital_er))
print("최종 통합 데이터 컬럼 수:", len(hospital_er.columns))

hospital_er.head()
## 12. 컬럼 설명표 저장
# %%
dictionary_rows = []

# 병원 기본정보
master_dict = {
    "hpid": "기관 ID",
    "old_hpid": "구 기관 ID",
    "hospital_name": "병원명",
    "dutyAddr": "주소",
    "sido": "시도",
    "sigungu": "시군구",
    "emergency_type_code": "응급의료기관 분류 코드",
    "emergency_type_name": "응급의료기관 분류명",
    "tel_main": "대표전화",
    "emergency_tel": "응급실 전화",
    "lat": "위도",
    "lon": "경도",
}

for col, desc in master_dict.items():
    dictionary_rows.append({
        "column": col,
        "group": "hospital_master",
        "description": desc
    })

for src, target in REALTIME_COLUMN_MAP.items():
    dictionary_rows.append({
        "column": target,
        "group": "realtime_beds",
        "description": f"원본 컬럼 {src} 기반 실시간 병상/장비/기준병상 정보"
    })

for src, target in SEVERE_COLUMN_MAP.items():
    dictionary_rows.append({
        "column": target,
        "group": "severe_disease",
        "description": f"원본 컬럼 {src} 기반 중증질환 수용가능정보"
    })

column_dictionary = pd.DataFrame(dictionary_rows).drop_duplicates()

column_dictionary.to_csv(
    f"{DATA_DIR}/column_dictionary.csv",
    index=False,
    encoding="utf-8-sig"
)

print("컬럼 설명표 저장 완료")
column_dictionary.head(20)
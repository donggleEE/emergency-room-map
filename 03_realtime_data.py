from __future__ import annotations

import os
import time
import argparse
import json
import requests
import pandas as pd
import xml.etree.ElementTree as ET

from math import ceil
from datetime import datetime


# ============================================================
# 0. 기본 설정
# ============================================================

BASE_URL = "https://apis.data.go.kr/B552657/ErmctInfoInqireService"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def load_service_key() -> str | None:
    key = os.getenv("ER_API_KEY") or os.getenv("SERVICE_KEY")

    if key:
        return key.strip()

    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return None

    with open(env_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            name, value = line.split("=", 1)
            name = name.strip().lstrip("\ufeff")

            if name in ["ER_API_KEY", "SERVICE_KEY"]:
                return value.strip().strip('"').strip("'")

    return None


SERVICE_KEY = load_service_key()

COLLECTED_AT = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

STATUS_PATH = f"{DATA_DIR}/last_update_status.txt"
STATUS_JSON_PATH = f"{DATA_DIR}/last_update_status.json"
update_notes = []


def write_status(message: str):
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        f.write(message)

    print(message)


def write_status_json(payload: dict):
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(STATUS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_failure_and_exit(message: str, target: str | None = None):
    write_status_json({
        "target": target,
        "run_at": COLLECTED_AT,
        "success": False,
        "realtime_update_success": False,
        "realtime_updated_count": 0,
        "severe_update_success": False,
        "severe_updated_count": 0,
        "api_quota_exceeded": False,
        "latest_realtime_source_updated_at_from_this_run": None,
        "current_latest_realtime_source_updated_at": None,
        "notes": [message],
    })
    write_status(message)
    raise SystemExit(1)


if not SERVICE_KEY:
    write_failure_and_exit("업데이트 실패: ER_API_KEY 또는 SERVICE_KEY가 설정되어 있지 않습니다.")


def max_realtime_updated_at(df: pd.DataFrame):
    if "realtime_updated_at" not in df.columns:
        return None

    values = df["realtime_updated_at"].dropna().astype(str).str.strip()
    values = values[values != ""]

    if values.empty:
        return None

    return values.max()


# ============================================================
# 1. 실행 인자 받기
# ============================================================

parser = argparse.ArgumentParser()
parser.add_argument("--sido", type=str, default="전국")
parser.add_argument("--sigungu", type=str, default="전체")
args = parser.parse_args()

if args.sido == "전국":
    print("전국 업데이트 모드입니다. 시간이 오래 걸리고 API 호출 제한이 발생할 수 있습니다.")


# ============================================================
# 2. API 공통 함수
# ============================================================

API_QUOTA_EXCEEDED = False
realtime_update_success = False
severe_update_success = False
realtime_updated_count = 0
severe_updated_count = 0
latest_realtime_source_updated_at = None


def xml_to_dataframe(xml_text: str) -> pd.DataFrame:
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
    global API_QUOTA_EXCEEDED

    url = f"{BASE_URL}/{endpoint}"

    request_params = {
        "serviceKey": SERVICE_KEY,
        "pageNo": 1,
        "numOfRows": 1000,
    }

    if params:
        request_params.update(params)

    try:
        response = requests.get(
            url,
            params=request_params,
            timeout=30
        )

        print("[API 호출]", endpoint, request_params)

        if response.status_code == 429:
            API_QUOTA_EXCEEDED = True
            print("상태코드 오류: 429")
            print("API token quota exceeded")
            return None

        if response.status_code != 200:
            print("상태코드 오류:", response.status_code)
            print(response.text[:1000])
            return None

        text = response.text

        if "API token quota exceeded" in text:
            API_QUOTA_EXCEEDED = True
            print("API token quota exceeded")
            return None

        return text

    except requests.RequestException as e:
        print("API 요청 오류:", e)
        return None


def call_api_all_pages(
    endpoint: str,
    params: dict | None = None,
    num_of_rows: int = 1000,
    sleep_sec: float = 0.5,
) -> pd.DataFrame:
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

            if not xml_text:
                continue

            df_page = xml_to_dataframe(xml_text)
            dfs.append(df_page)

            time.sleep(sleep_sec)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def normalize_yn(value):
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


# ============================================================
# 3. 컬럼 매핑
# ============================================================

REALTIME_COLUMN_MAP = {
    "hpid": "hpid",
    "phpid": "old_hpid",
    "dutyName": "realtime_hospital_name",
    "dutyname": "realtime_hospital_name",
    "dutyTel3": "realtime_emergency_tel",
    "hvidate": "realtime_updated_at",

    "hvec": "avail_er_general_beds",
    "hvoc": "avail_operating_rooms",
    "hvcc": "avail_icu_neurology",
    "hvncc": "avail_icu_neonatal",
    "hvccc": "avail_icu_thoracic_surgery",
    "hvicc": "avail_icu_general",
    "hvgc": "avail_inpatient_general_beds",

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
}


# ============================================================
# 4. 기존 데이터 불러오기
# ============================================================

hospital_master_path = f"{DATA_DIR}/hospital_master.csv"
region_pairs_path = f"{DATA_DIR}/region_pairs.csv"
old_realtime_path = f"{DATA_DIR}/realtime_beds_wide.csv"
old_severe_path = f"{DATA_DIR}/severe_disease_wide.csv"

if not os.path.exists(hospital_master_path):
    write_failure_and_exit("업데이트 실패: data/hospital_master.csv 파일이 없습니다.")

if not os.path.exists(region_pairs_path):
    write_failure_and_exit("업데이트 실패: data/region_pairs.csv 파일이 없습니다.")

hospital_master = pd.read_csv(
    hospital_master_path,
    encoding="utf-8-sig",
    dtype={"hpid": str}
)

region_pairs = pd.read_csv(
    region_pairs_path,
    encoding="utf-8-sig"
)

# ============================================================
# 업데이트 범위 설정
# 1) 전국 / 전체: 모든 region_pairs 사용
# 2) 특정 시도 / 전체: 해당 시도의 모든 시군구 사용
# 3) 특정 시도 / 특정 시군구: 해당 시군구만 사용
# ============================================================

if args.sido == "전국":
    target_text = "전국 전체"
    region_pairs = region_pairs.copy()

else:
    if args.sigungu == "전체":
        target_text = f"{args.sido} 전체"
        region_pairs = region_pairs[region_pairs["sido"] == args.sido]
    else:
        target_text = f"{args.sido} {args.sigungu}"
        region_pairs = region_pairs[
            (region_pairs["sido"] == args.sido)
            & (region_pairs["sigungu"] == args.sigungu)
        ]

region_pairs = region_pairs.reset_index(drop=True)

print("이번 업데이트 대상:", target_text)
print("이번 업데이트 대상 지역:")
print(region_pairs)
print("업데이트 대상 지역 수:", len(region_pairs))
print("기존 병원 기본정보:", len(hospital_master))

if len(region_pairs) == 0:
    write_failure_and_exit(f"업데이트 실패: {target_text} 지역 조합이 없습니다.", target_text)


# ============================================================
# 5. 실시간 병상정보 재수집
# ============================================================

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
    df_region = get_realtime_beds_by_region(row["sido"], row["sigungu"])
    realtime_beds_raw_list.append(df_region)
    time.sleep(0.5)

realtime_beds_raw = (
    pd.concat(realtime_beds_raw_list, ignore_index=True)
    if realtime_beds_raw_list
    else pd.DataFrame()
)

print("실시간 병상 원자료 행 수:", len(realtime_beds_raw))
print("실시간 병상 원자료 컬럼:", realtime_beds_raw.columns.tolist())

if os.path.exists(old_realtime_path):
    old_realtime_wide = pd.read_csv(
        old_realtime_path,
        encoding="utf-8-sig",
        dtype={
            "hpid": str,
            "realtime_updated_at": str,
            "collected_at": str,
        }
    )
else:
    old_realtime_wide = pd.DataFrame(columns=["hpid"])

# 새 API 결과가 없으면 기존 데이터 유지
if realtime_beds_raw.empty:
    realtime_beds_wide = old_realtime_wide.copy()

    if API_QUOTA_EXCEEDED:
        update_notes.append(
            f"실시간 병상 업데이트 실패: API 호출 한도 초과로 기존 병상 데이터를 유지했습니다. 대상: {target_text}"
        )
    else:
        update_notes.append(
            f"실시간 병상 업데이트 실패: 선택 범위의 API 결과가 비어 있어 기존 병상 데이터를 유지했습니다. 대상: {target_text}"
        )

else:
    realtime_beds_raw.to_csv(
        f"{DATA_DIR}/realtime_beds_raw_latest.csv",
        index=False,
        encoding="utf-8-sig"
    )

    realtime_beds = realtime_beds_raw.copy()

    lower_rename_map = {}

    for col in realtime_beds.columns:
        col_lower = col.lower()

        if col_lower in REALTIME_COLUMN_MAP:
            lower_rename_map[col] = REALTIME_COLUMN_MAP[col_lower]
        elif col in REALTIME_COLUMN_MAP:
            lower_rename_map[col] = REALTIME_COLUMN_MAP[col]

    realtime_beds = realtime_beds.rename(columns=lower_rename_map)

    # hpid 대소문자 보정
    for col in realtime_beds.columns:
        if col.lower() == "hpid":
            realtime_beds = realtime_beds.rename(columns={col: "hpid"})
            break

    if "hpid" not in realtime_beds.columns:
        realtime_beds_raw.to_csv(
            f"{DATA_DIR}/debug_realtime_beds_no_hpid.csv",
            index=False,
            encoding="utf-8-sig"
        )

        realtime_beds_wide = old_realtime_wide.copy()

        update_notes.append(
            f"실시간 병상 업데이트 실패: API 응답에 hpid 컬럼이 없어 기존 병상 데이터를 유지했습니다. 대상: {target_text}"
        )

    else:
        keep_cols = [
            col for col in realtime_beds.columns
            if col in set(REALTIME_COLUMN_MAP.values()) or col in ["query_sido", "query_sigungu"]
        ]

        new_realtime_wide = realtime_beds[keep_cols].copy()
        new_realtime_wide["collected_at"] = COLLECTED_AT

        for col in new_realtime_wide.columns:
            if (
                col.startswith("avail_")
                or col.startswith("standard_")
            ) and not col.endswith("_yn") and "phone" not in col and "status" not in col:
                new_realtime_wide[col] = pd.to_numeric(new_realtime_wide[col], errors="coerce")

        yn_like_cols = [
            col for col in new_realtime_wide.columns
            if col.endswith("_yn") or col.endswith("_status")
        ]

        for col in yn_like_cols:
            new_realtime_wide[col] = new_realtime_wide[col].apply(normalize_yn)

        if "realtime_updated_at" in new_realtime_wide.columns:
            new_realtime_wide["realtime_updated_at"] = new_realtime_wide["realtime_updated_at"].astype(str)

        new_realtime_wide = new_realtime_wide.dropna(subset=["hpid"])
        new_realtime_wide = new_realtime_wide.drop_duplicates(subset=["hpid"], keep="last")

        # 기존 전국 데이터에서 새로 받은 병원만 제거 후 새 데이터 붙이기
        if not old_realtime_wide.empty and "hpid" in old_realtime_wide.columns:
            old_realtime_wide = old_realtime_wide[
                ~old_realtime_wide["hpid"].isin(new_realtime_wide["hpid"])
            ]

        realtime_beds_wide = pd.concat(
            [old_realtime_wide, new_realtime_wide],
            ignore_index=True
        )

        realtime_beds_wide = realtime_beds_wide.drop_duplicates(subset=["hpid"], keep="last")
        realtime_update_success = True
        realtime_updated_count = len(new_realtime_wide)
        latest_realtime_source_updated_at = max_realtime_updated_at(new_realtime_wide)

        realtime_beds_wide.to_csv(
            f"{DATA_DIR}/realtime_beds_wide.csv",
            index=False,
            encoding="utf-8-sig"
        )

        update_notes.append(
            f"실시간 병상 데이터 갱신 완료: {target_text} / 갱신 병원 수: {realtime_updated_count}"
        )

print("실시간 병상 wide 유지/갱신 완료:", len(realtime_beds_wide))


# ============================================================
# 6. 중증질환 수용가능정보 재수집
# ============================================================

def get_severe_disease_by_region(sido: str, sigungu: str) -> pd.DataFrame:
    print(f"[중증질환 수용정보 수집] {sido} {sigungu}")

    df = call_api_all_pages(
        endpoint="getSrsillDissAceptncPosblInfoInqire",
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


severe_disease_raw_list = []

for _, row in region_pairs.iterrows():
    df_region = get_severe_disease_by_region(row["sido"], row["sigungu"])
    severe_disease_raw_list.append(df_region)
    time.sleep(0.5)

severe_disease_raw = (
    pd.concat(severe_disease_raw_list, ignore_index=True)
    if severe_disease_raw_list
    else pd.DataFrame()
)

print("중증질환 원자료 행 수:", len(severe_disease_raw))
print("중증질환 원자료 컬럼:", severe_disease_raw.columns.tolist())

if os.path.exists(old_severe_path):
    old_severe_wide = pd.read_csv(
        old_severe_path,
        encoding="utf-8-sig",
        dtype={"hpid": str}
    )
else:
    old_severe_wide = pd.DataFrame(columns=["hpid"])

# 새 API 결과가 없으면 기존 데이터 유지
if severe_disease_raw.empty:
    severe_disease_wide = old_severe_wide.copy()

    if API_QUOTA_EXCEEDED:
        update_notes.append(
            f"중증질환 업데이트 실패: API 호출 한도 초과로 기존 중증질환 데이터를 유지했습니다. 대상: {target_text}"
        )
    else:
        update_notes.append(
            f"중증질환 업데이트 실패 또는 결과 없음: 기존 중증질환 데이터를 유지했습니다. 대상: {target_text}"
        )

else:
    severe_disease_raw.to_csv(
        f"{DATA_DIR}/severe_disease_raw_latest.csv",
        index=False,
        encoding="utf-8-sig"
    )

    severe = severe_disease_raw.copy()

    severe_rename_map = {}

    for col in severe.columns:
        for source_col, target_col in SEVERE_COLUMN_MAP.items():
            if col.lower() == source_col.lower():
                severe_rename_map[col] = target_col
                break

    severe = severe.rename(columns=severe_rename_map)

    # hpid 대소문자 보정
    for col in severe.columns:
        if col.lower() == "hpid":
            severe = severe.rename(columns={col: "hpid"})
            break

    if "hpid" not in severe.columns:
        severe_disease_raw.to_csv(
            f"{DATA_DIR}/debug_severe_disease_no_hpid.csv",
            index=False,
            encoding="utf-8-sig"
        )

        severe_disease_wide = old_severe_wide.copy()

        update_notes.append(
            f"중증질환 업데이트 실패: API 응답에 hpid 컬럼이 없어 기존 중증질환 데이터를 유지했습니다. 대상: {target_text}"
        )

    else:
        keep_cols = [
            col for col in severe.columns
            if col in set(SEVERE_COLUMN_MAP.values()) or col in ["query_sido", "query_sigungu"]
        ]

        new_severe_wide = severe[keep_cols].copy()

        new_severe_wide = new_severe_wide.dropna(subset=["hpid"])
        new_severe_wide = new_severe_wide.drop_duplicates(subset=["hpid"], keep="last")

        for col in new_severe_wide.columns:
            if col.endswith("_yn"):
                new_severe_wide[col] = new_severe_wide[col].apply(normalize_yn)

        new_severe_wide["severe_collected_at"] = COLLECTED_AT

        # 기존 전국 데이터에서 새로 받은 병원만 제거 후 새 데이터 붙이기
        if not old_severe_wide.empty and "hpid" in old_severe_wide.columns:
            old_severe_wide = old_severe_wide[
                ~old_severe_wide["hpid"].isin(new_severe_wide["hpid"])
            ]

        severe_disease_wide = pd.concat(
            [old_severe_wide, new_severe_wide],
            ignore_index=True
        )

        severe_disease_wide = severe_disease_wide.drop_duplicates(subset=["hpid"], keep="last")
        severe_update_success = True
        severe_updated_count = len(new_severe_wide)

        severe_disease_wide.to_csv(
            f"{DATA_DIR}/severe_disease_wide.csv",
            index=False,
            encoding="utf-8-sig"
        )

        update_notes.append(
            f"중증질환 데이터 갱신 완료: {target_text} / 갱신 병원 수: {severe_updated_count}"
        )

print("중증질환 wide 유지/갱신 완료:", len(severe_disease_wide))

# ============================================================
# 7. 최종 병합
# ============================================================

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

notes_text = "\n".join(update_notes) if update_notes else "세부 업데이트 메시지 없음"
current_latest_realtime_updated_at = max_realtime_updated_at(realtime_beds_wide)

final_message = (
    f"최종 통합 데이터 저장 완료: {len(hospital_er)}행\n"
    f"대상: {target_text}\n"
    f"업데이트 실행 시각: {COLLECTED_AT}\n"
    f"현재 데이터의 최신 병상정보 갱신시각: {current_latest_realtime_updated_at or '-'}\n"
    f"{notes_text}"
)

update_success = realtime_update_success or severe_update_success

write_status_json({
    "target": target_text,
    "run_at": COLLECTED_AT,
    "success": update_success,
    "realtime_update_success": realtime_update_success,
    "realtime_updated_count": realtime_updated_count,
    "severe_update_success": severe_update_success,
    "severe_updated_count": severe_updated_count,
    "api_quota_exceeded": API_QUOTA_EXCEEDED,
    "latest_realtime_source_updated_at_from_this_run": latest_realtime_source_updated_at,
    "current_latest_realtime_source_updated_at": current_latest_realtime_updated_at,
    "notes": update_notes,
})

write_status(final_message)

if not update_success:
    print("선택 범위 실시간 업데이트 실패")
    raise SystemExit(1)

print("선택 범위 실시간 업데이트 완료")

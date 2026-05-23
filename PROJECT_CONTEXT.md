# 프로젝트 개요

## 주제

이 프로젝트는 전국 병원 및 응급실 데이터를 시각화하여 사용자가 응급실 병상과 주요 진료 자원의 가용 여부를 빠르게 확인할 수 있도록 하는 것을 목표로 한다.

## 현재 진행 방향

- 기존 웹 기반 구현을 중심으로 계속 진행한다.
- Python 기반 데이터 수집, 전처리, 시각화 흐름을 프로젝트의 주요 기반으로 사용한다.
- 명령어 실행 내역과 생성 파일 기록은 `COMMAND_LOG.md`에 남긴다.
- 별도의 모바일 앱 구조나 앱 내부 임베디드 데이터베이스는 프로젝트 방향이 바뀌기 전까지 도입하지 않는다.

## 주요 기존 파일

- `01_preprocess_er_data.py`: 데이터 전처리 작업 파일.
- `02_visualization_app.py`: 현재 웹 시각화 앱 파일.
- `03_realtime_data.py`: 실시간 응급실 데이터 수집 작업 파일.
- `requirements.txt`: pip 기반 Python 의존성 목록.
- `environment.yml`: conda 기반 Python 의존성 목록.
- `.vscode/tasks.json`: VS Code에서 선택된 Python 인터프리터로 Streamlit 앱 실행과 문법 검사를 수행하는 작업 정의.
- `data/`: 시각화에 사용하는 CSV 및 GeoJSON 데이터 폴더.

## 파일 구조 메모

- 현재 실행 기준 앱은 `02_visualization_app.py`이며, `02_visualization_app copy.py`, `02_visualization_app copy 2.py`는 보존된 복사본으로 본다.
- `03_realtime_data.py` 정상 실행 시 `data/last_update_status.json`이 생성될 수 있다.
- API 응답이 정상적으로 들어온 경우 `data/realtime_beds_raw_latest.csv`, `data/severe_disease_raw_latest.csv`가 최신 원자료 확인용으로 생성될 수 있다.
- API 응답 구조에 `hpid`가 없을 때는 원인 확인용 `data/debug_realtime_beds_no_hpid.csv`, `data/debug_severe_disease_no_hpid.csv`가 생성될 수 있다.

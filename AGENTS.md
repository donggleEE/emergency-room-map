# 작업 지침

## 프로젝트 목적

이 프로젝트는 전국 병원 데이터를 기반으로 응급실 병상과 주요 응급 진료 자원의 가용 여부를 빠르게 확인할 수 있도록 웹에서 시각화하는 프로젝트이다.

## 작업 원칙

- 모든 Markdown 문서는 한국어로 작성한다.
- 사용자가 입력한 요청과 작업 중 실행한 주요 명령어는 `COMMAND_LOG.md`에 기록한다.
- 명령어 기록에는 실행 목적과 생성된 파일 여부를 함께 남긴다.
- 기존 Python 기반 웹 시각화 구조를 우선 유지한다.
- 프로젝트 방향이 명확히 바뀌기 전까지 별도의 모바일 앱 구조나 앱 내부 임베디드 데이터베이스를 추가하지 않는다.

## 주요 파일

- `01_preprocess_er_data.py`: 응급실 및 병원 데이터 전처리.
- `02_visualization_app.py`: Streamlit/Folium 기반 웹 시각화 앱.
- `03_realtime_data.py`: 실시간 응급실 데이터 수집.
- `data/`: 전처리 결과, 실시간 데이터, GeoJSON 지도 데이터.
- `requirements.txt`: pip 기반 실행 환경 의존성.
- `environment.yml`: conda 기반 실행 환경 의존성.
- `.vscode/tasks.json`: VS Code에서 선택된 Python 인터프리터로 앱 실행과 문법 검사를 수행하는 작업 정의.
- `COMMAND_LOG.md`: 명령어 실행 및 생성 파일 기록.
- `PROJECT_CONTEXT.md`: 프로젝트 개요와 현재 진행 방향.
- `.codex/agents/project_manager.md`: 프로젝트 관리 전용 에이전트 정의.
- `.codex/agents/frontend.md`: 화면 UI 및 사용자 경험 개선 전용 에이전트 정의.
- `.codex/agents/backend.md`: 데이터 수집, 전처리, 파일 입출력 로직 개선 전용 에이전트 정의.
- `.codex/agents/tester.md`: 작성된 코드와 데이터 산출물 검증 전용 에이전트 정의.

## 작업 시 주의사항

- 기존 데이터 파일을 덮어쓰기 전에 변경 목적을 분명히 확인한다.
- 인코딩이 깨진 한글 문자열을 수정할 때는 원본 의미를 확인할 수 있는 데이터나 문맥을 먼저 살핀다.
- 사용자의 요청 범위를 벗어난 대규모 구조 변경은 피한다.

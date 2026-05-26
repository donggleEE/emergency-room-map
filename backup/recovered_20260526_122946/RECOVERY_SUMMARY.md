# 복구 백업 요약

생성 시각: 2026-05-26 12:29:46

## 백업 목적

현재 Streamlit 앱에서 GPS, 다중 지역 선택, 로딩 최적화, 문구 및 디자인 변경 등이 사라진 상태를 보존하고, 복구 후보를 비교할 수 있도록 주요 버전을 별도 파일로 백업했다.

## 주요 백업 파일

- `02_visualization_app_worktree.py`: 현재 작업트리의 앱 파일.
- `02_visualization_app_INDEX.py`: 현재 Git 스테이징 영역의 앱 파일.
- `02_visualization_app_HEAD.py`: 현재 `HEAD` 커밋의 앱 파일. 디자인 시스템, 메인 헤더 문구, 마커 제한, `returned_objects=[]`, `data_refresh_token` 등이 남아 있다.
- `02_visualization_app_copy.py`, `02_visualization_app_copy_2.py`, `02_visualization_app_copy_3.py`: 프로젝트 루트에 있던 기존 복사본 앱 파일.
- `02_visualization_app_staged.diff`: `HEAD`에서 스테이징본으로 바뀐 차이. 디자인/상태 요약/마커 제한 등 중간 작업이 빠지는 방향의 변경을 확인할 수 있다.
- `02_visualization_app_unstaged.diff`: 스테이징본에서 현재 작업트리로 바뀐 차이.
- `COMMAND_LOG_worktree.md`, `COMMAND_LOG_INDEX.md`, `COMMAND_LOG_HEAD.md`: 명령 기록의 현재본, 스테이징본, 커밋본.
- `COMMAND_LOG_unreachable_209c675.md`, `COMMAND_LOG_unreachable_f56030c.md`: `git fsck`에서 발견된 dangling blob 로그 백업.
- `git_unreachable_objects.txt`: 발견된 unreachable 객체 목록.
- `worktree_diff_stat.txt`, `cached_diff_stat.txt`: 백업 당시 변경 규모 요약.

## 발견 사항

- `HEAD`의 앱 파일에는 `apply_design_system()`, `Emergency Room Capacity Dashboard`, `MAX_HOSPITAL_MARKERS`, `data_refresh_token`, `returned_objects=[]` 등 디자인 및 로딩 관련 이전 작업 일부가 남아 있다.
- 현재 `INDEX`와 `02_visualization_app copy 3.py`는 같은 Git blob으로 확인되며, `HEAD`보다 단순한 예전 앱 구조에 가깝다.
- 현재 작업트리 앱 파일은 `INDEX`에서 일부 수정된 상태이며 `returned_objects=["last_clicked", "bounds", "zoom"]`가 남아 있다.
- `COMMAND_LOG_worktree.md`에는 GPS 현위치, GPS 기반 지역 필터와 다중 선택, 병원 popup, 마커 클릭 우선순위, Folium pane 오류 수정, tooltip 제거, 로딩 시간 개선 작업 기록이 남아 있다.
- `git fsck`에서 앱 코드로 식별되는 dangling blob은 발견되지 않았고, 발견된 두 blob은 `COMMAND_LOG.md` 계열 이전 객체로 확인했다.

## 다음 복구 기준

실제 기능 복구는 `COMMAND_LOG_worktree.md`의 작업 섹션과 `02_visualization_app_HEAD.py`의 디자인/성능 관련 구현을 기준으로, 현재 `02_visualization_app.py`에 필요한 기능을 다시 통합하는 방식이 가장 안전하다.

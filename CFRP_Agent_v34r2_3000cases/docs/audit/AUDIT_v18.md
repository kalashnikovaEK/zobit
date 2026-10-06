# v18 Python 3.14 / Windows 호환성 검토
<!-- [NEW v18] -->

## 확인된 버전 불일치

기존 v17의 START_WINDOWS.bat 및 windows_launcher_v17.py는 Python 3.12를 요구한다. check_html_runtime_v15.py도 sys.version_info[:2] != (3,12)이면 종료한다. 따라서 Python 3.14만 설치한 환경에서 기존 진입점이 정상 진행하지 못하는 문제는 확인된다.

기존 requirements-html-v15.txt의 pandas==2.2.3은 Windows x64 / cp314 wheel 조회에서 설치 후보를 찾지 못했다. 새 requirements-windows-py314-v18.txt에서는 pandas==2.3.3으로 변경했다. pandas 공식 문서도 2.3.3부터 Python 3.14 호환을 명시한다:
https://pandas.pydata.org/pandas-docs/version/2.3/whatsnew/v2.3.3.html

Numba 0.68.0의 공식 지원 표는 Python 3.14를 포함한다. 따라서 이 버전의 Numba가 원천적으로 Python 3.14를 지원하지 않는다는 진단은 맞지 않는다:
https://github.com/numba/numba/blob/main/docs/source/user/installing.rst

위의 버전 불일치는 설치 실패 요인이지만, 사용자 PC의 네이티브 비정상 종료 원인을 확정하는 증거는 아니다. 사용자 PC의 실제 오류 로그는 확보하지 못했다.

## 수정 범위

| 항목 | v18 적용 |
| --- | --- |
| Python 선택 및 버전 검사 | 표준 64비트 CPython 3.14 |
| 가상환경 | .venv_windows_py314_v18 새 생성; 기존 3.12 환경 미사용 |
| 의존성 | pandas 2.3.3, llvmlite 0.50.0 명시; 나머지 직접 의존성 버전 유지 |
| 설치 방식 | 단일 실행점에서 --only-binary=:all: 사용 |
| 진입점 | START_WINDOWS.bat 유지; 기존 setup/run 배치도 3.14 설정으로 수정 |
| 진단 | Python 실행 경로·버전, Numba 별도 프로세스 검사, 실패 시 Python 계산 전환 |
| 물리 모델 및 Guard | v17 코드 유지; 모델 해시 및 합성데이터 변경 없음 |
| 문서 | 기존 README 보존 후 v18 섹션 추가; START_HERE_PY314_v18.md 추가 |

기존 파일명 중 v15/v17이 남아 있는 것은 호출 호환성을 위한 것이다. 새 실행점이 참조하는 코드는 3.14용으로 수정되어 있다. requirements-html-v15.txt는 과거 이력으로 보존했으며 v18의 설치 명령은 requirements-windows-py314-v18.txt를 사용한다.

## 완료

| 검증 | 결과 |
| --- | --- |
| 실제 CPython 3.14.7 새 가상환경 | 모든 의존성 설치 성공 |
| pip check | No broken requirements found |
| 런타임 import 및 kinetics 평가 | 통과; Numba 0.68.0 / llvmlite 0.50.0 |
| 회귀/통합시험 12개 | 모두 통과 |
| 수동/실측 물리 계산, None 방어, 직접 spec Guard | 통과 |
| surrogate 학습·후보 물리 재계산·결과 Guard | 통과 |
| 실제 HTTP API 및 채팅 스트림 | 통과; LLM JSON 추출만 모의 |
| Python fallback 실제 계산 | nominal 및 measured 통과; cycle_time=None 유지 |
| 지연된 수동 응답 폐기 | 원본 JS run() 시험 통과 |
| Windows x64 / cp314 전체 의존성 wheel | 직접/간접 의존성 21종 조회·다운로드 성공 |
| Windows bootstrap 순서 | 설치→검사→실행 및 검사 실패시 서버 실행 차단 모의시험 통과 |

설치 목록: numpy 2.3.5, scipy 1.17.0, pandas 2.3.3, scikit-learn 1.8.0, numba 0.68.0, llvmlite 0.50.0, plotly 7.1.0, requests 2.34.2. 테스트 호스트는 Linux이며 배포 진입점은 Windows 전용이다. Windows wheel 다운로드 성공은 Windows 바이너리를 실제 import했다는 의미가 아니다.

로그: artifacts/runtime_py314_v18.log, artifacts/tests_py314_v18.log, artifacts/fallback_py314_v18.log, artifacts/install_py314_v18.log, artifacts/wheels_py314_windows_v18.log, artifacts/old_profile_cp314_failure_v18.log. v17의 기존 로그는 이력으로 보존한다.

## 미완료 및 한계

| 항목 | 상태 |
| --- | --- |
| Windows 실제 신규 설치·더블클릭·자동 브라우저 열기 | Windows 호스트가 없어 미검증 |
| 사용자 PC의 Numba 비정상 종료 원인 | 미확정; 이번 3.14 환경에서는 정상 |
| 실제 Ollama 모델 추론·브라우저 WebGL | 미검증 |
| 기존 OpenAI agent 경로 | 배포에 없어 미연결; 복원하지 않음 |
| 독립 실험 정확도 | 미검증 |

Guard/요약 검증의 기존 한계와 통합개선항목 전체 판정은 AUDIT_v17.md를 따른다. 3.14 변경으로 물리 모델의 외부 신뢰성 검증이 추가된 것은 아니다.

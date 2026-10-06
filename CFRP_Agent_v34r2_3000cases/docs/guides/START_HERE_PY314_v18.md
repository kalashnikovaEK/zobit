# Windows / Python 3.14 실행
<!-- [NEW v18] -->

1. 표준 64비트 Python 3.14를 설치한다. 기존 3.12를 지울 필요는 없다.
2. ZIP을 새 일반 폴더에 압축 해제한다. ZIP 내부에서 직접 실행하지 않는다.
3. START_WINDOWS.bat를 더블클릭한다.
4. 첫 실행의 패키지 설치와 런타임 검사가 끝날 때까지 기다린다.
5. 자동으로 열린 브라우저 또는 http://127.0.0.1:8765/ 에서 수동 계산을 실행한다. 서버 창은 유지한다.

환경은 .venv_windows_py314_v18에 새로 생성한다. Python Launcher가 없으면 PATH의 python을 확인하며 3.14가 아니면 오류를 표시한다. 오류 발생 시 setup_windows_v18.log와 runtime_check_v18.log를 확인한다. Numba 격리 검사가 실패하면 느릴 수 있는 Python 계산 경로로 전환한다.

AI 채팅에는 Ollama 서버와 선택한 모델이 별도로 필요하다. 수동 계산에는 필요하지 않다. 기존 README의 3.12 안내와 v15 requirements 파일은 과거 이력이며 현재 설치에는 사용하지 않는다. Windows x64용 패키지 확인과 실제 Windows 더블클릭 검증은 서로 다르므로 AUDIT_v18.md의 상태 구분을 확인한다.

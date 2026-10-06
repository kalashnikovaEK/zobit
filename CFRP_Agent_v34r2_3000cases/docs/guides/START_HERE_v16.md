# v16 배포용 시작 안내
<!-- [NEW v16] -->
Python 3.12를 사용한다. 기존 Python 3.14는 지우지 않아도 된다.
Windows: setup_html_v15_windows.bat → run_html_v15_windows.bat.
macOS/Linux: bash setup_html_v15_mac_linux.sh → bash run_html_v15_mac_linux.sh.
주소: http://127.0.0.1:8765/ . 서버 창은 켜 둔다.
HTML 전용 가상환경 .venv_html_v15와 requirements-html-v15.txt를 사용한다. Streamlit은 설치하지 않는다.

AI 사용: Ollama 설치 후 `ollama pull qwen3:8b` 또는 `ollama pull gemma2`. Ollama 서버 실행 → 화면 모델 선택 → 연결 확인 → 요청 입력. 서버/모델이 없으면 자연어 기능은 오류를 표시한다. 수동 물리 계산은 계속 사용할 수 있다.
요청 예: AS4/8552 두께 10mm 최고온도 200도 이하에서 승온속도 유지온도 유지시간 모두 최적화해서 공정시간을 최소화해줘.
채팅은 요청마다 독립 해석이다. 모델 결과 숫자는 물리 검산을 거친다. 실측 CSV/JSON은 별도 실측 재현 화면에서 사용한다.
후보 선택·시간·깊이·기준 비교를 확인하고 검토자 기록을 저장한다. 화면은 1D 계산을 3D로 표시한다. 실제 설비 제어 기능은 없다.

근거·재현·연구 화면은 Evidence ZIP이다. 두 ZIP을 같은 부모 폴더에 풀어 CFRP_Agent_v16을 합치면 연구 코드를 복원할 수 있다. 그때만 requirements-research-v15.txt 또는 requirements-validation-v15.txt를 선택 설치한다.
실제 Ollama 추론·Windows clean 설치·WebGL·독립 실험 정확도는 미검증/미완료다.

# v16 분리 검증
<!-- [NEW v16] -->
배포용 폴더만 Python import 경로에 넣고 Streamlit import를 강제 차단한 상태에서 실제 HTTP·물리 solver·학습·최적화·결과 guard를 실행했다. DOM 시험에서 채팅·후보 선택·시간/깊이·비교·검토 기록·오래된 응답 차단이 통과했다. Ollama JSON과 Plotly 렌더링만 모의다. 로그는 Evidence ZIP의 artifacts/distribution_smoke_v16.log에 있다.
모든 v15 원본 비캐시 파일은 두 ZIP 중 하나에 보존하며 PACKAGE_MAP_v16.json의 SHA256으로 확인했다. 원본 README는 Evidence의 README_history_v15.md로 이름만 바꾸어 보존했다. 배포 README는 별도 안내이며 과거 README 내용을 고치지 않았다.

완료: 배포/연구·근거 분리, 캐시 삭제, 배포 폴더 단독 연결시험, 모든 원본 비캐시 파일 해시 확인.
미완료: Windows clean 설치, 실제 모델 추론, 실제 WebGL 렌더링, 독립 실험 정확도.
Python/Numba는 실제 실행 중 캐시를 다시 생성할 수 있다. 이번 ZIP에는 캐시가 없다. 물리·AI 코드는 바이트 유지한다.

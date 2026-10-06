# v19 즉시 시각화 검증
<!-- [NEW v19] -->

사용자 화면에서 Guard passed와 물리 계산 완료를 확인했다. AI→표시 경로는 기존에도 연결되어 있다. 관찰된 결함은 표시 폭과 빈 시각화 영역이다. 빈 3D가 WebGL 때문인지는 화면만으로 확정하지 않았다.

새 live_view_v19.js는 기존 계산/Guard를 바꾸지 않고 검증된 display JSON을 SVG로 표시한다. interactive.html에 갱신/시간 동기화 호출과 폭 축소 CSS를 추가하고 순차 extension 목록에 연결했다. integrated_api_v14.py에 asset을 추가했다. workbench_v14.js는 결과 없는 비교 공간을 숨긴다. stack_view_v14.js는 렌더 예외·Promise rejection·WebGL context loss 안내를 추가한다.

물리 core.py, measured_boundary_v11.py, AI.py, AI_guard.py 및 모델 학습 데이터는 v18과 동일하다. 의존성/Windows 실행 설정도 동일하다.

실제 T1=120/hold1=60 공정 계산 출력과 짧은 실측 출력으로 Node DOM 모의시험을 실행했다. 표시 수치·SVG 생성·최고온도 시점·시간 연동·경화도 모드·재생·무효화·실측 null 표시를 확인했다. Plotly 렌더 거절의 안내도 모의했다. 기존 지연 응답 폐기 시험 통과. Python 회귀시험은 Linux Python 3.12 호스트에서 실행하며 Windows 3.14 실행을 뜻하지 않는다. Windows bootstrap 시험만 호스트 버전을 3.14로 모의한다.

실제 브라우저/화면 폭/WebGL 시각 확인은 Chromium 실행 파일 부재로 수행하지 못했다. v18의 Python 3.14 설치 결과는 이전 검증이며 이번 3.14 재시험과 구분한다.

최종 검증: 기존 회귀 12개 중 계산/Guard/async/HTTP 등 11개는 전체 실행에서 통과했다. Windows bootstrap 1개는 Linux 호스트의 버전 제한으로 최초 실패하여 테스트의 Python 버전·sysconfig 응답을 명시적으로 모의한 뒤 단독 재실행해 통과했다. 제품 launcher는 수정하지 않았다. SVG 시험과 3D 실패 안내 시험, 지연 응답 시험 모두 통과했다. 신규 asset handler도 통과했다.

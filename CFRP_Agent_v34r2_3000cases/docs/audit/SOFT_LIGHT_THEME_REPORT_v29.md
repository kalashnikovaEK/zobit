# [NEW v29] Soft Light Theme 검증 결과

기존 v28 구조·레이아웃·텍스트·버튼·이벤트를 보존하고 시각 스타일만 적용했습니다.
HTML 기존 스타일 끝에 독립 override를 추가했습니다. 새 asset 로더나 기능은 추가하지 않았습니다.
차트 관련 JavaScript 4개 파일은 색상 리터럴만 수정했으며 각 변경 줄에 [NEW v29] 표시를 붙였습니다.
물리 색상 범위·계산값·3D 형상·카메라·프레임·학습 모델은 유지했습니다.

| 완료 | 확인 근거 |
| --- | --- |
| HTML 테마 실제 연결 | interactive.html의 기존 style 블록에 직접 삽입 |
| UI 구조·텍스트 보존 | style/script를 제외한 원본 HTML 완전 일치 |
| 배치 보존 | 추가 CSS에 display/position/width/height/padding/margin/gap/grid-template 선언 없음 |
| 계산 및 서버 코드 보존 | 모든 Python 파일과 모델/데이터 원본 바이트 일치 |
| Python·JavaScript 문법 | 전체 Python AST, 전체 JS 및 HTML inline JS 검사 통과 |
| 지연 응답·SVG·demo·3D 회귀 | 기존 Node 시험 4개 통과 |

| 미완료 / 미검증 | 범위 |
| --- | --- |
| 실제 브라우저 시각 검증 | 실제 렌더링 및 사용자 GPU 화면은 확인하지 않음 |
| Windows Python 3.14 실행·Ollama | 실제 앱 전체 실행과 모델 추론은 수행하지 않음 |

실행 방법은 기존 START_WINDOWS.bat입니다. 이전 서버를 종료하고 별도 폴더에 압축을 풀어 실행한 뒤 Ctrl+F5로 새로고침하세요.

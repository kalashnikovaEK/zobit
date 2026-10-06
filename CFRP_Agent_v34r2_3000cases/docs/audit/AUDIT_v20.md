# v20 표시 계층 변경 검증
<!-- [NEW v20] -->

추가: viz3d_live_v20.js, tests/viz3d_live_v20.cjs 및 본 검증 기록.
기존 수정: interactive.html의 독립 호출/로더 항목 추가, integrated_api_v14.py의 asset 허용 추가, README.md 끝에 v20 섹션 추가.
물리·AI·Guard·기존 단면 코드는 ZIP 원본과 바이트 일치 확인.

실제 기본조건 계산: Tmax=187.1113333354787, delta_Tmax=6.076797488155933, final_DoC=0.8903592416872913, cycle_time=298.96666666666664.

| 완료 | 증거 |
| --- | --- |
| 수동/AI/후보선택/실측 공통 진입점 연결 | 기존 모든 renderCharts 호출 경로에 독립 렌더러 호출 추가; 실제 HTTP JS/HTML 200 확인 |
| 실제 결과 셀 대응, 최고온도 프레임, 최대60 프레임 | 실제 기본조건 Physics JSON으로 Node 모의 DOM/Plotly 시험 통과 |
| 공통 비교시간·색범위·먼저 종료된 상태 유지 | 기준안을 더 긴 시간축으로 만들어 frame 비교 시험 통과 |
| 실측 null 및 SVG 보존 | 실제 실측 결과로 기존 SVG 시험 통과; 새 KPI null 모의시험 통과 |
| 무효화·지연 newPlot 취소·재생 종료·WebGL 실패 설명 | Node 비동기 지연/거절 시험 통과 |
| 기존 수동 응답 경합 방지 | stale_response_v17.cjs 통과 |
| 기존 Python 계약/Guard/HTTP/최적화/to_thread | Linux Python 3.12에서 12개 회귀시험 통과; tests_v20.log |
| HTML/JS 문법 | 두 inline script 및 새 JS Node 문법 확인 |

| 미완료 | 제한 |
| --- | --- |
| 실제 브라우저 화면/Plotly mesh3d 프레임 재생 | Chromium 다운로드가 비정상 ZIP으로 실패; 실제 WebGL은 검증하지 못함 |
| 실제 Windows CPython3.14 설치/사용자 GPU | Linux 3.12 호스트이므로 미검증 |
| 실제 Ollama 모델 추론 | Python 회귀의 자연어 추출은 모의, 물리 재실행/HTTP는 실제 |
| 외부 실험 정확도 | 여전히 미완료 |

앞선 cut offset 결함 주장 정정: z_part는 상면 기준, compVals는 금형 기준으로 reverse된다. nz-cell개를 금형부터 남기는 기존 로직은 올바르며 수정하지 않았다.
기존 결과 계약과 run_id_v14를 재사용하며 input_version을 서버에 새로 추가하지 않았다. 기존 runGeneration/입력 스냅샷/채팅 revision과 새 화면 revision으로 오래된 응답 및 프레임 혼입을 막는다.

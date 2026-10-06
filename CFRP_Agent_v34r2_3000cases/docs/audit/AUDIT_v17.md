# CFRP Agent v17 검토 결과
<!-- [NEW v17] -->

검토 기준: 첨부 CFRP_Agent_v16_Distribution(2).zip. 현재 실행 구조는 HTML → ThreadingHTTPServer → API → 물리 솔버/로컬 Ollama이다. 연구 코드 전체와 기존 OpenAI agent.py는 이 배포 ZIP에 없다.

## 결함 처리

| 결함 | 처리 | 실제 확인 |
| --- | --- | --- |
| review_results(None,None) 예외 | 반환부 계약 해시를 안전하게 읽고 blocked 반환 | None/비객체/누락 계약 5가지 시험 |
| run_ai(spec=...) 요청 검사 우회 | 직접 spec 경로에 grounding + review_request 추가 | 시간 분모 불일치, 지원하지 않는 재료, 근거 없는 숫자가 계산 전 차단 |
| 예상 밖 계산 None | 솔버 튜플, AI 물리·학습·예측·최적화 반환값, 표시 검증 진입에서 차단 | simulate, _solve_tool, web bridge None 주입 시험 |
| Numba import 프로세스 종료 | 별도 프로세스 import/JIT 검사, 실패 시 Python njit 대체 함수 | 종료코드 -11 주입시험과 가속 비활성화 상태의 실제 수동/실측 계산 |

실측 cycle_time=None은 종료 조건이 관측되지 않았다는 뜻이다. 숫자 0으로 바꾸지 않으며 JSON null로 전달한다. 요약 내부의 의도된 null과 전체 계산 함수의 None 반환을 구분한다.

## 통합개선항목

| 원 항목 | 현재 판정 | 근거와 제한 |
| --- | --- | --- |
| 수동 계산 중 입력 변경 → 옛 결과 표시 | 반영·실행 확인 | interactive.html runGenerationV14 + 요청 snapshot. 원본 run()에 지연 응답을 주고 입력을 바꾸어 latest가 null인지 확인 |
| 기존 OpenAI의 최종 숫자 검증 | 미연결 | finalize_legacy 함수는 있으나 호출부/agent.py가 없다. 해당 구형 경로가 통합되었다고 볼 수 없음. 현재 Ollama 답변은 Python 도구 결과로 구성 |
| 실측 입력 HTML 연결, cycle_time=null | 반영·서버 실행 확인 | workbench_v14.js → /api/measured → reconstruct. 실제 API null 직렬화 통과. 화면 코드 metric은 null을 —로 표시하지만 브라우저 실제 렌더는 미검증 |
| 2°C/hour를 2°C/min로 적용 | 반영·실행 확인 | quantities 분모 검사, 직접 spec에서도 needs_clarification. 지원하지 않는 분모를 자동 환산하지 않고 재입력 요구 |
| 금형·표면 배열/요약 검사 확대 | 반영·실행 확인, 아래 한계 있음 | 전체 표시 배열 형상/유한성, 좌표/격자, 경화도, 시간, 저장 이력의 최대값 하한, 계약/후보 일치 검사 |
| 옵션 오타·소수 셀수·음수 반응열 | 반영·실행 확인 | nominal 및 measured의 기존 v11 입력 검증 보존; 3가지 오류 입력 시험 |
| 공기보다 뜨거움 = 경화 발열 단정 | 설명 수정 반영 | temperature_view.js에서 냉각 지연도 가능하다고 명시. 반응 발열/열관성의 정량 분리 기능은 없음 |

요약값 검사는 저장된 배열보다 작은 최대값을 거부한다. 솔버 요약은 모든 내부 시간 단계의 최대값이며 화면 배열은 저장 시점만 담으므로 둘을 단순 등호로 비교하지 않는다. 임의로 크게 부풀린 요약을 모두 검출하는 완전한 재계산 검증은 아니다. 이 한계는 v17에서도 남는다.

Guard의 규칙 분기는 독립 if이며 AST 기준 elif 노드는 0개다. policy JSON은 별칭·정규식 설정이고, Guard 구현에는 반복문·예외 처리·보조 함수도 있다. 모든 Python 구문이 if문만으로 되어 있다는 의미는 아니다. 물리 솔버의 단계별 if/elif는 Guard 정책이 아니므로 변경하지 않았다.

## 동기 실행 격리

`async_runtime_v17.call_sync`는 asyncio.to_thread를 호출한다. 수동 API의 simulate_payload, 실측 reconstruct, 검토 기록 record_review, 모델 연결 ollama_health, 채팅의 run_ai_async에 실제 연결했다. 채팅 worker 안에서 requests.post, 설정 파일 읽기, 대리모델 학습, 물리 계산, 보고서 작성이 실행된다. 스트림 쓰기는 같은 요청 worker에서 순서대로 처리된다. 웹 서버 자체도 요청마다 ThreadingHTTPServer worker를 사용한다. 기존 동기 함수는 유지하며 직접 호출하면 동기적으로 실행된다. 이벤트루프에서 직접 run_ai를 호출하지 말고 run_ai_async를 사용해야 한다. to_thread는 이벤트루프 격리이며 CPU 계산의 병렬 속도 향상을 보장하지 않는다.

## Windows 단일 진입점

START_WINDOWS.bat → windows_launcher_v17.py → Python 3.12 전용 .venv_windows_v17 → 패키지 설치 → 런타임 검사 → interactive_server.py. 성공한 의존성 프로필을 기록하고 변경/검사 실패 시 재설치한다. 실행 창을 유지해 오류 메시지를 확인할 수 있다. Linux/macOS .sh 파일 두 개는 사용자 요청에 따라 제외했다. 기존 Windows 배치 및 기존 README 이력은 보존했다.

이것은 Python 기반 Windows 전용 배포다. Python 설치가 필요 없는 EXE나 오프라인 패키지가 아니다. Numba 검사 실패 시 같은 식을 Python으로 계산하므로 처리 시간이 늘어날 수 있다. 격리 검사는 import와 간단한 JIT를 검사하며 가능한 모든 네이티브 오류를 없애는 것은 아니다.

## 검증 결과

- 새 Python 3.12.14 venv에서 requirements-html-v15.txt 실제 설치 및 런타임 검사 통과. Numba 0.68.0 / llvmlite 0.50.0 import 정상. 사용자 보고의 비정상 종료는 이번 환경에서 재현되지 않음.
- clean venv에서 12개 회귀/통합 시험 통과: 물리 계산, 실측 API, 학습·최적화·결과 Guard, HTTP 정적 자산/채팅 스트림, 비정상 반환, async heartbeat, Windows 실행 순서 모의검사.
- 실제 Ollama 대신 JSON 추출을 주입했다. 이후 계산·학습·최적화·HTTP는 실제 실행했다.
- Python fallback에서 수동 및 실측 계산 통과. 실측 cycle_time null 유지.
- 원본 JS run()의 지연 응답 폐기 시험 통과. 실제 Chromium/WebGL 시험은 실행 파일이 없어 수행 불가.
- 소스 해시 변경 후 기존 256개 입력을 재계산. 수치 타깃 최대 차이 3.495870259939693e-12. 해시를 숫자 검증 없이 바꾸어 붙이지 않았음.
- 실제 Windows 설치/브라우저 자동 열기/이중클릭은 미검증. 네이티브 충돌의 OS/CPU/보안 프로그램별 원인은 확정하지 못함.

로그: artifacts/tests_clean_v17.log, artifacts/fallback_v17.log, artifacts/stale_response_v17.log, artifacts/recompute_v17.log. 실패한 브라우저 시도는 artifacts/ui_v17.log에 보존했다. 과거 artifacts/ui_smoke_result_v14.json과 SPLIT_VERIFICATION_v16.md는 이력이며 v17 검증을 대체하지 않는다.

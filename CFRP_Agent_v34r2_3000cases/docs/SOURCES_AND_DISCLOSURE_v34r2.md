# CFRP Agent v34r2 제출용 출처·AI 활용·데이터·기존자산 정리
<!-- [NEW v34r2] 제출 체크리스트 12~14 대응 문서. 기능/물리식/모델은 변경하지 않음. -->

## 1. 제출본 식별

- 실행본: `CFRP_Agent_v34r2_3000cases`
- 대상 환경: Windows, 표준 64비트 CPython 3.14
- 기본 진입점: `START_WINDOWS.bat`
- 로컬 서비스: `http://127.0.0.1:8765/`
- 기본 로컬 LLM 설정: Ollama + `gemma2`
- 선택 프로필: `gemma2`, `qwen3:8b`, `qwen3:4b`, `qwen3:1.7b`
- 외부 실험 검증 상태: `external_validation_passed=false`

## 2. 논문·기술자료 출처

| 구분 | 출처 | 프로젝트에서의 사용 | 주의사항 |
|---|---|---|---|
| 주 물성/반응 모델 | Van Ee, D. & Poursartip, A. (2009), *HexPly 8552 Material Properties Database for use with COMPRO CCA and Raven* (NCAMP/NIAR) | NCAMP Model 15 경화 kinetics, Tg 관계, 반응열, 밀도, Vf의 기준 | 인증용 COMPRO 구현을 주장하지 않음 |
| 열전달·경계/검증 참고 | Li et al. (2020), *Cure-induced temperature gradient in laminated composite plate: Numerical simulation and experimental measurement*, Composite Structures 253, 112822, DOI: 10.1016/j.compstruct.2020.112822 | AS4/8552 열물성 함수, Invar 10 mm 형상, 상부 대류, 접촉 열전달 비교조건, 온도 측정 비교 구조 | 현재 솔버는 Li의 2D 모델을 그대로 재현한 것이 아니라 1D hybrid demonstration model |
| 경화주기 자료 | Hexcel, *HexPly 8552 Product Data Sheet* | 2단 경화주기 범위, 냉각 및 release temperature 참고 | 제조사 자료의 조건을 보편 공정값으로 일반화하지 않음 |
| Invar 물성 | Composites Knowledge Network, KPC/P129 | Invar 대표 rho=8000 kg/m3, cp=515 J/kg/K, k=11 W/m/K | Li 2020 논문 본문에 없는 금형 물성 보완용 전형값 |
| 최적화 방법 참고 | Zhang, Y., Feng, G. & Liu, B. (2023), *Sensitivity Analysis and Multi-Objective Optimization Strategy of the Curing Profile for Autoclave Processed Thick Composite Laminates*, Polymers 15(11), 2437, DOI: 10.3390/polym15112437 | surrogate/민감도/다목적 최적화의 선행연구 근거 | 해당 논문의 RBF/NSGA-II를 우리 구현과 동일하다고 주장하지 않음 |
| 한국어 이론 참고 | 유재우·김위대 (2023), *화학 반응열을 고려한 탄소 섬유 복합재 온도와 경화도 예측*, Composites Research 36(5), 315-320 | 열-경화 결합 이론 설명 참고 | 재료계가 AS4/3501-6이므로 8552 계수 출처로 사용하지 않음 |
| 확장 선행연구 참고 | Hegde, Zarouchas & Caglar (2026), *Accelerating curing simulations of composites using Graph Neural Networks* | surrogate 기반 cure simulation acceleration 선행연구 참고 | RTM6 기반으로 현재 AS4/8552 물성에 직접 혼합하지 않음 |

활성 계산계의 직접 출처/가정은 `app/config/material.json`에 기록되어 있다. 수식·단위·문헌 역할은 별도 팀 공유 이론자료와 일치하도록 관리한다.

## 3. Ollama / LLM 사용 신고

| 항목 | 사용 내용 | 제출 시 표기 |
|---|---|---|
| Ollama | 로컬 LLM 런타임. 기본 주소 `127.0.0.1:11434` | 외부 API Key 없이 로컬 실행. Ollama 자체는 별도 설치 |
| Gemma 2 | 기본 프로필 `gemma2` | 자연어 요청 해석/구조화에 사용. 모델 가중치는 ZIP에 포함하지 않음. Gemma Terms 적용 |
| Qwen3 | 선택 프로필 8B/4B/1.7B | 대체 로컬 모델 선택지. 모델 가중치는 ZIP에 포함하지 않음. 해당 배포 라이선스/모델 카드 조건 준수 |
| LLM 역할 | 사용자 자연어 목표를 공정 변수·목표·제약으로 구조화 | 물리 결과 수치를 LLM이 임의 생성하지 않음 |
| 승인 절차 | 해석 Preview → 사용자 승인 → 계산 | 승인 전 모델 로드/물리 계산 차단, 승인 후 재해석 없이 동일 구조화 요청으로 실행 |

중요: 이 제출본의 저장 surrogate는 물리 합성데이터로 학습된 Random Forest이며 **LLM fine-tuning 결과가 아니다**. v34/v34r1 검증 기록의 실제 Ollama 호출은 일부 미검증 또는 모의 추출임을 그대로 공개한다.

## 4. Python / JavaScript 의존성

현재 Windows Python 3.14 설치 기준은 `app/requirements-windows-py314-v18.txt`이다.

| 패키지 | 버전 | 역할 | 라이선스/출처 메모 |
|---|---:|---|---|
| NumPy | 2.3.5 | 배열·수치 계산, 모델 배열 저장 | BSD 계열 / PyPI 및 공식 프로젝트 |
| SciPy | 1.17.0 | 수치계산 보조 | BSD 계열 / PyPI 및 공식 프로젝트 |
| pandas | 2.3.3 | CSV·표 데이터 처리 | BSD 3-Clause 계열 / PyPI 및 공식 프로젝트 |
| scikit-learn | 1.8.0 | Random Forest 대리모델 학습/평가 | BSD 3-Clause 계열 / PyPI 및 공식 프로젝트 |
| Numba | 0.68.0 | 물리 계산 가속 선택 경로 | BSD 계열 / PyPI 및 공식 프로젝트 |
| llvmlite | 0.50.0 | Numba LLVM 계층 | BSD 계열 / PyPI 및 공식 프로젝트 |
| Plotly | 7.1.0 | 브라우저 그래프·3D 시각화 (`plotly.min.js`를 설치 패키지에서 제공) | MIT 계열 / PyPI 및 Plotly 프로젝트 |
| requests | 2.34.2 | Ollama HTTP 통신 | Apache-2.0 / PyPI 및 Requests 프로젝트 |

라이선스 표기는 제출 편의를 위한 요약이다. 실제 제출 시 각 패키지의 배포 메타데이터/LICENSE를 최종 기준으로 한다. 소스코드를 이 ZIP에 vendoring한 것이 아니라 `pip`로 설치한다.

## 5. 합성데이터와 AI 대리모델 출처

- 데이터 파일: `app/artifacts/development_cases_3000_v24r1.csv`
- 생성 방식: 문헌 기반 1D 열-경화 Physics Solver에 공정조건을 입력하여 계산한 **개발용 synthetic manufacturing data**
- 총 규모: 3,000건, 750개 공정 그룹
- 기존 700건 + 추가 Physics 계산 2,300건
- 학습/평가 분리: 2,248건 학습 / 752건 그룹 홀드아웃
- 별도 평가: 학습에 쓰지 않은 25개 공정 그룹 × 4개 두께 = 100건
- 대리모델: CPU Random Forest
- 배포 저장모델: `app/artifacts/trained_surrogate_v24r1/`
- 별도 100건에서 3,000건 모델 최고 내부온도 MAE 약 1.0613°C, 최대 절대오차 약 7.0768°C
- 위 오차는 **물리모델을 정답으로 둔 surrogate 근사오차**이며 실제 실험/현실 오차가 아니다.
- 최종 추천 후보는 surrogate만으로 확정하지 않고 Physics Solver로 다시 계산한다.
- 외부 실험 검증 완료를 주장하지 않는다.

상세 생성·학습 기록은 `docs/training/TRAINING_v24r1.md`, 원시 체크포인트 및 평가표는 `app/artifacts/` 아래에 보존되어 있다.

## 6. 기존자산 / 대회 기간 신규개발분

### Existing Assets / 기존자산

- CFRP/AS4-8552 선행문헌 조사 및 이론·공식 정리
- 문헌 기반 경화 kinetics·열전달·경계조건 검토자료
- 기존 Physics Solver 및 초기 계산/시각화 자산
- 초기 UI/HTML/JS 시각화 구성
- 기존 합성데이터/대리모델의 초기 버전과 검증 기록

### Newly Developed / 대회 기간 신규개발·개선

- 자연어 목표/제약 해석 및 Request Guard 강화
- v34 해석 Preview → 사용자 승인 → 실행 흐름
- 3,000건 synthetic dataset으로 확장한 surrogate 저장모델 연결
- Surrogate 기반 후보 탐색 → Physics 재검증 → Result Guard 흐름
- Evaluator/Feedback 및 실패·OOD/잘못된 입력 차단
- 실행 로그·검토/승인 UI 통합
- 단일 시각화 Studio 및 v34r2 3D 중복 표시 수정
- 대표 자연어/회귀/HTTP/UI 테스트 및 증거 로그

기존자산과 신규개발분의 세부 버전 이력은 README와 `docs/audit/`, `docs/training/`을 따른다.

## 7. 보안·개인정보 최종 확인

제출본에 대해 다음 항목을 정적 검사했다.

- `.env`, 개인키, 인증서, credential/secret 파일: 발견되지 않음
- OpenAI/GitHub/Google/Slack 계열의 전형적 API Key 패턴: 발견되지 않음
- Ollama 연결: localhost 주소만 사용하며 API Key 없음
- 비밀번호가 포함된 URL: 차단 로직만 존재하고 실제 비밀번호 값 없음
- `confirmation_token`: 로컬 실행 중 생성되는 10분/1회용 승인 토큰이며 외부 서비스 credential이 아님
- 이메일/전화번호: 제출 소스/로그에서 사용자 개인정보로 확인되는 값 없음
- 로컬 Windows 사용자 경로: 과거 테스트 로그 2건에서 발견하여 `<REDACTED_USER_PATH>`로 비식별화
- 합성데이터: 개인/기업 생산데이터가 아니라 자체 Physics 계산값
- 기업비밀/KAI 실제 생산조건: 포함하지 않음. 실제 KAI 공정 재현을 주장하지 않음

이 검사는 정적 문자열/파일명 기준이며, 제출 직전 최종 ZIP을 다시 검사하는 것을 권장한다.

## 8. 제출 문구 권장안

> 본 작품은 공개 문헌에 기반한 CFRP 경화 Physics Solver로 자체 synthetic manufacturing data를 생성하고, 이를 학습한 Random Forest surrogate와 최적화/물리 재검증 도구를 로컬 LLM 기반 Agent가 호출하는 연구용 MVP입니다. 실제 기업 생산데이터나 개인정보는 사용하지 않았으며, 외부 실험 검증 및 항공 인증 수준의 정확도를 주장하지 않습니다. 사용한 논문·기술자료·Python 오픈소스·Ollama/LLM 및 기존자산/신규개발분은 별도 출처표에 공개합니다.

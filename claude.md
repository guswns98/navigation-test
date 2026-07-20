# TMAP QA Automation Portfolio — 프로젝트 계획서

티맵모빌리티 QA Automation Engineer 포지션 지원용 포트폴리오.
실제 티맵 앱을 대상으로 GPS 모킹 기반 가상 주행 시나리오를 자동 검증하고,
API Mocking 도구와 비기능 측정까지 확장하는 자동화 테스트 플랫폼.

## 공고 요구사항 매핑

| 공고 요건 | 이 프로젝트에서 커버하는 방식 |
|---|---|
| 자동화 테스트 플랫폼 구축/운영/개선 | GPX 생성 → 주입 → 검증 → 리포트 전체 파이프라인 |
| UI/API 자동화 (Python) | Appium + pytest 시나리오, 라우팅 API 활용 |
| CI/CD (GitHub, Jenkins 등) | GitHub Actions에서 에뮬레이터 기동 후 전체 실행 |
| 테스트 자동화 도구 (Appium 등) | Appium(UiAutomator2) 기반 |
| API Mocking 도구 개발 | mitmproxy 애드온 기반 선언적 모킹 프록시 (트랙 B) |
| 비기능 테스트 | adb 기반 기동 시간/메모리/프레임 측정 (3단계, 선택) |

## 아키텍처

```
[GPX Generator]          [GPX Player]              [Verifier]
라우팅 API(OSRM 등)  →   보간된 좌표를 1초 간격   →  Appium이 티맵 UI에서
경로 생성 + 보간         으로 에뮬레이터에 주입       안내 문구/거리/재탐색 검증
+ 시나리오 변주              (geo fix /                    ↓
(이탈, 속도, 정차)         set_location)             [Allure Report]
                                                         ↑
[Mock Proxy (트랙 B)]  ── 데모 클라이언트 대상 장애 주입 검증 ──┘
```

- 핵심 원칙: 앱이 아니라 **OS를 속인다**. 에뮬레이터의 GPS는 소프트웨어이므로
  `geo fix`로 주입한 좌표가 곧 하드웨어 GPS 수신값 (mock 플래그 없음).
- 실단말은 확장 트랙: mock location 허용 여부 검증 + 비기능 실측용.
- 실제 티맵 API는 건드리지 않음 (SSL 피닝 가정). API Mocking은 통제 가능한
  데모 클라이언트 + 오픈 라우팅 API 대상으로 구현 (트랙 B).

## 기술 스택

- Python 3.11+, pytest, Appium-Python-Client, Allure
- Android SDK / Emulator (Play Store 이미지, API 30+), adb
- OSRM 공개 API (경로 생성), gpxpy (GPX 파싱/생성)
- mitmproxy (모킹 프록시, 2단계)
- GitHub Actions (reactivecircus/android-emulator-runner)

## 저장소 구조 (목표)

```
tmap-qa-automation/
├── README.md
├── gpx_generator/          # 경로 생성 + 보간 + 시나리오 변주
│   ├── generator.py        # OSRM 호출 → 좌표열 → GPX
│   ├── interpolate.py      # 속도 기반 1초 간격 보간
│   └── mutations.py        # 경로 이탈/정차/과속 변주
├── gpx_player/
│   └── player.py           # GPX → 에뮬레이터 좌표 주입 루프
│                           # (백엔드 추상화: adb geo fix / appium set_location)
├── tests/
│   ├── conftest.py         # Appium driver, player fixture
│   ├── pages/              # Page Object (지도 화면, 안내 화면)
│   └── scenarios/          # 시나리오 테스트 3~5개
├── mock_proxy/             # 2단계: mitmproxy 애드온
│   ├── proxy.py
│   ├── rules.yaml          # 선언적 장애 주입 규칙
│   └── tests/
├── perf/                   # 3단계(선택): 비기능 수집
└── .github/workflows/ci.yml
```

## 1단계 — 가상 주행 자동화 (필수, ~1주)

### 1-1. 환경 구축
- [ ] Android Studio + Play Store 이미지 AVD 생성 (API 30+)
- [ ] 스토어에서 티맵 설치, 최초 실행 및 번호 인증 통과
- [ ] 인증 완료 상태에서 **AVD 스냅샷 저장** (CI 재사용 대비)
- [ ] 스모크 테스트: `adb emu geo fix <lng> <lat>` 로 티맵 지도가 따라오는지 확인
  - 주의: geo fix 인자 순서는 **경도 위도** 순

### 1-2. GPX Generator
- [ ] OSRM API로 출발지→도착지 경로 좌표열 획득
- [ ] 목표 속도 기반 보간: 두 좌표 사이를 1초 간격 점으로 분할
      (예: 60km/h → 약 16.7m 간격)
- [ ] GPX 파일 출력 (gpxpy)
- [ ] 시나리오 변주 기능:
  - 정상 주행
  - 경로 이탈 (중간 좌표를 옆길로 오프셋) → 재탐색 유도
  - 정차 (동일 좌표 반복)
- [ ] CLI 인터페이스: `python -m gpx_generator --from ... --to ... --speed 60 --mutation detour`

### 1-3. GPX Player
- [ ] GPX 파싱 → 1초 간격으로 좌표 주입 루프
- [ ] 주입 백엔드 추상화 (전략 패턴):
  - `AdbBackend`: `adb emu geo fix` (에뮬레이터)
  - `AppiumBackend`: `driver.set_location()` (실기기 확장 대비)
- [ ] 재생 속도 배율 옵션 (테스트 시간 단축용)

### 1-4. Appium 시나리오 (pytest)
- [ ] conftest: Appium 세션 + player를 백그라운드 스레드로 구동하는 fixture
- [ ] Page Object: 지도 메인 화면 / 경로 안내 화면
- [ ] 시나리오 (3~5개):
  1. 목적지 설정 → 안내 시작 → 안내 화면 진입 확인
  2. 정상 주행 중 잔여 거리/도착 예정 시간 갱신 확인
  3. 경로 이탈 → 재탐색 발생 (안내 문구/경로 변경) 확인
  4. 정차 시 안내 상태 유지 확인
  5. 안내 종료 → 메인 복귀 확인
- [ ] Allure 리포트 연동, 실패 시 스크린샷 첨부

### 1-5. CI 파이프라인
- [ ] GitHub Actions: android-emulator-runner로 에뮬레이터 기동
- [ ] 티맵 로그인 상태 재사용 전략 구현 (스냅샷/데이터 복원)
  - 안 되면: CI에서는 앱 설치+주입+지도 스모크만 돌리고,
    전체 시나리오는 로컬 실행 → 리포트만 커밋하는 절충안. README에 사유 명시
- [ ] Allure 리포트를 GitHub Pages 또는 아티팩트로 배포

### 1단계 완료 기준
- 로컬에서 시나리오 3개 이상 안정적으로 통과 (3회 연속 그린)
- 경로 이탈 → 재탐색 검증이 포함될 것 (핵심 시나리오)
- Allure 리포트에서 시나리오별 스텝/스크린샷 확인 가능

## 2단계 — API Mocking 도구 (필수, ~1주)

- [ ] 데모 클라이언트: OSRM API를 호출하는 초간단 웹/웹뷰 클라이언트
- [ ] mitmproxy 애드온 개발:
  - rules.yaml 로 규칙 선언: 대상 엔드포인트, 응답 코드 강제(500 등),
    지연 주입(N초), 응답 바디 변조
  - 규칙 핫리로드 (파일 변경 감지)
- [ ] pytest 검증 케이스 4~5개:
  - 500 응답 시 클라이언트 에러 처리 확인
  - 3초 지연 시 타임아웃/로딩 처리 확인
  - 빈 경로 응답 등 비정상 데이터 처리 확인
- [ ] README에 도구 사용법 문서화 (설치, 규칙 작성법, 실행)

### 2단계 완료 기준
- 코드 수정 없이 rules.yaml 만으로 장애 시나리오 전환 가능
- "도구"로서 독립 실행 가능 + 문서 존재

## 3단계 — 비기능 측정 (선택)

- [ ] 시나리오 실행 중 수집: 콜드 스타트 시간(am start -W),
      메모리(dumpsys meminfo), 프레임 통계(dumpsys gfxinfo)
- [ ] 결과를 Allure 리포트에 첨부
- [ ] (여유 시) 실단말에서 동일 측정하여 에뮬레이터 수치와 비교
- [ ] (여유 시) k6로 mock proxy 대상 부하 테스트

## 산출물

1. GitHub 저장소 (위 구조, README에 아키텍처 다이어그램 포함)
2. 요약 PDF: 아키텍처 1장 + 시나리오/결과 + 공고 요건 매핑표
3. (보너스) 실단말 mock location 허용 여부 검증 결과 — 성공/차단 어느 쪽이든 README에 분석 기록

## 제약 및 주의사항

- 실제 티맵 서버 API를 가로채거나 변조하지 않는다 (트랙 분리 원칙)
- 루팅, SSL 피닝 우회 등 회색지대 작업 금지
- 티맵 첫 실행 인증은 실제 휴대폰 번호로 1회 수행, 이후 스냅샷 재사용
- 티맵 UI 요소 셀렉터는 버전 업데이트에 취약 → Page Object에 격리하고
  accessibility id 우선 사용
- 목표 일정: 1~2단계 2주 내 완성. 3단계는 서류 제출을 막지 않음
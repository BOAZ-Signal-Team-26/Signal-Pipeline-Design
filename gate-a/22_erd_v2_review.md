# 22. ERD v2 6관점 검토 — 2026-09-23

> 검토 대상은 v2(20표·FK 45개) 시점의 작업 트리다. 검토 뒤 A 조치를 반영한 현재 구조(v2.1, 20표·FK 47개)는 [DBML](schema.dbml)·[21](21_schema_catalog.md)·[20 v2.1 절](20_erd_redesign.md)이 정본이다. 아래 줄 번호는 반영 전 기준이므로 현재 파일과 어긋날 수 있다.

검토 대상: gate-a/schema.dbml (v2), [20_erd_redesign.md](20_erd_redesign.md), [21_schema_catalog.md](21_schema_catalog.md).
검토자: architect, data-engineer, data-scientist, platform-engineer, cloud-architect, backend-developer (AI 에이전트 6개, 파일 수정 없음). 표 판정은 앞의 5개 관점, backend는 API·서빙 관점만 담당.
줄 번호는 리뷰 시점 작업 트리 기준.

**본 검토는 팀 승인된 최종 결정이 아닙니다.** [19](19_pending_decisions_review.md)와 동일한 톤으로 미결 항목과 진행 상태를 기록합니다.

---

## 한줄 결론

진단은 맞고 처방이 과했다. 기존 score의 `section_id`·`raw_score` NOT NULL 결함(19 R1/R3) 수정은 필요했다. 20개 표는 규모상 문제 없다(run당 약 8M행, 5–10GB 추정). 새 표 6개 중 3개(metric_definition, analysis_target, analysis_target_member 축소)는 유지, 3개(score_dependency, evaluation_run, evaluation_response)는 미승인 산식·프로토콜을 표로 선반영한 것이라 보류 대상이다.

표가 늘어난 근거는 정당(문서/쌍 대상, 숫자 없는 결과, 복수 평가자)하나, 같은 날 나온 19가 "물리 표 수는 아직 정하지 않는다"(19:37), "승인 전 예약 표를 빈 정의로 DBML에 추가하지 않는다"(19:87), "표 수는 그다음"(19:116)이라 적었고 20이 이를 건너뛰었다. 표 개수보다 큰 비용은 **run_id 하나가 수집·추출·채점을 묶는 복합 FK 사슬**과 **DBML 밖 조건부 규칙 약 40개**다. 6관점에서 가장 많이 겹친 결함은 `pipeline_run` 한 표(실행 종류 분리·상류 참조·공식 run 마커)로 모인다. 표 제외 여부는 09-30 팀 결정이 필요하다.

---

## 새 표 6개 합의 판정

| 표 | 판정 | 5인 중 동의 | 이유 |
|---|---|---|---|
| metric_definition | 유지(얇게) | 5/5 | score_type enum 2값 고정 대체. 칼럼 최소화 |
| analysis_target | 유지 | 4/5 (architect는 score 병합 제안) | 절/문서/쌍/펀드 대상 실제 요구. FUND 대표문서 선택 기준 미문서화 |
| analysis_target_member | 축소 유지 | 4/5 | SECTION까지 PRIMARY member 강제 → target.section_id와 중복. PAIR 역할은 프로토콜 확정 후 |
| score_dependency | 보류 | 5/5 | 집계 공식·가중치 DRAFT(20:59). 18:174 ADR 뒤집는데 대체 ADR 없음 |
| evaluation_run | 보류/별도 영역 | 5/5 | 프로토콜 미정(19:33). 파일 manifest로 충분 |
| evaluation_response | 보류/별도 영역 | 5/5 | 사람 실험 원응답을 수집 DB에 섞음. 접근제한 메커니즘 없음 |

---

## 발견 사항

### CRITICAL (즉시 반영 필수)

| 항목 | 내용 | 지적 관점 | 근거 |
|---|---|---|---|
| C1 run_id 복합 FK 사슬 | score→target→member→file_extraction/section + "산식 변경은 새 run"(20:38) → 가중치만 바꿔도 추출·절 재적재. evaluation_run도 같은 패턴(565) | architect, platform, cloud | 20:38, dbml:488·603·606, 02:80 |
| C2 population_snapshot UNIQUE 충돌 | (run_id, population_key)에 metric_key 필요. 같은 층 두 지표면 충돌 | architect, backend | dbml:479, 20:59 |
| C3 pipeline_run 마커 부재 | "공식/최신 run" 포인터 없음. run_kind(EXTRACT/SCORE) / upstream_run_id / 공식 마커 필요. analysis_target·member는 extraction_run_id로 추출 계층 참조 | architect, platform, data-engineer, backend | 20:38, dbml:223-224 |

### HIGH (해결 선행 조건)

| 항목 | 내용 | 지적 관점 | 근거 |
|---|---|---|---|
| H1 게이트C 계약 선점 | payload v2(20:53), target_key(20:37), 구조 manifest(20:63-65), protocol(20:69) 미정 상태에서 스키마 선정 | architect, platform | 00:38, 20:30-39 |
| H2 물리 구현 지정 | 20:30 "CHECK/트리거로 구현" → DB 선택 전 선정(DuckDB 트리거 없음, SQLite FK 기본 OFF, BigQuery PK/FK 미강제) | platform, cloud | 20:30-39 |
| H3 15_api_spec.md 오해석 | 대시보드 API가 아니라 수집 API 명세(15:6 "어떻게 호출해서 받아오는가"). 서빙 계층 계약 없음 | backend | 15:1, 15:6 |
| H4 DRAFT 지표 오염 | definition_status='APPROVED' 강제 지점 없음. 모든 조회가 조인을 기억해야 함. 승인 점수 뷰(score_current)로 단일화 필요 | data-scientist, backend | dbml:512, 20:38, 04 2절 |
| H5 경로+sha 7쌍 산재 | artifact 표 + fsck 필요. 현재 DBML 밖 명세로 산재(dbml:412-413, 444-447, 475-476, 567-572, 367-369) | platform, cloud | 20:26·65, 02:79-83 |
| H6 02:79-83 경로 표 미갱신 | structure/protocol/response/summary manifest 경로 추가. gate-b/README.md:4 참조 갱신 필요 | platform | 02:79-83, 20 관련 섹션 |

### MEDIUM (09-30 검토)

| 항목 | 내용 | 지적 관점 | 근거 |
|---|---|---|---|
| M1 | population_snapshot.metric_definition text 칼럼이 동명 표와 이름 충돌·내용 중복 | architect, platform, cloud | dbml:464 |
| M2 | varchar 상태 칼럼 14개 vs enum 13개 혼재. 로더 오타가 조용히 통과 | architect, platform, cloud | dbml:308, 448, 511-512, 539, 566, 589-594 |
| M3 | score.target_type 칼럼 없음 → 20:38 "target_type 일치" 규칙이 3표 조인 트리거 | architect, platform | 20:38 |
| M4 | definition_status 가변인데 승인 이력 저장 자리 없음. DRAFT 개발 출력 저장 위치 미정의 | architect, platform | 20:38, dbml:512 |
| M5 | DOCUMENT_PAIR purpose(summary_body/comparison)가 selection_manifest JSON 안 → 역할 개수 CHECK 불가 | platform | 20:34, dbml:528 |
| M6 | 평가 표가 채점 run에 복합 FK. 완료 run 불변(dbml:409)이라 미채점 문서 평가 시 모순. run 보존 정책 필요 | architect, cloud | dbml:609-610 |
| M7 | derived 경로에 DB 서러게이트 ID(run_id, raw_object_id, population_snapshot_id) 포함 → PK 재발급 시 경로 무효. manifest 내용 주소화 권고 | cloud | 02:80-82 |
| M8 | target_key가 run별 서러게이트 section_id를 해시에 포함 → run 간 동일 대상 탐지 불가. "idempotency"는 같은 run 재시도 한정. 정규 JSON 규칙을 RFC 8785로 고정 필요 | data-engineer, cloud | 20:37, dbml:524 |
| M9 | metric_definition.direction(higher=harder)이 JSON 안 → 축 합산 부호 오류를 SQL에서 못 잡음(04 2절이 이미 경고). evaluation_response에 grader_key 없어 채점자 간 일치도가 JSON 파싱 의존 | data-scientist | dbml:513, 597 |
| M10 | 인라인 JSON text 약 13개 vs 파일 경로+sha 8쌍. 어느 쪽인지 기준 없음(20:26 "큰 불변 자료는 파일" vs selection_manifest 인라인) | platform, cloud | dbml:410, 513, 528, 311, 597 |
| M11 | result_status(5)×normalization_status(3) 조합을 API가 `score: number|null`로 누르면 0/계산불가/해당없음 구분 불가. 응답 envelope에 status·reason 필수 | backend | 20:46-51 |
| M12 | score_payload의 member_id/block_id는 내부 식별자. API pass-through 시 내부 구조 노출·암묵 계약 | backend | dbml:311, 20:53 |
| M13 | 사람 실험 원응답이 공개 원본과 같은 RAW_ROOT·DB. "접근 제한" 문구만 있고 메커니즘 없음. PII 잔여: raw_response 자유 텍스트, response_payload 채점자 실명 가능, 가명↔실명 대응표 위치 미정 | cloud | 20:73, dbml:567-572, 593 |

### LOW

- L1 nullable 복합 FK(dbml:489·603·606) MATCH SIMPLE 전제 명시 필요 (architect)
- L2 evaluation_run.status vs pipeline_run.status 열거값 불일치 (data-scientist, architect)
- L3 timestamp 시간대 미명시. 02는 UTC 전제 → "UTC" 명시 (cloud)
- L4 population_snapshot.baseline_date 잔존. 20:24 "기준일은 run으로"와 어긋남 (architect)
- L5 FK 대상이 없는 UNIQUE: member (member_id, run_id), population (id, run_id) (platform, architect)
- L6 match_failure.target_type(product/distributor)이 target_type_enum과 이름 같고 의미 다름 (platform)
- L7 판매사 필터가 product_distributor / document.distributor_id 두 경로 OR. 날짜 필터 기준 칼럼 미정 (backend)
- L8 population 멤버십(파일)과 target 멤버십(관계형) 비대칭 근거를 21에 한 줄 (data-engineer)

---

## pipeline_run 관련 교차 이슈

6관점에서 pipeline_run에 대한 지적이 가장 많이 겹침:
- run 종류 분리(EXTRACT vs SCORE): architect, platform, data-engineer, backend
- 상류 run 참조(upstream_run_id): architect, platform, cloud
- 공식 run 마커(is_official/is_current): architect, backend

이 3건은 같은 근본 문제(run_id 하나가 수집·추출·채점을 묶는 복합 FK 사슬)로 귀결.

---

## 조치 분류

### A. 명백한 결함 — 09-23 즉시 반영 (사용자 승인, 팀 결정 불필요·되돌릴 수 있는 논리안)

| 항목 | 조치 | 반영 상태 (v2.1) | 근거 |
|---|---|---|---|
| A1 | population_snapshot UNIQUE (run_id, population_key) → (run_id, metric_key, population_key). (population_snapshot_id, run_id) UNIQUE 삭제. 동명 표와 중복이던 metric_definition text 칼럼 삭제 | 반영 완료 — [schema.dbml](schema.dbml) population_snapshot, [21](21_schema_catalog.md) | C2, M1 |
| A2 | pipeline_run에 run_kind(EXTRACT/SCORE) / upstream_run_id(자기 참조) / is_official / published_at 추가, status → run_status_enum, UNIQUE (run_id, upstream_run_id). analysis_target.extraction_run_id를 (run_id, extraction_run_id) → pipeline_run(run_id, upstream_run_id) 복합 FK로 강제. analysis_target_member는 run_id를 없애고 (target_id, extraction_run_id)로 참조. section/file_extraction FK는 extraction_run_id로(FK 45→47) | 반영 완료 — schema.dbml pipeline_run·analysis_target·analysis_target_member, [20 v2.1 절](20_erd_redesign.md), [01 6절](01_logical_schema.md). architect 재검증 M-1·M-2·M-3·M-4·M-5·L-1 반영 | C1, C3 |
| A3 | varchar 코드 칼럼 15개 → enum 16개(run_status_enum은 pipeline_run·evaluation_run 공유). score_dependency.input_role은 B1 보류 표라 varchar 유지. 기존 소문자 값 3개 enum은 소문자 유지 | 반영 완료 — schema.dbml enum 블록, 21 Enum 상태값 | M2, L2, L6 |
| A4 | metric_definition.direction(HIGHER_IS_HARDER/HIGHER_IS_BETTER/NONE) 칼럼 승격 | 반영 완료 — schema.dbml metric_definition | M9 |
| A5 | 20 무결성 계약 도입부 "물리 DB CHECK/트리거로 구현" → "검증 규칙 목록, 구현 방식은 Gate B(DB 중립 적재 검증 기본)" | 반영 완료 — 20 | H2 |
| A6 | 02 경로 표에 structure/protocol/response/summary manifest 경로 추가, derived/는 EXTRACT run 아래. gate-b/README.md:4 참조를 20/21/22로 | 반영 완료 — [02 6절](02_raw_storage_policy.md), [gate-b/README](../gate-b/README.md) | H6 |
| A7 | 공개 식별자 규칙(document_id/product_id/fund_key 공개; section_id·run_id·metric_key는 run 파라미터 동반 — section_id는 EXTRACT run마다 재발급되는 서러게이트라 단독 공개 불가; target_*/member_id/block_id/score_id 내부 전용) | 반영 완료 — 21 말미. architect 재검증 HIGH-1(section_id 분류 오류) 수정 반영 | M8, M12 |

A 반영으로 해소: C1, C2, C3, H2, H6, M1, M2, M9(direction 부분), L2, L6. 미해소로 B에 남김: 나머지.

### B. 팀 결정 후 반영 — 09-30 안건

**B 항목은 09-30 회의(또는 그 이후 회의)의 결정에 따라서만 반영한다.** 아래 「권고」는 검토 의견이며 결정이 아니다. 결정 전에는 「결정 전 임시 상태」를 유지하고, DBML·문서를 권고 방향으로 미리 바꾸지 않는다(19:87, 20 v2.1 절과 같은 원칙). 결정이 나면 이 표의 「결정」 열에 회의 날짜·결론을 적고, 반영은 별도 작업으로 WORK_LOG에 기록한다. 결정이 권고와 다르면 권고가 아니라 결정을 따른다.

20·21·02는 아래 번호를 참조한다.

| 항목 | 결정 요청 | 선택지 | 권고 (검토 의견) | 결정 전 임시 상태 | 결정 (회의 날짜·결론) |
|---|---|---|---|---|---|
| B1 | score_dependency / evaluation_run / evaluation_response 3표를 DBML에서 빼고 예약 계약(20 문서)으로만 남길지 | 포함 유지 vs 예약 계약만 | 예약 계약만. 산식·프로토콜 승인 뒤 별도 PR로 추가 (5/5 동의) | DBML에 포함 유지 | 미결 |
| B2 | analysis_target_member의 SECTION PRIMARY member 의무 해제 | 의무 유지 vs 뷰 파생 | 뷰 파생. target.section_id와 이중 기록 제거 | 의무 유지 | 미결 |
| B3 | artifact 레지스트리 표 신설(kind, rel_path, sha256, byte_size, access_class, created_run_id) + 야간 fsck | 단일 표 vs 현재 경로+sha 7쌍 산재 | 단일 표. 표 +1이지만 칼럼 14 → FK 7로 순감 (4/5 동의) | 경로+sha 쌍 유지 | 미결 |
| B4 | 평가 표·자료의 접근 분리 | 같은 DB/RAW_ROOT vs eval 스키마 + restricted/ 버킷(또는 prefix IAM) + 보존 기한 | eval 스키마·role 분리, 별도 버킷. 인스턴스 분리는 불필요 | 같은 DB·RAW_ROOT | 미결 |
| B5 | 대시보드 서빙 API 계약 문서 신설(엔드포인트·필터·응답 envelope) 및 승인 점수 뷰(score_current: is_official ∧ APPROVED) | Gate A 범위 vs Gate B 첫 항목 | Gate B 첫 항목. 스키마 확정 전 드릴다운·랭킹 쿼리 2개를 실제로 짜 보고 read model 필요 여부 확인 | 없음. 모든 조회가 두 조건을 직접 걸어야 함 | 미결 |
| B6 | evaluation_response에 grader_key, source_response_id(재채점 원본 self-FK) 추가 | 칼럼 vs JSON 내부 | 칼럼 추가. B1 결정에 종속 | JSON 내부 | 미결 |
| B7 | manifest 저장 기준 통일(인라인 JSON vs 파일 경로+sha) 및 target_key·definition_sha256 정규 JSON을 RFC 8785로 고정 | 기준 선택 | 큰 불변 자료는 파일, SQL 필터 대상은 칼럼. RFC 8785 명시 | 혼재 | 미결 |
| B8 | metric_definition 승인 상태 이력과 DRAFT 개발 출력 저장 위치 | 이력 표 vs manifest 내 이력 vs 새 metric_key | 승인 상태 변경은 이력 표 또는 manifest 기록. DRAFT 출력은 공식 score와 분리 저장 | 가변 단일 칼럼 | 미결 |
| B9 | derived 경로의 서러게이트 ID 제거·manifest 내용 주소화(manifests/sha256/{ab}/{hash}.json) | 현행 유지 vs 내용 주소화 | 내용 주소화. Gate B PK 발급 방식과 함께 결정 | 현행 | 미결 |
| B10 | score.target_type 칼럼 추가 및 (metric_key, target_type) 복합 FK로 20:38 규칙 강제; DOCUMENT_PAIR purpose 칼럼 승격 | 칼럼 vs 적재 검증 | 칼럼 추가. B1·B2와 함께 검토 | 적재 검증 | 미결 |

---

## 관점별 요약

### 1. architect
- 진단은 맞으나 처방이 과함. score에 칼럼 몇 개(target_type, 앵커 3개, target_key, metric_key, assessor_key, result_status, reason_code, numerator/denominator)를 더하면 풀릴 문제를 표 6개로 풀었다.
- 대안 15표: 기존 14 + metric_definition(축소). 입력·근거는 score_payload에, 평가는 파일 manifest로. 잃는 것은 구간·입력 계보의 FK 강제, DAG SQL 조회, 평가 응답 SQL 조회이며 요구가 증명되면 표로 승격(18:157 원칙).
- 유일하게 population_snapshot UNIQUE 충돌(C2)을 찾아냈다. 다수 의견(analysis_target 유지)과 갈린 유일한 관점.

### 2. data-engineer
- 적재 순서를 끝까지 추적: 순환 없음. population_snapshot↔score 단방향. score/score_dependency는 PENDING 선삽입 후 하위→상위 UPDATE라 append-only가 아님.
- 19:37과 20:15-26이 같은 날 모순(평가 표 수 미정 → 2표 확정)임을 지적.
- protocol_manifest 안의 pair_key/question_key는 SQL FK가 아니라 manifest 재생성 시 조용히 드리프트 가능(20:71 자인). 적재 검증 잡 명세 없음.
- nullable anchor 패턴은 표준 트레이드오프로 유지 권장. FUND 대표문서 선택 기준 미문서화.

### 3. data-scientist
- 지원되는 분석: 절→축→최종 가중 집계, min-30·미병합 층내 백분위, 비율 지표, 계산불가 5분기, mixed-effects용 평가 칼럼(4/12/18 하드코딩 없음, PII 없음).
- 못 하는 분석: 채점자 간 일치도(grader_key 없음), 재채점 전후 비교(JSON 참조뿐), DRAFT 오염 차단(문서 규약뿐), 방향 검증(direction이 JSON 안).
- "표가 너무 많다"의 실체는 analysis_target_member의 SECTION 강제 1곳과 score_dependency의 시점상 조기 설계 1곳.

### 4. platform-engineer
- DBML 밖 규칙 약 42개 집계: 단일 행 CHECK 14, 교차 행 트리거/검증기 16, 파일 내용 검증 10. 2~3명 파트타임 기준 3~5 인·주를 채점 행 1건 적재 전에 선행해야 함. 수집→파싱만이면 규칙 6개.
- 09-26 인계 골든패스: 수집→파싱→매칭 12표 + 로더 계약 6단계 + 검증기 6개(경로 정규화, EXTRACT_OK 조건부 필수, char 범위, 원본 불변, 시도·바이트 분리, 완료 시 input_manifest). 채점 5표는 "칼럼 확정, 조건부 규칙은 Gate B 백로그"로.
- 표 배치 권고: 지금 17, Gate C 예약 3(DBML 제외), 삭제 0.

### 5. cloud-architect
- run당 행 수 추정: score 약 3.6M, score_dependency 약 3.4M(AXIS 이상만 저장하면 0.1M), analysis_target 약 225k, member 약 250~300k. 전량 재실행 1회 약 8M행·5~10GB. Postgres/DuckDB에서 가벼움. SQLite는 단일 writer라 Airflow 병렬 적재에 비권고.
- 원본 저장은 금투협 수시공시 백필이 지배(연 약 250GB 추정, 미측정). 비용은 결정 요인 아님.
- Gate B 최소 아키텍처: PostgreSQL 1개(core/eval 스키마) + 객체 스토리지(raw/ Object Lock, derived/ lifecycle, manifests/ 내용 주소화, restricted/eval/) + artifact 표 + 게시 규약(임시 키 → sha 검증 → 최종 키 → DB 커밋) + 야간 fsck + run 보존 정책.

### 6. backend-developer
- 15_api_spec.md는 첫 줄부터 "데이터 소스 API 명세"이고 범위를 "어떻게 호출해서 받아오는가 하나"로 못박은 수집 문서. 00:10이 확정한 대시보드 드릴다운을 소비할 계약이 저장소에 없다.
- 드릴다운 쿼리(문서→절별 원점수·백분위·근거): 조인 5 + 복합키 3, 근거 스팬까지 렌더링하면 실질 조인 7 + JSON 파싱 2단 + structure_manifest 파일 I/O가 요청 경로에 들어감. 층내 최하위 Top-N: 조인 6, 층 조합마다 전수 스캔·정렬 → read model 없이는 문서 총량에 선형.
- 공식 run 포인터 부재(C3)와 target_key의 run-scoped 성격(공개 ID 불가)을 지적. score_current 뷰(공식 run ∧ APPROVED)와 응답 envelope `{result:{status,value,reason}, normalization:{status,percentile,reason,population:{key,member_count,minimum_required}}, evidence:[{quote,section_id,char_start,char_end}]}` 제안.

---

## 검증 결과

리뷰 주장 중 팀 리드가 반영 전 파일에서 직접 대조 확인한 항목:
- population_snapshot UNIQUE가 (run_id, population_key)이고 metric_key 미포함(dbml:479): 확인
- pipeline_run에 run_kind·공식 run 마커 없음, document.is_current(dbml:224)는 DART 정정본 계보 전용: 확인
- 15_api_spec.md가 수집 API 명세(15:1 "데이터 소스 API 명세", 15:6 "어떻게 호출해서 받아오는가 하나"): 확인
- 19:37 "물리 표 수는 아직 정하지 않는다", 19:87 "승인 전 예약 표를 빈 정의로 DBML에 추가하지 않는다", 19:116 "표 수는 그다음": 원문 확인
- gate-b/README.md:4가 01과 18을 우선 참조: 확인
- 02:79-83 경로 표에 text/inputs/populations만 있음: 확인
- evaluation_run이 scoring_run_id를 별도로 둠(dbml:565): 확인

A 반영 후 검증(v2.1):
- `@dbml/core` 파서 통과: 20개 표·47개 관계·enum 30개. 모든 FK 부모 칼럼의 PK/UNIQUE 존재. PostgreSQL SQL 메모리 내보내기 성공.
- 01 Mermaid 관계선 47개 = DBML 47개. `git diff --check` 통과.
- 상태성 varchar 잔여는 score_dependency.input_role(B1 보류 표) 하나.

architect 에이전트의 반영 검증(1차 반영 뒤, 파일 수정 없이 판정만):
- A1~A6 DBML 반영 정확. Mermaid 관계선 47개 직접 셈 일치. B 선점 없음(표 삭제·병합 없음, 평가 표는 enum 타입만 변경).
- HIGH-1: 21의 공개 식별자 표가 `section_id`를 "run 무관 안정 ID"로 분류한 것은 오류. 절은 EXTRACT run마다 재적재되어 section_id가 바뀜 → `(run_id, section_id)` 쌍으로 공개하도록 수정. **반영.**
- M-1: `analysis_target.extraction_run_id = upstream_run_id`를 적재 검증에만 맡김 → pipeline_run UNIQUE (run_id, upstream_run_id) + 복합 FK로 강제. **반영.**
- M-2: run 종류와 자식 표 일치 검증 목록 누락 → 20 v2.1 절에 추가. **반영.**
- M-3: is_official/published_at이 "완료 run 불변"과 충돌 → 예외 명시, published_at은 해제 시에도 유지, 기준일별 서빙은 B5로. **반영.**
- M-4: run 칼럼의 kind 주석 누락(section, file_extraction, collection_attempt, match_failure, fund_group) → 주석 추가. **반영.** 매칭 성공/실패의 run 비대칭은 기존 문제로 B에 남김.
- M-5: 기준일 규칙 불일치 → SCORE.baseline_date = upstream EXTRACT, population_snapshot.baseline_date = SCORE run으로 통일. **반영.** L4(칼럼 존치)는 그대로 미결.
- L-1: member.run_id가 FK 한 곳에만 쓰임 → 칼럼 삭제, (target_id, extraction_run_id)로 참조. **반영.**
- L-2 대소문자, L-3 normalization_reason 누락, 20:55·20:93·20:103·gate-b/README:16·02:77 잔여 문구: **반영.**
- 약한 B 선점 지적 3곳(run_status_enum 공유, eval manifest 경로 위치, is_official 전역 1개): 인지하고 B4·B5에 위임. 되돌리기 쉬운 수준.

architect 2차 재확인(2차 반영 뒤):
- HIGH-1, M-1~M-5, L-1~L-3 모두 DBML·20·01에 반영 확인. M-1 복합 FK는 nullable upstream_run_id와 충돌 없음(자식 두 칼럼이 NOT NULL이라 SCORE run만 매칭되고, 덤으로 analysis_target.run_id가 SCORE run임이 FK로 강제됨). L-1 뒤 member의 SCORE run 조회는 target 조인으로 충분.
- 새 지적 N-1(21의 run kind 주석 6곳·population.baseline_date 설명 누락), N-2(`(run_id, section_id)`의 run_id가 EXTRACT run임을 명시): **반영.**
- 판정: 스키마 구조 결함 없음. v2.1 A 조치 종결.

검증하지 않은 항목:
- 실제 DB 적용·마이그레이션, 조건부 적재 검증 구현, 실제 데이터 파일럿
- 행 수·용량·작업량 추정치(cloud·platform)의 정확성
- 외부 대화형 ERD 아티팩트·Notion 갱신

---

## 관련 문서

- [00_context_brief.md](00_context_brief.md)
- [01_logical_schema.md](01_logical_schema.md)
- [02_raw_storage_policy.md](02_raw_storage_policy.md)
- [04_score_storage_and_population.md](04_score_storage_and_population.md)
- [15_api_spec.md](15_api_spec.md)
- [18_schema_review.md](18_schema_review.md)
- [19_pending_decisions_review.md](19_pending_decisions_review.md)
- [20_erd_redesign.md](20_erd_redesign.md)
- [21_schema_catalog.md](21_schema_catalog.md)
- [schema.dbml](schema.dbml)
- [../gate-b/README.md](../gate-b/README.md)

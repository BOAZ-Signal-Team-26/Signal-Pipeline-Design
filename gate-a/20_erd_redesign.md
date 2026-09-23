# 20. ERD 재설계 v2 — 2026-09-23

## 검토 결론과 근거

19의 R1~R7은 타당하다. 기존 `score.section_id NOT NULL`, `raw_score NOT NULL`, `(run_id, section_id, score_type)` UNIQUE는 문서/쌍 지표, 숫자 없는 결과, 복수 평가자를 수용하지 못한다. 원응답·문서 최종값·구조 정보도 보존해야 한다. 다만 “두 영역이니 두 표 추가”, “나머지는 JSON이므로 관계 변경 없음”은 타당하지 않다.

근거는 [8차 미팅 09.23](https://app.notion.com/p/3e3e1ac7050581929ac1defef0e90b7e)(조회 편집시각 2026-09-23T09:35:04.418Z), [CDI 변수표 티켓](https://app.notion.com/p/3d6e1ac7050581568e30e53cb38f56a7), [기존 ERD](https://app.notion.com/p/3e0e1ac705058115b023e714be75b2c8), 로컬 01/04/18/19 및 Project-Management의 WBS다. 8차 회의록의 결론 칸은 비어 있고 세부 선택 체크도 남아 있다. 사람·LLM 병행, 고지 점수화, 층내 백분위 방향은 반영하되 의견란의 가중치·분모·임계값까지 승인된 산식으로 만들지 않는다. 오늘 회의록은 용어 빈도 7+0+7+3=17 정정 설명을 이미 포함하므로 19의 이전 관찰과 구분한다.

기존 티켓에는 과거 4인 동의가 체크되어 있다. 프로젝트 관리 문서의 미기록 표기와 다르다. 과거 체크는 보존하며 **v2의 별도 인수는 미완료**로 기록한다.

## 선택한 구조: 14개 → 20개

기존 수집·원본·추출·절·상품 계보는 유지하고 `score`의 대상을 일반화한다. 새 표 6개는 빈 예약 표가 아니라 칼럼·키·참조·검증 계약을 갖는다.

| 추가 표 | 한 행 | 필요한 이유 |
|---|---|---|
| metric_definition | 지표의 불변 버전 | ASL·축값·CDI·변환값의 계산 단위/산식/승인 상태를 구분 |
| analysis_target | 실행 안의 절/문서/쌍/펀드 대상 | 가짜 절 없이 최종 문서·펀드 점수를 저장 |
| analysis_target_member | 대상에 사용한 파일/구간과 역할 | 같은 PDF의 요약/본문, 별도 PDF, 여러 근거 구간을 표현 |
| score_dependency | 출력 점수와 입력 점수 사이 의존관계 | 절→축→최종값의 실제 계산 근거와 가중치를 조회 |
| evaluation_run | 사람 또는 LLM 평가 실행 | 채점 실행과 별개인 실험·재채점 버전 관리 |
| evaluation_response | 실행·쌍·응답자·대상·문항·조건·반복 | 원응답·누락·채점·제시순서를 보존 |

`score`는 `target_id + run_id + metric_key + assessor_key`가 유일하다. PK는 계속 `score_id`다. `section_id`, `score_type`, `section_weight`, `baseline_date`는 각각 대상/지표/의존관계/실행으로 옮긴다. `metric_key`별로 원자 지표·축값·최종값을 별도 행에 저장한다. `score_payload`는 관계형 키의 대체물이 아니라 지표별 항목 판정과 근거 상세다.

파일 manifest는 문항 묶음·설정·모집단 회원·페이지 구조처럼 실행 후 불변인 큰 자료에 사용한다. 실제 점수와 응답은 SQL 조회가 필요한 공통 필드를 관계형으로 둔다. 지표별 테이블을 따로 만드는 대안은 중복·집계 코드 증가, 모든 결과를 JSON 하나에 넣는 대안은 참조/입도 검증 약화 때문에 채택하지 않았다. 운영 DB 제품·정밀도·성능 인덱스·물리 DDL은 후속 결정이다.

## 대상·근거의 무결성 계약

DBML의 PK/UNIQUE/FK는 구조를 강제한다. 아래 조건부 필수·교차 행 검사는 **검증 규칙 목록**이며, 적재 검증기·DB CHECK·트리거 중 무엇으로 구현할지는 Gate B에서 DB 제품과 함께 결정한다(00:70 논리 범위, [22](22_erd_v2_review.md) A5). DuckDB·SQLite·BigQuery는 트리거나 FK 강제가 없거나 제한적이므로 DB 중립 적재 검증을 기본으로 둔다. **DBML 파싱 통과가 이 규칙의 구현 완료는 아니다.**

1. SECTION은 section_id만, DOCUMENT는 document_id만, FUND는 fund_key만 앵커로 갖는다. DOCUMENT_PAIR는 세 앵커가 모두 NULL이며 멤버 양쪽이 대상이다. SECTION/DOCUMENT/FUND에서 다른 앵커는 NULL이다.
2. SECTION은 PRIMARY 1개가 같은 section_id·파일·실행·정확한 char 범위를 가리킨다. DOCUMENT는 PRIMARY 1개 이상의 파일이 모두 그 document_id 소속이다. FUND는 대표 문서/파일 PRIMARY를 1개 선택하고 선택 기준·상품/펀드 연결 당시 스냅숏을 selection_manifest와 실행 입력 manifest에 고정한다. 기준본 충돌이면 대상을 공식 통계에 넣지 않는다.
3. DOCUMENT_PAIR는 목적이 summary_body면 SUMMARY/BODY가 각각 1개, comparison이면 LEFT/RIGHT가 각각 1개다. 방향을 보존하며 두 쪽이 같은 파일·같은 구간인 쌍은 거절한다. 같은 파일의 서로 다른 구간과 별도 파일을 모두 허용한다. 상품/시점 적합성은 선택 정책으로 검증한다.
4. EVIDENCE는 모든 유형에 여러 행 가능하다. 다른 문서의 근거도 허용하되 source provenance를 유지한다. 멤버의 (파일, 실행)은 추출 FK, 선택 section은 (절, 파일, 실행) 복합 FK로 제한한다.
5. char_start/end는 모두 NULL(파일 전체) 또는 둘 다 있으며 `0 <= start < end <= text_length`다. section_id가 있으면 절의 정확한 범위와 일치한다. 성공 계산은 필요 텍스트/구조의 가용성을 검사한다. 파일 전체 참조만으로 추출 성공을 가정하지 않는다.
6. target_key는 `{contract_version:2, target_type, anchor, members:[{role,seq,raw_object_id,section_id,char_start,char_end}], selection_policy_version}`의 정규 JSON SHA-256. members는 role/seq로 정렬, Unicode/숫자/NULL 직렬화를 고정한다. 대상은 점수 생성 전 동결하며 재시도에 새 키를 만들지 않는다.
7. score의 target_type은 metric_definition.target_type과 같아야 한다. 지표 정의 내용은 불변이며 승인 상태 변경 이력/근거는 보존한다. 의미·산식 변경은 새 metric_key, 새 SCORE run이다(추출 run은 upstream으로 재사용, v2.1). DRAFT를 평가하는 개발 출력은 공식 점수와 분리하고 공식 score에는 UNDETERMINED/UNAPPROVED_DEFINITION을 남긴다.
8. score_dependency는 같은 run의 입력만 허용하며 자기 참조와 순환을 거절한다. 입력 역할·단위·필수 개수·상태는 지표 계약으로 검증한다. 절 가중치는 출력 문서마다 달라질 수 있어 의존관계에 둔다.

## 점수·결측·모집단 계약

| result_status | raw_score | reason_code | 의미 |
|---|---|---|---|
| PENDING | NULL | 필수 | 계획됐으나 계산 전 |
| OK | 필수, 0도 유효 | NULL | 승인된 기준으로 계산 가능 |
| NOT_APPLICABLE | NULL | 필수 | 상품/서류/지표 적용 대상 아님 |
| UNDETERMINED | NULL | 필수 | 분모 0, 정의 미승인, 구조 부족, 판정 불가 |
| FAILED | NULL | 필수 | 실행 오류 |

계획한 target×metric×assessor 슬롯은 실행 입력 manifest와 PENDING 행으로 남긴다. 행 부재는 계획 외이며 실패로 집계하지 않는다. 완료 실행에 PENDING이 남으면 SUCCEEDED로 닫지 않는다. 비율 지표 OK이면 numerator/denominator와 양의 분모를 요구하며 산식·허용 범위를 검증한다. 모든 원자값이 단순 비율은 아니므로 분자/분모를 억지로 채우지 않는다.

고지 항목의 판정은 MET/UNMET/NOT_APPLICABLE/UNDETERMINED로 분리한다. payload v2는 `contract_version`, `unit`, `items[{item_key,status,reason,evidence[{member_id,block_id,char_start,char_end}]}]`, `applicable_count`, `assessed_count`, `coverage`, `preprocessing`을 갖는다. block_id와 텍스트 구간은 멤버 파일의 structure_manifest/canonical text에 존재해야 한다. 문서 전체 부재 판정은 검사한 파일·범위·완전성도 기록한다. 불명확한 법적 서류 대응과 후보 절을 확정하지 않는다. 분모·미평가 공개 정책이 없으면 공식 최종 숫자는 비운다.

정규화 상태는 원점수와 독립이다. NOT_REQUESTED는 normalized_score/population/reason 모두 NULL, OK는 원점수 OK 및 normalized_score/모집단 필수, UNAVAILABLE은 normalized_score NULL 및 사유 필수다. 원점수 불가이면 정규화 OK 금지. population FK는 같은 실행뿐 아니라 같은 metric_key도 강제한다. 대상 단위·평가자·층·범위가 population_snapshot.metric_key가 가리키는 metric_definition과 membership manifest에 맞는지는 적재 검증한다(v2.1: population의 중복 JSON 칼럼은 삭제).

오늘 회의록의 최종 층내 백분위는 **상품군×위험등급, 고유 fund_key 30개 이상, 층 병합 없음**을 현재 기준으로 기록한다. 30 미만은 원점수가 있어도 백분위를 비우며 판매사/연도/문서유형을 층에 추가하지 않는다. fund_document는 FUND 대상(대표 문서) 또는 펀드 연결이 검증된 DOCUMENT 대상에만 적용한다. fund_section은 DS가 동등 절을 정의한 뒤 SECTION에 적용한다. 쌍 지표는 임의로 문서 모집단에 넣지 않는다.

축간 변환과 최종 층내 백분위는 별도 단계다. 여러 기준집단이 필요한 경우 별도 metric_key/score 행을 만들고 score_dependency로 연결한다. 한 점수 행에 모집단 ID 여러 개를 숨기지 않는다. 기준집단 입력 원값·회원·동점 처리·변환 파라미터·평가자 선택 정책을 불변 manifest에 저장한다. 집계 공식과 축 가중치는 DS 승인 전 DRAFT다.

## 구조 정보와 자산

file_extraction은 structure_status와 structure_manifest_path/sha256을 추가한다. AVAILABLE/PARTIAL이면 경로·해시가 필수, UNAVAILABLE/NOT_REQUESTED이면 두 값은 NULL이다. PARTIAL은 어떤 페이지/블록이 누락됐는지 manifest에 기록한다. PDF는 1-based 물리 페이지, 좌표 원점/단위/회전, 블록 종류(table/text/heading 등), 글꼴/강조 정보, canonical text의 code point 범위와 block_id를 저장한다. 비PDF는 없는 페이지·좌표를 만들지 않는다. 표 여부를 모르면 text로 강제 분류하지 않는다.

구조 manifest는 `{contract_version,raw_object_id,run_id,canonical_text_sha256,coordinate_system,blocks,missing_regions}`이며 내용 해시를 검증한다. 모든 파일 참조는 공통 RAW_ROOT 상대경로다. 사전·감점표·프롬프트·입력·모집단·프로토콜도 경로와 sha256을 함께 기록하고 `..`, 절대경로, 해시 불일치를 거절한다. LLM 제공자의 동일 출력 재현을 보장한다는 뜻은 아니다.

## 사람·LLM 평가와 재채점

평가 실행은 scoring_run_id로 정확한 채점 버전을 참조한다. protocol_manifest는 `contract_version`, 문서쌍과 target_ids, 선정에 사용한 score_ids, 문항/정답/채점기준, 가명 참여자 또는 모델 키, 배정·순서·조건·반복, 실제 입력 파일/구간, 프롬프트와 설정, 분석계획, 계획 응답 슬롯을 고정한다. 문서 없이 묻는 조건도 어떤 문서의 정보와 비교하는지 target_id를 유지하되 입력 파일은 제공하지 않았음을 기록한다.

ANSWERED이면 raw_response 필수, 다른 상태는 NULL이다. GRADED이면 ANSWERED와 graded_value 필수, 다른 채점 상태는 graded_value NULL이다. 누락/중단/실패·채점불가는 reason_code 필수이며 반복·제시순서는 양수다. 계획 응답 슬롯과 행을 대조해 조용한 누락을 잡는다. 문서쌍·문항·응답자·target의 소속, 모델 조건 일치는 protocol 검증 대상이다. protocol 파일 안의 키는 SQL FK가 아니므로 해시만으로 이 소속이 보장되지는 않는다.

사람 이름/연락처는 이 스키마에 저장하지 않는다. 원응답 JSON/텍스트는 실험 자료로 접근을 제한한다. 실제 응답을 받기 전에 수집·보관 범위를 정한다. 제시순서/원응답/모델 설정을 남기며 총점·p값만으로 대체하지 않는다. 문항 수 4/12, 응답자 수 18 등을 스키마 제약으로 하드코딩하지 않는다.

재채점은 새 evaluation_run과 새 프로토콜(새 채점기준), 동일 불변 response_manifest 참조, 새 response 행으로 기록한다. response_payload에 원 evaluation_run_id/response_id와 원응답 해시를 남겨 새로 응답한 것으로 오인하지 않게 한다. 응답 다시 수집은 새 실험이며 원응답 참조를 재채점처럼 재사용하지 않는다. 완료 평가 실행은 원응답 manifest 필수, 분석 완료를 주장할 때는 summary_manifest 및 포함/제외 응답 목록도 필수다. SUCCEEDED는 계획 슬롯이 terminal 상태이고 채점 계획이 끝났음을 뜻하며 효과 검증 성공을 의미하지 않는다.

## 이전 설계에서 옮기는 방법

1. 기존 DB 적용 여부부터 확인한다. 이번 작업은 논리 스키마와 문서 변경이며 운영 DB 마이그레이션 실행이 아니다.
2. 기존 section마다 SECTION target/PRIMARY member를 만든다. 기존 score_type에 해당하는 승인된 metric 버전을 식별하고, 알 수 없는 산식은 추측하지 않고 격리한다.
3. 기존 score_id는 유지하고 target_id/metric_key/assessor_key를 채운다. 실제 숫자가 있는 행만 OK. 기존 weight는 사용한 문서별 산식이 확인될 때 dependency로 이관한다. 백분위는 모집단·단위가 검증된 경우만 이관한다.
4. 파일 구조를 재추출하지 않았다면 structure_status=NOT_REQUESTED다. 기존 데이터에 페이지/좌표를 가정해 채우지 않는다.
5. 입력·모집단·대상·지표 연결 검증 뒤 구형 score 칼럼 소비자를 v2로 바꾼다. 실제 데이터가 있으면 행 수/해시/점수 동등성 대조와 되돌리기용 백업을 선행한다.

## 09-23 v2.1 — 22 검토의 A 조치 반영

[22 ERD v2 6관점 검토](22_erd_v2_review.md)에서 팀 결정 없이 고칠 수 있는 명백한 결함(A)만 반영했다. 표 수는 20개 그대로이고 관계는 45→47개다. 표 제외·artifact 표·평가 스키마 분리·서빙 계약(B)은 09-30 결정 대기다.

| 조치 | 변경 | 근거 |
|---|---|---|
| A1 | `population_snapshot` UNIQUE를 `(run_id, metric_key, population_key)`로 수정. 동명 표와 중복이던 `metric_definition` text 칼럼 삭제 | 한 실행에서 같은 층을 여러 지표가 쓰면 기존 `(run_id, population_key)`가 즉시 충돌 |
| A2 | `pipeline_run.run_kind`(EXTRACT/SCORE), `upstream_run_id`(자기 참조), `is_official`, `published_at` 추가, UNIQUE `(run_id, upstream_run_id)`. `analysis_target`에 `extraction_run_id`를 두고 `(run_id, extraction_run_id) → pipeline_run.(run_id, upstream_run_id)` 복합 FK로 upstream과 같음을 강제. `analysis_target_member`는 `run_id`를 없애고 `(target_id, extraction_run_id)`로 대상을 참조. section/file_extraction FK는 extraction_run_id로 연결 | 기존에는 run_id 하나가 추출과 채점을 묶어 산식만 바꿔도 file_extraction·section을 전량 재적재해야 했다. "지금 대시보드가 보여줄 채점 실행"을 가리키는 포인터도 없었다 |
| A3 | varchar 코드 칼럼 15개(evaluation_run.status 포함)를 enum 16개로 통일(`run_status_enum`은 pipeline_run·evaluation_run 공유). 기존 값이 소문자였던 section_kind/match_target/observation_unit은 소문자 유지, 새 enum은 대문자 | 로더 오타가 조용히 통과하는 것을 막음. DB 제품별 구현(PG enum vs CHECK)은 Gate B |
| A4 | `metric_definition.direction`(HIGHER_IS_HARDER/HIGHER_IS_BETTER/NONE) 칼럼 승격 | 04 2절이 지적한 축 합산 부호 오류를 SQL에서 검사할 수 있게 함 |
| A5 | 위 「대상·근거의 무결성 계약」 도입부를 "검증 규칙 목록, 구현 방식은 Gate B"로 수정 | 00:70 논리 범위. DuckDB/SQLite/BigQuery는 트리거·FK 강제가 없거나 제한적 |
| A6 | [02](02_raw_storage_policy.md) 경로 표에 structure/protocol/response/summary manifest 경로 추가, `derived/`는 EXTRACT run 아래로. [gate-b/README](../gate-b/README.md) 참조를 20/21/22로 | v2가 추가한 경로 칼럼이 02에 없었고 gate-b가 낡은 18을 우선 참조했다 |
| A7 | [21](21_schema_catalog.md)에 공개 식별자 규칙 신설 | `target_key`는 run-scoped 해시라 공개 ID로 쓸 수 없다 |

A2에 따른 이 문서의 해석 변경: 위 본문에서 "새 run"은 산식·평가자·모집단 기준 변경이면 새 SCORE run, 파서·입력 변경이면 새 EXTRACT run + 새 SCORE run을 뜻한다. `score_dependency` 규칙 8의 "같은 run"은 같은 SCORE run이다. 무결성 계약 2·4의 멤버 (파일, 실행)은 (파일, extraction_run_id)로 읽는다. 적재 검증에 다음이 추가된다.

- run 종류: `score`, `population_snapshot`, `analysis_target.run_id`, `evaluation_run.scoring_run_id`는 SCORE run. `section`, `file_extraction`, `collection_attempt`, `match_failure`, `fund_group.created_run_id`, `analysis_target.extraction_run_id`는 EXTRACT run.
- upstream: SCORE run의 `upstream_run_id`는 NOT NULL이고 kind=EXTRACT, status=SUCCEEDED, `baseline_date`가 같아야 한다. EXTRACT run의 `upstream_run_id`는 NULL. `analysis_target.extraction_run_id = upstream_run_id`는 복합 FK가 강제한다.
- 기준일: `population_snapshot.baseline_date`는 SCORE run의 값과 같다. 기준일 변경은 새 EXTRACT + 새 SCORE다.
- 공식 run: `is_official=true`는 SUCCEEDED인 SCORE run에서만, 동시에 최대 1개. 완료 run 불변 원칙의 유일한 예외는 `is_official`/`published_at` 두 칼럼이다(서빙 포인터이며 결과가 아님). 기준일별 과거 스냅숏 서빙이 필요해지면 이 규칙은 22 B5(서빙 계약)에서 확장한다.
- 매칭 성공(`document_product`)은 run 무관, 매칭 실패(`match_failure`)는 run별이라는 기존 비대칭은 v2.1이 만든 것이 아니며 B 검토로 남긴다.

## 인수와 남은 결정

저장 구조는 v2로 구체화했다. DS가 승인할 지표별 단위·분모·산식·배점·축간 변환, 문서쌍 선정과 대표본, 평가 문항/프로토콜, 법적 서류 대응, 금투협 정정 계보, ELS 키, 물리 DB는 여전히 결정이 필요하다. 미확정 기준을 스키마 빈칸과 혼동하지 않는다. 후속 구현은 이 문서의 검증 규칙 목록을 Gate B가 정한 방식(적재 검증기 기본, DB 제약은 보강)으로 강제하고 실제 파일럿을 통과해야 한다.

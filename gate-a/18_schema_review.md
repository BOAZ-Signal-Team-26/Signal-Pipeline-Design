# 18. 스키마·ERD 재검토 기록 — 2026-09-22

## 판정과 범위

**큰 방향은 적절하지만 기존 9개 표를 그대로 적재 구현에 쓰기에는 키·입도·계보·결측 처리의 누락이 있다.** 상품 클래스와 공시 문서를 N:M으로 분리한 점, 원본 불변, 펀드 단위 통계, 마스킹된 분쟁조정을 상품에 강제로 붙이지 않는 점은 유지했다.

이번 변경은 Notion과 저장소를 대조한 **설계 수정안**이다. 생산 DB 변경·크롤러 실행·외부 API 재수집·Notion 편집은 수행하지 않았다. Notion의 완료 상태나 담당자 승인도 바꾸지 않았다. 09-30 칼럼/인계 승인, 10-07 저장 계층 선택, 10-14 최종 JSON 계약은 남아 있다.

원칙: 실측 결과와 팀 결정은 근거로 인용하되, 그 위에 이번에 선택한 칼럼·타입·제약은 **09-22 제안**으로 구분한다. 검토 과정에서 architecture 스킬의 요구사항 대조·대안 비교·결정 기록 방식을 적용했다.

## 1. 대조한 Notion 근거

| 근거 | 확인한 요구 / 상태 |
|---|---|
| [7차 미팅 09-20](https://app.notion.com/p/3e1e1ac70505814c8283ffa6c472d8d8) 안건 4 | 성공 상태값, 펀드 단위 통계, fund_key 고정, run_id 통일, 모집단 별도 표의 **팀 결정** |
| [데이터 테이블·ERD 산출물](https://app.notion.com/p/3e0e1ac705058115b023e714be75b2c8) | 9개 표와 아직 실제 칸으로 옮기지 않은 실행/모집단, 남은 6개 조사 |
| [Schema & Relation 티켓](https://app.notion.com/p/3d6e1ac7050581f3aa6cda6e22f7d119) | 논리 스키마·원본·실패 규칙의 인계 범위 |
| [Join 확인 티켓](https://app.notion.com/p/3d6e1ac705058146938bd512f410364b) | 소스별 코드·문자열·연결 불가 구분 |
| [Week 4](https://app.notion.com/p/3e1e1ac70505813984f1f64af2fe9090) | DART·포털·KRX 우선, 금투협·금감원은 Week 5, 09-30 인계 |
| [Flow·서버 환경 티켓](https://app.notion.com/p/3e1e1ac7050581f5b9e4c3331a1f17b1) | run_id 발급·모집단 생성 지점, DB는 10-07 이후 |
| [CDI 산출 단위](https://app.notion.com/p/3d6e1ac7050581d3a541d488e1b0f3ce) | 절 채점·펀드 통계 확정, 짧은 절 처리는 변수표로 이관 |
| [CDI 4축 변수 티켓](https://app.notion.com/p/3d6e1ac7050581568e30e53cb38f56a7) | 절/문서/문서쌍 계산 단위 구분 필요, 공식·일부 임계값 미정 |
| [CDI 참고문헌 검토](https://app.notion.com/p/3e1e1ac7050581b8b8cee9281c108348) | ASL에서 표 제외하지만 고지용 표 정보 보존, 요약-본문 비교, 높은 CDI=어려움 |
| [6필드 확정 티켓](https://app.notion.com/p/3e1e1ac7050581c4ae29c5f64334390c) | 유형·판매사·위험등급·수수료·원금손실·핵심 위험의 이름/타입/출처 절 미확정 |
| [판매사별 제재 라벨 티켓](https://app.notion.com/p/3e1e1ac7050581c6856fe90d677dad68) | 제재 API 8건으로 과거 전수 라벨 불가. 게시판 경로 검토 필요 |
| [데이터 소스 실측 문서](https://app.notion.com/p/3e0e1ac70505814387aecac5b73ef7cf) | 원천 응답과 접근 제약 |
| [09-20 티켓 대조 기록](https://app.notion.com/p/3e1e1ac7050580ecbef4e3cf0f9dd223) | asoStdCd 체계 및 DART status=014 관련 조사 |
| [초기 프로젝트 최종안](https://app.notion.com/p/3c1e1ac70505809c87b8db8a2b52065e) | 프로젝트 목적. 이후 변경된 소스/검증 방식의 최종 근거로 쓰지 않음 |

조회 당시 09-21 편집본과 본문에 09-22 실측이 적힌 자료를 함께 읽었다. 편집일만으로 권위를 정하지 않고, 회의 결정·실측·초기 제안의 차이를 반영했다.

## 2. 수정한 결함

| 우선순위 | 기존 문제 | 반영 |
|---|---|---|
| P0 | emOpenNo가 8/8 공백인데 문서 자연키로 지정 | 소스 이름공간 + 검사/순번/구분 후보 복합키, 원천 키 payload·충돌 격리 |
| P0 | ERD의 short_code UK가 실측 중복과 충돌 | UK 제거. 후보 코드 매칭 후 전체 코드/운용사 확인 |
| P0 | 절 → 문서만 연결돼 어느 첨부/바이트인지 모름 | 절 → 파일·실행 복합 FK, 파일 → 문서 일치 FK |
| P0 | run_id·모집단은 채택됐지만 주석에만 존재 | pipeline_run·population_snapshot과 실제 FK |
| P0 | 같은 원본의 파서 재실행이 파일 상태를 덮어씀 | file_extraction의 (raw_object_id, run_id) PK |
| P0 | 타임아웃에도 raw_object의 해시/경로 필수 | collection_attempt로 바이트 없는 실패 표현, raw는 실제 파일 |
| P0 | 문서 FK가 없는 포털/KRX/목록 응답을 저장할 수 없음 | raw_object.document_id nullable + source/object key |
| P1 | fund_key가 매번 계산되는 파생키로 남음 | fund_group 고정 키와 상품 FK, 모자·호수 보존 |
| P1 | 포털에 운용사가 없는데 manager_id 필수 | 연결 전 NULL 허용. 임의 운용사 생성 금지 |
| P1 | 판매사코드가 없어서 확인된 코드 조인을 구현 못 함 | kofia_sales_code, 판매관계 API 원본 FK·observed_date |
| P1 | 미확정 정정 계보를 NOT NULL로 강제 | is_correction/lineage_id NULL 허용 |
| P1 | 일반 비ETF/판정 보류의 boolean·enum 조합 불완전 | NOT_ETF 추가, 보류의 is_etf/category는 NULL |
| P1 | 부마다 반복되는 절 번호, 전체 텍스트 위치 소실 | 전역 순번 + 원문 부·절 + canonical text의 시작/끝 |
| P1 | 500자 미만=추출 실패가 정상 짧은 절을 제거 | 추출 성패와 SHORT_TEXT/계산 적합성 분리 |
| P1 | 날짜 미상=판매 중, 설정일=판매시작일 | inception_date 분리, 확인/후보/미상 구분 |
| P1 | 해시 동일=정정 아님 / 문서=펀드라는 과도한 가정 | 파일 중복·공시 정정·대표본 선택을 구분 |
| P1 | n/평균/분위수만 보존하면 과거 백분위 재현 불가 | 입력·모집단 구성원 manifest와 해시 |
| P1 | XML/PDF 두 파일의 meta.json 이름 충돌 | 모든 소스에서 파일 식별자·역할·버전 포함 |
| P1 | 응답 0건을 일괄 실패 처리 | 정상 EMPTY, 요청 검증 실패, API 오류·한도 구분 |
| P1 | 수집 파라미터 전체 저장이 API 키를 남김 | 비밀값 제거 JSON, credential_ref만 |
| P1 | 제재 사건일과 공시 입력일 보관 칸 부재 | action_date와 source_input_at 분리 |
| P1 | 법인 후보를 상품 실패 FK에 넣을 수 없음 | target_type와 법인 후보 FK, 해결 상태 |

P0는 적재/재현을 직접 막는 결함, P1은 잘못된 연결·모집단·품질 판정으로 이어지는 결함이다. 이번 판정은 실제 운영 장애 이력이라는 뜻은 아니다.

## 3. 저장된 표본을 다시 집계한 결과

새 API 호출이 아니라 저장소 CSV를 읽어 확인했다.

| 표본 | 재집계 | 의미 |
|---|---|---|
| fss_sanctions_sample.csv | 8행, emOpenNo 공백 8행 | 기존 자연키 사용 불가 |
| 같은 표본 | (examMgmtNo, emOpenSeq, transCode, actGbn) 8종 | **후보키**로 사용 가능성. 8건 유일성이 전체·미래 유일성을 증명하지 않음 |
| 같은 표본 | actOrganCon의 '-' 1, actOfficerCon의 '-' 1, actEmpCon의 '-' 3 | 기존 16의 7/8·7/8·5/8은 '-' 개수와 반대로 적혔다. 원천 문자열 보존 |
| dart_sections_sample.csv | 9문서, 294행, 찾음 O 292 / X 2 | 절 위치 검증 표본이지 전체 본문 추출 성공률이 아님 |
| 같은 표본 | (문서, 절번호) 126종 / (문서, 부, 절번호) 294종 | 절 번호 반복을 설계에서 반드시 구분 |
| kofia_sales_companies.csv | 200행, saleCompCd 200종, 전부 6자리 | 운용사 3자리 코드와 분리된 판매사 코드 필요 |

DART CSV는 제목·시작행·찾음 여부만 있으므로 **실제 절 길이 분포/500자 미만 비율을 이 CSV에서 계산할 수 없다.** 금투협 코드 중복률·ETF 매칭률 등 전건 수치는 12~17의 기존 실측을 인용하며 새로 전수 수집했다고 주장하지 않는다.

## 4. 원천 → 타입 → 저장 위치

| 소스/필드 | 실제 형태 | 논리 타입·처리 | 목적지 |
|---|---|---|---|
| DART rcept_no/corp_code | 숫자로 보이는 코드 | 문자열, 선행 0 보존 | document / distributor |
| DART 공개 표지 | HTML, 명칭·위험등급·코드 | 원본 HTML + 구조 추출 | raw_object(cover_html), product 근거 |
| DART document.xml | ZIP 응답; 내용 확인 미완료 | ZIP 원본. 오류 XML과 매직바이트 구분 | raw_object, collection_attempt |
| DART 본문 | PDF 안에 요약 및 제1~5부 | 바이트 → canonical text → 실제 구간 | raw_object → file_extraction → section |
| 포털 response.body.items.item | 객체 또는 배열 | 항상 레코드 배열로 정규화 | API 원본 + product |
| 포털 srtnCd | 5자리 영숫자 | varchar(5), 비유일 | product.short_code |
| 포털 asoStdCd | 12자리, KR5/KRM 등 | varchar(12), 체계별 보존 | product.standard_code |
| 포털 fndNm | 정식 이름 | 원문 text와 매칭용 이름 분리 | product |
| 포털 setpDt | YYYYMMDD, 11111111 더미 | 엄격한 달력 검증, 실패 시 NULL+사유 | inception_date |
| 포털 basDt | YYYYMMDD | date. 수집 시각/설정일과 분리 | source_baseline_date |
| fndTp/prdClsfCd | 코드성 문자열 | 원문 코드 유지. enum 의미 추측 금지 | fund_type/product_class_code |
| KRX OutBlock_1 | 일별 레코드 배열 | 기준일마다 원본 스냅숏 | raw_object(document_id=NULL) |
| KRX ISU_CD / ISU_NM | 코드 / 상장 약명 | 문자열, 포털과 이름 매칭 근거 필요 | product.isu_cd / 실행 입력 |
| KRX 가격·NAV·수익률 | 수치 필드; 형식 전체 실측 미완료 | 입력 구분자/단위/결측 토큰을 확인한 뒤 decimal. 공백·'-'를 0으로 바꾸지 않음 | 현재 mart 칸을 임의 신설하지 않고 원본 보존 |
| 금투협 공시 | XML 행, standardCd의 K55/KR5/KRM 혼재 | 코드 접두별 분기, 수시공시 4필드 묶음 | document + document_product |
| 금투협 첨부 | 서버명·원본명·경로 + PDF 여러 개 | 역할과 파일 식별자를 별도로 관리 | raw_object |
| 금투협 saleCompCd | 예 A02008 | varchar(6), 현재 마스터 유일키 | distributor.kofia_sales_code |
| 금투협 tmpV17/tmpV18 | 펀드 표준코드 / 운용사코드 | 코드 체계 대조 후 연결 | product_distributor / 법인 |
| 금투협 standardDt / tmpV30 | YYYYMM / YYYYMMDD | 월과 일 분리 | snapshot_month / observed_date |
| 금감원 JSON | 루트 키가 reponse, EUC-KR 응답 | 인코딩 확인 후 decode, 원바이트 보존 | raw_object + collection_attempt |
| 금감원 resultCode | '1', '900', '030', '033' | 문자열, HTTP 상태와 별도 | source_result_code |
| 금감원 actReqDate | 2026.9.17. | 엄격 파싱 후 date, 원문 보존 | document.action_date |
| 금감원 inputDate | 2026-09-17 13:30:31.0 | timestamp, 시간대 해석 명시 | document.source_input_at |
| 금감원 제재 내용 | text, '-', '해당사항 없음', 깨진 escape | 원문 보존 + 정규화 결과에 상태/사유. 금액/조치 종류를 한 숫자로 압축하지 않음 | source_record_payload |
| 분쟁 HWP | hwp5/hwp3/배포용, 마스킹 | 포맷별 성공/부분/미지원, 사람·상품 추측 연결 금지 | 원본·추출·미연결 문서 |
| LLM 6필드 | 아직 최종 이름/형태 미확정 | 문자열·숫자·목록과 값 상태, 근거 구간을 정의해야 함 | Gate C 계약. score_payload로 대체하지 않음 |
| CDI 지표 | 절/문서/문서쌍 혼재 | 계산 단위·분모·원값·결측 사유를 함께 정의 | 절 점수는 score, 나머지는 DS 계약 후 결정 |

원천 raw는 원래 바이트를 그대로 보존한다. 저장소 CSV는 이미 디코딩된 표본이므로 원본 응답의 바이트 인코딩을 이 CSV만으로 재확인한 것은 아니다. 저장용 JSON/텍스트는 UTF-8과 LF를 사용하고, 요청/파싱 타임스탬프는 UTC로 직렬화한다. 원천이 시간대를 주지 않는 inputDate 등은 source_timezone을 실행 설정에 명시한 뒤 변환하고 원문을 유지한다.

### 결측·자료형 공통 규칙

- 코드: 문자열. 선행 0·혼합 영숫자 보존. 빈 문자열/공백은 정규 칼럼에서 NULL, raw에서는 보존.
- 금액·비율: decimal 계열. 단위(원/백만원, 비율/%) 없이 숫자만 넘기지 않는다. precision/scale은 실제 범위와 DS 계약으로 결정.
- 논리값: true/false/NULL(미확인). 확인 실패를 false로 바꾸지 않는다.
- 조치 내용의 '-'와 '해당사항 없음': 해당 필드에서 조치 없음으로 해석할 근거가 있을 때 NOT_APPLICABLE. MISSING·PARSE_FAILED·MASKED와 구분. 회사 전체의 「제재 이력 없음」을 뜻하지 않는다.
- 원금손실 고지를 찾지 못한 경우: 추출 성공 후 미발견과 추출 자체 실패를 구분한다. 후자를 「고지 없음」으로 계산하면 안 된다.
- 자유 텍스트/목록/중첩 수수료 구조: 임의 단일 문자열·실수로 평탄화하지 않는다. Gate C에서 값과 단위, 적용 클래스, 근거 section/offset을 정의한다.
- 소스 text의 'n'을 전부 개행으로 치환하지 않는다. 표본 특이 escape 복원 규칙은 버전 관리하며 정상 영어 단어를 훼손하지 않아야 한다.

## 5. 재현성과 무결성 계약

DBML의 PK/FK/UNIQUE 외에 다음 조건을 적재 검증에 구현해야 한다. DB 제품 선택 전이므로 특정 DB의 CHECK/트리거 문법은 여기서 확정하지 않는다.

1. **식별자**: source와 키 payload가 공백이 아니어야 한다. 해시 직렬화는 UTF-8 정규 JSON 배열, 필드 순서 고정. 같은 키의 상이한 레코드는 검수 없이 덮어쓰지 않는다.
2. **매칭**: 코드 후보가 2개 이상이면 자동 확정 금지. match_score/top1_similarity는 [0,1]. target_type에 맞는 후보 FK만 채운다. 해결 상태에는 resolved_at/근거 필요.
3. **분류**: 01의 ETF 상태 조합, 위험등급 [1,6], 올바른 YYYYMM, 실제 달력일, 시작일<=종료일(둘 다 있는 경우)을 검증한다.
4. **원본**: version_seq>=1, SHA-256은 소문자 64자리 hex. 실제 저장된 바이트와 해시 일치. 동일 역할의 여러 파일은 source_object_key로 구분한다.
5. **수집**: source_result_code와 outcome 일치. 타임아웃은 HTTP 상태/raw FK NULL 허용. 정상 0건은 EMPTY. 한 실행의 request_key에는 source/endpoint가 포함된다.
6. **추출**: raw.collect_status가 success인 입력만 본문 추출. EXTRACT_OK이면 canonical_text 경로/해시/길이 필수. canonical text가 없는 상태에서 가짜 절 생성 금지.
7. **절**: 성공 구간은 0<=char_start<char_end<=text_length. section_text는 실제 구간과 동일. 번호는 파일/실행 전역에서 유일, 원문 부/절 번호는 별도. 형제 구간의 불필요한 중복 적재 금지.
8. **점수**: EXTRACT_OK이며 DS의 계산 가능 조건을 충족한 절만 채점한다. baseline_date는 run.baseline_date와 같아야 한다. 다른 실행의 절/모집단 연결은 복합 FK로 거부한다.
9. **정규화**: normalized_score가 있으면 population FK 필수. 절 점수의 모집단은 fund_section이며 같은 의미의 절/산식이어야 한다. 표본 하한 미달·분류 미확정·분모 0은 NULL+사유. 실제 백분위 범위와 방향은 산식 계약에 고정.
10. **모집단**: member_count는 포함 manifest의 distinct fund_key와 같아야 한다. risk_grade 미상/NAME_ONLY/PENDING은 정의된 제외 사유로 기록한다. 배정 불가능한 상품은 가짜 위험등급 층을 만들지 않고 실행 전체 제외 목록에 둔다.
11. **시점**: 대표본은 기준일에 이용 가능한 문서여야 한다. source_input_at/received_date와 관측 컷오프를 적용한다. 현재 product/risk_grade/is_current를 읽어 과거 스냅숏을 재구성하지 않는다.
12. **완료 실행**: config와 input manifest 및 해시가 모두 고정된 뒤 SUCCEEDED. 완료 행·manifest를 덮어쓰지 않는다. 새 입력/산식은 새 run_id.
13. **판매관계**: source_raw_object_id는 실제 판매사별 펀드 응답이어야 한다. observed_date의 월은 snapshot_month와 일치한다. 대표일/완전성 정책 없이 서로 다른 일자를 한 월의 합집합으로 적재하지 않는다.

### Manifest 최소 내용 (09-22 제안)

입력 manifest는 실제 사용한 raw_object_id/sha256, 상품 product_id/fund_key와 그 시점의 분류·위험등급·판매일·공모 여부·근거 raw ID, document_product 매칭 근거, 판매관계 원천과 조회 기준일을 담는다. 현재 마스터 갱신과 무관하게 과거 입력을 복원해야 한다.

모집단 manifest는 각 포함/제외 관측치에 다음을 보존한다.

| 항목 | 목적 |
|---|---|
| run_id, baseline_date, fund_key | 실행·시점·통계 단위 |
| product_ids | 그때 연결된 클래스 목록 |
| document_id, raw_object_id, raw_sha256 | 대표본의 정확한 바이트 버전 |
| section_ids / section 의미 | 집계에 사용한 절 목록. 문서/절 비교 구분 |
| raw_value, score_ids, metric_definition | 실제 분포를 만든 값과 계산 근거 |
| product_category, risk_grade, 기타 선택된 층화 값 | 그때의 층 배정 |
| inclusion_status, exclusion_reason | 대상 선정/제외의 분모 |
| representative_selection_reason | 소스·문서 역할·버전 선택 이유 |

회원 전체 목록은 불변 JSON 파일로 시작한다. `n/mean/sd/p10/...`만 저장하는 방식은 기각했다. 데이터량·쿼리 요구가 커지면 같은 계약을 population_member 관계 테이블로 옮길 수 있다. 원점수 분포와 동점 처리 규칙 없이 정확한 백분위를 재생성할 수는 없다.

## 6. ADR: 왜 14개 표인가

**상태: Proposed (09-22).** 팀 4명, 설계/크롤러 인계 09-30, 저장 계층 결정 10-07이라는 제약을 따른다.

| 대안 | 장점 | 문제 | 선택 |
|---|---|---|---|
| 기존 9개 표에 run 문자열만 추가 | 변경이 작음 | 실패 요청·원본 파일·추출 실행이 혼재, 묶음 키 발급 근거 없음 | 기각 |
| 5개 최소 엔티티 추가 + 불변 manifest | 각 입도 분리, DB 중립, 실행 재현 가능 | 표 5개와 파일 manifest 검증이 늘어남 | 이번 검토안 |
| 완전한 SCD2/법령/LLM/지표/모집단 회원 테이블 모두 구현 | 모든 이력에 SQL 조회 가능 | DS·DB·법령 대응 미정인데 큰 모델을 먼저 고정 | 보류 |

- fund_group: 09-20 고정 키를 발급/조회할 자리가 필요하다. 이름에 UNIQUE를 걸어 모·자·호수를 잃는 대안은 피한다.
- pipeline_run/population_snapshot: 이미 채택된 개념의 논리 구체화다. 속성/정밀도는 승인 전이다.
- collection_attempt: 바이트 없는 실패·정상 빈 응답·인증/한도 오류를 원본파일과 같은 행으로 강제할 수 없다.
- file_extraction: 같은 파일에 여러 파서 결과가 생긴다. raw의 extract_status 한 칸으로는 과거 점수를 설명하지 못한다.

받아들이는 비용: 파일 manifest도 백업·해시 검증 대상이며, 재실행 시 절 메타데이터가 중복될 수 있다. 재사용을 위한 복잡한 다중 버전 참조 그래프는 지금 추가하지 않는다. 입력량이 커지거나 여러 팀이 독립 채점할 때 분리 실행/회원 테이블을 재검토한다.

## 7. 아직 결정이 필요한 항목

| 항목 | 지금의 처리 | 완료에 필요한 근거/담당 |
|---|---|---|
| CDI 축별·문서·문서쌍 지표 | 가짜 절/절마다 복제 금지. 원문 구간과 파일 관계 보존 | 다빈 변수표(09-23): 각 지표 계산 단위/필요 텍스트/분모/결측/산식 |
| 고지충실도 | 기존 score_type은 호환용으로 남김. 점수인지 체크리스트 필터인지 확정 전 산출 금지 | 민석·다빈: 법적 서류 대응과 점수 방향/적용 상품군 |
| 요약/본문 | DART 내 summary 구간과 금투협 별도 파일 식별 가능 | 비교쌍 선정·입력 길이·쌍 지표 저장 계약(DS, 09-30) |
| 짧은 절 | 성공 추출 유지, SHORT_TEXT 표시 | 최소 문장/어절/고유어 분모, 0분모 처리(DS) |
| 대표 문서 | 계보/기준일 제한 + 실행별 선택 기록, 충돌 제외 | DART/금투협 및 정식/간이 우선순위, 실제 적용일 확인 |
| 판매 중 전수 | 확인 범위와 후보 범위 분리 | 판매종료일 원천, KRX 영업일/완전성·공모 분류 정책 |
| ELS | CDI 제외, 식별 미정 데이터는 raw 대기 | 발행사/회차/표준코드와 상품 모델(Phase 2) |
| 법인 코드 대응 | saleCompCd 별도 보존, 미매칭 NULL | DART corp_code ↔ 금투협 운용사 코드 검수 |
| 제재 후보키/과거 커버리지 | 표본 8건만 후보 검증. 0건을 무제재 라벨로 쓰지 않음 | 복합키 안정성, 게시판 실명/키·API 대조, 대상 외 기준 |
| LLM 6필드 | 원본/근거 구간 보존, 이름·타입 임의 확정 안 함 | 민석·다빈 09-30 정의표 → 주영 인계 → 10-14 JSON |
| 물리 적재 | DBML은 논리 타입·관계만 | DB 10-07, PK 생성·CHECK·timestamp/decimal·SCD 버전 PK 결정 |

**지금 할 수 있는 일**은 원본 저장·요청 이력·구조 추출의 계보를 이 설계에 맞춰 구현하는 것이다. **CDI 전체 4축을 최종 재현 가능한 분석 스키마로 확정했다고 보기는 이르다.** 미정 항목은 테스트가 통과해도 자동 해소되지 않는다.

## 8. 검증 기록

- 저장 CSV 3종 직접 재집계: 위 3절.
- `@dbml/core` 실제 파서로 14개 테이블의 구문·참조 해석 성공. 검증 중 section의 indexes 블록 뒤에 칼럼이 있던 문법 오류를 수정했다.
- DBML과 Mermaid의 테이블 이름 집합 14개 일치, 부모→자식 관계의 중복을 포함한 목록 31개 일치. 누락됐던 raw_object→section 관계를 추가했다. Mermaid 렌더러를 통한 이미지 렌더링은 실행하지 않았다.
- PostgreSQL SQL 내보내기 스모크 검증 성공(메모리에서 생성만 수행). DB 제품 선택이나 물리 DDL 승인·실제 DB 적용을 뜻하지 않는다.
- 변경한 Markdown과 본 보고서의 상대 파일 링크 21개 모두 존재 확인. `git diff --check` 통과.
- 소스 현황표의 제재 `-` 개수를 1/8·1/8·3/8로 바로잡았다. 과거 0건 응답으로 연간 전수·보존 정책을 단정한 설명과 KRX 차집합을 상장폐지로 확정한 설명을 수정했다.
- 스키마가 논리 제안이므로 DB 마이그레이션 적용이나 운영 데이터 무결성 검증을 완료한 것은 아니다.

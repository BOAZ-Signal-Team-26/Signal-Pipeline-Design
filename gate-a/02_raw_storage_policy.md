# 02. 원본 보관 규칙 — 2026-09-22 재검토안

원본 바이트는 불변이다. 저장소 제품과 CAS 채택은 Gate B에서 결정한다. 아래는 문서·API·실패 응답 모두에 적용하는 **논리 경로 제안**이다. 기존 저장 파일을 이동하거나 덮어쓰지 않았다.

## 1. 파일 경로

```text
raw/{source}/{collected_date}/{object_key_hash}/{file_role}__v{version_seq}.{ext}
raw/{source}/{collected_date}/{object_key_hash}/{file_role}__v{version_seq}.{ext}.meta.json
```

| 요소 | 의미 |
|---|---|
| source | 서비스/엔드포인트 이름공간. 제재와 경영유의 API는 구분 |
| collected_date | 실제 수집 UTC 날짜 YYYY-MM-DD. 원천 기준일과 별개 |
| object_key_hash | source_object_key의 정규화된 원천 구성 필드를 UTF-8 JSON으로 직렬화한 SHA-256 |
| source_object_key | 문서: 문서키+역할+첨부 식별자. API: 서비스+기준일/조회기간+페이지+비밀값 없는 필터 |
| file_role | cover_html/cover_xml/body_pdf/api_response/attachment/prospectus/prospectus_simple/change_summary |
| version_seq | 동일 source/source_object_key의 바이트 버전. 1부터 시작 |
| ext | 실제 콘텐츠 형식에 따라 결정. 오류 HTML을 pdf로 저장하지 않음 |

**왜 바꿨나**: 기존 `{문서키}__v1.meta.json`은 DART XML/PDF의 metadata가 충돌했고, 역할만 추가해도 같은 역할의 여러 첨부를 구분하지 못했다. 파일 식별자가 경로를 구분하고 meta.json은 **확장자까지 포함한 정확한 파일명**에 붙인다. 원천 이름에 슬래시·쿼리·한글 등이 있어도 경로 구성으로 직접 사용하지 않는다. 읽기 쉬운 문서키와 원래 파일명은 metadata에 보존한다.

## 2. 원본과 요청은 다른 단위

- `raw_object`는 실제 저장한 바이트의 버전이다. SHA-256·storage_path는 필수다.
- `storage_path`는 **`RAW_ROOT` 기준 상대경로만** 저장한다(09-22). 절대경로를 넣으면 노트북·서버마다 루트가 달라 DB 덤프를 옮길 때 경로가 전부 무효가 된다. 오브젝트 스토리지로 옮기면 이 상대경로가 그대로 객체 키가 된다.
- `collection_attempt`는 요청 한 번이다. 타임아웃처럼 바이트가 없으면 raw_object_id=NULL인 시도만 기록한다. 가짜 파일·빈 해시를 만들지 않는다.
- HTTP 오류라도 응답 바이트가 있으면 원본으로 보존할 수 있다. `collect_status=failed`인 파일은 본문 추출 대상으로 쓰지 않는다.
- 정상 빈 API 응답도 바이트가 있으면 보존하고, 시도 outcome=EMPTY로 기록한다.
- 포털·KRX·목록 응답은 `document_id=NULL`로 저장한다. 파일을 보관하기 위해 가짜 공시 문서를 만들지 않는다.
- 문서와 파일 연결은 별개다. 같은 바이트가 여러 문서에 등장하면 각 문서의 연결을 남긴다. CAS로 실체를 공유할지는 별도 결정이다.

## 3. 버전·중복·재추출

동일 source/source_object_key의 최신 버전과 **바이트 SHA-256**을 비교한다.

1. 같으면 새 파일 버전을 만들지 않고 collection_attempt가 기존 raw_object를 참조한다.
2. 다르면 version_seq를 늘려 새 파일을 저장한다.
3. 같은 파일도 **새 run_id의 파서/전처리**가 다르면 다시 추출한다. 중복 다운로드 생략과 재추출 생략을 같은 규칙으로 처리하지 않는다.
4. 같은 run_id의 재시도는 키를 유지하고 결과를 멱등 처리한다. 완료 실행의 결과는 수정하지 않는다.

`document.version_no`는 확인된 공시 정정 계보, `raw_object.version_seq`는 파일 바이트 버전, `run_id`는 처리 실행이다. **해시가 같다는 이유로 두 공시가 정정 관계가 아니라고 결론 내리지 않는다.**

금투협 수시공시의 같은 공고 안에서 동일 `server_path + fileNm`을 가리키는 클래스 행은 다운로드 전에 접는다. 서로 다른 공고/날짜의 같은 파일명이 항상 불변이라는 가정은 하지 않는다. 수시공시 4필드 문서키와 정기공시 구분은 01·12를 따른다.

## 4. Metadata

모든 파일 metadata는 다음을 포함한다.

| 항목 | 내용 |
|---|---|
| raw_object_id, source, source_object_key, version_seq | 원본 식별 |
| document_id, source_doc_key, source_key_payload | 문서 파일이면 원천 공시 식별, API 스냅숏이면 NULL |
| file_role, file_name, original_file_name, server_path | 역할·서버명·표시명·서버 위치 |
| body_format, content_type, sha256, storage_path | 실제 형식·바이트 해시·저장 경로 |
| collected_at, source_baseline_date | UTC 수집 시각과 원천 기준일 |
| request_params, endpoint/download_url | **인증값 제거**된 JSON/URL. 헤더 AUTH_KEY, serviceKey, crtfc_key, authKey 등 원문 금지 |
| credential_ref | 필요하면 비밀값 저장소의 참조 이름만 |
| http_status, source_result_code, collect_status | 전송/업무 응답/파일 검증 결과 구분 |
| attempt_id, run_id | 파일을 확보한 요청/실행 연결 |

DB에서 빠진 원본도 복원할 수 있도록 파일 식별·해시·원천 정보를 함께 남긴다. 실패 요청 중 파일이 없는 경우는 별도의 시도 로그가 복구 원천이다. 전체 요청 로그를 출력하면서 인증 URL을 노출하지 않는다.

## 5. DART와 소스 간 중복

- 공개 `viewer.do` 표지는 **HTML**(`cover_html`)로 보관한다. 공개 뷰어 표지의 실측을 API `document.xml` 응답 실측으로 취급하지 않는다.
- `document.xml` API 응답은 ZIP을 원바이트로 보관한다. 내부 XML/PDF 동봉 여부는 확인 후 기록한다. 공개 뷰어 경로와 API 경로를 혼합해 문서당 정확히 2파일을 강제하지 않는다.
- 본문 PDF는 별도 `body_pdf`다. 간이투자설명서는 DART 본문 안의 실제 요약 구간일 수 있으므로 반드시 별도 첨부라고 가정하지 않는다.
- 금투협 간이 PDF와 DART 본문 속 요약 구간은 파일 해시가 달라도 내용이 중복될 수 있다. 파일 해시 교집합 0은 문서 내용 중복 0의 증거가 아니다.
- CAS는 바이트 저장 중복 문제를 해결할 수 있지만, 비교 모집단의 펀드/대표본 중복 문제는 해결하지 못한다.

## 6. 파생 텍스트·실행 스냅숏

```text
derived/{run_id}/text/{raw_object_id}.txt
runs/{run_id}/inputs.json
runs/{run_id}/populations/{population_snapshot_id}.json
```

canonical text는 UTF-8/LF이며 파일 전체 텍스트를 보존한다. `file_extraction`에 경로·해시·Unicode code point 길이를 남긴다. 각 지표에 따라 표/표준문안을 제외할 수 있지만 원문 텍스트를 전역 삭제하지 않는다.

입력·모집단 manifest는 완료 후 불변이고 해시 검증/백업 대상이다. 최소 내용은 [18](18_schema_review.md) 5절. 저장 제품·원자적 게시 방식·백업 스케줄은 Gate B에서 결정한다.

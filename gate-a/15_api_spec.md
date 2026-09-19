# 15. 데이터 소스 API 명세 (엔지니어링 참조)

**이 문서의 범위는 「어떻게 호출해서 받아오는가」 하나다.** 받은 뒤의 일 — 원본 보관은 `02`,
수집·파싱 실패 판정은 `03`, 조인 키는 `01`, 각 사실의 실측 근거는 `09`·`10`·`12`·`13`·`14`에 있다.
같은 내용을 여기에 다시 쓰지 않는다. 두 벌이 되면 반드시 어긋난다.

작성 2026-09-20. 모든 파라미터는 **실측 또는 공식 스펙 페이지 판독**으로 확인한 것이며,
확인하지 못한 것은 절마다 「미확인」으로 표시했다.

## 결론 먼저

| 소스 | 인증 | 상태 | 호출 스크립트 |
|---|---|---|---|
| 금투협 전자공시 | **불필요** | 실호출 확인 | `fetch_kofia_ann.py` · `fetch_kofia_sales.py` · `kofia_attachments.py` |
| 공공데이터포털 펀드상품기본정보 | 키 | 실호출 확인 (183,649건) | `verify_etf_rule.py` |
| KRX ETF 일별매매정보 | 키 + **서비스별 승인** | 실호출 확인 (1,167건) | `verify_etf_rule.py` |
| DART 공개 뷰어 | **불필요** | 실호출 확인 | (스크립트 없음, `curl`) |
| OPEN DART API | 키 | **미호출** — 가이드 판독만 | 없음 |
| 금감원 검사결과제재 / 경영유의 | 키 | **미호출** — 공개 샘플 판독만 | `fetch_fss_sanctions.py` |
| 금감원 분쟁조정결정례 | 불필요 | 실호출 확인 (8건) | `hwp_text.py` + `_ole.py` |
| 국가법령정보 | 키(`OC`) | **미호출** | 없음 |
| finlife | 키 | **조인 키 없음. 소스에서 뺄 후보** (`10`) | 없음 |

**세 가지를 먼저 알아야 한다.**

1. **`urllib`로는 금투협을 받을 수 없다.** 응답이 중간에서 잘린다(1,499행 중 43행). `curl`을 쓴다.
2. **파라미터 누락이 오류가 아니라 「빈 결과」로 나타나는 소스가 있다.** 금투협 `uRptAllYN`이 대표적이다.
   HTTP 200 + 정상 XML + 0행이 온다. 0건을 정상으로 넘기면 안 된다(`03`).
3. **금감원 OPEN API의 JSON 루트 키는 `reponse`다.** `response`가 아니다. 공식 스펙의 오타이며
   그대로 따라야 한다.

## 1. 금투협 전자공시 (dis.kofia.or.kr) — 인증 불필요

화면이 WebSquare이고 뒤에 **proframe**이라는 XML-RPC 계열 서버가 있다. 공식 API 문서는 없다.
아래는 화면 JS를 읽고 실호출로 확인한 것이다(`12`).

### 공통 호출 형식

```
POST https://dis.kofia.or.kr/proframeWeb/XMLSERVICES/
Content-Type: text/xml; charset=UTF-8
Referer: https://dis.kofia.or.kr/websquare/index.jsp
```

```xml
<message>
  <proframeHeader>
    <pfmAppName>FS-DIS2</pfmAppName>
    <pfmSvcName>{서비스명}</pfmSvcName>
    <pfmFnName>{함수명}</pfmFnName>
  </proframeHeader>
  <systemHeader></systemHeader>
  <{DTO명}> ... </{DTO명}>
</message>
```

`pfmAppName`은 네 서비스 모두 `FS-DIS2`로 같다. 바뀌는 것은 `pfmSvcName`·`pfmFnName`·DTO뿐이다.

### 1-1. 공시 목록 — `DISFundFTimeAnnSO.selectAnn`

DTO는 `DISFTimeAnnInsDTO`.

| 파라미터 | 값 | 설명 |
|---|---|---|
| `uGb` | `1` | 전체(정기+수시). **`2`·`3`은 0건을 돌려준다** |
| `vStrtDt` / `vEndDt` | `YYYYMMDD` | **조회기간 1년 이내.** 넘으면 화면 검증과 같은 이유로 실패 |
| `uCdList` | 빈 값 | 펀드 지정. 비우면 전체 |
| `gbOption` | `S` | `S`=펀드선택 / `N`·`F`=펀드명 |
| `uRptList` / `tsCd` | 빈 값 | 보고서 유형 |
| **`uRptAllYN`** | **`1`** | `tsCd`가 비면 **반드시 `1`**. `0`이면 **오류 없이 0건** |
| `companyCd` | 빈 값 | 운용사 지정. 비우면 전체 |

**응답**: 행 요소는 `<list>`, 그리드 컬럼 20개. 쓰는 것은
`standardDt` `uFundNm` `koreanNm` `standardCd` `companyCd` `tsCd` `txCd` `txVsn`
`announceTtl` `seq` `tmpV1` `uRptGb` `Status_GB`.

**자연키**는 `(companyCd, standardDt, announceTtl, tmpV1)`. **`tmpV1`을 빼면 안 된다** —
같은 날 같은 제목의 서로 다른 펀드가 한 묶음으로 뭉갠다(표본에서 펀드 72종 234행이 한 덩어리가 됐다).

**증분**: `standardDt`, 7일 룩백(`03`).

### 1-2. 첨부 목록 — `DISFtimeDetSO.select`

DTO는 `DISFtimeDetOutputListDTO`. 파라미터는 1-1 응답 행에서 그대로 가져온다:
`companyCd` `standardDt` `standardCd` `txCd` `txVsn` `seq`, 그리고 `uGb`는 **`F` 고정**.

**다운로드**: `https://disdown.kofia.or.kr/COMFSFileDownload.jsp` (Referer `https://dis.kofia.or.kr/` 필요).

**중복 판정은 `sha256`이 아니라 `fileNm`으로 한다** — 내려받기 *전에* 가려야 의미가 있기 때문이다(`02`).

### 1-3. 판매회사 마스터 — `DISMngCompInqSO.select`

DTO는 `DISMngCompInqListDTO`. `option=S2`, `standardDt={YYYYMM}`. 응답 행 요소는 `<list>`,
쓰는 필드는 `saleCompCd`·`koreanNm`. **약 200곳.**

### 1-4. 판매사별 펀드 — `DISSalesCompFeeCmsSO.select`

DTO는 `DISCondFuncDTO`. `tmpV11`=판매사코드, `tmpV30`=기준일(`YYYYMMDD`), 나머지(`tmpV12`·`tmpV3`·`tmpV5`·`tmpV4`)는 빈 값.

**응답 행 요소가 `<list>`가 아니라 `<selectMeta>`다.** 금투협의 다른 서비스와 다르다.
필드는 `tmpV17`=표준코드, `tmpV18`=운용사코드, `tmpV2`=펀드명, `tmpV4`=설정일, `tmpV16`=기준일.

**한계**: 「상장지수」가 **0건**이다. **ETF는 이 소스로 판매사를 붙일 수 없다**(`14` 4절).
전체 순회는 200곳 × 평균 3,000건 ≈ 60만 행이므로 호출 간격 1초를 둔다.

### 1-4를 쓸 때의 기한 리스크

**조회 창이 1년이다.** 받지 않고 1년이 지난 공시는 영구히 받을 수 없다. 백필 계획 자체는
관문 B 사안이지만 늦어질수록 잃는 구간이 늘어난다(`gate-b/README.md`).

## 2. 공공데이터포털 — 펀드상품기본정보

```
GET https://apis.data.go.kr/1160100/service/GetFundProductInfoService/getStandardCodeInfo
    ?serviceKey={키}&numOfRows=1000&pageNo={n}&resultType=json
```

- **인증**: `DATA_GO_KR_API_KEY`. `serviceKey`는 **URL 인코딩하지 않는다**(`safe=""`로 encode).
- **페이징**: `numOfRows` 최대 1,000. `response.body.totalCount`까지 `pageNo`를 올린다. 184페이지.
- **응답**: `response.body.items.item`. **1건일 때 배열이 아니라 객체로 온다** — 리스트로 감싸야 한다.
- **쓰는 필드**: `srtnCd`(단축코드 5자리) `asoStdCd`(표준코드) `fndNm` `setpDt` `fndTp`.
- **실측**: 183,649건(2026-09-19). 펀드 1개당 1행이며 **클래스와 사모를 포함한다**.
- **`srtnCd` 성질**: 형식은 `[A-Z0-9]{5}` 전건 일치. `srtnCd == asoStdCd[6:11]`이 100% 성립.
  **전역 유일이 아니다** — 4,899종(3.0%)이 겹친다. 우리 범위에서는 안전하다(`14` 2절).
- **증분**: `basDt`. **`setpDt`는 과거 날짜라 워터마크로 쓰면 안 된다**(`03`).

## 3. KRX — ETF 일별매매정보

```
GET https://data-dbg.krx.co.kr/svc/apis/etp/etf_bydd_trd?basDd={YYYYMMDD}
Header: AUTH_KEY: {키}
```

- **인증**: `KRX_API_KEY`. **발급과 승인이 별개다.** 키를 받아도 서비스별로 이용 승인을 따로 받아야 한다.

| 응답 | 뜻 |
|---|---|
| `{"respMsg":"Unauthorized **Key**"}` | 키가 없거나 틀림 |
| `{"respMsg":"Unauthorized **API Call**"}` | 키는 맞으나 **해당 서비스 승인이 없음** |

  **두 메시지를 구분해야 원인을 안다.**
- **응답**: 최상위 객체 안의 유일한 배열이 목록이다. 쓰는 필드는 `ISU_CD`(종목코드)·`ISU_NM`.
- **`ISU_NM`은 정식 펀드명이 아니라 상장 약명이다** (`1Q 200액티브` vs `하나1Q200액티브증권상장지수투자신탁[주식]`).
  공공데이터포털과 **완전일치율이 0.0%**다. 포함매칭으로도 80.4%가 천장이다(`13` 4절).
- **실측**: 1,167건(2026-09-04 기준일).
- **적재**: 증분이 아니라 **매일 전건 스냅숏, 전건 보관**. 상장 여부는 그날의 상태라 나중에 재구성할 수 없다(`03`).
- **미확인**: `basDd`로 과거 일자를 돌려주는지. 돌려준다면 위 결정은 되돌릴 수 있다.
- **우회로 없음**: `data.krx.co.kr`의 비공식 `getJsonData.cmd`는 세션을 요구해 `LOGOUT`만 준다.

## 4. DART

### 4-1. 공개 뷰어 — 인증 불필요 (실호출 확인)

```
GET https://dart.fss.or.kr/dsaf001/main.do?rcpNo={접수번호}
```

좌측 문서 트리를 만드는 **인라인 `<script>` 안에 노드 배열이 서버 렌더링되어 있다.** AJAX가 아니다.
거기서 `dcmNo`·`eleId`·`offset`·`length`·`dtd`를 뽑아 본문을 받는다.

```
GET https://dart.fss.or.kr/report/viewer.do
    ?rcpNo=&dcmNo=&eleId=&offset=&length=&dtd=dart4.xsd
```

- 표지 노드는 `eleId=2`, 위험등급은 `「n등급[문구]」` 표기(`08` A1).
- 목록 진입점 `https://dart.fss.or.kr/dsac001/mainF.do`는 서버 렌더링 HTML 표라 바로 파싱된다.
- **실측**: 투자설명서 10건 중 표지 펀드코드가 **10/10** 존재. ETF 3건 포함(`09`).
- **판매회사 명단은 표지에 없다**(`09`). 판매사는 금투협에서 받는다(1-4).

### 4-2. OPEN DART API — **미호출**

```
GET https://opendart.fss.or.kr/api/document.xml?crtfc_key={키}&rcept_no={접수번호}
```

인자는 둘뿐이고 응답은 zip이다. **가이드 페이지만 인증키 없이 읽었고 실제 호출은 못 했다**(`09`).

**확인 불가로 남긴 것**: zip 안에 XML만 있는지, PDF 등 첨부까지 들어있는지.
가이드 본문에 이를 명시하는 문장이 끝내 없었다. 추정으로 설계하지 말 것.

**증분**: `rcept_dt`, **3일 룩백**(정정본을 놓치지 않기 위해)(`03`).

## 5. 금감원 OPEN API — 검사결과제재 · 경영유의사항 등 공시

**두 API는 같은 표의 두 뷰다.** 요청 변수도 결과 필드 13개도 이름까지 같고, 예시의
`examMgmtNo`가 동일하다. 다른 것은 경로와 구분 필드뿐이다(`14` 6절).

```
GET https://www.fss.or.kr/fss/kr/openApi/api/openInfo.jsp        # 검사결과제재
GET https://www.fss.or.kr/fss/kr/openApi/api/openInfoImpr.jsp    # 경영유의사항 등
    ?apiType={xml|json}&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&authKey={32자리}
```

**요청 변수는 넷뿐이다.** 금융회사도 업종도 **페이지도 없다**.

**결과 필드 13개**: `emOpenNo`(제재정보번호) `examMgmtNo`(검사관리번호) `transCode` `emOpenSeq`
`actGbn` **`finInstName`(금융회사)** `actReqDate`(제재조치일) `actOrganCon` `actOfficerCon`
`actEmpCon` `actObjContent`(제재대상사실) `inputDate` `inputMan`.

| 함정 | 내용 |
|---|---|
| **JSON 루트 키가 `reponse`** | `response`로 짜면 전건 0으로 조용히 실패한다 |
| **페이징 없음** | 5,700여 건 백필은 **기간 분할**로만 가능 |
| **`emOpenSeq`는 워터마크가 아님** | 검사 1건 안의 순번이고 요청 변수에도 없다. 증분은 날짜로만 |
| 날짜 형식 3종 | 요청 `YYYY-MM-DD` / `actReqDate` `2026.04.24` / `inputDate` `2026-04-27 10:14:12` |
| **상품 칸이 없음** | 본문도 `㉮펀드`·`甲`·`A지점`으로 마스킹. `문서.product_id`는 영구 NULL |

**인증키**: 32자리. **개인 신청과 법인 신청의 경로가 다르고, 법인 키에만 요청 IP 등록이 붙는다.**
수집 서버 IP가 정해지기 전에 법인 키를 신청하면 재신청해야 한다.

**미확인 셋** (키를 받으면 `--probe` 한 번으로 전부 확인된다):
`startDate`가 `actReqDate`에 걸리는지 `inputDate`에 걸리는지 / 경영유의사항 본문의 실제 마스킹 수준 /
`emOpenNo`가 두 소스에 걸쳐 유일한지.

## 6. 금감원 분쟁조정결정례 — 게시판 + HWP

API가 없다. 게시판 `B0000390`이며 **본문이 비어 있고 HWP 첨부만 준다.**

HWP 5.0은 OLE 복합문서다. `BodyText/Section0`을 **zlib raw deflate(`-15`)**로 풀고
`HWPTAG_PARA_TEXT`(태그 67) 레코드에서 UTF-16LE 텍스트를 꺼낸다.
`scripts/hwp_text.py` + `scripts/_ole.py`가 외부 의존성 없이 처리한다.

| 한계 | 내용 |
|---|---|
| **HWP 3.0은 읽지 못한다** | OLE가 아니라 자체 바이너리다. 첨부 213단위 중 **94건**(1999~2004년)이 여기 해당 |
| 「상위 버전 배포용 문서」 | `BodyText`가 안내문뿐이다. `--preview`로 `PrvText`(약 1,000자)를 건지는 것이 최선 |

**조인 불가**: 상품명뿐 아니라 **판매사명도 마스킹**이다(`●●증권`). 업종만 남는다(`14` 5절).

**이 절의 구멍**: 게시판 **목록 조회와 첨부 다운로드의 정확한 URL·파라미터가 저장소에 기록돼 있지 않다.**
`14` 5절 실측은 임시 `curl`로 했고 스크립트로 남기지 않았다. 남은 것은 게시판 ID(`B0000390`)와
행 식별자(`nttId`)뿐이다. **수집 모듈을 짜기 전에 이 절을 채워야 한다** — 다른 소스와 달리
여기만 「다시 알아내야」 한다.

## 7. 국가법령정보 — **미호출**

`LAW_API_OC`가 비어 있다. 무인증 호출은
`{"result":{"err_cd":"010","err_msg":"미등록 인증키","total_count":"0"}}`를 돌려준다.

**다만 J13은 키를 받아도 풀리지 않는다.** 먼저 정해야 하는 것이 둘이다.

1. 금소법 19조의 **「설명서」**와 우리가 수집하는 **「투자설명서」**는 같은 서류가 아니다.
   대응 관계가 정의되지 않았다.
2. 고지충실도가 **점수 축인가 누락 검출 필터인가** — `04`와 팀 EPIC의 기재가 어긋나 있다.

→ `01` 미확인 3. 인증키 신청보다 이 결정이 먼저다.

**증분**: `MST` 변경 여부가 미확인이라 **조문 내용 해시**로 대체한다(`03`).

## 8. finlife — 조인 키 없음

오픈 API 8종은 정기예금·적금·연금저축·주택담보대출·전세자금대출·개인신용대출·개인사업자대출·금융회사개요다.
**펀드·ETF·ELS가 없다.** 화면의 「펀드」 메뉴는 금투협 전자공시로 리다이렉트된다(`10`).

→ **조인 키로 성립하지 않는다.** 소스 존치 여부는 미결(`01` J9).
`fin_prdt_cd`가 8종 공통 응답 필드라는 것도 공식 원문으로는 확인하지 못했다(`10`).

## 9. 공통 규칙

### 방어적 수집

호출 간격 **1초 이상**, 동시 요청 **1개**. 전체 순회가 60만 행 규모인 금투협 1-4에 특히 적용한다.

### 재시도

스크립트 공통: **3회**, 대기 2초·4초. 네트워크 오류와 파싱 오류를 함께 받는다.

### 응답 완전성 검증 — 소스마다 수단이 다르다

| 소스 | 검증 수단 |
|---|---|
| 금투협 | 응답이 **`</root>`로 끝나는지**. 끝나지 않으면 절단이다 |
| 공공데이터포털 | `totalCount`와 누적 건수 대조 |
| 금감원 OPEN API | `resultCode == "1"` 확인. 아니면 `resultMsg`를 그대로 올린다 |
| KRX | `respCode` 키가 있으면 오류 응답이다 |

**절단을 잡지 못하면 파서가 행을 조용히 적게 센다.** 이것이 가장 비싼 실패다.

### 인증키

`.env`에 두고 **절대 커밋하지 않는다**(`.gitignore`). `.env.example`에는 **이름만** 적는다.

| 이름 | 소스 | 상태 |
|---|---|---|
| `DATA_GO_KR_API_KEY` | 공공데이터포털 | 있음 |
| `KRX_API_KEY` | KRX | 있음 (+ 서비스 승인 완료) |
| `OPENDART_API_KEY` | OPEN DART | 미확인 |
| `FINLIFE_API_KEY` | finlife | 소스 존치 미결 |
| `LAW_API_OC` | 국가법령정보 | **비어 있음** |
| `FSS_API_KEY` | 금감원 제재·경영유의 | **미발급** — `.env.example`에도 아직 없다 |

## 10. 미확인 목록

| # | 항목 | 막고 있는 것 |
|---|---|---|
| 1 | OPEN DART `document.xml` zip 내용물 (XML만인가 첨부 포함인가) | 인증키 |
| 2 | 금감원 `startDate`가 걸리는 필드 | 인증키 |
| 3 | 경영유의사항 본문의 마스킹 수준 | 인증키 |
| 4 | `emOpenNo`가 제재·경영유의에 걸쳐 유일한지 | 인증키 |
| 5 | KRX `basDd`가 과거 일자를 돌려주는지 | 호출 1회 |
| 6 | 국가법령정보 연결 방식 | **인증키가 아니라 설계 결정** (7절) |
| 7 | finlife `fin_prdt_cd` 공통 필드 여부 | 소스 존치 결정이 먼저 |
| 8 | **분쟁조정 게시판 목록·첨부 URL과 파라미터** | 아무것도 막지 않는다. **기록하지 않아 잃어버린 것**이다 (6절) |

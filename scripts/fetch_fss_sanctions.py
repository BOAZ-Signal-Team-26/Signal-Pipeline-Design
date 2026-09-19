#!/usr/bin/env python3
"""금감원 검사결과제재 OPEN API 수집 (J11·J12).

설계 근거는 gate-a/14 6절. **아직 인증키가 없어 실호출로 검증하지 못했다.**
금감원 스펙 페이지(OPEN API > 상세 및 테스트 > 검사결과제재 API)의 공개 샘플에
맞춰 짰다. 키를 받으면 --probe 로 남은 미확인 하나를 먼저 확인할 것.

용례:
    python3 scripts/fetch_fss_sanctions.py --probe                 # 날짜 필터 대상 확인
    python3 scripts/fetch_fss_sanctions.py --from 2026-01-01 --to 2026-09-20 > s.csv

주의 넷 (전부 gate-a/14 6절)
- **JSON 루트 키는 `reponse`다.** `response`가 아니라 금감원 스펙의 오타 그대로다.
  `response`로 읽으면 전건 0으로 조용히 실패한다.
- **페이징이 없다.** 요청 변수는 넷뿐이라 전량 백필은 기간 분할로만 한다.
- **`emOpenSeq`는 워터마크가 아니다.** 검사 1건 안의 순번이며 요청 변수에도 없다.
  증분은 날짜로 잡는다.
- 응답에 **상품을 가리키는 칸이 없다.** 본문도 `㉮펀드`로 마스킹이라
  `문서.product_id`는 영구 NULL이고, 붙는 축은 `finInstName`(판매사)뿐이다.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request

URL = "https://www.fss.or.kr/fss/kr/openApi/api/openInfo.jsp"

# 결과변수 표 그대로. 순서를 CSV 열 순서로 쓴다.
FIELDS = ["emOpenNo", "examMgmtNo", "transCode", "emOpenSeq", "actGbn",
          "finInstName", "actReqDate", "actOrganCon", "actOfficerCon",
          "actEmpCon", "actObjContent", "inputDate", "inputMan"]

CALL_INTERVAL = 1.0     # 방어적 수집 원칙(조사 상세 2-1)
CHUNK_DAYS = 90         # 페이징이 없어 기간을 쪼갠다


def load_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, _, value = line.partition("=")
                os.environ.setdefault(name.strip(), value.strip())


def call(key: str, start: str, end: str, timeout: int = 60,
         attempts: int = 3) -> list[dict[str, str]]:
    query = urllib.parse.urlencode({"apiType": "json", "startDate": start,
                                    "endDate": end, "authKey": key})
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                "%s?%s" % (URL, query), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8", "replace"))
            # 스펙의 오타를 그대로 따르되, 금감원이 고칠 경우에 대비해 둘 다 본다.
            body = payload.get("reponse") or payload.get("response") or {}
            if str(body.get("resultCode", "")) != "1":
                raise RuntimeError("금감원 오류: %s" % body.get("resultMsg", payload))
            rows = body.get("result") or []
            return [rows] if isinstance(rows, dict) else rows
        except Exception as error:
            last = error
            if attempt < attempts - 1:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError("검사결과제재 조회 실패 (%s~%s): %s" % (start, end, last))


def spans(start: str, end: str) -> list[tuple[str, str]]:
    first = dt.date.fromisoformat(start)
    last = dt.date.fromisoformat(end)
    out = []
    while first <= last:
        stop = min(first + dt.timedelta(days=CHUNK_DAYS - 1), last)
        out.append((first.isoformat(), stop.isoformat()))
        first = stop + dt.timedelta(days=1)
    return out


def probe(key: str) -> None:
    """날짜 필터가 actReqDate에 걸리는지 inputDate에 걸리는지 가른다 (14 6절 미확인).

    두 날짜가 어긋나는 행이 있으면 조회 구간 밖의 값을 가진 쪽이 필터 대상이 아니다.
    """
    start, end = "2026-04-24", "2026-04-24"
    rows = call(key, start, end)
    print("%s~%s: %d행" % (start, end, len(rows)))
    for row in rows[:20]:
        act = (row.get("actReqDate") or "").replace(".", "-")
        inp = (row.get("inputDate") or "")[:10]
        mark = "" if act == inp else "  ← 두 날짜가 다르다"
        print("  actReqDate=%s  inputDate=%s  %s%s"
              % (act, inp, row.get("finInstName", ""), mark))
    print("\n조회 구간과 일치하는 쪽이 필터 대상이다. 다른 쪽이 앞서면 그 차이가 룩백 하한이다.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="start", default="2026-01-01", help="YYYY-MM-DD")
    parser.add_argument("--to", dest="end",
                        default=dt.date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--probe", action="store_true",
                        help="날짜 필터 대상 필드만 확인하고 끝낸다")
    args = parser.parse_args()

    load_env()
    key = os.environ.get("FSS_API_KEY", "").strip()
    if not key:
        sys.exit(".env 에 FSS_API_KEY 가 비어 있다. "
                 "www.fss.or.kr > OPEN API > 인증키 신청 (32자리). "
                 "법인 신청은 요청 IP 등록이 따른다 — gate-a/14 6절.")

    if args.probe:
        probe(key)
        return

    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    total = 0
    windows = spans(args.start, args.end)
    for index, (start, end) in enumerate(windows, 1):
        if index > 1:
            time.sleep(CALL_INTERVAL)
        rows = call(key, start, end)
        writer.writerows(rows)
        total += len(rows)
        print("  [%d/%d] %s~%s %5d건 (누적 %d)"
              % (index, len(windows), start, end, len(rows), total), file=sys.stderr)
    print("합계 %d행" % total, file=sys.stderr)


if __name__ == "__main__":
    main()

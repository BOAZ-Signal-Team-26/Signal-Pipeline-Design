#!/usr/bin/env python3
"""검증 2 — ETF 「상장지수」 문자열 규칙의 오분류율.

KRX ETF 전종목을 정답지로 놓고, 공공데이터포털 펀드상품기본정보에서 `fndNm`에
「상장지수」가 포함된 집합을 뽑아 정규화 문자열로 대조한다. 일치·누락·오탐·잔여
네 수치를 세고, 누락과 오탐이 각각 1% 미만이면 규칙 유지로 판정한다.

용례:
    cp .env.example .env   # 키 두 개를 채운다
    python3 scripts/verify_etf_rule.py --base-date 20260904

대조를 **이름**으로 하는 이유: 공공데이터포털은 펀드 단축코드(`srtnCd`)를,
KRX는 종목코드(`ISU_CD`)를 주는데 둘을 잇는 소스가 없다(01 미확인 2).
그래서 이 검증 자체가 이름 매칭의 신뢰도를 재는 일이 된다.
"""
import argparse
import collections
import csv
import io
import json
import os
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

DATA_GO_KR = ("https://apis.data.go.kr/1160100/service/"
              "GetFundProductInfoService/getStandardCodeInfo")
KRX_ETF = "https://data-dbg.krx.co.kr/svc/apis/etp/etf_bydd_trd"

ETF_MARKER = "상장지수"
PAGE_SIZE = 1000      # 공공데이터포털 한 페이지 최대치
THRESHOLD = 0.01      # 누락·오탐 각 1% 미만이면 규칙 유지


def load_env(path=".env"):
    """.env 를 읽어 환경변수에 얹는다. 이미 설정된 값은 덮어쓰지 않는다."""
    if not os.path.exists(path):
        return
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        os.environ.setdefault(name.strip(), value.strip())


def normalize(name):
    """05 1절의 앞 두 단계(NFKC → 공백 전면 제거)만 적용한다.

    호수·클래스 분리까지 하면 ETF 여부 판정이 아니라 상품 동일성 판정이 되어
    이 검증의 물음과 어긋난다. ETF 판정은 05 2절의 별도 규칙이다.
    """
    text = unicodedata.normalize("NFKC", name or "")
    return "".join(text.split())


def fetch_json(url, timeout=60, attempts=3):
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8", "replace"))
        except Exception as error:      # 네트워크·JSON 오류를 같이 받는다
            last = error
            if attempt < attempts - 1:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError("요청 실패: %s (%s)" % (url.split("?")[0], last))


def fetch_data_go_kr(key, limit_pages=None):
    """펀드상품기본정보 전건. 펀드 1개당 1행이며 클래스와 사모를 포함한다."""
    funds, page = [], 1
    while True:
        query = urllib.parse.urlencode({
            "serviceKey": key, "numOfRows": PAGE_SIZE,
            "pageNo": page, "resultType": "json",
        }, safe="")
        payload = fetch_json("%s?%s" % (DATA_GO_KR, query))
        body = payload["response"]["body"]
        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        funds.extend(items)
        total = int(body.get("totalCount", 0))
        print("  공공데이터포털 %d/%d" % (len(funds), total), end="\r", file=sys.stderr)
        if not items or len(funds) >= total:
            break
        page += 1
        if limit_pages and page > limit_pages:
            break
    print(file=sys.stderr)
    return funds


def fetch_krx_etf(key, base_date):
    """KRX ETF 일별매매정보. AUTH_KEY 헤더로 인증한다."""
    request = urllib.request.Request(
        "%s?basDd=%s" % (KRX_ETF, base_date),
        headers={"AUTH_KEY": key, "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = json.loads(response.read().decode("utf-8", "replace"))
    for value in payload.values():
        if isinstance(value, list):
            return value
    raise RuntimeError("KRX 응답에 목록이 없다: %s" % str(payload)[:200])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-date", default="20260904", help="KRX 조회 기준일 YYYYMMDD")
    parser.add_argument("--out", default="reference/etf_rule_check.csv")
    parser.add_argument("--limit-pages", type=int, default=None, help="시험용 페이지 제한")
    args = parser.parse_args()

    load_env()
    data_key = os.environ.get("DATA_GO_KR_API_KEY", "").strip()
    krx_key = os.environ.get("KRX_API_KEY", "").strip()
    if not data_key:
        sys.exit(".env 에 DATA_GO_KR_API_KEY 가 비어 있다. .env.example 참고.")

    # KRX 키가 없으면 규칙이 몇 건을 잡는지까지만 세고 멈춘다. 누락·오탐은
    # 정답지가 있어야 나오므로 판정은 유보한다.
    krx = {}
    if krx_key:
        print("KRX ETF 정답지 조회 (%s)" % args.base_date, file=sys.stderr)
        krx_rows = fetch_krx_etf(krx_key, args.base_date)
        krx_name_fields = [f for f in ("ISU_NM", "ISU_ABBRV", "ISU_KOR_NM", "ISU_SRT_CD")
                           if krx_rows and f in krx_rows[0]]
        if not krx_name_fields:
            sys.exit("KRX 응답에서 종목명 필드를 찾지 못했다: %s" % list(krx_rows[0])[:15])
        krx_by_field = {f: {normalize(r[f]): r for r in krx_rows} for f in krx_name_fields}
        print("  KRX ETF %d건, 이름 후보 필드 %s" % (len(krx_rows), krx_name_fields), file=sys.stderr)
    else:
        print("KRX_API_KEY 없음 — 공공데이터포털 쪽만 집계한다 (부분 실행)", file=sys.stderr)

    print("공공데이터포털 펀드상품기본정보 조회", file=sys.stderr)
    funds = fetch_data_go_kr(data_key, args.limit_pages)
    rule_hits = {}
    for fund in funds:
        normalized = normalize(fund.get("fndNm"))
        if ETF_MARKER in normalized:
            rule_hits[normalized] = fund
    print("  전체 %d건 중 「상장지수」 포함 %d건" % (len(funds), len(rule_hits)), file=sys.stderr)

    if not krx:
        print("\n=== 부분 결과 (KRX 정답지 없음) ===")
        print("  공공데이터포털 전체      %6d" % len(funds))
        print("  「상장지수」 포함(규칙 적중) %6d" % len(rule_hits))
        print("\n누락·오탐률은 KRX 정답지가 있어야 나온다. 판정 유보.")
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with io.open(args.out, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["구분", "정규화명", "srtnCd", "asoStdCd", "ISU_CD"])
            for name in sorted(rule_hits):
                fund = rule_hits[name]
                writer.writerow(["규칙적중", name, fund.get("srtnCd", ""), fund.get("asoStdCd", ""), ""])
        print("상세: %s" % args.out)
        return

    # 두 소스의 이름 공간이 다를 수 있다. 공공데이터포털 `fndNm`은 정식 펀드명
    # (「삼성KODEX200증권상장지수투자신탁[주식]」)이고, KRX 종목명은 상장 약명
    # (「KODEX 200」)인 경우가 있다. 완전일치만 쓰면 전부 불일치로 나와 누락률이
    # 거짓으로 100%에 가까워진다. 그래서 후보 필드마다 일치 수를 세어 가장 잘
    # 붙는 것을 고르고, 그래도 낮으면 판정하지 않고 멈춘다.
    scored = sorted(
        ((len(set(table) & set(rule_hits)), field, table) for field, table in krx_by_field.items()),
        reverse=True,
    )
    hit_count, name_field, krx = scored[0]
    print("\n이름 필드별 완전일치 수: %s" % ", ".join(
        "%s=%d" % (f, n) for n, f, _ in scored))
    print("선택한 필드: %s" % name_field)

    coverage = hit_count / len(krx) if krx else 0
    if coverage < 0.5:
        print("\n중단: 어느 이름 필드로도 KRX ETF의 절반을 붙이지 못했다 (최고 %.1f%%)." % (coverage * 100))
        print("두 소스의 이름 공간이 다르다는 뜻이며, 이 상태의 누락·오탐률은 ETF 규칙이")
        print("아니라 이름 매칭 실패를 재게 된다. 대조 축을 바꿔야 한다 (gate-a/13 참조).")
        sys.exit(2)

    both = set(krx) & set(rule_hits)                 # 일치
    missed = set(krx) - set(rule_hits)               # 누락: KRX엔 ETF인데 규칙이 못 잡음
    false_hits = set(rule_hits) - set(krx)           # 오탐: 규칙은 잡았는데 KRX에 없음

    miss_rate = len(missed) / len(krx) if krx else 0
    false_rate = len(false_hits) / len(rule_hits) if rule_hits else 0

    print("\n=== 대조 결과 (기준일 %s) ===" % args.base_date)
    print("  일치   %6d" % len(both))
    print("  누락   %6d  (KRX ETF 대비 %.2f%%)" % (len(missed), miss_rate * 100))
    print("  오탐   %6d  (규칙 적중 대비 %.2f%%)" % (len(false_hits), false_rate * 100))
    print("  잔여   %6d  (공공데이터포털 전체에서 규칙에도 KRX에도 없는 펀드)"
          % (len(funds) - len(rule_hits)))

    keep = miss_rate < THRESHOLD and false_rate < THRESHOLD
    print("\n판정: %s" % ("문자열 규칙 유지 (누락·오탐 각 1% 미만)" if keep else
                          "규칙 보조로 강등, KRX 대조를 1차 판정으로 승격 권고"))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with io.open(args.out, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["구분", "정규화명", "srtnCd", "asoStdCd", "ISU_CD"])
        for name in sorted(both):
            fund = rule_hits[name]
            writer.writerow(["일치", name, fund.get("srtnCd", ""), fund.get("asoStdCd", ""),
                             krx[name].get("ISU_CD", "")])
        for name in sorted(missed):
            writer.writerow(["누락", name, "", "", krx[name].get("ISU_CD", "")])
        for name in sorted(false_hits):
            fund = rule_hits[name]
            writer.writerow(["오탐", name, fund.get("srtnCd", ""), fund.get("asoStdCd", ""), ""])
    print("상세: %s" % args.out)


if __name__ == "__main__":
    main()

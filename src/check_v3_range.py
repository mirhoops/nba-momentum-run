"""v3 구간의 실제 사용 가능 범위를 확정한다.

특히 2019-20은 코로나로 시즌이 쪼개졌고 possession 채움률이 75%다.
버블 경기(2020년 7~10월)가 v3 쪽인지 확인해야
'무관중 자연실험'을 쓸 수 있는지 결정할 수 있다.
"""
import pandas as pd
from loader import load_season

V3_SEASONS = ["2019-20", "2020-21", "2021-22", "2022-23",
              "2023-24", "2024-25", "2025-26"]


def fmt(series):
    """날짜 하나를 'YYYY-MM-DD' 문자열로. 값이 없으면 '-'."""
    return "-" if series.empty or series.isna().all() else str(series.min().date())


rows = []
for s in V3_SEASONS:
    df = load_season(s)

    # [1] 경기 단위로 축약. possession이 절반 이상 채워졌으면 v3 경기로 판정한다.
    g = df.groupby("gameId").agg(
        date=("gameDate", "first"),                       # 날짜 타입이라 비교 가능
        poss=("possession", lambda x: x.notna().mean()),
    )
    g["is_v3"] = g["poss"] > 0.5

    v3, v2 = g.loc[g["is_v3"], "date"], g.loc[~g["is_v3"], "date"]

    rows.append({
        "시즌": s,
        "전체경기": len(g),
        "v3경기": int(g["is_v3"].sum()),
        "v2경기": int((~g["is_v3"]).sum()),
        "v3시작일": fmt(v3),
        # v2의 '마지막' 날짜가 필요하므로 부호를 뒤집어 min을 재활용
        "v2마지막": "-" if v2.empty or v2.isna().all() else str(v2.max().date()),
    })
    print(f"  {s} 완료", end="\r")

print("\n")
print(pd.DataFrame(rows).to_string(index=False))
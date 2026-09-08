"""PBP를 포제션 단위 테이블로 압축한다.

explore.ipynb에서 단일 시즌으로 검증한 로직을 함수로 옮긴 것이다.
여러 시즌에 반복 적용해야 하므로 재사용 가능한 형태가 필요하다.
"""
import numpy as np
import pandas as pd
from loader import load_season
from possession_parser import parse_possessions

# 공격팀만 할 수 있는 행동. 이것으로 포제션의 공격 주체를 판정한다.
# block, steal, 수비 리바운드는 수비팀 행동이므로 제외.
# foul은 공격자 파울도 있어 모호하므로 제외한다.
OFF_ACTIONS = ["2pt", "3pt", "heave", "freethrow", "turnover"]


def _points(df):
    """각 이벤트의 득점을 계산한다. 실패한 슛은 0점."""
    a, r = df["actionType"], df["shotResult"]
    return np.where(
        r == "Made",
        np.where(a == "3pt", 3,
        np.where(a == "2pt", 2,
        np.where(a == "freethrow", 1,
        np.where(a == "heave", 3, 0)))),
        0)


def _off_team(df):
    """포제션별 공격팀을 판정한다. NBA 공식 태깅 대비 98.91% 일치 검증됨."""
    is_off = (df["actionType"].isin(OFF_ACTIONS) |
              ((df["actionType"] == "rebound") & (df["subType"] == "offensive")))
    rows = df[is_off & df["teamTricode"].notna()]
    return rows.groupby(["gameId", "possNum"])["teamTricode"].first()

def build(season: str) -> pd.DataFrame:
    """한 시즌의 포제션 테이블을 만든다."""
    pdf = parse_possessions(load_season(season))
    pdf["points"] = _points(pdf)

    # [1] 포제션 단위로 압축. 한 포제션이 한 줄이 된다.
    poss = (pdf.groupby(["gameId", "possNum"])
            .agg(period=("period", "first"),
                 gameSec=("gameSec", "first"),
                 lastOrder=("orderNumber", "max"),   # 라인업 매칭에 쓸 기준점
                 points=("points", "sum"),
                 hasHeave=("isHeave", "any"))
            .reset_index())

    # [2] 공격팀 부여. 판정 불가 포제션(쿼터 종료 잔여분)은 제거된다.
    poss["offTeam"] = poss.set_index(["gameId", "possNum"]).index.map(_off_team(pdf))
    poss = poss[poss["offTeam"].notna()].reset_index(drop=True)

    # [3] 포제션 번호를 구멍 없이 다시 매긴다.
    #     원래 possNum은 제거된 포제션 자리에 구멍이 생겨
    #     rolling(7)이 실제로는 8포제션 범위를 덮는 문제가 있었다.
    poss = poss.sort_values(["gameId", "possNum"]).reset_index(drop=True)
    poss["possSeq"] = poss.groupby("gameId").cumcount()

    # [4] 상대팀 부여
    teams = poss.groupby("gameId")["offTeam"].unique().to_dict()
    poss["defTeam"] = [
        (t[1] if o == t[0] else t[0])
        for o, t in zip(poss["offTeam"], poss["gameId"].map(teams))
    ]

    poss["season"] = season
    return poss
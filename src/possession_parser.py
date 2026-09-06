"""각 이벤트에 포제션 번호와 공격기회 번호를 부여한다.

PBP는 이벤트 나열일 뿐 '포제션'이라는 단위가 없다. 우리가 만들어야 한다.

두 개의 축을 만드는 이유
  possNum   : 소유권 단위. 공격 리바운드로 늘지 않는다.
  chanceNum : 슛 기회 단위. 공격 리바운드마다 +1.
  → 18-19 도입된 '공격 리바운드 후 샷클락 14초 리셋'의 효과는
    포제션 수는 그대로 두고 포제션 안의 기회 수만 늘렸으므로
    두 축을 분리해야 측정할 수 있다.
"""
import numpy as np
import pandas as pd


def is_last_freethrow(sub_type) -> bool:
    """'2 of 2' → True, '1 of 2' → False

    데이터에 'shot', 빈 문자열 등 예외값이 5건 있으므로 방어한다.
    (434만 건 중 5건이지만, 모르고 두면 int() 변환에서 터진다)
    """
    if not isinstance(sub_type, str) or " of " not in sub_type:
        return False
    try:
        cur, total = sub_type.split(" of ")
        return int(cur) == int(total)
    except ValueError:
        return False


def mark_possession_end(df: pd.DataFrame) -> pd.Series:
    """각 행이 '포제션을 끝내는 이벤트'인지 True/False로 표시한다."""
    a, s, r = df["actionType"], df["subType"], df["shotResult"]

    made_fg = a.isin(["2pt", "3pt", "heave"]) & (r == "Made")   # 야투 성공
    def_reb = (a == "rebound") & (s == "defensive")             # 수비 리바운드
    turnover = a == "turnover"                                  # 턴오버
    last_ft = (a == "freethrow") & (r == "Made") & s.map(is_last_freethrow)
    period_end = (a == "period") & (s == "end")                 # 쿼터 종료

    # 공격 리바운드는 여기에 없다. 소유권이 유지되므로 종료가 아니다.
    return made_fg | def_reb | turnover | last_ft | period_end

def parse_possessions(df: pd.DataFrame) -> pd.DataFrame:
    """포제션·공격기회 번호를 부여한 새 DataFrame을 돌려준다.

    반드시 loader.load_season()으로 정렬된 데이터를 넣어야 한다.
    파일의 원래 행 순서는 경기 진행 순서가 아니다.
    """
    df = df.copy()

    # [1] 종료 이벤트 표시
    df["isPossEnd"] = mark_possession_end(df)

    # [2] 포제션 번호 매기기
    #     종료 이벤트 '다음' 행부터 새 번호가 시작되므로 shift(1)로 한 칸 민다.
    #     cumsum()은 True를 1로 세어 누적합을 낸다 → 자동으로 일련번호가 된다.
    df["possNum"] = (df.groupby("gameId")["isPossEnd"]
                       .transform(lambda x: x.shift(1, fill_value=False).cumsum()))

    # [3] 공격기회 번호: 포제션이 바뀌거나 공격 리바운드가 나오면 +1
    oreb = (df["actionType"] == "rebound") & (df["subType"] == "offensive")
    new_chance = df["isPossEnd"].groupby(df["gameId"]).shift(1, fill_value=False) | oreb
    df["chanceNum"] = new_chance.groupby(df["gameId"]).cumsum()

    # [4] heave 플래그. 버저비터 던지기는 성공률 3% 미만이라
    #     일반 슛과 섞으면 쿼터 마지막 포제션 효율이 인위적으로 깎인다.
    df["isHeave"] = df["actionType"] == "heave"

    return df
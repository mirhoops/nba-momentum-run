"""각 이벤트에 포제션 번호와 공격기회 번호를 부여한다.

PBP는 이벤트 나열일 뿐 '포제션' 단위가 없다. 우리가 만들어야 한다.

두 축을 만드는 이유
  possNum   : 소유권 단위. 공격 리바운드로 늘지 않는다.
  chanceNum : 슛 기회 단위. 공격 리바운드마다 +1.
"""
import pandas as pd


def is_last_freethrow(sub_type) -> bool:
    """'2 of 2' → True, '1 of 2' → False

    데이터에 'shot', 빈 문자열 등 예외값이 섞여 있어 방어한다.
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

    made_fg = a.isin(["2pt", "3pt"]) & (r == "Made")
    def_reb = (a == "rebound") & (s == "defensive")
    turnover = a == "turnover"        # steal은 같은 사건의 반대편이라 세지 않음
    period_end = (a == "period") & (s == "end")
    last_ft = (a == "freethrow") & (r == "Made") & s.map(is_last_freethrow)

    # 앤드원 제외: 야투 성공으로 이미 포제션이 끝났는데
    # 보너스 자유투를 또 종료로 세면 한 포제션을 두 번 센다.
    # 실제 데이터에서 2,851건(2024-25) 확인.
    made_back = (a.shift(2).isin(["2pt", "3pt"]) & (r.shift(2) == "Made")) | \
                (a.shift(1).isin(["2pt", "3pt"]) & (r.shift(1) == "Made"))
    and1 = (a == "freethrow") & (s == "1 of 1") & made_back

    return made_fg | def_reb | turnover | period_end | (last_ft & ~and1)

def parse_possessions(df: pd.DataFrame) -> pd.DataFrame:
    """포제션·공격기회 번호를 부여한 새 DataFrame을 돌려준다.

    반드시 loader.load_season()으로 정렬된 데이터를 넣어야 한다.
    """
    df = df.copy()
    df["isPossEnd"] = mark_possession_end(df)

    # 종료 이벤트 '다음' 행부터 새 번호가 시작되므로 shift(1)로 한 칸 민다.
    # cumsum()은 True를 1로 세어 누적합을 낸다 → 자동 일련번호.
    g = df.groupby("gameId")["isPossEnd"]
    df["possNum"] = g.transform(lambda x: x.shift(1, fill_value=False).cumsum())

    # 공격기회: 포제션이 바뀌거나 공격 리바운드가 나오면 +1
    oreb = (df["actionType"] == "rebound") & (df["subType"] == "offensive")
    new_chance = g.shift(1, fill_value=False) | oreb
    df["chanceNum"] = new_chance.groupby(df["gameId"]).cumsum()

    # 버저비터 던지기는 성공률 3% 미만. 일반 슛과 섞으면
    # 쿼터 마지막 포제션 효율이 인위적으로 깎인다.
    df["isHeave"] = df["actionType"] == "heave"
    return df
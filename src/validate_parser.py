"""자체 파서를 NBA 공식 possession 컬럼과 대조 검증한다.

'남이 준 라벨을 그냥 믿지 않았다'는 것이 이 프로젝트의 방법론적 기여다.
불일치율과 그 원인 유형이 논문 방법론 챕터의 핵심 표가 된다.
"""
import pandas as pd
from loader import load_season
from possession_parser import parse_possessions

df = parse_possessions(load_season("2024-25"))

# 정규시즌만. 플레이오프는 페이스가 달라 기준값 비교가 어긋난다.
df = df[df["gameCategory"] == "regular"]

# [1] 경기별 포제션 수 — 자체 파서
mine = df.groupby("gameId")["possNum"].max()

# [2] 경기별 포제션 수 — NBA possession 컬럼의 값 변화 횟수
def count_changes(s):
    s = s[s.notna() & (s != "0")]
    return (s != s.shift()).sum()

nba = df.groupby("gameId")["possession"].apply(count_changes)

cmp = pd.DataFrame({"자체파서": mine, "NBA컬럼": nba}).dropna()
cmp["차이"] = cmp["자체파서"] - cmp["NBA컬럼"]

print(f"검증 경기수 {len(cmp):,}\n")
print(f"  자체 파서   경기당 {cmp['자체파서'].mean():.1f}  (팀당 {cmp['자체파서'].mean()/2:.1f})")
print(f"  NBA 컬럼    경기당 {cmp['NBA컬럼'].mean():.1f}  (팀당 {cmp['NBA컬럼'].mean()/2:.1f})")
print(f"  리그 실측 Pace 참조값: 팀당 약 98~100\n")
print(f"  차이 평균 {cmp['차이'].mean():+.2f} / 표준편차 {cmp['차이'].std():.2f}")
print(f"  완전 일치 경기 {(cmp['차이'] == 0).mean() * 100:.1f}%")
print(f"  ±2 이내 경기 {(cmp['차이'].abs() <= 2).mean() * 100:.1f}%")
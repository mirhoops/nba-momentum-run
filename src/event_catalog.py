"""v3 6시즌의 이벤트 종류를 전수 조사한다.

파서를 쓰기 전에 '무엇을 처리해야 하는지' 목록을 확보해야 한다.
상상으로 규칙을 짜면 반드시 빠뜨린다.
"""
import pandas as pd
from loader import load_season

V3_SEASONS = ["2020-21", "2021-22", "2022-23",
              "2023-24", "2024-25", "2025-26"]

frames = []
for s in V3_SEASONS:
    df = load_season(s)
    # 필요한 컬럼만 남긴다. 6시즌 전체를 통째로 들고 있으면 메모리가 힘들다.
    frames.append(df[["actionType", "subType", "shotResult"]])
    print(f"  {s} 로드 완료", end="\r")

all_df = pd.concat(frames, ignore_index=True)
print(f"\n총 {len(all_df):,}개 이벤트\n")

# [1] 대분류 빈도. 파서가 다뤄야 할 이벤트의 전체 지도.
print("=== actionType 분포 ===")
print(all_df["actionType"].value_counts().to_string())

# [2] 리바운드 세부 — 공/수 구분이 포제션 판정의 핵심
print("\n=== rebound subType ===")
reb = all_df[all_df["actionType"] == "rebound"]
print(reb["subType"].value_counts(dropna=False).to_string())

# [3] 자유투 세부 — '몇 번째 중 몇 번째'인지가 종료 판정을 가른다
print("\n=== freethrow subType ===")
ft = all_df[all_df["actionType"] == "freethrow"]
print(ft["subType"].value_counts(dropna=False).head(15).to_string())

# [4] 타임아웃 세부 — 개입 분석의 처치 변수
print("\n=== timeout subType ===")
to = all_df[all_df["actionType"] == "timeout"]
print(to["subType"].value_counts(dropna=False).to_string())
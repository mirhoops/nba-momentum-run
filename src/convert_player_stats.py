"""445MB xlsx를 parquet으로 1회 변환한다.

xlsx는 압축 해제 시 2.87GB이고 Excel 행 한계(1,048,576)에 근접해 있다.
pd.read_excel()은 전체를 메모리에 올려 수십 분이 걸리므로,
openpyxl의 read_only 모드로 한 줄씩 흘려 읽는다.
"""
import openpyxl
import pandas as pd
from datetime import timedelta  
from config import PROJECT_ROOT

SRC = PROJECT_ROOT / "data" / "master" / "PlayerStatisticsExtended.xlsx"
OUT = PROJECT_ROOT / "data" / "master" / "PlayerStats.parquet"

# 라인업 복원과 검증에 필요한 컬럼만 추린다. 110개를 다 들고 있을 이유가 없다.
KEEP = [
    "gameId", "personId", "firstName", "lastName",
    "playerteamId", "opponentteamId", "home", "win", "gameType",
    "startingPosition",      # 'G'/'F'/'C' = 선발, 빈칸 = 벤치
    "numMinutes", "points", "plusMinusPoints",
    "possessions",           # NBA 공식 선수별 포제션 → 파서 검증용
    "pointsInPaint", "pointsFastBreak",
    "pointsOffTurnovers", "pointsSecondChance",
    "offensiveRating", "defensiveRating", "usagePercentage", "pace",
]
def convert():
    # read_only=True 가 핵심. 파일 전체가 아니라 한 행씩 스트리밍한다.
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    ws = wb.active

    rows = ws.iter_rows(values_only=True)   # 값만 꺼낸다(서식 무시 → 빠름)
    header = list(next(rows))               # 첫 행이 컬럼명

    # 필요한 컬럼이 몇 번째에 있는지 위치를 미리 찾아둔다
    idx = [header.index(c) for c in KEEP]

    data = []
    for i, r in enumerate(rows, 1):
        data.append([r[j] for j in idx])
        if i % 100000 == 0:
            print(f"  {i:,}행 처리", end="\r")

    wb.close()

    df = pd.DataFrame(data, columns=KEEP)
    df["gameId"] = df["gameId"].astype(str).str.zfill(10)   # PBP와 자릿수 통일

    # openpyxl이 셀 서식을 보고 numMinutes를 timedelta로 변환해버린다.
    # parquet은 이 타입을 숫자 컬럼에 못 넣으므로 '분' 단위 실수로 되돌린다.
    def to_minutes(v):
        if isinstance(v, timedelta):
            return v.total_seconds() / 60
        return v

    df["numMinutes"] = df["numMinutes"].map(to_minutes)

    # 나머지 수치 컬럼도 안전하게 숫자로 강제 변환한다.
    # errors="coerce" = 변환 실패한 값은 에러 대신 결측(NaN) 처리
    num_cols = [c for c in KEEP if c not in
                ("gameId", "personId", "firstName", "lastName",
                 "playerteamId", "opponentteamId", "gameType", "startingPosition")]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df.to_parquet(OUT, compression="snappy", index=False)
    return df

if __name__ == "__main__":
    df = convert()
    print(f"\n\n{len(df):,}행 저장 완료 → {OUT.name}")
    print(f"용량: {OUT.stat().st_size / 1e6:.0f} MB")
    print(f"\n선발 표시: {df['startingPosition'].notna().sum():,}행")
    print(f"경기 수: {df['gameId'].nunique():,}")
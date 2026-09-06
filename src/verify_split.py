"""분할 결과가 원본과 일치하는지, 빠진 시즌이 없는지 검증한다."""
import pyarrow.parquet as pq
from config import MASTER_FILE, RAW_DIR, GAME_TYPE_MAP

master_rows = pq.ParquetFile(MASTER_FILE).metadata.num_rows
files = sorted(RAW_DIR.glob("PlayByPlay_Season_*.parquet"))

print(f"{'시즌':<10}{'행수':>11}{'경기':>7}{'정규':>7}{'플옵':>6}{'MB':>7}")
print("-" * 50)

total = 0
seasons = []
for f in files:
    # gameId 컬럼만 읽는다. Parquet은 열 단위 저장이라 필요한 열만 골라 읽을 수 있다.
    gids = pq.read_table(f, columns=["gameId"]).column("gameId").to_pylist()
    n = len(gids)
    total += n

    # 중복 제거해 실제 경기 수를 세고, 종류별로 나눈다
    uniq = {str(g).zfill(10) for g in gids}
    kind = lambda k: sum(1 for g in uniq if GAME_TYPE_MAP.get(g[2]) == k)

    label = f.stem.replace("PlayByPlay_Season_", "")
    seasons.append(label)
    print(f"{label:<10}{n:>11,}{len(uniq):>7}{kind('regular'):>7}"
          f"{kind('playoff'):>6}{f.stat().st_size / 1e6:>7.0f}")

print("-" * 50)
print(f"분할 합계 {total:,} / 원본 {master_rows:,}  "
      f"→ {'✅ 일치' if total == master_rows else f'❌ {master_rows - total:,}행 손실'}")

# 시즌이 연속인지 확인. 24-25처럼 중간이 비면 여기서 잡힌다.
years = sorted(int(s[:4]) for s in seasons)
gaps = [y for y in range(years[0], years[-1] + 1) if y not in years]
print(f"시즌 범위 {years[0]}~{years[-1]}  "
      f"→ {'✅ 연속' if not gaps else f'❌ 누락: {gaps}'}")
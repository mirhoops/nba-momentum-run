"""원본 통합 파일을 '읽지 않고' 정찰한다.

Parquet은 파일 끝에 요약 정보(메타데이터)를 따로 갖고 있다.
그것만 읽으면 889MB를 통째로 열지 않고도 1초 만에 규모를 파악할 수 있다.
"""
import pyarrow.parquet as pq
from config import MASTER_FILE, season_label

pf = pq.ParquetFile(MASTER_FILE)
md = pf.metadata

print("=" * 55)
print(f"파일 크기 : {MASTER_FILE.stat().st_size / 1e9:.2f} GB")
print(f"총 행수   : {md.num_rows:,}")
print(f"컬럼 수   : {md.num_columns}")
print(f"row group : {md.num_row_groups}개")   # 분할 처리의 단위가 된다
print("=" * 55)

# [1] gameId가 문자열인지 정수인지 확인. 이걸 모르고 자르면 결과가 깨진다.
print(f"\ngameId 타입: {pf.schema_arrow.field('gameId').type}")

# [2] 첫 row group에서 gameId만 뽑아 시즌 변환이 제대로 되는지 눈으로 검증
sample = pf.read_row_group(0, columns=["gameId"]).column("gameId").to_pylist()[:8]
print("\ngameId 샘플 → 시즌 변환 결과")
for g in sample:
    print(f"  {str(g):>12s}  ->  {season_label(g)}")

# [3] 전체 컬럼 목록
print("\n[컬럼 목록]")
for i, n in enumerate(pf.schema_arrow.names):
    print(f"  {i:2d}. {n}")
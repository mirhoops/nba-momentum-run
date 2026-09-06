"""통합 원본을 시즌별 Parquet으로 분할한다.

핵심 설계 2가지
 (1) 날짜가 아니라 gameId로 자른다.
     시즌 정보가 ID에 박혀 있으므로 경계 실수가 불가능하다.
 (2) 파일을 통째로 메모리에 올리지 않는다.
     row group(1개당 약 5만 행) 단위로 읽어 곧바로 시즌 파일에 흘려보낸다.
     → 원본이 889MB여도 램은 수백 MB만 쓴다.
"""
import pyarrow as pa
import pyarrow.parquet as pq
from config import MASTER_FILE, RAW_DIR, season_label


def split_by_season():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    pf = pq.ParquetFile(MASTER_FILE)

    writers = {}    # 시즌 -> 열려 있는 출력 파일
    counts = {}     # 시즌 -> 누적 행수
    unknown = 0     # 시즌 판정 실패 행수. 조용히 사라지면 안 되므로 센다.

    for i in range(pf.num_row_groups):
        tbl = pf.read_row_group(i)                    # 한 덩어리만 메모리에 로드

        # [1] 이 덩어리 안 모든 행의 시즌 라벨을 계산
        labels = [season_label(g) for g in tbl.column("gameId").to_pylist()]
        unknown += sum(1 for s in labels if s is None)

        # [2] 이 덩어리에 등장한 시즌만 골라 각자의 파일에 추가
        for season in sorted({s for s in labels if s}):
            mask = pa.array([s == season for s in labels])   # True/False 목록
            part = tbl.filter(mask)                          # 해당 시즌 행만 추출

            # 처음 만나는 시즌이면 새 파일을 열어둔다
            if season not in writers:
                path = RAW_DIR / f"PlayByPlay_Season_{season}.parquet"
                writers[season] = pq.ParquetWriter(path, tbl.schema,
                                                   compression="snappy")
                counts[season] = 0

            writers[season].write_table(part)
            counts[season] += part.num_rows

        print(f"  진행 {i + 1}/{pf.num_row_groups} row group", end="\r")

    # [3] 열어둔 파일을 모두 닫는다. 안 닫으면 파일이 손상된 채로 남는다.
    for w in writers.values():
        w.close()

    return counts, unknown


if __name__ == "__main__":
    counts, unknown = split_by_season()

    print(f"\n\n총 {len(counts)}개 시즌 생성 완료")
    if unknown:
        print(f"⚠️  시즌 판정 실패 {unknown:,}행 (gameId 형식 이상)")
    print()
    for s in sorted(counts):
        print(f"  {s}   {counts[s]:>10,} 행")
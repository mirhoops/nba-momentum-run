"""각 시즌 파일의 '실제 채움 상태'를 스캔해 데이터 포맷 세대를 판정한다.

30시즌 모두 컬럼은 89개로 동일하다. 하지만 값이 들어 있느냐는 다르다.
캐글 배포본이 서로 다른 두 API(구형 stats.nba.com / 신형 CDN liveData)를
하나의 스키마로 합쳐놓았기 때문이다.
따라서 '컬럼이 있느냐'가 아니라 '값이 채워졌느냐'를 봐야 한다.
"""
import pyarrow.parquet as pq
import pandas as pd
from config import RAW_DIR

# 포맷 세대를 가르는 결정적 컬럼. 하나라도 비면 하위 분석 설계가 통째로 바뀐다.
PROBE = [
    "possession",    # 포제션 소유팀 → 없으면 직접 파싱해야 함
    "timeActual",    # 실제 벽시계  → 없으면 타임아웃 지속시간 IV 불가
    "x",             # 슛 좌표      → 없으면 코너3 구분 불가
    "descriptor",    # 슛 세부유형
    "shotDistance",  # 슛 거리      → 좌표의 대체재
    "subType",       # 리바운드 공/수 구분이 여기 담긴다
]


def read_sample(pf, cols, min_rows=20000):
    """행이 충분히 모일 때까지 row group을 이어 읽는다.

    시즌 경계에 걸린 첫 덩어리가 수백 행뿐일 수 있어서,
    첫 row group만 읽으면 판정이 흔들린다.
    """
    frames, n = [], 0
    for i in range(pf.num_row_groups):
        t = pf.read_row_group(i, columns=cols).to_pandas()
        frames.append(t)
        n += len(t)
        if n >= min_rows:
            break
    return pd.concat(frames, ignore_index=True)


def probe(path):
    pf = pq.ParquetFile(path)
    df = read_sample(pf, PROBE + ["actionType"])

    row = {"시즌": path.stem.replace("PlayByPlay_Season_", "")}

    # [1] 채움률(%). 문자열 컬럼은 빈 문자열('')도 결측으로 봐야 한다.
    for c in PROBE:
        filled = df[c].notna() & (df[c].astype(str).str.strip() != "")
        row[c] = f"{filled.mean() * 100:.0f}"

    # [2] 세대 판정: v3는 '2pt'/'3pt', v2는 'Made Shot'/'Missed Shot'
    kinds = set(df["actionType"].dropna().astype(str))
    row["세대"] = "v3" if {"2pt", "3pt"} & kinds else "v2"

    # [3] 리바운드 공/수 구분 가능 여부 — 포제션 파싱의 핵심 재료
    is_reb = df["actionType"].astype(str).str.lower().str.contains("rebound", na=False)
    subs = set(df.loc[is_reb, "subType"].dropna().astype(str).str.lower())
    row["리바운드"] = "공/수OK" if {"offensive", "defensive"} & subs else "구분없음"

    return row


if __name__ == "__main__":
    files = sorted(RAW_DIR.glob("PlayByPlay_Season_*.parquet"))
    print(f"스캔 대상 {len(files)}개 시즌\n")
    print(pd.DataFrame([probe(f) for f in files]).to_string(index=False))
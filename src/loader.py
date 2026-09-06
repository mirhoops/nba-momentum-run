"""시즌 파일을 '분석 가능한 상태'로 정규화해 불러온다.

이 프로젝트의 모든 분석은 반드시 이 함수를 거친다.
정렬·필터를 매번 따로 하면 언젠가 빼먹고, 그때는 에러도 안 난다.
"""
import numpy as np
import pandas as pd
from config import RAW_DIR, GAME_TYPE_MAP, ANALYSIS_TYPES

REGULATION_SEC, OVERTIME_SEC = 720, 300   # 정규 쿼터 12분, 연장 5분


def load_season(season: str, filter_types: bool = True) -> pd.DataFrame:
    """season 예시: '2023-24'"""
    df = pd.read_parquet(RAW_DIR / f"PlayByPlay_Season_{season}.parquet")

    # [1] gameId를 10자리로 통일. 원본은 앞의 0이 잘려 8자리다.
    df["gameId"] = df["gameId"].astype(str).str.zfill(10)
    df["gameCategory"] = df["gameId"].str[2].map(GAME_TYPE_MAP)

    # [2] ★최중요★ 정렬. 파일의 행 순서는 경기 진행 순서가 아니다.
    #     (앞서 178경기 중 176경기에서 불일치 확인)
    #     mergesort = 안정 정렬. 값이 같을 때 원래 순서를 보존한다.
    #     자유투 '1 of 2'와 '2 of 2'처럼 동시각 이벤트의 순서를 지키려면 필수.
    df = df.sort_values(["gameId", "orderNumber"], kind="mergesort").reset_index(drop=True)

    # [3] 프리시즌·올스타 제거. 런의 조작적 정의를 오염시키는 주범.
    if filter_types:
        df = df[df["gameCategory"].isin(ANALYSIS_TYPES)].reset_index(drop=True)

    return _add_time_axis(df)


def _add_time_axis(df: pd.DataFrame) -> pd.DataFrame:
    """문자열 시계('PT11M37.00S')를 수치 시간축으로 변환한다."""
    # [4] 정규식으로 분·초를 한 번에 추출. 반복문보다 수십 배 빠르다.
    t = df["clock"].str.extract(r"PT(\d+)M([\d.]+)S")
    df["clockSec"] = t[0].astype(float) * 60 + t[1].astype(float)   # 쿼터 잔여 초

    # [5] 경기 시작부터의 누적 경과 초. 쿼터를 넘나드는 '런' 추적에 필수.
    per = df["period"]
    prior = np.where(per <= 4, (per - 1) * REGULATION_SEC,
                     4 * REGULATION_SEC + (per - 5) * OVERTIME_SEC)
    length = np.where(per <= 4, REGULATION_SEC, OVERTIME_SEC)
    df["gameSec"] = prior + (length - df["clockSec"])

        # [6] 벽시계 시각. 타임아웃 실제 지속시간 → 의무/팀 타임아웃 판별에 사용.
    df["timeActual"] = pd.to_datetime(df["timeActual"], utc=True, errors="coerce")

    # [7] 경기 날짜. 문자열과 결측이 섞여 있어 그대로 두면 대소 비교가 불가능하다.
    #     errors="coerce" = 변환 실패한 값은 에러 대신 NaT(결측)로 처리
    df["gameDate"] = pd.to_datetime(df["gameDateTimeEst"], errors="coerce").dt.tz_localize(None)
    return df
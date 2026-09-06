"""프로젝트 전역 설정. 경로와 상수를 한 곳에 모아 하드코딩을 방지한다."""
from pathlib import Path
from typing import Optional          # Python 3.9 호환

# __file__ = 이 파일 위치(src/config.py), parents[1] = 프로젝트 루트
# 절대경로를 코드에 박으면 다른 컴퓨터에서 안 돌아간다. 상대적으로 계산한다.
PROJECT_ROOT  = Path(__file__).resolve().parents[1]
MASTER_FILE   = PROJECT_ROOT / "data" / "master" / "PlayByPlay.parquet"
RAW_DIR       = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# gameId 3번째 자리 = 경기 종류
GAME_TYPE_MAP = {
    "1": "preseason",   # 프리시즌: 로테이션 비정상 → 분석 제외
    "2": "regular",
    "3": "allstar",     # 올스타: 수비 부재 → 가짜 런 양산, 반드시 제외
    "4": "playoff",
    "5": "playin",
    "6": "cupfinal",
}
ANALYSIS_TYPES = {"regular", "playoff", "playin"}


def season_label(game_id) -> Optional[str]:
    """gameId에서 시즌 라벨을 뽑는다.  '0029600001' -> '1996-97'

    날짜가 아니라 ID로 시즌을 판정하므로 경계 오류가 원천 차단된다.
    (날짜 컷은 매년 개막일이 달라 한 시즌이 통째로 누락될 수 있다)
    """
    gid = str(game_id).strip().zfill(10)   # 앞의 0이 잘린 파일 대비
    yy = gid[3:5]                          # 4~5번째 자리 = 시즌 시작연도 뒤 2자리
    if not yy.isdigit():
        return None                        # 형식이 깨진 행은 건너뛴다

    yy = int(yy)
    # NBA는 1946-47이 원년. 46 이상이면 1900년대, 미만이면 2000년대.
    start = 1900 + yy if yy >= 46 else 2000 + yy
    # 1999 -> '1999-00' 이 되도록 두 자리 0채움
    return f"{start}-{(start + 1) % 100:02d}"
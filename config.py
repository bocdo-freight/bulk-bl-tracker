import os

# v1.8 - Final Production Grade Configuration

# 1. 선사별 프리픽스 및 TrackingMore 표준 코드 매핑
CARRIER_MAP = {
    "HMCU": "hmm",
    "MAEU": "maersk",
    "ONEY": "one",
    "OOLU": "oocl",
    "COSU": "cosco",
    "EMCU": "evergreen"
}

# 2. API 타임아웃 및 재시도 설정
API_TIMEOUT = 5.0  # 실제 requests 호출 시 5초 타임아웃 적용
MAX_RETRIES = 3    # 실패 시 최대 3번 재시도

# 3. 챗GPT 피드백 버그 2위 해결: 함수형 환경변수 로딩 (임포트 시점 꼬임 방지)
def get_trackingmore_key():
    """
    app.py에서 뒤늦게 세팅한 환경변수도 실시간으로 완벽하게 읽어오도록 보장합니다.
    """
    return os.getenv("TRACKINGMORE_API_KEY", "MOCK_KEY_FOR_NOW")
import os

ACTIVE_PROVIDER = os.getenv("ACTIVE_PROVIDER", "trackingmore")

# 🚀 각 선사별 TrackingMore 표준 코드 최적화 (이대로 복사하세요)
CARRIER_MAP = {
    "HMCU": "hyundai",
    "HDMU": "hyundai",
    "MAEU": "maersk",
    "ONEY": "one-line",
    "COSU": "cosco",
    "EMCU": "evergreen",
    "EGLV": "evergreen",
    "MSCU": "msc",
    "MEDU": "msc",
    "OOLU": "oocl",
    "CMAU": "cma-cgm",
    "APLU": "apl",
    "YMLU": "yang-ming",
    "WHLC": "wan-hai"
}

API_TIMEOUT = 15.0  # 시간 여유 추가
MAX_RETRIES = 3    

def get_trackingmore_key():
    return os.getenv("TRACKINGMORE_API_KEY", "")
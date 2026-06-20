import os

ACTIVE_PROVIDER = os.getenv("ACTIVE_PROVIDER", "trackingmore")

# 🚀 TrackingMore API 실전 표준 Courier Code로 100% 수정
CARRIER_MAP = {
    # ONE: one-line (정확히 확인됨)
    "ONEY": "one-line",
    # HMM: hmm (hyundai가 아니라 hmm으로 변경 시도)
    "HMCU": "hmm",
    "HDMU": "hmm",
    # MAERSK
    "MAEU": "maersk",
    # COSCO
    "COSU": "cosco",
    # EVERGREEN
    "EMCU": "evergreen",
    "EGLV": "evergreen",
    # MSC
    "MSCU": "msc",
    "MEDU": "msc",
    # OOCL
    "OOLU": "oocl",
    # CMA CGM
    "CMAU": "cma-cgm",
    # APL
    "APLU": "apl",
    # YANG MING
    "YMLU": "yang-ming",
    # WAN HAI
    "WHLC": "wanhai"
}

API_TIMEOUT = 20.0  
MAX_RETRIES = 3    

def get_trackingmore_key():
    return os.getenv("TRACKINGMORE_API_KEY", "")
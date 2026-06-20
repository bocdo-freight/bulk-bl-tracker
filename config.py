import os

# 선사 코드 매핑 (TrackingMore 공식 표준)
CARRIER_MAP = {
    "ONEY": "one-line",
    "HMCU": "hmm",
    "HDMU": "hmm",
    "MAEU": "maersk",
    "COSU": "cosco",
    "EMCU": "evergreen",
    "EGLV": "evergreen",
    "MSCU": "msc",
    "MEDU": "msc",
    "OOLU": "oocl",
    "CMAU": "cma-cgm",
    "APLU": "apl",
    "YMLU": "yangming",
    "WHLC": "wanhai"
}

def get_trackingmore_key():
    return os.getenv("TRACKINGMORE_API_KEY", "")
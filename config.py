import os

# TrackingMore API 표준 Courier Code (최신 버전)
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

API_TIMEOUT = 20.0
MAX_RETRIES = 3

def get_trackingmore_key():
    return os.getenv("TRACKINGMORE_API_KEY", "")
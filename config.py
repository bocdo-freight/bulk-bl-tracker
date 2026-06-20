import os

# v1.95 - Final Enterprise Waterproof Configuration

# 1. 챗GPT 5위 피드백 반영: 클라우드 환경변수에서 공급자를 실시간으로 제어 가능하도록 확장
ACTIVE_PROVIDER = os.getenv("ACTIVE_PROVIDER", "trackingmore")

# 2. 실무용 주요 선사 프리픽스 마스터 맵
# (챗GPT 6위 조언대로 실제 TrackingMore 연동 시 문서의 정식 courier_code와 대조하여 미세조정 가능)
CARRIER_MAP = {
    "HMCU": "hmm",
    "MAEU": "maersk",
    "ONEY": "one",
    "OOLU": "oocl",
    "COSU": "cosco",
    "EMCU": "evergreen",
    "MSCU": "msc",        
    "CMAU": "cma-cgm",    
    "APLU": "apl",        
    "YMLU": "yang-ming",  
    "HDMU": "hmm",        
    "WHLC": "wan-hai"     
}

# 3. API 인프라 세팅
API_TIMEOUT = 5.0  
MAX_RETRIES = 3    

# 4. 환경변수 안전 로딩 함수
def get_trackingmore_key():
    return os.getenv("TRACKINGMORE_API_KEY", "MOCK_KEY_FOR_NOW")
import time
from datetime import datetime

# 선사 prefix 맵
CARRIER_MAP = {
    "HMCU": "HMM",
    "MAEU": "MAERSK",
    "ONEY": "ONE",
    "COSU": "COSCO",
    "EMCU": "EMC",
    "OOLU": "OOCL",
    "HLCU": "HAPAG"
}

# Mock 데이터 구조 (추후 실제 API 연동 시 이 데이터 포맷 그대로 결과만 치환)
TRACKING_SAMPLE = {
    "HMM": {"status": "On Board", "eta": "2026-07-10", "pol": "JAKARTA", "pod": "ROTTERDAM", "vessel": "HMM RAON"},
    "MAERSK": {"status": "Delay", "eta": "2026-07-15", "pol": "SHANGHAI", "pod": "HAMBURG", "vessel": "MAERSK MC-KINNEY"},
    "ONE": {"status": "On Schedule", "eta": "2026-07-22", "pol": "BUSAN", "pod": "GENOVA", "vessel": "ONE OLYMPUS"},
    "UNKNOWN": {"status": "Failed", "eta": "N/A", "pol": "N/A", "pod": "N/A", "vessel": "N/A"}
}

def detect_carrier(bl_number):
    """B/L 번호 prefix로 선사 자동 인식"""
    prefix = str(bl_number).strip().upper()[:4]
    return CARRIER_MAP.get(prefix, "UNKNOWN")

# GPT Pick: 추후 실제 API 연동을 위해 bl_number 인자를 미리 설계에 반영
def fetch_tracking_data(bl_number, carrier):
    """현재는 Mock 데이터를 반환, 추후 실제 API 호출 코드로 이 내부만 교체"""
    time.sleep(0.3)  # 실제 API 조회 UX 체감을 위한 딜레이
    return TRACKING_SAMPLE.get(carrier, TRACKING_SAMPLE["UNKNOWN"])
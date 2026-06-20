import time
import logging
from config import CARRIER_MAP, API_TIMEOUT, MAX_RETRIES
from provider import get_provider

logger = logging.getLogger(__name__)

def detect_carrier(bl_number):
    prefix = str(bl_number)[:4].upper()
    return CARRIER_MAP.get(prefix, "UNKNOWN")

def track_bulk_bl(bl_list, progress_callback=None):
    results = []
    provider = get_provider()
    total_bl = len(bl_list)
    
    for index, bl in enumerate(bl_list):
        carrier_code = detect_carrier(bl)
        
        # UI 업데이트
        if progress_callback:
            progress_callback(index + 1, total_bl)
            
        # ⚠️ 조회 간격 2.5초로 여유 확보 (API 429 에러 완벽 차단)
        time.sleep(2.5) 
            
        if carrier_code == "UNKNOWN":
            results.append({"B/L Number": bl, "Carrier": "UNKNOWN", "Status": "Failed", "Remarks": "Carrier mapping missing"})
            continue
            
        tracking_request = {"bl_number": bl, "carrier_code": carrier_code}
        
        result_object = None
        for attempt in range(MAX_RETRIES):
            try:
                result_object = provider.fetch_data(tracking_request, timeout=API_TIMEOUT)
                if result_object and result_object.status != "Error":
                    break
            except Exception as e:
                time.sleep(5.0) # 재시도 시 대기시간 연장
                    
        if result_object:
            results.append({
                "B/L Number": bl,
                "Carrier": carrier_code.upper(),
                "Status": result_object.status,
                "POL": result_object.pol,
                "ETD": result_object.etd,
                "POD": result_object.pod,
                "ETA": result_object.eta,
                "Remarks": result_object.remarks
            })
        else:
            results.append({"B/L Number": bl, "Carrier": carrier_code.upper(), "Status": "Failed", "Remarks": "API Connection Timeout"})
            
    return results
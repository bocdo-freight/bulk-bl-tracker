import time
import logging
import os
from logging.handlers import RotatingFileHandler  # 👈 챗GPT 4위 피드백 반영
from config import CARRIER_MAP, API_TIMEOUT, MAX_RETRIES
from provider import get_provider, TrackingResult

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    os.makedirs("logs", exist_ok=True)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # ❌ 챗GPT 4위 피드백 적극 반영: 10MB 단위로 로그 파일을 자동 분할 관리하는 고급 로깅 기법 탑재
    file_handler = RotatingFileHandler(
        "logs/tracking.log", 
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,               # 최대 5개까지 백업 로테이션 (.log.1, .log.2 ...)
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def detect_carrier(bl_number):
    if not bl_number or len(str(bl_number)) < 4:
        return "UNKNOWN"
    prefix = str(bl_number)[:4].upper()
    return CARRIER_MAP.get(prefix, "UNKNOWN")

def track_bulk_bl(bl_list, progress_callback=None):
    results = []
    provider = get_provider() 
    total_bl = len(bl_list)
    
    for index, bl in enumerate(bl_list):
        carrier_code = detect_carrier(bl)
        
        if progress_callback:
            progress_callback(index + 1, total_bl)
            
        if carrier_code == "UNKNOWN":
            error_msg = "Carrier not supported. Please verify B/L number."
            logger.warning(f"BL: {bl} | Evaluation: {error_msg}")
            results.append({
                "B/L Number": bl, "Carrier": "UNKNOWN", "Status": "Failed",
                "POL": "N/A", "ETD": "N/A", "POD": "N/A", "ETA": "N/A", "Remarks": error_msg
            })
            continue
            
        tracking_request = {
            "bl_number": bl,
            "carrier_code": carrier_code
        }
        
        result_object = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result_object = provider.fetch_data(tracking_request, timeout=API_TIMEOUT)
                if result_object and result_object.status != "Error":
                    break
            except Exception as e:
                logger.error(f"Network exception on BL {bl} (Attempt {attempt}/{MAX_RETRIES}): {str(e)}")
                if attempt < MAX_RETRIES:
                    time.sleep(0.5)
                    
        if result_object:
            logger.info(f"TRACKING REPORTED | BL: {bl} | Carrier: {carrier_code.upper()} | Status: {result_object.status}")
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
            fail_reason = "API Critical Timeout or Provider Server down."
            logger.error(f"FINAL SYSTEM CRITICAL FAILURE | BL: {bl} | Reason: {fail_reason}")
            results.append({
                "B/L Number": bl, "Carrier": carrier_code.upper(), "Status": "Not Found",
                "POL": "N/A", "ETD": "N/A", "POD": "N/A", "ETA": "N/A", "Remarks": fail_reason
            })
            
    return results
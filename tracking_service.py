import time
import logging
import os
from logging.handlers import RotatingFileHandler
from config import CARRIER_MAP, API_TIMEOUT, MAX_RETRIES
from provider import get_provider, TrackingResult

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    os.makedirs("logs", exist_ok=True)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    file_handler = RotatingFileHandler(
        "logs/tracking.log", 
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
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

# 🚨 에러의 원인이었던 progress_callback을 완벽하게 수신하는 부분!
def track_bulk_bl(bl_list, progress_callback=None):
    results = []
    provider = get_provider() 
    total_bl = len(bl_list)
    
    for index, bl in enumerate(bl_list):
        carrier_code = detect_carrier(bl)
        
        # UI로 진행률(%)을 쏴주는 역할
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
import time
import logging
from config import CARRIER_MAP, API_TIMEOUT, MAX_RETRIES
from provider import get_provider

# 챗GPT 피드백 버그 5위 해결: 모듈 전용 독립 로거 선언 (운영 표준 구조)
logger = logging.getLogger(__name__)

def detect_carrier(bl_number):
    if not bl_number or len(str(bl_number)) < 4:
        return "UNKNOWN"
    prefix = str(bl_number)[:4].upper()
    return CARRIER_MAP.get(prefix, "UNKNOWN")

def track_bulk_bl(bl_list, progress_callback=None):
    results = []
    # 팩토리 함수 인터페이스 확장 반영
    provider = get_provider("trackingmore")
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
        
        api_data = None
        # 챗GPT 피드백 버그 4위 반영 준비: 실제 연동 시 구체적 네트워크 예외 처리 공간 세팅
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # 타임아웃을 안전하게 공급자 엔진에 전달
                api_data = provider.fetch_data(tracking_request, timeout=API_TIMEOUT)
                if api_data:
                    break
            except KeyError as ke:
                logger.error(f"Data parsing error on BL {bl} (Attempt {attempt}): {str(ke)}")
                break
            except Exception as e:
                # [Phase 2 실제 연동 시 requests.exceptions.Timeout 등으로 확장]
                logger.error(f"Network error on BL {bl} (Attempt {attempt}/{MAX_RETRIES}): {str(e)}")
                if attempt < MAX_RETRIES:
                    time.sleep(0.5)
                    
        if api_data:
            logger.info(f"SUCCESS | BL: {bl} | Carrier: {carrier_code.upper()}")
            
            # 🚨 챗GPT가 찾아낸 1순위 치명적 오타 버그 깔끔하게 수술 완료! 🚨
            results.append({
                "B/L Number": bl, 
                "Carrier": carrier_code.upper(), 
                "Status": api_data["status"],
                "POL": api_data["pol"],    # 👈 따옴표 중복 에러 완전 진압!
                "ETD": api_data["etd"], 
                "POD": api_data["pod"], 
                "ETA": api_data["eta"],
                "Remarks": "Successfully fetched via API"
            })
        else:
            fail_reason = "API Timeout or Carrier Server maintenance."
            logger.error(f"FINAL CRITICAL FAILURE | BL: {bl} | Reason: {fail_reason}")
            results.append({
                "B/L Number": bl, "Carrier": carrier_code.upper(), "Status": "Not Found",
                "POL": "N/A", "ETD": "N/A", "POD": "N/A", "ETA": "N/A", "Remarks": fail_reason
            })
            
    return results
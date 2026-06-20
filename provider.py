from dataclasses import dataclass
from abc import ABC, abstractmethod
import requests  # 👈 드디어 진짜 인터넷 통신 모듈 등장!
from config import get_trackingmore_key, ACTIVE_PROVIDER

@dataclass
class TrackingResult:
    status: str
    pol: str
    etd: str
    pod: str
    eta: str
    vessel: str
    remarks: str

class BaseProvider(ABC):
    @abstractmethod
    def fetch_data(self, tracking_request, timeout=5.0) -> TrackingResult:
        pass

class TrackingMoreProvider(BaseProvider):
    """
    TrackingMore 진짜 실시간 API 공급자 (Phase 2 가동)
    """
    def __init__(self):
        self.base_url = "https://api.trackingmore.com/v4/trackings"
        self.session = requests.Session()  # 고속 대량 처리를 위한 세션 활성화

    def fetch_data(self, tracking_request, timeout=5.0) -> TrackingResult:
        api_key = get_trackingmore_key()
        
        if api_key == "MOCK_KEY_FOR_NOW":
            raise RuntimeError(
                "🚨 Streamlit Secrets에 TrackingMore API 키가 세팅되지 않았습니다!"
            )
            
        bl_number = tracking_request["bl_number"]
        carrier_code = tracking_request["carrier_code"]
        
        if carrier_code == "UNKNOWN":
            return TrackingResult(
                status="Failed", pol="N/A", etd="N/A", pod="N/A", eta="N/A", vessel="N/A",
                remarks="Carrier not supported. Please verify B/L number."
            )
            
        headers = {
            "Tracking-Api-Key": api_key, 
            "Content-Type": "application/json"
        }
        
        payload = {
            "tracking_number": bl_number, 
            "courier_code": carrier_code
        }
        
        try:
            # 1. Create API 호출 (TrackingMore는 최초 생성 시 실시간 데이터를 동시 반환합니다)
            response = self.session.post(
                f"{self.base_url}/create", 
                json=payload, 
                headers=headers, 
                timeout=timeout
            )
            raw_json = response.json()
            
            # 2. 만약 "이미 등록된 B/L" 에러(4006)가 발생하면, GET API로 안전하게 재조회
            if raw_json.get("meta", {}).get("code") == 4006:
                get_url = f"{self.base_url}/get?tracking_numbers={bl_number}&courier_code={carrier_code}"
                response = self.session.get(get_url, headers=headers, timeout=timeout)
                raw_json = response.json()
                
            return self._normalize_response(bl_number, carrier_code, raw_json)
            
        except Exception as e:
            return TrackingResult(
                status="Error", pol="N/A", etd="N/A", pod="N/A", eta="N/A", vessel="N/A",
                remarks=f"Network/Request Failed: {str(e)}"
            )

    def _normalize_response(self, bl_number, carrier_code, raw_json) -> TrackingResult:
        try:
            meta_code = raw_json.get("meta", {}).get("code")
            if meta_code != 200:
                error_msg = raw_json.get("meta", {}).get("message", "Unknown API Error")
                return TrackingResult(
                    status="Error", pol="N/A", etd="N/A", pod="N/A", eta="N/A", vessel="N/A",
                    remarks=f"API Error ({meta_code}): {error_msg}"
                )

            data = raw_json.get("data")
            # GET 요청 응답은 list, POST 응답은 dict일 수 있으므로 구조 방어
            if isinstance(data, list):
                data = data[0] if len(data) > 0 else {}
                
            if not data:
                return TrackingResult(
                    status="Not Found", pol="N/A", etd="N/A", pod="N/A", eta="N/A", vessel="N/A",
                    remarks="No tracking data returned from Carrier."
                )

            # 🚀 진짜 실시간 데이터 추출 구역!
            status = data.get("delivery_status", "Unknown")
            pol = data.get("origin_country", "N/A")
            pod = data.get("destination_country", "N/A")
            eta = data.get("scheduled_delivery_date", "N/A")
            
            return TrackingResult(
                status=status.upper(),
                pol=pol,
                etd="N/A",  # 해상 특화 필드는 추후 상세 API 문서를 보며 고도화
                pod=pod,
                eta=eta if eta else "N/A",
                vessel="N/A",
                remarks="🚀 Real-time Live Fetched!"
            )
        except Exception as e:
            return TrackingResult(
                status="Error", pol="N/A", etd="N/A", pod="N/A", eta="N/A", vessel="N/A",
                remarks=f"Parsing error: {str(e)}"
            )

class VizionProvider(BaseProvider):
    def fetch_data(self, tracking_request, timeout=5.0) -> TrackingResult:
        pass

def get_provider():
    provider_name = ACTIVE_PROVIDER
    if provider_name.lower() == "trackingmore":
        return TrackingMoreProvider()
    elif provider_name.lower() == "vizion":
        return VizionProvider()
    else:
        raise ValueError(f"Unknown provider configured: {provider_name}")
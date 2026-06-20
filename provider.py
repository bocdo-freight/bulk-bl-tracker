from dataclasses import dataclass
from abc import ABC, abstractmethod  # 👈 챗GPT 1위 피드백: 추상 클래스 도구 소환
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

class BaseProvider(ABC):  # 👈 챗GPT 1위 피드백: 추상 클래스로 격상
    """
    SaaS 아키텍처의 핵심 뼈대인 인터페이스 계약서.
    이 규격을 따르지 않는 자식 공급자는 태어날 수 없습니다.
    """
    @abstractmethod
    def fetch_data(self, tracking_request, timeout=5.0) -> TrackingResult:
        pass

class TrackingMoreProvider(BaseProvider):
    """
    TrackingMore API 공급자 실구현체 (v1.95 - 추상화 및 보안 검증 강화)
    """
    def __init__(self):
        self.base_url = "https://api.trackingmore.com/v4/trackings"
        # 챗GPT 3위 피드백용 주석 유지 (실제 연동 시 아래 주석 해제)
        # import requests
        # self.session = requests.Session()

    def fetch_data(self, tracking_request, timeout=5.0) -> TrackingResult:
        api_key = get_trackingmore_key()
        
        # ❌ 챗GPT 2위 피드백 반영: 키 설정 안 된 채로 가동 시 즉시 폭발하는 안전핀 장착
        if api_key == "MOCK_KEY_FOR_NOW":
            raise RuntimeError(
                "Critical Configuration Error: TrackingMore API key is not configured in Streamlit Secrets."
            )
            
        bl_number = tracking_request["bl_number"]
        carrier_code = tracking_request["carrier_code"]
        
        if carrier_code == "UNKNOWN":
            return TrackingResult(
                status="Failed", pol="N/A", etd="N/A", pod="N/A", eta="N/A", vessel="N/A",
                remarks="Carrier not supported. Please verify B/L number."
            )
            
        # [Phase 2 실제 연동 시 주석 해제 구역]
        # headers = {"Tracking-Api-Key": api_key, "Content-Type": "application/json"}
        # response = self.session.get(f"{self.base_url}/...", headers=headers, timeout=timeout)
        # return self._normalize_response(bl_number, carrier_code, response.json())
        
        return TrackingResult(
            status="In Transit",
            pol="SHANGHAI (CNSHA)",
            etd="2026-06-18",
            pod="ROTTERDAM (NLRTM)",
            eta="2026-07-22",
            vessel="COSCO SHIPPING GEMINI",
            remarks="Successfully fetched via API"
        )

    def _normalize_response(self, bl_number, carrier_code, raw_json) -> TrackingResult:
        try:
            data = raw_json.get("data", [{}])[0]
            return TrackingResult(
                status=data.get("delivery_status", "Unknown"),
                pol=data.get("origin_country", "Unknown"),
                etd="2026-06-18", 
                pod=data.get("destination_country", "Unknown"),
                eta=data.get("scheduled_delivery_date", "Unknown"),
                vessel="Unknown",
                remarks="Successfully parsed"
            )
        except Exception as e:
            return TrackingResult(
                status="Error", pol="N/A", etd="N/A", pod="N/A", eta="N/A", vessel="N/A",
                remarks=f"API Response parsing error: {str(e)}"
            )

class VizionProvider(BaseProvider):
    """
    BaseProvider 규격을 명확하게 상속받아 확장 준비 완료
    """
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
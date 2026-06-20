from config import get_trackingmore_key

class BaseProvider:
    """
    챗GPT 강력 추천: 나중에 Vizion, project44 등으로 1초 만에 확장하기 위한 규격 뼈대
    """
    def fetch_data(self, tracking_request, timeout=5.0):
        pass

class TrackingMoreProvider(BaseProvider):
    """
    TrackingMore API 공급자 실구현체 (v1.8 - 버그 수정 및 인터페이스 장착)
    """
    def __init__(self):
        self.base_url = "https://api.trackingmore.com/v4/trackings"

    def fetch_data(self, tracking_request, timeout=5.0):
        # 함수형으로 호출하여 최신 API 키가 안전하게 주입되도록 수정 완료!
        api_key = get_trackingmore_key()
        
        bl_number = tracking_request["bl_number"]
        carrier_code = tracking_request["carrier_code"]
        
        if carrier_code == "UNKNOWN":
            return None
            
        # [Phase 2 실제 연동 시 아래 주석이 해제되며, 챗GPT 지적대로 timeout이 직접 꽂힙니다]
        # import requests
        # headers = {"Tracking-Api-Key": api_key, "Content-Type": "application/json"}
        # response = requests.get(f"{self.base_url}/...", headers=headers, timeout=timeout) # 👈 버그 3위 해결
        # return response.json()
        
        # 현재 인프라 검증용 가짜 데이터 반환
        return {
            "status": "In Transit",
            "pol": "SHANGHAI (CNSHA)",
            "etd": "2026-06-18",
            "pod": "ROTTERDAM (NLRTM)",
            "eta": "2026-07-22",
            "vessel": "COSCO SHIPPING GEMINI"
        }

class VizionProvider(BaseProvider):
    """
    [예시] 추후 챗GPT 가이드대로 대기업용 Vizion API 확장 시 사용할 구역
    """
    def fetch_data(self, tracking_request, timeout=5.0):
        pass

# 챗GPT 피드백 버그 6위 해결: 나중에 다른 공급자 확장성을 고려한 매니저형 팩토리 함수
def get_provider(provider_name="trackingmore"):
    if provider_name.lower() == "trackingmore":
        return TrackingMoreProvider()
    elif provider_name.lower() == "vizion":
        return VizionProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
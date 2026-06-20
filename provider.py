import requests
from config import get_trackingmore_key, CARRIER_MAP

class TrackingResult:
    def __init__(self, status, pol, etd, pod, eta, vessel, remarks):
        self.status = status
        self.pol = pol
        self.etd = etd
        self.pod = pod
        self.eta = eta
        self.vessel = vessel
        self.remarks = remarks

class TrackingMoreProvider:
    def __init__(self):
        self.base_url = "https://api.trackingmore.com/v4/trackings"
        self.session = requests.Session()

    def fetch_data(self, bl_number, carrier_code, timeout=20.0):
        api_key = get_trackingmore_key()
        headers = {"Tracking-Api-Key": api_key, "Content-Type": "application/json"}
        
        # 1. 먼저 CREATE 호출
        payload = {"tracking_number": bl_number, "courier_code": carrier_code}
        try:
            resp = self.session.post(f"{self.base_url}/create", json=payload, headers=headers, timeout=timeout)
            data = resp.json()
            
            # 2. 이미 등록된 경우 GET 호출
            if data.get("meta", {}).get("code") == 4006:
                resp = self.session.get(f"{self.base_url}/get?tracking_numbers={bl_number}&courier_code={carrier_code}", headers=headers, timeout=timeout)
                data = resp.json()
            
            return self._parse(data)
        except Exception as e:
            return TrackingResult("Error", "N/A", "N/A", "N/A", "N/A", "N/A", f"Request Failed: {str(e)}")

    def _parse(self, raw_data):
        # TrackingMore 데이터 구조에 맞춘 정밀 파싱
        try:
            items = raw_data.get("data", {}).get("items", [])
            # 만약 items가 리스트라면 첫 번째 데이터를 사용
            d = items[0] if isinstance(items, list) and len(items) > 0 else {}
            
            # 실제 정보 추출
            status = d.get("delivery_status", "Unknown")
            # origin_info / destination_info 구조에서 정보 추출
            orig = d.get("origin_info", {})
            dest = d.get("destination_info", {})
            eta = d.get("scheduled_delivery_date", "N/A")
            
            return TrackingResult(
                status, 
                orig.get("city", "N/A"), 
                "N/A", 
                dest.get("city", "N/A"), 
                eta, 
                "N/A", 
                "Success"
            )
        except Exception as e:
            return TrackingResult("Error", "N/A", "N/A", "N/A", "N/A", "N/A", f"Parse Error: {str(e)}")
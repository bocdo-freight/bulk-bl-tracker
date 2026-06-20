import json
import requests
from config import get_trackingmore_key

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

    def _to_debug(self, response):
        try: return response.json()
        except: return response.text

    def fetch_data(self, bl_number, carrier_code, timeout=20.0):
        api_key = get_trackingmore_key()
        headers = {"Tracking-Api-Key": api_key, "Content-Type": "application/json"}
        
        # 1. CREATE 호출
        payload = {"tracking_number": bl_number, "courier_code": carrier_code}
        create_resp = self.session.post(f"{self.base_url}/create", json=payload, headers=headers, timeout=timeout)
        create_data = self._to_debug(create_resp)
        
        # 2. GET 호출 (필요시)
        get_data = None
        if create_resp.status_code != 200 and create_data.get("meta", {}).get("code") == 4006:
            get_resp = self.session.get(f"{self.base_url}/get?tracking_numbers={bl_number}&courier_code={carrier_code}", headers=headers, timeout=timeout)
            get_data = self._to_debug(get_resp)
            
        # 3. 디버그 데이터를 한 묶음으로 파서에 전달
        return self._parse({"create": create_data, "get": get_data})

    def _parse(self, debug_data):
        # JSON 문자열로 변환하여 Remarks에 출력
        raw_text = json.dumps(debug_data, ensure_ascii=False, indent=2, default=str)
        return TrackingResult("RAW DEBUG", "N/A", "N/A", "N/A", "N/A", "N/A", raw_text)
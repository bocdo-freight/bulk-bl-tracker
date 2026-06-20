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
        payload = {"tracking_number": bl_number, "courier_code": carrier_code}
        
        try:
            response = self.session.post(f"{self.base_url}/create", json=payload, headers=headers, timeout=timeout)
            data = response.json()
            if data.get("meta", {}).get("code") == 4006:
                response = self.session.get(f"{self.base_url}/get?tracking_numbers={bl_number}&courier_code={carrier_code}", headers=headers, timeout=timeout)
                data = response.json()
            
            return self._parse(data)
        except Exception as e:
            return TrackingResult("Error", "N/A", "N/A", "N/A", "N/A", "N/A", str(e))

    def _parse(self, raw_data):
        # 파싱 로직 단순화
        d = raw_data.get("data", {})
        if isinstance(d, list): d = d[0] if d else {}
        return TrackingResult(
            d.get("delivery_status", "Unknown"), "N/A", "N/A", "N/A", 
            d.get("scheduled_delivery_date", "N/A"), "N/A", "Success"
        )
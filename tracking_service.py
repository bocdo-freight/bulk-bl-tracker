import time
from config import CARRIER_MAP
from provider import TrackingMoreProvider

def track_bulk_bl(bl_list, progress_callback=None):
    results = []
    provider = TrackingMoreProvider()
    total = len(bl_list)
    
    for i, bl in enumerate(bl_list):
        if progress_callback: progress_callback(i + 1, total)
        time.sleep(2.0) # 속도 제한 방어
        
        prefix = bl[:4].upper()
        carrier = CARRIER_MAP.get(prefix)
        
        if not carrier:
            results.append({"B/L Number": bl, "Carrier": "UNKNOWN", "Status": "Failed", "Remarks": "Mapping Error"})
            continue
            
        res = provider.fetch_data(bl, carrier)
        results.append({
            "B/L Number": bl, "Carrier": carrier.upper(), "Status": res.status,
            "POL": res.pol, "ETD": res.etd, "POD": res.pod, "ETA": res.eta, "Remarks": res.remarks
        })
    return results
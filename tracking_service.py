import time

def detect_carrier(bl_number):
    """
    B/L 번호의 앞자리 프리픽스를 분석하여 선사를 자동으로 인식합니다.
    """
    if not bl_number or len(str(bl_number)) < 4:
        return "UNKNOWN"
        
    prefix = str(bl_number)[:4].upper()
    
    carrier_map = {
        "HMCU": "HMM",
        "MAEU": "MAERSK",
        "ONEY": "ONE",
        "OOLU": "OOCL",
        "COSU": "COSCO",
        "EMCU": "EVERGREEN"
    }
    
    return carrier_map.get(prefix, "UNKNOWN")

def track_bulk_bl(bl_list):
    """
    대량의 B/L 리스트를 받아 트래킹 결과를 반환합니다. (v1.4 - ETD 반영 및 가짜 데이터 보강)
    """
    results = []
    total_count = len(bl_list)
    
    for i, bl in enumerate(bl_list):
        carrier = detect_carrier(bl)
        
        # 선사별로 실무에 가깝게 가짜 스케줄 데이터 매핑 (ETD 추가)
        if carrier == "HMM":
            status = "On Board"
            pol = "BUSAN (KRPUS)"
            etd = "2026-06-12"
            pod = "HAMBURG (DEHAM)"
            eta = "2026-07-18"
        elif carrier == "MAERSK":
            status = "Delay"
            pol = "SHANGHAI (CNSHA)"
            etd = "2026-06-05"
            pod = "ROTTERDAM (NLRTM)"
            eta = "2026-07-20"
        elif carrier == "ONE":
            status = "On Schedule"
            pol = "SINGAPORE (SGSIN)"
            etd = "2026-06-10"
            pod = "ROTTERDAM (NLRTM)"
            eta = "2026-07-12"
        else:
            status = "Failed"
            pol = "UNKNOWN"
            etd = "N/A"
            pod = "UNKNOWN"
            eta = "N/A"
            
        results.append({
            "B/L Number": bl,
            "Carrier": carrier,
            "Status": status,
            "POL": pol,
            "ETD": etd,      # 👈 형님이 말씀하신 ETD 추가!
            "POD": pod,
            "ETA": eta
        })
        
    return results
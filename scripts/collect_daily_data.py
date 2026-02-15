"""
통합 키위 농장 데이터 수집 시스템
- 센서 데이터 수집
- 적산온도 계산
- 생육 단계 자동 감지
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta

# 환경변수
ECOWITT_APP_KEY = os.environ.get('ECOWITT_APP_KEY')
ECOWITT_API_KEY = os.environ.get('ECOWITT_API_KEY')
ECOWITT_MAC = os.environ.get('ECOWITT_MAC')

# 파일 경로
DATA_DIR = "data"
SENSOR_FILE = os.path.join(DATA_DIR, "sensor_history.json")
GDD_FILE = os.path.join(DATA_DIR, "gdd_data.json")
PHENOLOGY_FILE = os.path.join(DATA_DIR, "phenology.json")

def get_daily_data(date_str):
    """ECOWITT 일별 데이터 가져오기"""
    try:
        url = "https://api.ecowitt.net/api/v3/device/history"
        t = str(int(time.time() * 1000))
        
        params = {
            "application_key": ECOWITT_APP_KEY,
            "api_key": ECOWITT_API_KEY,
            "mac": ECOWITT_MAC,
            "start_date": date_str,
            "end_date": date_str,
            "cycle_type": "daily",
            "call_back": "all",
            "temp_unitid": "1",
            "t": t
        }
        
        print(f"📡 Fetching {date_str}...")
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0 and result.get("data", {}).get("list"):
                print(f"✅ Success")
                return result["data"]
        
        print(f"⚠️  No data")
        return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def parse_daily_data(data, date_str):
    """데이터 파싱"""
    try:
        day_data = data["list"][0]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        
        def safe_get(d, key, default=0.0):
            try:
                val = d.get(key, {})
                if isinstance(val, dict):
                    return float(val.get("value", default))
                return float(val) if val is not None else default
            except:
                return default
        
        return {
            "date": date_str,
            "month": date_obj.month,
            "day_of_year": date_obj.timetuple().tm_yday,
            "temp_2dong": safe_get(day_data, "temp_ch1_avg"),
            "temp_3dong": safe_get(day_data, "temp_ch3_avg"),
            "temp_soil": safe_get(day_data, "temp_ch2_avg"),
            "moisture_2dong": safe_get(day_data, "soilmoisture_ch1_avg"),
            "moisture_3dong": safe_get(day_data, "soilmoisture_ch2_avg"),
            "outdoor_temp": safe_get(day_data, "outdoor_temp_avg"),
            "outdoor_temp_max": safe_get(day_data, "outdoor_temp_max"),
            "outdoor_temp_min": safe_get(day_data, "outdoor_temp_min"),
            "outdoor_humid": safe_get(day_data, "outdoor_humidity_avg"),
        }
        
    except Exception as e:
        print(f"❌ Parse error: {e}")
        return None

def load_json(filepath):
    """JSON 로드"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return [] if filepath != PHENOLOGY_FILE else {}
    except:
        return [] if filepath != PHENOLOGY_FILE else {}

def save_json(filepath, data):
    """JSON 저장"""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Save error: {e}")
        return False

def save_sensor_data(parsed_data):
    """센서 데이터 저장"""
    history = load_json(SENSOR_FILE)
    date_str = parsed_data["date"]
    
    existing_idx = None
    for idx, record in enumerate(history):
        if record.get("date") == date_str:
            existing_idx = idx
            break
    
    if existing_idx is not None:
        history[existing_idx] = parsed_data
        print(f"🔄 Updated: {date_str}")
    else:
        history.append(parsed_data)
        print(f"➕ Added: {date_str}")
    
    history.sort(key=lambda x: x["date"])
    return save_json(SENSOR_FILE, history)

def calculate_gdd(parsed_data, base_temp=10.0, shock_threshold=8.0):
    """적산온도 계산"""
    gdd_records = load_json(GDD_FILE)
    date_str = parsed_data["date"]
    outdoor_temp = parsed_data["outdoor_temp"]
    
    for record in gdd_records:
        if record.get("date") == date_str:
            print(f"⚠️  GDD exists")
            return True
    
    yesterday_gdd = 0
    stress_days = 0
    
    if gdd_records:
        last = gdd_records[-1]
        yesterday_gdd = last.get("accumulated_gdd", 0)
        stress_days = last.get("stress_days_remaining", 0)
    
    daily_gdd = 0
    recovery_penalty = 0.5
    
    if outdoor_temp < shock_threshold:
        daily_gdd = 0
        stress_days = 3
        print(f"❄️  Shock: {outdoor_temp}°C")
    elif stress_days > 0:
        raw_gdd = max(0, outdoor_temp - base_temp)
        daily_gdd = raw_gdd * recovery_penalty
        stress_days -= 1
    else:
        daily_gdd = max(0, outdoor_temp - base_temp)
    
    accumulated_gdd = yesterday_gdd + daily_gdd
    
    new_record = {
        "date": date_str,
        "outdoor_temp": outdoor_temp,
        "daily_gdd": round(daily_gdd, 2),
        "accumulated_gdd": round(accumulated_gdd, 2),
        "stress_days_remaining": stress_days,
        "is_shock": outdoor_temp < shock_threshold
    }
    
    gdd_records.append(new_record)
    
    if save_json(GDD_FILE, gdd_records):
        print(f"📈 GDD: +{daily_gdd:.2f} → {accumulated_gdd:.2f}")
        
        # 생육 단계 자동 감지
        detect_phenology_stage(accumulated_gdd, date_str)
        
        return True
    return False

def detect_phenology_stage(current_gdd, date_str):
    """생육 단계 자동 감지 및 기록"""
    phenology = load_json(PHENOLOGY_FILE)
    
    year = datetime.strptime(date_str, "%Y-%m-%d").year
    year_str = str(year)
    
    if year_str not in phenology:
        phenology[year_str] = {}
    
    year_data = phenology[year_str]
    
    # 발아 감지 (GDD 200)
    if current_gdd >= 200 and "bud_break" not in year_data:
        year_data["bud_break"] = {
            "date": date_str,
            "gdd_at_event": round(current_gdd, 2),
            "auto_detected": True
        }
        print(f"🌱 발아 감지!")
    
    # 개화 감지 (GDD 750)
    if current_gdd >= 750 and "flowering_start" not in year_data:
        year_data["flowering_start"] = {
            "date": date_str,
            "gdd_at_event": round(current_gdd, 2),
            "auto_detected": True
        }
        print(f"🌸 개화 감지!")
    
    save_json(PHENOLOGY_FILE, phenology)

def backfill_missing_dates():
    """최근 7일 누락 데이터 보충"""
    print("\n🔍 Checking missing dates...")
    
    history = load_json(SENSOR_FILE)
    existing_dates = set(r["date"] for r in history)
    
    filled = 0
    for i in range(1, 8):
        check_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        
        if check_date not in existing_dates:
            print(f"📥 Backfill: {check_date}")
            data = get_daily_data(check_date)
            
            if data:
                parsed = parse_daily_data(data, check_date)
                if parsed and save_sensor_data(parsed):
                    calculate_gdd(parsed)
                    filled += 1
                    time.sleep(2)
    
    print(f"✅ Backfilled: {filled} dates")

def main():
    print("="*60)
    print("🥝 키위 농장 통합 데이터 수집")
    print("="*60)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not all([ECOWITT_APP_KEY, ECOWITT_API_KEY, ECOWITT_MAC]):
        print("❌ API credentials missing")
        return False
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"🎯 Target: {yesterday}\n")
    
    # 어제 데이터 수집
    data = get_daily_data(yesterday)
    
    if not data:
        print("⚠️  Fetch failed, trying backfill...")
        backfill_missing_dates()
        return True
    
    parsed = parse_daily_data(data, yesterday)
    
    if not parsed:
        print("❌ Parse failed")
        return False
    
    if not save_sensor_data(parsed):
        print("❌ Save failed")
        return False
    
    if not calculate_gdd(parsed):
        print("❌ GDD failed")
        return False
    
    backfill_missing_dates()
    
    # 통계
    sensor_count = len(load_json(SENSOR_FILE))
    gdd_count = len(load_json(GDD_FILE))
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"✅ Sensor records: {sensor_count}")
    print(f"✅ GDD records: {gdd_count}")
    print(f"✅ Files saved to: {DATA_DIR}/")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

"""
ECOWITT 주간 데이터 수집 및 일평균 계산
- 주간 데이터 다운로드 (30분 간격)
- 날짜별로 평균 계산
- 적산온도 자동 계산
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from collections import defaultdict

# 환경변수
ECOWITT_APP_KEY = os.environ.get('ECOWITT_APP_KEY')
ECOWITT_API_KEY = os.environ.get('ECOWITT_API_KEY')
ECOWITT_MAC = os.environ.get('ECOWITT_MAC')

# 파일 경로
DATA_DIR = "data"
SENSOR_FILE = os.path.join(DATA_DIR, "sensor_history.json")
GDD_FILE = os.path.join(DATA_DIR, "gdd_data.json")
PHENOLOGY_FILE = os.path.join(DATA_DIR, "phenology.json")

def get_weekly_data():
    """ECOWITT 주간 데이터 가져오기 (30분 간격)"""
    try:
        url = "https://api.ecowitt.net/api/v3/device/history"
        t = str(int(time.time() * 1000))
        
        # 지난 7일
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        params = {
            "application_key": ECOWITT_APP_KEY,
            "api_key": ECOWITT_API_KEY,
            "mac": ECOWITT_MAC,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "cycle_type": "30min",  # ← 30분 간격
            "call_back": "outdoor,temp_and_humidity_ch1,temp_and_humidity_ch2,temp_and_humidity_ch3,soil_ch1,soil_ch2",
            "temp_unitid": "1",
            "t": t
        }
        
        print(f"📡 Fetching weekly data ({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})...")
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                data = result.get("data", {})
                if data and "list" in data and data["list"]:
                    print(f"✅ Received {len(data['list'])} records")
                    return data["list"]
                else:
                    print(f"⚠️  No data in response")
                    return None
            else:
                print(f"❌ API Error: {result.get('msg', 'Unknown')}")
                return None
        else:
            print(f"❌ HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None

def parse_and_average_by_day(raw_data):
    """30분 간격 데이터를 날짜별 평균으로 변환"""
    try:
        # 날짜별로 데이터 그룹화
        daily_data = defaultdict(lambda: {
            'temp_2dong': [],
            'temp_3dong': [],
            'temp_soil': [],
            'moisture_2dong': [],
            'moisture_3dong': [],
            'outdoor_temp': [],
            'outdoor_humid': []
        })
        
        print(f"\n📊 Processing {len(raw_data)} records...")
        
        for record in raw_data:
            try:
                # 타임스탬프에서 날짜 추출
                timestamp = record.get("timestamp")
                if not timestamp:
                    continue
                
                # Unix timestamp를 날짜로 변환
                dt = datetime.fromtimestamp(int(timestamp))
                date_str = dt.strftime("%Y-%m-%d")
                
                # 안전한 값 추출
                def safe_get(data_dict, key, default=None):
                    try:
                        val = data_dict.get(key, {})
                        if isinstance(val, dict):
                            return float(val.get("value", default))
                        return float(val) if val is not None else default
                    except:
                        return default
                
                # 각 센서 데이터 추출
                temp_2 = safe_get(record, "temp_ch1")
                temp_3 = safe_get(record, "temp_ch3")
                temp_s = safe_get(record, "temp_ch2")
                moist_2 = safe_get(record, "soilmoisture_ch1")
                moist_3 = safe_get(record, "soilmoisture_ch2")
                out_t = safe_get(record, "outdoor_temp")
                out_h = safe_get(record, "outdoor_humidity")
                
                # 유효한 값만 추가
                if temp_2 is not None:
                    daily_data[date_str]['temp_2dong'].append(temp_2)
                if temp_3 is not None:
                    daily_data[date_str]['temp_3dong'].append(temp_3)
                if temp_s is not None:
                    daily_data[date_str]['temp_soil'].append(temp_s)
                if moist_2 is not None:
                    daily_data[date_str]['moisture_2dong'].append(moist_2)
                if moist_3 is not None:
                    daily_data[date_str]['moisture_3dong'].append(moist_3)
                if out_t is not None:
                    daily_data[date_str]['outdoor_temp'].append(out_t)
                if out_h is not None:
                    daily_data[date_str]['outdoor_humid'].append(out_h)
                    
            except Exception as e:
                continue
        
        # 날짜별 평균 계산
        daily_averages = []
        
        for date_str in sorted(daily_data.keys()):
            data = daily_data[date_str]
            
            # 평균 계산
            def calc_avg(values):
                return round(sum(values) / len(values), 2) if values else 0.0
            
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            avg_record = {
                "date": date_str,
                "month": date_obj.month,
                "day_of_year": date_obj.timetuple().tm_yday,
                "temp_2dong": calc_avg(data['temp_2dong']),
                "temp_3dong": calc_avg(data['temp_3dong']),
                "temp_soil": calc_avg(data['temp_soil']),
                "moisture_2dong": calc_avg(data['moisture_2dong']),
                "moisture_3dong": calc_avg(data['moisture_3dong']),
                "outdoor_temp": calc_avg(data['outdoor_temp']),
                "outdoor_humid": calc_avg(data['outdoor_humid']),
                "sample_count": len(data['outdoor_temp'])  # 하루에 몇 개 샘플
            }
            
            daily_averages.append(avg_record)
            print(f"  ✅ {date_str}: {avg_record['sample_count']} samples → avg {avg_record['outdoor_temp']}°C")
        
        return daily_averages
        
    except Exception as e:
        print(f"❌ Parse error: {str(e)}")
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

def merge_sensor_data(new_data):
    """새 데이터를 기존 데이터와 병합"""
    history = load_json(SENSOR_FILE)
    
    # 기존 날짜 목록
    existing_dates = {record["date"] for record in history}
    
    added = 0
    updated = 0
    
    for new_record in new_data:
        date_str = new_record["date"]
        
        if date_str in existing_dates:
            # 기존 데이터 업데이트
            for idx, record in enumerate(history):
                if record["date"] == date_str:
                    history[idx] = new_record
                    updated += 1
                    break
        else:
            # 새 데이터 추가
            history.append(new_record)
            added += 1
    
    # 날짜순 정렬
    history.sort(key=lambda x: x["date"])
    
    if save_json(SENSOR_FILE, history):
        print(f"💾 Sensor data: {added} added, {updated} updated (total: {len(history)})")
        return True
    return False

def calculate_gdd(sensor_data, base_temp=10.0, shock_threshold=8.0):
    """적산온도 계산"""
    gdd_records = load_json(GDD_FILE)
    existing_dates = {r["date"] for r in gdd_records}
    
    # 날짜순 정렬
    sorted_data = sorted(sensor_data, key=lambda x: x["date"])
    
    for record in sorted_data:
        date_str = record["date"]
        
        if date_str in existing_dates:
            continue  # 이미 계산됨
        
        outdoor_temp = record["outdoor_temp"]
        
        # 어제까지의 누적 GDD
        yesterday_gdd = 0
        stress_days = 0
        
        if gdd_records:
            last = gdd_records[-1]
            yesterday_gdd = last.get("accumulated_gdd", 0)
            stress_days = last.get("stress_days_remaining", 0)
        
        # 오늘의 GDD 계산
        daily_gdd = 0
        recovery_penalty = 0.5
        
        if outdoor_temp < shock_threshold:
            daily_gdd = 0
            stress_days = 3
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
        print(f"  📈 {date_str}: GDD +{daily_gdd:.2f} → {accumulated_gdd:.2f}")
    
    if save_json(GDD_FILE, gdd_records):
        return True
    return False

def detect_phenology_stage(sensor_data):
    """생육 단계 자동 감지"""
    gdd_records = load_json(GDD_FILE)
    if not gdd_records:
        return
    
    phenology = load_json(PHENOLOGY_FILE)
    
    for gdd_record in gdd_records:
        date_str = gdd_record["date"]
        current_gdd = gdd_record["accumulated_gdd"]
        
        year = datetime.strptime(date_str, "%Y-%m-%d").year
        year_str = str(year)
        
        if year_str not in phenology:
            phenology[year_str] = {}
        
        year_data = phenology[year_str]
        
        # 발아 감지
        if current_gdd >= 200 and "bud_break" not in year_data:
            year_data["bud_break"] = {
                "date": date_str,
                "gdd_at_event": round(current_gdd, 2),
                "auto_detected": True
            }
            print(f"  🌱 발아 감지: {date_str}")
        
        # 개화 감지
        if current_gdd >= 750 and "flowering_start" not in year_data:
            year_data["flowering_start"] = {
                "date": date_str,
                "gdd_at_event": round(current_gdd, 2),
                "auto_detected": True
            }
            print(f"  🌸 개화 감지: {date_str}")
    
    save_json(PHENOLOGY_FILE, phenology)

def main():
    print("="*60)
    print("🥝 키위 농장 주간 데이터 수집")
    print("="*60)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not all([ECOWITT_APP_KEY, ECOWITT_API_KEY, ECOWITT_MAC]):
        print("❌ API credentials missing")
        return False
    
    # 1. 주간 데이터 가져오기
    raw_data = get_weekly_data()
    
    if not raw_data:
        print("❌ No data received")
        return False
    
    # 2. 날짜별 평균 계산
    daily_averages = parse_and_average_by_day(raw_data)
    
    if not daily_averages:
        print("❌ Failed to calculate averages")
        return False
    
    print(f"\n✅ Calculated {len(daily_averages)} daily averages")
    
    # 3. 센서 데이터 저장
    print("\n💾 Saving sensor data...")
    if not merge_sensor_data(daily_averages):
        print("❌ Failed to save sensor data")
        return False
    
    # 4. 적산온도 계산
    print("\n📈 Calculating GDD...")
    if not calculate_gdd(daily_averages):
        print("❌ Failed to calculate GDD")
        return False
    
    # 5. 생육 단계 감지
    print("\n🌱 Detecting phenology stages...")
    detect_phenology_stage(daily_averages)
    
    # 6. 통계
    sensor_count = len(load_json(SENSOR_FILE))
    gdd_count = len(load_json(GDD_FILE))
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"✅ Sensor records: {sensor_count}")
    print(f"✅ GDD records: {gdd_count}")
    print(f"✅ New data: {len(daily_averages)} days")
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

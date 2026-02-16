"""
ECOWITT 히스토리 데이터 수집 및 일평균 계산
- 예전 코드의 파싱 방식 적용
- 30분 간격 데이터 → 일평균
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

def get_history_data(start_date, end_date):
    """ECOWITT 히스토리 데이터 가져오기 (예전 방식 적용)"""
    try:
        url = "https://api.ecowitt.net/api/v3/device/history"
        t = str(int(time.time() * 1000))
        
        params = {
            "application_key": ECOWITT_APP_KEY,
            "api_key": ECOWITT_API_KEY,
            "mac": ECOWITT_MAC,
            "start_date": start_date,
            "end_date": end_date,
            "call_back": "indoor,temp_and_humidity_ch1,temp_and_humidity_ch3,temp_ch2,soil_ch1,soil_ch2",  # 예전 코드처럼 all 사용
            "temp_unitid": "1",  # 섭씨
            "pressure_unitid": "3",
            "wind_speed_unitid": "7",
            "rainfall_unitid": "12",
            "solar_irradiance_unitid": "16",
            "cycle_type": "30min",
            "t": t
        }
        
        print(f"📡 Fetching history data ({start_date} ~ {end_date})...")
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response code: {result.get('code')}")
            
            if result.get("code") == 0:
                data = result.get("data", {})
                if data:
                    print(f"✅ API Success")
                    return data
                else:
                    print(f"⚠️  No data in response")
                    return None
            else:
                print(f"❌ API Error: code={result.get('code')}, msg={result.get('msg', 'Unknown')}")
                return None
        else:
            print(f"❌ HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def parse_history_data(api_data):
    """
    히스토리 데이터 파싱 (예전 코드 방식 참고)
    응답 형식:
    {
      "indoor": {
        "temperature": {
          "list": {
            "1768348800": "44.3",
            "1768363200": "58.0"
          }
        }
      }
    }
    """
    try:
        # 날짜별 데이터 그룹화
        daily_data = defaultdict(lambda: {
            'temp_2dong': [],
            'temp_3dong': [],
            'temp_soil': [],
            'moisture_2dong': [],
            'moisture_3dong': [],
            'outdoor_temp': [],
            'outdoor_humid': []
        })
        
        print(f"\n📊 Parsing data...")
        
        # 실내(게이트웨이) = 실외 온도로 사용
        if "indoor" in api_data:
            indoor = api_data["indoor"]
            
            # 실외 온도
            if "temperature" in indoor:
                temp_list = indoor["temperature"].get("list", {})
                print(f"  Indoor temp records: {len(temp_list)}")
                
                for timestamp, value in temp_list.items():
                    try:
                        dt = datetime.fromtimestamp(int(timestamp))
                        date_str = dt.strftime("%Y-%m-%d")
                        daily_data[date_str]['outdoor_temp'].append(float(value))
                    except Exception as e:
                        continue
            
            # 실외 습도
            if "humidity" in indoor:
                humid_list = indoor["humidity"].get("list", {})
                print(f"  Indoor humid records: {len(humid_list)}")
                
                for timestamp, value in humid_list.items():
                    try:
                        dt = datetime.fromtimestamp(int(timestamp))
                        date_str = dt.strftime("%Y-%m-%d")
                        daily_data[date_str]['outdoor_humid'].append(float(value))
                    except:
                        continue
        
        # 온습도 센서 CH1 = 2동
        if "temp_and_humidity_ch1" in api_data:
            ch1 = api_data["temp_and_humidity_ch1"]
            
            if "temperature" in ch1:
                temp_list = ch1["temperature"].get("list", {})
                print(f"  CH1 temp records: {len(temp_list)}")
                
                for timestamp, value in temp_list.items():
                    try:
                        dt = datetime.fromtimestamp(int(timestamp))
                        date_str = dt.strftime("%Y-%m-%d")
                        daily_data[date_str]['temp_2dong'].append(float(value))
                    except:
                        continue
        
        # 온습도 센서 CH3 = 3동
        if "temp_and_humidity_ch3" in api_data:
            ch3 = api_data["temp_and_humidity_ch3"]
            
            if "temperature" in ch3:
                temp_list = ch3["temperature"].get("list", {})
                print(f"  CH3 temp records: {len(temp_list)}")
                
                for timestamp, value in temp_list.items():
                    try:
                        dt = datetime.fromtimestamp(int(timestamp))
                        date_str = dt.strftime("%Y-%m-%d")
                        daily_data[date_str]['temp_3dong'].append(float(value))
                    except:
                        continue
        
        # 온도 센서 CH2 = 토양
        if "temp_ch2" in api_data:
            ch2 = api_data["temp_ch2"]
            
            if "temperature" in ch2:
                temp_list = ch2["temperature"].get("list", {})
                print(f"  CH2 (soil) temp records: {len(temp_list)}")
                
                for timestamp, value in temp_list.items():
                    try:
                        dt = datetime.fromtimestamp(int(timestamp))
                        date_str = dt.strftime("%Y-%m-%d")
                        daily_data[date_str]['temp_soil'].append(float(value))
                    except:
                        continue
        
        # 토양 수분 CH1 = 2동
        if "soil_ch1" in api_data:
            soil1 = api_data["soil_ch1"]
            
            if "soilmoisture" in soil1:
                moist_list = soil1["soilmoisture"].get("list", {})
                print(f"  Soil CH1 records: {len(moist_list)}")
                
                for timestamp, value in moist_list.items():
                    try:
                        dt = datetime.fromtimestamp(int(timestamp))
                        date_str = dt.strftime("%Y-%m-%d")
                        daily_data[date_str]['moisture_2dong'].append(float(value))
                    except:
                        continue
        
        # 토양 수분 CH2 = 3동
        if "soil_ch2" in api_data:
            soil2 = api_data["soil_ch2"]
            
            if "soilmoisture" in soil2:
                moist_list = soil2["soilmoisture"].get("list", {})
                print(f"  Soil CH2 records: {len(moist_list)}")
                
                for timestamp, value in moist_list.items():
                    try:
                        dt = datetime.fromtimestamp(int(timestamp))
                        date_str = dt.strftime("%Y-%m-%d")
                        daily_data[date_str]['moisture_3dong'].append(float(value))
                    except:
                        continue
        
        # 날짜별 평균 계산
        daily_averages = []
        
        for date_str in sorted(daily_data.keys()):
            data = daily_data[date_str]
            
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
                "sample_count": len(data['outdoor_temp'])
            }
            
            daily_averages.append(avg_record)
            print(f"  ✅ {date_str}: {avg_record['sample_count']} samples → {avg_record['outdoor_temp']}°C")
        
        return daily_averages
        
    except Exception as e:
        print(f"❌ Parse error: {str(e)}")
        import traceback
        traceback.print_exc()
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
    """센서 데이터 병합"""
    history = load_json(SENSOR_FILE)
    existing_dates = {r["date"] for r in history}
    
    added = 0
    updated = 0
    
    for new_record in new_data:
        date_str = new_record["date"]
        
        if date_str in existing_dates:
            for idx, record in enumerate(history):
                if record["date"] == date_str:
                    history[idx] = new_record
                    updated += 1
                    break
        else:
            history.append(new_record)
            added += 1
    
    history.sort(key=lambda x: x["date"])
    
    if save_json(SENSOR_FILE, history):
        print(f"💾 Sensor: {added} added, {updated} updated (total: {len(history)})")
        return True
    return False

def calculate_gdd(sensor_data, base_temp=10.0, shock_threshold=8.0):
    """적산온도 계산"""
    gdd_records = load_json(GDD_FILE)
    existing_dates = {r["date"] for r in gdd_records}
    
    sorted_data = sorted(sensor_data, key=lambda x: x["date"])
    
    for record in sorted_data:
        date_str = record["date"]
        
        if date_str in existing_dates:
            continue
        
        outdoor_temp = record["outdoor_temp"]
        
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
        print(f"  📈 {date_str}: +{daily_gdd:.2f} → {accumulated_gdd:.2f}")
    
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
        
        if current_gdd >= 200 and "bud_break" not in year_data:
            year_data["bud_break"] = {
                "date": date_str,
                "gdd_at_event": round(current_gdd, 2),
                "auto_detected": True
            }
            print(f"  🌱 발아 감지: {date_str}")
        
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
    print("🥝 키위 농장 데이터 수집")
    print("="*60)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not all([ECOWITT_APP_KEY, ECOWITT_API_KEY, ECOWITT_MAC]):
        print("❌ API credentials missing")
        return False
    
    # 지난 7일 데이터 가져오기
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    start_str = start_date.strftime("%Y-%m-%d 00:00:00")
    end_str = end_date.strftime("%Y-%m-%d 23:59:59")
    
    # API 호출
    api_data = get_history_data(start_str, end_str)
    
    if not api_data:
        print("❌ No data received")
        return False
    
    # 파싱
    daily_averages = parse_history_data(api_data)
    
    if not daily_averages:
        print("❌ Parse failed")
        return False
    
    print(f"\n✅ Calculated {len(daily_averages)} daily averages")
    
    # 저장
    print("\n💾 Saving data...")
    if not merge_sensor_data(daily_averages):
        print("❌ Save failed")
        return False
    
    # GDD 계산
    print("\n📈 Calculating GDD...")
    if not calculate_gdd(daily_averages):
        print("❌ GDD failed")
        return False
    
    # 생육 단계 감지
    print("\n🌱 Detecting stages...")
    detect_phenology_stage(daily_averages)
    
    # 통계
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

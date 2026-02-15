import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import json
import os
import plotly.graph_objects as go

# ============================================================
# Page config
# ============================================================
st.set_page_config(
    page_title="키위 농장 AI 시스템",
    page_icon="🥝",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# 스타일
# ============================================================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background-color: var(--bg);
        color: var(--text);
    }
    :root {
        --bg: #ffffff;
        --text: #1c1c1e;
        --card: rgba(255,255,255,0.9);
        --border: rgba(60,60,67,0.12);
        --muted: rgba(60,60,67,0.72);
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --bg: #000000;
            --text: #ffffff;
            --card: rgba(28,28,30,0.9);
            --border: rgba(140,140,140,0.24);
            --muted: rgba(235,235,245,0.6);
        }
        .stMarkdown, p, span, div, h1, h2, h3 {
            color: #ffffff !important;
        }
    }
    .block-container { 
        padding-top: 0 !important;
        max-width: 100%;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    div[data-testid="stToolbar"], footer, #MainMenu, header[data-testid="stHeader"] { 
        display: none; 
    }
    .card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .stage-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        margin-bottom: 8px;
    }
    .stage-dormancy { background: rgba(100,100,100,0.2); color: #666; }
    .stage-flowering { background: rgba(255,105,180,0.2); color: #FF69B4; }
    .stage-fruiting { background: rgba(52,199,89,0.2); color: #34C759; }
    .stage-harvest { background: rgba(255,149,0,0.2); color: #FF9500; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 설정
# ============================================================
TODAY = date.today()
DATA_DIR = "data"
SENSOR_FILE = os.path.join(DATA_DIR, "sensor_history.json")
GDD_FILE = os.path.join(DATA_DIR, "gdd_data.json")
PHENOLOGY_FILE = os.path.join(DATA_DIR, "phenology.json")
GROWTH_FILE = "fruit_growth.json"

# ============================================================
# 데이터 로드
# ============================================================
def load_json(filepath):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return [] if filepath != PHENOLOGY_FILE else {}
    except:
        return [] if filepath != PHENOLOGY_FILE else {}

def save_json(filepath, data):
    try:
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

# ============================================================
# 생육 단계 감지
# ============================================================
def get_current_growth_stage():
    """현재 생육 단계 자동 감지"""
    month = TODAY.month
    
    gdd_data = load_json(GDD_FILE)
    phenology = load_json(PHENOLOGY_FILE)
    
    current_gdd = gdd_data[-1].get("accumulated_gdd", 0) if gdd_data else 0
    year_str = str(TODAY.year)
    year_data = phenology.get(year_str, {})
    
    # GDD와 날짜 기반 판단
    if month in [1, 2, 3]:
        if current_gdd < 200:
            return {
                "id": "dormancy",
                "name": "휴면기/발아기",
                "emoji": "🌱",
                "color": "stage-dormancy",
                "progress": min(100, (current_gdd / 200) * 100),
                "next_milestone": "발아",
                "next_gdd": 200
            }
        elif current_gdd < 750:
            return {
                "id": "pre_flowering",
                "name": "발아 후 성장기",
                "emoji": "🌿",
                "color": "stage-dormancy",
                "progress": min(100, ((current_gdd - 200) / 550) * 100),
                "next_milestone": "개화",
                "next_gdd": 750
            }
    
    elif month in [4, 5]:
        return {
            "id": "flowering",
            "name": "개화기/착과기",
            "emoji": "🌸",
            "color": "stage-flowering",
            "progress": min(100, ((current_gdd - 750) / 250) * 100) if current_gdd >= 750 else 0,
            "next_milestone": "착과 완료",
            "next_gdd": 1000
        }
    
    elif month in [6, 7, 8, 9, 10]:
        return {
            "id": "fruiting",
            "name": "과실 비대기",
            "emoji": "🥝",
            "color": "stage-fruiting",
            "progress": ((month - 6) / 4) * 100,
            "next_milestone": "수확",
            "next_gdd": 0
        }
    
    else:  # 11, 12월
        return {
            "id": "harvest",
            "name": "수확 후 관리",
            "emoji": "📦",
            "color": "stage-harvest",
            "progress": 100,
            "next_milestone": "내년 준비",
            "next_gdd": 0
        }

# ============================================================
# AI 모델 (간단한 다중 회귀)
# ============================================================
class SimpleMultipleRegression:
    def __init__(self):
        self.coefficients = {}
        self.intercept = 0
        self.feature_names = []
        self.is_trained = False
        self.training_score = 0
        self.X_mean = None
        self.X_std = None
        
    def fit(self, X_list, y_list):
        try:
            if len(X_list) < 3:
                return False, f"데이터 부족: {len(X_list)}개"
            
            self.feature_names = list(X_list[0].keys())
            X = np.array([[x[f] for f in self.feature_names] for x in X_list])
            y = np.array(y_list)
            
            self.X_mean = X.mean(axis=0)
            self.X_std = X.std(axis=0) + 1e-8
            X_norm = (X - self.X_mean) / self.X_std
            y_mean = y.mean()
            
            XtX = X_norm.T @ X_norm
            XtX_inv = np.linalg.inv(XtX + np.eye(len(self.feature_names)) * 0.01)
            weights_norm = XtX_inv @ X_norm.T @ (y - y_mean)
            
            self.coefficients = {
                self.feature_names[i]: weights_norm[i] / self.X_std[i]
                for i in range(len(self.feature_names))
            }
            
            self.intercept = y_mean - sum(
                self.coefficients[f] * self.X_mean[i] 
                for i, f in enumerate(self.feature_names)
            )
            
            y_pred = np.array([self.predict(X_list[i]) for i in range(len(X_list))])
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - y_mean) ** 2)
            self.training_score = max(0, 1 - (ss_res / ss_tot)) if ss_tot > 0 else 0
            self.is_trained = True
            
            return True, f"학습 완료 (R²: {self.training_score*100:.1f}%)"
        except:
            return False, "학습 실패"
    
    def predict(self, X_dict):
        if not self.is_trained:
            return None
        prediction = self.intercept
        for feat in self.feature_names:
            prediction += X_dict.get(feat, 0) * self.coefficients[feat]
        return max(0, prediction)
    
    def to_dict(self):
        return {
            'coefficients': self.coefficients,
            'intercept': float(self.intercept),
            'feature_names': self.feature_names,
            'is_trained': self.is_trained,
            'training_score': float(self.training_score),
            'X_mean': self.X_mean.tolist() if self.X_mean is not None else [],
            'X_std': self.X_std.tolist() if self.X_std is not None else []
        }
    
    @classmethod
    def from_dict(cls, data):
        model = cls()
        model.coefficients = data['coefficients']
        model.intercept = data['intercept']
        model.feature_names = data['feature_names']
        model.is_trained = data['is_trained']
        model.training_score = data['training_score']
        model.X_mean = np.array(data['X_mean'])
        model.X_std = np.array(data['X_std'])
        return model

# ============================================================
# 헤더
# ============================================================
stage = get_current_growth_stage()

st.markdown(f"""
<div style="padding: 1.5rem; background: var(--card); border-bottom: 1px solid var(--border); margin-bottom: 1rem;">
    <h1 style="margin:0; color: var(--text);">🥝 키위 농장 AI 관리 시스템</h1>
    <p style="margin:5px 0 10px 0; color: var(--muted);">{TODAY.strftime('%Y년 %m월 %d일')}</p>
    <span class="stage-badge {stage['color']}">{stage['emoji']} {stage['name']}</span>
</div>
""", unsafe_allow_html=True)

# ============================================================
# 홈 탭 (생육 단계별 대시보드)
# ============================================================
def home_dashboard():
    stage = get_current_growth_stage()
    gdd_data = load_json(GDD_FILE)
    sensor_data = load_json(SENSOR_FILE)
    
    # 현재 GDD
    current_gdd = gdd_data[-1].get("accumulated_gdd", 0) if gdd_data else 0
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"### {stage['emoji']} 현재 생육 단계: {stage['name']}")
    
    if stage['next_gdd'] > 0:
        remaining = stage['next_gdd'] - current_gdd
        st.metric("다음 단계까지", f"{remaining:.1f}°C·일 남음")
        st.progress(stage['progress'] / 100, text=f"{stage['progress']:.0f}% 진행")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 단계별 핵심 지표
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 📊 핵심 지표")
    
    c1, c2, c3 = st.columns(3)
    
    if gdd_data:
        c1.metric("누적 GDD", f"{current_gdd:.1f}°C·일")
    
    if sensor_data:
        latest = sensor_data[-1]
        c2.metric("평균 온도", f"{latest['outdoor_temp']:.1f}°C")
        c3.metric("평균 수분", f"{latest['moisture_2dong']:.0f}%")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 단계별 안내
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 💡 이번 단계 관리 포인트")
    
    if stage['id'] == 'dormancy':
        st.info("🌱 발아 준비 중입니다. 저온 관리에 주의하세요.")
        st.caption("• 적산온도 200°C·일 도달 시 발아 시작 예상")
        st.caption("• 저온 쇼크 (8°C 이하) 주의")
    
    elif stage['id'] == 'flowering':
        st.info("🌸 개화기입니다. 수분 활동과 온도 관리가 중요합니다.")
        st.caption("• 최적 인공수분 시간: 오전 9~11시")
        st.caption("• 야간 온도 15°C 이상 유지")
    
    elif stage['id'] == 'fruiting':
        st.info("🥝 과실이 성장 중입니다. 주기적으로 크기를 측정하세요.")
        st.caption("• 주 1회 횡경 측정 권장")
        st.caption("• 수분 관리 철저 (40-45% 유지)")
    
    elif stage['id'] == 'harvest':
        st.info("📦 수확 시즌입니다. 당도를 확인하세요.")
        st.caption("• Brix 14° 이상 확인 후 수확")
        st.caption("• 내년 데이터 분석 및 계획 수립")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# 센서 탭
# ============================================================
def sensor_tab():
    st.markdown("## 📡 센서 모니터링")
    
    sensor_data = load_json(SENSOR_FILE)
    
    if not sensor_data:
        st.info("📊 GitHub Actions가 매일 자동으로 데이터를 수집합니다")
        return
    
    latest = sensor_data[-1]
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"### 최근 데이터 ({latest['date']})")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("실외 온도", f"{latest['outdoor_temp']:.1f}°C")
    c2.metric("2동 온도", f"{latest['temp_2dong']:.1f}°C")
    c3.metric("3동 온도", f"{latest['temp_3dong']:.1f}°C")
    c4.metric("토양 온도", f"{latest['temp_soil']:.1f}°C")
    
    c1, c2 = st.columns(2)
    c1.metric("2동 수분", f"{latest['moisture_2dong']:.0f}%")
    c2.metric("3동 수분", f"{latest['moisture_3dong']:.0f}%")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 최근 7일 추이
    if len(sensor_data) >= 2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 📈 최근 추이")
        
        df = pd.DataFrame(sensor_data[-30:])
        df['date'] = pd.to_datetime(df['date'])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['date'], y=df['outdoor_temp'], name='실외 온도', line=dict(color='#FF9500', width=2)))
        fig.add_trace(go.Scatter(x=df['date'], y=df['temp_2dong'], name='2동 온도', line=dict(color='#34C759', width=2)))
        fig.add_trace(go.Scatter(x=df['date'], y=df['moisture_2dong'], name='2동 수분', line=dict(color='#007AFF', width=2), yaxis='y2'))
        
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(title='온도 (°C)'),
            yaxis2=dict(title='수분 (%)', overlaying='y', side='right')
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# 적산온도 탭
# ============================================================
def gdd_tab():
    st.markdown("## 🌡️ 적산온도 (GDD)")
    
    gdd_data = load_json(GDD_FILE)
    
    if not gdd_data:
        st.info("📊 데이터 수집 중입니다")
        return
    
    latest = gdd_data[-1]
    current_gdd = latest['accumulated_gdd']
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("누적 GDD", f"{current_gdd:.1f}°C·일")
    c2.metric("일일 증가", f"+{latest['daily_gdd']:.1f}")
    c3.metric("수집 일수", f"{len(gdd_data)}일")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 이정표
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 📍 생육 이정표")
    
    milestones = [
        {"name": "발아", "gdd": 200, "emoji": "🌱"},
        {"name": "개화", "gdd": 750, "emoji": "🌸"},
    ]
    
    for m in milestones:
        reached = current_gdd >= m['gdd']
        status = "✅" if reached else f"{((current_gdd/m['gdd'])*100):.0f}%"
        st.progress(min(1.0, current_gdd/m['gdd']), text=f"{m['emoji']} {m['name']} ({m['gdd']}°C·일): {status}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 그래프
    df = pd.DataFrame(gdd_data)
    df['date'] = pd.to_datetime(df['date'])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['accumulated_gdd'], mode='lines+markers', name='누적 GDD', line=dict(color='#34C759', width=3)))
    fig.add_hline(y=200, line_dash='dash', line_color='#FF9500', annotation_text='발아 (200)')
    fig.add_hline(y=750, line_dash='dash', line_color='#FF69B4', annotation_text='개화 (750)')
    
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis_title='누적 GDD (°C·일)'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# 생육 기록 탭
# ============================================================
def phenology_tab():
    st.markdown("## 📝 생육 기록")
    
    phenology = load_json(PHENOLOGY_FILE)
    year_str = str(TODAY.year)
    
    if year_str not in phenology:
        phenology[year_str] = {}
    
    year_data = phenology[year_str]
    
    # 이벤트 추가
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### ➕ 새 이벤트 기록")
    
    with st.form("phenology_form"):
        event_date = st.date_input("날짜", value=TODAY)
        event_type = st.selectbox("이벤트", ["개화 시작", "개화 피크", "착과 확인", "적과 완료", "수확 시작"])
        notes = st.text_input("메모 (선택)", placeholder="예: 80% 개화 확인")
        
        if st.form_submit_button("💾 저장", type="primary"):
            event_key = event_type.replace(" ", "_").lower()
            year_data[event_key] = {
                "date": event_date.strftime("%Y-%m-%d"),
                "notes": notes,
                "manual_entry": True
            }
            
            if save_json(PHENOLOGY_FILE, phenology):
                st.success("✅ 저장 완료")
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 기록 표시
    if year_data:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 📅 올해 생육 기록")
        
        for key, value in sorted(year_data.items(), key=lambda x: x[1].get('date', '')):
            event_name = key.replace("_", " ").title()
            event_date = value.get('date', '')
            notes = value.get('notes', '')
            auto = value.get('auto_detected', False)
            
            badge = "🤖 자동" if auto else "✍️ 수동"
            st.text(f"{event_date} | {event_name} {badge}")
            if notes:
                st.caption(f"   💬 {notes}")
        
        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# AI 예측 탭
# ============================================================
def ai_tab():
    st.markdown("## 🤖 AI 예측")
    
    stage = get_current_growth_stage()
    
    # 단계별 다른 AI 표시
    if stage['id'] in ['dormancy', 'pre_flowering']:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 🌱 발아/개화 예측")
        
        gdd_data = load_json(GDD_FILE)
        if gdd_data and len(gdd_data) >= 7:
            current_gdd = gdd_data[-1]['accumulated_gdd']
            recent = gdd_data[-7:]
            avg_daily = np.mean([r['daily_gdd'] for r in recent])
            
            if avg_daily > 0:
                days_to_bud = int((200 - current_gdd) / avg_daily) if current_gdd < 200 else 0
                days_to_flower = int((750 - current_gdd) / avg_daily) if current_gdd < 750 else 0
                
                if days_to_bud > 0:
                    pred_date = (TODAY + timedelta(days=days_to_bud)).strftime('%m월 %d일')
                    st.success(f"🌱 발아 예상: {pred_date} (약 {days_to_bud}일 후)")
                elif days_to_flower > 0:
                    pred_date = (TODAY + timedelta(days=days_to_flower)).strftime('%m월 %d일')
                    st.success(f"🌸 개화 예상: {pred_date} (약 {days_to_flower}일 후)")
                else:
                    st.success("✅ 개화 단계 도달")
        else:
            st.info("📊 데이터 수집 중 (7일 이상 필요)")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    elif stage['id'] == 'flowering':
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 🌸 착과율 예측")
        st.info("개화기 환경 데이터를 기반으로 착과율을 예측합니다")
        
        sensor_data = load_json(SENSOR_FILE)
        if len(sensor_data) >= 7:
            recent = sensor_data[-7:]
            avg_temp = np.mean([s['outdoor_temp'] for s in recent])
            avg_humid = np.mean([s['outdoor_humid'] for s in recent])
            
            # 간단한 착과율 예측 (실제로는 더 정교한 모델 필요)
            base_rate = 75
            temp_factor = max(0, min(10, (avg_temp - 15) * 2))
            humid_factor = max(0, min(10, (70 - abs(avg_humid - 70)) / 7))
            
            predicted_rate = min(95, base_rate + temp_factor + humid_factor)
            
            st.metric("예상 착과율", f"{predicted_rate:.0f}%")
            
            if predicted_rate >= 80:
                st.success("🎉 우수한 착과율 예상")
            elif predicted_rate >= 70:
                st.info("📊 양호한 착과율 예상")
            else:
                st.warning("⚠️ 환경 관리 필요")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    elif stage['id'] == 'fruiting':
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 🥝 과실 성장 예측")
        
        # 기존 성장 예측 모델
        growth_data = load_json(GROWTH_FILE)
        sensor_data = load_json(SENSOR_FILE)
        
        if len(sensor_data) >= 3 and len(growth_data) >= 3:
            st.info("✅ AI 모델 학습 가능")
            
            if st.button("🚀 모델 학습", type="primary"):
                st.info("학습 기능은 과실 측정 데이터 입력 후 사용 가능합니다")
        else:
            st.info(f"📊 데이터 수집 중 (센서: {len(sensor_data)}/3, 성장: {len(growth_data)}/3)")
        
        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# 탭 구조
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 홈", "📡 센서", "🌡️ 적산온도", "📝 생육 기록", "🤖 AI 예측"])

with tab1:
    home_dashboard()

with tab2:
    sensor_tab()

with tab3:
    gdd_tab()

with tab4:
    phenology_tab()

with tab5:
    ai_tab()

# 사이드바
with st.sidebar:
    st.markdown("### ℹ️ 시스템 정보")
    
    sensor_count = len(load_json(SENSOR_FILE))
    gdd_count = len(load_json(GDD_FILE))
    
    st.metric("센서 데이터", f"{sensor_count}일")
    st.metric("GDD 데이터", f"{gdd_count}일")
    
    stage = get_current_growth_stage()
    st.info(f"현재: {stage['emoji']} {stage['name']}")
    
    st.caption("🤖 GitHub Actions가 매일 자동 수집")
    
    if st.button("🔄 새로고침"):
        st.rerun()

# 🚀 5분 설치 가이드

## ✅ 준비물
- GitHub 계정
- ECOWITT API 키 (이미 있음)

---

## 1️⃣ GitHub 저장소 생성 (2분)

### 방법 A: 웹에서 업로드
1. GitHub 접속 → **New repository**
2. 이름: `kiwi-farm-ai`
3. Public 선택 → **Create**
4. **Upload files** 클릭
5. 압축 푼 모든 파일 드래그 & 드롭
6. **Commit** 클릭

### 방법 B: Git 명령어
```bash
cd kiwi-integrated-system
git init
git add .
git commit -m "🥝 Initial"
git remote add origin https://github.com/당신아이디/kiwi-farm-ai.git
git push -u origin main
```

---

## 2️⃣ GitHub Secrets 설정 (2분)

1. 저장소 → **Settings**
2. 왼쪽 → **Secrets and variables** → **Actions**
3. **New repository secret** 클릭

**3개 입력:**

```
Name: ECOWITT_APP_KEY
Value: A173F6BFBBBD80ABB1F3E85E63C694E3

Name: ECOWITT_API_KEY
Value: 963717d1-764c-47f8-aecf-ffddebddba03

Name: ECOWITT_MAC
Value: 30:83:98:A7:26:4F
```

---

## 3️⃣ GitHub Actions 활성화 (30초)

1. **Actions** 탭
2. **I understand my workflows, go ahead and enable them** 클릭

---

## 4️⃣ 테스트 (1분)

1. **Actions** 탭
2. **Daily Data Collection & Analysis** 클릭
3. **Run workflow** → **Run workflow**
4. 1분 대기 → 초록색 체크 ✅
5. 저장소 → `data/sensor_history.json` 확인

---

## 5️⃣ Streamlit 배포 (2분)

1. https://share.streamlit.io/
2. **New app**
3. Repository: `당신아이디/kiwi-farm-ai`
4. Branch: `main`
5. Main file: `app.py`
6. **Deploy!**

---

## ✅ 완료!

앱 URL: `https://당신앱이름.streamlit.app`

---

## 🎯 다음 단계

1. **매일 확인**: 데이터 자동 수집 확인
2. **생육 기록**: 중요 이벤트 기록
3. **과실 측정**: 6월부터 주 1회

---

## ❓ 문제 발생 시

### Actions 실행 안 됨
→ Secrets 3개 정확히 입력했는지 확인

### 데이터 안 쌓임
→ Actions 탭에서 로그 확인

### 앱 오류
→ Streamlit 앱 재배포

---

**총 소요 시간: 약 7분**

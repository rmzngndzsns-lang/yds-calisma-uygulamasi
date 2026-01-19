import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import google.generativeai as genai
import edge_tts
import asyncio
import os
import re
import nest_asyncio

# Döngü yaması
nest_asyncio.apply()

# --- 1. AYARLAR ---
st.set_page_config(page_title="YDS Pro LMS", page_icon="🎓", layout="wide")

# --- 2. PREMIUM CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Poppins', sans-serif; background-color: #f4f6f9; }
    
    .login-container {
        max-width: 500px; margin: 80px auto; padding: 40px;
        background: white; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.08);
        text-align: center; border: 1px solid #eef2f6;
    }
    
    .passage-box { 
        background-color: #ffffff; padding: 30px; border-radius: 12px; height: 60vh; 
        overflow-y: auto; font-size: 16px; line-height: 1.8; 
        border: 1px solid #dfe6e9; color: #2d3436; font-family: 'Georgia', serif; 
    }
    .question-stem { 
        font-size: 18px; font-weight: 600; background-color: #ffffff; padding: 25px; 
        border-radius: 12px; border-left: 5px solid #0984e3; margin-bottom: 25px; 
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    }
    
    div.stButton > button { width: 100%; border-radius: 8px; font-weight: 600; height: 45px; }
    
    .analysis-report {
        background-color: #fff; border: 2px solid #6c5ce7; border-radius: 15px;
        padding: 25px; margin-top: 20px; box-shadow: 0 5px 15px rgba(108, 92, 231, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- 3. VERİ YÖNETİMİ ---
SCORES_FILE = "lms_scores.csv"

def save_score_to_csv(username, exam_name, score, correct, wrong, empty):
    if os.path.exists(SCORES_FILE):
        try: df = pd.read_csv(SCORES_FILE)
        except: df = pd.DataFrame(columns=["Kullanıcı", "Sınav", "Puan", "Doğru", "Yanlış", "Boş", "Tarih"])
    else:
        df = pd.DataFrame(columns=["Kullanıcı", "Sınav", "Puan", "Doğru", "Yanlış", "Boş", "Tarih"])

    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    mask = (df["Kullanıcı"] == username) & (df["Sınav"] == exam_name)
    
    if mask.any():
        df.loc[mask, ["Puan", "Doğru", "Yanlış", "Boş", "Tarih"]] = [score, correct, wrong, empty, date_str]
    else:
        new_row = pd.DataFrame({"Kullanıcı": [username], "Sınav": [exam_name], "Puan": [score], "Doğru": [correct], "Yanlış": [wrong], "Boş": [empty], "Tarih": [date_str]})
        df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(SCORES_FILE, index=False)

def get_leaderboard_pivot():
    if not os.path.exists(SCORES_FILE): return None
    try:
        df = pd.read_csv(SCORES_FILE)
        if df.empty: return None
        pivot_df = df.pivot_table(index="Kullanıcı", columns="Sınav", values="Puan", aggfunc="max").fillna("-")
        numeric_df = pivot_df.replace("-", 0)
        pivot_df["ORTALAMA"] = numeric_df.mean(axis=1).round(2)
        return pivot_df.sort_values(by="ORTALAMA", ascending=False)
    except: return None

# --- 4. SESSION INITIALIZATION ---
def init_session():
    if 'username' not in st.session_state: st.session_state.username = None
    if 'selected_exam_id' not in st.session_state: st.session_state.selected_exam_id = 1
    if 'exam_files' not in st.session_state: st.session_state.exam_files = {} # Yüklenen dosyaları tutar
    if 'idx' not in st.session_state: st.session_state.idx = 0
    if 'answers' not in st.session_state: st.session_state.answers = {}
    if 'marked' not in st.session_state: st.session_state.marked = set()
    if 'end_timestamp' not in st.session_state: st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000 
    if 'finish' not in st.session_state: st.session_state.finish = False
    if 'data_saved' not in st.session_state: st.session_state.data_saved = False 
    if 'gemini_res' not in st.session_state: st.session_state.gemini_res = {} 
    if 'analysis_report' not in st.session_state: st.session_state.analysis_report = None
    if 'user_api_key' not in st.session_state: st.session_state.user_api_key = ""

init_session()

# --- 5. GİRİŞ EKRANI ---
if st.session_state.username is None:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="login-container"><h2>🎓 YDS LMS Giriş</h2><p>Hoş geldiniz, lütfen isminizi girin.</p></div>', unsafe_allow_html=True)
        name = st.text_input("Ad Soyad:")
        if st.button("🚀 Giriş Yap", type="primary"):
            if name.strip(): st.session_state.username = name.strip(); st.rerun()
            else: st.error("İsim boş bırakılamaz.")
    st.stop()

# --- 6. SİDEBAR ---
with st.sidebar:
    st.success(f"👤 {st.session_state.username}")
    
    st.markdown("### 📚 Sınav Seçimi")
    exam_id = st.selectbox("Sınav Seç:", range(1, 11), format_func=lambda x: f"YDS Deneme {x}")
    
    if exam_id != st.session_state.selected_exam_id:
        st.session_state.selected_exam_id = exam_id
        st.session_state.answers, st.session_state.marked, st.session_state.idx = {}, set(), 0
        st.session_state.finish, st.session_state.data_saved = False, False
        st.session_state.gemini_res, st.session_state.analysis_report = {}, None
        st.rerun()

    # DOSYA YÜKLEME ALANI
    if st.session_state.selected_exam_id not in st.session_state.exam_files:
        st.warning(f"Sınav {st.session_state.selected_exam_id} yüklü değil.")
        uploaded_file = st.file_uploader(f"Deneme {st.session_state.selected_exam_id} Dosyasını Yükle (.xlsx veya .csv)", type=['xlsx', 'csv'])
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.xlsx'): df_new = pd.read_excel(uploaded_file, engine='openpyxl')
                else: df_new = pd.read_csv(uploaded_file)
                df_new.columns = df_new.columns.str.strip()
                if 'Dogru_Cevap' in df_new.columns: df_new['Dogru_Cevap'] = df_new['Dogru_Cevap'].astype(str).str.strip().str.upper()
                st.session_state.exam_files[st.session_state.selected_exam_id] = df_new
                st.success("Yüklendi! Başlatılıyor...")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Hata: {e}")
    
    st.write("---")
    st.info("🔑 API Anahtarı")
    api_key = st.text_input("Gemini Key:", type="password", value=st.session_state.user_api_key)
    if st.button("💾 Kaydet"):
        st.session_state.user_api_key = api_key.strip()
        st.success("Kaydedildi!")

    # NAVİGASYON
    if st.session_state.selected_exam_id in st.session_state.exam_files:
        df = st.session_state.exam_files[st.session_state.selected_exam_id]
        st.write("---")
        st.markdown("### 🗺️ Harita")
        cols = st.columns(5)
        for i in range(len(df)):
            u_a = st.session_state.answers.get(i)
            lbl = f"{i+1} ✅" if u_a and u_a == df.iloc[i]['Dogru_Cevap'] else f"{i+1} ❌" if u_a else f"{i+1} ⭐" if i in st.session_state.marked else str(i+1)
            if cols[i % 5].button(lbl, key=f"n_{i}", type="primary" if i == st.session_state.idx else "secondary"):
                st.session_state.idx = i; st.rerun()
        
        if not st.session_state.finish and st.button("🏁 BİTİR", type="primary"):
            st.session_state.finish = True; st.rerun()

# --- 7. ANA EKRAN ---
def get_ai_response(prompt):
    if not st.session_state.user_api_key: return "⚠️ API Key girin."
    try:
        genai.configure(api_key=st.session_state.user_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        return model.generate_content(prompt).text
    except Exception as e: return f"HATA: {e}"

if st.session_state.selected_exam_id in st.session_state.exam_files:
    df = st.session_state.exam_files[st.session_state.selected_exam_id]
    if not st.session_state.finish:
        # SORU EKRANI
        row = df.iloc[st.session_state.idx]
        st.title(f"Soru {st.session_state.idx + 1}")
        
        # Paragraf kontrolü
        q_text = str(row['Soru']).replace('\\n', '\n')
        passage, stem = (q_text.split('\n\n', 1) if '\n\n' in q_text else (None, q_text))
        
        if passage:
            l, r = st.columns(2)
            l.markdown(f"<div class='passage-box'>{passage}</div>", unsafe_allow_html=True)
            with r:
                st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
                opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
                sel = st.radio("Cevap:", opts, index=next((i for i,v in enumerate(opts) if v.startswith(st.session_state.answers.get(st.session_state.idx, "")+")")), None))
                if sel: st.session_state.answers[st.session_state.idx] = sel.split(")")[0]
        else:
            st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
            opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
            sel = st.radio("Cevap:", opts, index=next((i for i,v in enumerate(opts) if v.startswith(st.session_state.answers.get(st.session_state.idx, "")+")")), None))
            if sel: st.session_state.answers[st.session_state.idx] = sel.split(")")[0]

        if st.button("🤖 AI Çözümle"):
            with st.spinner("Düşünüyor..."):
                prompt = f"YDS Soru Analizi: {q_text}. Şıklar: {opts}. Doğru: {row['Dogru_Cevap']}. Strateji ve analiz ver."
                st.session_state.gemini_res[st.session_state.idx] = get_ai_response(prompt)
                st.rerun()
        
        if st.session_state.idx in st.session_state.gemini_res:
            st.info(st.session_state.gemini_res[st.session_state.idx])

    else:
        # SONUÇ EKRANI
        st.title("📊 Sınav Analizi")
        correct = sum(1 for i, a in st.session_state.answers.items() if a == df.iloc[i]['Dogru_Cevap'])
        wrong = len(st.session_state.answers) - correct
        empty = len(df) - len(st.session_state.answers)
        score = correct * 1.25
        
        if not st.session_state.data_saved:
            save_score_to_csv(st.session_state.username, f"Deneme {st.session_state.selected_exam_id}", score, correct, wrong, empty)
            st.session_state.data_saved = True
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Puan", score)
        c2.metric("Doğru", correct)
        c3.metric("Yanlış", wrong)
        c4.metric("Boş", empty)
        
        st.write("---")
        st.subheader("🏆 Liderlik Tablosu (Pivot)")
        st.dataframe(get_leaderboard_pivot(), use_container_width=True)
        
        if st.button("✨ AI Koçluk Analizi"):
            with st.spinner("Analiz ediliyor..."):
                p = f"Öğrenci {correct} doğru, {wrong} yanlış yaptı. YDS tavsiyesi ver."
                st.session_state.analysis_report = get_ai_response(p)
        if st.session_state.analysis_report:
            st.markdown(f"<div class='analysis-report'>{st.session_state.analysis_report}</div>", unsafe_allow_html=True)
else:
    st.info("Lütfen Sidebar'dan bir sınav dosyası yükleyin.")
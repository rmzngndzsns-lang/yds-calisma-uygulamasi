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

# --- 2. PREMIUM CSS (SİMETRİK VE MERKEZİ TASARIM) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    .stApp { font-family: 'Poppins', sans-serif; background-color: #f4f6f9; }
    
    /* SIDEBAR ESNEKLİĞİ */
    [data-testid="stSidebar"] { min-width: 320px !important; }

    /* GİRİŞ EKRANI - MERKEZİ VE KÜÇÜLTÜLMÜŞ BAR */
    .login-container {
        max-width: 400px; margin: 100px auto; padding: 40px;
        background: white; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.08);
        text-align: center; border: 1px solid #eef2f6;
    }
    
    /* Giriş input alanını küçültme ve butonu ortalama */
    div[data-testid="stForm"] { border: none !important; padding: 0 !important; }
    .stTextInput { max-width: 300px; margin: 0 auto; }
    
    .login-btn-container {
        display: flex;
        justify-content: center;
        margin-top: 20px;
    }

    /* OKUMA PARÇASI & SORU */
    .passage-box { 
        background-color: #ffffff; padding: 25px; border-radius: 12px; height: 55vh; 
        overflow-y: auto; font-size: 15px; line-height: 1.7; 
        border: 1px solid #dfe6e9; color: #2d3436; font-family: 'Georgia', serif; 
    }
    .question-stem { 
        font-size: 17px; font-weight: 600; background-color: #ffffff; padding: 20px; 
        border-radius: 12px; border-left: 6px solid #0984e3; margin-bottom: 20px; 
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    }

    /* --- SORU HARİTASI BUTONLARI (KESİN SİMETRİ) --- */
    /* 80 numaraya göre boyut sabitlendi */
    div[data-testid="column"] button {
        width: 55px !important;
        height: 55px !important;
        min-width: 55px !important;
        max-width: 55px !important;
        padding: 0px !important;
        margin: 2px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 11px !important; 
        border-radius: 8px !important;
        white-space: nowrap !important;
        line-height: 1 !important;
    }

    div[data-testid="column"] { padding: 0.5px !important; display: flex; justify-content: center; }

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
        return pivot_df
    except: return None

# --- 4. SESSION INITIALIZATION ---
def init_session():
    if 'username' not in st.session_state: st.session_state.username = None
    if 'selected_exam_id' not in st.session_state: st.session_state.selected_exam_id = 1
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

# --- 5. GELİŞMİŞ DOSYA BULUCU ---
def load_exam_file(exam_id):
    names = [f"Sinav_{exam_id}.xlsx", f"sinav_{exam_id}.xlsx", f"Sinav_{exam_id}.csv", f"sinav_{exam_id}.csv"]
    for name in names:
        if os.path.exists(name):
            try:
                df = pd.read_excel(name, engine='openpyxl') if name.endswith('xlsx') else pd.read_csv(name)
                df.columns = df.columns.str.strip()
                if 'Dogru_Cevap' in df.columns:
                    df['Dogru_Cevap'] = df['Dogru_Cevap'].astype(str).str.strip().str.upper()
                return df
            except: continue
    return None

# --- 6. GİRİŞ EKRANI ---
if st.session_state.username is None:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="login-container"><h2>🎓 YDS LMS Giriş</h2><p>Hoş geldiniz! Lütfen bilgilerinizi girin.</p></div>', unsafe_allow_html=True)
        # Giriş barını daraltmak için div içinde kullanıyoruz
        with st.container():
            name = st.text_input("Ad Soyad:", placeholder="İsminizi yazın...")
            # Butonu ortalamak için kolonlar
            cb1, cb2, cb3 = st.columns([1, 1, 1])
            with cb2:
                if st.button("🚀 Giriş Yap", type="primary", use_container_width=True):
                    if name.strip(): st.session_state.username = name.strip(); st.rerun()
                    else: st.error("İsim gerekli.")
    st.stop()

# --- 7. SİDEBAR ---
with st.sidebar:
    st.success(f"👤 {st.session_state.username}")
    
    st.markdown("### 📚 Sınav Listesi")
    exam_id = st.selectbox("Bir sınav seçin:", range(1, 11), format_func=lambda x: f"YDS Deneme {x}", index=st.session_state.selected_exam_id - 1)
    
    if exam_id != st.session_state.selected_exam_id:
        st.session_state.selected_exam_id = exam_id
        st.session_state.answers, st.session_state.marked, st.session_state.idx = {}, set(), 0
        st.session_state.finish, st.session_state.data_saved = False, False
        st.session_state.gemini_res, st.session_state.analysis_report = {}, None
        st.rerun()

    df = load_exam_file(st.session_state.selected_exam_id)
    
    st.write("---")
    st.info("🔑 Yapay Zeka")
    key = st.text_input("Gemini API Key:", type="password", value=st.session_state.user_api_key)
    if st.button("💾 Anahtarı Kaydet"):
        st.session_state.user_api_key = key.strip()
        st.success("Kaydedildi!")

    if df is not None:
        st.write("---")
        st.markdown("### 🗺️ Soru Haritası")
        for r in range(0, len(df), 5):
            cols = st.columns(5, gap="small")
            for c in range(5):
                q_idx = r + c
                if q_idx < len(df):
                    u_a = st.session_state.answers.get(q_idx)
                    lbl = str(q_idx + 1)
                    if u_a: lbl += " ✅" if u_a == df.iloc[q_idx]['Dogru_Cevap'] else " ❌"
                    elif q_idx in st.session_state.marked: lbl += " ⭐"
                    
                    if cols[c].button(lbl, key=f"nav_{q_idx}", type="primary" if q_idx == st.session_state.idx else "secondary"):
                        st.session_state.idx = q_idx; st.rerun()
        
        st.write("---")
        if not st.session_state.finish and st.button("🏁 SINAVI BİTİR", type="primary"):
            st.session_state.finish = True; st.rerun()

# --- 8. ANA EKRAN ---
if df is not None:
    if not st.session_state.finish:
        row = df.iloc[st.session_state.idx]
        st.subheader(f"Soru {st.session_state.idx + 1}")
        
        q_raw = str(row['Soru']).replace('\\n', '\n')
        passage, stem = (q_raw.split('\n\n', 1) if '\n\n' in q_raw else (None, q_raw))
        
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

        if st.button("🤖 Gemini 2.5 Çözümle"):
            if not st.session_state.user_api_key: st.error("Key girin.")
            else:
                with st.spinner("Analiz ediliyor..."):
                    genai.configure(api_key=st.session_state.user_api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    res = model.generate_content(f"Soru: {q_raw}. Doğru: {row['Dogru_Cevap']}. Analiz et.").text
                    st.session_state.gemini_res[st.session_state.idx] = res
                    st.rerun()
        
        if st.session_state.idx in st.session_state.gemini_res:
            st.info(st.session_state.gemini_res[st.session_state.idx])
    else:
        st.title("📊 Sonuç Analizi")
        correct = sum(1 for i, a in st.session_state.answers.items() if a == df.iloc[i]['Dogru_Cevap'])
        score = correct * 1.25
        if not st.session_state.data_saved:
            save_score_to_csv(st.session_state.username, f"Deneme {st.session_state.selected_exam_id}", score, correct, len(st.session_state.answers)-correct, len(df)-len(st.session_state.answers))
            st.session_state.data_saved = True
        
        st.metric("Toplam Puan", score)
        st.write("---")
        st.subheader("🏆 Liderlik Tablosu")
        st.dataframe(get_leaderboard_pivot(), use_container_width=True)
        
        if st.button("🔄 Yeniden Başlat"):
            st.session_state.answers, st.session_state.idx, st.session_state.finish, st.session_state.data_saved = {}, 0, False, False
            st.rerun()
else:
    st.warning(f"⚠️ Klasörde 'Sinav_{st.session_state.selected_exam_id}.xlsx' dosyası bulunamadı.")
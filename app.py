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

# --- 2. PROFESYONEL CSS (YATAY YAYILMAYI ENGELLEYEN TASARIM) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    .stApp { font-family: 'Poppins', sans-serif; background-color: #f8fafc; }
    
    /* SIDEBAR GENİŞLİĞİNİ SABİTLEME */
    section[data-testid="stSidebar"] {
        min-width: 280px !important;
        max-width: 280px !important;
    }

    /* GİRİŞ EKRANI */
    .login-wrapper { max-width: 450px; margin: 80px auto; }
    .login-container {
        padding: 35px; background: white; border-radius: 20px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.08); text-align: center; 
        border: 1px solid #eef2f6; margin-bottom: 20px;
    }

    /* --- SORU HARİTASI BUTONLARI (KESİN SİMETRİ VE YATAY KORUMA) --- */
    /* stSidebar içindeki tüm butonları küçük karelere zorla */
    section[data-testid="stSidebar"] button {
        width: 42px !important; 
        height: 42px !important;
        min-width: 42px !important;
        max-width: 42px !important;
        padding: 0px !important;
        margin: 1px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 10px !important; 
        font-weight: 700 !important;
        border-radius: 8px !important;
        white-space: nowrap !important;
        line-height: 1 !important;
        overflow: hidden !important;
    }

    /* Streamlit'in kolonlar arasındaki o büyük boşlukları yok et */
    [data-testid="column"] {
        width: fit-content !important;
        flex: unset !important;
        min-width: unset !important;
        padding: 0px !important;
        margin: 0px !important;
    }
    
    /* Yan yana dizilimi daha sıkı yap */
    [data-testid="stHorizontalBlock"] {
        gap: 2px !important;
        justify-content: center !important;
    }

    /* Okuma parçası ve soru kutuları */
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
        return df.pivot_table(index="Kullanıcı", columns="Sınav", values="Puan", aggfunc="max").fillna("-")
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
    if 'user_api_key' not in st.session_state: st.session_state.user_api_key = ""

init_session()

# --- 5. GELİŞMİŞ DOSYA BULUCU ---
def load_exam_file(exam_id):
    names = [f"Sinav_{exam_id}.xlsx", f"sinav_{exam_id}.xlsx", f"Sinav_{exam_id}.csv"]
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
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
        st.markdown('<div class="login-container"><h2>🎓 YDS Pro LMS</h2><p>Giriş yaparak sınava başlayın.</p></div>', unsafe_allow_html=True)
        name = st.text_input("Ad Soyad:", placeholder="İsminizi yazın...")
        if st.button("🚀 Giriş Yap", type="primary"):
            if name.strip(): st.session_state.username = name.strip(); st.rerun()
            else: st.error("İsim gerekli.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 7. SİDEBAR ---
with st.sidebar:
    st.success(f"👤 {st.session_state.username}")
    
    st.markdown("📘 **SINAV SEÇ**")
    exam_id = st.selectbox("Sınav seç:", range(1, 11), format_func=lambda x: f"Deneme {x}", index=st.session_state.selected_exam_id - 1, label_visibility="collapsed")
    
    if exam_id != st.session_state.selected_exam_id:
        st.session_state.selected_exam_id = exam_id
        st.session_state.answers, st.session_state.marked, st.session_state.idx = {}, set(), 0
        st.session_state.finish, st.session_state.data_saved = False, False
        st.session_state.gemini_res = {}
        st.rerun()

    df = load_exam_file(st.session_state.selected_exam_id)
    
    st.write("---")
    st.markdown("🔑 **API KEY**")
    key = st.text_input("Gemini API Key:", type="password", value=st.session_state.user_api_key, label_visibility="collapsed")
    if st.button("💾 Kaydet", use_container_width=True):
        st.session_state.user_api_key = key.strip()
        st.success("Kaydedildi!")

    if df is not None:
        st.write("---")
        st.markdown("🗺️ **SORU HARİTASI**")
        # DAR VE KARE BUTON GRID SİSTEMİ
        for r in range(0, len(df), 5):
            cols = st.columns(5)
            for c in range(5):
                q_idx = r + c
                if q_idx < len(df):
                    u_a = st.session_state.answers.get(q_idx)
                    lbl = str(q_idx + 1)
                    if u_a: lbl += "✅" if u_a == df.iloc[q_idx]['Dogru_Cevap'] else "❌"
                    elif q_idx in st.session_state.marked: lbl += "⭐"
                    
                    if cols[c].button(lbl, key=f"nav_{q_idx}", type="primary" if q_idx == st.session_state.idx else "secondary"):
                        st.session_state.idx = q_idx; st.rerun()
        
        st.write("---")
        if not st.session_state.finish and st.button("🏁 BİTİR", type="primary", use_container_width=True):
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

        if st.button("🤖 Gemini 2.5 Flash Çözümle", use_container_width=True):
            if not st.session_state.user_api_key: st.error("API Key gerekli.")
            else:
                with st.spinner("Analiz..."):
                    genai.configure(api_key=st.session_state.user_api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    res = model.generate_content(f"Soru: {q_raw}. Doğru: {row['Dogru_Cevap']}. Analiz et.").text
                    st.session_state.gemini_res[st.session_state.idx] = res
                    st.rerun()
        
        if st.session_state.idx in st.session_state.gemini_res:
            st.info(st.session_state.gemini_res[st.session_state.idx])
    else:
        st.title("📊 Sonuçlar")
        correct = sum(1 for i, a in st.session_state.answers.items() if a == df.iloc[i]['Dogru_Cevap'])
        score = correct * 1.25
        if not st.session_state.data_saved:
            save_score_to_csv(st.session_state.username, f"Deneme {st.session_state.selected_exam_id}", score, correct, len(st.session_state.answers)-correct, len(df)-len(st.session_state.answers))
            st.session_state.data_saved = True
        
        st.metric("Puan", score)
        st.subheader("🏆 Liderlik")
        st.dataframe(get_leaderboard_pivot(), use_container_width=True)
        
        if st.button("🔄 Yeniden Başlat", use_container_width=True):
            st.session_state.answers, st.session_state.idx, st.session_state.finish, st.session_state.data_saved = {}, 0, False, False
            st.rerun()
else:
    st.warning("⚠️ Sinav_X.xlsx bulunamadı.")
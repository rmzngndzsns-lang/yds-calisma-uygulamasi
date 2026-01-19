import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import google.generativeai as genai
import os
import nest_asyncio

# Döngü yaması
nest_asyncio.apply()

# --- 1. AYARLAR & KONFIGURASYON ---
st.set_page_config(page_title="YDS Pro LMS", page_icon="🎓", layout="wide")

# --- 2. CSS (MÜKEMMELLEŞTİRİLMİŞ) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Poppins', sans-serif; background-color: #f8fafc; }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] { min-width: 300px !important; max-width: 300px !important; }

    /* LOGIN */
    .login-wrapper { max-width: 450px; margin: 80px auto; }
    .login-container {
        padding: 40px; background: white; border-radius: 20px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.08); text-align: center; 
        border: 1px solid #eef2f6; margin-bottom: 20px;
    }
    
    /* BUTONLAR (SORU HARİTASI) - SİMETRİK KARELER */
    div[data-testid="stSidebar"] div.stButton > button:not([kind="primary"]):not([kind="secondaryFormSubmit"]) {
        width: 44px !important; height: 44px !important; 
        min-width: 44px !important; max-width: 44px !important;
        padding: 0px !important; margin: 1px !important;
        display: inline-flex !important; align-items: center !important; justify-content: center !important;
        font-size: 11px !important; font-weight: 700 !important;
        border-radius: 8px !important; border: 1px solid #e2e8f0;
        white-space: nowrap !important; line-height: 1 !important; overflow: hidden !important;
    }
    
    /* AKTİF SORU BUTONU */
    div[data-testid="stSidebar"] button[kind="primary"] {
        background-color: #2563eb !important; border: none !important; color: white !important;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.4);
    }

    /* OKUMA ALANI */
    .passage-box { 
        background-color: #ffffff; padding: 30px; border-radius: 15px; 
        border: 1px solid #e2e8f0; color: #334155; font-family: 'Georgia', serif;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .question-stem { 
        font-size: 18px; font-weight: 600; background-color: #ffffff; padding: 25px; 
        border-radius: 15px; border-left: 5px solid #2563eb; margin-bottom: 25px;
        color: #1e293b; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }

    /* METRİKLER */
    [data-testid="stMetricValue"] { font-size: 24px !important; color: #2563eb !important; }
    
    /* ZAMANLAYICI */
    .timer-box {
        font-size: 20px; font-weight: bold; color: #dc2626; 
        text-align: center; padding: 10px; background: #fee2e2; 
        border-radius: 8px; margin-bottom: 10px; border: 1px solid #fecaca;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. VERİ VE DOSYA YÖNETİMİ ---
SCORES_FILE = "lms_scores.csv"

@st.cache_data(show_spinner=False)
def load_exam_file_cached(exam_id):
    """Dosya okumayı önbelleğe alır (Performans Artışı)"""
    names = [f"Sinav_{exam_id}.xlsx", f"sinav_{exam_id}.xlsx", f"Sinav_{exam_id}.csv"]
    for name in names:
        if os.path.exists(name):
            try:
                df = pd.read_excel(name, engine='openpyxl') if name.endswith('xlsx') else pd.read_csv(name)
                df.columns = df.columns.str.strip()
                if 'Dogru_Cevap' in df.columns: df['Dogru_Cevap'] = df['Dogru_Cevap'].astype(str).str.strip().str.upper()
                return df
            except: continue
    return None

def save_score_to_csv(username, exam_name, score, correct, wrong, empty):
    try:
        if os.path.exists(SCORES_FILE):
            df = pd.read_csv(SCORES_FILE)
        else:
            df = pd.DataFrame(columns=["Kullanıcı", "Sınav", "Puan", "Doğru", "Yanlış", "Boş", "Tarih"])
        
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        # Eski skoru güncelle veya yeni ekle
        mask = (df["Kullanıcı"] == username) & (df["Sınav"] == exam_name)
        if mask.any():
            df.loc[mask, ["Puan", "Doğru", "Yanlış", "Boş", "Tarih"]] = [score, correct, wrong, empty, date_str]
        else:
            new_row = pd.DataFrame({"Kullanıcı": [username], "Sınav": [exam_name], "Puan": [score], "Doğru": [correct], "Yanlış": [wrong], "Boş": [empty], "Tarih": [date_str]})
            df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(SCORES_FILE, index=False)
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

def get_user_progress(username):
    if not os.path.exists(SCORES_FILE): return None
    try:
        df = pd.read_csv(SCORES_FILE)
        user_df = df[df["Kullanıcı"] == username].sort_values("Tarih")
        return user_df
    except: return None

# --- 4. SESSION BAŞLATMA ---
def init_session():
    defaults = {
        'username': None, 'selected_exam_id': 1, 'idx': 0, 'answers': {}, 
        'marked': set(), 'finish': False, 'data_saved': False, 'gemini_res': {}, 
        'user_api_key': "", 'font_size': 16, 'exam_mode': False, # Yeni özellikler
        'start_time': None
    }
    for key, val in defaults.items():
        if key not in st.session_state: st.session_state[key] = val

init_session()

# --- 5. GİRİŞ EKRANI ---
if st.session_state.username is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-wrapper"><div class="login-container"><h2>🎓 YDS Pro</h2><p>Başarı yolculuğunuz burada başlıyor.</p></div>', unsafe_allow_html=True)
        name = st.text_input("Ad Soyad:", placeholder="İsminizi giriniz...")
        if st.button("🚀 Giriş Yap", type="primary"):
            if name.strip(): 
                st.session_state.username = name.strip()
                st.session_state.start_time = datetime.now() # Sayaç başlat
                st.rerun()
            else: st.error("Lütfen isminizi girin.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 6. SIDEBAR (NAVİGASYON & AYARLAR) ---
with st.sidebar:
    st.success(f"👤 **{st.session_state.username}**")
    
    # SAYAÇ (YENİ)
    if not st.session_state.finish:
        elapsed = datetime.now() - st.session_state.start_time
        remaining = timedelta(minutes=180) - elapsed
        if remaining.total_seconds() > 0:
            mm, ss = divmod(int(remaining.total_seconds()), 60)
            hh, mm = divmod(mm, 60)
            st.markdown(f"<div class='timer-box'>⏳ {hh:02}:{mm:02}:{ss:02}</div>", unsafe_allow_html=True)
        else:
            st.error("Süre Doldu!")

    # MOD SEÇİMİ (YENİ)
    st.caption("⚙️ Sınav Ayarları")
    mode = st.toggle("Sınav Modu (Cevapları Gizle)", value=st.session_state.exam_mode)
    if mode != st.session_state.exam_mode:
        st.session_state.exam_mode = mode
        st.rerun()

    exam_id = st.selectbox("Deneme Seç:", range(1, 11), format_func=lambda x: f"YDS Deneme {x}", index=st.session_state.selected_exam_id - 1)
    if exam_id != st.session_state.selected_exam_id:
        st.session_state.selected_exam_id = exam_id
        st.session_state.answers, st.session_state.marked, st.session_state.idx = {}, set(), 0
        st.session_state.finish, st.session_state.data_saved, st.session_state.gemini_res = False, False, {}
        st.session_state.start_time = datetime.now()
        st.rerun()

    df = load_exam_file_cached(st.session_state.selected_exam_id)

    # API KEY
    with st.expander("🔑 AI Anahtarı"):
        key_input = st.text_input("API Key:", type="password", value=st.session_state.user_api_key)
        if st.button("Kaydet"):
            st.session_state.user_api_key = key_input.strip()
            st.success("Kaydedildi.")

    # SORU HARİTASI
    if df is not None:
        st.write("---")
        st.markdown("**🗺️ Soru Haritası**")
        for r in range(0, len(df), 5):
            cols = st.columns(5)
            for c in range(5):
                q_idx = r + c
                if q_idx < len(df):
                    u_a = st.session_state.answers.get(q_idx)
                    lbl = str(q_idx + 1)
                    # Sınav modundaysak sadece doluluk göster, değilse D/Y göster
                    if u_a: 
                        if st.session_state.exam_mode: lbl += "🟦" # Dolu
                        else: lbl += "✅" if u_a == df.iloc[q_idx]['Dogru_Cevap'] else "❌"
                    elif q_idx in st.session_state.marked: lbl += "⭐"
                    
                    if cols[c].button(lbl, key=f"nav_{q_idx}", type="primary" if q_idx == st.session_state.idx else "secondary"):
                        st.session_state.idx = q_idx; st.rerun()
        
        st.write("")
        if not st.session_state.finish:
            if st.button("🏁 SINAVI BİTİR", type="primary", use_container_width=True):
                st.session_state.finish = True; st.rerun()

# --- 7. ANA EKRAN ---
if df is not None:
    if not st.session_state.finish:
        # ÜST BAR: Font Ayarı ve İşaretleme
        c1, c2, c3 = st.columns([6, 1, 1])
        c1.subheader(f"Soru {st.session_state.idx + 1}")
        with c2: 
            if st.button("🔠", help="Yazı Boyutunu Değiştir"):
                st.session_state.font_size = 20 if st.session_state.font_size == 16 else 16
                st.rerun()
        with c3:
            is_m = st.session_state.idx in st.session_state.marked
            if st.button("⭐" if is_m else "☆", help="İşaretle"):
                if is_m: st.session_state.marked.remove(st.session_state.idx)
                else: st.session_state.marked.add(st.session_state.idx)
                st.rerun()

        row = df.iloc[st.session_state.idx]
        q_raw = str(row['Soru']).replace('\\n', '\n')
        passage, stem = (q_raw.split('\n\n', 1) if '\n\n' in q_raw else (None, q_raw))
        
        # Paragraf varsa iki sütun, yoksa tek
        if passage:
            l, r = st.columns(2)
            # Font boyutu dinamik
            f_size = st.session_state.font_size
            l.markdown(f"<div class='passage-box' style='font-size:{f_size}px; line-height:{f_size*1.6}px'>{passage}</div>", unsafe_allow_html=True)
            main_col = r
        else: main_col = st

        with main_col:
            st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
            opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
            
            curr = st.session_state.answers.get(st.session_state.idx)
            sel_idx = next((i for i,v in enumerate(opts) if v.startswith(str(curr) + ")")), None)
            sel = st.radio("Cevap:", opts, index=sel_idx, key=f"ans_{st.session_state.idx}")
            
            if sel:
                chosen = sel.split(")")[0]
                st.session_state.answers[st.session_state.idx] = chosen
                
                # SINAV MODU KONTROLÜ: Eğer sınav modundaysak sonucu gösterme!
                if not st.session_state.exam_mode:
                    if chosen == row['Dogru_Cevap']: st.success("TEBRİKLER! DOĞRU CEVAP 🎉")
                    else: st.error(f"YANLIŞ! Doğru Cevap: {row['Dogru_Cevap']}")

        st.write("")
        # AI Analizi (Sınav Modunda Gizlenebilir veya Açık Bırakılabilir - Genelde açık kalması iyidir)
        if st.button("🤖 Gemini 2.5 Çözümle", use_container_width=True):
            if not st.session_state.user_api_key: st.warning("Lütfen Sidebar'dan API Anahtarı girin.")
            else:
                with st.spinner("Yapay Zeka soruyu inceliyor..."):
                    genai.configure(api_key=st.session_state.user_api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    prompt = f"YDS Sorusu: {q_raw}. Doğru: {row['Dogru_Cevap']}. Kelime analizi, çeviri ve çözüm stratejisi ver."
                    res = model.generate_content(prompt).text
                    st.session_state.gemini_res[st.session_state.idx] = res
                    st.rerun()

        # Navigasyon
        c_p, c_n = st.columns(2)
        if st.session_state.idx > 0 and c_p.button("⬅️ Önceki", use_container_width=True): 
            st.session_state.idx -= 1; st.rerun()
        if st.session_state.idx < len(df)-1 and c_n.button("Sonraki ➡️", use_container_width=True): 
            st.session_state.idx += 1; st.rerun()

        if st.session_state.idx in st.session_state.gemini_res:
            st.info(st.session_state.gemini_res[st.session_state.idx])

    else:
        # --- SONUÇ EKRANI (DASHBOARD) ---
        st.title("📊 Performans Raporu")
        
        correct = sum(1 for i, a in st.session_state.answers.items() if a == df.iloc[i]['Dogru_Cevap'])
        wrong = len(st.session_state.answers) - correct
        empty = len(df) - len(st.session_state.answers)
        score = correct * 1.25
        
        # Veriyi Kaydet
        if not st.session_state.data_saved:
            save_score_to_csv(st.session_state.username, f"Deneme {st.session_state.selected_exam_id}", score, correct, wrong, empty)
            st.session_state.data_saved = True
            if score > 50: st.balloons()

        # Metrik Kartları
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Puan", f"{score:.2f}")
        m2.metric("Doğru", correct, delta_color="normal")
        m3.metric("Yanlış", wrong, delta_color="inverse")
        m4.metric("Boş", empty, delta_color="off")

        # Gelişim Grafiği (YENİ)
        st.subheader("📈 Gelişim Grafiği")
        prog_df = get_user_progress(st.session_state.username)
        if prog_df is not None and not prog_df.empty:
            st.line_chart(prog_df.set_index("Sınav")["Puan"])
        else:
            st.info("Grafik için daha fazla deneme çözmelisiniz.")

        # Detaylı Tablo
        with st.expander("Detaylı Cevap Anahtarı"):
            res_data = []
            for i in range(len(df)):
                u_ans = st.session_state.answers.get(i, "-")
                real = df.iloc[i]['Dogru_Cevap']
                status = "✅" if u_ans == real else "❌" if u_ans != "-" else "⬜"
                res_data.append({"Soru": i+1, "Sizin Cevap": u_ans, "Doğru Cevap": real, "Durum": status})
            st.dataframe(pd.DataFrame(res_data), use_container_width=True)

        if st.button("🔄 Yeni Sınava Başla", type="primary", use_container_width=True):
            st.session_state.answers = {}
            st.session_state.idx = 0
            st.session_state.finish = False
            st.session_state.data_saved = False
            st.session_state.start_time = datetime.now()
            st.rerun()

else:
    st.warning("⚠️ Sınav dosyası bulunamadı. Lütfen 'Sinav_1.xlsx' dosyasını yükleyin.")
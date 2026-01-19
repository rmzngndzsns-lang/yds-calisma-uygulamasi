import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import google.generativeai as genai
import os
import nest_asyncio

# Döngü yaması
nest_asyncio.apply()

# --- 1. AYARLAR ---
st.set_page_config(page_title="YDS Pro", page_icon="🎓", layout="wide")

# --- 2. CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Poppins', sans-serif; background-color: #f8fafc; }
    
    section[data-testid="stSidebar"] { min-width: 300px !important; max-width: 300px !important; }

    .login-wrapper { max-width: 400px; margin: 80px auto; }
    .login-container {
        padding: 40px; background: white; border-radius: 20px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.08); text-align: center; 
        border: 1px solid #eef2f6; margin-bottom: 20px; width: 100%;
    }
    
    .stTextInput > div > div > input { width: 100% !important; }
    div.stButton > button { width: 100% !important; border-radius: 8px; font-weight: 600; }

    div[data-testid="stSidebar"] div[data-testid="column"] button {
        width: 44px !important; height: 44px !important;
        min-width: 44px !important; max-width: 44px !important;
        padding: 0px !important; margin: 1px !important;
        display: flex !important; align-items: center !important; justify-content: center !important;
        font-size: 11px !important; font-weight: 700 !important;
        border-radius: 8px !important; border: 1px solid #e2e8f0;
        white-space: nowrap !important; line-height: 1 !important; overflow: hidden !important;
    }

    div[data-testid="stSidebar"] div[data-testid="column"] {
        width: fit-content !important; flex: unset !important; min-width: unset !important; padding: 0px !important;
    }

    .passage-box { 
        background-color: #ffffff; padding: 25px; border-radius: 12px; height: 55vh; 
        overflow-y: auto; font-size: 15px; line-height: 1.7; border: 1px solid #dfe6e9; color: #2d3436; 
    }
    .question-stem { 
        font-size: 17px; font-weight: 600; background-color: #ffffff; padding: 20px; 
        border-radius: 12px; border-left: 5px solid #2563eb; margin-bottom: 20px; color: #1e293b;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. VERİ YÖNETİMİ ---
SCORES_FILE = "lms_scores.csv"

@st.cache_data(show_spinner=False)
def load_exam_file_cached(exam_id):
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
        if os.path.exists(SCORES_FILE): df = pd.read_csv(SCORES_FILE)
        else: df = pd.DataFrame(columns=["Kullanıcı", "Sınav", "Puan", "Doğru", "Yanlış", "Boş", "Tarih"])
        
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        mask = (df["Kullanıcı"] == username) & (df["Sınav"] == exam_name)
        if mask.any(): df.loc[mask, ["Puan", "Doğru", "Yanlış", "Boş", "Tarih"]] = [score, correct, wrong, empty, date_str]
        else:
            new_row = pd.DataFrame({"Kullanıcı": [username], "Sınav": [exam_name], "Puan": [score], "Doğru": [correct], "Yanlış": [wrong], "Boş": [empty], "Tarih": [date_str]})
            df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(SCORES_FILE, index=False)
    except: pass

def get_user_progress(username):
    if not os.path.exists(SCORES_FILE): return None
    try:
        df = pd.read_csv(SCORES_FILE)
        return df[df["Kullanıcı"] == username].sort_values("Tarih")
    except: return None

# --- 4. SESSION ---
defaults = {
    'username': None, 'selected_exam_id': 1, 'idx': 0, 'answers': {}, 
    'marked': set(), 'finish': False, 'data_saved': False, 'gemini_res': {}, 
    'user_api_key': "", 'font_size': 16, 'exam_mode': False,
    'end_timestamp': 0 # JS için bitiş zamanı (timestamp)
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# --- 5. GİRİŞ ---
if st.session_state.username is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-wrapper"><div class="login-container"><h2>🎓 YDS Pro</h2><p>Giriş yaparak başlayın.</p></div>', unsafe_allow_html=True)
        with st.form("login_form"):
            name = st.text_input("Ad Soyad:", placeholder="İsminizi giriniz...")
            submitted = st.form_submit_button("🚀 Giriş Yap")
            if submitted:
                if name.strip():
                    st.session_state.username = name.strip()
                    # 180 dakika sonrasını hesapla (JS için milisaniye cinsinden)
                    st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000
                    st.rerun()
                else: st.error("İsim gerekli.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.success(f"👤 **{st.session_state.username}**")
    
    # GERÇEK ZAMANLI SAYAÇ (JS ENTEGRASYONU)
    if not st.session_state.finish:
        # Bu HTML/JS bloğu tarayıcıda çalışır ve her saniye güncellenir
        components.html(
            f"""
            <div id="countdown" style="
                font-family: 'Poppins', sans-serif;
                font-size: 18px; 
                font-weight: bold; 
                color: #dc2626; 
                text-align: center; 
                padding: 8px; 
                background: #fee2e2; 
                border-radius: 8px; 
                border: 1px solid #fecaca;
            ">⏳ Hesapla...</div>
            <script>
                var dest = {st.session_state.end_timestamp};
                var x = setInterval(function() {{
                    var now = new Date().getTime();
                    var distance = dest - now;
                    var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                    var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                    document.getElementById("countdown").innerHTML = "⏳ " + 
                        (hours < 10 ? "0" + hours : hours) + ":" + 
                        (minutes < 10 ? "0" + minutes : minutes) + ":" + 
                        (seconds < 10 ? "0" + seconds : seconds);
                    if (distance < 0) {{
                        clearInterval(x);
                        document.getElementById("countdown").innerHTML = "SÜRE DOLDU";
                    }}
                }}, 1000);
            </script>
            """,
            height=60
        )

    mode = st.toggle("Sınav Modu (Cevabı Gizle)", value=st.session_state.exam_mode)
    if mode != st.session_state.exam_mode:
        st.session_state.exam_mode = mode
        st.rerun()

    exam_id = st.selectbox("Sınav Seç:", range(1, 11), format_func=lambda x: f"YDS Deneme {x}", index=st.session_state.selected_exam_id - 1)
    if exam_id != st.session_state.selected_exam_id:
        st.session_state.selected_exam_id = exam_id
        st.session_state.answers, st.session_state.marked, st.session_state.idx = {}, set(), 0
        st.session_state.finish, st.session_state.data_saved, st.session_state.gemini_res = False, False, {}
        # Sınav değişince süreyi sıfırla
        st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000
        st.rerun()

    df = load_exam_file_cached(st.session_state.selected_exam_id)

    with st.expander("🔑 AI Ayarları"):
        key_input = st.text_input("API Key:", type="password", value=st.session_state.user_api_key)
        if st.button("Kaydet"):
            st.session_state.user_api_key = key_input.strip()
            st.success("Kaydedildi.")

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
                    if u_a: 
                        if st.session_state.exam_mode: lbl += " 🟦"
                        else: lbl += " ✅" if u_a == df.iloc[q_idx]['Dogru_Cevap'] else " ❌"
                    elif q_idx in st.session_state.marked: lbl += " ⭐"
                    
                    if cols[c].button(lbl, key=f"nav_{q_idx}", type="primary" if q_idx == st.session_state.idx else "secondary"):
                        st.session_state.idx = q_idx; st.rerun()
        
        st.write("")
        if not st.session_state.finish:
            if st.button("🏁 SINAVI BİTİR", type="primary", use_container_width=True):
                st.session_state.finish = True; st.rerun()

# --- 7. ANA EKRAN ---
if df is not None:
    if not st.session_state.finish:
        c1, c2, c3 = st.columns([6, 1, 1])
        c1.subheader(f"Soru {st.session_state.idx + 1}")
        with c2: 
            if st.button("🔠", help="Yazı Boyutu"):
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
        
        if passage:
            l, r = st.columns(2)
            f_size = st.session_state.font_size
            l.markdown(f"<div class='passage-box' style='font-size:{f_size}px; line-height:{f_size*1.6}px'>{passage}</div>", unsafe_allow_html=True)
            main_col = r
        else: main_col = st.container()

        with main_col:
            st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
            opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
            
            curr = st.session_state.answers.get(st.session_state.idx)
            sel_idx = next((i for i,v in enumerate(opts) if v.startswith(str(curr) + ")")), None)
            sel = st.radio("Cevap:", opts, index=sel_idx, key=f"ans_{st.session_state.idx}")
            
            if sel:
                chosen = sel.split(")")[0]
                st.session_state.answers[st.session_state.idx] = chosen
                if not st.session_state.exam_mode:
                    if chosen == row['Dogru_Cevap']: st.success("TEBRİKLER! DOĞRU CEVAP 🎉")
                    else: st.error(f"YANLIŞ! Doğru Cevap: {row['Dogru_Cevap']}")

        st.write("")
        if st.button("🤖 Gemini 2.5 Çözümle", use_container_width=True):
            if not st.session_state.user_api_key: st.warning("API Key gerekli.")
            else:
                with st.spinner("Analiz ediliyor..."):
                    genai.configure(api_key=st.session_state.user_api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    res = model.generate_content(f"Soru: {q_raw}. Doğru: {row['Dogru_Cevap']}. Analiz et.").text
                    st.session_state.gemini_res[st.session_state.idx] = res
                    st.rerun()

        c_p, c_n = st.columns(2)
        if st.session_state.idx > 0 and c_p.button("⬅️ Önceki", use_container_width=True): 
            st.session_state.idx -= 1; st.rerun()
        if st.session_state.idx < len(df)-1 and c_n.button("Sonraki ➡️", use_container_width=True): 
            st.session_state.idx += 1; st.rerun()

        if st.session_state.idx in st.session_state.gemini_res:
            st.info(st.session_state.gemini_res[st.session_state.idx])

    else:
        st.title("📊 Performans Raporu")
        correct = sum(1 for i, a in st.session_state.answers.items() if a == df.iloc[i]['Dogru_Cevap'])
        wrong = len(st.session_state.answers) - correct
        empty = len(df) - len(st.session_state.answers)
        score = correct * 1.25
        
        if not st.session_state.data_saved:
            save_score_to_csv(st.session_state.username, f"Deneme {st.session_state.selected_exam_id}", score, correct, wrong, empty)
            st.session_state.data_saved = True
            if score > 50: st.balloons()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Puan", f"{score:.2f}")
        m2.metric("Doğru", correct)
        m3.metric("Yanlış", wrong)
        m4.metric("Boş", empty)

        st.subheader("📈 Gelişim Grafiği")
        prog_df = get_user_progress(st.session_state.username)
        if prog_df is not None and not prog_df.empty:
            st.line_chart(prog_df.set_index("Sınav")["Puan"])
        else: st.info("Grafik için daha fazla sınav çözmelisiniz.")

        with st.expander("Detaylı Cevaplar"):
            res_data = []
            for i in range(len(df)):
                u_ans = st.session_state.answers.get(i, "-")
                real = df.iloc[i]['Dogru_Cevap']
                status = "✅" if u_ans == real else "❌" if u_ans != "-" else "⬜"
                res_data.append({"Soru": i+1, "Cevap": u_ans, "Doğru": real, "Durum": status})
            st.dataframe(pd.DataFrame(res_data), use_container_width=True)

        if st.button("🔄 Yeni Sınava Başla", type="primary", use_container_width=True):
            st.session_state.answers = {}
            st.session_state.idx = 0
            st.session_state.finish = False
            st.session_state.data_saved = False
            # Yeni sınav için yeni süre başlat
            st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000
            st.rerun()

else: st.warning("⚠️ Sınav dosyası bulunamadı.")
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import google.generativeai as genai
import os
import nest_asyncio

# Döngü yaması
nest_asyncio.apply()

# --- 1. AYARLAR ---
st.set_page_config(page_title="YDS Pro", page_icon="🎓", layout="wide")

# --- 2. SESSION STATE (BAŞLANGIÇ AYARLARI) ---
defaults = {
    'username': None, 'selected_exam_id': 1, 'idx': 0, 'answers': {}, 
    'marked': set(), 'finish': False, 'data_saved': False, 'gemini_res': {}, 
    'user_api_key': "", 'font_size': 18, 'exam_mode': False, 'end_timestamp': 0
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# --- 3. CSS (KESİN VE SABİT ÖLÇÜLER) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Poppins', sans-serif; background-color: #f8fafc; }
    
    /* SIDEBAR GENİŞLİK: Butonların sığması için genişlettik */
    section[data-testid="stSidebar"] { min-width: 350px !important; max-width: 350px !important; }

    /* --- SORU BUTONLARI (KESİN BOYUTLANDIRMA) --- */
    /* Kolon genişliğini baştan geniş tutuyoruz ki sonradan büyümesin */
    div[data-testid="stSidebar"] div[data-testid="column"] {
        width: 50px !important;
        min-width: 50px !important;
        max-width: 50px !important;
        flex: 0 0 50px !important; 
        padding: 0 !important;
        margin: 1px !important;
    }

    /* Butonun kendisi */
    div[data-testid="stSidebar"] div[data-testid="column"] button {
        width: 48px !important;      /* Genişlik SABİT */
        height: 48px !important;     /* Yükseklik SABİT */
        min-width: 48px !important;
        max-width: 48px !important;
        min-height: 48px !important;
        max-height: 48px !important;
        padding: 0 !important;
        
        font-size: 11px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        
        /* İçerik hizalama */
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        
        /* Metin Taşma Kontrolü */
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: clip !important;
        line-height: 1 !important;
    }
    
    /* Kolonlar arası boşluğu sıfırla */
    div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
        gap: 0px !important;
        justify-content: center !important;
    }

    /* GİRİŞ EKRANI */
    .login-container {
        max-width: 400px; margin: 60px auto; padding: 40px;
        background: white; border-radius: 16px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: center; 
        border: 1px solid #eef2f6;
    }
    .stTextInput > div > div > input { width: 100% !important; }
    
    /* DİĞER BUTONLAR */
    div.stButton > button { width: 100% !important; border-radius: 8px; font-weight: 600; min-height: 45px; }

    /* OKUMA ALANI (DİNAMİK FONT İÇİN) */
    .passage-box { 
        background-color: #ffffff; padding: 25px; border-radius: 12px; 
        border: 1px solid #dfe6e9; color: #2d3436; 
        overflow-y: auto; max-height: 70vh;
        /* Font boyutu inline style ile verilecek */
    }
    
    .question-stem { 
        font-size: 18px; font-weight: 600; 
        border-left: 5px solid #2563eb; padding-left: 15px; margin-bottom: 20px; 
        color: #1e293b;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. VERİ YÖNETİMİ ---
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

def get_leaderboard_pivot():
    if not os.path.exists(SCORES_FILE): return None
    try:
        df = pd.read_csv(SCORES_FILE)
        if df.empty: return None
        return df.pivot_table(index="Kullanıcı", columns="Sınav", values="Puan", aggfunc="max").fillna("-")
    except: return None

# --- 5. GİRİŞ EKRANI ---
if st.session_state.username is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container"><h1 style="color:#2563eb;">YDS Pro</h1><p>Giriş Yapın</p></div>', unsafe_allow_html=True)
        with st.form("login_form"):
            name = st.text_input("Ad Soyad:", placeholder="İsim giriniz...")
            submitted = st.form_submit_button("🚀 Giriş Yap")
            if submitted:
                if name.strip():
                    st.session_state.username = name.strip()
                    st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000
                    st.rerun()
                else: st.error("İsim gerekli.")
    st.stop()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.success(f"👤 **{st.session_state.username}**")
    
    # SAYAÇ
    if not st.session_state.finish:
        components.html(
            f"""<div id="countdown" style="font-family:'Poppins',sans-serif;font-size:18px;font-weight:bold;color:#dc2626;text-align:center;padding:8px;background:#fee2e2;border-radius:8px;border:1px solid #fecaca;">⏳ Hesapla...</div>
            <script>
            var dest={st.session_state.end_timestamp};
            setInterval(function(){{var now=new Date().getTime();var dist=dest-now;
            var h=Math.floor((dist%(1000*60*60*24))/(1000*60*60));
            var m=Math.floor((dist%(1000*60*60))/(1000*60));
            var s=Math.floor((dist%(1000*60))/1000);
            document.getElementById("countdown").innerHTML="⏳ "+(h<10?"0"+h:h)+":"+(m<10?"0"+m:m)+":"+(s<10?"0"+s:s);}},1000);
            </script>""", height=60
        )

    mode = st.toggle("Sınav Modu", value=st.session_state.exam_mode)
    if mode != st.session_state.exam_mode:
        st.session_state.exam_mode = mode
        st.rerun()

    exam_id = st.selectbox("Sınav Seç:", range(1, 11), format_func=lambda x: f"YDS Deneme {x}", index=st.session_state.selected_exam_id - 1)
    if exam_id != st.session_state.selected_exam_id:
        st.session_state.selected_exam_id = exam_id
        st.session_state.answers, st.session_state.marked, st.session_state.idx = {}, set(), 0
        st.session_state.finish, st.session_state.data_saved, st.session_state.gemini_res = False, False, {}
        st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000
        st.rerun()

    df = load_exam_file_cached(st.session_state.selected_exam_id)

    with st.expander("🔑 AI Ayarları"):
        key_input = st.text_input("API Key:", type="password", value=st.session_state.user_api_key)
        if st.button("Kaydet"):
            if key_input and len(key_input.strip()) > 0:
                st.session_state.user_api_key = key_input.strip()
                st.success("Kaydedildi.")
            else:
                st.error("Lütfen anahtar girin!")

    if df is not None:
        st.write("---")
        st.markdown("**🗺️ Soru Haritası**")
        st.markdown('<div style="font-size:12px; margin-bottom:10px; display:flex; justify-content:space-between;"><span>✅ Doğru</span><span>❌ Yanlış</span><span>⭐ İşaret</span></div>', unsafe_allow_html=True)

        cols = st.columns(5)
        for i in range(len(df)):
            q_idx = i
            col_idx = i % 5 
            with cols[col_idx]:
                u_a = st.session_state.answers.get(q_idx)
                lbl = str(q_idx + 1)
                
                # İkonlar
                if u_a: 
                    if st.session_state.exam_mode: lbl += "🟦"
                    else: lbl += "✅" if u_a == df.iloc[q_idx]['Dogru_Cevap'] else "❌"
                elif q_idx in st.session_state.marked: lbl += "⭐"
                
                b_type = "primary" if q_idx == st.session_state.idx else "secondary"
                if st.button(lbl, key=f"nav_{q_idx}", type=b_type):
                    st.session_state.idx = q_idx; st.rerun()
        
        st.write("---")
        if not st.session_state.finish:
            if st.button("🏁 SINAVI BİTİR", type="primary"):
                st.session_state.finish = True; st.rerun()

# --- 7. ANA EKRAN ---
if df is not None:
    if not st.session_state.finish:
        # ÜST BAR
        c1, c2, c3, c4 = st.columns([5, 1, 1, 1])
        c1.subheader(f"Soru {st.session_state.idx + 1}")
        
        # --- METİN BÜYÜTME/KÜÇÜLTME (DÜZELTİLDİ) ---
        with c2:
            if st.button("A ➖", help="Küçült"):
                if st.session_state.font_size > 12: 
                    st.session_state.font_size -= 2
                    st.rerun()
        with c3:
            if st.button("A ➕", help="Büyüt"):
                if st.session_state.font_size < 40:
                    st.session_state.font_size += 2
                    st.rerun()
                
        with c4:
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
            # FONT BOYUTUNU BURADA ZORLA UYGULUYORUZ
            l.markdown(f"""
            <div class='passage-box' style='font-size: {f_size}px !important; line-height: {f_size * 1.5}px !important;'>
                {passage}
            </div>
            """, unsafe_allow_html=True)
            main_col = r
        else: main_col = st.container()

        with main_col:
            st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
            opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
            curr = st.session_state.answers.get(st.session_state.idx)
            sel_idx = next((i for i,v in enumerate(opts) if v.startswith(str(curr) + ")")), None)
            sel = st.radio("Cevabınız:", opts, index=sel_idx, key=f"ans_{st.session_state.idx}")
            
            if sel:
                chosen = sel.split(")")[0]
                st.session_state.answers[st.session_state.idx] = chosen
                if not st.session_state.exam_mode:
                    if chosen == row['Dogru_Cevap']: st.success("DOĞRU! 🎉")
                    else: st.error(f"YANLIŞ! (Doğru: {row['Dogru_Cevap']})")

        st.write("")
        c_act1, c_act2 = st.columns([1, 1])
        with c_act1:
            if st.button("🤖 Çözümle", use_container_width=True):
                if not st.session_state.user_api_key: st.warning("Lütfen API Key girin.")
                else:
                    with st.spinner("Analiz..."):
                        genai.configure(api_key=st.session_state.user_api_key)
                        model = genai.GenerativeModel('gemini-2.5-flash')
                        res = model.generate_content(f"Soru: {q_raw}. Doğru: {row['Dogru_Cevap']}. Analiz et.").text
                        st.session_state.gemini_res[st.session_state.idx] = res
                        st.rerun()
        
        with c_act2:
            c_p, c_n = st.columns(2)
            if st.session_state.idx > 0 and c_p.button("⬅️ Önceki", use_container_width=True): st.session_state.idx -= 1; st.rerun()
            if st.session_state.idx < len(df)-1 and c_n.button("Sonraki ➡️", use_container_width=True): st.session_state.idx += 1; st.rerun()

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

        st.subheader("🏆 Liderlik Tablosu")
        st.dataframe(get_leaderboard_pivot(), use_container_width=True)

        if st.button("🔄 Yeni Sınava Başla", type="primary"):
            st.session_state.answers = {}
            st.session_state.idx = 0
            st.session_state.finish = False
            st.session_state.data_saved = False
            st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000
            st.rerun()

else: st.warning("⚠️ Sınav dosyası bulunamadı.")
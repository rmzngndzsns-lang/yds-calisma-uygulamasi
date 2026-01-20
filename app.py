import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import google.generativeai as genai
import os
import json
import nest_asyncio

# Döngü yaması
nest_asyncio.apply()

# --- 1. AYARLAR ---
st.set_page_config(page_title="YDS Pro", page_icon="🎓", layout="wide")

# --- 2. SESSION STATE ---
defaults = {
    'username': None, 'selected_exam_id': 1, 'idx': 0, 'answers': {}, 
    'marked': set(), 'finish': False, 'data_saved': False, 'gemini_res': {}, 
    'user_api_key': "", 'font_size': 16, 'exam_mode': False, 'end_timestamp': 0,
    'current_exam_data': None, 'cached_exam_id': None, 'progress_loaded': False,
    'dark_mode': False
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# --- 3. CSS (DARK MODE - EXPANDER AÇIK HALİ KESİN ÇÖZÜM) ---
if st.session_state.dark_mode:
    dark_css = """
    /* ANA GÖVDE */
    .stApp { 
        background-color: #0e1117 !important; 
        color: #fafafa !important; 
    }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] { 
        background-color: #1a1d24 !important; 
    }
    section[data-testid="stSidebar"] * {
        color: #fafafa !important;
    }

    /* KUTULAR */
    .passage-box, .login-container, .control-panel { 
        background-color: #262730 !important; 
        color: #fafafa !important; 
        border-color: #41444e !important; 
    }
    .question-stem { 
        color: #fafafa !important; 
        background-color: #262730 !important; 
        border-left-color: #4f83f5 !important;
    }
    h1, h2, h3, h4, h5, h6, p, span, div, label, li { 
        color: #fafafa !important; 
    }
    
    /* --- INPUT ALANLARI --- */
    div[data-baseweb="input"] {
        background-color: #262730 !important;
        border-color: #41444e !important;
    }
    .stTextInput input { 
        background-color: #262730 !important; 
        color: #fafafa !important; 
        border: none !important; 
    }
    .stTextInput button {
        background-color: #262730 !important; 
        color: #fafafa !important; 
        border: none !important;
    }
    .stTextInput button svg {
        fill: #fafafa !important;
    }

    /* --- EXPANDER (AI AYARLARI) KESİN ÇÖZÜM --- */
    
    /* 1. Expander'ın Başlık Kısmı (Genel Sınıf) */
    .streamlit-expanderHeader {
        background-color: #262730 !important;
        color: #fafafa !important;
    }

    /* 2. Expander AÇIKKEN (Details[open]) ve Mouse Üzerinde DEĞİLKEN */
    details[data-testid="stExpander"][open] > summary {
        background-color: #262730 !important; /* İşte burası beyazlığı engeller */
        color: #fafafa !important;
    }

    

    /* 4. Expander AÇIKKEN İkon ve Yazı Renkleri */
    details[data-testid="stExpander"][open] > summary svg,
    details[data-testid="stExpander"][open] > summary span,
    details[data-testid="stExpander"][open] > summary p {
        color: #fafafa !important;
        fill: #fafafa !important;
    }

    /* 5. Expander İçerik Gövdesi */
    details[data-testid="stExpander"] {
        background-color: #262730 !important;
        border-color: #41444e !important;
        color: #fafafa !important;
    }
    details[data-testid="stExpander"] > div {
        color: #fafafa !important;
    }

    /* --- SELECTBOX --- */
    div[data-baseweb="select"] > div {
        background-color: #262730 !important;
        border-color: #41444e !important;
        color: #fafafa !important;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
        background-color: #262730 !important;
    }
    li[role="option"] {
        background-color: #262730 !important;
        color: #fafafa !important;
    }
    li[role="option"][aria-selected="true"], li[role="option"]:hover {
        background-color: #4f83f5 !important;
        color: white !important;
    }
    
    /* BUTONLAR */
    .stButton > button {
        background-color: #262730 !important;
        color: #fafafa !important;
        border: 1px solid #41444e !important;
    }
    .stButton > button:hover {
        border-color: #4f83f5 !important;
        color: #4f83f5 !important;
    }
    
    /* DİĞER */
    .stRadio label { color: #fafafa !important; }
    div[data-testid="stMetricValue"] { color: #fafafa !important; }
    div[data-testid="stMetricLabel"] { color: #c5c5c5 !important; }
    """
else:
    dark_css = ""

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    .stApp {{ 
        font-family: 'Poppins', sans-serif; 
        background-color: {'#0e1117' if st.session_state.dark_mode else '#f8fafc'}; 
    }}
    
    {dark_css}
    
    /* SIDEBAR GENİŞLİK */
    section[data-testid="stSidebar"] {{ 
        min-width: 380px !important; 
        max-width: 380px !important; 
    }}

    /* SORU HARİTASI */
    div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {{
        display: grid !important;
        grid-template-columns: repeat(5, 1fr) !important;
        gap: 6px !important;
        margin-bottom: 8px !important;
    }}
    div[data-testid="stSidebar"] div[data-testid="column"] {{
        width: 100% !important; flex: none !important; padding: 0 !important; margin: 0 !important;
    }}
    div[data-testid="stSidebar"] div[data-testid="column"] button {{
        width: 100% !important; height: 48px !important; padding: 4px !important;
        font-size: 13px !important; font-weight: 600 !important; border-radius: 8px !important;
        display: flex !important; flex-direction: column !important; align-items: center !important;
        justify-content: center !important; line-height: 1.2 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }}
    
    /* ELEMENT STİLLERİ */
    .login-container {{
        max-width: 400px; margin: 60px auto; padding: 40px;
        background: {'#262730' if st.session_state.dark_mode else 'white'}; 
        border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); 
        text-align: center; border: 1px solid {'#41444e' if st.session_state.dark_mode else '#eef2f6'};
    }}
    .passage-box {{ 
        background-color: {'#262730' if st.session_state.dark_mode else '#ffffff'}; 
        padding: 25px; border-radius: 12px; 
        border: 1px solid {'#41444e' if st.session_state.dark_mode else '#dfe6e9'}; 
        color: {'#fafafa' if st.session_state.dark_mode else '#2d3436'}; 
        overflow-y: auto; max-height: 70vh;
    }}
    .question-stem {{ 
        font-weight: 600; border-left: 5px solid {'#4f83f5' if st.session_state.dark_mode else '#2563eb'}; 
        padding-left: 15px; margin-bottom: 20px; 
        color: {'#fafafa' if st.session_state.dark_mode else '#1e293b'};
        background-color: transparent;
    }}
    .control-panel {{
        position: sticky !important; top: 0; z-index: 999;
        background: {'#262730' if st.session_state.dark_mode else 'white'};
        padding: 15px 0; margin-bottom: 20px; 
        border-bottom: 2px solid {'#41444e' if st.session_state.dark_mode else '#e5e7eb'};
        display: flex; align-items: center; justify-content: space-between; gap: 10px;
    }}
    .legend-box {{
        background-color: {'#262730' if st.session_state.dark_mode else '#f8fafc'};
        border: 1px solid {'#41444e' if st.session_state.dark_mode else '#e5e7eb'};
        padding: 8px; border-radius: 8px; font-size: 11px;
        display: flex; justify-content: space-between; margin-bottom: 10px;
        color: {'#fafafa' if st.session_state.dark_mode else '#333'};
    }}
</style>
""", unsafe_allow_html=True)

# --- 4. VERİ VE DOSYA İŞLEMLERİ ---
SCORES_FILE = "lms_scores.csv"

@st.cache_data(show_spinner=False)
def load_exam_file_cached(exam_id):
    if not isinstance(exam_id, int) or exam_id < 1 or exam_id > 10: return None
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
        return True
    except: return False

def autosave_progress():
    if st.session_state.username and st.session_state.selected_exam_id:
        progress_file = f"progress_{st.session_state.username}_{st.session_state.selected_exam_id}.json"
        data = {
            'answers': {str(k): v for k, v in st.session_state.answers.items()},
            'marked': list(st.session_state.marked),
            'idx': st.session_state.idx,
            'timestamp': datetime.now().isoformat()
        }
        try:
            with open(progress_file, 'w', encoding='utf-8') as f: json.dump(data, f)
        except: pass

def load_progress():
    if st.session_state.username and st.session_state.selected_exam_id:
        progress_file = f"progress_{st.session_state.username}_{st.session_state.selected_exam_id}.json"
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    st.session_state.answers = {int(k): v for k, v in data['answers'].items()}
                    st.session_state.marked = set(data['marked'])
                    st.session_state.idx = data.get('idx', 0)
                    return True
            except: pass
    return False

# --- 5. GİRİŞ EKRANI ---
if st.session_state.username is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f'<div class="login-container"><h1 style="color:{"#4f83f5" if st.session_state.dark_mode else "#2563eb"};">YDS Pro</h1><p>Giriş Yapın</p></div>', unsafe_allow_html=True)
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

if not st.session_state.progress_loaded:
    load_progress()
    st.session_state.progress_loaded = True

# --- 6. VERİ YÜKLEME ---
exam_id = st.session_state.selected_exam_id
if st.session_state.current_exam_data is None or st.session_state.cached_exam_id != exam_id:
    df = load_exam_file_cached(exam_id)
    st.session_state.current_exam_data = df
    st.session_state.cached_exam_id = exam_id
else: df = st.session_state.current_exam_data

if not st.session_state.finish and datetime.now().timestamp() * 1000 >= st.session_state.end_timestamp:
    st.session_state.finish = True; st.rerun()

# --- 7. SIDEBAR ---
with st.sidebar:
    st.success(f"👤 **{st.session_state.username}**")
    
    if not st.session_state.finish:
        components.html(
            f"""<div id="countdown" style="font-family:'Poppins',sans-serif;font-size:18px;font-weight:bold;color:#dc2626;text-align:center;padding:8px;background:#fee2e2;border-radius:8px;border:1px solid #fecaca;">⏳ Hesapla...</div>
            <script>
            var dest={st.session_state.end_timestamp};
            var interval = setInterval(function(){{
                var now=new Date().getTime();
                var dist=dest-now;
                if(dist <= 0) {{ clearInterval(interval); document.getElementById("countdown").innerHTML="⏰ BİTTİ!"; return; }}
                var h=Math.floor((dist%(1000*60*60*24))/(1000*60*60));
                var m=Math.floor((dist%(1000*60*60))/(1000*60));
                var s=Math.floor((dist%(1000*60))/1000);
                document.getElementById("countdown").innerHTML="⏳ "+(h<10?"0"+h:h)+":"+(m<10?"0"+m:m)+":"+(s<10?"0"+s:s);
            }}, 1000);
            </script>""", height=60
        )
    
    # MOD VE AYARLAR
    c_set1, c_set2 = st.columns(2)
    with c_set1:
        mode = st.toggle("Sınav Modu", value=st.session_state.exam_mode)
        if mode != st.session_state.exam_mode: st.session_state.exam_mode = mode; st.rerun()
    with c_set2:
        dm = st.toggle("🌙 Dark Mod", value=st.session_state.dark_mode)
        if dm != st.session_state.dark_mode: st.session_state.dark_mode = dm; st.rerun()

    new_exam_id = st.selectbox("Sınav Seç:", range(1, 11), format_func=lambda x: f"YDS Deneme {x}", index=st.session_state.selected_exam_id - 1)
    if new_exam_id != st.session_state.selected_exam_id:
        st.session_state.selected_exam_id = new_exam_id
        st.session_state.answers, st.session_state.marked, st.session_state.idx = {}, set(), 0
        st.session_state.finish, st.session_state.data_saved = False, False
        st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000
        st.session_state.current_exam_data = None
        st.rerun()

    with st.expander("🔑 AI Ayarları"):
        key_input = st.text_input("API Key:", type="password", value=st.session_state.user_api_key)
        if st.button("Kaydet"):
            if key_input and len(key_input.strip()) > 0:
                st.session_state.user_api_key = key_input.strip()
                st.success("Kaydedildi.")

    if df is not None:
        st.write("---")
        total, answered = len(df), len(st.session_state.answers)
        st.progress(answered / total if total > 0 else 0)
        st.caption(f"📝 {answered}/{total} soru yanıtlandı")
        
        st.markdown("**🗺️ Soru Haritası**")
        st.markdown('<div class="legend-box"><span>✅ Doğru</span><span>❌ Yanlış</span><span>⭐ İşaret</span></div>', unsafe_allow_html=True)

        for row_start in range(0, len(df), 5):
            cols = st.columns(5)
            for col_idx in range(5):
                q_idx = row_start + col_idx
                if q_idx >= len(df): break
                with cols[col_idx]:
                    u_a = st.session_state.answers.get(q_idx)
                    num = str(q_idx + 1)
                    icon = ""
                    if u_a:
                        if st.session_state.exam_mode: icon = "🟦"
                        else: icon = "✅" if u_a == df.iloc[q_idx]['Dogru_Cevap'] else "❌"
                    elif q_idx in st.session_state.marked: icon = "⭐"
                    
                    lbl = f"{num}\n{icon}" if icon else num
                    b_type = "primary" if q_idx == st.session_state.idx else "secondary"
                    if st.button(lbl, key=f"nav_{q_idx}", type=b_type):
                        st.session_state.idx = q_idx
                        st.rerun()
        
        st.write("---")
        if not st.session_state.finish:
            if st.button("🏁 SINAVI BİTİR", type="primary"): 
                st.session_state.finish = True
                st.rerun()

# --- 8. ANA EKRAN ---
if df is not None:
    if not st.session_state.finish:
        # ÜST PANEL
        control_col1, control_col2, control_col3, control_col4, control_col5 = st.columns([10, 1, 1, 1, 1])
        with control_col1: 
            st.markdown(f"<h3 style='margin:0;padding:0;color:{"#fafafa" if st.session_state.dark_mode else "#1e293b"};'>Soru {st.session_state.idx + 1}</h3>", unsafe_allow_html=True)
        with control_col2: 
            if st.button("A➖", key="font_dec"): 
                st.session_state.font_size = max(12, st.session_state.font_size - 2)
                st.rerun()
        with control_col3: 
            if st.button("A➕", key="font_inc"): 
                st.session_state.font_size = min(30, st.session_state.font_size + 2)
                st.rerun()
        with control_col4: 
            st.markdown(f"<div style='text-align:center;padding-top:8px;font-size:12px;color:{"#fafafa" if st.session_state.dark_mode else "#1e293b"};'>{st.session_state.font_size}px</div>", unsafe_allow_html=True)
        with control_col5:
            is_m = st.session_state.idx in st.session_state.marked
            if st.button("⭐" if is_m else "☆", key="mark_tgl"):
                if is_m: st.session_state.marked.remove(st.session_state.idx)
                else: st.session_state.marked.add(st.session_state.idx)
                autosave_progress()
                st.rerun()

        st.markdown("<hr style='margin:15px 0;'>", unsafe_allow_html=True)
        row = df.iloc[st.session_state.idx]
        q_raw = str(row['Soru']).replace('\\n', '\n')
        passage, stem = (q_raw.split('\n\n', 1) if '\n\n' in q_raw else (None, q_raw))
        
        f_size = st.session_state.font_size
        if passage:
            l, r = st.columns(2)
            l.markdown(f"<div class='passage-box' style='font-size:{f_size}px; line-height:{f_size*1.6}px;'>{passage}</div>", unsafe_allow_html=True)
            main_col = r
        else: main_col = st.container()

        with main_col:
            st.markdown(f"<div class='question-stem' style='font-size:{f_size+2}px;'>{stem}</div>", unsafe_allow_html=True)
            opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
            curr = st.session_state.answers.get(st.session_state.idx)
            sel_idx = next((i for i,v in enumerate(opts) if v.startswith(str(curr) + ")")), None)
            sel = st.radio("Cevabınız:", opts, index=sel_idx, key=f"ans_{st.session_state.idx}")
            
            if sel:
                chosen = sel.split(")")[0]
                if st.session_state.answers.get(st.session_state.idx) != chosen:
                    st.session_state.answers[st.session_state.idx] = chosen
                    autosave_progress()
                    st.rerun()

                if not st.session_state.exam_mode:
                    if chosen == row['Dogru_Cevap']: st.success("✅ DOĞRU!")
                    else: st.error(f"❌ YANLIŞ! (Doğru: {row['Dogru_Cevap']})")

        st.write("")
        c_act1, c_act2 = st.columns([1, 1])
        with c_act1:
            if st.button("🤖 AI Çözümle", use_container_width=True):
                if not st.session_state.user_api_key: st.warning("⚠️ API Key Girin")
                else:
                    with st.spinner("🔍 Analiz..."):
                        try:
                            genai.configure(api_key=st.session_state.user_api_key)
                            model = genai.GenerativeModel('gemini-2.5-flash')
                            res = model.generate_content(f"Soru: {q_raw}. Doğru: {row['Dogru_Cevap']}. Detaylı anlat.").text
                            st.session_state.gemini_res[st.session_state.idx] = res
                            st.rerun()
                        except Exception as e: st.error(f"Hata: {e}")
        with c_act2:
            c_p, c_n = st.columns(2)
            if st.session_state.idx > 0 and c_p.button("⬅️ Önceki", use_container_width=True): 
                st.session_state.idx -= 1; st.rerun()
            if st.session_state.idx < len(df)-1 and c_n.button("Sonraki ➡️", use_container_width=True): 
                st.session_state.idx += 1; st.rerun()
            
        if st.session_state.idx in st.session_state.gemini_res: 
            st.info(st.session_state.gemini_res[st.session_state.idx])

    else:
        st.title("📊 Sonuçlar")
        correct = sum(1 for i, a in st.session_state.answers.items() if a == df.iloc[i]['Dogru_Cevap'])
        wrong = len(st.session_state.answers) - correct
        empty = len(df) - len(st.session_state.answers)
        score = correct * 1.25
        if not st.session_state.data_saved:
            save_score_to_csv(st.session_state.username, f"Deneme {st.session_state.selected_exam_id}", score, correct, wrong, empty)
            st.session_state.data_saved = True
            st.balloons()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Puan", score)
        m2.metric("Doğru", correct); m3.metric("Yanlış", wrong); m4.metric("Boş", empty)
        if st.button("🔄 Yeni Sınav", type="primary"): 
            st.session_state.finish = False; st.session_state.answers = {}; st.session_state.idx = 0; st.rerun()
else: st.warning("Dosya bulunamadı.")
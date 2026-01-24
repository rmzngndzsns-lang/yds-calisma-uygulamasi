import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import google.generativeai as genai
import os
import json
import nest_asyncio
import altair as alt
import math

# Döngü yaması (Asyncio çakışmalarını önler)
nest_asyncio.apply()

# --- 1. AYARLAR ---
st.set_page_config(page_title="YDS Pro", page_icon="🎓", layout="wide")

# --- 2. SESSION STATE ---
defaults = {
    'username': None, 'selected_exam_id': 1, 'idx': 0, 'answers': {}, 
    'marked': set(), 'finish': False, 'data_saved': False, 'gemini_res': {}, 
    'user_api_key': "", 'font_size': 16, 'exam_mode': False, 
    'end_timestamp': 0, 
    'start_timestamp': 0, 
    'current_exam_data': None, 'cached_exam_id': None, 'progress_loaded': False,
    'dark_mode': False,
    'coach_analysis': None
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# --- 3. CSS (TASARIM) ---
if st.session_state.dark_mode:
    bg_color = "#0e1117"
    card_bg = "#262730"
    text_color = "#e0e0e0" 
    border_color = "#41444e"
    primary_color = "#4f83f5"
    button_bg = "#2b313e" 
    button_hover = "#363945"
    input_bg = "#262730" 
    shadow = "0 4px 15px rgba(0,0,0,0.4)"
    ai_box_bg = "linear-gradient(145deg, #1e2028, #23252e)"
    ai_box_border = "#4f83f5"
    ai_text_color = "#e0e0e0"
    ai_title_color = "#8baaf0"
    ai_shadow = "0 4px 15px rgba(0,0,0,0.4)"
    
    custom_dark_css = f"""
    div[data-baseweb="input"] {{ background-color: {input_bg} !important; border-color: {border_color} !important; border-radius: 8px !important; }}
    div[data-baseweb="base-input"] {{ background-color: transparent !important; }}
    input.st-bd, input.st-bc {{ color: {text_color} !important; background-color: transparent !important; }}
    button[aria-label="Password visibility"] svg {{ fill: {text_color} !important; }}
    div[data-baseweb="select"] > div {{ background-color: {input_bg} !important; border-color: {border_color} !important; color: {text_color} !important; }}
    div[data-baseweb="select"] span {{ color: {text_color} !important; }}
    ul[role="listbox"] {{ background-color: {card_bg} !important; }}
    li[role="option"] {{ color: {text_color} !important; background-color: {card_bg} !important; }}
    li[role="option"]:hover, li[role="option"][aria-selected="true"] {{ background-color: {primary_color} !important; color: white !important; }}
    .streamlit-expanderHeader {{ background-color: {card_bg} !important; color: {text_color} !important; border: 1px solid {border_color} !important; border-radius: 8px !important; }}
    .streamlit-expanderHeader:hover {{ color: {primary_color} !important; border-color: {primary_color} !important; }}
    .streamlit-expanderHeader svg {{ fill: {text_color} !important; }}
    div[data-testid="stExpander"] {{ border: none !important; box-shadow: none !important; }}
    div[data-testid="stExpander"] > details > div {{ border: 1px solid {border_color}; border-top: none; border-radius: 0 0 8px 8px; background-color: {bg_color}; padding: 15px; }}
    """
else:
    bg_color = "#f8fafc"
    card_bg = "#ffffff"
    text_color = "#334155"
    border_color = "#e2e8f0"
    primary_color = "#2563eb"
    button_bg = "#ffffff"
    button_hover = "#f1f5f9"
    input_bg = "#ffffff"
    shadow = "0 20px 40px -5px rgba(0,0,0,0.08)"
    ai_box_bg = "linear-gradient(145deg, #f0f4ff, #eef2ff)"
    ai_box_border = "#6366f1"
    ai_text_color = "#334155"
    ai_title_color = "#4338ca"
    ai_shadow = "0 10px 25px -5px rgba(99, 102, 241, 0.15)"
    custom_dark_css = ""

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    .stApp {{ font-family: 'Poppins', sans-serif; background-color: {bg_color}; color: {text_color}; }}
    p, label, span, div, h1, h2, h3, h4, h5, h6 {{ color: {text_color}; }}

    /* Sidebar Butonları */
    div[data-testid="stSidebar"] div[data-testid="column"] button {{
        height: 50px !important; min-height: 50px !important; max-height: 50px !important;
        width: 100% !important; padding: 0px !important; position: relative !important;
        overflow: hidden !important; border-radius: 8px !important;
    }}
    div[data-testid="stSidebar"] div[data-testid="column"] button div[data-testid="stMarkdownContainer"] p {{
        display: grid !important; place-items: center !important; height: 100% !important;
        margin: 0 !important; line-height: 0 !important;
    }}
    
    div[data-testid="stForm"] {{ background-color: {card_bg}; border: 1px solid {border_color}; padding: 50px 40px; border-radius: 24px; box-shadow: {shadow}; max-width: 450px; margin: auto; }}
    div[role="radiogroup"] label {{ color: {text_color} !important; background-color: transparent !important; }}
    .stButton > button {{ background-color: {button_bg} !important; color: {text_color} !important; border: 1px solid {border_color} !important; border-radius: 10px !important; font-weight: 500 !important; transition: all 0.2s ease; }}
    .stButton > button:hover {{ background-color: {button_hover} !important; border-color: {primary_color} !important; color: {primary_color} !important; }}
    .stButton > button[kind="primary"] {{ background-color: {primary_color} !important; color: white !important; border: none !important; }}
    
    .ai-result-box {{ margin-top: 25px; background: {ai_box_bg}; border-radius: 16px; padding: 24px; box-shadow: {ai_shadow}; border-left: 6px solid {ai_box_border}; position: relative; overflow: hidden; }}
    .ai-result-box::before {{ content: '🤖'; position: absolute; right: -10px; bottom: -20px; font-size: 120px; opacity: 0.05; transform: rotate(-15deg); pointer-events: none; }}
    .ai-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid rgba(0,0,0, 0.05); }}
    .ai-header-icon {{ font-size: 24px; background: {ai_box_border}; color: white; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 50%; }}
    .ai-title {{ font-size: 18px; font-weight: 700; color: {ai_title_color}; }}
    .ai-content {{ font-size: 16px; line-height: 1.7; color: {ai_text_color}; text-align: justify; }}
    
    section[data-testid="stSidebar"] {{ background-color: {bg_color} !important; border-right: 1px solid {border_color}; }}
    section[data-testid="stSidebar"] * {{ color: {text_color} !important; }}
    div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {{ display: grid !important; grid-template-columns: repeat(5, 1fr) !important; gap: 6px !important; }}
    div[data-testid="stSidebar"] div[data-testid="column"] button {{ width: 100% !important; border-radius: 8px !important; }}
    .stRadio label {{ user-select: none !important; -webkit-user-select: none !important; }}
    .login-title {{ text-align: center; font-size: 32px; font-weight: 700; color: {primary_color}; margin-bottom: 5px; }}
    .login-subtitle {{ text-align: center; font-size: 14px; color: {text_color}; opacity: 0.7; margin-bottom: 30px; }}
    .passage-box {{ background-color: {card_bg}; padding: 25px; border-radius: 12px; border: 1px solid {border_color}; color: {text_color}; overflow-y: auto; max-height: 70vh; line-height: 1.8; }}
    .question-stem {{ font-weight: 600; border-left: 5px solid {primary_color}; padding-left: 20px; margin-bottom: 25px; color: {text_color}; }}

    {custom_dark_css}
</style>
""", unsafe_allow_html=True)

# --- 4. VERİ VE DOSYA İŞLEMLERİ ---
SCORES_FILE = "lms_scores.csv"

@st.cache_data(show_spinner=False)
def load_exam_file_cached(exam_id):
    if not isinstance(exam_id, int) or exam_id < 1 or exam_id > 10: return None
    possible_names = [f"Sinav_{exam_id}.xlsx", f"sinav_{exam_id}.xlsx", f"Sinav_{exam_id}.xls", f"sinav_{exam_id}.csv"]
    for name in possible_names:
        if os.path.exists(name):
            try:
                if name.endswith('.csv'): df = pd.read_csv(name)
                else: df = pd.read_excel(name)
                df.columns = df.columns.astype(str).str.strip()
                if 'Dogru_Cevap' in df.columns: df['Dogru_Cevap'] = df['Dogru_Cevap'].astype(str).str.strip().str.upper()
                return df
            except: continue
    return None

def save_score_to_csv(username, exam_name, score, correct, wrong, empty, duration_str):
    try:
        if os.path.exists(SCORES_FILE): df = pd.read_csv(SCORES_FILE)
        else: df = pd.DataFrame(columns=["Kullanıcı", "Sınav", "Puan", "Doğru", "Yanlış", "Boş", "Tarih", "Süre"])
        new_row = pd.DataFrame({"Kullanıcı": [username], "Sınav": [exam_name], "Puan": [score], "Doğru": [correct], "Yanlış": [wrong], "Boş": [empty], "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")], "Süre": [duration_str]})
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(SCORES_FILE, index=False)
        return True
    except: return False

def autosave_progress():
    if st.session_state.username and st.session_state.selected_exam_id:
        progress_file = f"progress_{st.session_state.username}_{st.session_state.selected_exam_id}.json"
        data = {'answers': {str(k): v for k, v in st.session_state.answers.items()}, 'marked': list(st.session_state.marked), 'idx': st.session_state.idx, 'end_timestamp': st.session_state.end_timestamp, 'start_timestamp': st.session_state.start_timestamp}
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
                    st.session_state.end_timestamp = data.get('end_timestamp', 0)
                    st.session_state.start_timestamp = data.get('start_timestamp', 0)
                    return True
            except: pass
    return False

# --- 5. GİRİŞ EKRANI ---
if st.session_state.username is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown('<div class="login-title">YDS Pro</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-subtitle">Giriş Yapın</div>', unsafe_allow_html=True)
            name = st.text_input("Ad Soyad:", placeholder="İsim giriniz...")
            submitted = st.form_submit_button("🚀 Giriş Yap", type="primary", use_container_width=True)
            if submitted:
                if name.strip():
                    st.session_state.username = name.strip()
                    if not load_progress(): 
                         now_ms = datetime.now().timestamp() * 1000
                         st.session_state.start_timestamp = now_ms
                         st.session_state.end_timestamp = now_ms + (180 * 60 * 1000)
                    st.rerun()
                else: st.error("Lütfen isminizi giriniz.")
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
        components.html(f"""
            <div id="countdown" style="font-family:'Poppins',sans-serif;font-size:18px;font-weight:bold;color:#dc2626;text-align:center;padding:8px;background:#fee2e2;border-radius:8px;border:1px solid #fecaca;">⏳ Hesapla...</div>
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
            </script>
            """, height=80)
    
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
        st.session_state.finish, st.session_state.data_saved, st.session_state.coach_analysis = False, False, None
        now_ms = datetime.now().timestamp() * 1000
        st.session_state.start_timestamp, st.session_state.end_timestamp = now_ms, now_ms + (180 * 60 * 1000)
        st.session_state.current_exam_data = None
        st.rerun()

    with st.expander("🔑 AI Ayarları"):
        key_input = st.text_input("API Key:", type="password", value=st.session_state.user_api_key)
        if st.button("Kaydet"):
            st.session_state.user_api_key = key_input.strip()
            st.success("Kaydedildi.")

    if df is not None:
        st.write("---")
        total, answered = len(df), len(st.session_state.answers)
        st.progress(answered / total if total > 0 else 0)
        st.caption(f"📝 {answered}/{total} soru yanıtlandı")
        for row_start in range(0, len(df), 5):
            cols = st.columns(5)
            for col_idx in range(5):
                q_idx = row_start + col_idx
                if q_idx >= len(df): break
                with cols[col_idx]:
                    u_a = st.session_state.answers.get(q_idx)
                    icon = ("🟦" if st.session_state.exam_mode else ("✅" if u_a == df.iloc[q_idx]['Dogru_Cevap'] else "❌")) if u_a else ("⭐" if q_idx in st.session_state.marked else "")
                    if st.button(f"{q_idx+1}\n{icon}", key=f"nav_{q_idx}", type="primary" if q_idx == st.session_state.idx else "secondary"):
                        st.session_state.idx = q_idx
                        st.rerun()
        if not st.session_state.finish and st.button("🏁 SINAVI BİTİR", type="primary"): 
            st.session_state.finish = True; st.rerun()

# --- 8. ANA EKRAN ---
if df is not None:
    if not st.session_state.finish:
        # --- SORU EKRANI ---
        control_col1, control_col2, control_col3, control_col4, control_col5 = st.columns([10, 1, 1, 1, 1])
        with control_col1: st.markdown(f"### Soru {st.session_state.idx + 1}")
        with control_col2: 
            if st.button("A➖"): st.session_state.font_size = max(12, st.session_state.font_size - 2); st.rerun()
        with control_col3: 
            if st.button("A➕"): st.session_state.font_size = min(30, st.session_state.font_size + 2); st.rerun()
        with control_col4: st.markdown(f"<div style='padding-top:8px;'>{st.session_state.font_size}px</div>", unsafe_allow_html=True)
        with control_col5:
            is_m = st.session_state.idx in st.session_state.marked
            if st.button("⭐" if is_m else "☆"):
                if is_m: st.session_state.marked.remove(st.session_state.idx)
                else: st.session_state.marked.add(st.session_state.idx)
                autosave_progress(); st.rerun()

        st.divider()
        row = df.iloc[st.session_state.idx]
        q_raw = str(row['Soru']).replace('\\n', '\n')
        passage, stem = (q_raw.split('\n\n', 1) if '\n\n' in q_raw else (None, q_raw))
        
        if passage:
            l, r = st.columns(2)
            l.markdown(f"<div class='passage-box' style='font-size:{st.session_state.font_size}px;'>{passage}</div>", unsafe_allow_html=True)
            main_col = r
        else: main_col = st.container()

        with main_col:
            st.markdown(f"<div class='question-stem' style='font-size:{st.session_state.font_size+2}px;'>{stem}</div>", unsafe_allow_html=True)
            opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
            curr = st.session_state.answers.get(st.session_state.idx)
            sel_idx = next((i for i,v in enumerate(opts) if v.startswith(str(curr) + ")")), None)
            sel = st.radio("Cevabınız:", opts, index=sel_idx, key=f"ans_{st.session_state.idx}")
            if sel:
                chosen = sel.split(")")[0]
                if st.session_state.answers.get(st.session_state.idx) != chosen:
                    st.session_state.answers[st.session_state.idx] = chosen
                    autosave_progress(); st.rerun()
                if not st.session_state.exam_mode:
                    if chosen == row['Dogru_Cevap']: st.success("✅ DOĞRU!")
                    else: st.error(f"❌ YANLIŞ! (Doğru: {row['Dogru_Cevap']})")

        c_act1, c_act2 = st.columns([1, 1])
        with c_act1:
            if st.button("🤖 AI Çözümle", use_container_width=True):
                if not st.session_state.user_api_key: st.warning("⚠️ API Key Girin")
                else:
                    with st.spinner("🔍 Stratejik Analiz Yapılıyor..."):
                        try:
                            # Şıkları string haline getir
                            options_str = "\n".join([f"{c}: {row[c]}" for c in "ABCDE" if pd.notna(row[c])])
                            
                            genai.configure(api_key=st.session_state.user_api_key)
                            model = genai.GenerativeModel('gemini-2.0-flash') # Güncel model
                            custom_prompt = f"""
                            Sen uzman bir YDS (Yabancı Dil Sınavı) İngilizce öğretmenisin. 
                            
                            SORU METNİ: {q_raw}
                            
                            ŞIKLAR:
                            {options_str}
                            
                            DOĞRU CEVAP: {row['Dogru_Cevap']}
                            
                            Lütfen cevabını şu katı şablona göre ver:
                            ### 1. 🎯 Soru Tipi ve Yaklaşım Stratejisi
                            (Bu soru hangi gramer/kelime konusunu ölçüyor?)
                            
                            ### 2. 💡 Detaylı Çözüm
                            (Neden doğru cevap {row['Dogru_Cevap']}? Cümle yapısını analiz et.)
                            
                            ### 3. ❌ Diğer Şıkların Analizi
                            (Lütfen yukarıda verilen her bir yanlış şıkkı ({[c for c in "ABCDE" if c != row['Dogru_Cevap']]}) tek tek ele al ve neden bu cümle için uygun olmadığını açıkla.)
                            
                            ### 4. 🇹🇷 Türkçe Çeviri
                            (Cümlenin tam çevirisi.)
                            """
                            res = model.generate_content(custom_prompt).text
                            st.session_state.gemini_res[st.session_state.idx] = res
                            st.rerun()
                        except Exception as e: st.error(f"Hata: {e}")
        with c_act2:
            c_p, c_n = st.columns(2)
            if st.session_state.idx > 0 and c_p.button("⬅️ Önceki", use_container_width=True): st.session_state.idx -= 1; st.rerun()
            if st.session_state.idx < len(df)-1 and c_n.button("Sonraki ➡️", use_container_width=True): st.session_state.idx += 1; st.rerun()
            
        if st.session_state.idx in st.session_state.gemini_res: 
            st.markdown(f'<div class="ai-result-box"><div class="ai-header"><div class="ai-header-icon">✨</div><div class="ai-title">AI Stratejisi</div></div><div class="ai-content">{st.session_state.gemini_res[st.session_state.idx]}</div></div>', unsafe_allow_html=True)

    else:
        # --- SONUÇ EKRANI ---
        st.title("🏆 Sınav Sonuç Paneli")
        correct = sum(1 for i, a in st.session_state.answers.items() if a == df.iloc[i]['Dogru_Cevap'])
        wrong = len(st.session_state.answers) - correct
        empty = len(df) - len(st.session_state.answers)
        score = correct * 1.25
        duration_min = math.floor(max(0, datetime.now().timestamp() * 1000 - st.session_state.start_timestamp) / 60000)
        duration_str = f"{duration_min} dk"
        
        if not st.session_state.data_saved:
            save_score_to_csv(st.session_state.username, f"Deneme {st.session_state.selected_exam_id}", score, correct, wrong, empty, duration_str)
            st.session_state.data_saved = True; st.balloons()
            
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam Puan", f"{score:.2f}")
        m2.metric("✅ Doğru", correct)
        m3.metric("❌ Yanlış", wrong)
        m4.metric("⏱️ Süre", duration_str)
        
        st.divider()
        g_col1, g_col2 = st.columns([1, 2])
        with g_col1:
            pie_data = pd.DataFrame({'Durum': ['Doğru', 'Yanlış', 'Boş'], 'Sayı': [correct, wrong, empty]})
            st.altair_chart(alt.Chart(pie_data).mark_arc(innerRadius=50).encode(theta="Sayı", color=alt.Color("Durum", scale=alt.Scale(domain=['Doğru', 'Yanlış', 'Boş'], range=['#4caf50', '#f44336', '#9e9e9e']))), use_container_width=True)

        with g_col2:
            if os.path.exists(SCORES_FILE):
                h_df = pd.read_csv(SCORES_FILE)
                u_h = h_df[h_df['Kullanıcı'] == st.session_state.username].reset_index()
                if not u_h.empty:
                    chart = alt.Chart(u_h).mark_line(point=True, color=primary_color).encode(x=alt.X('index:O', title='Sınav Sırası'), y=alt.Y('Puan:Q', scale=alt.Scale(domain=[0, 100])))
                    st.altair_chart(chart, use_container_width=True)

        st.subheader("🧠 YDS Baş Koç Analizi")
        if st.session_state.coach_analysis:
            st.markdown(f'<div class="ai-result-box"><div class="ai-content">{st.session_state.coach_analysis}</div></div>', unsafe_allow_html=True)
        else:
            if st.button("🚀 Analizi Başlat", type="primary"):
                if not st.session_state.user_api_key: st.warning("API Key girin.")
                else:
                    with st.spinner("Koç analiz yapıyor..."):
                        try:
                            # Hatalı soruların şıklarını da koça gönderelim
                            wrong_details = []
                            for idx, ans in st.session_state.answers.items():
                                if ans != df.iloc[idx]['Dogru_Cevap']:
                                    r = df.iloc[idx]
                                    wrong_details.append(f"Soru: {r['Soru'][:100]}... | Senin Cevabın: {ans} | Doğru: {r['Dogru_Cevap']}")

                            genai.configure(api_key=st.session_state.user_api_key)
                            model = genai.GenerativeModel('gemini-2.0-flash')
                            coach_prompt = f"""
                            YDS Koçu olarak öğrencini analiz et:
                            Puan: {score}, Doğru: {correct}, Yanlış: {wrong}, Boş: {empty}, Süre: {duration_str}.
                            Hatalı Sorular: {wrong_details[:5]}
                            Motivasyonel, yapıcı ve stratejik bir rapor yaz.
                            """
                            st.session_state.coach_analysis = model.generate_content(coach_prompt).text
                            st.rerun()
                        except: st.error("Analiz hatası.")

        if st.button("🔄 Yeni Sınav", type="primary"): 
            st.session_state.update({'finish': False, 'answers': {}, 'marked': set(), 'idx': 0, 'coach_analysis': None, 'data_saved': False})
            now_ms = datetime.now().timestamp() * 1000
            st.session_state.start_timestamp, st.session_state.end_timestamp = now_ms, now_ms + (180 * 60 * 1000)
            st.rerun()

# --- 9. JAVASCRIPT (Sağ Tık Şık Eleme) ---
components.html("""
<script>
    function toggleStrikethrough(element) {
        element.style.textDecoration = (element.style.textDecoration === "line-through") ? "none" : "line-through";
        element.style.opacity = (element.style.opacity === "0.5") ? "1" : "0.5";
    }
    const observer = new MutationObserver(() => {
        const labels = parent.document.querySelectorAll('div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p');
        labels.forEach(label => {
            if (label.getAttribute('data-strike') === 'true') return;
            label.setAttribute('data-strike', 'true');
            label.addEventListener('contextmenu', (e) => { e.preventDefault(); toggleStrikethrough(label); });
        });
    });
    observer.observe(parent.document.body, { childList: true, subtree: true });
</script>
""", height=0, width=0)
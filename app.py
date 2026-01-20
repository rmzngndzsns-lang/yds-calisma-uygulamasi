import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import google.generativeai as genai
import os
import json
import nest_asyncio
import re

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
    'dark_mode': True # Varsayılan olarak Dark Mode başlasın
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# --- 3. PROFESYONEL CSS (DÜZELTİLMİŞ & MINIMALIST) ---
# AI Kutuları için yeni, modern, göz yormayan tasarım
ai_box_css = """
    /* AI KUTU GENEL STİLİ - Modern Card Yapısı */
    .ai-box {
        background-color: #1e2126 !important; /* Çok koyu gri/antrasit arka plan */
        padding: 18px 22px;
        border-radius: 8px;
        margin-bottom: 16px;
        color: #e6e6e6 !important; /* Kırık beyaz metin - Okunabilirlik için */
        font-size: 15px;
        line-height: 1.7;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); /* Hafif gölge */
        border: 1px solid #363b42; /* İnce çerçeve */
        border-left-width: 5px; /* Sol çizgi kalın */
    }
    
    .ai-box h1, .ai-box h2, .ai-box h3, .ai-box h4, .ai-box strong {
        font-weight: 600;
        margin-bottom: 8px;
        display: block;
        color: #ffffff !important;
    }
    
    .ai-box ul { margin-left: 18px; margin-top: 5px; }
    .ai-box li { margin-bottom: 6px; }

    /* RENK PALETİ (Göz yormayan Pastel Tonlar) */
    
    /* 1. MANTIK: Soft Mavi */
    .ai-style-1 { border-left-color: #3b82f6 !important; }
    .ai-style-1 strong, .ai-style-1 h3 { color: #60a5fa !important; }

    /* 2. ANALİZ: Soft Yeşil */
    .ai-style-2 { border-left-color: #10b981 !important; }
    .ai-style-2 strong, .ai-style-2 h3 { color: #34d399 !important; }

    /* 3. KELİME: Soft Turuncu/Amber */
    .ai-style-3 { border-left-color: #f59e0b !important; }
    .ai-style-3 strong, .ai-style-3 h3 { color: #fbbf24 !important; }

    /* 4. ÇEVİRİ: Soft Mor */
    .ai-style-4 { border-left-color: #8b5cf6 !important; }
    .ai-style-4 strong, .ai-style-4 h3 { color: #a78bfa !important; }
    
    /* DEFAULT */
    .ai-style-default { border-left-color: #94a3b8 !important; }
"""

# Dark Mode ve Genel UI Düzeltmeleri
if st.session_state.dark_mode:
    main_css = f"""
    /* GENEL RENKLER */
    .stApp {{ background-color: #0e1117 !important; color: #e6e6e6 !important; }}
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] {{ background-color: #161b22 !important; border-right: 1px solid #30363d; }}
    section[data-testid="stSidebar"] * {{ color: #e6e6e6 !important; }}

    /* KUTULAR (Passage, Login) */
    .passage-box, .login-container {{ 
        background-color: #1e2126 !important; 
        color: #e6e6e6 !important; 
        border: 1px solid #363b42 !important; 
    }}
    
    /* SORU KÖKÜ */
    .question-stem {{ 
        color: #ffffff !important; 
        background-color: transparent !important; 
        border-left: 4px solid #3b82f6 !important;
        padding-left: 15px;
    }}
    
    /* INPUT & SELECTBOX ARKAPLANLARI */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {{ 
        background-color: #0d1117 !important; 
        color: #e6e6e6 !important; 
        border: 1px solid #30363d !important; 
    }}
    
    /* --- BUTON DÜZELTMESİ (KRİTİK) --- */
    /* Tüm butonları koyu yap, beyaz arka planı engelle */
    div.stButton > button {{
        background-color: #21262d !important; /* Koyu Gri */
        color: #c9d1d9 !important; /* Açık Gri Yazı */
        border: 1px solid #30363d !important;
        transition: all 0.2s ease;
    }}
    
    /* Hover (Üzerine gelince) */
    div.stButton > button:hover {{
        background-color: #30363d !important; /* Biraz daha açık gri */
        color: #58a6ff !important; /* Mavi yazı */
        border-color: #8b949e !important;
    }}
    
    /* Active (Tıklayınca) */
    div.stButton > button:active {{
        background-color: #238636 !important; 
        color: white !important;
    }}

    /* RADIO BUTTON YAZILARI */
    .stRadio label {{ color: #e6e6e6 !important; }}
    
    /* EXPANDER */
    .streamlit-expanderHeader {{ background-color: #1e2126 !important; color: #e6e6e6 !important; }}
    
    {ai_box_css}
    """
else:
    # Light Mode ayarları (AI kutuları yine de temiz kalsın)
    main_css = ai_box_css.replace("#1e2126", "#ffffff").replace("#e6e6e6", "#1e293b").replace("#363b42", "#e2e8f0")

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp {{ font-family: 'Inter', sans-serif; }}
    {main_css}
    
    /* SIDEBAR SORU BUTONLARI ÖZEL AYAR */
    div[data-testid="stSidebar"] div[data-testid="column"] button {{
        font-size: 12px !important; font-weight: 600 !important; border-radius: 6px !important;
        box-shadow: none !important;
        background-color: #21262d !important; /* Buton içi koyu */
        color: #c9d1d9 !important;
    }}
    
    /* UI ELEMENTLERİ */
    .login-container {{
        max-width: 400px; margin: 60px auto; padding: 40px;
        border-radius: 12px; text-align: center;
    }}
    .passage-box {{ 
        padding: 25px; border-radius: 10px; 
        overflow-y: auto; max-height: 70vh; line-height: 1.8;
    }}
    .control-panel {{
        margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #30363d;
    }}
    .legend-box {{
        background-color: transparent; border: 1px dashed #30363d;
        padding: 8px; border-radius: 6px; font-size: 11px;
        display: flex; justify-content: space-between; margin-bottom: 10px;
        color: #8b949e;
    }}
    
    /* AI Kutu Font Ayarları */
    .ai-box {{ font-family: 'Inter', sans-serif; }}
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
        st.markdown(f'<div class="login-container"><h1 style="color:#3b82f6;">YDS Pro</h1><p style="color:#8b949e;">Giriş Yapın</p></div>', unsafe_allow_html=True)
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
            f"""<div style="font-family:'Inter',sans-serif;font-size:16px;font-weight:bold;color:#ff6b6b;text-align:center;padding:10px;background:#2d1b1b;border-radius:8px;border:1px solid #4a2c2c;">⏳ <span id="countdown">Hesapla...</span></div>
            <script>
            var dest={st.session_state.end_timestamp};
            var interval = setInterval(function(){{
                var now=new Date().getTime();
                var dist=dest-now;
                if(dist <= 0) {{ clearInterval(interval); document.getElementById("countdown").innerHTML="BİTTİ!"; return; }}
                var h=Math.floor((dist%(1000*60*60*24))/(1000*60*60));
                var m=Math.floor((dist%(1000*60*60))/(1000*60));
                var s=Math.floor((dist%(1000*60))/1000);
                document.getElementById("countdown").innerHTML=(h<10?"0"+h:h)+":"+(m<10?"0"+m:m)+":"+(s<10?"0"+s:s);
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
            st.markdown(f"<h3 style='margin:0;padding:0;color:{'#ffffff' if st.session_state.dark_mode else '#1e293b'};'>Soru {st.session_state.idx + 1}</h3>", unsafe_allow_html=True)
        with control_col2: 
            if st.button("A➖", key="font_dec"): 
                st.session_state.font_size = max(12, st.session_state.font_size - 2)
                st.rerun()
        with control_col3: 
            if st.button("A➕", key="font_inc"): 
                st.session_state.font_size = min(30, st.session_state.font_size + 2)
                st.rerun()
        with control_col4: 
            st.markdown(f"<div style='text-align:center;padding-top:8px;font-size:12px;color:{'#e6e6e6' if st.session_state.dark_mode else '#1e293b'};'>{st.session_state.font_size}px</div>", unsafe_allow_html=True)
        with control_col5:
            is_m = st.session_state.idx in st.session_state.marked
            if st.button("⭐" if is_m else "☆", key="mark_tgl"):
                if is_m: st.session_state.marked.remove(st.session_state.idx)
                else: st.session_state.marked.add(st.session_state.idx)
                autosave_progress()
                st.rerun()

        st.markdown("<hr style='margin:15px 0; border-color: #30363d;'>", unsafe_allow_html=True)
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
            
            # --- CEVAP MEKANİZMASI ---
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
            
            # --- DÜZELTİLMİŞ TEMİZLE BUTONU ---
            if curr is not None:
                if st.button("🗑️ Seçimi Temizle", key=f"clr_{st.session_state.idx}", help="Bu sorudaki işaretlemeyi kaldır"):
                    del st.session_state.answers[st.session_state.idx]
                    if f"ans_{st.session_state.idx}" in st.session_state:
                        del st.session_state[f"ans_{st.session_state.idx}"]
                    autosave_progress()
                    st.rerun()
            # ------------------------------------------------

        st.write("")
        c_act1, c_act2 = st.columns([1, 1])
        with c_act1:
            if st.button("🤖 AI Çözümle", use_container_width=True):
                if not st.session_state.user_api_key: st.warning("⚠️ API Key Girin")
                else:
                    with st.spinner("🔍 Analiz Ediliyor..."):
                        try:
                            genai.configure(api_key=st.session_state.user_api_key)
                            model = genai.GenerativeModel('gemini-2.5-flash')
                            
                            # PROMPT
                            prompt = f"""
                            Sen uzman bir YDS öğretmenisin.
                            Soru: {q_raw}
                            Doğru: {row['Dogru_Cevap']}
                            
                            Lütfen cevabı TAM OLARAK aşağıdaki 4 numaralı başlık formatında ver. 
                            
                            1. 🧠 **Sorunun Mantığı:**
                            (Kısa ve net strateji)

                            2. 🔍 **Detaylı Analiz:**
                            (Şık şık inceleme)

                            3. 📚 **Kritik Kelimeler:**
                            (Kelime - Anlam listesi)

                            4. 🇹🇷 **Tam Çeviri:**
                            (Türkçe karşılığı)
                            """
                            
                            res = model.generate_content(prompt).text
                            st.session_state.gemini_res[st.session_state.idx] = res
                            st.rerun()
                        except Exception as e: st.error(f"Hata: {e}")
        with c_act2:
            c_p, c_n = st.columns(2)
            if st.session_state.idx > 0 and c_p.button("⬅️ Önceki", use_container_width=True): 
                st.session_state.idx -= 1; st.rerun()
            if st.session_state.idx < len(df)-1 and c_n.button("Sonraki ➡️", use_container_width=True): 
                st.session_state.idx += 1; st.rerun()
            
        # --- MODERN AI ÇIKTISI (PARSER) ---
        if st.session_state.idx in st.session_state.gemini_res: 
            raw_text = st.session_state.gemini_res[st.session_state.idx]
            sections = re.split(r'(?=\d+\.\s)', raw_text)
            
            if len(sections) < 2:
                 st.markdown(f"<div class='ai-box ai-style-default'>{raw_text}</div>", unsafe_allow_html=True)
            else:
                for sec in sections:
                    if not sec.strip(): continue 
                    
                    style_class = "ai-style-default"
                    if "1." in sec: style_class = "ai-style-1"
                    elif "2." in sec: style_class = "ai-style-2"
                    elif "3." in sec: style_class = "ai-style-3"
                    elif "4." in sec: style_class = "ai-style-4"
                    
                    st.markdown(f"<div class='ai-box {style_class}'>{sec}</div>", unsafe_allow_html=True)

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

# --- 9. JAVASCRIPT: ŞIK ELEME ÖZELLİĞİ ---
components.html("""
<script>
    function toggleStrikethrough(element) {
        if (element.style.textDecoration === "line-through") {
            element.style.textDecoration = "none";
            element.style.opacity = "1";
        } else {
            element.style.textDecoration = "line-through";
            element.style.opacity = "0.5";
        }
    }

    const observer = new MutationObserver((mutations) => {
        const labels = parent.document.querySelectorAll('div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p');
        labels.forEach(label => {
            if (label.getAttribute('data-strike-listener') === 'true') return;
            label.setAttribute('data-strike-listener', 'true');
            label.addEventListener('contextmenu', function(e) { e.preventDefault(); toggleStrikethrough(this); }, false);
            let pressTimer;
            label.addEventListener('touchstart', function(e) {
                pressTimer = setTimeout(() => { toggleStrikethrough(this); if (navigator.vibrate) navigator.vibrate(50); }, 600);
            });
            label.addEventListener('touchend', function(e) { clearTimeout(pressTimer); });
            label.addEventListener('touchmove', function(e) { clearTimeout(pressTimer); });
        });
    });
    observer.observe(parent.document.body, { childList: true, subtree: true });
</script>
""", height=0, width=0)
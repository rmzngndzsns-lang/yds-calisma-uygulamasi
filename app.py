import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="YDS Pro", page_icon="🎓", layout="wide")

# --- 2. AGRESİF MOBİL CSS (GRID ZORLAMA) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #f3f4f6;
    }
    
    /* --- KESİN ÇÖZÜM: SIDEBAR KOLONLARINI ZORLA YAN YANA TUT --- */
    
    /* 1. Sidebar içindeki kolon container'ını yakala */
    [data-testid="stSidebar"] [data-testid="column"] {
        width: 20% !important;       /* Ekranın tam 5'te 1'i */
        flex: 0 0 20% !important;    /* Esnemeyi durdur, %20'de sabitle */
        min-width: 0px !important;   /* Streamlit'in mobil korumasını devre dışı bırak */
        padding: 0px 1px !important; /* Aradaki boşlukları neredeyse sıfırla */
        display: inline-block !important; /* Yan yana dizilmeyi zorla */
    }

    /* 2. Butonların kendisini ayarla */
    [data-testid="stSidebar"] button {
        width: 100% !important;
        padding: 0px !important;
        margin: 0px 0px 4px 0px !important; /* Altına az boşluk */
        height: 35px !important;
        border-radius: 4px !important;
        font-weight: 700 !important;
        border: 1px solid #d1d5db;
        line-height: 1 !important;
    }
    
    /* 3. MOBİL CİHAZLAR İÇİN ÖZEL AYAR (Yazılar birbirine girmesin) */
    @media (max-width: 640px) {
        [data-testid="stSidebar"] button {
            font-size: 10px !important; /* Yazıyı küçült */
            height: 30px !important;    /* Butonu kısalt */
            padding-left: 0px !important;
            padding-right: 0px !important;
        }
        /* İşaretli/Cevaplı ikonlarını sığdırmak için */
        [data-testid="stSidebar"] button div {
             justify-content: center !important;
        }
    }
    
    /* Masaüstü Yazı Boyutu */
    @media (min-width: 641px) {
        [data-testid="stSidebar"] button {
            font-size: 12px !important;
        }
    }

    /* --- DİĞER STİLLER --- */
    
    /* Okuma Parçası */
    .passage-box {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        height: 50vh;
        overflow-y: auto;
        font-size: 15px;
        line-height: 1.6;
        text-align: justify;
        border: 1px solid #e5e7eb;
        border-left: 4px solid #2c3e50;
    }

    /* Soru Alanı */
    .question-stem {
        font-size: 16px;
        font-weight: 600;
        background-color: white;
        padding: 15px;
        border: 1px solid #e5e7eb;
        border-left: 4px solid #3b82f6;
        border-radius: 10px;
        color: #111827;
        margin-bottom: 20px;
        line-height: 1.5;
    }

    /* Radyo Butonlar */
    .stRadio > label { display: none; }
    .stRadio div[role='radiogroup'] > label {
        padding: 10px 12px;
        margin-bottom: 6px;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        background-color: white;
        font-size: 15px;
        color: #374151;
    }
    .stRadio div[role='radiogroup'] > label:hover {
        background-color: #eff6ff;
        border-color: #3b82f6;
    }

    /* İşaretle Butonu */
    div.stButton > button:contains("İşaretle") {
        border-color: #d97706 !important;
        color: #d97706 !important;
        font-weight: 700;
    }
    div.stButton > button:contains("Kaldır") {
        background-color: #d97706 !important;
        color: white !important;
        border: none;
    }
    
    /* Navigasyon Butonları */
    div.stButton > button {
        height: 45px;
        font-weight: 500;
        font-size: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. VERİ YÜKLEME ---
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("sorular.xlsx", engine="openpyxl")
        df['Dogru_Cevap'] = df['Dogru_Cevap'].astype(str).str.strip().str.upper()
        return df
    except:
        return None

# --- 4. SESSION BAŞLATMA ---
def init_session():
    if 'idx' not in st.session_state: st.session_state.idx = 0
    if 'answers' not in st.session_state: st.session_state.answers = {}
    if 'marked' not in st.session_state: st.session_state.marked = set()
    
    if 'end_timestamp' not in st.session_state:
        future = datetime.now() + timedelta(minutes=180)
        st.session_state.end_timestamp = future.timestamp() * 1000 

    if 'finish' not in st.session_state: st.session_state.finish = False

df = load_data()
init_session()

# --- 5. PARSER ---
def parse_question(text):
    if pd.isna(text): return None, "..."
    text = str(text).replace('\\n', '\n')
    if '\n\n' in text:
        parts = text.split('\n\n', 1)
        return parts[0].strip(), parts[1].strip()
    return None, text.strip()

# --- 6. UYGULAMA GÖVDESİ ---
if df is not None:
    
    # --- SIDEBAR ---
    with st.sidebar:
        # SAYAÇ
        end_ts = st.session_state.end_timestamp
        timer_html = f"""
        <div style="
            font-family: 'Courier New', monospace;
            font-size: 32px; 
            font-weight: 800; 
            color: #dc2626; 
            background-color: #ffffff;
            padding: 5px 0px;
            border-radius: 8px;
            text-align: center;
            border: 3px solid #dc2626;
            margin-bottom: 15px;
            letter-spacing: 1px;
            width: 100%;
        " id="countdown">...</div>
        <script>
            var countDownDate = {end_ts};
            var x = setInterval(function() {{
                var now = new Date().getTime();
                var distance = countDownDate - now;
                var h = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                var m = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                var s = Math.floor((distance % (1000 * 60)) / 1000);
                h = h < 10 ? "0" + h : h; m = m < 10 ? "0" + m : m; s = s < 10 ? "0" + s : s;
                document.getElementById("countdown").innerHTML = h + ":" + m + ":" + s;
                if (distance < 0) {{ clearInterval(x); document.getElementById("countdown").innerHTML = "00:00:00"; }}
            }}, 1000);
        </script>
        """
        components.html(timer_html, height=70)
        
        st.caption("🟢:D | 🔴:Y | ⭐:İşaret")
        
        # --- KESİN ÇÖZÜM İÇİN YENİ GRID YAPISI ---
        # st.columns(5)'i döngü içinde değil, TEK SEFERDE çağırıyoruz.
        # Böylece Streamlit 5 tane uzun sütun oluşturuyor.
        # CSS ile bu sütunları %20 genişliğe zorladığımız için mobilde alt alta geçemiyorlar.
        
        grid_cols = st.columns(5)
        
        for i in range(len(df)):
            u_ans = st.session_state.answers.get(i)
            c_ans = df.iloc[i]['Dogru_Cevap']
            
            label = str(i+1)
            
            if u_ans:
                if u_ans == c_ans: label = "✅"
                else: label = "❌"
            elif i in st.session_state.marked:
                label = "⭐"
            
            b_type = "primary" if i == st.session_state.idx else "secondary"
            
            # Sütunları sırasıyla dolduruyoruz (1. sütun, 2. sütun...)
            # i % 5 formülü ile 1, 6, 11. sorular 1. sütuna gider.
            # 2, 7, 12. sorular 2. sütuna gider.
            with grid_cols[i % 5]:
                if st.button(label, key=f"n{i}", type=b_type, use_container_width=True):
                    st.session_state.idx = i
                    st.rerun()

        st.divider()
        if st.button("SINAVI BİTİR", type="primary", use_container_width=True):
            st.session_state.finish = True
            st.rerun()

    # --- ANA EKRAN ---
    if not st.session_state.finish:
        # Başlık
        st.markdown(f"### Soru {st.session_state.idx + 1} / {len(df)}")
        
        row = df.iloc[st.session_state.idx]
        passage, stem = parse_question(row['Soru'])

        # İşaretleme Butonu
        is_marked = st.session_state.idx in st.session_state.marked
        btn_txt = "🏳️ Kaldır" if is_marked else "🏳️ İşaretle"
        
        c_mark, c_dummy = st.columns([2, 5]) # Butona biraz daha yer açtık mobilde sığsın diye
        if c_mark.button(btn_txt, key="mark_q"):
            if is_marked: st.session_state.marked.remove(st.session_state.idx)
            else: st.session_state.marked.add(st.session_state.idx)
            st.rerun()

        # DÜZEN
        if passage:
            col_l, col_r = st.columns([1, 1], gap="medium")
            with col_l:
                st.info("Okuma Parçası")
                st.markdown(f"<div class='passage-box'>{passage}</div>", unsafe_allow_html=True)
            with col_r:
                st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
                
                opts, opt_map = [], {}
                for char in ['A','B','C','D','E']:
                    if pd.notna(row[char]):
                        full = f"{char}) {row[char]}"
                        opts.append(full)
                        opt_map[full] = char
                
                curr = st.session_state.answers.get(st.session_state.idx)
                idx_s = None
                if curr:
                    for k,v in enumerate(opts):
                        if v.startswith(curr+")"): idx_s = k; break
                
                sel = st.radio("Cevap:", opts, index=idx_s, key=f"r{st.session_state.idx}", label_visibility="collapsed")
                
                if sel:
                    sel_char = opt_map[sel]
                    st.session_state.answers[st.session_state.idx] = sel_char
                    true_char = row['Dogru_Cevap']
                    if sel_char == true_char: st.success("✅ DOĞRU")
                    else: st.error(f"❌ YANLIŞ! (Cevap: {true_char})")
        else:
            st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
            opts, opt_map = [], {}
            for char in ['A','B','C','D','E']:
                if pd.notna(row[char]):
                    full = f"{char}) {row[char]}"
                    opts.append(full)
                    opt_map[full] = char
            
            curr = st.session_state.answers.get(st.session_state.idx)
            idx_s = None
            if curr:
                for k,v in enumerate(opts):
                    if v.startswith(curr+")"): idx_s = k; break
            
            sel = st.radio("Cevap:", opts, index=idx_s, key=f"r{st.session_state.idx}", label_visibility="collapsed")
            
            if sel:
                sel_char = opt_map[sel]
                st.session_state.answers[st.session_state.idx] = sel_char
                true_char = row['Dogru_Cevap']
                if sel_char == true_char: st.success("✅ DOĞRU")
                else: st.error(f"❌ YANLIŞ! (Cevap: {true_char})")

        # NAVİGASYON
        st.markdown("<br>", unsafe_allow_html=True)
        col_prev, col_next = st.columns([1, 1])
        
        if st.session_state.idx > 0:
            col_prev.button("⬅️ Önceki Soru", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx-1), use_container_width=True)
        
        if st.session_state.idx < len(df) - 1:
            st.markdown("""<style>div[data-testid="column"]:nth-of-type(2) button {background-color:#3b82f6; color:white; border:none;}</style>""", unsafe_allow_html=True)
            col_next.button("Sonraki Soru ➡️", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx+1), use_container_width=True)

    else:
        st.title("Sınav Sonuçları")
        c, w, e = 0, 0, 0
        data = []
        for i in range(len(df)):
            ua = st.session_state.answers.get(i)
            ca = df.iloc[i]['Dogru_Cevap']
            if ua:
                if ua == ca: c+=1; s="Doğru"
                else: w+=1; s="Yanlış"
            else: e+=1; s="Boş"
            data.append({"Soru": i+1, "Cevabın": ua, "Doğru Cevap": ca, "Durum": s})
            
        col1, col2, col3 = st.columns(3)
        col1.metric("Doğru", c)
        col2.metric("Yanlış", w)
        col3.metric("Boş", e)
        st.dataframe(pd.DataFrame(data), use_container_width=True)
        if st.button("Yeniden Başlat"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

else:
    st.error("Excel dosyası yüklenemedi.")
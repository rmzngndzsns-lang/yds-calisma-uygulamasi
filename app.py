import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="YDS Pro", page_icon="📱", layout="wide", initial_sidebar_state="collapsed")

# --- 2. MOBİL UYUMLU CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@700&display=swap');
    
    .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #f3f4f6;
    }
    
    /* DUYARLI SAYAÇ (MOBİLDE KÜÇÜLÜR, MASAÜSTÜNDE BÜYÜR) */
    .sidebar-timer {
        font-family: 'Roboto Mono', monospace;
        color: #dc2626;
        background-color: #ffffff;
        padding: 10px 5px;
        border-radius: 8px;
        text-align: center;
        border: 2px solid #dc2626;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        width: 100%;
        box-sizing: border-box;
    }
    
    /* Masaüstü Yazı Boyutu */
    @media (min-width: 768px) {
        .sidebar-timer { font-size: 32px; font-weight: 900; letter-spacing: 2px; }
    }
    /* Mobil Yazı Boyutu */
    @media (max-width: 767px) {
        .sidebar-timer { font-size: 22px; font-weight: 700; letter-spacing: 1px; padding: 8px; }
    }

    /* Okuma Parçası */
    .passage-box {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        max-height: 50vh; /* Mobilde çok yer kaplamasın */
        overflow-y: auto;
        font-size: 15px;
        line-height: 1.6;
        text-align: justify;
        border: 1px solid #e5e7eb;
        border-left: 4px solid #2c3e50;
        margin-bottom: 15px;
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
        margin-bottom: 15px;
        line-height: 1.5;
    }

    /* Radyo Butonlar */
    .stRadio > label { display: none; }
    .stRadio div[role='radiogroup'] > label {
        padding: 12px;
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
        font-weight: 600;
        width: 100%; /* Mobilde tam genişlik */
    }
    div.stButton > button:contains("Kaldır") {
        background-color: #d97706 !important;
        color: white !important;
        width: 100%;
    }
    
    /* Navigasyon Butonları */
    div.stButton > button {
        height: 45px;
        font-weight: 500;
        font-size: 15px;
        width: 100%;
    }
    
    /* Sidebar Butonları (Masaüstü için 5'li, Mobil için Dropdown yapacağız) */
    div[data-testid="stSidebar"] button {
        padding: 0px;
        height: 35px;
        font-size: 13px;
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
    
    # --- SIDEBAR (MOBİL UYUMLU NAVİGASYON) ---
    with st.sidebar:
        # SAYAÇ
        end_ts = st.session_state.end_timestamp
        timer_html = f"""
        <div class="sidebar-timer" id="countdown">...</div>
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
        components.html(timer_html, height=80)

        # MOBİLDE DROPDOWN, MASAÜSTÜNDE GRID
        # Streamlit'te ekran boyutunu Python ile algılayamayız, o yüzden kullanıcıya seçenek sunuyoruz
        # VEYA basitçe "Soru Seç" listesi koyuyoruz ki mobilde kaymasın.
        
        st.markdown("### 🗺️ Soru Gezgini")
        
        # Seçenek 1: Hızlı Atlama Listesi (Mobilde Bozulmaz)
        question_options = []
        for i in range(len(df)):
            durum = "⚪"
            if i in st.session_state.marked: durum = "⭐"
            if i in st.session_state.answers:
                if st.session_state.answers[i] == df.iloc[i]['Dogru_Cevap']: durum = "✅"
                else: durum = "❌"
            question_options.append(f"Soru {i+1} {durum}")
            
        selected_q_str = st.selectbox(
            "Listeden Seç:", 
            question_options, 
            index=st.session_state.idx,
            label_visibility="collapsed"
        )
        
        # Seçim değiştiyse güncelle
        new_idx = int(selected_q_str.split()[1]) - 1
        if new_idx != st.session_state.idx:
            st.session_state.idx = new_idx
            st.rerun()
            
        st.divider()
        
        # Klasik Grid Görünümü (İsteyen İçin Aşağıda)
        with st.expander("Tüm Paleti Göster (Masaüstü)"):
            cols = st.columns(5)
            for i in range(len(df)):
                u_ans = st.session_state.answers.get(i)
                c_ans = df.iloc[i]['Dogru_Cevap']
                label = str(i+1)
                if u_ans:
                    label = "✅" if u_ans == c_ans else "❌"
                elif i in st.session_state.marked:
                    label = "⭐"
                
                b_type = "primary" if i == st.session_state.idx else "secondary"
                if cols[i%5].button(label, key=f"n{i}", type=b_type, use_container_width=True):
                    st.session_state.idx = i
                    st.rerun()

        st.divider()
        if st.button("SINAVI BİTİR", type="primary", use_container_width=True):
            st.session_state.finish = True
            st.rerun()

    # --- ANA EKRAN ---
    if not st.session_state.finish:
        # Başlık ve İşaretle Butonu (Yan Yana)
        c_title, c_mark = st.columns([2, 1])
        with c_title:
            st.markdown(f"**Soru {st.session_state.idx + 1}**")
        with c_mark:
            is_marked = st.session_state.idx in st.session_state.marked
            btn_txt = "🏳️ Kaldır" if is_marked else "🚩 İşaretle"
            if st.button(btn_txt, key="mark_q"):
                if is_marked: st.session_state.marked.remove(st.session_state.idx)
                else: st.session_state.marked.add(st.session_state.idx)
                st.rerun()

        row = df.iloc[st.session_state.idx]
        passage, stem = parse_question(row['Soru'])

        # İÇERİK DÜZENİ (Mobilde Alt Alta Olsun Diye Columns Kullanımını Şartlara Bağladık)
        
        # Paragraf Varsa
        if passage:
            # Streamlit columns mobilde otomatik alt alta düşer ama bazen sıkışır.
            # Mobilde daha rahat okuma için önce Paragrafı tam genişlikte veriyoruz.
            st.info("📖 Okuma Parçası")
            st.markdown(f"<div class='passage-box'>{passage}</div>", unsafe_allow_html=True)
            
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
        
        # Paragraf Yoksa
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

        # ALT NAVİGASYON (MOBİL DOSTU)
        st.write("") # Boşluk
        col_prev, col_next = st.columns([1, 1])
        
        if st.session_state.idx > 0:
            col_prev.button("⬅️ Geri", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx-1), use_container_width=True)
        
        if st.session_state.idx < len(df) - 1:
            st.markdown("""<style>div[data-testid="column"]:nth-of-type(2) button {background-color:#3b82f6; color:white; border:none;}</style>""", unsafe_allow_html=True)
            col_next.button("İleri ➡️", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx+1), use_container_width=True)

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
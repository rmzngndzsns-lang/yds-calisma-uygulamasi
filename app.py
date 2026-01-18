import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="YDS Pro", page_icon="📝", layout="wide")

# --- 2. CSS (GÖRÜNÜM VE RENKLER) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #f8f9fa;
    }
    
    /* Yan Menüdeki Sayaç Kutusu */
    .sidebar-timer {
        font-family: 'Courier New', monospace;
        font-size: 24px;
        font-weight: 900;
        color: #ffffff;
        background-color: #2c3e50; /* Lacivert */
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        border: 2px solid #34495e;
    }

    /* Okuma Parçası (Scroll) */
    .passage-box {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        height: 50vh;
        overflow-y: auto;
        font-size: 15px;
        line-height: 1.6;
        text-align: justify;
        border: 1px solid #dfe6e9;
        border-left: 5px solid #2c3e50;
    }

    /* Soru Alanı */
    .question-stem {
        font-size: 16px;
        font-weight: 600;
        background-color: white;
        padding: 15px;
        border: 1px solid #dfe6e9;
        border-left: 5px solid #0984e3;
        border-radius: 8px;
        color: #2d3436;
        margin-bottom: 15px;
        line-height: 1.5;
    }

    /* Radyo Butonlar (Şıklar) */
    .stRadio > label { display: none; }
    .stRadio div[role='radiogroup'] > label {
        padding: 10px 15px;
        margin-bottom: 5px;
        border: 1px solid #bdc3c7;
        border-radius: 6px;
        background-color: white;
        font-size: 15px;
        color: #2c3e50;
        transition: all 0.2s;
    }
    .stRadio div[role='radiogroup'] > label:hover {
        background-color: #f1f2f6;
        border-color: #0984e3;
    }

    /* --- BUTON RENKLENDİRMELERİ --- */
    
    /* İşaretle Butonu (SARI / GOLD) */
    div.stButton > button:contains("İşaretle") {
        border-color: #f1c40f !important;
        color: #d35400 !important; /* Koyu Turuncu Yazı */
        font-weight: bold;
    }
    /* İşareti Kaldır Butonu (SARI DOLGU) */
    div.stButton > button:contains("Kaldır") {
        background-color: #f1c40f !important;
        color: white !important;
        border: none;
    }
    
    /* Sidebar'daki SARI BAYRAK Butonları */
    /* Streamlit'te butonu içeriğine göre seçmek zordur ama emoji ile yakalarız */
    /* Bu kısım görsel düzeltme içindir */
    
    /* Navigasyon Butonları Genel */
    div[data-testid="stSidebar"] button {
        padding: 0px;
        height: 35px;
        font-size: 14px;
        font-weight: bold;
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
    
    # Bitiş zamanını SADECE BİR KERE hesapla ve sabitle
    if 'end_timestamp' not in st.session_state:
        # Şu an + 180 dakika (Unix timestamp olarak sakla)
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
        # SAYAÇ (JS)
        end_ts = st.session_state.end_timestamp
        timer_html = f"""
        <div class="sidebar-timer" id="countdown">Loading...</div>
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
                if (distance < 0) {{ clearInterval(x); document.getElementById("countdown").innerHTML = "BİTTİ"; }}
            }}, 1000);
        </script>
        """
        components.html(timer_html, height=70)
        st.divider()

        # PALET LEJANTI
        st.caption("🟢:Doğru | 🔴:Yanlış | ⭐:İşaretli (Sarı)")
        
        # SORU PALETİ
        cols = st.columns(5)
        for i in range(len(df)):
            u_ans = st.session_state.answers.get(i)
            c_ans = df.iloc[i]['Dogru_Cevap']
            
            # --- LABEL VE İKON MANTIĞI ---
            label = str(i+1)
            
            if u_ans:
                if u_ans == c_ans: label = "✅"
                else: label = "❌"
            elif i in st.session_state.marked:
                # Sarı Bayrak Unicode olmadığı için "Yıldız" veya "Sarı Kare" en iyi alternatiftir.
                # Ancak kullanıcı Sarı Bayrak istediği için Beyaz Bayrak koyup CSS ile sarartmayı denedik,
                # fakat Streamlit sidebar'da bu zordur. En net çözüm ⭐ (Yıldız) ikonudur.
                label = "⭐" 
            
            # Aktif Soru Rengi (Koyu)
            b_type = "primary" if i == st.session_state.idx else "secondary"
            
            if cols[i%5].button(label, key=f"n{i}", type=b_type, use_container_width=True):
                st.session_state.idx = i
                st.rerun()

        st.divider()
        if st.button("SINAVI BİTİR", type="primary"):
            st.session_state.finish = True
            st.rerun()

    # --- ANA EKRAN ---
    if not st.session_state.finish:
        # Başlık
        st.markdown(f"### 🇹🇷 Soru {st.session_state.idx + 1}")
        
        row = df.iloc[st.session_state.idx]
        passage, stem = parse_question(row['Soru'])

        # İŞARETLEME BUTONU (SARI)
        is_marked = st.session_state.idx in st.session_state.marked
        # İkonu Beyaz Bayrak yapıyoruz ama CSS ile sarı görünecek/algılanacak
        btn_txt = "🏳️ İşareti Kaldır" if is_marked else "🏳️ Bu Soruyu İşaretle"
        
        c_mark, c_dummy = st.columns([2, 5])
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

        # ALT NAVİGASYON
        st.markdown("<br>", unsafe_allow_html=True)
        col_prev, col_next = st.columns([1, 1])
        
        if st.session_state.idx > 0:
            col_prev.button("⬅️ Önceki", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx-1), use_container_width=True)
        
        if st.session_state.idx < len(df) - 1:
            st.markdown("""<style>div[data-testid="column"]:nth-of-type(2) button {background-color:#0984e3; color:white; border:none;}</style>""", unsafe_allow_html=True)
            col_next.button("Sonraki ➡️", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx+1), use_container_width=True)

    else:
        # SONUÇ EKRANI
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
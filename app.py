import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta

# --- 1. SAYFA AYARLARI (Geniş ve Sıkışık Mod) ---
st.set_page_config(page_title="YDS Compact", page_icon="⚡", layout="wide")

# --- 2. KOMPAKT CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #f8f9fa;
    }
    
    /* Bloklar arası varsayılan boşluğu azalt */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }

    /* Sayaç Kutusu (Daha küçük) */
    .timer-box {
        font-size: 20px;
        font-weight: 700;
        color: #d63031;
        background-color: #fff;
        padding: 4px 12px;
        border-radius: 6px;
        border: 1px solid #d63031;
        text-align: center;
        width: 120px;
    }

    /* Okuma Parçası (Kompakt) */
    .passage-box {
        background-color: white;
        padding: 15px; /* Daha az padding */
        border-radius: 8px;
        height: 50vh; /* Ekranın yarısı kadar yükseklik */
        overflow-y: auto;
        font-size: 14.5px; /* Daha okunaklı ama küçük font */
        line-height: 1.6;
        text-align: justify;
        border: 1px solid #dee2e6;
        border-left: 4px solid #2c3e50;
    }

    /* Soru Kökü (Daha sıkışık) */
    .question-stem {
        font-size: 16px;
        font-weight: 600;
        background-color: #ffffff;
        padding: 15px;
        border: 1px solid #dee2e6;
        border-left: 4px solid #0984e3;
        border-radius: 6px;
        color: #212529;
        margin-bottom: 12px;
        line-height: 1.5;
    }

    /* Radyo Butonları (Şıklar) - Kompakt */
    .stRadio > label {
        font-size: 14px;
        display: none; /* "Seçiniz" yazısını gizle */
    }
    .stRadio div[role='radiogroup'] > label {
        padding: 8px 12px; /* Buton içi boşluğu azalt */
        margin-bottom: 4px; /* Buton arası boşluğu azalt */
        border-radius: 6px;
        border: 1px solid #ced4da;
        background-color: #fff;
        font-size: 14.5px;
    }
    .stRadio div[role='radiogroup'] > label:hover {
        background-color: #e9ecef;
        border-color: #0d6efd;
    }

    /* Sidebar Butonları (Kare Kare) */
    div[data-testid="stSidebar"] button {
        padding: 2px 0px;
        font-size: 13px;
        min-height: 0px;
        height: 35px;
    }
    
    /* İleri/Geri Butonları (Kompakt) */
    div.stButton > button {
        height: 40px;
        padding: 0px;
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

def init_session():
    if 'idx' not in st.session_state: st.session_state.idx = 0
    if 'answers' not in st.session_state: st.session_state.answers = {}
    if 'marked' not in st.session_state: st.session_state.marked = set()
    if 'start_time' not in st.session_state: st.session_state.start_time = datetime.now()
    if 'finish' not in st.session_state: st.session_state.finish = False

df = load_data()
init_session()

# --- 4. SAYAÇ HESABI ---
now = datetime.now()
elapsed = (now - st.session_state.start_time).total_seconds()
remaining = max(0, int((180 * 60) - elapsed))

# --- 5. PARSER ---
def parse_question(text):
    if pd.isna(text): return None, "..."
    text = str(text).replace('\\n', '\n')
    if '\n\n' in text:
        parts = text.split('\n\n', 1)
        return parts[0].strip(), parts[1].strip()
    return None, text.strip()

# --- 6. UYGULAMA ---
if df is not None:
    
    # --- HEADER (Çok İnce) ---
    c1, c2, c3 = st.columns([3, 5, 2])
    with c1:
        st.markdown("**YDS 2021/1**") # Başlığı küçülttük
    with c3:
        # JS Sayaç
        st.components.v1.html(f"""
            <div class="timer-box" id="t">...</div>
            <script>
                var tl = {remaining};
                setInterval(function(){{
                    var h = Math.floor(tl/3600);
                    var m = Math.floor((tl%3600)/60);
                    var s = Math.floor(tl%60);
                    document.getElementById("t").innerHTML = 
                        (h<10?"0":"")+h + ":" + (m<10?"0":"")+m + ":" + (s<10?"0":"")+s;
                    tl--;
                }}, 1000);
            </script>
        """, height=40)

    # --- SIDEBAR (Soru Paleti) ---
    with st.sidebar:
        st.caption("🟢:D | 🔴:Y | ⚪:B")
        cols = st.columns(5)
        for i in range(len(df)):
            # Durum Rengi
            u_ans = st.session_state.answers.get(i)
            c_ans = df.iloc[i]['Dogru_Cevap']
            label = str(i+1)
            
            # Emojisiz, sadece renkli kenarlık/buton stili (Daha temiz görünüm için)
            # Ama Streamlit'te butona stil veremediğimiz için emoji mecburi
            if i in st.session_state.marked: label = "🚩"
            elif u_ans:
                label = "✅" if u_ans == c_ans else "❌"
            
            # Aktif soru ise primary
            b_type = "primary" if i == st.session_state.idx else "secondary"
            
            if cols[i%5].button(label, key=f"n{i}", type=b_type, use_container_width=True):
                st.session_state.idx = i
                st.rerun()
        
        st.divider()
        if st.button("Bitir", type="primary"):
            st.session_state.finish = True
            st.rerun()

    # --- ANA İÇERİK ---
    if not st.session_state.finish:
        row = df.iloc[st.session_state.idx]
        passage, stem = parse_question(row['Soru'])

        # İşaretleme Butonu (Küçük)
        is_m = st.session_state.idx in st.session_state.marked
        if st.button("🚩 İşaretle" if not is_m else "🏳️ Kaldır", key="mark"):
            if is_m: st.session_state.marked.remove(st.session_state.idx)
            else: st.session_state.marked.add(st.session_state.idx)
            st.rerun()

        # DÜZEN
        if passage:
            # OKUMA MODU (50% - 50%)
            col_l, col_r = st.columns([1, 1], gap="small")
            
            with col_l:
                # Başlıkları kaldırıp direkt içeriği verdim
                st.markdown(f"<div class='passage-box'>{passage}</div>", unsafe_allow_html=True)
            
            with col_r:
                st.markdown(f"<div class='question-stem'><b>Soru {st.session_state.idx+1}:</b> {stem}</div>", unsafe_allow_html=True)
                
                # Şık Hazırlığı
                opts, opt_map = [], {}
                for char in ['A','B','C','D','E']:
                    if pd.notna(row[char]):
                        full = f"{char}) {row[char]}"
                        opts.append(full)
                        opt_map[full] = char
                
                # Cevap Seçimi
                curr = st.session_state.answers.get(st.session_state.idx)
                idx_sel = None
                if curr:
                    for k,v in enumerate(opts):
                        if v.startswith(curr+")"): idx_sel = k; break
                
                sel = st.radio("Cv", opts, index=idx_sel, key=f"r{st.session_state.idx}", label_visibility="collapsed")
                
                # Kontrol
                if sel:
                    sel_char = opt_map[sel]
                    st.session_state.answers[st.session_state.idx] = sel_char
                    true_char = row['Dogru_Cevap']
                    
                    if sel_char == true_char:
                        st.success("✅ Doğru")
                    else:
                        st.error(f"❌ Yanlış (Cevap: {true_char})")

        else:
            # NORMAL MOD (Tek Sütun ama Dar)
            # Ekranın tamamını kaplamasın diye ortalıyoruz
            c_spacer_l, c_mid, c_spacer_r = st.columns([1, 6, 1])
            with c_mid:
                st.markdown(f"<div class='question-stem'><b>Soru {st.session_state.idx+1}:</b> {stem}</div>", unsafe_allow_html=True)
                
                opts, opt_map = [], {}
                for char in ['A','B','C','D','E']:
                    if pd.notna(row[char]):
                        full = f"{char}) {row[char]}"
                        opts.append(full)
                        opt_map[full] = char
                
                curr = st.session_state.answers.get(st.session_state.idx)
                idx_sel = None
                if curr:
                    for k,v in enumerate(opts):
                        if v.startswith(curr+")"): idx_sel = k; break
                
                sel = st.radio("Cv", opts, index=idx_sel, key=f"r{st.session_state.idx}", label_visibility="collapsed")
                
                if sel:
                    sel_char = opt_map[sel]
                    st.session_state.answers[st.session_state.idx] = sel_char
                    true_char = row['Dogru_Cevap']
                    if sel_char == true_char:
                        st.success("✅ Doğru")
                    else:
                        st.error(f"❌ Yanlış (Cevap: {true_char})")

        # ALT NAVİGASYON (Yan yana küçük butonlar)
        st.markdown("<br>", unsafe_allow_html=True)
        bc1, bc2 = st.columns([1, 1])
        if st.session_state.idx > 0:
            bc1.button("⬅️ Geri", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx-1), use_container_width=True)
        
        if st.session_state.idx < len(df) - 1:
            # Mavi buton stili
            st.markdown("""<style>div[data-testid="column"]:nth-of-type(2) button {background-color:#0984e3;color:white;}</style>""", unsafe_allow_html=True)
            bc2.button("İleri ➡️", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx+1), use_container_width=True)

    else:
        # SONUÇ EKRANI
        st.title("Sonuçlar")
        res_data = []
        c, w, e = 0, 0, 0
        for i in range(len(df)):
            ua = st.session_state.answers.get(i)
            ca = df.iloc[i]['Dogru_Cevap']
            if ua:
                if ua == ca: c+=1; s="D"
                else: w+=1; s="Y"
            else: e+=1; s="B"
            res_data.append({"No": i+1, "Cevap": ua, "Doğru": ca, "D": s})
            
        k1, k2, k3 = st.columns(3)
        k1.metric("Doğru", c); k2.metric("Yanlış", w); k3.metric("Boş", e)
        st.dataframe(pd.DataFrame(res_data))
        if st.button("Başa Dön"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
else:
    st.error("Dosya yok.")
import streamlit as st
import pandas as pd

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="YDS Pro Master", page_icon="🎓", layout="wide")

# --- 2. PROFESYONEL CSS & TİPOGRAFİ (GÜNCELLENDİ) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        background-color: #f8f9fa;
        color: #212529;
    }
    
    /* Okuma Parçası Kutusu (Sol Taraf) */
    .passage-box {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 12px;
        border-left: 5px solid #0d6efd; /* Profesyonel Mavi */
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        font-size: 18px;
        line-height: 1.7; 
        color: #343a40;
        margin-bottom: 20px;
        
        /* Tipografi Düzeltmeleri */
        text-align: justify; /* İki yana yasla */
        text-justify: inter-word; /* Kelime aralarını değil, kelimeleri dengele */
        hyphens: auto; /* Sığmayan kelimeleri tirele (Türkçe/İngilizce uyumlu) */
        -webkit-hyphens: auto;
        -moz-hyphens: auto;
        word-break: break-word; /* Uzun kelimeleri gerekirse kır */
    }
    
    /* Soru Kökü (Sağ Taraf) */
    .question-stem {
        font-size: 19px;
        font-weight: 700;
        color: #000000;
        background-color: #e9ecef;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 25px;
        line-height: 1.5;
        border: 1px solid #dee2e6;
    }
    
    /* Şık Butonları */
    .stButton>button {
        background-color: white;
        border: 1px solid #ced4da;
        border-radius: 8px;
        padding: 12px 20px;
        font-size: 16px;
        text-align: left !important;
        width: 100%;
        color: #495057;
        margin-bottom: 8px;
        transition: all 0.2s;
        display: flex;
        align-items: center; /* Şık harfi ile metni hizala */
    }
    
    .stButton>button:hover {
        border-color: #0d6efd;
        color: #0d6efd;
        background-color: #f1f8ff;
    }

    /* Üst Bilgi Barı */
    .status-bar {
        font-size: 14px;
        font-weight: 600;
        color: #6c757d;
        margin-bottom: 15px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. VERİ YÜKLEME ---
@st.cache_data
def load_data():
    try:
        return pd.read_excel("sorular.xlsx", engine="openpyxl")
    except:
        return None

df = load_data()

# --- 4. PARSER (METİN AYRIŞTIRICI) ---
def parse_question(text):
    if pd.isna(text): return None, "Soru yok."
    text = str(text).replace('\\n', '\n')
    if '\n\n' in text:
        parts = text.split('\n\n', 1)
        return parts[0].strip(), parts[1].strip()
    return None, text.strip()

# --- 5. ANA UYGULAMA ---
if df is not None:
    if 'idx' not in st.session_state: st.session_state.idx = 0
    if 'score' not in st.session_state: st.session_state.score = {"T": 0, "F": 0}
    if 'ans_status' not in st.session_state: st.session_state.ans_status = None

    # Sidebar
    with st.sidebar:
        st.header("🎛️ Kontrol Paneli")
        col1, col2 = st.columns(2)
        col1.metric("✅ Doğru", st.session_state.score["T"])
        col2.metric("❌ Yanlış", st.session_state.score["F"])
        st.divider()
        
        # Soru Seçici
        new_idx = st.selectbox(
            "Soruya Git:", 
            range(1, len(df)+1), 
            index=st.session_state.idx
        ) - 1
        
        if new_idx != st.session_state.idx:
            st.session_state.idx = new_idx
            st.session_state.ans_status = None
            st.rerun()

        st.divider()
        if st.button("Sıfırla"):
            st.session_state.score = {"T": 0, "F": 0}
            st.session_state.idx = 0
            st.session_state.ans_status = None
            st.rerun()

    # Ana İçerik
    row = df.iloc[st.session_state.idx]
    passage, stem = parse_question(row['Soru'])
    
    st.progress((st.session_state.idx + 1) / len(df))
    st.markdown(f"<div class='status-bar'>Soru {st.session_state.idx + 1} / {len(df)}</div>", unsafe_allow_html=True)

    # Düzen (Layout)
    if passage:
        # Geniş ekranlarda 2 kolon, mobilde alt alta
        col_text, col_q = st.columns([1.1, 1], gap="large")
        
        with col_text:
            st.markdown(f"""<div class="passage-box">{passage}</div>""", unsafe_allow_html=True)
            
        with col_q:
            st.markdown(f"""<div class="question-stem">{stem}</div>""", unsafe_allow_html=True)
            
            # Şıklar
            for s in ['A', 'B', 'C', 'D', 'E']:
                if pd.notna(row[s]):
                    if st.button(f"{s}) {row[s]}", key=f"q{st.session_state.idx}_{s}"):
                        correct = str(row['Dogru_Cevap']).strip().upper()
                        if s == correct:
                            st.session_state.ans_status = ("success", f"✅ DOĞRU! (Cevap: {correct})")
                            st.session_state.score["T"] += 1
                        else:
                            st.session_state.ans_status = ("error", f"❌ YANLIŞ. Doğru Cevap: {correct}")
                            st.session_state.score["F"] += 1
                            
            if st.session_state.ans_status:
                typ, msg = st.session_state.ans_status
                if typ == "success": st.success(msg)
                else: st.error(msg)

            # Navigasyon Butonları
            c_prev, c_next = st.columns([1, 1])
            with c_prev:
                if st.session_state.idx > 0:
                    if st.button("⬅️ Önceki", use_container_width=True):
                        st.session_state.idx -= 1
                        st.session_state.ans_status = None
                        st.rerun()
            with c_next:
                if st.session_state.idx < len(df) - 1:
                    if st.button("Sonraki ➡️", type="primary", use_container_width=True):
                        st.session_state.idx += 1
                        st.session_state.ans_status = None
                        st.rerun()

    else:
        # Paragrafsız Sorular (Ortalı Görünüm)
        c_spacer_l, c_center, c_spacer_r = st.columns([1, 2, 1])
        with c_center:
            st.markdown(f"""<div class="question-stem">{stem}</div>""", unsafe_allow_html=True)
            
            for s in ['A', 'B', 'C', 'D', 'E']:
                if pd.notna(row[s]):
                    if st.button(f"{s}) {row[s]}", key=f"q{st.session_state.idx}_{s}"):
                        correct = str(row['Dogru_Cevap']).strip().upper()
                        if s == correct:
                            st.session_state.ans_status = ("success", f"✅ DOĞRU! (Cevap: {correct})")
                            st.session_state.score["T"] += 1
                        else:
                            st.session_state.ans_status = ("error", f"❌ YANLIŞ. Doğru Cevap: {correct}")
                            st.session_state.score["F"] += 1

            if st.session_state.ans_status:
                typ, msg = st.session_state.ans_status
                if typ == "success": st.success(msg)
                else: st.error(msg)

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.session_state.idx > 0:
                    if st.button("⬅️ Geri", use_container_width=True):
                        st.session_state.idx -= 1
                        st.session_state.ans_status = None
                        st.rerun()
            with col_b2:
                if st.session_state.idx < len(df) - 1:
                    if st.button("İleri ➡️", type="primary", use_container_width=True):
                        st.session_state.idx += 1
                        st.session_state.ans_status = None
                        st.rerun()

else:
    st.error("Veri dosyası yüklenemedi.")
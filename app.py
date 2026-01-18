import streamlit as st
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="YDS Exam Portal", page_icon="🎓", layout="wide")

# --- PROFESYONEL CSS (UI/UX) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Roboto', sans-serif;
    }
    
    /* Soru Kartı */
    .question-box {
        background-color: #f8f9fa;
        padding: 30px;
        border-radius: 15px;
        border-left: 8px solid #007bff;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 25px;
        text-align: justify; /* İki yana yaslama */
        font-size: 20px;
        line-height: 1.6;
        color: #1a1a1a;
    }
    
    /* Şık Butonları */
    .stButton>button {
        background-color: white;
        color: #333;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px 25px;
        font-size: 17px;
        text-align: left !important;
        transition: all 0.3s ease;
        margin-bottom: 10px;
        display: block;
        width: 100%;
    }
    
    .stButton>button:hover {
        border-color: #007bff;
        color: #007bff;
        background-color: #f0f7ff;
        box-shadow: 0 4px 12px rgba(0,123,255,0.2);
        transform: translateY(-2px);
    }

    /* Sidebar Düzeni */
    .css-1d391kg {
        background-color: #f1f3f4;
    }
</style>
""", unsafe_allow_html=True)

# --- VERİ YÜKLEME ---
@st.cache_data
def load_data():
    try:
        return pd.read_excel("sorular.xlsx", engine="openpyxl")
    except:
        return None

df = load_data()

if df is not None:
    # --- SESSION STATE ---
    if 'idx' not in st.session_state: st.session_state.idx = 0
    if 'score' not in st.session_state: st.session_state.score = {"T": 0, "F": 0}
    if 'ans_status' not in st.session_state: st.session_state.ans_status = None

    # --- SIDEBAR NAVİGASYON ---
    with st.sidebar:
        st.markdown("### 📊 SINAV DURUMU")
        col_s1, col_s2 = st.columns(2)
        col_s1.metric("Doğru", st.session_state.score["T"])
        col_s2.metric("Yanlış", st.session_state.score["F"])
        
        st.divider()
        st.markdown("### 🎯 SORU NAVİGASYONU")
        q_selection = st.selectbox("Soruya Atla:", range(1, len(df)+1), index=st.session_state.idx)
        if q_selection - 1 != st.session_state.idx:
            st.session_state.idx = q_selection - 1
            st.session_state.ans_status = None
            st.rerun()
            
        if st.button("🔄 Sınavı Sıfırla"):
            st.session_state.idx = 0
            st.session_state.score = {"T": 0, "F": 0}
            st.rerun()

    # --- ANA PANEL ---
    row = df.iloc[st.session_state.idx]
    
    # Üst Bilgi
    st.markdown(f"<p style='color:gray; font-weight:bold;'>YDS Sınav Sistemi / Soru {st.session_state.idx + 1}</p>", unsafe_allow_html=True)
    st.progress((st.session_state.idx + 1) / len(df))

    # Soru Kutusu (İki yana yaslanmış)
    st.markdown(f"""<div class="question-box">{row['Soru']}</div>""", unsafe_allow_html=True)

    # Şıklar
    siklar = ['A', 'B', 'C', 'D', 'E']
    for s in siklar:
        if pd.notna(row[s]):
            if st.button(f"{s}) {row[s]}", key=f"btn_{st.session_state.idx}_{s}"):
                correct = str(row['Dogru_Cevap']).strip().upper()
                if s == correct:
                    st.session_state.ans_status = ("success", f"TEBRİKLER! Doğru Cevap: {correct}")
                    st.session_state.score["T"] += 1
                else:
                    st.session_state.ans_status = ("error", f"ÜZGÜNÜM! Yanlış. Doğru Cevap: {correct}")
                    st.session_state.score["F"] += 1

    # Bildirim Alanı
    if st.session_state.ans_status:
        type, msg = st.session_state.ans_status
        if type == "success": st.success(msg)
        else: st.error(msg)

    st.divider()

    # Alt Navigasyon
    n_col1, n_col2, n_col3 = st.columns([1, 4, 1])
    with n_col1:
        if st.session_state.idx > 0:
            if st.button("⬅️ Önceki"):
                st.session_state.idx -= 1
                st.session_state.ans_status = None
                st.rerun()
    with n_col3:
        if st.session_state.idx < len(df) - 1:
            if st.button("Sonraki ➡️"):
                st.session_state.idx += 1
                st.session_state.ans_status = None
                st.rerun()

else:
    st.error("Excel dosyası yüklenemedi. Lütfen 'sorular.xlsx' dosyasını kontrol edin.")
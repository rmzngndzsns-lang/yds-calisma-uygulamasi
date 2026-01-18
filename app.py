import streamlit as st
import pandas as pd

# --- 1. SAYFA AYARLARI (GENİŞ MOD) ---
st.set_page_config(page_title="YDS Pro Master", page_icon="🎓", layout="wide")

# --- 2. PROFESYONEL CSS & TİPOGRAFİ ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
        background-color: #f4f6f9; /* Göz yormayan hafif gri zemin */
    }
    
    /* Okuma Parçası Kutusu (Sol Taraf) */
    .passage-box {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 12px;
        border-left: 6px solid #2c3e50; /* Koyu Lacivert Vurgu */
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        font-size: 18px;
        line-height: 1.8; /* Satır aralığını açtık, okuma kolaylaşsın */
        color: #2c3e50;
        margin-bottom: 20px;
        text-align: justify;
    }
    
    /* Soru Kökü (Sağ Taraf - Vurgulu) */
    .question-stem {
        font-size: 20px;
        font-weight: 700;
        color: #000000;
        background-color: #e9ecef;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        line-height: 1.5;
    }
    
    /* Şık Butonları (Kart Tasarımı) */
    .stButton>button {
        background-color: white;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 16px 20px;
        font-size: 17px;
        text-align: left !important;
        width: 100%;
        color: #4b5563;
        transition: all 0.2s ease-in-out;
        margin-bottom: 8px;
    }
    
    /* Hover (Üzerine gelince) Efekti */
    .stButton>button:hover {
        border-color: #3b82f6;
        color: #1d4ed8;
        background-color: #eff6ff;
        transform: translateX(5px); /* Hafif sağa kayma hissi */
    }

    /* Üst Bilgi Barı */
    .status-bar {
        font-size: 14px;
        font-weight: 600;
        color: #6b7280;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
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

# --- 4. AKILLI METİN AYRIŞTIRICI (PARSER) ---
def parse_question(text):
    """
    Metni '\n\n' işaretine göre böler.
    Eğer işaret varsa: [Paragraf, Soru Kökü] döner.
    Yoksa: [None, Soru Kökü] döner.
    """
    if pd.isna(text):
        return None, "Soru metni bulunamadı."
        
    text = str(text)
    # Excel'deki \n karakterlerini düzeltelim
    text = text.replace('\\n', '\n')
    
    if '\n\n' in text:
        parts = text.split('\n\n', 1) # Sadece ilk bölücüden ayır
        passage = parts[0].strip()
        question_stem = parts[1].strip()
        return passage, question_stem
    else:
        return None, text.strip()

# --- 5. ANA UYGULAMA MANTIĞI ---
if df is not None:
    # State Tanımları
    if 'idx' not in st.session_state: st.session_state.idx = 0
    if 'score' not in st.session_state: st.session_state.score = {"T": 0, "F": 0}
    if 'ans_status' not in st.session_state: st.session_state.ans_status = None

    # --- SIDEBAR (KONTROL PANELİ) ---
    with st.sidebar:
        st.title("🚀 YDS Pro Panel")
        
        # Skor Kartı
        col1, col2 = st.columns(2)
        col1.metric("Doğru", st.session_state.score["T"])
        col2.metric("Yanlış", st.session_state.score["F"])
        
        st.markdown("---")
        
        # Soru Gezgini
        selected_q = st.selectbox(
            "Soruya Git:", 
            options=range(1, len(df)+1), 
            index=st.session_state.idx,
            format_func=lambda x: f"Soru {x}"
        )
        
        if selected_q - 1 != st.session_state.idx:
            st.session_state.idx = selected_q - 1
            st.session_state.ans_status = None
            st.rerun()
            
        st.markdown("---")
        if st.button("🔄 Sıfırla", type="secondary"):
            st.session_state.score = {"T": 0, "F": 0}
            st.session_state.idx = 0
            st.session_state.ans_status = None
            st.rerun()

    # --- ANA EKRAN DÜZENİ ---
    row = df.iloc[st.session_state.idx]
    passage, question_stem = parse_question(row['Soru'])
    
    # İlerleme Çubuğu ve Başlık
    progress = (st.session_state.idx + 1) / len(df)
    st.progress(progress)
    st.markdown(f"<div class='status-bar'>Question {st.session_state.idx + 1} of {len(df)}</div>", unsafe_allow_html=True)

    # --- DİNAMİK LAYOUT (TEK SÜTUN MU ÇİFT SÜTUN MU?) ---
    
    # Eğer uzun bir paragraf varsa ekranı ikiye böl (2 Kolon)
    if passage:
        col_left, col_right = st.columns([1.2, 1]) # Sol taraf biraz daha geniş okuma için
        
        with col_left:
            st.markdown(f"""
            <div class="passage-box">
                {passage}
            </div>
            """, unsafe_allow_html=True)
            
        with col_right:
            # Soru Kökü (Bold)
            st.markdown(f"""<div class="question-stem">{question_stem}</div>""", unsafe_allow_html=True)
            
            # Şıklar
            siklar = ['A', 'B', 'C', 'D', 'E']
            for s in siklar:
                if pd.notna(row[s]):
                    btn_label = f"**{s})** {row[s]}"
                    if st.button(btn_label, key=f"btn_{st.session_state.idx}_{s}"):
                        correct = str(row['Dogru_Cevap']).strip().upper()
                        if s == correct:
                            st.session_state.ans_status = ("success", f"✅ DOĞRU! Cevap: {correct}")
                            st.session_state.score["T"] += 1
                        else:
                            st.session_state.ans_status = ("error", f"❌ YANLIŞ. Doğru Cevap: {correct}")
                            st.session_state.score["F"] += 1
            
            # Cevap Bildirimi (Sağ kolonda şıkların altında çıksın)
            if st.session_state.ans_status:
                type_, msg = st.session_state.ans_status
                if type_ == "success": st.success(msg)
                else: st.error(msg)
                
            # İleri/Geri Butonları (Sağ tarafta el altında olsun)
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.session_state.idx > 0:
                    if st.button("⬅️ Önceki", use_container_width=True):
                        st.session_state.idx -= 1
                        st.session_state.ans_status = None
                        st.rerun()
            with c2:
                if st.session_state.idx < len(df) - 1:
                    if st.button("Sonraki ➡️", type="primary", use_container_width=True):
                        st.session_state.idx += 1
                        st.session_state.ans_status = None
                        st.rerun()

    # Eğer paragraf yoksa (Kısa soruysa) Ortalanmış Tek Kolon
    else:
        # Ortada daha dar bir alan kullanarak odağı topla
        c_spacer1, c_main, c_spacer2 = st.columns([1, 2, 1])
        
        with c_main:
            st.markdown(f"""<div class="question-stem" style="text-align:center;">{question_stem}</div>""", unsafe_allow_html=True)
            
            siklar = ['A', 'B', 'C', 'D', 'E']
            for s in siklar:
                if pd.notna(row[s]):
                    if st.button(f"{s}) {row[s]}", key=f"btn_{st.session_state.idx}_{s}"):
                        correct = str(row['Dogru_Cevap']).strip().upper()
                        if s == correct:
                            st.session_state.ans_status = ("success", f"✅ DOĞRU! Cevap: {correct}")
                            st.session_state.score["T"] += 1
                        else:
                            st.session_state.ans_status = ("error", f"❌ YANLIŞ. Doğru Cevap: {correct}")
                            st.session_state.score["F"] += 1
            
            if st.session_state.ans_status:
                type_, msg = st.session_state.ans_status
                if type_ == "success": st.success(msg)
                else: st.error(msg)
                
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.session_state.idx > 0:
                    if st.button("⬅️ Önceki", use_container_width=True):
                        st.session_state.idx -= 1
                        st.session_state.ans_status = None
                        st.rerun()
            with col_b2:
                if st.session_state.idx < len(df) - 1:
                    if st.button("Sonraki ➡️", type="primary", use_container_width=True):
                        st.session_state.idx += 1
                        st.session_state.ans_status = None
                        st.rerun()

else:
    st.error("Veri dosyası (sorular.xlsx) bulunamadı.")
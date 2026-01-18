import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta

# --- 1. SAYFA YAPILANDIRMASI (OSYM STİLİ) ---
st.set_page_config(page_title="ÖSYM E-Sınav Sistemi", page_icon="📝", layout="wide")

# --- 2. PROFESYONEL CSS (ÖSYM ARAYÜZÜ) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    
    body {
        font-family: 'Roboto', sans-serif;
        background-color: #f0f2f5;
    }
    
    /* Üst Bar (Header) */
    .header-bar {
        background-color: #2c3e50;
        color: white;
        padding: 15px;
        border-radius: 8px;
        display: flex;
        justify_content: space-between;
        align-items: center;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    /* Sayaç Kutusu */
    .timer-box {
        font-size: 24px;
        font-weight: bold;
        color: #e74c3c;
        background-color: #fff;
        padding: 5px 15px;
        border-radius: 5px;
        border: 2px solid #e74c3c;
    }

    /* Sol Taraf: Soru Paleti */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        padding: 10px;
    }
    .grid-btn {
        width: 100%;
        padding: 8px 0;
        text-align: center;
        font-size: 12px;
        font-weight: bold;
        border: 1px solid #ccc;
        border-radius: 4px;
        cursor: pointer;
        background-color: white;
        color: #333;
        transition: all 0.2s;
    }
    /* Durum Renkleri */
    .grid-btn.active { border: 2px solid #2c3e50; font-weight: 900; transform: scale(1.1); }
    .grid-btn.answered { background-color: #3498db; color: white; border-color: #2980b9; }
    .grid-btn.marked { background-color: #f39c12; color: white; border-color: #d35400; }
    
    /* Okuma Parçası (Scrollable) */
    .passage-container {
        background-color: white;
        border: 1px solid #ddd;
        border-left: 5px solid #2c3e50;
        padding: 20px;
        border-radius: 8px;
        height: 600px; /* Sabit yükseklik */
        overflow-y: auto; /* Scroll */
        font-size: 16px;
        line-height: 1.8;
        text-align: justify;
    }
    
    /* Soru Alanı */
    .question-container {
        background-color: white;
        border: 1px solid #ddd;
        padding: 20px;
        border-radius: 8px;
        min-height: 600px;
    }
    .question-stem {
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 20px;
        padding: 15px;
        background-color: #ecf0f1;
        border-radius: 5px;
        color: #2c3e50;
    }
    
    /* Şık Butonları */
    .stButton > button {
        width: 100%;
        text-align: left;
        padding: 15px;
        border: 1px solid #bdc3c7;
        background-color: #fff;
        border-radius: 6px;
        margin-bottom: 8px;
        font-size: 16px;
        transition: 0.2s;
    }
    .stButton > button:hover {
        background-color: #eaf2f8;
        border-color: #3498db;
        color: #2980b9;
    }
    
</style>
""", unsafe_allow_html=True)

# --- 3. VERİ VE DURUM YÖNETİMİ ---
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("sorular.xlsx", engine="openpyxl")
        return df
    except:
        return None

def init_session():
    if 'idx' not in st.session_state: st.session_state.idx = 0
    if 'answers' not in st.session_state: st.session_state.answers = {} # {0: 'A', 1: 'C'}
    if 'marked' not in st.session_state: st.session_state.marked = set() # {3, 15} (İşaretli sorular)
    if 'start_time' not in st.session_state: st.session_state.start_time = datetime.now()
    if 'exam_finished' not in st.session_state: st.session_state.exam_finished = False

df = load_data()
init_session()

# --- 4. ZAMANLAYICI MANTIĞI ---
def get_timer():
    now = datetime.now()
    elapsed = now - st.session_state.start_time
    total_duration = timedelta(minutes=180)
    remaining = total_duration - elapsed
    
    if remaining.total_seconds() <= 0:
        st.session_state.exam_finished = True
        return "00:00:00"
    
    # Formatlama HH:MM:SS
    seconds = int(remaining.total_seconds())
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# --- 5. PARSER ---
def parse_question(text):
    if pd.isna(text): return None, "Soru yüklenemedi."
    text = str(text).replace('\\n', '\n')
    if '\n\n' in text:
        parts = text.split('\n\n', 1)
        return parts[0].strip(), parts[1].strip()
    return None, text.strip()

# --- 6. UYGULAMA GÖVDESİ ---
if df is not None and not st.session_state.exam_finished:
    
    # --- ÜST BAR (HEADER) ---
    timer_str = get_timer()
    c1, c2, c3 = st.columns([2, 6, 2])
    with c1:
        st.markdown(f"**2021-YDS/1 İngilizce**")
    with c3:
        st.markdown(f"<div class='timer-box'>⏳ {timer_str}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- YAN PANEL (SORU PALETİ) ---
    with st.sidebar:
        st.header("Soru Gezgini")
        st.write("⚪ Boş | 🔵 Cevaplı | 🟠 İşaretli")
        
        # Grid Oluşturma
        cols = st.columns(5)
        for i in range(len(df)):
            # Durum Belirleme
            style_class = "grid-btn"
            if i == st.session_state.idx: style_class += " active"
            elif i in st.session_state.marked: style_class += " marked"
            elif i in st.session_state.answers: style_class += " answered"
            
            # Buton Rengi (CSS ile)
            color_map = {
                "active": "border: 2px solid black; font-weight:bold;",
                "marked": "background-color: #f39c12; color: white;",
                "answered": "background-color: #3498db; color: white;",
                "default": "background-color: white;"
            }
            
            # Basit Streamlit butonu ile navigasyon
            # Not: Streamlit butonlarına CSS class atamak zordur, o yüzden görsel hile yapıyoruz
            label = f"{i+1}"
            if i in st.session_state.marked: label += " 🚩"
            
            # Soruya Git Butonu
            if cols[i % 5].button(label, key=f"nav_{i}", use_container_width=True):
                st.session_state.idx = i
                st.rerun()

        st.divider()
        if st.button("🏁 Sınavı Bitir", type="primary"):
            st.session_state.exam_finished = True
            st.rerun()

    # --- ANA SORU EKRANI ---
    row = df.iloc[st.session_state.idx]
    passage, stem = parse_question(row['Soru'])
    
    # Araç Çubuğu (Tool Bar)
    t_col1, t_col2, t_col3 = st.columns([1, 4, 1])
    with t_col1:
        # İşaretle Butonu (Toggle)
        is_marked = st.session_state.idx in st.session_state.marked
        btn_label = "🚩 İşaretle" if not is_marked else "🏳️ İşareti Kaldır"
        if st.button(btn_label):
            if is_marked: st.session_state.marked.remove(st.session_state.idx)
            else: st.session_state.marked.add(st.session_state.idx)
            st.rerun()

    # Düzen (Split View)
    if passage:
        col_left, col_right = st.columns([1, 1], gap="medium")
        
        with col_left:
            st.markdown("### 📖 Okuma Parçası")
            st.markdown(f"<div class='passage-container'>{passage}</div>", unsafe_allow_html=True)
            
        with col_right:
            st.markdown(f"### Soru {st.session_state.idx + 1}")
            st.markdown(f"<div class='question-container'><div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
            
            # Şıklar
            for s in ['A', 'B', 'C', 'D', 'E']:
                if pd.notna(row[s]):
                    # Eğer daha önce cevap verdiyse onu göster
                    user_ans = st.session_state.answers.get(st.session_state.idx)
                    
                    if st.button(f"{s}) {row[s]}", key=f"q_{st.session_state.idx}_{s}"):
                        st.session_state.answers[st.session_state.idx] = s
                        st.rerun()
            
            # Seçili Cevabı Göster
            if st.session_state.idx in st.session_state.answers:
                st.info(f"✅ Seçtiğiniz Cevap: **{st.session_state.answers[st.session_state.idx]}**")
            
            st.markdown("</div>", unsafe_allow_html=True) # Kapatma div'i

    else:
        # Tek Sütun (Paragrafsız)
        st.markdown(f"### Soru {st.session_state.idx + 1}")
        st.markdown(f"<div class='question-container'><div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
        
        for s in ['A', 'B', 'C', 'D', 'E']:
            if pd.notna(row[s]):
                if st.button(f"{s}) {row[s]}", key=f"q_{st.session_state.idx}_{s}"):
                    st.session_state.answers[st.session_state.idx] = s
                    st.rerun()
        
        if st.session_state.idx in st.session_state.answers:
            st.info(f"✅ Seçtiğiniz Cevap: **{st.session_state.answers[st.session_state.idx]}**")
        
        st.markdown("</div>", unsafe_allow_html=True)

    # --- ALT NAVİGASYON ---
    st.markdown("---")
    b_col1, b_col2 = st.columns([1, 1])
    with b_col1:
        if st.session_state.idx > 0:
            if st.button("⬅️ Önceki Soru", use_container_width=True):
                st.session_state.idx -= 1
                st.rerun()
    with b_col2:
        if st.session_state.idx < len(df) - 1:
            if st.button("Sonraki Soru ➡️", type="primary", use_container_width=True):
                st.session_state.idx += 1
                st.rerun()

# --- SINAV SONUÇ EKRANI ---
elif st.session_state.exam_finished:
    st.title("🏁 Sınav Tamamlandı!")
    
    score_t = 0
    score_f = 0
    empty = 0
    
    results = []
    
    for i in range(len(df)):
        user_choice = st.session_state.answers.get(i)
        correct_choice = str(df.iloc[i]['Dogru_Cevap']).strip().upper()
        
        if user_choice:
            if user_choice == correct_choice:
                score_t += 1
                status = "✅ Doğru"
            else:
                score_f += 1
                status = f"❌ Yanlış (Cevap: {correct_choice})"
        else:
            empty += 1
            status = f"⚪ Boş (Cevap: {correct_choice})"
            
        results.append({"Soru": i+1, "Cevabın": user_choice, "Durum": status})
    
    # Özet Kartları
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Toplam Soru", len(df))
    k2.metric("Doğru", score_t)
    k3.metric("Yanlış", score_f)
    k4.metric("Boş", empty)
    
    st.divider()
    st.markdown("### 📊 Detaylı Analiz")
    st.dataframe(pd.DataFrame(results))
    
    if st.button("🔄 Sınavı Yeniden Başlat"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

else:
    st.error("Dosya yüklenemedi.")
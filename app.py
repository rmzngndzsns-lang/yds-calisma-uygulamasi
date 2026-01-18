import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="ÖSYM E-Sınav", page_icon="📝", layout="wide")

# --- 2. PROFESYONEL CSS & JS ---
st.markdown("""
<style>
    /* Genel Font ve Arkaplan */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    
    .stApp {
        background-color: #f4f6f9;
        font-family: 'Roboto', sans-serif;
    }

    /* Sayaç Kutusu (Header Sağ) */
    .timer-container {
        font-size: 26px;
        font-weight: 800;
        color: #d63031;
        background-color: white;
        padding: 10px 25px;
        border-radius: 8px;
        border: 2px solid #d63031;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }

    /* Sol Okuma Parçası (Sabit Yükseklik + Scroll) */
    .passage-box {
        background-color: white;
        padding: 25px;
        border-radius: 10px;
        border-left: 6px solid #2d3436;
        height: 65vh; /* Ekranın %65'i kadar yükseklik */
        overflow-y: auto; /* İçinde kaydırma çubuğu çıksın */
        font-size: 17px;
        line-height: 1.8;
        text-align: justify;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        color: #2d3436;
    }

    /* Sağ Soru Alanı */
    .question-box {
        background-color: white;
        padding: 25px;
        border-radius: 10px;
        border: 1px solid #dfe6e9;
        min-height: 65vh;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }

    .question-stem {
        font-size: 18px;
        font-weight: 700;
        background-color: #f1f2f6;
        padding: 15px;
        border-radius: 8px;
        color: #2c3e50;
        margin-bottom: 20px;
        line-height: 1.5;
    }

    /* Radyo Butonlarını Özelleştirme (Şıklar) */
    .stRadio > label {
        font-weight: bold;
        font-size: 16px;
    }
    .stRadio div[role='radiogroup'] > label {
        background-color: #ffffff;
        padding: 12px 20px;
        border-radius: 8px;
        border: 1px solid #b2bec3;
        margin-bottom: 8px;
        width: 100%;
        display: flex;
        cursor: pointer;
        transition: all 0.2s;
    }
    .stRadio div[role='radiogroup'] > label:hover {
        border-color: #0984e3;
        background-color: #f0f9ff;
    }
    
    /* Navigasyon Butonları (Önceki/Sonraki) */
    div.stButton > button {
        width: 100%;
        font-weight: bold;
        border-radius: 8px;
        height: 50px;
        font-size: 16px;
    }
    
    /* İleri Butonu Özel Renk */
    div[data-testid="column"] button:contains("Sonraki") {
        background-color: #0984e3 !important;
        color: white !important;
    }
</style>

<script>
// JavaScript Canlı Sayaç
function startTimer(duration, display) {
    var timer = duration, minutes, seconds;
    setInterval(function () {
        hours = parseInt(timer / 3600, 10);
        minutes = parseInt((timer % 3600) / 60, 10);
        seconds = parseInt(timer % 60, 10);

        hours = hours < 10 ? "0" + hours : hours;
        minutes = minutes < 10 ? "0" + minutes : minutes;
        seconds = seconds < 10 ? "0" + seconds : seconds;

        display.textContent = hours + ":" + minutes + ":" + seconds;

        if (--timer < 0) {
            timer = 0;
            // Süre bitince uyarı verebiliriz
        }
    }, 1000);
}

window.onload = function () {
    // Python'dan gelen kalan saniyeyi al (Streamlit iframe içinde çalıştığı için trick gerekir)
    // Şimdilik basitçe JS tarafında başlatıyoruz, sayfa yenilenince süre sunucudan güncellenir.
};
</script>
""", unsafe_allow_html=True)

# --- 3. VERİ YÖNETİMİ ---
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("sorular.xlsx", engine="openpyxl")
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

# --- 4. PARSER ---
def parse_question(text):
    if pd.isna(text): return None, "Soru yüklenemedi."
    text = str(text).replace('\\n', '\n')
    if '\n\n' in text:
        parts = text.split('\n\n', 1)
        return parts[0].strip(), parts[1].strip()
    return None, text.strip()

# --- 5. UYGULAMA MANTIĞI ---
if df is not None:
    
    # --- HEADER (ZAMANLAYICI) ---
    # Kalan saniyeyi hesapla
    now = datetime.now()
    elapsed = (now - st.session_state.start_time).total_seconds()
    total_seconds = 180 * 60
    remaining_seconds = max(0, int(total_seconds - elapsed))
    
    # Kalan süreyi HH:MM:SS formatına çevir
    m, s = divmod(remaining_seconds, 60)
    h, m = divmod(m, 60)
    time_str = f"{h:02d}:{m:02d}:{s:02d}"

    # Header Dizilimi
    c_head_1, c_head_2, c_head_3 = st.columns([2, 6, 2])
    with c_head_1:
        st.markdown(f"### 🇹🇷 YDS 2021/1")
    with c_head_3:
        # Bu kısım JS ile de güncellenebilir ama Streamlit'te native olarak her işlemde yenilenir
        # Canlı akış için HTML/JS inject ediyoruz:
        st.markdown(
            f"""
            <div class="timer-container" id="safeTimerDisplay">{time_str}</div>
            <script>
            // Basit JS Sayacı (Görsel Akıcılık İçin)
            var timeleft = {remaining_seconds};
            var downloadTimer = setInterval(function(){{
              if(timeleft <= 0){{
                clearInterval(downloadTimer);
                document.getElementById("safeTimerDisplay").innerHTML = "00:00:00";
              }} else {{
                var h = Math.floor(timeleft / 3600);
                var m = Math.floor((timeleft % 3600) / 60);
                var s = Math.floor(timeleft % 60);
                document.getElementById("safeTimerDisplay").innerHTML = 
                    (h<10?"0":"")+h + ":" + (m<10?"0":"")+m + ":" + (s<10?"0":"")+s;
              }}
              timeleft -= 1;
            }}, 1000);
            </script>
            """, 
            unsafe_allow_html=True
        )

    st.markdown("---")

    # --- YAN MENÜ (SORU PALETİ) ---
    with st.sidebar:
        st.header("Soru Paleti")
        st.caption("🔵: Cevaplı | ⚪: Boş | 🟠: İşaretli")
        
        # Grid Sistemi (5 kolonlu)
        col_list = st.columns(5)
        for i in range(len(df)):
            label = str(i+1)
            
            # Durum Kontrolü
            is_answered = i in st.session_state.answers
            is_marked = i in st.session_state.marked
            is_active = (i == st.session_state.idx)
            
            # İkon Ekleme
            if is_marked: label = "🚩"
            elif is_answered: label = "✅"
            
            # Buton Rengi (Streamlit'te dinamik renk zordur, 'type' ile oynuyoruz)
            btn_type = "primary" if (is_answered or is_active) else "secondary"
            
            if col_list[i % 5].button(label, key=f"nav_{i}", type=btn_type, use_container_width=True):
                st.session_state.idx = i
                st.rerun()
        
        st.divider()
        if st.button("SINAVI BİTİR", type="primary", use_container_width=True):
            st.session_state.finish = True
            st.rerun()

    # --- ANA İÇERİK (SORU) ---
    if not st.session_state.finish:
        row = df.iloc[st.session_state.idx]
        passage, stem = parse_question(row['Soru'])
        
        # Üst Araç Çubuğu
        col_tool1, col_tool2 = st.columns([1, 5])
        with col_tool1:
            marked_label = "🏳️ Kaldır" if st.session_state.idx in st.session_state.marked else "🚩 İşaretle"
            if st.button(marked_label, key="mark_btn"):
                if st.session_state.idx in st.session_state.marked:
                    st.session_state.marked.remove(st.session_state.idx)
                else:
                    st.session_state.marked.add(st.session_state.idx)
                st.rerun()

        # --- GÖRÜNÜM (SPLIT vs FULL) ---
        if passage:
            # OKUMA MODU
            c_left, c_right = st.columns([1.1, 1], gap="medium")
            
            with c_left:
                st.info("Okuma Parçası")
                st.markdown(f"<div class='passage-box'>{passage}</div>", unsafe_allow_html=True)
                
            with c_right:
                st.markdown(f"**Soru {st.session_state.idx + 1}**")
                st.markdown(f"<div class='question-box'><div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
                
                # RADYO BUTON SİSTEMİ
                options = []
                mapping = {}
                for opt in ['A', 'B', 'C', 'D', 'E']:
                    if pd.notna(row[opt]):
                        full_opt = f"{opt}) {row[opt]}"
                        options.append(full_opt)
                        mapping[full_opt] = opt # "A) Apple" -> "A"
                
                # Daha önce verilmiş cevap varsa seçili getir
                current_ans = st.session_state.answers.get(st.session_state.idx)
                default_idx = None
                if current_ans:
                    # Kayıtlı şıkkı (örn 'A') tam metinle eşleştir
                    for i, o in enumerate(options):
                        if o.startswith(current_ans + ")"):
                            default_idx = i
                            break
                
                selected = st.radio(
                    "Cevabınız:", 
                    options, 
                    index=default_idx, 
                    key=f"radio_{st.session_state.idx}",
                    label_visibility="collapsed"
                )
                
                # Seçimi Kaydet
                if selected:
                    choice_char = mapping[selected]
                    st.session_state.answers[st.session_state.idx] = choice_char
                
                st.markdown("</div>", unsafe_allow_html=True)

        else:
            # NORMAL MOD (TEK SÜTUN)
            c_spacer_1, c_mid, c_spacer_2 = st.columns([1, 3, 1])
            with c_mid:
                st.markdown(f"**Soru {st.session_state.idx + 1}**")
                st.markdown(f"<div class='question-box'><div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
                
                options = []
                mapping = {}
                for opt in ['A', 'B', 'C', 'D', 'E']:
                    if pd.notna(row[opt]):
                        full_opt = f"{opt}) {row[opt]}"
                        options.append(full_opt)
                        mapping[full_opt] = opt
                
                current_ans = st.session_state.answers.get(st.session_state.idx)
                default_idx = None
                if current_ans:
                    for i, o in enumerate(options):
                        if o.startswith(current_ans + ")"):
                            default_idx = i
                            break

                selected = st.radio(
                    "Cevabınız:", 
                    options, 
                    index=default_idx, 
                    key=f"radio_{st.session_state.idx}",
                    label_visibility="collapsed"
                )
                
                if selected:
                    st.session_state.answers[st.session_state.idx] = mapping[selected]
                
                st.markdown("</div>", unsafe_allow_html=True)

        # --- ALT NAVİGASYON ---
        st.markdown("<br>", unsafe_allow_html=True)
        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
        
        with col_nav1:
            if st.session_state.idx > 0:
                if st.button("⬅️ Önceki Soru", use_container_width=True):
                    st.session_state.idx -= 1
                    st.rerun()
        
        with col_nav3:
            if st.session_state.idx < len(df) - 1:
                # Buton metnini Sonraki Soru yap, CSS ile rengini değiştiriyoruz
                if st.button("Sonraki Soru ➡️", use_container_width=True):
                    st.session_state.idx += 1
                    st.rerun()

    # --- SINAV BİTİŞ EKRANI ---
    else:
        st.balloons()
        st.title("🏁 Sınav Sonucu")
        
        correct_count = 0
        wrong_count = 0
        empty_count = 0
        
        results_data = []
        
        for i in range(len(df)):
            user_ans = st.session_state.answers.get(i)
            true_ans = str(df.iloc[i]['Dogru_Cevap']).strip().upper()
            
            status = "Boş"
            if user_ans:
                if user_ans == true_ans:
                    correct_count += 1
                    status = "Doğru"
                else:
                    wrong_count += 1
                    status = "Yanlış"
            else:
                empty_count += 1
                
            results_data.append({
                "No": i+1,
                "Cevabın": user_ans if user_ans else "-",
                "Doğru Cevap": true_ans,
                "Durum": status
            })
            
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam", len(df))
        c2.metric("Doğru", correct_count, delta_color="normal")
        c3.metric("Yanlış", wrong_count, delta_color="inverse")
        c4.metric("Boş", empty_count)
        
        st.divider()
        st.dataframe(pd.DataFrame(results_data), use_container_width=True)
        
        if st.button("Yeniden Başla"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

else:
    st.error("Veri dosyası (sorular.xlsx) bulunamadı.")
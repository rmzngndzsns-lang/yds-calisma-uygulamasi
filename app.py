import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import google.generativeai as genai

# --- 1. AYARLAR ---
st.set_page_config(page_title="YDS Pro AI", page_icon="🤖", layout="wide")

# ==========================================
# !!! BURAYA GEMINI API KEY YAPIŞTIR !!!
# ==========================================
GEMINI_API_KEY = "AIzaSyBYhFhLXc2mz7D9MgcGzAXZmxgzrTpL_Mg" 
# Örnek: "AIzaSyD_OrnekAnahtar..."

# --- 2. CSS TASARIMI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { font-family: 'Inter', sans-serif; background-color: #f3f4f6; }
    
    /* SIDEBAR BUTON AYARLARI (Sıkışık Grid) */
    [data-testid="stSidebar"] [data-testid="column"] { padding: 0px 1px !important; min-width: 0 !important; }
    [data-testid="stSidebar"] button { 
        width: 100% !important; 
        padding: 0px !important; 
        height: 34px !important; 
        font-size: 13px !important; 
        font-weight: 600 !important; 
        margin: 0px !important; 
    }

    /* OKUMA PARÇASI KUTUSU */
    .passage-box { 
        background-color: white; 
        padding: 20px; 
        border-radius: 12px; 
        height: 55vh; 
        overflow-y: auto; 
        font-size: 15.5px; 
        line-height: 1.7; 
        text-align: justify; 
        border: 1px solid #e5e7eb; 
        border-left: 5px solid #2c3e50; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.05); 
        color: #374151; 
    }

    /* SORU KÖKÜ */
    .question-stem { 
        font-size: 16.5px; 
        font-weight: 600; 
        background-color: white; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #e5e7eb; 
        border-left: 4px solid #3b82f6; 
        margin-bottom: 20px; 
        color: #111827; 
    }

    /* RADYO BUTONLAR (ŞIKLAR) */
    .stRadio > label { display: none; }
    .stRadio div[role='radiogroup'] > label { 
        padding: 12px 16px; 
        margin-bottom: 8px; 
        border: 1px solid #d1d5db; 
        border-radius: 8px; 
        background-color: white; 
        font-size: 15px; 
        color: #374151; 
        transition: all 0.2s; 
    }
    .stRadio div[role='radiogroup'] > label:hover { 
        background-color: #eff6ff; 
        border-color: #3b82f6; 
        color: #1d4ed8; 
    }

    /* ÖZEL BUTON RENKLERİ */
    div.stButton > button:contains("İşaretle") { border-color: #d97706 !important; color: #d97706 !important; font-weight: 700; }
    div.stButton > button:contains("Kaldır") { background-color: #d97706 !important; color: white !important; border: none; }
    
    /* GEMINI BUTONU */
    div.stButton > button:contains("Gemini") { 
        border: 2px solid #8e44ad !important; 
        color: #8e44ad !important; 
        font-weight: 700; 
        background-color: white; 
    }
    div.stButton > button:contains("Gemini"):hover { background-color: #f3e5f5 !important; }

    /* GEMINI CEVAP KUTUSU */
    .gemini-box {
        background-color: #f8f0fc;
        border: 1px solid #e1bee7;
        border-left: 5px solid #8e44ad;
        border-radius: 10px;
        padding: 20px;
        margin-top: 15px;
        font-size: 15px;
        color: #4a148c;
        line-height: 1.6;
    }

    /* NAVİGASYON BUTONLARI */
    div.stButton > button { height: 45px; font-weight: 500; font-size: 15px; }
</style>
""", unsafe_allow_html=True)

# --- 3. VERİ YÜKLEME ---
@st.cache_data
def load_data():
    dosya_adi = "sorular.xlsx"
    try:
        # engine='openpyxl' xlsx dosyaları için gereklidir
        df = pd.read_excel(dosya_adi, engine="openpyxl")
        
        # Sütun isimlerini kontrol et ve temizle
        df.columns = df.columns.str.strip()
        
        # 'Dogru_Cevap' sütununu standartlaştır
        if 'Dogru_Cevap' in df.columns:
            df['Dogru_Cevap'] = df['Dogru_Cevap'].astype(str).str.strip().str.upper()
        else:
            st.error(f"Excel dosyasında 'Dogru_Cevap' sütunu bulunamadı!")
            return None
            
        return df
    except FileNotFoundError:
        st.error(f"❌ Dosya Bulunamadı: '{dosya_adi}' dosyasının bu klasörde olduğundan emin ol.")
        return None
    except Exception as e:
        st.error(f"❌ Bir hata oluştu: {e}")
        return None

# --- 4. SESSION (OTURUM) BAŞLATMA ---
def init_session():
    if 'idx' not in st.session_state: st.session_state.idx = 0
    if 'answers' not in st.session_state: st.session_state.answers = {}
    if 'marked' not in st.session_state: st.session_state.marked = set()
    if 'end_timestamp' not in st.session_state:
        st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000 
    if 'finish' not in st.session_state: st.session_state.finish = False
    if 'gemini_res' not in st.session_state: st.session_state.gemini_res = {} # AI cevapları hafızası

df = load_data()
init_session()

# --- 5. PARSER (SORU AYRIŞTIRICI) ---
def parse_question(text):
    if pd.isna(text): return None, "..."
    text = str(text).replace('\\n', '\n')
    # Eğer çift enter varsa paragraf ve soru kökü olarak ayır
    parts = text.split('\n\n', 1) if '\n\n' in text else (None, text.strip())
    return parts[0].strip() if parts[0] else None, parts[1].strip()

# --- 6. GEMINI YAPAY ZEKA FONKSİYONU ---
def ask_ai(passage, question, options):
    if "BURAYA" in GEMINI_API_KEY or len(GEMINI_API_KEY) < 10:
        return "⚠️ Lütfen geçerli bir Gemini API Key girin. Kodun 15. satırını kontrol edin."
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Sen uzman bir YDS/YÖKDİL İngilizce sınav koçusun. Aşağıdaki soruyu öğrenciye detaylıca açıkla.
        
        PARAGRAF: {passage if passage else "-"}
        SORU KÖKÜ: {question}
        ŞIKLAR: {options}
        
        Lütfen şu formatta yanıt ver:
        1. **Çeviri:** Sorunun ve şıkların Türkçe anlamı.
        2. **Analiz:** Doğru cevap neden doğru? Hangi ipucundan yakalanmalı?
        3. **Çeldiriciler:** Diğer şıklar neden yanlış?
        4. **Kelime/Gramer:** Bu soruda öğrenilmesi gereken kritik kelime veya yapı nedir?
        """
        
        with st.spinner("🤖 Gemini Hoca Soruyu İnceliyor..."):
            res = model.generate_content(prompt)
            return res.text
    except Exception as e:
        return f"Bağlantı Hatası: {e}"

# --- 7. UYGULAMA GÖVDESİ ---
if df is not None:
    
    # --- SIDEBAR (YAN MENÜ) ---
    with st.sidebar:
        # SAYAÇ
        components.html(f"""
        <div style="font-family:'Courier New',monospace;font-size:36px;font-weight:800;color:#dc2626;background:white;padding:10px 0;border-radius:10px;text-align:center;border:3px solid #dc2626;margin-bottom:20px;letter-spacing:2px;box-shadow:0 4px 6px rgba(0,0,0,0.1);" id="cnt">...</div>
        <script>
            var dest = {st.session_state.end_timestamp};
            setInterval(function() {{
                var now = new Date().getTime(); var diff = dest - now;
                var h = Math.floor((diff%(1000*60*60*24))/(1000*60*60));
                var m = Math.floor((diff%(1000*60*60))/(1000*60));
                var s = Math.floor((diff%(1000*60))/1000);
                document.getElementById("cnt").innerHTML = (h<10?"0"+h:h)+":"+(m<10?"0"+m:m)+":"+(s<10?"0"+s:s);
            }}, 1000);
        </script>
        """, height=100)
        
        st.caption("🟢:D | 🔴:Y | ⭐:İşaret")

        # --- MOBİL UYUMLU GRID YAPISI (ROW-BASED) ---
        # Burası telefonda sıralamanın 1,2,3 diye gitmesini sağlar.
        chunk_size = 5
        for i in range(0, len(df), chunk_size):
            row_cols = st.columns(chunk_size)
            for j in range(chunk_size):
                if i + j < len(df):
                    q_idx = i + j
                    u_ans = st.session_state.answers.get(q_idx)
                    c_ans = df.iloc[q_idx]['Dogru_Cevap']
                    
                    label = str(q_idx + 1)
                    if u_ans: label = "✅" if u_ans == c_ans else "❌"
                    elif q_idx in st.session_state.marked: label = "⭐"
                    
                    b_type = "primary" if q_idx == st.session_state.idx else "secondary"
                    
                    with row_cols[j]:
                        if st.button(label, key=f"q_{q_idx}", type=b_type, use_container_width=True):
                            st.session_state.idx = q_idx
                            st.rerun()

        st.divider()
        if st.button("SINAVI BİTİR", type="primary", use_container_width=True):
            st.session_state.finish = True
            st.rerun()

    # --- ANA EKRAN ---
    if not st.session_state.finish:
        # BAŞLIK VE İŞARETLEME
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"### Soru {st.session_state.idx + 1} / {len(df)}")
        
        is_marked = st.session_state.idx in st.session_state.marked
        if c2.button("🏳️ Kaldır" if is_marked else "🚩 İşaretle", key="mark_main"):
            if is_marked: st.session_state.marked.remove(st.session_state.idx)
            else: st.session_state.marked.add(st.session_state.idx)
            st.rerun()

        # SORU İÇERİĞİ
        row = df.iloc[st.session_state.idx]
        passage, stem = parse_question(row['Soru'])
        
        # Şıkları Listele (A, B, C, D, E sütunlarından)
        opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
        
        # PARAGRAF VARSA İKİ SÜTUN, YOKSA TEK SÜTUN
        if passage:
            col_l, col_r = st.columns([1, 1], gap="medium")
            with col_l:
                st.info("Okuma Parçası")
                st.markdown(f"<div class='passage-box'>{passage}</div>", unsafe_allow_html=True)
            with col_r:
                st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
                
                # Şık Seçimi
                curr = st.session_state.answers.get(st.session_state.idx)
                idx_s = next((k for k,v in enumerate(opts) if v.startswith(curr + ")")), None) if curr else None
                sel = st.radio("Cevap", opts, index=idx_s, key=f"rad_{st.session_state.idx}")
                
                if sel:
                    char = sel.split(")")[0]
                    st.session_state.answers[st.session_state.idx] = char
                    if char == row['Dogru_Cevap']: st.success("✅ DOĞRU")
                    else: st.error(f"❌ YANLIŞ! (Cevap: {row['Dogru_Cevap']})")
                
                # GEMINI BUTONU (SAĞDA)
                st.write("")
                if st.button("🤖 Gemini'ye Sor & Açıkla", use_container_width=True):
                    res = ask_ai(passage, stem, opts)
                    st.session_state.gemini_res[st.session_state.idx] = res
                    st.rerun()

        else:
            # Sadece Soru Varsa
            st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
            
            curr = st.session_state.answers.get(st.session_state.idx)
            idx_s = next((k for k,v in enumerate(opts) if v.startswith(curr + ")")), None) if curr else None
            sel = st.radio("Cevap", opts, index=idx_s, key=f"rad_{st.session_state.idx}")
            
            if sel:
                char = sel.split(")")[0]
                st.session_state.answers[st.session_state.idx] = char
                if char == row['Dogru_Cevap']: st.success("✅ DOĞRU")
                else: st.error(f"❌ YANLIŞ! (Cevap: {row['Dogru_Cevap']})")
            
            # GEMINI BUTONU (ALTTA)
            st.write("")
            if st.button("🤖 Gemini'ye Sor & Açıkla", use_container_width=True):
                res = ask_ai(passage, stem, opts)
                st.session_state.gemini_res[st.session_state.idx] = res
                st.rerun()

        # GEMINI CEVAP GÖSTERİMİ (Varsa Ekrana Bas)
        if st.session_state.idx in st.session_state.gemini_res:
            st.markdown(f"""
            <div class="gemini-box">
                <h4>🤖 Gemini Öğretmen Diyor ki:</h4>
                {st.session_state.gemini_res[st.session_state.idx]}
            </div>
            """, unsafe_allow_html=True)

        # ALT NAVİGASYON (İLERİ / GERİ)
        st.write("")
        cp, cn = st.columns(2)
        if st.session_state.idx > 0:
            cp.button("⬅️ Önceki", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx-1), use_container_width=True)
        if st.session_state.idx < len(df) - 1:
            cn.button("Sonraki ➡️", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx+1), type="primary", use_container_width=True)

    else:
        # SONUÇ EKRANI
        st.title("Sınav Sonuçları")
        res = []
        c, w, e = 0, 0, 0
        for i in range(len(df)):
            ua = st.session_state.answers.get(i)
            true_a = df.iloc[i]['Dogru_Cevap']
            if ua:
                if ua == true_a: c+=1; s="Doğru"
                else: w+=1; s="Yanlış"
            else: e+=1; s="Boş"
            res.append({"No": i+1, "Cevap": ua, "Doğru": true_a, "Durum": s})
            
        k1, k2, k3 = st.columns(3)
        k1.metric("Doğru", c)
        k2.metric("Yanlış", w)
        k3.metric("Boş", e)
        st.dataframe(pd.DataFrame(res), use_container_width=True)
        if st.button("Başa Dön"):
            st.session_state.clear()
            st.rerun()
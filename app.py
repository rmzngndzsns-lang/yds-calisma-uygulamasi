import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import google.generativeai as genai
import edge_tts
import asyncio
import os

# --- 1. AYARLAR ---
st.set_page_config(page_title="Yds App", page_icon="🎓", layout="wide")

# ==========================================
# !!! BURAYA GEMINI API KEY YAPIŞTIR !!!
# ==========================================
GEMINI_API_KEY = "AIzaSyAiuriJuQLwsa54EwnY9Zy8zk1jj_Tajsg"

# --- 2. CSS TASARIMI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    .stApp { font-family: 'Inter', sans-serif; background-color: #f3f4f6; }
    
    [data-testid="stSidebar"] [data-testid="column"] { padding: 0px 1px !important; min-width: 0 !important; }
    [data-testid="stSidebar"] button { width: 100% !important; padding: 0px !important; height: 34px !important; font-size: 13px !important; font-weight: 700 !important; margin: 0px !important; }
    
    .passage-box { background-color: white; padding: 20px; border-radius: 12px; height: 55vh; overflow-y: auto; font-size: 16px; font-weight: 700; line-height: 1.8; text-align: justify; border: 1px solid #e5e7eb; border-left: 5px solid #2c3e50; color: #111827; }
    .question-stem { font-size: 17px; font-weight: 800; background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #e5e7eb; border-left: 4px solid #3b82f6; margin-bottom: 20px; color: #000000; }
    
    .strategy-box { background-color: #e3f2fd; border: 1px solid #bbdefb; border-left: 5px solid #1976d2; padding: 15px; border-radius: 8px; margin-bottom: 20px; color: #0d47a1; font-size: 15px; font-weight: 600; }
    .strategy-title { font-weight: 900; text-transform: uppercase; margin-bottom: 5px; display: flex; align-items: center; gap: 8px;}

    .sentence-box { background-color: white; border-radius: 8px; padding: 12px; margin-bottom: 12px; border-left: 4px solid #f39c12; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .eng-text { font-weight: 700; color: #2c3e50; margin-bottom: 4px; font-size: 15px; }
    .tr-text { color: #555; font-weight: 600; font-style: italic; font-size: 14px; }
    
    .ai-header { color: #8e44ad; font-weight: 900; font-size: 16px; margin-bottom: 8px; text-transform: uppercase; margin-top: 15px;}
    .ai-text { font-size: 15px; font-weight: 600; line-height: 1.6; color: #333; background: white; padding: 15px; border-radius: 10px; }

    div.stButton > button { height: 45px; font-weight: 700; font-size: 15px; }
    .stRadio div[role='radiogroup'] > label { font-weight: 600 !important; color: #1f2937 !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. VERİ YÜKLEME ---
@st.cache_data
def load_data():
    dosya_adi = "sorular.xlsx" 
    try:
        df = pd.read_excel(dosya_adi, engine="openpyxl")
        df.columns = df.columns.str.strip()
        if 'Dogru_Cevap' in df.columns:
            df['Dogru_Cevap'] = df['Dogru_Cevap'].astype(str).str.strip().str.upper()
        else:
            st.error(f"Excel dosyasında 'Dogru_Cevap' sütunu bulunamadı!")
            return None
        return df
    except FileNotFoundError:
        try:
             df = pd.read_csv("YDS1_ingilizce (2).xlsx - Table 1.csv")
             st.warning("Excel bulunamadı, CSV dosyası yüklendi.")
             return df
        except:
            st.error(f"❌ Dosya Bulunamadı! Lütfen dosya adının '{dosya_adi}' olduğundan emin ol.")
            return None
    except Exception as e:
        st.error(f"❌ Hata: {e}")
        return None

def init_session():
    if 'idx' not in st.session_state: st.session_state.idx = 0
    if 'answers' not in st.session_state: st.session_state.answers = {}
    if 'marked' not in st.session_state: st.session_state.marked = set()
    if 'end_timestamp' not in st.session_state: st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000 
    if 'finish' not in st.session_state: st.session_state.finish = False
    if 'gemini_res' not in st.session_state: st.session_state.gemini_res = {} 
    if 'speech_rate' not in st.session_state: st.session_state.speech_rate = "+0%"

df = load_data()
init_session()

def parse_question(text):
    if pd.isna(text): return None, "..."
    text = str(text).replace('\\n', '\n')
    parts = text.split('\n\n', 1) if '\n\n' in text else (None, text.strip())
    return parts[0].strip() if parts[0] else None, parts[1].strip()

# --- 6. HIZLI GEMINI ---
def get_gemini_text(passage, question, options):
    if "BURAYA" in GEMINI_API_KEY or len(GEMINI_API_KEY) < 10:
        return "⚠️ API Key Hatalı"
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Sen YDS sınav koçusun.
        PARAGRAF: {passage if passage else "Paragraf yok."}
        SORU: {question}
        ŞIKLAR: {options}
        
        Cevabı şu başlıklarla ver:
        
        [BÖLÜM 1: STRATEJİ VE MANTIK]
        (Soru türü ve çözüm ipucu)
        
        [BÖLÜM 2: CÜMLE ANALİZİ]
        (Her cümle için İngilizce ve Türkçe çeviri)
        
        [BÖLÜM 3: DOĞRU CEVAP]
        (Neden doğru?)
        
        [BÖLÜM 4: ÇELDİRİCİLER]
        (Neden yanlışlar?)
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Hata oluştu: {e}"

# --- 7. PARALEL SES FONKSİYONU (HIZ CANAVARI) ---
async def generate_segment(text, voice, rate, index):
    """Tek bir parçayı sese çevirir ve bytes döner"""
    if not text.strip(): return b""
    # Hızlandırmak için gereksiz karakterleri temizle
    clean = text.replace('*', '').replace('[', '').replace(']', '').replace('`', '')
    
    temp_file = f"temp_{index}.mp3"
    try:
        communicate = edge_tts.Communicate(clean, voice, rate=rate)
        await communicate.save(temp_file)
        
        with open(temp_file, "rb") as f:
            data = f.read()
        os.remove(temp_file) # Temizlik
        return data
    except:
        return b""

def generate_parallel_audio(full_text, speed_val):
    voice = "en-US-AndrewMultilingualNeural"
    rate_str = f"{speed_val}%" if speed_val < 0 else f"+{speed_val}%"
    
    # Metni bölümlere ayır
    parts = full_text.split('[BÖLÜM')
    # İlk parça genellikle boştur, onu atlayalım
    text_segments = [p for p in parts if len(p.strip()) > 10]
    
    # Eğer bölümleme başarısızsa tüm metni tek parça al
    if not text_segments:
        text_segments = [full_text]

    async def _main():
        # Tüm parçalar için aynı anda (paralel) görev başlat
        tasks = []
        for i, segment in enumerate(text_segments):
            # Segment başına "Bölüm X" ekleyerek anlam bütünlüğü sağla
            # (split yaparken [BÖLÜM silindiği için geri eklemek okunabilirlik sağlar ama süre yer)
            # Hız için eklemiyoruz, direkt içeriği okutuyoruz.
            tasks.append(generate_segment(segment, voice, rate_str, i))
        
        # Hepsini bekle ve sonuçları topla
        results = await asyncio.gather(*tasks)
        return b"".join(results) # Byte'ları birleştir

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        final_audio = loop.run_until_complete(_main())
        loop.close()
        return final_audio
    except Exception as e:
        st.error(f"Ses Hatası: {e}")
        return None

# --- 8. UYGULAMA GÖVDESİ ---
if df is not None:
    
    with st.sidebar:
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
        st.divider()
        st.write("🗣️ **Okuma Hızı**")
        speed_val = st.slider("Hız Ayarı (%)", min_value=-50, max_value=50, value=0, step=10)
        
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

    if not st.session_state.finish:
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"### Soru {st.session_state.idx + 1} / {len(df)}")
        
        is_marked = st.session_state.idx in st.session_state.marked
        if c2.button("🏳️ Kaldır" if is_marked else "🚩 İşaretle", key="mark_main"):
            if is_marked: st.session_state.marked.remove(st.session_state.idx)
            else: st.session_state.marked.add(st.session_state.idx)
            st.rerun()

        row = df.iloc[st.session_state.idx]
        passage, stem = parse_question(row['Soru'])
        opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
        
        if passage:
            col_l, col_r = st.columns([1, 1], gap="medium")
            with col_l:
                st.info("Okuma Parçası")
                st.markdown(f"<div class='passage-box'>{passage}</div>", unsafe_allow_html=True)
            with col_r:
                st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
                curr = st.session_state.answers.get(st.session_state.idx)
                idx_s = next((k for k,v in enumerate(opts) if v.startswith(curr + ")")), None) if curr else None
                sel = st.radio("Cevap", opts, index=idx_s, key=f"rad_{st.session_state.idx}")
                
                if sel:
                    char = sel.split(")")[0]
                    st.session_state.answers[st.session_state.idx] = char
                    if char == row['Dogru_Cevap']: st.success("✅ DOĞRU")
                    else: st.error(f"❌ YANLIŞ! (Cevap: {row['Dogru_Cevap']})")
                
                st.write("")
                if st.button("🤖 Strateji & Çözüm (Dinle) 🔊", use_container_width=True):
                    with st.spinner("🤖 Analiz yapılıyor..."):
                        txt = get_gemini_text(passage, stem, opts)
                        st.session_state.gemini_res[st.session_state.idx] = {'text': txt, 'audio': None}
                        st.rerun()

        else:
            st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
            curr = st.session_state.answers.get(st.session_state.idx)
            idx_s = next((k for k,v in enumerate(opts) if v.startswith(curr + ")")), None) if curr else None
            sel = st.radio("Cevap", opts, index=idx_s, key=f"rad_{st.session_state.idx}")
            
            if sel:
                char = sel.split(")")[0]
                st.session_state.answers[st.session_state.idx] = char
                if char == row['Dogru_Cevap']: st.success("✅ DOĞRU")
                else: st.error(f"❌ YANLIŞ! (Cevap: {row['Dogru_Cevap']})")
            
            st.write("")
            if st.button("🤖 Strateji & Çözüm (Dinle) 🔊", use_container_width=True):
                with st.spinner("🤖 Analiz yapılıyor..."):
                    txt = get_gemini_text(passage, stem, opts)
                    st.session_state.gemini_res[st.session_state.idx] = {'text': txt, 'audio': None}
                    st.rerun()

        # --- GÖRSELLEŞTİRME ---
        if st.session_state.idx in st.session_state.gemini_res:
            data = st.session_state.gemini_res[st.session_state.idx]
            full_text = data['text']
            
            # --- SES OYNATICI ---
            if data['audio'] is not None:
                st.success(f"🔊 Tam Metin Seslendiriliyor (Hız: {speed_val}%)")
                st.audio(data['audio'], format='audio/mp3')

            # --- METİN GÖSTERİMİ ---
            parts = full_text.split('[BÖLÜM')
            for part in parts:
                if "1: STRATEJİ" in part:
                    clean_text = part.replace("1: STRATEJİ VE MANTIK]", "").strip()
                    st.markdown(f"""<div class="strategy-box"><div class="strategy-title">💡 SINAV STRATEJİSİ & ÇÖZÜM MANTIĞI</div>{clean_text}</div>""", unsafe_allow_html=True)
                elif "2: CÜMLE ANALİZİ]" in part:
                    raw_content = part.replace("2: CÜMLE ANALİZİ]", "").strip()
                    st.markdown("<div class='ai-header'>🔍 CÜMLE CÜMLE ANALİZ</div>", unsafe_allow_html=True)
                    lines = raw_content.split('\n')
                    eng_buf, tr_buf = "", ""
                    for line in lines:
                        line = line.strip()
                        if "🇬🇧" in line: eng_buf = line.replace("🇬🇧", "").strip()
                        elif "🇹🇷" in line: tr_buf = line.replace("🇹🇷", "").strip()
                        if eng_buf and tr_buf:
                            st.markdown(f"""<div class="sentence-box"><div class="eng-text">{eng_buf}</div><div class="tr-text">{tr_buf}</div></div>""", unsafe_allow_html=True)
                            eng_buf, tr_buf = "", ""
                elif "3: DOĞRU CEVAP]" in part:
                    clean_text = part.replace("3: DOĞRU CEVAP]", "").strip()
                    st.markdown(f"""<div class="ai-header" style="color:#27ae60;">✅ NEDEN DOĞRU?</div><div class="ai-text" style="border-left: 5px solid #27ae60;">{clean_text}</div>""", unsafe_allow_html=True)
                elif "4: ÇELDİRİCİLER]" in part:
                    clean_text = part.replace("4: ÇELDİRİCİLER]", "").strip()
                    st.markdown(f"""<div class="ai-header" style="color:#c0392b;">❌ NEDEN YANLIŞ?</div><div class="ai-text" style="border-left: 5px solid #c0392b;">{clean_text}</div>""", unsafe_allow_html=True)
            
            # --- SES OLUŞTURMA (PARALEL) ---
            if data['audio'] is None:
                with st.spinner("🔊 Sesler birleştiriliyor... (Çok daha hızlı!)"):
                    # PARALEL ÇAĞRI
                    aud_bytes = generate_parallel_audio(full_text, speed_val)
                    if aud_bytes:
                        st.session_state.gemini_res[st.session_state.idx]['audio'] = aud_bytes
                        st.rerun()
                    else:
                        st.error("Ses oluşturulamadı.")

    else:
        st.title("Sonuçlar")
else:
    st.error("Excel yüklenemedi.")
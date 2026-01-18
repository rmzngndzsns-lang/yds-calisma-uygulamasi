import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import google.generativeai as genai
import edge_tts
import asyncio
import os
import re

# --- 1. AYARLAR ---
st.set_page_config(page_title="Yds App", page_icon="🎓", layout="wide")

# ==========================================
# !!! BURAYA GEMINI API KEY YAPIŞTIR !!!
# ==========================================
GEMINI_API_KEY = "AIzaSyDu9xpibnjd8pjtczu7GG-AkP7QaoBWsG0"

# --- 2. PREMIUM CSS TASARIMI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    
    .stApp { 
        font-family: 'Roboto', sans-serif; 
        background-color: #f8f9fa; 
    }
    
    /* BUTONLAR */
    div.stButton > button { 
        width: 100%; 
        border-radius: 8px; 
        font-weight: 600; 
        height: 40px;
        transition: all 0.3s ease;
    }

    /* OKUMA PARÇASI KUTUSU (Sol Taraf) */
    .passage-box { 
        background-color: #ffffff; 
        padding: 25px; 
        border-radius: 15px; 
        height: 60vh; 
        overflow-y: auto; 
        font-size: 16px; 
        font-weight: 500; 
        line-height: 1.8; 
        text-align: justify; /* İKİ YANA YASLAMA */
        border: 1px solid #e9ecef; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        color: #2d3436; 
    }
    
    /* SORU KÖKÜ */
    .question-stem { 
        font-size: 18px; 
        font-weight: 700; 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 12px; 
        border-left: 5px solid #0984e3; 
        margin-bottom: 25px; 
        color: #2d3436;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* STRATEJİ KUTUSU (Mavi) */
    .strategy-box { 
        background-color: #e8f4fd; 
        border-left: 5px solid #3498db; 
        padding: 20px; 
        border-radius: 10px; 
        margin-bottom: 20px; 
        color: #2c3e50; 
        font-size: 15px; 
        line-height: 1.6;
        text-align: justify; /* İKİ YANA YASLAMA */
    }
    
    /* CÜMLE KUTULARI (Sarı) */
    .sentence-box { 
        background-color: #fffbf2; 
        border-left: 5px solid #f1c40f; 
        padding: 15px; 
        border-radius: 10px; 
        margin-bottom: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .eng-text { 
        font-weight: 700; 
        color: #2c3e50; 
        margin-bottom: 8px; 
        font-size: 16px;
    }
    .tr-text { 
        color: #576574; 
        font-style: italic; 
        font-size: 15px; 
        font-weight: 400;
    }

    /* AI BAŞLIKLARI */
    .ai-header { 
        color: #8e44ad; 
        font-weight: 900; 
        font-size: 14px; 
        letter-spacing: 1px; 
        margin-bottom: 10px; 
        text-transform: uppercase; 
        margin-top: 20px;
        border-bottom: 2px solid #ecf0f1;
        padding-bottom: 5px;
    }
    
    /* DOĞRU/YANLIŞ KUTULARI */
    .answer-box-correct {
        background-color: #eafaf1;
        border-left: 5px solid #2ecc71;
        padding: 15px;
        border-radius: 8px;
        text-align: justify;
        color: #27ae60;
        font-weight: 500;
    }
    .answer-box-wrong {
        background-color: #fdedec;
        border-left: 5px solid #e74c3c;
        padding: 15px;
        border-radius: 8px;
        text-align: justify;
        color: #c0392b;
        font-weight: 500;
    }

    /* Scrollbar Güzelleştirme */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #f1f1f1; }
    ::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #a8a8a8; }

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
        return df
    except:
        try:
             df = pd.read_csv("YDS1_ingilizce (2).xlsx - Table 1.csv")
             return df
        except:
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

# --- 4. HIZLI GEMINI ---
def get_gemini_text(passage, question, options):
    if "BURAYA" in GEMINI_API_KEY or len(GEMINI_API_KEY) < 10: return "⚠️ API Key Hatalı"
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Sen YDS sınav koçusun.
        PARAGRAF: {passage if passage else "Paragraf yok."}
        SORU: {question}
        ŞIKLAR: {options}
        
        Cevabı şu başlıklarla ver (Markdown yıldızlarını abartma):
        
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

# --- 5. GÖRSEL TEMİZLİK FONKSİYONU ---
def clean_visual_text(text):
    """Ekranda görünen metindeki *** gibi kirlilikleri temizler."""
    # 3 yıldızları sil veya normale çevir
    text = text.replace('***', '') 
    # Gereksiz markdown bold işaretlerini temizle (İsteğe bağlı)
    # text = text.replace('**', '') 
    return text

# --- 6. SES TEMİZLİK FONKSİYONU ---
def clean_text_for_tts(text):
    """Sese gitmeden önce metni temizler."""
    text = re.sub(r'[\#\*\_\`]', '', text) # Yıldız, kare, alt tire sil
    text = text.replace('🇬🇧', '').replace('🇹🇷', '').replace('💡', '').replace('✅', '').replace('❌', '').replace('🔍', '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- 7. PARALEL SES OLUŞTURMA (HIZ AYARI DÜZELTİLDİ) ---
async def generate_segment(text, voice, rate, index):
    if not text.strip(): return b""
    cleaned_text = clean_text_for_tts(text)
    temp_file = f"temp_{index}.mp3"
    try:
        # HIZ AYARI BURADA DEVREYE GİRİYOR (rate parametresi)
        communicate = edge_tts.Communicate(cleaned_text, voice, rate=rate)
        await communicate.save(temp_file)
        with open(temp_file, "rb") as f: data = f.read()
        os.remove(temp_file)
        return data
    except:
        return b""

def generate_parallel_audio(full_text, speed_val):
    voice = "en-US-BrianMultilingualNeural" # Brian daha profesyonel ve nettir.
    
    # HIZ FORMATI KONTROLÜ
    # Edge-TTS için format: "+10%" veya "-10%"
    rate_str = f"{speed_val}%" if speed_val < 0 else f"+{speed_val}%"
    
    parts = full_text.split('[BÖLÜM')
    text_segments = [p for p in parts if len(p.strip()) > 10]
    if not text_segments: text_segments = [full_text]

    async def _main():
        tasks = []
        for i, segment in enumerate(text_segments):
            # rate_str'yi her parçaya gönderiyoruz
            tasks.append(generate_segment(segment, voice, rate_str, i))
        results = await asyncio.gather(*tasks)
        return b"".join(results)

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
        # SAYAÇ
        components.html(f"""
        <div style="font-family:'Courier New',monospace;font-size:32px;font-weight:bold;color:#e74c3c;background:white;padding:10px;border-radius:10px;text-align:center;border:2px solid #e74c3c;margin-bottom:20px;" id="cnt">...</div>
        <script>
            var dest = {st.session_state.end_timestamp};
            setInterval(function() {{
                var now = new Date().getTime(); var diff = dest - now;
                var h = Math.floor((diff%(1000*60*60*24))/(1000*60*60));
                var m = Math.floor((diff%(1000*60*60))/(1000*60));
                var s = Math.floor((diff%(1000*60))/1000);
                document.getElementById("cnt").innerHTML = (h<10?"0"+h:h)+":"+(m<10?"0"+m:m)+":"+(s<10?"0"+s:s);
            }}, 1000);
        </script>""", height=90)
        
        st.write("---")
        st.markdown("### ⚙️ Ayarlar")
        st.write("🗣️ **Okuma Hızı**")
        # Slider'ı session_state'e bağlayalım ki değeri kaybolmasın
        speed_val = st.slider("Hız Ayarı (%)", min_value=-50, max_value=50, value=0, step=10, key="speed_slider")
        
        st.write("---")
        st.markdown("### 🧩 Sorular")
        
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
        
        st.write("---")
        if st.button("🏁 SINAVI BİTİR", type="primary"):
            st.session_state.finish = True
            st.rerun()

    if not st.session_state.finish:
        # ÜST BAR
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"## 📝 Soru {st.session_state.idx + 1} / {len(df)}")
        is_marked = st.session_state.idx in st.session_state.marked
        if c2.button("🏳️ Kaldır" if is_marked else "🚩 İşaretle", key="mark_main"):
            if is_marked: st.session_state.marked.remove(st.session_state.idx)
            else: st.session_state.marked.add(st.session_state.idx)
            st.rerun()

        row = df.iloc[st.session_state.idx]
        passage, stem = parse_question(row['Soru'])
        opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
        
        # SORU ALANI
        if passage:
            col_l, col_r = st.columns([1, 1], gap="medium")
            with col_l:
                st.markdown("#### 📖 Okuma Parçası")
                st.markdown(f"<div class='passage-box'>{passage}</div>", unsafe_allow_html=True)
            with col_r:
                st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
                curr = st.session_state.answers.get(st.session_state.idx)
                idx_s = next((k for k,v in enumerate(opts) if v.startswith(curr + ")")), None) if curr else None
                sel = st.radio("Cevabınız:", opts, index=idx_s, key=f"rad_{st.session_state.idx}")
                
                if sel:
                    char = sel.split(")")[0]
                    st.session_state.answers[st.session_state.idx] = char
                    if char == row['Dogru_Cevap']: st.success("TEBRİKLER! DOĞRU CEVAP 🎉")
                    else: st.error(f"MAALESEF YANLIŞ. DOĞRU CEVAP: {row['Dogru_Cevap']}")
                
                st.write("")
                if st.button("🤖 Çözümle ve Seslendir 🔊", use_container_width=True):
                    with st.spinner("🧠 Yapay Zeka Düşünüyor..."):
                        txt = get_gemini_text(passage, stem, opts)
                        st.session_state.gemini_res[st.session_state.idx] = {'text': txt, 'audio': None}
                        st.rerun()
        else:
            # Paragrafsız Soru
            st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
            curr = st.session_state.answers.get(st.session_state.idx)
            idx_s = next((k for k,v in enumerate(opts) if v.startswith(curr + ")")), None) if curr else None
            sel = st.radio("Cevabınız:", opts, index=idx_s, key=f"rad_{st.session_state.idx}")
            
            if sel:
                char = sel.split(")")[0]
                st.session_state.answers[st.session_state.idx] = char
                if char == row['Dogru_Cevap']: st.success("TEBRİKLER! DOĞRU CEVAP 🎉")
                else: st.error(f"MAALESEF YANLIŞ. DOĞRU CEVAP: {row['Dogru_Cevap']}")
            
            st.write("")
            if st.button("🤖 Çözümle ve Seslendir 🔊", use_container_width=True):
                with st.spinner("🧠 Yapay Zeka Düşünüyor..."):
                    txt = get_gemini_text(passage, stem, opts)
                    st.session_state.gemini_res[st.session_state.idx] = {'text': txt, 'audio': None}
                    st.rerun()

        # SONUÇ GÖSTERİMİ
        if st.session_state.idx in st.session_state.gemini_res:
            data = st.session_state.gemini_res[st.session_state.idx]
            full_text = clean_visual_text(data['text']) # EKRAN İÇİN TEMİZLEME
            
            st.markdown("---")
            
            # SES OYNATICI
            if data['audio'] is not None:
                st.success(f"🔊 Seslendirme Hazır (Hız: {speed_val}%)")
                st.audio(data['audio'], format='audio/mp3')

            # PARÇALI GÖSTERİM (PROFESYONEL CSS İLE)
            parts = full_text.split('[BÖLÜM')
            for part in parts:
                if "1: STRATEJİ" in part:
                    clean_text = part.replace("1: STRATEJİ VE MANTIK]", "").strip()
                    st.markdown(f"""<div class="strategy-box"><div class="ai-header">💡 STRATEJİ & İPUCU</div>{clean_text}</div>""", unsafe_allow_html=True)
                elif "2: CÜMLE ANALİZİ]" in part:
                    raw_content = part.replace("2: CÜMLE ANALİZİ]", "").strip()
                    st.markdown("<div class='ai-header' style='margin-left:5px;'>🔍 DETAYLI CÜMLE ANALİZİ</div>", unsafe_allow_html=True)
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
                    st.markdown(f"""<div class="answer-box-correct"><div class="ai-header" style="color:#27ae60; border-color:#27ae60;">✅ DOĞRU CEVAP</div>{clean_text}</div><br>""", unsafe_allow_html=True)
                elif "4: ÇELDİRİCİLER]" in part:
                    clean_text = part.replace("4: ÇELDİRİCİLER]", "").strip()
                    st.markdown(f"""<div class="answer-box-wrong"><div class="ai-header" style="color:#c0392b; border-color:#c0392b;">❌ ÇELDİRİCİ ANALİZİ</div>{clean_text}</div>""", unsafe_allow_html=True)
            
            # SES YOKSA OLUŞTUR
            if data['audio'] is None:
                with st.spinner("🔊 Profesyonel ses oluşturuluyor..."):
                    # Burada "speed_val" slider'dan gelen güncel değeri kullanıyoruz
                    aud_bytes = generate_parallel_audio(data['text'], speed_val)
                    if aud_bytes:
                        st.session_state.gemini_res[st.session_state.idx]['audio'] = aud_bytes
                        st.rerun()
                    else:
                        st.error("Ses oluşturulamadı.")
    else:
        st.title("Sınav Sonuçları")
        # Sonuç ekranı kodları...
else:
    st.error("Veri dosyası yüklenemedi.")
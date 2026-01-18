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
import nest_asyncio

# Döngü yaması
nest_asyncio.apply()

# --- 1. AYARLAR ---
st.set_page_config(page_title="Yds Pro", page_icon="🎓", layout="wide")

# --- 2. PREMIUM CSS TASARIMI (GÜNCELLENDİ) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    
    .stApp { font-family: 'Roboto', sans-serif; background-color: #f0f2f6; }
    
    div.stButton > button { 
        width: 100%; border-radius: 8px; font-weight: 600; height: 45px;
        transition: all 0.2s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* OKUMA PARÇASI - DAHA OKUNAKLI */
    .passage-box { 
        background-color: #ffffff; padding: 30px; border-radius: 12px; height: 60vh; 
        overflow-y: auto; font-size: 17px; font-weight: 500; line-height: 2.0; 
        text-align: justify; border: 1px solid #dfe6e9; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        color: #2d3436; font-family: 'Georgia', serif; /* Okuma parçası için serif font */
    }
    
    /* SORU KÖKÜ */
    .question-stem { 
        font-size: 19px; font-weight: 700; background-color: #ffffff; padding: 25px; 
        border-radius: 12px; border-left: 6px solid #0984e3; margin-bottom: 25px; 
        color: #1e272e; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* ANALİZ KUTULARI - RENK AYRIMI */
    .strategy-box { 
        background-color: #e3f2fd; border-left: 5px solid #2196f3; padding: 20px; 
        border-radius: 8px; margin-bottom: 20px; color: #0d47a1; font-size: 16px; 
        line-height: 1.6; text-align: justify;
    }
    
    .sentence-box { 
        background-color: #ffffff; border-left: 5px solid #f1c40f; padding: 20px; 
        border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        border: 1px solid #f9f9f9;
    }
    /* İNGİLİZCE CÜMLE - KOYU VE BELİRGİN */
    .eng-text { 
        font-weight: 700; color: #2c3e50; margin-bottom: 10px; font-size: 17px; 
        border-bottom: 1px dashed #ecf0f1; padding-bottom: 8px;
    }
    /* TÜRKÇE CÜMLE - GRİ VE İTALİK (KARIŞMAMASI İÇİN) */
    .tr-text { 
        color: #7f8c8d; font-style: italic; font-size: 16px; font-weight: 400; line-height: 1.6;
    }

    .ai-header { 
        color: #8e44ad; font-weight: 900; font-size: 15px; letter-spacing: 1px; 
        margin-bottom: 15px; text-transform: uppercase; margin-top: 25px;
        border-bottom: 2px solid #ecf0f1; padding-bottom: 5px;
    }
    
    .answer-box-correct { background-color: #e8f5e9; border-left: 5px solid #2ecc71; padding: 20px; border-radius: 8px; text-align: justify; color: #27ae60; font-weight: 600; font-size: 16px;}
    .answer-box-wrong { background-color: #ffebee; border-left: 5px solid #e74c3c; padding: 20px; border-radius: 8px; text-align: justify; color: #c0392b; font-weight: 600; font-size: 16px;}

    /* SCROLLBAR */
    ::-webkit-scrollbar { width: 10px; }
    ::-webkit-scrollbar-track { background: #f1f1f1; }
    ::-webkit-scrollbar-thumb { background: #b2bec3; border-radius: 5px; }
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

df = load_data()
init_session()

def parse_question(text):
    if pd.isna(text): return None, "..."
    text = str(text).replace('\\n', '\n')
    parts = text.split('\n\n', 1) if '\n\n' in text else (None, text.strip())
    return parts[0].strip() if parts[0] else None, parts[1].strip()

# --- 4. HIZLI GEMINI ---
def get_gemini_text(api_key, passage, question, options):
    if "BURAYA" in api_key or len(api_key) < 10:
        return "⚠️ Lütfen kodun 326. satırına API Key'inizi girin!"
    
    try:
        genai.configure(api_key=api_key)
        # --- MODEL SEÇİMİ (JOKER YÖNTEMİ) ---
        # Senin listende bu vardı. Bu, "elindeki en yeni çalışan Flash modeli neyse onu ver" demektir.
        # Sürüm hatası vermez.
        model = genai.GenerativeModel('gemini-flash-latest')
        
        prompt = f"""
        Sen YDS sınav koçusun.
        PARAGRAF: {passage if passage else "Paragraf yok."}
        SORU: {question}
        ŞIKLAR: {options}
        
        Cevabı ETİKETLERİ BOZMADAN şu formatta ver:
        
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
        return f"HATA: {str(e)}"

# --- 5. GELİŞMİŞ METİN FORMATLAYICI ---
def format_markdown_to_html(text):
    """
    Hem **çift yıldız** hem *tek yıldız* kalın (bold) yapılır.
    """
    if not text: return ""
    # Çift yıldızları bold yap
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Tek yıldızları da bold yap
    text = re.sub(r'\*(.*?)\*', r'<b>\1</b>', text)
    return text

def clean_text_for_tts(text):
    """Sese gitmeden önce metni temizler"""
    # Yıldızların hepsini sil (Seste duyulmasın)
    text = text.replace('**', '').replace('*', '')
    text = re.sub(r'[\#\_\`]', '', text)
    text = text.replace('🇬🇧', '').replace('🇹🇷', '').replace('💡', '').replace('✅', '').replace('❌', '').replace('🔍', '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- 6. PARALEL SES ---
async def generate_segment(text, voice, rate, index):
    if not text.strip(): return b""
    if len(text) < 2: return b"" 
    
    cleaned_text = clean_text_for_tts(text)
    temp_file = f"temp_{index}.mp3"
    try:
        communicate = edge_tts.Communicate(cleaned_text, voice, rate=rate)
        await communicate.save(temp_file)
        with open(temp_file, "rb") as f: data = f.read()
        os.remove(temp_file)
        return data
    except:
        return b""

def generate_parallel_audio(full_text):
    if full_text.startswith("HATA") or full_text.startswith("⚠️"): return None

    voice = "en-US-BrianMultilingualNeural" 
    rate_str = "+0%" # SABİT HIZ
    
    lines = full_text.split('\n')
    text_segments = [line for line in lines if len(line.strip()) > 5]

    async def _main():
        tasks = []
        for i, segment in enumerate(text_segments):
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

# --- 7. UYGULAMA GÖVDESİ ---
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
        
        # --- API KEY (SABİT) ---
        st.info("🔑 **API Anahtarı**")
        # 👇👇👇 BURAYA KENDİ KEYİNİ YAPIŞTIR 👇👇👇
        user_api_key = "AIzaSyBieaJ-pyHstD1hzvTspVaU58BPyT12Uxs" 
        # 👆👆👆 BURAYA KENDİ KEYİNİ YAPIŞTIR 👆👆👆
        
        if "BURAYA" in user_api_key:
            st.error("Lütfen kodun 326. satırına API Key'inizi girin!")

        st.write("---")
        
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
        
        if passage:
            col_l, col_r = st.columns([1, 1], gap="medium")
            with col_l:
                st.markdown("#### 📖 Okuma Parçası")
                formatted_passage = format_markdown_to_html(passage)
                st.markdown(f"<div class='passage-box'>{formatted_passage}</div>", unsafe_allow_html=True)
            with col_r:
                formatted_stem = format_markdown_to_html(stem)
                st.markdown(f"<div class='question-stem'>{formatted_stem}</div>", unsafe_allow_html=True)
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
                        txt = get_gemini_text(user_api_key, passage, stem, opts)
                        st.session_state.gemini_res[st.session_state.idx] = {'text': txt, 'audio': None}
                        st.rerun()
        else:
            formatted_stem = format_markdown_to_html(stem)
            st.markdown(f"<div class='question-stem'>{formatted_stem}</div>", unsafe_allow_html=True)
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
                    txt = get_gemini_text(user_api_key, passage, stem, opts)
                    st.session_state.gemini_res[st.session_state.idx] = {'text': txt, 'audio': None}
                    st.rerun()

        # SONUÇ GÖSTERİMİ
        if st.session_state.idx in st.session_state.gemini_res:
            data = st.session_state.gemini_res[st.session_state.idx]
            
            if data['text'].startswith("HATA") or data['text'].startswith("⚠️"):
                 st.error(data['text'])
            else:
                full_text = data['text'] 
                
                st.markdown("---")
                
                if data['audio'] is not None:
                    st.success(f"🔊 Seslendirme Hazır")
                    st.audio(data['audio'], format='audio/mp3')

                parts = full_text.split('[BÖLÜM')
                for part in parts:
                    if "1: STRATEJİ" in part:
                        clean_text = part.replace("1: STRATEJİ VE MANTIK]", "").strip()
                        html_text = format_markdown_to_html(clean_text)
                        st.markdown(f"""<div class="strategy-box"><div class="ai-header">💡 STRATEJİ & İPUCU</div>{html_text}</div>""", unsafe_allow_html=True)
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
                                eng_html = format_markdown_to_html(eng_buf)
                                tr_html = format_markdown_to_html(tr_buf)
                                st.markdown(f"""<div class="sentence-box"><div class="eng-text">{eng_html}</div><div class="tr-text">{tr_html}</div></div>""", unsafe_allow_html=True)
                                eng_buf, tr_buf = "", ""
                    elif "3: DOĞRU CEVAP]" in part:
                        clean_text = part.replace("3: DOĞRU CEVAP]", "").strip()
                        html_text = format_markdown_to_html(clean_text)
                        st.markdown(f"""<div class="answer-box-correct"><div class="ai-header" style="color:#27ae60; border-color:#27ae60;">✅ DOĞRU CEVAP</div>{html_text}</div><br>""", unsafe_allow_html=True)
                    elif "4: ÇELDİRİCİLER]" in part:
                        clean_text = part.replace("4: ÇELDİRİCİLER]", "").strip()
                        html_text = format_markdown_to_html(clean_text)
                        st.markdown(f"""<div class="answer-box-wrong"><div class="ai-header" style="color:#c0392b; border-color:#c0392b;">❌ ÇELDİRİCİ ANALİZİ</div>{html_text}</div>""", unsafe_allow_html=True)
                
                # SES OLUŞTURMA
                if data['audio'] is None:
                    with st.spinner("🔊 Ultra-Hızlı ses oluşturuluyor..."):
                        aud_bytes = generate_parallel_audio(data['text'])
                        if aud_bytes:
                            st.session_state.gemini_res[st.session_state.idx]['audio'] = aud_bytes
                            st.rerun()
                        else:
                            st.error("Ses oluşturulamadı (Metin boş veya hatalı olabilir).")
    else:
        st.title("Sınav Sonuçları")
else:
    st.error("Veri dosyası yüklenemedi.")
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
st.set_page_config(page_title="Yds App", page_icon="🎓", layout="wide")

# --- 2. CSV KAYIT SİSTEMİ ---
SCORES_FILE = "sinav_sonuclari.csv"

def save_score_to_csv(username, score, correct, wrong, empty):
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_data = {
        "Tarih": [date_str],
        "Kullanıcı": [username],
        "Puan": [score],
        "Doğru": [correct],
        "Yanlış": [wrong],
        "Boş": [empty]
    }
    new_df = pd.DataFrame(new_data)
    if os.path.exists(SCORES_FILE):
        try:
            existing_df = pd.read_csv(SCORES_FILE)
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            updated_df.to_csv(SCORES_FILE, index=False)
        except:
            new_df.to_csv(SCORES_FILE, index=False)
    else:
        new_df.to_csv(SCORES_FILE, index=False)

def get_leaderboard():
    if os.path.exists(SCORES_FILE):
        try:
            df = pd.read_csv(SCORES_FILE)
            df = df.sort_values(by="Puan", ascending=False).reset_index(drop=True)
            df.index = df.index + 1
            return df
        except:
            return None
    return None

# --- 3. PREMIUM CSS TASARIMI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    
    .stApp { font-family: 'Roboto', sans-serif; background-color: #f0f2f6; }
    
    div.stButton > button { 
        width: 100%; border-radius: 8px; font-weight: 600; height: 45px;
        transition: all 0.2s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .passage-box { 
        background-color: #ffffff; padding: 30px; border-radius: 12px; height: 60vh; 
        overflow-y: auto; font-size: 17px; font-weight: 500; line-height: 2.0; 
        text-align: justify; border: 1px solid #dfe6e9; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        color: #2d3436; font-family: 'Georgia', serif; 
    }
    
    .question-stem { 
        font-size: 19px; font-weight: 700; background-color: #ffffff; padding: 25px; 
        border-radius: 12px; border-left: 6px solid #0984e3; margin-bottom: 25px; 
        color: #1e272e; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
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
    .eng-text { 
        font-weight: 700; color: #2c3e50; margin-bottom: 10px; font-size: 17px; 
        border-bottom: 1px dashed #ecf0f1; padding-bottom: 8px;
    }
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

    /* ANALİZ RAPORU KUTUSU */
    .analysis-report {
        background-color: #fff; border: 2px solid #6c5ce7; border-radius: 15px;
        padding: 25px; margin-top: 20px; box-shadow: 0 5px 15px rgba(108, 92, 231, 0.1);
    }
    
    ::-webkit-scrollbar { width: 10px; }
    ::-webkit-scrollbar-track { background: #f1f1f1; }
    ::-webkit-scrollbar-thumb { background: #b2bec3; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 4. VERİ YÜKLEME ---
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
    if 'username' not in st.session_state: st.session_state.username = None
    if 'idx' not in st.session_state: st.session_state.idx = 0
    if 'answers' not in st.session_state: st.session_state.answers = {}
    if 'marked' not in st.session_state: st.session_state.marked = set()
    if 'end_timestamp' not in st.session_state: st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000 
    if 'finish' not in st.session_state: st.session_state.finish = False
    if 'data_saved' not in st.session_state: st.session_state.data_saved = False 
    if 'gemini_res' not in st.session_state: st.session_state.gemini_res = {} 
    if 'analysis_report' not in st.session_state: st.session_state.analysis_report = None # Yapay zeka raporu için

df = load_data()
init_session()

# --- 5. GİRİŞ EKRANI ---
if st.session_state.username is None:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
        st.title("YDS Sınav Sistemi")
        st.markdown("Sınava başlamak için lütfen adınızı giriniz.")
        name_input = st.text_input("Adınız Soyadınız:")
        if st.button("🚀 Sınava Başla", type="primary"):
            if name_input.strip():
                st.session_state.username = name_input.strip()
                st.rerun()
            else:
                st.warning("Lütfen bir isim giriniz.")
    st.stop()

def parse_question(text):
    if pd.isna(text): return None, "..."
    text = str(text).replace('\\n', '\n')
    parts = text.split('\n\n', 1) if '\n\n' in text else (None, text.strip())
    return parts[0].strip() if parts[0] else None, parts[1].strip()

# --- 6. SORU ÇÖZÜMLEME GEMINI ---
def get_gemini_text(api_key, passage, question, options):
    if not api_key: return "⚠️ API Key Yok."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Sen YDS koçusun. PARAGRAF: {passage} SORU: {question} ŞIKLAR: {options}. Cevabı [BÖLÜM 1: STRATEJİ], [BÖLÜM 2: ANALİZ], [BÖLÜM 3: DOĞRU CEVAP], [BÖLÜM 4: ÇELDİRİCİLER] formatında ver."
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"HATA: {str(e)}"

# --- 7. PERFORMANS ANALİZİ YAPAN YENİ YAPAY ZEKA FONKSİYONU ---
def generate_performance_analysis(api_key, wrong_questions_text, score_info):
    if not api_key: return "⚠️ Analiz için API Anahtarı gerekli."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Sen profesyonel bir YDS ve İngilizce Eğitmenisin.
        Öğrencinin Sınav Sonucu:
        {score_info}
        
        Aşağıda öğrencinin YANLIŞ yaptığı soruların metinleri var.
        Bu soruları analiz ederek öğrencinin hangi gramer konularında (Tense, Preposition, Bağlaç, Relative Clause, Kelime vb.) eksiği olduğunu tespit et.
        
        YANLIŞ YAPILAN SORULAR:
        {wrong_questions_text}
        
        Lütfen cevabı şu formatta ver (Markdown kullanarak):
        
        ### 📊 Genel Değerlendirme
        (Öğrencinin genel seviyesi hakkında kısa yorum)
        
        ### ⚠️ Tespit Edilen Eksik Konular
        * **Konu Adı:** (Neden bu kanıya vardın? Örn: "If clause sorularında hata yapılmış.")
        
        ### 💡 Çalışma Tavsiyeleri
        (Bu öğrenci netlerini artırmak için ne yapmalı? Spesifik tavsiyeler ver.)
        
        ### 🎯 Motivasyon Notu
        (Kısa ve motive edici bir kapanış)
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Analiz oluşturulurken hata oluştu: {str(e)}"

# --- 8. FORMAT VE TTS ---
def format_markdown_to_html(text):
    if not text: return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<b>\1</b>', text)
    return text

def clean_text_for_tts(text):
    text = text.replace('**', '').replace('*', '')
    text = re.sub(r'[\#\_\`]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def generate_segment(text, voice, rate, index):
    if not text.strip(): return b""
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
    if full_text.startswith("HATA"): return None
    voice = "en-US-BrianMultilingualNeural" 
    lines = full_text.split('\n')
    text_segments = [line for line in lines if len(line.strip()) > 5]
    async def _main():
        tasks = []
        for i, seg in enumerate(text_segments):
            tasks.append(generate_segment(seg, voice, "+0%", i))
        return b"".join(await asyncio.gather(*tasks))
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_main())
    except: return None

# --- 9. UYGULAMA GÖVDESİ ---
if df is not None:
    with st.sidebar:
        st.success(f"👤 **{st.session_state.username}**")
        
        # SAYAÇ
        components.html(f"""<div style="font-family:'Courier',monospace;font-size:32px;font-weight:bold;color:#e74c3c;background:white;padding:10px;border-radius:10px;text-align:center;border:2px solid #e74c3c;">...</div><script>var dest={st.session_state.end_timestamp};setInterval(function(){{var now=new Date().getTime();var diff=dest-now;var h=Math.floor((diff%(1000*60*60*24))/(1000*60*60));var m=Math.floor((diff%(1000*60*60))/(1000*60));var s=Math.floor((diff%(1000*60))/1000);document.querySelector("div").innerHTML=(h<10?"0"+h:h)+":"+(m<10?"0"+m:m)+":"+(s<10?"0"+s:s);}},1000);</script>""", height=70)
        
        st.write("---")
        st.info("🔑 **Kendi API Anahtarınız**")
        user_api_key = st.text_input("Google AI Studio Key:", type="password")
        
        st.write("---")
        # NAVİGASYON
        chunk_size = 5
        for i in range(0, len(df), chunk_size):
            cols = st.columns(chunk_size)
            for j in range(chunk_size):
                if i+j < len(df):
                    idx = i+j
                    lbl = str(idx+1)
                    if st.session_state.answers.get(idx): 
                        lbl = "✅" if st.session_state.answers[idx] == df.iloc[idx]['Dogru_Cevap'] else "❌"
                    elif idx in st.session_state.marked: lbl = "⭐"
                    if cols[j].button(lbl, key=f"q_{idx}", type="primary" if idx==st.session_state.idx else "secondary"):
                        st.session_state.idx = idx
                        st.rerun()
        
        st.write("---")
        if not st.session_state.finish:
            if st.button("🏁 SINAVI BİTİR", type="primary"):
                st.session_state.finish = True
                st.rerun()
        
        # LİDERLİK TABLOSU
        st.markdown("### 🏆 Liderlik Tablosu")
        lb = get_leaderboard()
        if lb is not None: st.dataframe(lb[['Kullanıcı','Puan']], use_container_width=True, hide_index=False)

    # --- ANA EKRAN ---
    if not st.session_state.finish:
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"## 📝 Soru {st.session_state.idx + 1} / {len(df)}")
        is_marked = st.session_state.idx in st.session_state.marked
        if c2.button("🏳️ Kaldır" if is_marked else "🚩 İşaretle"):
            if is_marked: st.session_state.marked.remove(st.session_state.idx)
            else: st.session_state.marked.add(st.session_state.idx)
            st.rerun()

        row = df.iloc[st.session_state.idx]
        passage, stem = parse_question(row['Soru'])
        opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
        
        if passage:
            c_l, c_r = st.columns(2)
            c_l.markdown(f"#### 📖 Okuma Parçası\n<div class='passage-box'>{format_markdown_to_html(passage)}</div>", unsafe_allow_html=True)
            with c_r:
                st.markdown(f"<div class='question-stem'>{format_markdown_to_html(stem)}</div>", unsafe_allow_html=True)
                sel = st.radio("Cevap:", opts, index=next((i for i,v in enumerate(opts) if v.startswith(st.session_state.answers.get(st.session_state.idx, "")+")")), None), key=f"rad_{st.session_state.idx}")
                if sel: 
                    st.session_state.answers[st.session_state.idx] = sel.split(")")[0]
                    if sel.split(")")[0] == row['Dogru_Cevap']: st.success("TEBRİKLER! 🎉")
                    else: st.error(f"YANLIŞ. Cevap: {row['Dogru_Cevap']}")
        else:
            st.markdown(f"<div class='question-stem'>{format_markdown_to_html(stem)}</div>", unsafe_allow_html=True)
            sel = st.radio("Cevap:", opts, index=next((i for i,v in enumerate(opts) if v.startswith(st.session_state.answers.get(st.session_state.idx, "")+")")), None), key=f"rad_{st.session_state.idx}")
            if sel:
                st.session_state.answers[st.session_state.idx] = sel.split(")")[0]
                if sel.split(")")[0] == row['Dogru_Cevap']: st.success("TEBRİKLER! 🎉")
                else: st.error(f"YANLIŞ. Cevap: {row['Dogru_Cevap']}")

        # BUTONLAR
        st.write("")
        if st.button("🤖 Çözümle ve Seslendir 🔊", use_container_width=True):
            if not user_api_key: st.error("API Anahtarı Gerekli!")
            else:
                with st.spinner("Analiz ediliyor..."):
                    txt = get_gemini_text(user_api_key, passage, stem, opts)
                    st.session_state.gemini_res[st.session_state.idx] = {'text': txt, 'audio': None}
                    st.rerun()
        
        c_p, c_n = st.columns(2)
        if st.session_state.idx > 0 and c_p.button("⬅️ Önceki"): 
            st.session_state.idx -= 1
            st.rerun()
        if st.session_state.idx < len(df)-1 and c_n.button("Sonraki ➡️"): 
            st.session_state.idx += 1
            st.rerun()

        if st.session_state.idx in st.session_state.gemini_res:
            res = st.session_state.gemini_res[st.session_state.idx]
            st.markdown("---")
            if res['audio']: st.audio(res['audio'])
            st.markdown(res['text']) # Basit gösterim, detaylısı yukarıdaki kodda var
            if not res['audio']:
                with st.spinner("Ses oluşturuluyor..."):
                    aud = generate_parallel_audio(res['text'])
                    if aud: 
                        st.session_state.gemini_res[st.session_state.idx]['audio'] = aud
                        st.rerun()
    else:
        # --- SONUÇ EKRANI VE YAPAY ZEKA ANALİZİ ---
        st.title("📊 Sınav Sonuç Analizi")
        st.markdown("---")
        
        correct, wrong, empty = 0, 0, 0
        wrong_questions_text = "" # Yanlış soruları burada biriktireceğiz
        
        results_data = []
        for i in range(len(df)):
            ans = st.session_state.answers.get(i)
            real = df.iloc[i]['Dogru_Cevap']
            if ans:
                if ans == real: 
                    correct += 1
                    status = "DOĞRU"
                else: 
                    wrong += 1
                    status = "YANLIŞ"
                    # Yanlış sorunun metnini al (çok uzunsa kısalt)
                    q_text = str(df.iloc[i]['Soru'])[:300] 
                    wrong_questions_text += f"- Soru {i+1}: {q_text}...\n"
            else: 
                empty += 1
                status = "BOŞ"
                q_text = str(df.iloc[i]['Soru'])[:300]
                wrong_questions_text += f"- Soru {i+1} (BOŞ): {q_text}...\n"
            
            results_data.append({"No": i+1, "Cevap": ans if ans else "-", "Doğru": real, "Durum": status})

        score = correct * 1.25
        if not st.session_state.data_saved:
            save_score_to_csv(st.session_state.username, score, correct, wrong, empty)
            st.session_state.data_saved = True
            st.toast("Kaydedildi!", icon="💾")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Puan", f"{score:.2f}")
        c2.metric("Doğru", correct)
        c3.metric("Yanlış", wrong)
        c4.metric("Boş", empty)
        
        st.markdown("---")
        
        # --- YAPAY ZEKA PERFORMANS ANALİZİ BUTONU ---
        st.subheader("🤖 Yapay Zeka Koçluk Sistemi")
        st.info("Sonuçlarınıza göre eksik konularınızı tespit etmek için aşağıdaki butona basın.")
        
        if st.button("✨ Performansımı Analiz Et", type="primary", use_container_width=True):
            if not user_api_key:
                st.error("Lütfen önce sol menüden API Anahtarınızı giriniz.")
            else:
                score_info = f"Doğru: {correct}, Yanlış: {wrong}, Boş: {empty}, Puan: {score}"
                with st.spinner("🧠 Yapay Zeka yanlış yaptığın soruları inceliyor ve eksiklerini tespit ediyor..."):
                    # Analiz fonksiyonunu çağır
                    analysis = generate_performance_analysis(user_api_key, wrong_questions_text, score_info)
                    st.session_state.analysis_report = analysis
        
        # Rapor varsa göster
        if st.session_state.analysis_report:
            st.markdown(f"<div class='analysis-report'>{format_markdown_to_html(st.session_state.analysis_report)}</div>", unsafe_allow_html=True)
            
        st.markdown("---")
        st.subheader("Detaylı Tablo")
        res_df = pd.DataFrame(results_data)
        st.dataframe(res_df.style.map(lambda v: f'color: {"green" if v=="DOĞRU" else "red" if v=="YANLIŞ" else "orange"}; font-weight: bold;', subset=['Durum']), use_container_width=True)
        
        if st.button("🔄 YENİ SINAV BAŞLAT"):
            st.session_state.answers = {}
            st.session_state.marked = set()
            st.session_state.idx = 0
            st.session_state.finish = False
            st.session_state.data_saved = False
            st.session_state.analysis_report = None
            st.session_state.gemini_res = {}
            st.rerun()
else:
    st.error("Dosya yüklenemedi.")
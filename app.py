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
st.set_page_config(page_title="YDS Pro", page_icon="🎓", layout="wide")

# --- 2. PREMIUM CSS TASARIMI (MODERN GİRİŞ & SİMETRİK BUTONLAR) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    .stApp { font-family: 'Poppins', sans-serif; background-color: #f8f9fa; }
    
    /* GİRİŞ EKRANI KARTI */
    .login-container {
        max-width: 500px;
        margin: 100px auto;
        padding: 40px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        text-align: center;
        border: 1px solid #eef2f6;
    }
    
    .login-title {
        color: #2c3e50;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 10px;
    }
    
    .login-subtitle {
        color: #7f8c8d;
        font-size: 14px;
        margin-bottom: 30px;
    }
    
    /* SORU BUTONLARI İÇİN IZGARA (GRID) SİSTEMİ - HEPİSİ EŞİT */
    .question-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr); /* Yan yana 5 tane */
        gap: 8px; /* Aralarındaki boşluk */
        margin-bottom: 20px;
    }
    
    .grid-btn {
        width: 100%;
        aspect-ratio: 1/1; /* Kare olması için */
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        background: white;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 14px;
        color: #555;
    }
    
    .grid-btn:hover {
        background-color: #f0f2f5;
        border-color: #bdc3c7;
    }
    
    .grid-btn.active {
        background-color: #3498db;
        color: white;
        border-color: #2980b9;
        box-shadow: 0 4px 10px rgba(52, 152, 219, 0.3);
    }
    
    .grid-btn.correct { background-color: #eafaf1; color: #27ae60; border-color: #2ecc71; }
    .grid-btn.wrong { background-color: #fdedec; color: #c0392b; border-color: #e74c3c; }
    .grid-btn.marked { background-color: #fff8e1; color: #f39c12; border-color: #f1c40f; }

    /* OKUMA PARÇASI */
    .passage-box { 
        background-color: #ffffff; padding: 30px; border-radius: 12px; height: 60vh; 
        overflow-y: auto; font-size: 17px; font-weight: 500; line-height: 2.0; 
        text-align: justify; border: 1px solid #dfe6e9; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        color: #2d3436; font-family: 'Georgia', serif; 
    }
    
    /* SORU KÖKÜ */
    .question-stem { 
        font-size: 19px; font-weight: 700; background-color: #ffffff; padding: 25px; 
        border-radius: 12px; border-left: 6px solid #0984e3; margin-bottom: 25px; 
        color: #1e272e; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* STANDART BUTONLAR */
    div.stButton > button {
        width: 100%; border-radius: 10px; font-weight: 600; height: 45px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* ANALİZ RAPORU KUTUSU */
    .analysis-report {
        background-color: #fff; border: 2px solid #6c5ce7; border-radius: 15px;
        padding: 25px; margin-top: 20px; box-shadow: 0 5px 15px rgba(108, 92, 231, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- 3. VERİ YÜKLEME VE CSV İŞLEMLERİ ---
SCORES_FILE = "sinav_sonuclari.csv"

def save_score_to_csv(username, score, correct, wrong, empty):
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_data = {"Tarih": [date_str], "Kullanıcı": [username], "Puan": [score], "Doğru": [correct], "Yanlış": [wrong], "Boş": [empty]}
    new_df = pd.DataFrame(new_data)
    if os.path.exists(SCORES_FILE):
        try:
            existing_df = pd.read_csv(SCORES_FILE)
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            updated_df.to_csv(SCORES_FILE, index=False)
        except: new_df.to_csv(SCORES_FILE, index=False)
    else: new_df.to_csv(SCORES_FILE, index=False)

def get_leaderboard():
    if os.path.exists(SCORES_FILE):
        try:
            df = pd.read_csv(SCORES_FILE)
            df = df.sort_values(by="Puan", ascending=False).reset_index(drop=True)
            df.index = df.index + 1
            return df
        except: return None
    return None

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
    if 'analysis_report' not in st.session_state: st.session_state.analysis_report = None

df = load_data()
init_session()

# --- 4. PROFESYONEL GİRİŞ EKRANI ---
if st.session_state.username is None:
    # Boşluklarla ortala
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="login-container">
            <img src="https://cdn-icons-png.flaticon.com/512/3406/3406987.png" width="80" style="margin-bottom: 15px;">
            <div class="login-title">YDS Hazırlık Koçu</div>
            <div class="login-subtitle">Yapay Zeka Destekli Sınav Analiz Sistemi</div>
        </div>
        """, unsafe_allow_html=True)
        
        name_input = st.text_input("Adınız Soyadınız", placeholder="Örn: Ahmet Yılmaz")
        
        if st.button("🚀 Sınava Başla", type="primary", use_container_width=True):
            if name_input.strip():
                st.session_state.username = name_input.strip()
                st.rerun()
            else:
                st.toast("Lütfen adınızı giriniz!", icon="⚠️")
    
    st.stop() # İsim girilmeden aşağıyı çalıştırma

# --- 5. FONKSİYONLAR ---
def parse_question(text):
    if pd.isna(text): return None, "..."
    text = str(text).replace('\\n', '\n')
    parts = text.split('\n\n', 1) if '\n\n' in text else (None, text.strip())
    return parts[0].strip() if parts[0] else None, parts[1].strip()

def get_gemini_text(api_key, passage, question, options):
    if not api_key: return "⚠️ API Key Yok."
    # API Key temizliği (Boşlukları sil)
    clean_key = api_key.strip()
    try:
        genai.configure(api_key=clean_key)
        # Kararlı model
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Sen YDS koçusun. PARAGRAF: {passage} SORU: {question} ŞIKLAR: {options}. Cevabı [BÖLÜM 1: STRATEJİ], [BÖLÜM 2: ANALİZ], [BÖLÜM 3: DOĞRU CEVAP], [BÖLÜM 4: ÇELDİRİCİLER] formatında ver."
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"HATA: {str(e)} (API Key'i kontrol edin)"

def generate_performance_analysis(api_key, wrong_questions_text, score_info):
    clean_key = api_key.strip()
    try:
        genai.configure(api_key=clean_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Sen profesyonel bir YDS eğitmenisin.
        Sonuç: {score_info}
        Yanlışlar: {wrong_questions_text}
        Lütfen Türkçe olarak; Genel Değerlendirme, Eksik Konular, Çalışma Tavsiyeleri ve Motivasyon başlıkları altında analiz et.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Analiz hatası: {str(e)}"

# Formatlayıcılar
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
    except: return b""

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

# --- 6. UYGULAMA GÖVDESİ ---
if df is not None:
    with st.sidebar:
        st.success(f"👤 **{st.session_state.username}**")
        
        # SAYAÇ
        components.html(f"""<div style="font-family:'Segoe UI',sans-serif;font-size:28px;font-weight:bold;color:#e74c3c;background:white;padding:10px;border-radius:10px;text-align:center;border:2px solid #e74c3c;">...</div><script>var dest={st.session_state.end_timestamp};setInterval(function(){{var now=new Date().getTime();var diff=dest-now;var h=Math.floor((diff%(1000*60*60*24))/(1000*60*60));var m=Math.floor((diff%(1000*60*60))/(1000*60));var s=Math.floor((diff%(1000*60))/1000);document.querySelector("div").innerHTML=(h<10?"0"+h:h)+":"+(m<10?"0"+m:m)+":"+(s<10?"0"+s:s);}},1000);</script>""", height=70)
        
        st.write("---")
        st.info("🔑 **Kendi API Anahtarınız**")
        user_api_key = st.text_input("Google AI Studio Key:", type="password", help="Hata alırsanız anahtarın başında/sonunda boşluk olmadığından emin olun.")
        
        st.write("---")
        st.markdown("### 🗺️ Soru Haritası")
        
        # --- YENİ EŞİT BOYUTLU IZGARA SİSTEMİ (GRID) ---
        # Streamlit'in kendi columns'u yerine HTML/CSS Grid kullanıyoruz.
        # Bu sayede hepsi %100 eşit kutucuklar oluyor.
        
        # HTML kodunu oluştur
        grid_html = '<div class="question-grid">'
        for i in range(len(df)):
            status_class = ""
            u_ans = st.session_state.answers.get(i)
            c_ans = df.iloc[i]['Dogru_Cevap']
            
            # Renk Sınıfları
            if u_ans:
                if u_ans == c_ans: status_class = "correct"
                else: status_class = "wrong"
            elif i in st.session_state.marked: status_class = "marked"
            if i == st.session_state.idx: status_class += " active"
            
            # Tıklanabilir buton (Streamlit butonları yerine HTML butonları simüle edemiyoruz, 
            # bu yüzden Streamlit kolonlarını daha sıkı bir döngüyle kullanacağız)
            pass 
        
        # Streamlit'in native kolonlarıyla en düzgün grid yapısı:
        # 5'li gruplar halinde döneceğiz ve her kolon eşit olacak.
        chunk_size = 5
        for i in range(0, len(df), chunk_size):
            cols = st.columns(chunk_size) # Eşit genişlikte 5 kolon
            for j in range(chunk_size):
                if i + j < len(df):
                    q_idx = i + j
                    # Buton Etiketi
                    lbl = str(q_idx + 1)
                    u_ans = st.session_state.answers.get(q_idx)
                    
                    if u_ans:
                        lbl = "✅" if u_ans == df.iloc[q_idx]['Dogru_Cevap'] else "❌"
                    elif q_idx in st.session_state.marked:
                        lbl = "⭐"
                    
                    # Aktif buton tipi
                    b_type = "primary" if q_idx == st.session_state.idx else "secondary"
                    
                    # Butonu çiz
                    if cols[j].button(lbl, key=f"nav_{q_idx}", type=b_type, use_container_width=True):
                        st.session_state.idx = q_idx
                        st.rerun()
        
        st.write("---")
        if not st.session_state.finish:
            if st.button("🏁 SINAVI BİTİR", type="primary"):
                st.session_state.finish = True
                st.rerun()
        
        st.markdown("### 🏆 Liderlik Tablosu")
        lb = get_leaderboard()
        if lb is not None: st.dataframe(lb[['Kullanıcı','Puan']], use_container_width=True, hide_index=False)

    # --- ANA EKRAN ---
    if not st.session_state.finish:
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"## 📝 Soru {st.session_state.idx + 1} / {len(df)}")
        is_marked = st.session_state.idx in st.session_state.marked
        if c2.button("🏳️ Kaldır" if is_marked else "🚩 İşaretle", use_container_width=True):
            if is_marked: st.session_state.marked.remove(st.session_state.idx)
            else: st.session_state.marked.add(st.session_state.idx)
            st.rerun()

        row = df.iloc[st.session_state.idx]
        passage, stem = parse_question(row['Soru'])
        opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
        
        # Okuma Parçası ve Soru Yan Yana
        if passage:
            c_l, c_r = st.columns([1, 1], gap="medium")
            with c_l:
                st.markdown("#### 📖 Okuma Parçası")
                st.markdown(f"<div class='passage-box'>{format_markdown_to_html(passage)}</div>", unsafe_allow_html=True)
            with c_r:
                st.markdown(f"<div class='question-stem'>{format_markdown_to_html(stem)}</div>", unsafe_allow_html=True)
                sel_idx = next((i for i,v in enumerate(opts) if v.startswith(st.session_state.answers.get(st.session_state.idx, "")+")")), None)
                sel = st.radio("Cevabınız:", opts, index=sel_idx, key=f"rad_{st.session_state.idx}")
                
                if sel: 
                    st.session_state.answers[st.session_state.idx] = sel.split(")")[0]
                    if sel.split(")")[0] == row['Dogru_Cevap']: st.success("DOĞRU CEVAP! 🎉")
                    else: st.error(f"YANLIŞ! Doğru: {row['Dogru_Cevap']}")
        else:
            st.markdown(f"<div class='question-stem'>{format_markdown_to_html(stem)}</div>", unsafe_allow_html=True)
            sel_idx = next((i for i,v in enumerate(opts) if v.startswith(st.session_state.answers.get(st.session_state.idx, "")+")")), None)
            sel = st.radio("Cevabınız:", opts, index=sel_idx, key=f"rad_{st.session_state.idx}")
            if sel:
                st.session_state.answers[st.session_state.idx] = sel.split(")")[0]
                if sel.split(")")[0] == row['Dogru_Cevap']: st.success("DOĞRU CEVAP! 🎉")
                else: st.error(f"YANLIŞ! Doğru: {row['Dogru_Cevap']}")

        st.write("")
        c_act1, c_act2 = st.columns([2, 1])
        with c_act1:
            if st.button("🤖 Çözümle ve Seslendir 🔊", use_container_width=True):
                if not user_api_key: st.error("Lütfen sol menüden API Key giriniz!")
                else:
                    with st.spinner("Yapay Zeka Analiz Ediyor..."):
                        txt = get_gemini_text(user_api_key, passage, stem, opts)
                        st.session_state.gemini_res[st.session_state.idx] = {'text': txt, 'audio': None}
                        st.rerun()
        
        # İleri-Geri Butonları
        c_prev, c_next = st.columns(2)
        if st.session_state.idx > 0 and c_prev.button("⬅️ Önceki", use_container_width=True): 
            st.session_state.idx -= 1
            st.rerun()
        if st.session_state.idx < len(df)-1 and c_next.button("Sonraki ➡️", use_container_width=True): 
            st.session_state.idx += 1
            st.rerun()

        # Analiz Sonucu Gösterimi
        if st.session_state.idx in st.session_state.gemini_res:
            res = st.session_state.gemini_res[st.session_state.idx]
            st.markdown("---")
            if res['audio']: st.audio(res['audio'])
            
            # Metni parçalayıp güzel gösterme
            parts = res['text'].split('[BÖLÜM')
            for part in parts:
                if "1: STRATEJİ" in part:
                    st.markdown(f"<div class='strategy-box'><b>STRATEJİ:</b> {format_markdown_to_html(part.replace('1: STRATEJİ VE MANTIK]', ''))}</div>", unsafe_allow_html=True)
                elif "2: CÜMLE" in part:
                    st.markdown(f"<div class='sentence-box'><b>ANALİZ:</b> {format_markdown_to_html(part.replace('2: CÜMLE ANALİZİ]', ''))}</div>", unsafe_allow_html=True)
                # Diğer bölümler için de benzer kutular eklenebilir...
            
            if not res['audio']:
                with st.spinner("Ses oluşturuluyor..."):
                    aud = generate_parallel_audio(res['text'])
                    if aud: 
                        st.session_state.gemini_res[st.session_state.idx]['audio'] = aud
                        st.rerun()
    else:
        # --- SONUÇ EKRANI ---
        st.title("📊 Sınav Sonuç Analizi")
        st.markdown("---")
        
        correct, wrong, empty = 0, 0, 0
        wrong_questions_text = ""
        
        results_data = []
        for i in range(len(df)):
            ans = st.session_state.answers.get(i)
            real = df.iloc[i]['Dogru_Cevap']
            status = "BOŞ"
            if ans:
                if ans == real: 
                    correct += 1
                    status = "DOĞRU"
                else: 
                    wrong += 1
                    status = "YANLIŞ"
                    q_text = str(df.iloc[i]['Soru'])[:300] 
                    wrong_questions_text += f"- Soru {i+1}: {q_text}...\n"
            else: 
                empty += 1
                q_text = str(df.iloc[i]['Soru'])[:300]
                wrong_questions_text += f"- Soru {i+1} (BOŞ): {q_text}...\n"
            
            results_data.append({"No": i+1, "Cevap": ans if ans else "-", "Doğru": real, "Durum": status})

        score = correct * 1.25
        if not st.session_state.data_saved:
            save_score_to_csv(st.session_state.username, score, correct, wrong, empty)
            st.session_state.data_saved = True
            st.balloons()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Puan", f"{score:.2f}")
        c2.metric("Doğru", correct)
        c3.metric("Yanlış", wrong)
        c4.metric("Boş", empty)
        
        st.markdown("---")
        
        st.subheader("🤖 Yapay Zeka Koçluk Sistemi")
        st.info("Eksiklerinizi analiz etmek için butona basın (API Key girili olmalı).")
        
        if st.button("✨ Performansımı Analiz Et", type="primary", use_container_width=True):
            if not user_api_key: st.error("Lütfen sol menüden API Key giriniz.")
            else:
                with st.spinner("Analiz yapılıyor..."):
                    score_info = f"Doğru: {correct}, Yanlış: {wrong}, Boş: {empty}, Puan: {score}"
                    analysis = generate_performance_analysis(user_api_key, wrong_questions_text, score_info)
                    st.session_state.analysis_report = analysis
        
        if st.session_state.analysis_report:
            st.markdown(f"<div class='analysis-report'>{format_markdown_to_html(st.session_state.analysis_report)}</div>", unsafe_allow_html=True)
            
        st.markdown("---")
        st.subheader("Detaylı Tablo")
        res_df = pd.DataFrame(results_data)
        st.dataframe(res_df.style.map(lambda v: f'color: {"green" if v=="DOĞRU" else "red" if v=="YANLIŞ" else "orange"}; font-weight: bold;', subset=['Durum']), use_container_width=True)
        
        if st.button("🔄 YENİ SINAV BAŞLAT", type="secondary", use_container_width=True):
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
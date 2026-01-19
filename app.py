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
st.set_page_config(page_title="YDS Pro LMS", page_icon="🎓", layout="wide")

# --- 2. PREMIUM CSS TASARIMI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    .stApp { font-family: 'Poppins', sans-serif; background-color: #f4f6f9; }
    
    /* GİRİŞ EKRANI */
    .login-container {
        max-width: 500px; margin: 80px auto; padding: 40px;
        background: white; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.08);
        text-align: center; border: 1px solid #eef2f6;
    }
    .login-title { color: #2c3e50; font-size: 28px; font-weight: 700; margin-bottom: 10px; }
    
    /* SINAV KARTLARI (GRID) */
    .exam-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; margin-top: 20px; }
    .exam-card {
        background: white; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px;
        text-align: center; cursor: pointer; transition: all 0.3s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .exam-card:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); border-color: #3498db; }
    .exam-card.active { background-color: #e3f2fd; border-color: #2196f3; color: #1565c0; font-weight: bold; }

    /* SORU NAVİGASYON BUTONLARI */
    div.stButton > button {
        width: 100%; border-radius: 8px; font-weight: 600; height: 45px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: all 0.2s;
    }
    
    /* OKUMA PARÇASI & SORU */
    .passage-box { 
        background-color: #ffffff; padding: 30px; border-radius: 12px; height: 60vh; 
        overflow-y: auto; font-size: 16px; line-height: 1.8; 
        border: 1px solid #dfe6e9; color: #2d3436; font-family: 'Georgia', serif; 
    }
    .question-stem { 
        font-size: 18px; font-weight: 600; background-color: #ffffff; padding: 25px; 
        border-radius: 12px; border-left: 5px solid #0984e3; margin-bottom: 25px; 
        color: #1e272e; box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    }
    
    /* ANALİZ RAPORU */
    .analysis-report {
        background-color: #fff; border: 2px solid #6c5ce7; border-radius: 15px;
        padding: 25px; margin-top: 20px; box-shadow: 0 5px 15px rgba(108, 92, 231, 0.1);
    }
    
    /* LİDERLİK TABLOSU ÖZELLEŞTİRME */
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

# --- 3. VERİ YÖNETİMİ (KAYIT & LİDERLİK) ---
SCORES_FILE = "lms_scores.csv"

def save_score_to_csv(username, exam_name, score, correct, wrong, empty):
    """
    Kullanıcının o sınavdaki SON sonucunu günceller.
    """
    # Mevcut veriyi oku veya oluştur
    if os.path.exists(SCORES_FILE):
        try:
            df = pd.read_csv(SCORES_FILE)
        except:
            df = pd.DataFrame(columns=["Kullanıcı", "Sınav", "Puan", "Doğru", "Yanlış", "Boş", "Tarih"])
    else:
        df = pd.DataFrame(columns=["Kullanıcı", "Sınav", "Puan", "Doğru", "Yanlış", "Boş", "Tarih"])

    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # KONTROL: Bu kullanıcı bu sınava daha önce girmiş mi?
    # Filtre: Kullanıcı Adı VE Sınav Adı eşleşiyor mu?
    mask = (df["Kullanıcı"] == username) & (df["Sınav"] == exam_name)
    
    if mask.any():
        # Varsa GÜNCELLE (Satırı bul ve değerleri değiştir)
        df.loc[mask, ["Puan", "Doğru", "Yanlış", "Boş", "Tarih"]] = [score, correct, wrong, empty, date_str]
    else:
        # Yoksa YENİ EKLE
        new_row = pd.DataFrame({
            "Kullanıcı": [username],
            "Sınav": [exam_name],
            "Puan": [score],
            "Doğru": [correct],
            "Yanlış": [wrong],
            "Boş": [empty],
            "Tarih": [date_str]
        })
        df = pd.concat([df, new_row], ignore_index=True)
    
    # Kaydet
    df.to_csv(SCORES_FILE, index=False)

def get_leaderboard_pivot():
    """
    Veriyi 'Pivot Table' formatına çevirir.
    Satırlar: Kullanıcılar
    Sütunlar: Sınavlar
    Değerler: Puanlar
    """
    if not os.path.exists(SCORES_FILE):
        return None
    
    try:
        df = pd.read_csv(SCORES_FILE)
        if df.empty: return None
        
        # Pivot işlemi (Satır: Kullanıcı, Sütun: Sınav, Değer: Puan)
        pivot_df = df.pivot_table(index="Kullanıcı", columns="Sınav", values="Puan", aggfunc="max")
        
        # NaN (Girilmeyen sınavlar) yerine "-" koy
        pivot_df = pivot_df.fillna("-")
        
        # Toplam Puanı Hesapla (Sıralama için opsiyonel)
        # Sadece sayısal değerleri topla
        numeric_df = pivot_df.replace("-", 0)
        pivot_df["ORTALAMA"] = numeric_df.mean(axis=1).round(2)
        
        # Ortalamaya göre sırala
        pivot_df = pivot_df.sort_values(by="ORTALAMA", ascending=False)
        
        return pivot_df
    except:
        return None

# --- 4. EXCEL DOSYA YÖNETİCİSİ ---
@st.cache_data
def load_exam_data(exam_id):
    """
    Seçilen sınava göre (1, 2... 10) ilgili Excel dosyasını yükler.
    Dosya adları: Sinav_1.xlsx, Sinav_2.xlsx ... şeklinde olmalı.
    """
    # Dosya adı formatı
    file_name = f"Sinav_{exam_id}.xlsx"
    
    # Eğer dosya yoksa (Kullanıcı henüz yüklememişse)
    if not os.path.exists(file_name):
        # Geliştirme aşamasında senin elindeki dosyayı "Sinav_1" varsayalım
        if exam_id == 1 and os.path.exists("YDS1_ingilizce (2).xlsx - Table 1.csv"):
             try:
                 df = pd.read_csv("YDS1_ingilizce (2).xlsx - Table 1.csv")
                 return df
             except: pass
        return None # Dosya bulunamadı

    try:
        # Önce Excel dene
        df = pd.read_excel(file_name, engine="openpyxl")
    except:
        try:
            # Olmazsa CSV dene
            df = pd.read_csv(file_name)
        except:
            return None

    # Kolon temizliği
    df.columns = df.columns.str.strip()
    if 'Dogru_Cevap' in df.columns:
        df['Dogru_Cevap'] = df['Dogru_Cevap'].astype(str).str.strip().str.upper()
    
    return df

def init_session():
    if 'username' not in st.session_state: st.session_state.username = None
    if 'selected_exam_id' not in st.session_state: st.session_state.selected_exam_id = 1
    
    # Her sınav değiştiğinde sıfırlanması gerekenler
    if 'exam_data' not in st.session_state: st.session_state.exam_data = None
    if 'idx' not in st.session_state: st.session_state.idx = 0
    if 'answers' not in st.session_state: st.session_state.answers = {}
    if 'marked' not in st.session_state: st.session_state.marked = set()
    if 'end_timestamp' not in st.session_state: st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000 
    if 'finish' not in st.session_state: st.session_state.finish = False
    if 'data_saved' not in st.session_state: st.session_state.data_saved = False 
    if 'gemini_res' not in st.session_state: st.session_state.gemini_res = {} 
    if 'analysis_report' not in st.session_state: st.session_state.analysis_report = None
    if 'user_api_key' not in st.session_state: st.session_state.user_api_key = ""

init_session()

# --- 5. GİRİŞ EKRANI ---
if st.session_state.username is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="login-container">
            <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" width="80" style="margin-bottom: 15px;">
            <div class="login-title">YDS Eğitim Platformu</div>
            <div class="login-subtitle">10 Adet Deneme Sınavı ve Yapay Zeka Analizi</div>
        </div>
        """, unsafe_allow_html=True)
        name_input = st.text_input("Adınız Soyadınız", placeholder="Örn: Mehmet Demir")
        if st.button("🚀 Giriş Yap", type="primary", use_container_width=True):
            if name_input.strip():
                st.session_state.username = name_input.strip()
                st.rerun()
            else: st.toast("Lütfen adınızı giriniz!", icon="⚠️")
    st.stop() 

# --- 6. SINAV SEÇİM MANTIĞI ---
# Kullanıcı giriş yaptıysa Sidebar'da Sınav Seçici ve Bilgiler
with st.sidebar:
    st.success(f"👤 **{st.session_state.username}**")
    
    # 1'den 10'a kadar Sınav Seçimi
    st.markdown("### 📚 Sınav Seçimi")
    exam_options = {i: f"YDS Deneme {i}" for i in range(1, 11)}
    
    # Selectbox ile seçim (Daha temiz görünür)
    selected_id = st.selectbox(
        "Lütfen bir sınav seçin:",
        options=list(exam_options.keys()),
        format_func=lambda x: exam_options[x],
        index=st.session_state.selected_exam_id - 1
    )
    
    # Eğer sınav değiştiyse her şeyi sıfırla ve yeni veriyi yükle
    if selected_id != st.session_state.selected_exam_id:
        st.session_state.selected_exam_id = selected_id
        st.session_state.answers = {}
        st.session_state.marked = set()
        st.session_state.idx = 0
        st.session_state.finish = False
        st.session_state.data_saved = False
        st.session_state.gemini_res = {}
        st.session_state.analysis_report = None
        st.rerun()

    # Veriyi Yükle
    df = load_exam_data(st.session_state.selected_exam_id)
    
    st.write("---")
    
    # Sayaç
    components.html(f"""<div style="font-family:'Segoe UI',sans-serif;font-size:24px;font-weight:bold;color:#e74c3c;background:white;padding:5px;border-radius:10px;text-align:center;border:2px solid #e74c3c;">...</div><script>var dest={st.session_state.end_timestamp};setInterval(function(){{var now=new Date().getTime();var diff=dest-now;var h=Math.floor((diff%(1000*60*60*24))/(1000*60*60));var m=Math.floor((diff%(1000*60*60))/(1000*60));var s=Math.floor((diff%(1000*60))/1000);document.querySelector("div").innerHTML=(h<10?"0"+h:h)+":"+(m<10?"0"+m:m)+":"+(s<10?"0"+s:s);}},1000);</script>""", height=60)
    
    st.write("---")
    # API Key
    temp_key = st.text_input("Google AI Key:", type="password", value=st.session_state.user_api_key)
    if st.button("💾 Kaydet", use_container_width=True):
        if temp_key.strip():
            st.session_state.user_api_key = temp_key.strip()
            st.success("Kaydedildi!")
    
    st.write("---")
    
    # EĞER DOSYA YOKSA UYARI VER
    if df is None:
        st.error(f"⚠️ YDS Deneme {st.session_state.selected_exam_id} dosyası bulunamadı.")
        st.info("Lütfen 'Sinav_X.xlsx' dosyasını klasöre ekleyin.")
    else:
        # SORU HARİTASI (Sadece dosya varsa göster)
        st.markdown("### 🗺️ Soru Haritası")
        chunk_size = 5
        for i in range(0, len(df), chunk_size):
            cols = st.columns(chunk_size)
            for j in range(chunk_size):
                if i + j < len(df):
                    q_idx = i + j
                    u_ans = st.session_state.answers.get(q_idx)
                    
                    # ETİKET: Numara + Durum
                    if u_ans:
                        is_correct = (u_ans == df.iloc[q_idx]['Dogru_Cevap'])
                        icon = "✅" if is_correct else "❌"
                        lbl = f"{q_idx + 1} {icon}"
                    elif q_idx in st.session_state.marked:
                        lbl = f"{q_idx + 1} ⭐"
                    else:
                        lbl = str(q_idx + 1)
                    
                    b_type = "primary" if q_idx == st.session_state.idx else "secondary"
                    
                    if cols[j].button(lbl, key=f"nav_{q_idx}", type=b_type, use_container_width=True):
                        st.session_state.idx = q_idx
                        st.rerun()

        st.write("---")
        if not st.session_state.finish:
            if st.button("🏁 SINAVI BİTİR", type="primary"):
                st.session_state.finish = True
                st.rerun()

# --- 7. YARDIMCI FONKSİYONLAR ---
def parse_question(text):
    if pd.isna(text): return None, "..."
    text = str(text).replace('\\n', '\n')
    parts = text.split('\n\n', 1) if '\n\n' in text else (None, text.strip())
    return parts[0].strip() if parts[0] else None, parts[1].strip()

def get_gemini_text(api_key, passage, question, options):
    if not api_key: return "⚠️ API Key Yok."
    clean_key = api_key.strip()
    try:
        genai.configure(api_key=clean_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Sen YDS koçusun. PARAGRAF: {passage} SORU: {question} ŞIKLAR: {options}
        Cevabı ETİKETLERİ BOZMADAN: [BÖLÜM 1: STRATEJİ], [BÖLÜM 2: ANALİZ], [BÖLÜM 3: DOĞRU CEVAP], [BÖLÜM 4: ÇELDİRİCİLER] formatında ver.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"HATA: {str(e)}"

def generate_performance_analysis(api_key, wrong_questions_text, score_info):
    clean_key = api_key.strip()
    try:
        genai.configure(api_key=clean_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Sen YDS eğitmenisin. Sonuç: {score_info} Yanlışlar: {wrong_questions_text}. Türkçe olarak; Genel Değerlendirme, Eksik Konular, Tavsiyeler ve Motivasyon başlıklarında analiz et."
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Analiz hatası: {str(e)}"

def format_html(text):
    if not text: return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    return re.sub(r'\*(.*?)\*', r'<b>\1</b>', text)

def clean_tts(text):
    text = text.replace('**', '').replace('*', '')
    return re.sub(r'[\#\_\`]', '', text).strip()

async def gen_audio(text):
    if not text.strip(): return b""
    try:
        c = edge_tts.Communicate(clean_tts(text), "en-US-BrianMultilingualNeural")
        await c.save("temp.mp3")
        with open("temp.mp3", "rb") as f: d = f.read()
        os.remove("temp.mp3")
        return d
    except: return b""

def get_audio_sync(text):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(gen_audio(text))
    except: return None

# --- 8. ANA EKRAN MANTIĞI ---

# Dosya Yüklenmemişse Durdur
if df is None:
    st.markdown(f"""
    <div style="text-align:center; margin-top:50px;">
        <h2>📂 Dosya Eksik</h2>
        <p><b>YDS Deneme {st.session_state.selected_exam_id}</b> için soru dosyası bulunamadı.</p>
        <p>Lütfen uygulama klasörüne <code>Sinav_{st.session_state.selected_exam_id}.xlsx</code> dosyasını ekleyin.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not st.session_state.finish:
    # SINAV ARAYÜZÜ
    c1, c2 = st.columns([3, 1])
    c1.markdown(f"## 📝 {exam_options[st.session_state.selected_exam_id]} - Soru {st.session_state.idx + 1}")
    
    is_marked = st.session_state.idx in st.session_state.marked
    if c2.button("🏳️ Kaldır" if is_marked else "🚩 İşaretle", use_container_width=True):
        if is_marked: st.session_state.marked.remove(st.session_state.idx)
        else: st.session_state.marked.add(st.session_state.idx)
        st.rerun()

    row = df.iloc[st.session_state.idx]
    passage, stem = parse_question(row['Soru'])
    opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
    
    if passage:
        c_l, c_r = st.columns([1, 1], gap="medium")
        c_l.markdown(f"#### 📖 Okuma Parçası\n<div class='passage-box'>{format_html(passage)}</div>", unsafe_allow_html=True)
        with c_r:
            st.markdown(f"<div class='question-stem'>{format_html(stem)}</div>", unsafe_allow_html=True)
            sel_idx = next((i for i,v in enumerate(opts) if v.startswith(st.session_state.answers.get(st.session_state.idx, "")+")")), None)
            sel = st.radio("Cevabınız:", opts, index=sel_idx, key=f"rad_{st.session_state.idx}")
            if sel: 
                st.session_state.answers[st.session_state.idx] = sel.split(")")[0]
                if sel.split(")")[0] == row['Dogru_Cevap']: st.success("DOĞRU! 🎉")
                else: st.error(f"YANLIŞ! Doğru: {row['Dogru_Cevap']}")
    else:
        st.markdown(f"<div class='question-stem'>{format_html(stem)}</div>", unsafe_allow_html=True)
        sel_idx = next((i for i,v in enumerate(opts) if v.startswith(st.session_state.answers.get(st.session_state.idx, "")+")")), None)
        sel = st.radio("Cevabınız:", opts, index=sel_idx, key=f"rad_{st.session_state.idx}")
        if sel:
            st.session_state.answers[st.session_state.idx] = sel.split(")")[0]
            if sel.split(")")[0] == row['Dogru_Cevap']: st.success("DOĞRU! 🎉")
            else: st.error(f"YANLIŞ! Doğru: {row['Dogru_Cevap']}")

    st.write("")
    if st.button("🤖 Çözümle ve Seslendir 🔊", use_container_width=True):
        if not st.session_state.user_api_key: st.error("Lütfen soldan API Key kaydedin.")
        else:
            with st.spinner("Analiz ediliyor..."):
                txt = get_gemini_text(st.session_state.user_api_key, passage, stem, opts)
                st.session_state.gemini_res[st.session_state.idx] = {'text': txt, 'audio': None}
                st.rerun()
    
    c_p, c_n = st.columns(2)
    if st.session_state.idx > 0 and c_p.button("⬅️ Önceki", use_container_width=True): 
        st.session_state.idx -= 1
        st.rerun()
    if st.session_state.idx < len(df)-1 and c_n.button("Sonraki ➡️", use_container_width=True): 
        st.session_state.idx += 1
        st.rerun()

    if st.session_state.idx in st.session_state.gemini_res:
        res = st.session_state.gemini_res[st.session_state.idx]
        st.markdown("---")
        if res['audio']: st.audio(res['audio'])
        st.markdown(format_html(res['text']), unsafe_allow_html=True)
        if not res['audio']:
            with st.spinner("Ses..."):
                aud = get_audio_sync(res['text'])
                if aud: 
                    st.session_state.gemini_res[st.session_state.idx]['audio'] = aud
                    st.rerun()
else:
    # --- SONUÇ EKRANI ---
    st.title(f"📊 {exam_options[st.session_state.selected_exam_id]} Sonuç Analizi")
    st.markdown("---")
    correct, wrong, empty = 0, 0, 0
    wrong_q_text = ""
    res_data = []
    
    for i in range(len(df)):
        ans = st.session_state.answers.get(i)
        real = df.iloc[i]['Dogru_Cevap']
        status = "BOŞ"
        if ans:
            if ans == real: 
                correct += 1; status = "DOĞRU"
            else: 
                wrong += 1; status = "YANLIŞ"
                wrong_q_text += f"- Soru {i+1}: {str(df.iloc[i]['Soru'])[:200]}...\n"
        else: 
            empty += 1
            wrong_q_text += f"- Soru {i+1} (BOŞ): {str(df.iloc[i]['Soru'])[:200]}...\n"
        res_data.append({"No": i+1, "Cevap": ans if ans else "-", "Doğru": real, "Durum": status})

    score = correct * 1.25
    
    # --- SONUCU KAYDETME VE GÜNCELLEME ---
    if not st.session_state.data_saved:
        save_score_to_csv(
            st.session_state.username, 
            exam_options[st.session_state.selected_exam_id], # Örn: "YDS Deneme 1"
            score, correct, wrong, empty
        )
        st.session_state.data_saved = True
        st.balloons()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Puan", f"{score:.2f}")
    c2.metric("Doğru", correct)
    c3.metric("Yanlış", wrong)
    c4.metric("Boş", empty)

    # --- LİDERLİK TABLOSU (PIVOT) ---
    st.markdown("---")
    st.subheader("🏆 Genel Liderlik Tablosu (Tüm Sınavlar)")
    pivot_table = get_leaderboard_pivot()
    if pivot_table is not None:
        st.dataframe(pivot_table, use_container_width=True)
    else:
        st.info("Henüz veri yok.")

    st.markdown("---")
    st.subheader("🤖 Yapay Zeka Koçluk")
    if st.button("✨ Performansımı Analiz Et", type="primary"):
        if not st.session_state.user_api_key: st.error("API Key gerekli.")
        else:
            with st.spinner("Analiz..."):
                info = f"Puan: {score}, D: {correct}, Y: {wrong}, B: {empty}"
                st.session_state.analysis_report = generate_performance_analysis(st.session_state.user_api_key, wrong_q_text, info)
    
    if st.session_state.analysis_report:
        st.markdown(f"<div class='analysis-report'>{format_html(st.session_state.analysis_report)}</div>", unsafe_allow_html=True)
        
    st.markdown("---")
    st.subheader("Detaylı Cevaplar")
    st.dataframe(pd.DataFrame(res_data).style.map(lambda v: f'color: {"green" if v=="DOĞRU" else "red" if v=="YANLIŞ" else "orange"}; font-weight: bold;', subset=['Durum']), use_container_width=True)
    
    if st.button("🔄 SINAVI TEKRARLA"):
        st.session_state.answers = {}
        st.session_state.marked = set()
        st.session_state.idx = 0
        st.session_state.finish = False
        st.session_state.data_saved = False
        st.session_state.analysis_report = None
        st.rerun()
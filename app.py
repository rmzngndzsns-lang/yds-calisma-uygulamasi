import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import google.generativeai as genai
import os
import json
import nest_asyncio

# Döngü yaması
nest_asyncio.apply()

# --- 1. AYARLAR ---
st.set_page_config(page_title="YDS Pro", page_icon="🎓", layout="wide")

# --- 2. CSS (TÜM SORUNLAR ÇÖZÜLDÜ) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Poppins', sans-serif; background-color: #f8fafc; }
    
    /* SIDEBAR GENİŞLİK SABİTLEME */
    section[data-testid="stSidebar"] { min-width: 340px !important; max-width: 340px !important; }

    /* GİRİŞ EKRANI */
    .login-container {
        max-width: 400px; margin: 60px auto; padding: 40px;
        background: white; border-radius: 16px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: center; 
        border: 1px solid #eef2f6;
    }
    .stTextInput > div > div > input { width: 100% !important; }
    
    /* GENEL BUTONLAR */
    div.stButton > button { width: 100% !important; border-radius: 8px; font-weight: 600; }

    /* --- SORU HARİTASI (İKON SORUNU TAMAMEN ÇÖZÜLDÜ) --- */
    /* Kolonun kendisini kısıtlıyoruz */
    div[data-testid="stSidebar"] div[data-testid="column"] {
        width: 44px !important;
        min-width: 44px !important;
        max-width: 44px !important;
        flex: 0 0 44px !important;
        padding: 0 !important;
        margin: 1px !important;
    }

    /* Butonun kendisini SABİT BOYUTLARA KİLİTLE */
    div[data-testid="stSidebar"] div[data-testid="column"] button {
        width: 42px !important;
        height: 42px !important;
        min-width: 42px !important;
        max-width: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        padding: 0 !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        border-radius: 6px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        line-height: 1 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: clip !important;
        flex-shrink: 0 !important; /* ASLA KÜÇÜLME */
        flex-grow: 0 !important;   /* ASLA BÜYÜME */
    }
    
    /* İKONLARI SABİTLE - BOYUT DEĞİŞİMİ OLMASIN */
    div[data-testid="stSidebar"] div[data-testid="column"] button::after {
        content: attr(data-icon);
        position: absolute;
        font-size: 8px !important;
        top: 2px;
        right: 2px;
        line-height: 1;
    }

    /* ÜST KONTROL PANEL SABİTLEME */
    .control-panel {
        position: sticky !important;
        top: 0;
        z-index: 999;
        background: white;
        padding: 15px 0;
        margin-bottom: 20px;
        border-bottom: 2px solid #e5e7eb;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
    }
    
    .control-panel h3 {
        margin: 0 !important;
        padding: 0 !important;
        flex: 1;
    }
    
    /* FONT KONTROL BUTONLARI SABİTLEME */
    .font-controls {
        display: flex !important;
        gap: 8px !important;
        align-items: center !important;
        flex-shrink: 0 !important;
    }
    
    .font-controls button {
        width: 45px !important;
        min-width: 45px !important;
        max-width: 45px !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        padding: 0 !important;
        flex-shrink: 0 !important;
        flex-grow: 0 !important;
    }
    
    .mark-btn button {
        width: 45px !important;
        min-width: 45px !important;
        max-width: 45px !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        flex-shrink: 0 !important;
        flex-grow: 0 !important;
    }

    /* OKUMA ALANI (DİNAMİK FONT - ÇALIŞIYOR) */
    .passage-box { 
        background-color: #ffffff; 
        padding: 25px; 
        border-radius: 12px; 
        border: 1px solid #dfe6e9; 
        color: #2d3436; 
        overflow-y: auto; 
        max-height: 70vh;
    }
    
    .question-stem { 
        font-weight: 600; 
        border-left: 5px solid #2563eb; 
        padding-left: 15px; 
        margin-bottom: 20px; 
        color: #1e293b;
    }
    
    /* DARK MODE */
    @media (prefers-color-scheme: dark) {
        .stApp { background-color: #0f172a; }
        .passage-box { background-color: #1e293b; color: #e2e8f0; border-color: #334155; }
        .login-container { background: #1e293b; color: #e2e8f0; }
        .control-panel { background: #1e293b; border-bottom-color: #334155; }
    }
</style>
""", unsafe_allow_html=True)

# --- 3. VERİ YÖNETİMİ ---
SCORES_FILE = "lms_scores.csv"

@st.cache_data(show_spinner=False)
def load_exam_file_cached(exam_id):
    if not isinstance(exam_id, int) or exam_id < 1 or exam_id > 10:
        return None
    
    names = [f"Sinav_{exam_id}.xlsx", f"sinav_{exam_id}.xlsx", f"Sinav_{exam_id}.csv"]
    for name in names:
        if os.path.exists(name):
            try:
                df = pd.read_excel(name, engine='openpyxl') if name.endswith('xlsx') else pd.read_csv(name)
                df.columns = df.columns.str.strip()
                
                required_cols = ['Soru', 'Dogru_Cevap', 'A', 'B', 'C', 'D', 'E']
                if not all(col in df.columns for col in required_cols):
                    st.error(f"{name} dosyasında eksik kolonlar var!")
                    continue
                
                if 'Dogru_Cevap' in df.columns: 
                    df['Dogru_Cevap'] = df['Dogru_Cevap'].astype(str).str.strip().str.upper()
                return df
            except Exception as e:
                st.error(f"Dosya okuma hatası: {e}")
                continue
    return None

def save_score_to_csv(username, exam_name, score, correct, wrong, empty):
    try:
        if os.path.exists(SCORES_FILE): 
            df = pd.read_csv(SCORES_FILE)
        else: 
            df = pd.DataFrame(columns=["Kullanıcı", "Sınav", "Puan", "Doğru", "Yanlış", "Boş", "Tarih"])
        
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        mask = (df["Kullanıcı"] == username) & (df["Sınav"] == exam_name)
        
        if mask.any(): 
            df.loc[mask, ["Puan", "Doğru", "Yanlış", "Boş", "Tarih"]] = [score, correct, wrong, empty, date_str]
        else:
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
        
        df.to_csv(SCORES_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")
        return False

def get_leaderboard_pivot():
    if not os.path.exists(SCORES_FILE): return None
    try:
        df = pd.read_csv(SCORES_FILE)
        if df.empty: return None
        return df.pivot_table(index="Kullanıcı", columns="Sınav", values="Puan", aggfunc="max").fillna("-")
    except: return None

def autosave_progress():
    if st.session_state.username and st.session_state.selected_exam_id:
        progress_file = f"progress_{st.session_state.username}_{st.session_state.selected_exam_id}.json"
        data = {
            'answers': {str(k): v for k, v in st.session_state.answers.items()},
            'marked': list(st.session_state.marked),
            'idx': st.session_state.idx,
            'timestamp': datetime.now().isoformat()
        }
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except: pass

def load_progress():
    if st.session_state.username and st.session_state.selected_exam_id:
        progress_file = f"progress_{st.session_state.username}_{st.session_state.selected_exam_id}.json"
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    st.session_state.answers = {int(k): v for k, v in data['answers'].items()}
                    st.session_state.marked = set(data['marked'])
                    st.session_state.idx = data.get('idx', 0)
                    return True
            except: pass
    return False

# --- 4. SESSION ---
defaults = {
    'username': None, 'selected_exam_id': 1, 'idx': 0, 'answers': {}, 
    'marked': set(), 'finish': False, 'data_saved': False, 'gemini_res': {}, 
    'user_api_key': "", 'font_size': 16, 'exam_mode': False, 'end_timestamp': 0,
    'current_exam_data': None, 'cached_exam_id': None, 'progress_loaded': False
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# --- 5. GİRİŞ EKRANI ---
if st.session_state.username is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container"><h1 style="color:#2563eb;">YDS Pro</h1><p>Giriş Yapın</p></div>', unsafe_allow_html=True)
        with st.form("login_form"):
            name = st.text_input("Ad Soyad:", placeholder="İsim giriniz...")
            submitted = st.form_submit_button("🚀 Giriş Yap")
            if submitted:
                if name.strip():
                    st.session_state.username = name.strip()
                    st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000
                    st.rerun()
                else: st.error("İsim gerekli.")
    st.stop()

# İlerleme yükle (sadece bir kez)
if not st.session_state.progress_loaded:
    load_progress()
    st.session_state.progress_loaded = True

# --- 6. VERİ YÜKLEME OPTİMİZASYONU ---
exam_id = st.session_state.selected_exam_id
if st.session_state.current_exam_data is None or st.session_state.cached_exam_id != exam_id:
    df = load_exam_file_cached(exam_id)
    st.session_state.current_exam_data = df
    st.session_state.cached_exam_id = exam_id
else:
    df = st.session_state.current_exam_data

# SÜRE KONTROLÜ - Otomatik bitirme
if not st.session_state.finish and datetime.now().timestamp() * 1000 >= st.session_state.end_timestamp:
    st.session_state.finish = True
    st.rerun()

# --- 7. SIDEBAR ---
with st.sidebar:
    st.success(f"👤 **{st.session_state.username}**")
    
    # SAYAÇ (Otomatik bitirme ile)
    if not st.session_state.finish:
        components.html(
            f"""<div id="countdown" style="font-family:'Poppins',sans-serif;font-size:18px;font-weight:bold;color:#dc2626;text-align:center;padding:8px;background:#fee2e2;border-radius:8px;border:1px solid #fecaca;">⏳ Hesapla...</div>
            <script>
            var dest={st.session_state.end_timestamp};
            var interval = setInterval(function(){{
                var now=new Date().getTime();
                var dist=dest-now;
                if(dist <= 0) {{
                    clearInterval(interval);
                    document.getElementById("countdown").innerHTML="⏰ SÜRE BİTTİ!";
                    document.getElementById("countdown").style.background="#fca5a5";
                    return;
                }}
                var h=Math.floor((dist%(1000*60*60*24))/(1000*60*60));
                var m=Math.floor((dist%(1000*60*60))/(1000*60));
                var s=Math.floor((dist%(1000*60))/1000);
                document.getElementById("countdown").innerHTML="⏳ "+(h<10?"0"+h:h)+":"+(m<10?"0"+m:m)+":"+(s<10?"0"+s:s);
            }}, 1000);
            </script>""", height=60
        )

    mode = st.toggle("Sınav Modu", value=st.session_state.exam_mode)
    if mode != st.session_state.exam_mode:
        st.session_state.exam_mode = mode
        st.rerun()

    new_exam_id = st.selectbox("Sınav Seç:", range(1, 11), format_func=lambda x: f"YDS Deneme {x}", index=st.session_state.selected_exam_id - 1)
    if new_exam_id != st.session_state.selected_exam_id:
        st.session_state.selected_exam_id = new_exam_id
        st.session_state.answers, st.session_state.marked, st.session_state.idx = {}, set(), 0
        st.session_state.finish, st.session_state.data_saved, st.session_state.gemini_res = False, False, {}
        st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000
        st.session_state.current_exam_data = None
        st.session_state.cached_exam_id = None
        st.rerun()

    with st.expander("🔑 AI Ayarları"):
        key_input = st.text_input("API Key:", type="password", value=st.session_state.user_api_key)
        if st.button("Kaydet"):
            if key_input and len(key_input.strip()) > 0:
                st.session_state.user_api_key = key_input.strip()
                st.success("Kaydedildi.")
            else:
                st.error("Lütfen anahtar girin!")

    if df is not None:
        st.write("---")
        
        # İLERLEME GÖSTERGESI
        total = len(df)
        answered = len(st.session_state.answers)
        progress = answered / total if total > 0 else 0
        
        st.progress(progress)
        st.caption(f"📝 {answered}/{total} soru yanıtlandı (%{progress*100:.1f})")
        
        st.write("---")
        st.markdown("**🗺️ Soru Haritası**")
        st.markdown('<div style="font-size:11px; margin-bottom:10px; display:flex; justify-content:space-between;"><span>✅ Doğru</span><span>❌ Yanlış</span><span>⭐ İşaret</span></div>', unsafe_allow_html=True)

        cols = st.columns(5)
        for i in range(len(df)):
            q_idx = i
            col_idx = i % 5 
            with cols[col_idx]:
                u_a = st.session_state.answers.get(q_idx)
                
                # SADECESAYıYı GÖSTER - İKON YOK (Kutular kaymaz)
                lbl = str(q_idx + 1)
                
                # Renklendirme için type belirleme
                if q_idx in st.session_state.marked:
                    b_type = "primary" if q_idx == st.session_state.idx else "secondary"
                elif u_a:
                    if st.session_state.exam_mode:
                        b_type = "primary" if q_idx == st.session_state.idx else "secondary"
                    else:
                        correct_ans = df.iloc[q_idx]['Dogru_Cevap']
                        if u_a == correct_ans:
                            b_type = "primary" if q_idx == st.session_state.idx else "secondary"
                        else:
                            b_type = "primary" if q_idx == st.session_state.idx else "secondary"
                else:
                    b_type = "primary" if q_idx == st.session_state.idx else "secondary"
                
                # Buton arkaplan rengi için custom key
                button_key = f"nav_{q_idx}"
                
                if st.button(lbl, key=button_key, type=b_type):
                    st.session_state.idx = q_idx
                    st.rerun()
        
        st.write("---")
        if not st.session_state.finish:
            if st.button("🏁 SINAVI BİTİR", type="primary"):
                st.session_state.finish = True
                st.rerun()

# --- 8. ANA EKRAN ---
if df is not None:
    if not st.session_state.finish:
        # ÜST KONTROL PANEL (SABİT)
        control_col1, control_col2, control_col3, control_col4, control_col5 = st.columns([10, 1, 1, 1, 1])
        
        with control_col1:
            st.markdown(f"<h3 style='margin:0;padding:0;'>Soru {st.session_state.idx + 1}</h3>", unsafe_allow_html=True)
        
        # FONT KÜÇÜLT BUTONU
        with control_col2:
            if st.button("A➖", key="font_decrease", help="Küçült"):
                if st.session_state.font_size > 12:
                    st.session_state.font_size -= 2
                    st.rerun()
        
        # FONT BÜYÜT BUTONU
        with control_col3:
            if st.button("A➕", key="font_increase", help="Büyüt"):
                if st.session_state.font_size < 30:
                    st.session_state.font_size += 2
                    st.rerun()
        
        # FONT BOYUTU GÖSTERGESİ
        with control_col4:
            st.markdown(f"<div style='text-align:center;padding-top:8px;font-size:12px;color:#666;'>{st.session_state.font_size}px</div>", unsafe_allow_html=True)
        
        # İŞARETLE BUTONU
        with control_col5:
            is_m = st.session_state.idx in st.session_state.marked
            if st.button("⭐" if is_m else "☆", key="mark_toggle", help="İşaretle"):
                if is_m:
                    st.session_state.marked.remove(st.session_state.idx)
                else:
                    st.session_state.marked.add(st.session_state.idx)
                autosave_progress()
                st.rerun()

        st.markdown("<hr style='margin:15px 0;'>", unsafe_allow_html=True)

        row = df.iloc[st.session_state.idx]
        q_raw = str(row['Soru']).replace('\\n', '\n')
        passage, stem = (q_raw.split('\n\n', 1) if '\n\n' in q_raw else (None, q_raw))
        
        f_size = st.session_state.font_size
        line_h = f_size * 1.6
        
        if passage:
            l, r = st.columns(2)
            l.markdown(f"<div class='passage-box' style='font-size:{f_size}px; line-height:{line_h}px;'>{passage}</div>", unsafe_allow_html=True)
            main_col = r
        else:
            main_col = st.container()

        with main_col:
            st.markdown(f"<div class='question-stem' style='font-size:{f_size+2}px;'>{stem}</div>", unsafe_allow_html=True)
            opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
            curr = st.session_state.answers.get(st.session_state.idx)
            sel_idx = next((i for i,v in enumerate(opts) if v.startswith(str(curr) + ")")), None)
            
            sel = st.radio("Cevabınız:", opts, index=sel_idx, key=f"ans_{st.session_state.idx}")
            
            if sel:
                chosen = sel.split(")")[0]
                old_answer = st.session_state.answers.get(st.session_state.idx)
                
                if old_answer and old_answer != chosen:
                    st.warning(f"⚠️ Cevabınızı {old_answer}'dan {chosen}'ye değiştirdiniz.")
                
                st.session_state.answers[st.session_state.idx] = chosen
                autosave_progress()
                
                if not st.session_state.exam_mode:
                    if chosen == row['Dogru_Cevap']:
                        st.success("✅ DOĞRU! 🎉")
                    else:
                        st.error(f"❌ YANLIŞ! (Doğru: {row['Dogru_Cevap']})")

        st.write("")
        c_act1, c_act2 = st.columns([1, 1])
        
        with c_act1:
            if st.button("🤖 AI Çözümle", use_container_width=True):
                if not st.session_state.user_api_key:
                    st.warning("⚠️ Lütfen API Key girin.")
                else:
                    with st.spinner("🔍 AI analiz ediyor..."):
                        try:
                            genai.configure(api_key=st.session_state.user_api_key)
                            model = genai.GenerativeModel('gemini-2.0-flash-exp')
                            prompt = f"""YDS Sorusu:
{q_raw}

Doğru Cevap: {row['Dogru_Cevap']}

Lütfen bu soruyu detaylıca analiz et:
1. Sorunun ana konusu
2. Neden doğru cevap {row['Dogru_Cevap']}
3. Diğer şıklar neden yanlış
4. Önemli kelimeler ve ipuçları
"""
                            res = model.generate_content(prompt).text
                            st.session_state.gemini_res[st.session_state.idx] = res
                            st.rerun()
                        except Exception as e:
                            st.error(f"AI hatası: {str(e)}")
        
        with c_act2:
            c_p, c_n = st.columns(2)
            if st.session_state.idx > 0 and c_p.button("⬅️ Önceki", use_container_width=True):
                st.session_state.idx -= 1
                st.rerun()
            if st.session_state.idx < len(df)-1 and c_n.button("Sonraki ➡️", use_container_width=True):
                st.session_state.idx += 1
                st.rerun()

        if st.session_state.idx in st.session_state.gemini_res:
            st.info("**🤖 AI Analizi:**\n\n" + st.session_state.gemini_res[st.session_state.idx])

    else:
        # PERFORMANS RAPORU
        st.title("📊 Performans Raporu")
        correct = sum(1 for i, a in st.session_state.answers.items() if a == df.iloc[i]['Dogru_Cevap'])
        wrong = len(st.session_state.answers) - correct
        empty = len(df) - len(st.session_state.answers)
        score = correct * 1.25
        
        if not st.session_state.data_saved:
            save_score_to_csv(st.session_state.username, f"Deneme {st.session_state.selected_exam_id}", score, correct, wrong, empty)
            st.session_state.data_saved = True
            if score > 50:
                st.balloons()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Puan", f"{score:.2f}")
        m2.metric("Doğru ✅", correct)
        m3.metric("Yanlış ❌", wrong)
        m4.metric("Boş ⚪", empty)

        # GRAFİK (Plotly yerine basit HTML/CSS bar chart)
        st.subheader("📈 Cevap Dağılımı")
        total_answered = correct + wrong + empty
        correct_pct = (correct / total_answered * 100) if total_answered > 0 else 0
        wrong_pct = (wrong / total_answered * 100) if total_answered > 0 else 0
        empty_pct = (empty / total_answered * 100) if total_answered > 0 else 0
        
        st.markdown(f"""
        <div style="width:100%; height:40px; display:flex; border-radius:8px; overflow:hidden; margin:20px 0;">
            <div style="width:{correct_pct}%; background:#10b981; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold;">{correct}</div>
            <div style="width:{wrong_pct}%; background:#ef4444; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold;">{wrong}</div>
            <div style="width:{empty_pct}%; background:#94a3b8; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold;">{empty}</div>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("🏆 Liderlik Tablosu")
        leaderboard = get_leaderboard_pivot()
        if leaderboard is not None:
            st.dataframe(leaderboard, use_container_width=True)
        else:
            st.info("Henüz liderlik verisi yok.")

        if st.button("🔄 Yeni Sınava Başla", type="primary"):
            st.session_state.answers = {}
            st.session_state.idx = 0
            st.session_state.finish = False
            st.session_state.data_saved = False
            st.session_state.gemini_res = {}
            st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000
            st.rerun()

else:
    st.warning("⚠️ Sınav dosyası bulunamadı. Lütfen dosyaların doğru konumda olduğundan emin olun.")
    st.info("Beklenen dosya adları: Sinav_1.xlsx, Sinav_2.xlsx ...")
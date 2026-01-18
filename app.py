import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- 1. PAGE SETTINGS ---
st.set_page_config(page_title="YDS Pro", page_icon="🎓", layout="wide")

# --- 2. CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #f3f4f6;
    }
    
    /* SIDEBAR BUTTON GRID STYLING */
    /* Force smaller padding between columns in sidebar for tight grid */
    [data-testid="stSidebar"] [data-testid="column"] {
        padding: 0px 1px !important;
        min-width: 0 !important;
    }
    
    [data-testid="stSidebar"] button {
        width: 100% !important;
        padding: 0px !important;
        height: 34px !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        margin: 0px !important;
    }

    /* PASSAGE BOX */
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

    /* QUESTION STEM */
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

    /* RADIO BUTTONS */
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
        background-color: #eff6ff; border-color: #3b82f6; color: #1d4ed8;
    }

    /* SPECIAL BUTTONS */
    div.stButton > button:contains("İşaretle") { border-color: #d97706 !important; color: #d97706 !important; font-weight: 700; }
    div.stButton > button:contains("Kaldır") { background-color: #d97706 !important; color: white !important; border: none; }
    
    /* NAV BUTTONS */
    div.stButton > button { height: 45px; font-weight: 500; font-size: 15px; }
</style>
""", unsafe_allow_html=True)

# --- 3. DATA LOAD ---
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("sorular.xlsx", engine="openpyxl")
        df['Dogru_Cevap'] = df['Dogru_Cevap'].astype(str).str.strip().str.upper()
        return df
    except:
        return None

# --- 4. SESSION ---
def init_session():
    if 'idx' not in st.session_state: st.session_state.idx = 0
    if 'answers' not in st.session_state: st.session_state.answers = {}
    if 'marked' not in st.session_state: st.session_state.marked = set()
    if 'end_timestamp' not in st.session_state:
        st.session_state.end_timestamp = (datetime.now() + timedelta(minutes=180)).timestamp() * 1000 
    if 'finish' not in st.session_state: st.session_state.finish = False

df = load_data()
init_session()

# --- 5. PARSER ---
def parse_question(text):
    if pd.isna(text): return None, "..."
    text = str(text).replace('\\n', '\n')
    parts = text.split('\n\n', 1) if '\n\n' in text else (None, text.strip())
    return parts[0].strip() if parts[0] else None, parts[1].strip()

# --- 6. APP LOGIC ---
if df is not None:
    
    # --- SIDEBAR ---
    with st.sidebar:
        # TIMER
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

        # --- THE ROW-BASED GRID LOGIC (MOBILE FRIENDLY) ---
        # We loop through questions in chunks of 5 (Row by Row)
        # This ensures that Question 1, 2, 3, 4, 5 are in the first 'st.columns' block.
        # On mobile, that block stacks 1, 2, 3, 4, 5 vertically. PERFECT ORDER.
        
        chunk_size = 5
        for i in range(0, len(df), chunk_size):
            # Create a row of 5 columns
            row_cols = st.columns(chunk_size)
            
            # Fill this row
            for j in range(chunk_size):
                if i + j < len(df):
                    q_idx = i + j
                    
                    u_ans = st.session_state.answers.get(q_idx)
                    c_ans = df.iloc[q_idx]['Dogru_Cevap']
                    
                    label = str(q_idx + 1)
                    if u_ans:
                        label = "✅" if u_ans == c_ans else "❌"
                    elif q_idx in st.session_state.marked:
                        label = "⭐"
                    
                    b_type = "primary" if q_idx == st.session_state.idx else "secondary"
                    
                    with row_cols[j]:
                        if st.button(label, key=f"q_{q_idx}", type=b_type, use_container_width=True):
                            st.session_state.idx = q_idx
                            st.rerun()

        st.divider()
        if st.button("SINAVI BİTİR", type="primary", use_container_width=True):
            st.session_state.finish = True
            st.rerun()

    # --- MAIN CONTENT ---
    if not st.session_state.finish:
        # Header
        c_title, c_mark = st.columns([3, 1])
        c_title.markdown(f"### Soru {st.session_state.idx + 1} / {len(df)}")
        
        is_marked = st.session_state.idx in st.session_state.marked
        btn_txt = "🏳️ Kaldır" if is_marked else "🚩 İşaretle"
        if c_mark.button(btn_txt, key="mark_main"):
            if is_marked: st.session_state.marked.remove(st.session_state.idx)
            else: st.session_state.marked.add(st.session_state.idx)
            st.rerun()

        row = df.iloc[st.session_state.idx]
        passage, stem = parse_question(row['Soru'])

        if passage:
            col_l, col_r = st.columns([1, 1], gap="medium")
            with col_l:
                st.info("Okuma Parçası")
                st.markdown(f"<div class='passage-box'>{passage}</div>", unsafe_allow_html=True)
            with col_r:
                st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
                opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
                curr = st.session_state.answers.get(st.session_state.idx)
                idx_s = next((k for k,v in enumerate(opts) if v.startswith(curr + ")")), None) if curr else None
                sel = st.radio("Cevap", opts, index=idx_s, key=f"r{st.session_state.idx}")
                if sel:
                    char = sel.split(")")[0]
                    st.session_state.answers[st.session_state.idx] = char
                    if char == row['Dogru_Cevap']: st.success("✅ DOĞRU")
                    else: st.error(f"❌ YANLIŞ! (Cevap: {row['Dogru_Cevap']})")
        else:
            st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
            opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
            curr = st.session_state.answers.get(st.session_state.idx)
            idx_s = next((k for k,v in enumerate(opts) if v.startswith(curr + ")")), None) if curr else None
            sel = st.radio("Cevap", opts, index=idx_s, key=f"r{st.session_state.idx}")
            if sel:
                char = sel.split(")")[0]
                st.session_state.answers[st.session_state.idx] = char
                if char == row['Dogru_Cevap']: st.success("✅ DOĞRU")
                else: st.error(f"❌ YANLIŞ! (Cevap: {row['Dogru_Cevap']})")

        st.write("")
        cp, cn = st.columns(2)
        if st.session_state.idx > 0:
            cp.button("⬅️ Önceki", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx-1), use_container_width=True)
        if st.session_state.idx < len(df) - 1:
            cn.button("Sonraki ➡️", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx+1), type="primary", use_container_width=True)

    else:
        st.title("Sonuçlar")
        data = []
        c,w,e = 0,0,0
        for i in range(len(df)):
            u = st.session_state.answers.get(i)
            t = df.iloc[i]['Dogru_Cevap']
            if u:
                if u == t: c+=1; s="Doğru"
                else: w+=1; s="Yanlış"
            else: e+=1; s="Boş"
            data.append({"Soru": i+1, "Cevap": u, "Doğru": t, "Durum": s})
        
        k1,k2,k3 = st.columns(3)
        k1.metric("Doğru", c)
        k2.metric("Yanlış", w)
        k3.metric("Boş", e)
        st.dataframe(pd.DataFrame(data), use_container_width=True)
        if st.button("Başa Dön"):
            st.session_state.clear()
            st.rerun()

else:
    st.error("Excel yüklenemedi.")
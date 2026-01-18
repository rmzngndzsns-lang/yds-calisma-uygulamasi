import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- 1. PAGE SETTINGS ---
st.set_page_config(page_title="YDS Pro", page_icon="🎓", layout="wide")

# --- 2. ADVANCED CSS (THE FIX) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #f3f4f6;
    }

    /* --- THE SIDEBAR GRID FIX --- */
    /* We target the container that holds the buttons and force it into a 5-column grid */
    
    /* 1. Define a class for the container of our buttons */
    .button-grid-container {
        display: grid;
        grid-template-columns: repeat(5, 1fr); /* Always 5 columns */
        gap: 4px; /* Space between buttons */
        width: 100%;
    }

    /* 2. Styling the buttons inside the grid to look good */
    .grid-btn {
        width: 100%;
        padding: 0;
        height: 35px;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        background-color: white;
        color: #374151;
        font-weight: 600;
        font-size: 13px;
        cursor: pointer;
        transition: all 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* Active/State Styles (We will apply these via Python logic) */
    .grid-btn.active { background-color: #ef4444; color: white; border-color: #dc2626; } /* Current Q - Red */
    .grid-btn.correct { background-color: #22c55e; color: white; border-color: #16a34a; } /* Correct - Green */
    .grid-btn.wrong { background-color: #ef4444; color: white; border-color: #dc2626; } /* Wrong - Red */
    .grid-btn.marked { border: 2px solid #eab308; color: #ca8a04; } /* Marked - Yellow Border */

    /* STREAMLIT BUTTON OVERRIDE 
       Since we must use st.button for functionality, we need to strip Streamlit's 
       default margins and force them into our visual grid. 
    */
    
    /* Target the columns inside the sidebar */
    [data-testid="stSidebar"] [data-testid="column"] {
        min-width: 0 !important;
        width: 20% !important; /* Force 1/5th width */
        flex: 0 0 20% !important;
        padding: 1px !important;
    }
    
    [data-testid="stSidebar"] button {
        width: 100% !important;
        padding: 0px !important;
        margin: 0px !important;
        height: 32px !important;
        font-size: 12px !important;
        line-height: 1 !important;
    }
    
    /* Responsive Text Size for Mobile */
    @media (max-width: 600px) {
        [data-testid="stSidebar"] button {
            font-size: 10px !important;
            height: 28px !important;
        }
    }

    /* --- OTHER STYLES --- */
    .passage-box {
        background-color: white;
        padding: 15px;
        border-radius: 12px;
        height: 50vh;
        overflow-y: auto;
        font-size: 15px;
        line-height: 1.6;
        text-align: justify;
        border: 1px solid #e5e7eb;
        border-left: 5px solid #2c3e50;
    }
    .question-stem {
        font-size: 16px; 
        font-weight: 600;
        background-color: white; 
        padding: 15px;
        border-radius: 12px; 
        border: 1px solid #e5e7eb;
        border-left: 4px solid #3b82f6; 
        margin-bottom: 15px;
    }
    /* Hide Radio Labels */
    .stRadio > label { display: none; }
    div[role='radiogroup'] > label {
        padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; margin-bottom: 5px; background: white;
    }
    div[role='radiogroup'] > label:hover { background: #eff6ff; border-color: #3b82f6; }
    
    /* Nav Buttons */
    div.stButton > button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 3. DATA LOADING ---
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
        <div style="font-family:'Courier New',monospace;font-size:32px;font-weight:800;color:#dc2626;background:white;padding:5px;border-radius:8px;text-align:center;border:3px solid #dc2626;margin-bottom:10px;" id="cnt">...</div>
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
        """, height=70)

        st.caption("🟢:D | 🔴:Y | ⭐:İşaretli")

        # --- THE GRID LOGIC ---
        # Instead of 1 loop creating columns iteratively (which breaks on mobile),
        # We create ONE set of 5 columns, then fill them vertically.
        # This forces Streamlit to keep the structure.
        
        # 1. Create 5 columns once
        grid_columns = st.columns(5)
        
        # 2. Iterate through all questions
        for i in range(len(df)):
            u_ans = st.session_state.answers.get(i)
            c_ans = df.iloc[i]['Dogru_Cevap']
            
            label = str(i+1)
            if u_ans:
                label = "✅" if u_ans == c_ans else "❌"
            elif i in st.session_state.marked:
                label = "⭐"
            
            # Highlight current question
            b_type = "primary" if i == st.session_state.idx else "secondary"
            
            # 3. Place button in the correct column based on index
            # i % 5 ensures we cycle through col 0, 1, 2, 3, 4, 0, 1...
            with grid_columns[i % 5]:
                if st.button(label, key=f"q_btn_{i}", type=b_type, use_container_width=True):
                    st.session_state.idx = i
                    st.rerun()

        st.divider()
        if st.button("SINAVI BİTİR", type="primary"):
            st.session_state.finish = True
            st.rerun()

    # --- MAIN CONTENT ---
    if not st.session_state.finish:
        # Header
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"### Soru {st.session_state.idx + 1} / {len(df)}")
        
        is_marked = st.session_state.idx in st.session_state.marked
        if c2.button("🏳️ Kaldır" if is_marked else "🚩 İşaretle", key="mark_main"):
            if is_marked: st.session_state.marked.remove(st.session_state.idx)
            else: st.session_state.marked.add(st.session_state.idx)
            st.rerun()

        row = df.iloc[st.session_state.idx]
        passage, stem = parse_question(row['Soru'])

        # Layout
        if passage:
            col_l, col_r = st.columns([1, 1], gap="medium")
            with col_l:
                st.info("Okuma Parçası")
                st.markdown(f"<div class='passage-box'>{passage}</div>", unsafe_allow_html=True)
            with col_r:
                st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
                # Options
                opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
                curr = st.session_state.answers.get(st.session_state.idx)
                idx_s = next((i for i, v in enumerate(opts) if v.startswith(curr + ")")), None) if curr else None
                
                sel = st.radio("Cevap", opts, index=idx_s, key=f"rad_{st.session_state.idx}")
                if sel:
                    char = sel.split(")")[0]
                    st.session_state.answers[st.session_state.idx] = char
                    if char == row['Dogru_Cevap']: st.success("✅ DOĞRU")
                    else: st.error(f"❌ YANLIŞ! (Cevap: {row['Dogru_Cevap']})")
        else:
            st.markdown(f"<div class='question-stem'>{stem}</div>", unsafe_allow_html=True)
            opts = [f"{c}) {row[c]}" for c in "ABCDE" if pd.notna(row[c])]
            curr = st.session_state.answers.get(st.session_state.idx)
            idx_s = next((i for i, v in enumerate(opts) if v.startswith(curr + ")")), None) if curr else None
            
            sel = st.radio("Cevap", opts, index=idx_s, key=f"rad_{st.session_state.idx}")
            if sel:
                char = sel.split(")")[0]
                st.session_state.answers[st.session_state.idx] = char
                if char == row['Dogru_Cevap']: st.success("✅ DOĞRU")
                else: st.error(f"❌ YANLIŞ! (Cevap: {row['Dogru_Cevap']})")

        # Nav
        st.write("")
        cp, cn = st.columns(2)
        if st.session_state.idx > 0:
            cp.button("⬅️ Önceki", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx-1), use_container_width=True)
        if st.session_state.idx < len(df) - 1:
            cn.button("Sonraki ➡️", on_click=lambda: setattr(st.session_state, 'idx', st.session_state.idx+1), type="primary", use_container_width=True)

    else:
        st.title("Sonuçlar")
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
        if st.button("Tekrar Başla"):
            st.session_state.clear()
            st.rerun()
else:
    st.error("Excel yüklenemedi.")
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import google.generativeai as genai
import os
import nest_asyncio

nest_asyncio.apply()

# -------------------------------------------------
# SAYFA AYARI
# -------------------------------------------------
st.set_page_config(
    page_title="YDS Pro",
    page_icon="🎓",
    layout="wide"
)

# -------------------------------------------------
# SABİTLER
# -------------------------------------------------
SCORES_FILE = "lms_scores.csv"
EXAM_DURATION_MIN = 180

# -------------------------------------------------
# VERİ YÜKLEME
# -------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def load_exam(exam_id):
    files = [
        f"Sinav_{exam_id}.xlsx",
        f"sinav_{exam_id}.xlsx",
        f"Sinav_{exam_id}.csv"
    ]
    for f in files:
        if os.path.exists(f):
            df = pd.read_excel(f) if f.endswith("xlsx") else pd.read_csv(f)
            df.columns = df.columns.str.strip()
            df["Dogru_Cevap"] = (
                df["Dogru_Cevap"]
                .astype(str)
                .str.strip()
                .str.upper()
            )
            return df
    return None

def save_score(username, exam, score, correct, wrong, empty):
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    if os.path.exists(SCORES_FILE):
        df = pd.read_csv(SCORES_FILE)
    else:
        df = pd.DataFrame(columns=[
            "Kullanıcı", "Sınav", "Puan",
            "Doğru", "Yanlış", "Boş", "Tarih"
        ])
    df = pd.concat([df, pd.DataFrame([{
        "Kullanıcı": username,
        "Sınav": exam,
        "Puan": score,
        "Doğru": correct,
        "Yanlış": wrong,
        "Boş": empty,
        "Tarih": date
    }])], ignore_index=True)
    df.to_csv(SCORES_FILE, index=False)

# -------------------------------------------------
# SESSION DEFAULTS
# -------------------------------------------------
defaults = {
    "username": None,
    "exam_id": 1,
    "idx": 0,
    "answers": {},     # {idx: {"answer": "A", "time": datetime}}
    "marked": set(),
    "finish": False,
    "font_size": 16,
    "exam_mode": False,
    "end_ts": 0,
    "ai_cache": {},
    "api_key": "",
    "saved": False
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -------------------------------------------------
# GİRİŞ EKRANI
# -------------------------------------------------
if st.session_state.username is None:
    st.title("🎓 YDS PRO")
    name = st.text_input("Ad Soyad")
    if st.button("Giriş"):
        if name.strip():
            st.session_state.username = name.strip()
            st.session_state.end_ts = (
                datetime.now() + timedelta(minutes=EXAM_DURATION_MIN)
            ).timestamp() * 1000
            st.rerun()
    st.stop()

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
with st.sidebar:
    st.success(f"👤 {st.session_state.username}")

    # ⏳ SAYAÇ (JS – HATASIZ)
    if not st.session_state.finish:
        components.html("""
        <div id="cd" style="
            font-weight:bold;
            color:#dc2626;
            text-align:center;
            padding:6px;
            border:1px solid #fecaca;
            border-radius:6px;
            background:#fee2e2;">
        </div>

        <script>
        let end = {END_TS};

        setInterval(function() {{
            let d = end - new Date().getTime();

            if (d <= 0) {{
                document.getElementById("cd").innerHTML = "⛔ SÜRE BİTTİ";
            }} else {{
                let m = Math.floor((d % (1000*60*60)) / (1000*60));
                let s = Math.floor((d % (1000*60)) / 1000);
                document.getElementById("cd").innerHTML =
                    "⏳ " + m + ":" + (s < 10 ? "0" + s : s);
            }}
        }}, 1000);
        </script>
        """.format(END_TS=st.session_state.end_ts), height=70)

    st.session_state.exam_mode = st.toggle(
        "Sınav Modu",
        value=st.session_state.exam_mode
    )

    st.session_state.exam_id = st.selectbox(
        "Deneme Seç",
        range(1, 11),
        index=st.session_state.exam_id - 1
    )

    st.session_state.api_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=st.session_state.api_key
    )

# -------------------------------------------------
# SINAV VERİSİ
# -------------------------------------------------
df = load_exam(st.session_state.exam_id)
if df is None:
    st.error("❌ Sınav dosyası bulunamadı.")
    st.stop()

# Süre dolduysa otomatik bitir
if not st.session_state.finish:
    if datetime.now().timestamp() * 1000 > st.session_state.end_ts:
        st.session_state.finish = True
        st.rerun()

# -------------------------------------------------
# SINAV EKRANI
# -------------------------------------------------
if not st.session_state.finish:
    row = df.iloc[st.session_state.idx]

    st.subheader(f"Soru {st.session_state.idx + 1}")
    st.markdown(row["Soru"])

    options = [
        f"{c}) {row[c]}" for c in "ABCDE"
        if c in row and pd.notna(row[c])
    ]

    prev = st.session_state.answers.get(st.session_state.idx)
    prev_index = None
    if prev:
        prev_index = next(
            (i for i, o in enumerate(options)
             if o.startswith(prev["answer"])),
            None
        )

    sel = st.radio(
        "Cevabınız",
        options,
        index=prev_index
    )

    if sel:
        choice = sel[0]
        st.session_state.answers[st.session_state.idx] = {
            "answer": choice,
            "time": datetime.now()
        }

        if not st.session_state.exam_mode:
            if choice == row["Dogru_Cevap"]:
                st.success("✅ Doğru")
            else:
                st.error(f"❌ Yanlış (Doğru: {row['Dogru_Cevap']})")

    col1, col2 = st.columns(2)

    if col1.button("🤖 Çözümle"):
        if not st.session_state.api_key:
            st.warning("API Key giriniz.")
        else:
            genai.configure(api_key=st.session_state.api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")

            prompt = f"""
            Bu soru YDS formatındadır.

            1) Soru türünü belirt
            2) Doğru seçeneği açıkla
            3) Yanlış şıkların tuzaklarını anlat
            4) Sınav taktiği ver

            Türkçe yaz.

            Soru:
            {row['Soru']}

            Doğru cevap: {row['Dogru_Cevap']}
            """

            st.session_state.ai_cache[
                st.session_state.idx
            ] = model.generate_content(prompt).text
            st.rerun()

    if st.session_state.idx in st.session_state.ai_cache:
        st.info(st.session_state.ai_cache[st.session_state.idx])

    nav1, nav2 = st.columns(2)
    if nav1.button("⬅️ Önceki") and st.session_state.idx > 0:
        st.session_state.idx -= 1
        st.rerun()
    if nav2.button("➡️ Sonraki") and st.session_state.idx < len(df) - 1:
        st.session_state.idx += 1
        st.rerun()

    if st.button("🏁 SINAVI BİTİR", type="primary"):
        st.session_state.finish = True
        st.rerun()

# -------------------------------------------------
# SONUÇ EKRANI
# -------------------------------------------------
else:
    correct = sum(
        1 for i, a in st.session_state.answers.items()
        if a["answer"] == df.iloc[i]["Dogru_Cevap"]
    )
    wrong = len(st.session_state.answers) - correct
    empty = len(df) - len(st.session_state.answers)

    # ❗ ESKİ USUL YDS PUANI
    score = correct * 1.25

    if not st.session_state.saved:
        save_score(
            st.session_state.username,
            f"Deneme {st.session_state.exam_id}",
            score, correct, wrong, empty
        )
        st.session_state.saved = True

    st.title("📊 Sonuçlar")
    st.metric("Puan", round(score, 2))
    st.metric("Doğru", correct)
    st.metric("Yanlış", wrong)
    st.metric("Boş", empty)

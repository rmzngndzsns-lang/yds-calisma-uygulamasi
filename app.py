import streamlit as st
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="YDS Navigasyonlu Çalışma", page_icon="📖", layout="wide")

# CSS: Buton tasarımları
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 10px; height: 50px; font-size: 16px; }
    .sidebar-content { border: 1px solid #ddd; padding: 10px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- VERİ YÜKLEME ---
@st.cache_data
def veri_yukle():
    try:
        # Soruları SIRALI okuyoruz (sample/karıştırma yok)
        df = pd.read_excel("sorular.xlsx", engine="openpyxl")
        return df
    except Exception as e:
        st.error(f"Excel okunurken hata oluştu: {e}")
        return None

df = veri_yukle()

# --- DURUM YÖNETİMİ ---
if df is not None:
    if 'soru_no' not in st.session_state:
        st.session_state.soru_no = 0  # Kaçıncı sorudayız?
    if 'skor' not in st.session_state:
        st.session_state.skor = {"Dogru": 0, "Yanlis": 0}

    # --- YAN MENÜ (NAVİGASYON) ---
    with st.sidebar:
        st.title("🧩 Soru Paneli")
        st.write(f"✅ Doğru: {st.session_state.skor['Dogru']} | ❌ Yanlış: {st.session_state.skor['Yanlis']}")
        st.divider()
        
        # İstediğin soruya atlama listesi
        soru_listesi = [f"Soru {i+1}" for i in range(len(df))]
        secilen_soru = st.selectbox("Gitmek istediğin soruyu seç:", soru_listesi, index=st.session_state.soru_no)
        st.session_state.soru_no = soru_listesi.index(secilen_soru)
        
        if st.button("Skoru Sıfırla"):
            st.session_state.skor = {"Dogru": 0, "Yanlis": 0}
            st.rerun()

    # --- ANA EKRAN ---
    st.title(f"📝 YDS Denemesi - Soru {st.session_state.soru_no + 1}")
    
    current_soru = df.iloc[st.session_state.soru_no]
    
    # Soru Metni
    st.info(current_soru['Soru'])
    
    # Şıklar
    siklar = ['A', 'B', 'C', 'D', 'E']
    cols = st.columns(1) # Şıkları alt alta dizmek için
    
    for sik in siklar:
        if pd.notna(current_soru[sik]):
            if st.button(f"{sik}) {current_soru[sik]}", key=f"btn_{sik}"):
                dogru_cevap = str(current_soru['Dogru_Cevap']).strip().upper()
                
                if sik == dogru_cevap:
                    st.success(f"DOĞRU! 🎉 (Cevap: {dogru_cevap})")
                    st.session_state.skor["Dogru"] += 1
                else:
                    st.error(f"YANLIŞ! ❌ Doğru Cevap: {dogru_cevap}")
                    st.session_state.skor["Yanlis"] += 1

    st.divider()

    # --- KONTROL BUTONLARI (ATLAYABİLME ÖZELLİĞİ) ---
    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
    
    with nav_col1:
        if st.session_state.soru_no > 0:
            if st.button("⬅️ Önceki Soru"):
                st.session_state.soru_no -= 1
                st.rerun()
                
    with nav_col3:
        if st.session_state.soru_no < len(df) - 1:
            if st.button("Sonraki Soru ➡️"):
                st.session_state.soru_no += 1
                st.rerun()
    
    # İlerleme Çubuğu
    st.progress((st.session_state.soru_no + 1) / len(df))

else:
    st.warning("Lütfen sorular.xlsx dosyasının yüklü olduğundan emin olun.")
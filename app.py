import streamlit as st
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="YDS Çalışma", page_icon="📚", layout="centered")

# CSS: Butonları güzelleştir
st.markdown("""
<style>
div.stButton > button {
    width: 100%;
    border-radius: 12px;
    height: 60px;
    font-size: 18px;
    margin-bottom: 10px;
}
</style>""", unsafe_allow_html=True)

# Başlık
st.title("📚 YDS Soru Kampı")

# --- VERİ YÜKLEME ---
@st.cache_data
def veri_yukle():
    try:
        # Excel dosyasını okuyoruz
        df = pd.read_excel("sorular.xlsx", engine="openpyxl")
        # Soruları her açılışta karıştıralım (Shuffle)
        return df.sample(frac=1).reset_index(drop=True)
    except Exception as e:
        return None

# --- STATE (DURUM) YÖNETİMİ ---
if 'sorular' not in st.session_state:
    st.session_state.sorular = veri_yukle()
    st.session_state.index = 0
    st.session_state.dogru = 0
    st.session_state.yanlis = 0
    # Cevabın verilip verilmediğini kontrol etmek için:
    st.session_state.cevap_verildi = False 

# Dosya hatası kontrolü
if st.session_state.sorular is None:
    st.error("⚠️ 'sorular.xlsx' dosyası bulunamadı! GitHub'a yüklediğinden emin ol.")
    st.stop()

# Test Bitti mi?
if st.session_state.index >= len(st.session_state.sorular):
    st.balloons()
    st.success("🏁 Testi Tamamladın!")
    st.metric("Doğru Sayısı", st.session_state.dogru)
    st.metric("Yanlış Sayısı", st.session_state.yanlis)
    
    if st.button("🔄 Testi Başa Sar"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.stop()

# Şu anki soruyu al
soru = st.session_state.sorular.iloc[st.session_state.index]

# İlerleme Çubuğu
toplam_soru = len(st.session_state.sorular)
st.progress((st.session_state.index + 1) / toplam_soru)
st.caption(f"Soru {st.session_state.index + 1} / {toplam_soru}")

# Soruyu Ekrana Bas
st.markdown(f"### {soru['Soru']}")

# Şık Butonları
siklar = ['A', 'B', 'C', 'D', 'E']

# Eğer cevap henüz verilmediyse şıkları göster
if not st.session_state.cevap_verildi:
    for sik in siklar:
        if pd.notna(soru.get(sik)): # Şık boş değilse göster
            if st.button(f"{sik}) {soru[sik]}"):
                dogru_cev = str(soru['Dogru_Cevap']).strip().upper()
                
                if sik == dogru_cev:
                    st.session_state.dogru += 1
                    st.toast("Doğru! 🎉", icon="✅")
                else:
                    st.session_state.yanlis += 1
                    st.toast(f"Yanlış! Doğru cevap: {dogru_cev}", icon="❌")
                
                # Cevap verildi olarak işaretle ve sayfayı yenile
                st.session_state.cevap_verildi = True
                st.rerun()

# Cevap verildiyse sadece "Sonraki Soru" butonunu göster
else:
    st.info("Cevap kaydedildi. Sıradakine geçelim.")
    if st.button("Sonraki Soru ➡️", type="primary"):
        st.session_state.index += 1
        st.session_state.cevap_verildi = False
        st.rerun()
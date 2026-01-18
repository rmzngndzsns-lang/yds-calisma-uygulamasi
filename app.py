import streamlit as st
import pandas as pd
import random

# Sayfa Ayarları
st.set_page_config(page_title="YDS Pro", page_icon="🎓", layout="centered")

# --- AKILLI VERİ YÜKLEYİCİ ---
@st.cache_data
def veri_yukle():
    try:
        # Excel'i başlık yokmuş gibi (header=None) ham haliyle oku
        df_ham = pd.read_excel("sorular.xlsx", header=None, engine="openpyxl")
        
        # --- BAŞLIK SATIRINI ARAMA ---
        # İlk 20 satırı tara, içinde "Soru" ve "A" geçen satırı bul
        baslik_satiri_index = -1
        
        for i in range(min(20, len(df_ham))):
            satir_verisi = df_ham.iloc[i].astype(str).str.lower().tolist()
            # Eğer satırda hem 'soru' hem 'a' harfi/kelimesi varsa bu başlıktır
            if any("soru" in s for s in satir_verisi) and any("a" in s for s in satir_verisi):
                baslik_satiri_index = i
                break
        
        if baslik_satiri_index == -1:
            st.error("❌ Excel içinde 'Soru', 'A', 'B' gibi başlıkların olduğu satır bulunamadı!")
            return None

        # --- VERİYİ TEMİZLEME ---
        # Başlık satırını yeni sütun isimleri yap
        df_ham.columns = df_ham.iloc[baslik_satiri_index]
        
        # Başlıktan sonraki kısmı al (Asıl veriler)
        df_temiz = df_ham[baslik_satiri_index + 1:].reset_index(drop=True)
        
        # Sütun isimlerindeki boşlukları temizle (Örn: "Soru " -> "Soru")
        df_temiz.columns = df_temiz.columns.astype(str).str.strip()
        
        # Sadece ihtiyacımız olan sütunları seçelim (Gereksiz sütunları at)
        gerekli_sutunlar = ['Soru', 'A', 'B', 'C', 'D', 'E', 'Dogru_Cevap']
        
        # Excel'deki sütun isimleri bazen büyük/küçük harf farklı olabilir, düzeltelim:
        # (Bu kısım biraz teknik, sütunları eşleştiriyor)
        mevcut_sutunlar = df_temiz.columns.tolist()
        seçilenler = []
        for gerekli in gerekli_sutunlar:
            # Excel'deki sütun ismini bul (Büyük küçük harf duyarsız)
            bulunan = next((col for col in mevcut_sutunlar if col.lower() == gerekli.lower()), None)
            if bulunan:
                seçilenler.append(bulunan)
        
        # Varsa o sütunları al
        if len(seçilenler) > 0:
            df_son = df_temiz[seçilenler].copy()
            # İsimleri standart hale getir (Bizim kodumuz 'Soru' istiyor, excelde 'soru' yazsa bile)
            df_son.columns = [col.capitalize() if col.lower() != 'dogru_cevap' else 'Dogru_Cevap' for col in df_son.columns]
            
            # Dogru_Cevap sütun adını zorla düzelt (Bazen 'Dogru_cevap' vb gelir)
            # Sütun listesinde 'Dogru_Cevap'a benzeyen hangisiyse onu bul ve düzelt
            cols = df_son.columns.tolist()
            for idx, c in enumerate(cols):
                if 'dogru' in c.lower() and 'cevap' in c.lower():
                    cols[idx] = 'Dogru_Cevap'
            df_son.columns = cols
            
        else:
            df_son = df_temiz # Eşleşme bulamazsa olduğu gibi bırak (Riskli ama denesin)

        # Soruları Karıştır
        return df_son.sample(frac=1).reset_index(drop=True)

    except Exception as e:
        st.error(f"Hata oluştu: {e}")
        return None

# --- STATE (DURUM) YÖNETİMİ ---
if 'sorular' not in st.session_state:
    st.session_state.sorular = veri_yukle()
    st.session_state.index = 0
    st.session_state.dogru = 0
    st.session_state.yanlis = 0
    st.session_state.cevaplandi = False 

# Veri kontrolü
if st.session_state.sorular is None or st.session_state.sorular.empty:
    st.warning("Veri yüklenemedi. Lütfen Excel dosyanızı kontrol edin.")
    st.stop()

# --- ARAYÜZ ---
# Başlık ve Skor
col1, col2 = st.columns([3, 1])
with col1:
    st.title("📚 YDS Kampı")
with col2:
    st.write(f"✅ {st.session_state.dogru} | ❌ {st.session_state.yanlis}")

# Test Bitti mi?
if st.session_state.index >= len(st.session_state.sorular):
    st.balloons()
    st.success("Test Bitti! 🎉")
    if st.button("🔄 Başa Dön"):
        st.cache_data.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.stop()

# Soruyu Getir
soru = st.session_state.sorular.iloc[st.session_state.index]

# İlerleme Çubuğu
st.progress((st.session_state.index + 1) / len(st.session_state.sorular))

# Soru Metni
st.markdown(f"### {soru.get('Soru', 'Soru Metni Bulunamadı')}")
st.write("---")

# Şıklar
siklar = ['A', 'B', 'C', 'D', 'E']

if not st.session_state.cevaplandi:
    for sik in siklar:
        # Şık metni boş değilse butonu koy
        sik_metni = soru.get(sik)
        if pd.notna(sik_metni):
            if st.button(f"{sik}) {sik_metni}", use_container_width=True):
                # Cevap Kontrolü
                dogru_cevap = str(soru.get('Dogru_Cevap', '')).strip().upper()
                
                if sik == dogru_cevap:
                    st.session_state.dogru += 1
                    st.toast("Doğru! 🎯", icon="✅")
                else:
                    st.session_state.yanlis += 1
                    st.toast(f"Yanlış! Doğru cevap: {dogru_cevap}", icon="❌")
                
                st.session_state.cevaplandi = True
                st.rerun()
else:
    st.info("Cevabın alındı.")
    if st.button("Sonraki Soru ➡️", type="primary", use_container_width=True):
        st.session_state.index += 1
        st.session_state.cevaplandi = False
        st.rerun()
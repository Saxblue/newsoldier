# app.py
"""
Streamlit uygulaması - ana çalışma dosyası.
Kullanım:
- streamlit run app.py
Ön koşullar:
- st.secrets içerisindeki GITHUB_TOKEN veya ortam değişkeni GITHUB_TOKEN ayarlı olmalı
- Repo owner ve repo name doğru ayarlanmalı (varsayılan Saxblue/newsoldier)
"""
import streamlit as st
import json
from datetime import datetime
from github_manager import GitHubManager
from token_manager import TokenManager
from data_processor import DataProcessor
from member_manager import MemberManager

st.set_page_config(page_title="BTag Affiliate System", layout="wide")

# -----------------------
# Ayarlar (repo bilgisi)
# -----------------------
DEFAULT_OWNER = "Saxblue"    # gerektiğinde değiştir
DEFAULT_REPO = "newsoldier"  # gerektiğinde değiştir
BRANCH = "main"

# -----------------------
# Token al (güvenli)
# -----------------------
try:
    GITHUB_TOKEN = TokenManager.get_github_token()
except Exception as e:
    st.error("GitHub token alınamadı. Lütfen st.secrets veya GITHUB_TOKEN env değişkeni ayarlayın.")
    st.stop()

# -----------------------
# GitHub Manager init
# -----------------------
gh = GitHubManager(owner=DEFAULT_OWNER, repo=DEFAULT_REPO, token=GITHUB_TOKEN, branch=BRANCH)

if not gh.is_connected():
    st.error("GitHub bağlantısı kurulamadı. Token veya repo bilgilerini kontrol et.")
    st.stop()

# -----------------------
# Manager'lar
# -----------------------
member_mgr = MemberManager(gh, file_path="members.json")

# -----------------------
# Uygulama başlığı
# -----------------------
st.title("BTag Affiliate System — Yönetim Paneli")
st.markdown("Github üzerinden JSON dosyalarını okuyup güncelleyebilirsiniz. Token güvenli şekilde st.secrets veya ENV ile sağlanmalı.")

# -----------------------
# Sidebar - dosya seçimi
# -----------------------
st.sidebar.header("Dosya İşlemleri")
file_choice = st.sidebar.selectbox("Hangi dosyayı görüntülemek/güncellemek istersin?",
                                   ["daily_data.json", "members.json", "token.json"])

# -----------------------
# Dosya yükleme / gösterme
# -----------------------
def load_json_from_github(path: str):
    try:
        data = gh.get_json(path)
        return data, None
    except FileNotFoundError:
        return None, f"{path} bulunamadı."
    except PermissionError as pe:
        return None, str(pe)
    except Exception as e:
        return None, f"Hata: {str(e)}"

data, err = load_json_from_github(file_choice)
if err:
    st.warning(err)
    if st.button("Dosya oluştur (boş)"):
        # boş içerikle oluştur
        default_content = {} if file_choice != "members.json" else []
        try:
            gh.update_json(file_choice, default_content, commit_message=f"Create {file_choice}")
            st.success(f"{file_choice} oluşturuldu.")
            data = default_content
        except Exception as e:
            st.error(f"Oluşturulamadı: {e}")

# show current data
st.subheader(f"İçerik: {file_choice}")
if data is None:
    st.info("Dosya yok veya okunamadı.")
else:
    st.json(data)

# -----------------------
# Eğer daily_data.json seçili ise günlük veri ekleme formu
# -----------------------
if file_choice == "daily_data.json":
    st.markdown("---")
    st.header("Günlük veri ekle")
    with st.form("add_daily"):
        date_input = st.date_input("Tarih (UTC)", value=datetime.utcnow().date())
        invest = st.number_input("Yatırım (numeric)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        withdraw = st.number_input("Çekim (numeric)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        note = st.text_input("Not (isteğe bağlı)")
        submitted = st.form_submit_button("Ekle ve GitHub'a kaydet")
        if submitted:
            key = date_input.strftime("%Y-%m-%d")
            entry = {"yatirim": invest, "cekim": withdraw}
            if note:
                entry["note"] = note
            # mevcut data'yı al ve güncelle
            existing = data if isinstance(data, dict) else {}
            updated = DataProcessor.add_daily_entry(existing, key, entry)
            try:
                res = gh.update_json("daily_data.json", updated, commit_message=f"Add daily entry {key}")
                st.success("Günlük veri kaydedildi.")
                st.json(updated)
                data = updated
            except PermissionError as pe:
                st.error(str(pe))
            except Exception as e:
                st.error(f"Kaydetme hatası: {e}")

# -----------------------
# Eğer members.json seçili ise üye ekleme
# -----------------------
if file_choice == "members.json":
    st.markdown("---")
    st.header("Üye yönetimi")
    with st.form("add_member"):
        m_id = st.text_input("Üye ID")
        m_name = st.text_input("Üye adı")
        m_meta = st.text_area("Diğer JSON metadata (ör: {\"level\":1})", value="{}")
        add_sub = st.form_submit_button("Üye Ekle/Güncelle")
        if add_sub:
            try:
                meta_obj = json.loads(m_meta) if m_meta.strip() else {}
            except Exception:
                st.error("Metadata JSON parse edilemedi.")
                meta_obj = {}

            member = {"id": m_id, "name": m_name}
            member.update(meta_obj)
            try:
                resp = member_mgr.add_member(member)
                st.success("Üye eklendi/güncellendi.")
            except Exception as e:
                st.error(f"Hata: {e}")

# -----------------------
# Eğer token.json seçili ise token dosyasını göster / düzenle (uyarı: hassas)
# -----------------------
if file_choice == "token.json":
    st.markdown("---")
    st.header("Token dosyası (UYARI: hassas veridir)")

    st.warning("token.json içinde hassas veriler olabilir. Bu verileri GitHub repo içinde saklamadan önce riskleri değerlendir.")
    if data is None:
        current_text = "{}"
    else:
        current_text = json.dumps(data, ensure_ascii=False, indent=2)

    edited = st.text_area("token.json içeriğini düzenle", value=current_text, height=300)
    if st.button("token.json'u GitHub'a kaydet"):
        try:
            parsed = json.loads(edited)
        except Exception:
            st.error("JSON parse hatası.")
            parsed = None
        if parsed is not None:
            try:
                gh.update_json("token.json", parsed, commit_message="Update token.json via app")
                st.success("token.json kaydedildi.")
            except PermissionError as pe:
                st.error(str(pe))
            except Exception as e:
                st.error(f"Kaydetme başarısız: {e}")

# -----------------------
# Footer / diagnostic
# -----------------------
st.sidebar.markdown("---")
st.sidebar.subheader("Diagnostic")
st.sidebar.write(f"Repo: {DEFAULT_OWNER}/{DEFAULT_REPO}@{BRANCH}")
st.sidebar.write(f"Connected: {gh.is_connected()}")

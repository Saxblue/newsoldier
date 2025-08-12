import streamlit as st
import pandas as pd
import json
import os
import requests
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import base64

# Streamlit sayfa konfigürasyonu
st.set_page_config(
    page_title="BTag Affiliate Takip Sistemi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS stil eklemeleri
st.markdown("""
<style>
.settings-button {
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 999;
    background-color: #f0f2f6;
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    padding: 8px 12px;
    cursor: pointer;
}
.settings-button:hover {
    background-color: #e0e0e0;
}
</style>
""", unsafe_allow_html=True)

class GitHubSync:
    """GitHub senkronizasyon sınıfı"""
    def __init__(self):
        self.github_repo = "Saxblue/newsoldier"
        self.github_branch = "main"
        self.github_api_url = "https://api.github.com"
        
    def get_github_token(self):
        """GitHub token'ını al"""
        try:
            # Önce ayrı github_token.json dosyasından dene
            if os.path.exists("github_token.json"):
                with open("github_token.json", 'r', encoding='utf-8') as f:
                    token_data = json.load(f)
                    return token_data.get("github_token", "")
            
            # Yoksa token.json'dan dene (geriye uyumluluk)
            with open("token.json", 'r', encoding='utf-8') as f:
                token_data = json.load(f)
                return token_data.get("github_token", "")
        except:
            return ""
    
    def upload_to_github(self, file_path, content, commit_message="Update data"):
        """Dosyayı GitHub'a yükle"""
        token = self.get_github_token()
        if not token:
            return False, "GitHub token bulunamadı"
        
        try:
            # Mevcut dosyayı kontrol et
            url = f"{self.github_api_url}/repos/{self.github_repo}/contents/{file_path}"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(url, headers=headers)
            sha = None
            if response.status_code == 200:
                sha = response.json().get("sha")
            
            # Dosya içeriğini base64'e çevir
            content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # Dosyayı güncelle/oluştur
            data = {
                "message": commit_message,
                "content": content_encoded,
                "branch": self.github_branch
            }
            
            if sha:
                data["sha"] = sha
            
            response = requests.put(url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                return True, "Başarıyla yüklendi"
            else:
                return False, f"GitHub API hatası: {response.status_code}"
                
        except Exception as e:
            return False, f"GitHub yükleme hatası: {str(e)}"
    
    def sync_json_file(self, local_file, github_file):
        """JSON dosyasını GitHub ile senkronize et"""
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            success, message = self.upload_to_github(github_file, content, f"Update {github_file}")
            return success, message
        except Exception as e:
            return False, f"Dosya okuma hatası: {str(e)}"

class TokenManager:
    """Token yönetimi için sınıf"""
    def __init__(self):
        self.token_file = "token.json"
        self.github_sync = GitHubSync()
        self.ensure_token_file()
    
    def ensure_token_file(self):
        """Token dosyasının varlığını kontrol et"""
        if not os.path.exists(self.token_file):
            default_token = {
                "token": "",
                "github_token": "",
                "api_url": "https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientWithdrawalRequestsWithTotals"
            }
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(default_token, f, ensure_ascii=False, indent=2)
    
    def load_token(self):
        """Token dosyasını yükle"""
        try:
            with open(self.token_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Token dosyası okuma hatası: {e}")
            return {"token": "", "api_url": ""}
    
    def save_token(self, token, api_url, github_token="", update_member_status=False):
        """Token dosyasını kaydet"""
        try:
            # Sadece API token ve URL'yi token.json'a kaydet (GitHub token ayrı dosyada)
            token_data = {
                "token": token,
                "api_url": api_url
            }
            
            # Yerel dosyaya kaydet
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, ensure_ascii=False, indent=2)
            
            # GitHub token varsa ayrı dosyaya kaydet
            if github_token:
                self.save_github_token(github_token)
            
            # GitHub'a senkronize et (artık güvenli)
            success, message = self.github_sync.sync_json_file(self.token_file, "token.json")
            if success:
                st.success(f"✅ Token hem yerel hem de GitHub'a kaydedildi!")
            else:
                st.warning(f"⚠️ Token yerel olarak kaydedildi, GitHub senkronizasyonu başarısız: {message}")
            
            # Üye durumlarını güncelle (isteğe bağlı)
            if update_member_status:
                st.info("🔄 Üye durumları güncelleniyor...")
                member_manager = MemberManager()
                updated_count, failed_count = member_manager.update_all_members_status()
                
                if updated_count > 0:
                    st.success(f"✅ {updated_count} üyenin durumu güncellendi!")
                if failed_count > 0:
                    st.warning(f"⚠️ {failed_count} üye için durum güncellenemedi")
                if updated_count == 0 and failed_count == 0:
                    st.info("📊 Tüm üye durumları güncel")
            
            return True
        except Exception as e:
            st.error(f"Token kaydetme hatası: {e}")
            return False
    
    def save_github_token(self, github_token):
        """Sadece GitHub token'ını kaydet"""
        try:
            # GitHub token'ı ayrı dosyada sakla (güvenlik için)
            github_token_data = {
                "github_token": github_token,
                "created_at": datetime.now().isoformat()
            }
            
            with open("github_token.json", 'w', encoding='utf-8') as f:
                json.dump(github_token_data, f, ensure_ascii=False, indent=2)
            
            # token.json'dan github_token alanını kaldır (varsa)
            current_data = self.load_token()
            if "github_token" in current_data:
                del current_data["github_token"]
                with open(self.token_file, 'w', encoding='utf-8') as f:
                    json.dump(current_data, f, ensure_ascii=False, indent=2)
                
                # Temizlenmiş token.json'ı GitHub'a yükle
                github_sync = GitHubSync()
                github_sync.sync_json_file(self.token_file, "token.json")
            
            st.success("✅ GitHub token güvenli olarak kaydedildi!")
            return True
        except Exception as e:
            st.error(f"GitHub token kaydetme hatası: {e}")
            return False

class DataProcessor:
    """Veri işleme sınıfı"""
    def __init__(self):
        self.daily_data_file = "daily_data.json"
        self.members_file = "members.json"
        self.github_sync = GitHubSync()
        self.ensure_data_files()
    
    def ensure_data_files(self):
        """Veri dosyalarını oluştur"""
        if not os.path.exists(self.daily_data_file):
            with open(self.daily_data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        
        if not os.path.exists(self.members_file):
            with open(self.members_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
    
    def process_excel_data(self, df):
        """Excel verisini işle"""
        column_mapping = {
            'ID': 'member_id',
            'Kullanıcı Adı': 'username', 
            'Müşteri Adı': 'customer_name',
            'Para Yatırma Sayısı': 'deposit_count',
            'Yatırımlar': 'total_deposits',
            'Para Çekme Sayısı': 'withdrawal_count',
            'Para Çekme Miktarı': 'total_withdrawals'
        }
        
        df_processed = df.copy()
        
        for old_col, new_col in column_mapping.items():
            if old_col in df_processed.columns:
                df_processed = df_processed.rename(columns={old_col: new_col})
        
        required_columns = ['member_id', 'username', 'customer_name', 'deposit_count', 
                          'total_deposits', 'withdrawal_count', 'total_withdrawals']
        
        for col in required_columns:
            if col not in df_processed.columns:
                df_processed[col] = 0
        
        numeric_columns = ['deposit_count', 'total_deposits', 'withdrawal_count', 'total_withdrawals']
        for col in numeric_columns:
            df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')
            df_processed[col] = df_processed[col].fillna(0)
        
        string_columns = ['member_id', 'username', 'customer_name'] 
        for col in string_columns:
            df_processed[col] = df_processed[col].astype(str)
            df_processed[col] = df_processed[col].fillna('')
        
        return df_processed[required_columns]
    
    def save_daily_data(self, processed_df, btag, date):
        """Günlük veriyi kaydet"""
        try:
            with open(self.daily_data_file, 'r', encoding='utf-8') as f:
                daily_data = json.load(f)
            
            date_str = date.strftime('%Y-%m-%d')
            
            if date_str not in daily_data:
                daily_data[date_str] = {}
            
            daily_data[date_str][btag] = processed_df.to_dict('records')
            
            # Yerel dosyaya kaydet
            with open(self.daily_data_file, 'w', encoding='utf-8') as f:
                json.dump(daily_data, f, ensure_ascii=False, indent=2)
            
            # GitHub'a senkronize et
            success, message = self.github_sync.sync_json_file(self.daily_data_file, "daily_data.json")
            if success:
                st.success(f"✅ Günlük veri hem yerel hem de GitHub'a kaydedildi!")
            else:
                st.warning(f"⚠️ Yerel kayıt başarılı, GitHub senkronizasyonu başarısız: {message}")
            
            return True
        except Exception as e:
            st.error(f"Veri kaydetme hatası: {e}")
            return False
            return False

class MemberManager:
    """Üye yönetimi sınıfı"""
    def __init__(self):
        self.members_file = "members.json"
        self.ensure_members_file()
        self.token_manager = TokenManager()
        self.github_sync = GitHubSync()
    
    def ensure_members_file(self):
        """Üye dosyasını oluştur"""
        if not os.path.exists(self.members_file):
            with open(self.members_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
    
    def get_all_members(self):
        """Tüm üyeleri getir"""
        try:
            with open(self.members_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def get_active_members(self):
        """Aktif üyeleri getir"""
        all_members = self.get_all_members()
        return [member for member in all_members if member.get('is_active', True)]
    
    def add_member(self, member_id, username, full_name):
        """Yeni üye ekle"""
        try:
            members = self.get_all_members()
            
            existing_member = next((m for m in members if m['member_id'] == str(member_id)), None)
            if existing_member:
                return False
            
            new_member = {
                "member_id": str(member_id),
                "username": username,
                "full_name": full_name,
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "last_deposit_date": None,
                "days_without_deposit": 0,
                "api_data": {}
            }
            
            members.append(new_member)
            
            with open(self.members_file, 'w', encoding='utf-8') as f:
                json.dump(members, f, ensure_ascii=False, indent=2)
            
            # GitHub'a senkronize et
            success, message = self.github_sync.sync_json_file(self.members_file, "members.json")
            if not success:
                st.warning(f"⚠️ Üye yerel olarak eklendi, GitHub senkronizasyonu başarısız: {message}")
            
            # Üye eklendikten sonra API'den veri çek
            self.fetch_member_api_data(str(member_id))
            
            return True
        except Exception as e:
            st.error(f"Üye ekleme hatası: {e}")
            return False
    
    def add_members_bulk(self, member_ids):
        """Toplu üye ekleme - API'den detaylı bilgilerle"""
        added_count = 0
        failed_ids = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, member_id in enumerate(member_ids):
            if member_id.strip():
                status_text.text(f"İşleniyor: {member_id.strip()}")
                
                # API'den üye bilgilerini çek
                member_data = self.fetch_member_api_data(member_id.strip())
                
                if member_data and member_data.get('username'):
                    success = self.add_member(
                        member_id.strip(),
                        member_data.get('username', f'User_{member_id}'),
                        member_data.get('full_name', f'Member {member_id}')
                    )
                    if success:
                        added_count += 1
                    else:
                        failed_ids.append(member_id.strip())
                else:
                    failed_ids.append(member_id.strip())
                
                # Progress güncellemesi
                progress = (i + 1) / len(member_ids)
                progress_bar.progress(progress)
        
        progress_bar.empty()
        status_text.empty()
        
        if failed_ids:
            st.warning(f"⚠️ {len(failed_ids)} ID için veri çekilemedi: {', '.join(failed_ids[:5])}{'...' if len(failed_ids) > 5 else ''}")
        
        return added_count
    
    def fetch_member_api_data(self, member_id):
        """API'den üye verilerini çek"""
        try:
            token_data = self.token_manager.load_token()
            token = token_data.get('token', '')
            
            if not token:
                return None
            
            # Kim.py'deki API yapısını kullan
            api_url = f"https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientById?id={member_id}"
            
            headers = {
                'Authentication': token,
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Referer': 'https://backoffice.betconstruct.com/',
                'Origin': 'https://backoffice.betconstruct.com',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # API çağrısı yap
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # API verisini işle ve standartlaştır
                processed_data = self.process_api_response(data)
                
                # Üye veritabanını güncelle
                self.update_member_api_data(member_id, processed_data)
                
                return processed_data
            else:
                st.warning(f"API yanıt hatası ({response.status_code}): {member_id}")
                return None
                
        except Exception as e:
            st.warning(f"API çağrısı hatası: {e}")
            return None
    
    def process_api_response(self, api_data):
        """API yanıtını işle ve standartlaştır"""
        try:
            # Kim.py'deki yapıya göre Data içindeki bilgileri al
            data = api_data.get('Data', {})
            
            processed = {
                'username': data.get('Login', ''),
                'full_name': f"{data.get('FirstName', '')} {data.get('LastName', '')}".strip(),
                'email': data.get('Email', ''),
                'phone': data.get('Phone', ''),
                'status': data.get('Status', ''),
                'registration_date': data.get('CreatedLocalDate', ''),
                'last_login_date': data.get('LastLoginLocalDate', ''),
                'balance': data.get('Balance', 0),
                'currency': data.get('CurrencyId', 'TRY'),
                'partner_name': data.get('PartnerName', ''),
                'birth_date': data.get('BirthDate', ''),
                'last_deposit_date': data.get('LastDepositDateLocal', ''),
                'last_casino_bet': data.get('LastCasinoBetTimeLocal', ''),
                'total_deposits': 0,  # Bu bilgiler ayrı API'den gelebilir
                'total_withdrawals': 0,
                'deposit_count': 0,
                'withdrawal_count': 0
            }
            
            # Son yatırım tarihinden bugüne kadar geçen günleri hesapla
            if processed['last_deposit_date'] and processed['last_deposit_date'] != 'Bilinmiyor':
                try:
                    # Farklı tarih formatlarını dene
                    date_str = processed['last_deposit_date']
                    if 'T' in date_str:
                        last_deposit = datetime.fromisoformat(date_str.replace('Z', ''))
                    else:
                        last_deposit = datetime.strptime(date_str.split(' ')[0], '%d.%m.%Y')
                    
                    days_diff = (datetime.now() - last_deposit).days
                    processed['days_without_deposit'] = max(0, days_diff)
                except Exception as e:
                    processed['days_without_deposit'] = 999
            else:
                processed['days_without_deposit'] = 999
            
            return processed
            
        except Exception as e:
            st.error(f"API veri işleme hatası: {e}")
            return {}
    
    def update_member_api_data(self, member_id, api_data):
        """Üye API verisini güncelle"""
        try:
            members = self.get_all_members()
            
            for member in members:
                if member['member_id'] == str(member_id):
                    member['api_data'] = api_data
                    member['last_api_update'] = datetime.now().isoformat()
                    
                    # API'den gelen bilgileri üye kaydına ekle
                    if api_data:
                        member['email'] = api_data.get('email', '')
                        member['phone'] = api_data.get('phone', '')
                        member['balance'] = api_data.get('balance', 0)
                        member['currency'] = api_data.get('currency', 'TRY')
                        member['total_deposits'] = api_data.get('total_deposits', 0)
                        member['total_withdrawals'] = api_data.get('total_withdrawals', 0)
                        member['last_deposit_date'] = api_data.get('last_deposit_date', '')
                        member['last_casino_bet'] = api_data.get('last_casino_bet', '')
                        member['days_without_deposit'] = api_data.get('days_without_deposit', 999)
                        member['registration_date'] = api_data.get('registration_date', '')
                        member['last_login_date'] = api_data.get('last_login_date', '')
                        member['partner_name'] = api_data.get('partner_name', '')
                        member['birth_date'] = api_data.get('birth_date', '')
                    
                    break
            
            with open(self.members_file, 'w', encoding='utf-8') as f:
                json.dump(members, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            st.error(f"Üye API verisi güncelleme hatası: {e}")
    
    def toggle_member_status(self, member_id):
        """Üye durumunu değiştir"""
        try:
            members = self.get_all_members()
            
            for member in members:
                if member['member_id'] == str(member_id):
                    member['is_active'] = not member.get('is_active', True)
                    member['updated_at'] = datetime.now().isoformat()
                    break
            
            with open(self.members_file, 'w', encoding='utf-8') as f:
                json.dump(members, f, ensure_ascii=False, indent=2)
            
            # GitHub'a senkronize et
            success, message = self.github_sync.sync_json_file(self.members_file, "members.json")
            if not success:
                st.warning(f"⚠️ Üye durumu yerel olarak güncellendi, GitHub senkronizasyonu başarısız: {message}")
            
            return True
        except Exception as e:
            st.error(f"Üye durumu değiştirme hatası: {e}")
            return False
    
    def update_all_members_status(self):
        """Tüm üyelerin aktiflik durumunu API'den güncelle"""
        try:
            members = self.get_all_members()
            if not members:
                return 0, 0
            
            updated_count = 0
            failed_count = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, member in enumerate(members):
                member_id = member['member_id']
                status_text.text(f"Üye durumu güncelleniyor: {member.get('username', member_id)}")
                
                # API'den güncel veriyi çek
                api_data = self.fetch_member_api_data(member_id)
                
                if api_data:
                    # Aktiflik durumunu belirle
                    is_active = self.determine_member_activity_status(api_data)
                    
                    # Üye durumunu güncelle
                    if member.get('is_active') != is_active:
                        member['is_active'] = is_active
                        member['status_updated_at'] = datetime.now().isoformat()
                        member['status_reason'] = self.get_status_reason(api_data)
                        updated_count += 1
                else:
                    failed_count += 1
                
                # Progress güncellemesi
                progress = (i + 1) / len(members)
                progress_bar.progress(progress)
            
            # Dosyayı kaydet
            with open(self.members_file, 'w', encoding='utf-8') as f:
                json.dump(members, f, ensure_ascii=False, indent=2)
            
            # GitHub'a senkronize et
            success, message = self.github_sync.sync_json_file(self.members_file, "members.json")
            
            progress_bar.empty()
            status_text.empty()
            
            return updated_count, failed_count
            
        except Exception as e:
            st.error(f"Üye durumu güncelleme hatası: {e}")
            return 0, 0
    
    def determine_member_activity_status(self, api_data):
        """API verisine göre üye aktiflik durumunu belirle"""
        try:
            # Son yatırım tarihi kontrolü
            days_without_deposit = api_data.get('days_without_deposit', 999)
            
            # API'den gelen durum bilgisi
            api_status = api_data.get('status', '')
            
            # Aktiflik kriterleri:
            # 1. Son 30 gün içinde yatırım yapmış
            # 2. API durumu aktif
            # 3. Hesap bloke değil
            
            if days_without_deposit <= 30:  # Son 30 günde yatırım var
                return True
            elif api_status and api_status.lower() in ['active', 'aktif', '1']:
                return True
            elif days_without_deposit > 90:  # 90 günden fazla yatırım yok
                return False
            else:
                return True  # Belirsiz durumlarda aktif kabul et
                
        except Exception as e:
            return True  # Hata durumunda aktif kabul et
    
    def get_status_reason(self, api_data):
        """Durum değişikliği sebebini belirle"""
        try:
            days_without_deposit = api_data.get('days_without_deposit', 999)
            api_status = api_data.get('status', '')
            
            if days_without_deposit <= 30:
                return "Son 30 günde yatırım yaptı"
            elif days_without_deposit > 90:
                return f"{days_without_deposit} gündür yatırım yapmadı"
            elif api_status:
                return f"API durumu: {api_status}"
            else:
                return "Otomatik güncelleme"
                
        except Exception as e:
            return "Bilinmeyen sebep"

def show_settings_modal():
    """Ayarlar modalını göster"""
    token_manager = TokenManager()
    token_data = token_manager.load_token()
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ API Ayarları")
    
    # Mevcut token göster
    with st.sidebar.expander("Mevcut Token Bilgileri"):
        st.code(token_data.get('token', 'Token bulunamadı'), language='text')
        st.text(f"API URL: {token_data.get('api_url', '')}")
        
        # GitHub token'ı ayrı dosyadan kontrol et
        github_sync = GitHubSync()
        github_token = github_sync.get_github_token()
        if github_token:
            st.text(f"GitHub Token: {'*' * 20}...{github_token[-4:] if len(github_token) > 4 else '****'}")
        else:
            st.text("GitHub Token: Girilmemiş")
    
    # Yeni token girişi
    st.sidebar.markdown("**API Token Bilgileri:**")
    new_token = st.sidebar.text_input("API Token", value=token_data.get('token', ''), type='password')
    new_api_url = st.sidebar.text_input("API URL", value=token_data.get('api_url', ''))
    
    st.sidebar.markdown("**GitHub Senkronizasyon:**")
    # GitHub token'ı ayrı dosyadan al
    github_sync = GitHubSync()
    current_github_token = github_sync.get_github_token()
    new_github_token = st.sidebar.text_input("GitHub Token", value=current_github_token, type='password', help="GitHub Personal Access Token (repo yazma yetkisi gerekli)")
    
    # Üye durumu güncelleme seçeneği
    st.sidebar.markdown("**Üye Yönetimi:**")
    update_members = st.sidebar.checkbox("🔄 API token değiştirildiğinde üye durumlarını güncelle", help="Yeni API token ile tüm üyelerin aktif/pasif durumlarını kontrol eder")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("💾 API Token Kaydet", type='primary'):
            if new_token and new_api_url:
                success = token_manager.save_token(new_token, new_api_url, "", update_members)
                if success:
                    st.sidebar.success("✅ API Token başarıyla kaydedildi!")
                    st.rerun()
                else:
                    st.sidebar.error("❌ Token kaydetme hatası!")
            else:
                st.sidebar.warning("⚠️ API Token ve URL alanlarını doldurun!")
    
    with col2:
        if st.button("🔗 GitHub Token Kaydet"):
            if new_github_token:
                success = token_manager.save_github_token(new_github_token)
                if success:
                    st.sidebar.success("✅ GitHub Token kaydedildi!")
                    st.rerun()
                else:
                    st.sidebar.error("❌ GitHub Token kaydetme hatası!")
            else:
                st.sidebar.warning("⚠️ GitHub Token alanını doldurun!")

def show_dashboard():
    """Ana sayfa göster"""
    st.header("🏠 Ana Sayfa")
    
    member_manager = MemberManager()
    data_processor = DataProcessor()
    
    current_month = datetime.now().strftime("%Y-%m")
    st.subheader(f"📅 Mevcut Ay: {datetime.now().strftime('%B %Y')}")
    
    members = member_manager.get_active_members()
    total_members = len(members)
    
    # Günlük verileri yükle
    try:
        with open(data_processor.daily_data_file, 'r', encoding='utf-8') as f:
            daily_data = json.load(f)
    except:
        daily_data = {}
    
    # Bu ay için toplam hesaplamaları
    current_month_data = {}
    total_deposits = 0
    total_withdrawals = 0
    total_net = 0
    
    # Aktif üyelerin ID'lerini al
    active_member_ids = [str(m['member_id']) for m in members]
    
    for date, btag_data in daily_data.items():
        if date.startswith(current_month):
            for btag, records in btag_data.items():
                for record in records:
                    # Sadece aktif üyelerin verilerini dahil et
                    member_id = str(record.get('member_id', ''))
                    if member_id in active_member_ids:
                        total_deposits += record.get('total_deposits', 0)
                        total_withdrawals += record.get('total_withdrawals', 0)
    
    total_net = total_deposits - total_withdrawals
    
    # Metrikler
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Toplam Üye", total_members)
    
    with col2:
        # Pasif üyeler (1 haftadan fazla yatırım yapmayan)
        passive_members = len([m for m in members if m.get('days_without_deposit', 0) > 7])
        st.metric("⚠️ Pasif Üyeler", passive_members)
    
    with col3:
        st.metric("💰 Toplam Yatırım", f"{total_deposits:,.0f} TL")
    
    with col4:
        st.metric("💸 Toplam Çekim", f"{total_withdrawals:,.0f} TL")
    
    # Net kar/zarar
    st.markdown("---")
    col_net1, col_net2, col_net3 = st.columns([1, 2, 1])
    with col_net2:
        if total_net >= 0:
            st.success(f"📈 **Net Kar: {total_net:,.0f} TL**")
        else:
            st.error(f"📉 **Net Zarar: {abs(total_net):,.0f} TL**")
    
    st.markdown("---")
    
    # Günlük istatistikler
    if daily_data:
        st.subheader("📊 Son 7 Günün İstatistikleri")
        
        # Son 7 günün verilerini al
        recent_dates = sorted(daily_data.keys())[-7:]
        daily_stats = []
        
        for date in recent_dates:
            date_deposits = 0
            date_withdrawals = 0
            date_deposit_count = 0
            date_withdrawal_count = 0
            
            for btag, records in daily_data[date].items():
                for record in records:
                    # Sadece aktif üyelerin verilerini dahil et
                    member_id = str(record.get('member_id', ''))
                    if member_id in active_member_ids:
                        date_deposits += record.get('total_deposits', 0)
                        date_withdrawals += record.get('total_withdrawals', 0)
                        date_deposit_count += record.get('deposit_count', 0)
                        date_withdrawal_count += record.get('withdrawal_count', 0)
            
            daily_stats.append({
                'Tarih': date,
                'Yatırım Adedi': date_deposit_count,
                'Yatırım Miktarı': date_deposits,
                'Çekim Adedi': date_withdrawal_count,
                'Çekim Miktarı': date_withdrawals,
                'Net': date_deposits - date_withdrawals
            })
        
        if daily_stats:
            df_stats = pd.DataFrame(daily_stats)
            
            # Grafik
            fig = px.bar(df_stats, x='Tarih', y=['Yatırım Miktarı', 'Çekim Miktarı'], 
                        title='Son 7 Günün Yatırım-Çekim Grafiği',
                        color_discrete_map={'Yatırım Miktarı': 'green', 'Çekim Miktarı': 'red'})
            st.plotly_chart(fig, use_container_width=True)
            
            # Tablo
            def color_net(val):
                color = 'green' if val >= 0 else 'red'
                return f'color: {color}; font-weight: bold'
            
            styled_df = df_stats.style.map(color_net, subset=['Net'])
            styled_df = styled_df.format({
                'Yatırım Miktarı': '{:,.0f} TL',
                'Çekim Miktarı': '{:,.0f} TL', 
                'Net': '{:,.0f} TL'
            })
            st.dataframe(styled_df, use_container_width=True)
    
    st.markdown("---")
    
    # Pasif üye uyarıları
    if passive_members > 0:
        st.warning(f"🚨 {passive_members} üye 7 günden fazladır yatırım yapmıyor!")
        
        with st.expander("Pasif Üyeleri Göster"):
            passive_list = [m for m in members if m.get('days_without_deposit', 0) > 7]
            for member in passive_list:
                days = member.get('days_without_deposit', 0)
                st.write(f"• {member['full_name']} ({member['username']}) - {days} gündür yatırım yapmıyor")

def show_excel_upload():
    """Excel yükleme sayfası"""
    st.header("📤 Excel Dosyası Yükleme")
    
    data_processor = DataProcessor()
    member_manager = MemberManager()
    
    btag_input = st.text_input("🏷️ BTag Numarası", placeholder="Örnek: 2424878")
    
    uploaded_file = st.file_uploader(
        "📁 Players Report Excel Dosyasını Seçin",
        type=['xlsx', 'xls'],
        help="players-report.xlsx formatında dosya yükleyin"
    )
    
    if uploaded_file and btag_input:
        try:
            df = pd.read_excel(uploaded_file)
            st.success(f"✅ Excel dosyası başarıyla yüklendi! {len(df)} satır bulundu.")
            
            with st.expander("📋 Veri Önizleme"):
                st.dataframe(df.head(), use_container_width=True)
            
            if 'BTag' in df.columns:
                filtered_df = df[df['BTag'].astype(str) == str(btag_input)]
                st.info(f"🎯 BTag {btag_input} için {len(filtered_df)} kayıt bulundu.")
                
                if len(filtered_df) > 0:
                    processed_data = data_processor.process_excel_data(filtered_df)
                    
                    # Yeni üye kontrolü
                    current_members = member_manager.get_all_members()
                    current_member_ids = [str(m['member_id']) for m in current_members]
                    
                    new_members = []
                    for _, row in processed_data.iterrows():
                        if str(row['member_id']) not in current_member_ids:
                            new_members.append({
                                'member_id': str(row['member_id']),
                                'username': row['username'],
                                'full_name': row['customer_name']
                            })
                    
                    if new_members:
                        st.warning(f"🆕 {len(new_members)} yeni üye bulundu!")
                        
                        new_members_df = pd.DataFrame(new_members)
                        st.dataframe(new_members_df, use_container_width=True)
                        
                        if st.button("➕ Yeni Üyeleri Ekle"):
                            for member in new_members:
                                member_manager.add_member(
                                    member['member_id'],
                                    member['username'],
                                    member['full_name']
                                )
                            st.success("✅ Yeni üyeler başarıyla eklendi!")
                            st.rerun()
                    
                    # İşlenmiş veriyi göster
                    st.subheader("📊 İşlenmiş Veriler")
                    
                    display_df = processed_data.copy()
                    display_df = display_df.rename(columns={
                        'member_id': 'Üye ID',
                        'username': 'Kullanıcı Adı',
                        'customer_name': 'Müşteri Adı',
                        'deposit_count': 'Yatırım Adedi',
                        'total_deposits': 'Yatırım Miktarı',
                        'withdrawal_count': 'Çekim Adedi',
                        'total_withdrawals': 'Çekim Miktarı'
                    })
                    display_df['Net Miktar'] = display_df['Yatırım Miktarı'] - display_df['Çekim Miktarı']
                    
                    def highlight_totals(val):
                        if val > 0:
                            return 'background-color: lightgreen'
                        elif val < 0:
                            return 'background-color: lightcoral'
                        else:
                            return 'background-color: lightgray'
                    
                    styled_df = display_df.style.map(highlight_totals, subset=['Net Miktar'])
                    styled_df = styled_df.format({
                        'Yatırım Miktarı': '{:,.0f} TL',
                        'Çekim Miktarı': '{:,.0f} TL',
                        'Net Miktar': '{:,.0f} TL'
                    })
                    st.dataframe(styled_df, use_container_width=True)
                    
                    # Kayıt işlemi
                    st.subheader("💾 Kayıt İşlemi")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        selected_date = st.date_input(
                            "📅 Kayıt Tarihi",
                            value=datetime.now(),
                            help="Verilerin hangi tarihe kaydedileceğini seçin"
                        )
                    
                    with col2:
                        if st.button("💾 Kaydet", type="primary"):
                            success = data_processor.save_daily_data(
                                processed_data,
                                btag_input,
                                selected_date
                            )
                            
                            if success:
                                st.success("✅ Veriler başarıyla kaydedildi!")
                            else:
                                st.error("❌ Kayıt sırasında hata oluştu!")
                
                else:
                    st.warning(f"⚠️ BTag {btag_input} için veri bulunamadı.")
            
            else:
                st.error("❌ Excel dosyasında 'BTag' sütunu bulunamadı!")
        
        except Exception as e:
            st.error(f"❌ Dosya işlenirken hata oluştu: {str(e)}")

def show_member_management():
    """Üye yönetimi sayfası"""
    st.header("👥 Üye Yönetimi")
    
    member_manager = MemberManager()
    
    # Üye ekleme seçenekleri
    with st.expander("➕ Üye Ekleme"):
        tab1, tab2 = st.tabs(["Tekli Ekleme", "Toplu Ekleme"])
        
        with tab1:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                new_member_id = st.text_input("🆔 Üye ID")
            with col2:
                new_username = st.text_input("👤 Kullanıcı Adı")
            with col3:
                new_fullname = st.text_input("📝 İsim Soyisim")
            
            if st.button("➕ Üye Ekle"):
                if new_member_id:
                    success = member_manager.add_member(new_member_id, new_username, new_fullname)
                    if success:
                        st.success("✅ Üye başarıyla eklendi!")
                        st.rerun()
                    else:
                        st.error("❌ Bu üye zaten mevcut!")
                else:
                    st.warning("⚠️ En az Üye ID alanını doldurun!")
        
        with tab2:
            st.write("Her satıra bir Üye ID girin:")
            bulk_ids = st.text_area("Üye ID'leri", placeholder="303364529\n303340703\n303000951", height=150)
            
            if st.button("➕ Toplu Ekle"):
                if bulk_ids:
                    id_list = bulk_ids.strip().split('\n')
                    added_count = member_manager.add_members_bulk(id_list)
                    st.success(f"✅ {added_count} üye başarıyla eklendi!")
                    st.rerun()
                else:
                    st.warning("⚠️ Üye ID'leri girin!")
    
    # Üye listesi
    st.subheader("📋 Üye Listesi")
    
    members = member_manager.get_all_members()
    if members:
        search_term = st.text_input("🔍 Üye Ara", placeholder="İsim, kullanıcı adı veya ID ile ara...")
        
        if search_term:
            filtered_members = [
                m for m in members 
                if search_term.lower() in m['full_name'].lower() 
                or search_term.lower() in m['username'].lower()
                or search_term in str(m['member_id'])
            ]
        else:
            filtered_members = members
        
        # Üye tablosu
        for i, member in enumerate(filtered_members):
            # Ana satır
            col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 2, 1, 1, 1])
            
            with col1:
                st.write(f"🆔 {member['member_id']}")
            with col2:
                st.write(f"👤 {member['username']}")
            with col3:
                st.write(f"📝 {member['full_name']}")
            with col4:
                status = "✅ Aktif" if member.get('is_active', True) else "❌ Banlandı"
                st.write(status)
            with col5:
                days_without = member.get('days_without_deposit', 0)
                if days_without > 7:
                    st.error(f"⚠️ {days_without} gün")
                elif days_without > 0:
                    st.warning(f"🟡 {days_without} gün")
                else:
                    st.success("🟢 Aktif")
            with col6:
                if member.get('is_active', True):
                    if st.button(f"🚫 Ban", key=f"ban_{member['member_id']}"):
                        member_manager.toggle_member_status(member['member_id'])
                        st.success(f"Üye {member['username']} banlandı!")
                        st.rerun()
                else:
                    if st.button(f"✅ Aktif", key=f"unban_{member['member_id']}"):
                        member_manager.toggle_member_status(member['member_id'])
                        st.success(f"Üye {member['username']} aktif edildi!")
                        st.rerun()
            
            # Detay bilgileri (API'den gelen)
            if member.get('api_data') or member.get('email') or member.get('phone'):
                with st.expander(f"📋 {member['username']} - Detay Bilgileri"):
                    detail_col1, detail_col2, detail_col3 = st.columns(3)
                    
                    with detail_col1:
                        st.write(f"📧 **Email:** {member.get('email', 'Bilinmiyor')}")
                        st.write(f"📞 **Telefon:** {member.get('phone', 'Bilinmiyor')}")
                        st.write(f"💰 **Bakiye:** {member.get('balance', 0)} {member.get('currency', 'TRY')}")
                    
                    with detail_col2:
                        st.write(f"📅 **Kayıt Tarihi:** {member.get('registration_date', 'Bilinmiyor')}")
                        st.write(f"🕐 **Son Giriş:** {member.get('last_login_date', 'Bilinmiyor')}")
                        st.write(f"💳 **Son Yatırım:** {member.get('last_deposit_date', 'Bilinmiyor')}")
                    
                    with detail_col3:
                        st.write(f"🎰 **Son Casino:** {member.get('last_casino_bet', 'Bilinmiyor')}")
                        st.write(f"👥 **Partner:** {member.get('partner_name', 'Bilinmiyor')}")
                        st.write(f"🎂 **Doğum Tarihi:** {member.get('birth_date', 'Bilinmiyor')}")
                        
                        # API verilerini güncelle butonu
                        if st.button(f"🔄 API Güncelle", key=f"refresh_{member['member_id']}"):
                            with st.spinner("API'den veriler çekiliyor..."):
                                member_manager.fetch_member_api_data(member['member_id'])
                            st.success("✅ API verileri güncellendi!")
                            st.rerun()
        
        st.info(f"📊 Toplam {len(filtered_members)} üye gösteriliyor")
    
    else:
        st.info("👥 Henüz üye bulunmuyor.")

def show_reports():
    """Raporlar sayfası"""
    st.header("📊 Detaylı Raporlar")
    
    data_processor = DataProcessor()
    member_manager = MemberManager()
    
    # Günlük verileri yükle
    try:
        with open(data_processor.daily_data_file, 'r', encoding='utf-8') as f:
            daily_data = json.load(f)
    except:
        daily_data = {}
        st.warning("Henüz veri bulunmuyor.")
        return
    
    if not daily_data:
        st.info("Rapor oluşturmak için önce veri yüklemeniz gerekiyor.")
        return
    
    # Tarih aralığı seçimi
    st.subheader("📅 Rapor Dönemi Seçin")
    col1, col2 = st.columns(2)
    
    available_dates = sorted(daily_data.keys())
    min_date = datetime.strptime(available_dates[0], '%Y-%m-%d').date() if available_dates else datetime.now().date()
    max_date = datetime.strptime(available_dates[-1], '%Y-%m-%d').date() if available_dates else datetime.now().date()
    
    with col1:
        start_date = st.date_input("Başlangıç Tarihi", value=min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("Bitiş Tarihi", value=max_date, min_value=min_date, max_value=max_date)
    
    # Rapor oluştur
    if st.button("📋 Rapor Oluştur"):
        st.markdown("---")
        
        # Seçilen tarih aralığındaki verileri filtrele
        filtered_data = []
        total_deposits = 0
        total_withdrawals = 0
        member_summary = {}
        
        # Aktif üyelerin ID'lerini al
        all_members = member_manager.get_all_members()
        active_member_ids = [str(m['member_id']) for m in all_members if m.get('is_active', True)]
        
        for date_str in daily_data:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            if start_date <= date_obj <= end_date:
                for btag, records in daily_data[date_str].items():
                    for record in records:
                        member_id = str(record.get('member_id', ''))
                        # Sadece aktif üyelerin verilerini dahil et
                        if member_id not in active_member_ids:
                            continue
                            
                        deposits = record.get('total_deposits', 0)
                        withdrawals = record.get('total_withdrawals', 0)
                        deposit_count = record.get('deposit_count', 0)
                        withdrawal_count = record.get('withdrawal_count', 0)
                        
                        filtered_data.append({
                            'Tarih': date_str,
                            'BTag': btag,
                            'Üye ID': member_id,
                            'Kullanıcı Adı': record.get('username', ''),
                            'Müşteri Adı': record.get('customer_name', ''),
                            'Yatırım Adedi': deposit_count,
                            'Yatırım': deposits,
                            'Çekim Adedi': withdrawal_count,
                            'Çekim': withdrawals,
                            'Net': deposits - withdrawals
                        })
                        
                        total_deposits += deposits
                        total_withdrawals += withdrawals
                        
                        # Üye bazında özet
                        if member_id not in member_summary:
                            member_summary[member_id] = {
                                'username': record.get('username', ''),
                                'customer_name': record.get('customer_name', ''),
                                'deposits': 0,
                                'withdrawals': 0,
                                'deposit_count': 0,
                                'withdrawal_count': 0
                            }
                        member_summary[member_id]['deposits'] += deposits
                        member_summary[member_id]['withdrawals'] += withdrawals
                        member_summary[member_id]['deposit_count'] += deposit_count
                        member_summary[member_id]['withdrawal_count'] += withdrawal_count
        
        if filtered_data:
            total_net = total_deposits - total_withdrawals
            
            # Genel özet
            st.subheader("📈 Genel Özet")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📅 Toplam Gün", (end_date - start_date).days + 1)
            with col2:
                st.metric("💰 Toplam Yatırım", f"{total_deposits:,.0f} TL")
            with col3:
                st.metric("💸 Toplam Çekim", f"{total_withdrawals:,.0f} TL")
            with col4:
                if total_net >= 0:
                    st.metric("📈 Net Kar", f"{total_net:,.0f} TL", delta=None, delta_color="normal")
                else:
                    st.metric("📉 Net Zarar", f"{abs(total_net):,.0f} TL", delta=None, delta_color="inverse")
            
            # Grafik - Günlük trend
            st.subheader("📊 Günlük Trend")
            df_daily = pd.DataFrame(filtered_data)
            daily_summary = df_daily.groupby('Tarih').agg({
                'Yatırım': 'sum',
                'Çekim': 'sum'
            }).reset_index()
            daily_summary['Net'] = daily_summary['Yatırım'] - daily_summary['Çekim']
            
            fig = px.line(daily_summary, x='Tarih', y=['Yatırım', 'Çekim'], 
                         title='Günlük Yatırım-Çekim Trendi',
                         color_discrete_map={'Yatırım': 'green', 'Çekim': 'red'})
            st.plotly_chart(fig, use_container_width=True)
            
            # Üye bazında özet
            st.subheader("👥 Üye Bazında Özet")
            member_report = []
            for member_id, data in member_summary.items():
                net = data['deposits'] - data['withdrawals']
                member_report.append({
                    'Üye ID': member_id,
                    'Kullanıcı Adı': data['username'],
                    'Müşteri Adı': data['customer_name'],
                    'Yatırım Adedi': data['deposit_count'],
                    'Yatırım Miktarı': data['deposits'],
                    'Çekim Adedi': data['withdrawal_count'],
                    'Çekim Miktarı': data['withdrawals'],
                    'Net': net
                })
            
            df_members = pd.DataFrame(member_report)
            df_members = df_members.sort_values('Net', ascending=False)
            
            # Renk kodlaması
            def highlight_net(val):
                color = 'background-color: lightgreen' if val > 0 else 'background-color: lightcoral' if val < 0 else 'background-color: lightgray'
                return color
            
            styled_members = df_members.style.map(highlight_net, subset=['Net'])
            styled_members = styled_members.format({
                'Yatırım Miktarı': '{:,.0f} TL',
                'Çekim Miktarı': '{:,.0f} TL',
                'Net': '{:,.0f} TL'
            })
            st.dataframe(styled_members, use_container_width=True)
            
            # Excel indirme
            st.subheader("📥 Raporu İndir")
            
            # Excel dosyası oluştur
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Genel özet
                summary_data = {
                    'Metrik': ['Toplam Gün', 'Toplam Yatırım', 'Toplam Çekim', 'Net Kar/Zarar'],
                    'Değer': [
                        (end_date - start_date).days + 1,
                        f"{total_deposits:,.0f} TL",
                        f"{total_withdrawals:,.0f} TL",
                        f"{total_net:,.0f} TL"
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Özet', index=False)
                
                # Günlük detay
                df_daily_detail = pd.DataFrame(filtered_data)
                df_daily_detail.to_excel(writer, sheet_name='Günlük Detay', index=False)
                
                # Üye bazında
                df_members.to_excel(writer, sheet_name='Üye Bazında', index=False)
            
            output.seek(0)
            
            st.download_button(
                label="📊 Excel Raporu İndir",
                data=output.read(),
                file_name=f"btag_raporu_{start_date}_{end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        else:
            st.warning("Seçilen tarih aralığında veri bulunamadı.")

def show_statistics():
    """İstatistik sayfası"""
    st.header("📊 Detaylı İstatistikler")
    
    data_processor = DataProcessor()
    member_manager = MemberManager()
    
    # Verileri yükle
    try:
        with open(data_processor.daily_data_file, 'r', encoding='utf-8') as f:
            daily_data = json.load(f)
    except:
        daily_data = {}
    
    if not daily_data:
        st.warning("⚠️ Henüz veri bulunmuyor. Önce Excel dosyası yükleyin.")
        return
    
    # Tarih aralığı seçimi
    st.sidebar.subheader("📅 Tarih Aralığı")
    
    available_dates = sorted(daily_data.keys())
    if available_dates:
        start_date = st.sidebar.date_input(
            "Başlangıç Tarihi",
            value=datetime.strptime(available_dates[0], '%Y-%m-%d').date()
        )
        end_date = st.sidebar.date_input(
            "Bitiş Tarihi", 
            value=datetime.strptime(available_dates[-1], '%Y-%m-%d').date()
        )
    else:
        st.error("Veri bulunamadı")
        return
    
    # Veri toplama
    member_stats = {}
    total_deposits = 0
    total_withdrawals = 0
    total_deposit_count = 0
    total_withdrawal_count = 0
    
    for date_str, btag_data in daily_data.items():
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        if start_date <= date_obj <= end_date:
            for btag, records in btag_data.items():
                for record in records:
                    member_id = str(record.get('member_id', ''))
                    username = record.get('username', '')
                    customer_name = record.get('customer_name', '')
                    deposit_count = record.get('deposit_count', 0)
                    deposit_amount = record.get('total_deposits', 0)
                    withdrawal_count = record.get('withdrawal_count', 0)
                    withdrawal_amount = record.get('total_withdrawals', 0)
                    
                    if member_id not in member_stats:
                        member_stats[member_id] = {
                            'username': username,
                            'customer_name': customer_name,
                            'total_deposits': 0,
                            'total_withdrawals': 0,
                            'deposit_count': 0,
                            'withdrawal_count': 0,
                            'net_amount': 0,
                            'days_active': 0
                        }
                    
                    member_stats[member_id]['total_deposits'] += deposit_amount
                    member_stats[member_id]['total_withdrawals'] += withdrawal_amount
                    member_stats[member_id]['deposit_count'] += deposit_count
                    member_stats[member_id]['withdrawal_count'] += withdrawal_count
                    member_stats[member_id]['days_active'] += 1
                    
                    total_deposits += deposit_amount
                    total_withdrawals += withdrawal_amount
                    total_deposit_count += deposit_count
                    total_withdrawal_count += withdrawal_count
    
    # Net miktarları hesapla
    for member_id in member_stats:
        member_stats[member_id]['net_amount'] = (
            member_stats[member_id]['total_deposits'] - 
            member_stats[member_id]['total_withdrawals']
        )
    
    # Genel özet metrikleri
    st.subheader("📈 Genel Özet")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Toplam Yatırım", f"{total_deposits:,.0f} TL")
        st.metric("🔢 Yatırım Adedi", f"{total_deposit_count:,}")
    
    with col2:
        st.metric("💸 Toplam Çekim", f"{total_withdrawals:,.0f} TL")
        st.metric("🔢 Çekim Adedi", f"{total_withdrawal_count:,}")
    
    with col3:
        net_total = total_deposits - total_withdrawals
        st.metric("📊 Net Kar/Zarar", f"{net_total:,.0f} TL")
        if total_deposit_count > 0:
            avg_deposit = total_deposits / total_deposit_count
            st.metric("📊 Ort. Yatırım", f"{avg_deposit:,.0f} TL")
    
    with col4:
        total_members = len(member_stats)
        st.metric("👥 Aktif Üye", total_members)
        if total_withdrawal_count > 0:
            avg_withdrawal = total_withdrawals / total_withdrawal_count
            st.metric("📊 Ort. Çekim", f"{avg_withdrawal:,.0f} TL")
    
    st.markdown("---")
    
    # En iyi performans gösteren üyeler
    st.subheader("🏆 Top Performans")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**💰 En Çok Yatırım Yapan Üyeler**")
        top_deposits = sorted(member_stats.items(), 
                            key=lambda x: x[1]['total_deposits'], reverse=True)[:10]
        
        top_deposits_data = []
        for member_id, stats in top_deposits:
            if stats['total_deposits'] > 0:
                top_deposits_data.append({
                    'Sıra': len(top_deposits_data) + 1,
                    'Kullanıcı Adı': stats['username'],
                    'Müşteri Adı': stats['customer_name'],
                    'Yatırım Miktarı': f"{stats['total_deposits']:,.0f} TL",
                    'Yatırım Adedi': stats['deposit_count']
                })
        
        if top_deposits_data:
            st.dataframe(pd.DataFrame(top_deposits_data), use_container_width=True)
        
        st.write("**🔢 En Sık Yatırım Yapan Üyeler**")
        top_deposit_count = sorted(member_stats.items(), 
                                 key=lambda x: x[1]['deposit_count'], reverse=True)[:10]
        
        top_count_data = []
        for member_id, stats in top_deposit_count:
            if stats['deposit_count'] > 0:
                top_count_data.append({
                    'Sıra': len(top_count_data) + 1,
                    'Kullanıcı Adı': stats['username'],
                    'Müşteri Adı': stats['customer_name'],
                    'Yatırım Adedi': stats['deposit_count'],
                    'Toplam Miktar': f"{stats['total_deposits']:,.0f} TL"
                })
        
        if top_count_data:
            st.dataframe(pd.DataFrame(top_count_data), use_container_width=True)
    
    with col2:
        st.write("**💸 En Çok Çekim Yapan Üyeler**")
        top_withdrawals = sorted(member_stats.items(), 
                               key=lambda x: x[1]['total_withdrawals'], reverse=True)[:10]
        
        top_withdrawals_data = []
        for member_id, stats in top_withdrawals:
            if stats['total_withdrawals'] > 0:
                top_withdrawals_data.append({
                    'Sıra': len(top_withdrawals_data) + 1,
                    'Kullanıcı Adı': stats['username'],
                    'Müşteri Adı': stats['customer_name'],
                    'Çekim Miktarı': f"{stats['total_withdrawals']:,.0f} TL",
                    'Çekim Adedi': stats['withdrawal_count']
                })
        
        if top_withdrawals_data:
            st.dataframe(pd.DataFrame(top_withdrawals_data), use_container_width=True)
        
        st.write("**📈 En Karlı Üyeler**")
        top_profitable = sorted(member_stats.items(), 
                              key=lambda x: x[1]['net_amount'], reverse=True)[:10]
        
        top_profit_data = []
        for member_id, stats in top_profitable:
            if stats['net_amount'] != 0:
                top_profit_data.append({
                    'Sıra': len(top_profit_data) + 1,
                    'Kullanıcı Adı': stats['username'],
                    'Müşteri Adı': stats['customer_name'],
                    'Net Kar': f"{stats['net_amount']:,.0f} TL",
                    'Yatırım': f"{stats['total_deposits']:,.0f} TL"
                })
        
        if top_profit_data:
            st.dataframe(pd.DataFrame(top_profit_data), use_container_width=True)
    
    st.markdown("---")
    
    # Grafik analizler
    st.subheader("📊 Grafik Analizleri")
    
    tab1, tab2, tab3 = st.tabs(["Dağılım Analizi", "Trend Analizi", "Karşılaştırma"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Yatırım miktarı dağılımı
            deposit_amounts = [stats['total_deposits'] for stats in member_stats.values() if stats['total_deposits'] > 0]
            if deposit_amounts:
                fig = px.histogram(x=deposit_amounts, nbins=20, 
                                 title='Yatırım Miktarı Dağılımı',
                                 labels={'x': 'Yatırım Miktarı (TL)', 'y': 'Üye Sayısı'})
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Çekim miktarı dağılımı
            withdrawal_amounts = [stats['total_withdrawals'] for stats in member_stats.values() if stats['total_withdrawals'] > 0]
            if withdrawal_amounts:
                fig = px.histogram(x=withdrawal_amounts, nbins=20,
                                 title='Çekim Miktarı Dağılımı',
                                 labels={'x': 'Çekim Miktarı (TL)', 'y': 'Üye Sayısı'})
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Günlük trend analizi
        daily_summary = {}
        for date_str, btag_data in daily_data.items():
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            if start_date <= date_obj <= end_date:
                daily_deposits = 0
                daily_withdrawals = 0
                daily_dep_count = 0
                daily_with_count = 0
                
                for btag, records in btag_data.items():
                    for record in records:
                        daily_deposits += record.get('total_deposits', 0)
                        daily_withdrawals += record.get('total_withdrawals', 0)
                        daily_dep_count += record.get('deposit_count', 0)
                        daily_with_count += record.get('withdrawal_count', 0)
                
                daily_summary[date_str] = {
                    'Yatırım Miktarı': daily_deposits,
                    'Çekim Miktarı': daily_withdrawals,
                    'Yatırım Adedi': daily_dep_count,
                    'Çekim Adedi': daily_with_count
                }
        
        if daily_summary:
            df_trend = pd.DataFrame(daily_summary).T
            df_trend.index = pd.to_datetime(df_trend.index)
            
            # Miktar trendi
            fig = px.line(df_trend, y=['Yatırım Miktarı', 'Çekim Miktarı'],
                         title='Günlük Miktar Trendi',
                         color_discrete_map={'Yatırım Miktarı': 'green', 'Çekim Miktarı': 'red'})
            st.plotly_chart(fig, use_container_width=True)
            
            # Adet trendi
            fig = px.line(df_trend, y=['Yatırım Adedi', 'Çekim Adedi'],
                         title='Günlük İşlem Adedi Trendi',
                         color_discrete_map={'Yatırım Adedi': 'blue', 'Çekim Adedi': 'orange'})
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Yatırım vs Çekim karşılaştırması
        member_comparison = []
        for member_id, stats in member_stats.items():
            if stats['total_deposits'] > 0 or stats['total_withdrawals'] > 0:
                member_comparison.append({
                    'Kullanıcı Adı': stats['username'],
                    'Yatırım Miktarı': stats['total_deposits'],
                    'Çekim Miktarı': stats['total_withdrawals'],
                    'Yatırım Adedi': stats['deposit_count'],
                    'Çekim Adedi': stats['withdrawal_count']
                })
        
        if member_comparison:
            df_comparison = pd.DataFrame(member_comparison)
            
            # Miktar karşılaştırması
            fig = px.scatter(df_comparison, x='Yatırım Miktarı', y='Çekim Miktarı',
                           hover_data=['Kullanıcı Adı'],
                           title='Yatırım vs Çekim Miktarı Karşılaştırması')
            # Eşit çizgi ekle
            max_val = max(df_comparison['Yatırım Miktarı'].max(), df_comparison['Çekim Miktarı'].max())
            fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, 
                         line=dict(color="red", dash="dash"))
            st.plotly_chart(fig, use_container_width=True)
            
            # Adet karşılaştırması
            fig = px.scatter(df_comparison, x='Yatırım Adedi', y='Çekim Adedi',
                           hover_data=['Kullanıcı Adı'],
                           title='Yatırım vs Çekim Adedi Karşılaştırması')
            st.plotly_chart(fig, use_container_width=True)

def startup_github_sync():
    """Uygulama başlatıldığında GitHub senkronizasyonu"""
    github_sync = GitHubSync()
    github_token = github_sync.get_github_token()
    
    if not github_token:
        return  # GitHub token yoksa senkronizasyon yapma
    
    # Senkronize edilecek dosyalar
    files_to_sync = [
        ("members.json", "members.json"),
        ("daily_data.json", "daily_data.json")
    ]
    
    sync_results = []
    
    for local_file, github_file in files_to_sync:
        if os.path.exists(local_file):
            success, message = github_sync.sync_json_file(local_file, github_file)
            sync_results.append((github_file, success, message))
    
    # Sonuçları göster (sadece hata varsa)
    failed_syncs = [result for result in sync_results if not result[1]]
    if failed_syncs:
        with st.sidebar.expander("⚠️ Başlangıç Senkronizasyon Uyarıları", expanded=False):
            for file_name, success, message in failed_syncs:
                st.warning(f"{file_name}: {message}")
    else:
        # Başarılı senkronizasyon için küçük bildirim
        if sync_results:
            st.sidebar.success(f"✅ {len(sync_results)} dosya GitHub'a senkronize edildi")

def main():
    """Ana uygulama fonksiyonu"""
    st.title("📊 BTag Affiliate Takip Sistemi")
    st.markdown("---")
    
    # Başlangıç GitHub senkronizasyonu
    startup_github_sync()
    
    # Sidebar - Ana menü
    st.sidebar.title("📋 Menü")
    menu = st.sidebar.selectbox(
        "İşlem Seçin",
        ["Ana Sayfa", "Excel Yükleme", "Üye Yönetimi", "Raporlar", "İstatistikler", "Ayarlar"]
    )
    
    # Ayarlar modalını göster
    show_settings_modal()
    
    if menu == "Ana Sayfa":
        show_dashboard()
    elif menu == "Excel Yükleme":
        show_excel_upload()
    elif menu == "Üye Yönetimi":
        show_member_management()
    elif menu == "Raporlar":
        show_reports()
    elif menu == "İstatistikler":
        show_statistics()
    elif menu == "Ayarlar":
        st.header("⚙️ Ayarlar")
        st.info("Ayarlar sidebar'da bulunmaktadır.")

if __name__ == "__main__":
    main()

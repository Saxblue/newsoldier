import streamlit as st
import pandas as pd
import json
import os
import requests
import time
from datetime import datetime, timedelta

def clear_streamlit_cache():
    """Streamlit cache'ini temizle"""
    if hasattr(st, 'cache_data'):
        st.cache_data.clear()
    if hasattr(st, 'cache_resource'):
        st.cache_resource.clear()
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
# GitHub sync'i opsiyonel olarak import et
try:
    from github_sync import GitHubSync
    GITHUB_SYNC_AVAILABLE = True
except ImportError:
    GITHUB_SYNC_AVAILABLE = False
    class GitHubSync:
        """Dummy GitHub sync class when not available"""
        def __init__(self):
            self.sync_enabled = False

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

class TokenManager:
    """Token yönetimi için sınıf"""
    def __init__(self):
        self.token_file = "token.json"
        self.ensure_token_file()
    
    def ensure_token_file(self):
        """Token dosyasının varlığını kontrol et"""
        if not os.path.exists(self.token_file):
            default_token = {
                "token": "",
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
    
    def save_token(self, token, api_url):
        """Token dosyasını kaydet"""
        try:
            token_data = {
                "token": token,
                "api_url": api_url
            }
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"Token kaydetme hatası: {e}")
            return False

class DataProcessor:
    """Veri işleme sınıfı"""
    def __init__(self):
        self.daily_data_file = "daily_data.json"
        self.members_file = "members.json"
        self.github_sync = GitHubSync() if GITHUB_SYNC_AVAILABLE else None
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
        """Günlük veriyi kaydet ve GitHub'a senkronize et"""
        try:
            with open(self.daily_data_file, 'r', encoding='utf-8') as f:
                daily_data = json.load(f)
            
            date_str = date.strftime('%Y-%m-%d')
            
            if date_str not in daily_data:
                daily_data[date_str] = {}
            
            daily_data[date_str][btag] = processed_df.to_dict('records')
            
            with open(self.daily_data_file, 'w', encoding='utf-8') as f:
                json.dump(daily_data, f, ensure_ascii=False, indent=2)
            
            # Otomatik GitHub senkronizasyonu
            if self.github_sync and self.github_sync.sync_enabled:
                with st.spinner("GitHub'a senkronize ediliyor..."):
                    sync_success = self.github_sync.sync_json_file(self.daily_data_file)
                    if sync_success:
                        st.success("🔄 Veriler GitHub'a otomatik yüklendi!")
            
            return True
        except Exception as e:
            st.error(f"Veri kaydetme hatası: {e}")
            return False

class MemberManager:
    """Üye yönetimi sınıfı"""
    def __init__(self):
        self.members_file = "members.json"
        self.ensure_members_file()
        self.token_manager = TokenManager()
        self.data_processor = DataProcessor()
        self.github_sync = GitHubSync() if GITHUB_SYNC_AVAILABLE else None
    
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
                "api_data": {},
                "kpi_data": {},
                "last_kpi_update": None,
                "total_deposits": 0,
                "total_withdrawals": 0,
                "deposit_count": 0,
                "withdrawal_count": 0
            }
            
            members.append(new_member)
            
            with open(self.members_file, 'w', encoding='utf-8') as f:
                json.dump(members, f, ensure_ascii=False, indent=2)
            
            # Üye eklendikten sonra API'den veri çek
            self.fetch_member_api_data(str(member_id))
            # KPI verilerini güncelle
            self.update_member_kpis(str(member_id))
            
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
                        # KPI verilerini güncelle
                        self.update_member_kpis(member_id.strip())
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
            
            # API URL'leri
            client_url = f"https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientById?id={member_id}"
            kpi_url = "https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientKpis"
            
            headers = {
                'Authentication': token,
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Referer': 'https://backoffice.betconstruct.com/',
                'Origin': 'https://backoffice.betconstruct.com',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # Temel üye bilgilerini çek
            client_response = requests.get(client_url, headers=headers, timeout=10)
            
            if client_response.status_code == 200:
                client_data = client_response.json()
                
                # API verisini işle ve standartlaştır
                processed_data = self.process_api_response(client_data)
                
                # KPI verilerini çek
                try:
                    kpi_payload = {"ClientId": int(member_id)}
                    kpi_response = requests.post(kpi_url, headers=headers, json=kpi_payload, timeout=10)
                    
                    if kpi_response.status_code == 200:
                        kpi_data = kpi_response.json()
                        if not kpi_data.get("HasError", True) and kpi_data.get("Data"):
                            kpi_info = kpi_data["Data"][0] if kpi_data["Data"] else {}
                            processed_data.update({
                                'total_deposits': kpi_info.get('TotalDeposit', 0),
                                'total_withdrawals': kpi_info.get('TotalWithdrawal', 0),
                                'deposit_count': kpi_info.get('DepositCount', 0),
                                'withdrawal_count': kpi_info.get('WithdrawalCount', 0),
                                'last_kpi_update': datetime.now().isoformat()
                            })
                except Exception as kpi_error:
                    st.warning(f"KPI verileri çekilirken hata oluştu: {kpi_error}")
                
                # Üye veritabanını güncelle
                self.update_member_api_data(member_id, processed_data)
                
                return processed_data
            else:
                st.warning(f"API yanıt hatası ({client_response.status_code}): {member_id}")
                return None
                
        except Exception as e:
            st.warning(f"API çağrısı hatası: {e}")
            return None
    
    def is_token_valid(self, token):
        """Token'ın geçerli olup olmadığını kontrol et"""
        if not token:
            return False
            
        # Token'ın son kullanma tarihini kontrol et
        try:
            if len(token) < 10:
                return False
                
            # JWT token kontrolü
            parts = token.split('.')
            if len(parts) != 3:
                return True  # JWT değilse basit token olarak kabul et
            
            # Payload kısmını al
            payload = parts[1]
            # Padding ekle (base64 decode için)
            payload += '=' * (4 - len(payload) % 4)
            
            # Base64 decode et
            import base64
            import json
            payload_data = json.loads(base64.b64decode(payload).decode('utf-8'))
            
            # Expire kontrolü
            import time
            current_time = time.time()
            exp_time = payload_data.get('exp', 0)
            
            return exp_time > current_time
        except:
            # JWT decode hatası durumunda basit token olarak kabul et
            return True

    def update_member_kpis(self, member_id):
        """Tek bir üyenin KPI verilerini güncelle"""
        try:
            members = self.get_all_members()
            member_found = False
            
            for member in members:
                if member['member_id'] == str(member_id):
                    member_found = True
                    
                    # Token'ı yükle ve kontrol et
                    token_data = self.token_manager.load_token()
                    token = token_data.get('token', '')
                    
                    if not token or not self.is_token_valid(token):
                        st.warning("Geçersiz veya süresi dolmuş API token'ı. Lütfen ayarlardan yeni bir token girin.")
                        return False
                    
                    kpi_url = "https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientKpis"
                    headers = {
                        'Authentication': token,  # Bearer kaldırıldı
                        'Accept': 'application/json',
                        'Content-Type': 'application/json;charset=UTF-8',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Origin': 'https://backoffice.betconstruct.com',
                        'Referer': 'https://backoffice.betconstruct.com/'
                    }
                    
                    try:
                        kpi_payload = {"ClientId": int(member_id)}
                        
                        # Debug için istek bilgilerini yazdır
                        print(f"Sending request to {kpi_url}")
                        print(f"Headers: {headers}")
                        print(f"Payload: {kpi_payload}")
                        
                        response = requests.post(
                            kpi_url, 
                            headers=headers, 
                            json=kpi_payload, 
                            timeout=30
                        )
                        
                        print(f"Response status: {response.status_code}")
                        print(f"Response text: {response.text[:500]}")
                        
                        if response.status_code == 200:
                            kpi_data = response.json()
                            
                            if kpi_data.get("HasError", True):
                                error_msg = kpi_data.get("ErrorMessage", "Bilinmeyen hata")
                                st.warning(f"API hatası: {error_msg}")
                                
                                # Yetki hatasında token'ı temizle
                                if "token" in error_msg.lower() or "yetkisiz" in error_msg.lower():
                                    self.token_manager.save_token("", "")
                                return False
                                
                            if not kpi_data.get("Data"):
                                st.warning(f"{member_id} ID'li üye için KPI verisi bulunamadı.")
                                return False
                                
                            kpi_info = kpi_data["Data"][0] if kpi_data["Data"] else {}
                            
                            # KPI verilerini güncelle
                            member['kpi_data'] = kpi_info
                            member['last_kpi_update'] = datetime.now().isoformat()
                            # Ana alanları da güncelle ve float'a çevir
                            member['total_deposits'] = float(kpi_info.get('TotalDeposit', member.get('total_deposits', 0)) or 0)
                            member['total_withdrawals'] = float(kpi_info.get('TotalWithdrawal', member.get('total_withdrawals', 0)) or 0)
                            member['deposit_count'] = int(kpi_info.get('DepositCount', member.get('deposit_count', 0)) or 0)
                            member['withdrawal_count'] = int(kpi_info.get('WithdrawalCount', member.get('withdrawal_count', 0)) or 0)
                            
                            # Dosyayı kaydet
                            with open(self.members_file, 'w', encoding='utf-8') as f:
                                json.dump(members, f, ensure_ascii=False, indent=2)
                            
                            return True
                            
                        elif response.status_code == 401 or response.status_code == 403:
                            st.error("Yetkisiz erişim hatası. Lütfen API token'ınızı kontrol edin ve güncelleyin.")
                            self.token_manager.save_token("", "")  # Geçersiz token'ı temizle
                            return False
                            
                        else:
                            st.warning(f"API yanıt hatası ({response.status_code}): {response.text}")
                            return False
                            
                    except requests.exceptions.RequestException as req_err:
                        st.error(f"API isteği sırasında hata oluştu: {req_err}")
                        return False
                        
            if not member_found:
                st.warning(f"{member_id} ID'li üye bulunamadı.")
                
            return False
            
        except Exception as e:
            st.error(f"Beklenmeyen bir hata oluştu: {str(e)}")
            import traceback
            print(f"Hata detayı: {traceback.format_exc()}")
            return False
            
    def update_all_members_kpis(self):
        """Tüm üyelerin KPI verilerini güncelle"""
        try:
            members = self.get_all_members()
            total_members = len(members)

            if total_members == 0:
                st.warning("Güncellenecek üye bulunamadı.")
                return

            # Token kontrolü yap
            token_data = self.token_manager.load_token()
            if not token_data.get('token'):
                st.error("API token'ı bulunamadı. Lütfen ayarlardan token girin.")
                return

            # İlerleme çubuğu ve durum metni oluştur
            progress_bar = st.progress(0)
            status_text = st.empty()
            error_container = st.container()

            updated_count = 0
            failed_count = 0
            errors = []

            # Her bir üye için KPI güncelle
            for i, member in enumerate(members):
                member_id = member['member_id']
                username = member.get('username', f'Üye-{member_id}')

                # İlerleme durumunu güncelle
                progress = (i + 1) / total_members
                progress_bar.progress(progress)
                status_text.text(f"Güncelleniyor: {username} ({i+1}/{total_members}) - Başarılı: {updated_count}, Başarısız: {failed_count}")

                # KPI'ları güncelle
                try:
                    if self.update_member_kpis(member_id):
                        updated_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"{username} (ID: {member_id}): Güncelleme başarısız")

                    # API'ye çok fazla yüklenmemek için kısa bir bekleme
                    time.sleep(0.5)

                except Exception as e:
                    failed_count += 1
                    error_msg = f"{username} (ID: {member_id}) güncellenirken hata: {str(e)}"
                    errors.append(error_msg)
                    print(error_msg)  # Konsola da yazdır

                # Her 5 üyede bir hataları göster
                if errors and (i + 1) % 5 == 0:
                    with error_container:
                        st.error("Güncelleme hataları:")
                        for error in errors[-10:]:  # Son 10 hatayı göster
                            st.write(f"• {error}")
                        if len(errors) > 10:
                            st.info(f"Toplam {len(errors)} hata oluştu, son 10 hata gösteriliyor.")

            # Tüm işlemler bittiğinde sonuçları göster
            progress_bar.empty()
            status_text.empty()
            
            # Son hataları göster
            if errors:
                with error_container:
                    st.error("Son güncelleme hataları:")
                    for error in errors[-10:]:
                        st.write(f"• {error}")
                    if len(errors) > 10:
                        st.info(f"Toplam {len(errors)} hata oluştu, son 10 hata gösteriliyor.")

            if updated_count > 0:
                st.success(f"✅ {updated_count} üyenin KPI verileri güncellendi.")
            if failed_count > 0:
                st.error(f"❌ {failed_count} üyenin KPI verileri güncellenirken hata oluştu.")

            # Sayfayı yenile
            st.rerun()
            
        except Exception as e:
            st.error(f"Toplu güncelleme sırasında beklenmeyen bir hata oluştu: {str(e)}")
            import traceback
            print(f"Hata detayı: {traceback.format_exc()}")
            st.stop()

def process_api_response(self, api_data):
    """API yanıtını işle ve standartlaştır"""
    try:
        # API yanıtı doğrudan Data içinde gelebilir veya başka bir yapıda olabilir
        if 'Data' in api_data and isinstance(api_data['Data'], dict):
            data = api_data['Data']
        else:
            data = api_data  # Zaten doğrudan data gelmişse

        # Tarih formatı dönüşümü için yardımcı fonksiyon
        def parse_date(date_str):
            if not date_str:
                return ''
            try:
                # Farklı tarih formatlarını işle
                for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                    try:
                        return datetime.strptime(date_str.split('.')[0], fmt).strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, AttributeError):
                        continue
                return date_str
            except Exception:
                return date_str

        processed = {
            'username': data.get('Login', data.get('username', '')),
            'full_name': f"{data.get('FirstName', data.get('first_name', ''))} {data.get('LastName', data.get('last_name', ''))}".strip(),
            'email': data.get('Email', data.get('email', '')),
            'phone': data.get('Phone', data.get('phone', '')),
            'balance': float(data.get('Balance', data.get('balance', 0)) or 0),
            'currency': data.get('Currency', data.get('currency', 'TRY')),
            'registration_date': parse_date(data.get('RegistrationDate', data.get('registration_date', ''))),
            'last_login_date': parse_date(data.get('LastLoginDate', data.get('last_login_date', ''))),
            'is_active': not data.get('IsBlocked', not data.get('is_active', True) if 'is_active' in data else False),
            'partner_name': data.get('PartnerName', data.get('partner_name', '')),
            'birth_date': parse_date(data.get('BirthDate', data.get('birth_date', ''))),
            'last_deposit_date': parse_date(data.get('LastDepositDate', data.get('last_deposit_date', ''))),
            'last_casino_bet': parse_date(data.get('LastCasinoBet', data.get('last_casino_bet', '')))
        }

        # Günlük verileri kontrol et ve güncelle
        if 'last_deposit_date' in processed and processed['last_deposit_date']:
            try:
                last_deposit = datetime.strptime(processed['last_deposit_date'].split('.')[0], '%Y-%m-%d %H:%M:%S')
                days_diff = (datetime.now() - last_deposit).days
                processed['days_without_deposit'] = max(0, days_diff)
            except (ValueError, AttributeError, Exception):
                processed['days_without_deposit'] = 999  # Hata durumunda büyük bir değer ata
                
        return processed
        
    except Exception as e:
        st.error(f"API yanıtı işlenirken hata: {e}")
        # Hata durumunda en azından boş bir dict döndür
        return {
            'username': '',
            'full_name': '',
            'email': '',
            'phone': '',
            'balance': 0,
            'currency': 'TRY',
            'registration_date': '',
            'last_login_date': '',
            'is_active': True,
            'partner_name': '',
            'birth_date': '',
            'last_deposit_date': '',
            'last_casino_bet': '',
            'days_without_deposit': 999
        }

    def update_member_api_data(self, member_id, api_data):
        """Üye API verisini güncelle"""
        try:
            members = self.get_all_members()
            
            for member in members:
                if member['member_id'] == str(member_id):
                    # Mevcut KPI verilerini koru
                    kpi_data = member.get('kpi_data', {})
                    last_kpi_update = member.get('last_kpi_update')
                    
                    # Üye verilerini güncelle
                    member.update({
                        'api_data': api_data,
                        'last_api_update': datetime.now().isoformat(),
                        'kpi_data': kpi_data,
                        'last_kpi_update': last_kpi_update
                    })
                    
                    # API'den gelen bilgileri üye kaydına ekle
                    if api_data:
                        member['email'] = api_data.get('email', member.get('email', ''))
                        member['phone'] = api_data.get('phone', member.get('phone', ''))
                        member['balance'] = api_data.get('balance', member.get('balance', 0))
                        member['currency'] = api_data.get('currency', member.get('currency', 'TRY'))
                        member['total_deposits'] = api_data.get('total_deposits', member.get('total_deposits', 0))
                        member['total_withdrawals'] = api_data.get('total_withdrawals', member.get('total_withdrawals', 0))
                        member['last_deposit_date'] = api_data.get('last_deposit_date', member.get('last_deposit_date', ''))
                        member['last_casino_bet'] = api_data.get('last_casino_bet', member.get('last_casino_bet', ''))
                        member['days_without_deposit'] = api_data.get('days_without_deposit', member.get('days_without_deposit', 999))
                        member['registration_date'] = api_data.get('registration_date', member.get('registration_date', ''))
                        member['last_login_date'] = api_data.get('last_login_date', member.get('last_login_date', ''))
                        member['partner_name'] = api_data.get('partner_name', member.get('partner_name', ''))
                        member['birth_date'] = api_data.get('birth_date', member.get('birth_date', ''))
                    
                    break
            
            with open(self.members_file, 'w', encoding='utf-8') as f:
                json.dump(members, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            st.error(f"Üye güncelleme hatası: {e}")
            return False
    
    def toggle_member_status(self, member_id):
        """Üyenin aktif/pasif durumunu değiştir"""
        try:
            members = self.get_all_members()
            
            for member in members:
                if member['member_id'] == str(member_id):
                    member['is_active'] = not member.get('is_active', True)
                    member['status_updated_at'] = datetime.now().isoformat()
                    break
            
            with open(self.members_file, 'w', encoding='utf-8') as f:
                json.dump(members, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            st.error(f"Üye durumu değiştirme hatası: {e}")
            return False

def show_reports():
    """Raporlar sayfası"""
    st.header("📊 Raporlar")
    
    member_manager = MemberManager()
    
    # Günlük verileri yükle
    try:
        with open(member_manager.data_processor.daily_data_file, 'r', encoding='utf-8') as f:
            daily_data = json.load(f)
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        st.warning("Henüz veri bulunmuyor.")
        return
    
    if not daily_data:
        st.info("Rapor oluşturmak için önce veri yüklemeniz gerekiyor.")
        return
    
    # Tarih aralığı seçimi
    st.subheader("📅 Rapor Dönemi Seçin")
    col1, col2 = st.columns(2)
    
    available_dates = sorted(daily_data.keys(), key=lambda x: datetime.strptime(x, '%Y-%m-%d'))
    min_date = datetime.strptime(available_dates[0], '%Y-%m-%d').date() if available_dates else datetime.now().date()
    max_date = datetime.strptime(available_dates[-1], '%Y-%m-%d').date() if available_dates else datetime.now().date()
    
    with col1:
        start_date = st.date_input("Başlangıç Tarihi", value=min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("Bitiş Tarihi", value=max_date, min_value=min_date, max_value=max_date)
    
    # Rapor türü seçimi
    report_type = st.selectbox(
        "Rapor Türü Seçin",
        ["Genel Özet", "Detaylı Rapor", "Üye Bazlı Rapor"]
    )
    
    # Rapor oluştur butonu
    if st.button("📋 Rapor Oluştur", type="primary"):
        with st.spinner("Rapor oluşturuluyor..."):
            st.markdown("---")
            
            # Seçilen tarih aralığındaki verileri filtrele
            filtered_data = []
            total_deposits = 0
            total_withdrawals = 0
            member_summary = {}
            
            # Tüm üyelerin verilerini al
            all_members = member_manager.get_all_members()
            
            for date_str in daily_data:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                if start_date <= date_obj <= end_date:
                    for btag, records in daily_data[date_str].items():
                        for record in records:
                            member_id = str(record.get('member_id', ''))
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
            
            if not filtered_data:
                st.warning("Seçilen tarih aralığında veri bulunamadı.")
                return
                
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
            if report_type in ["Üye Bazlı Rapor", "Detaylı Rapor"]:
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
            
            # Detaylı tablo
            if report_type == "Detaylı Rapor":
                st.subheader("📋 Detaylı İşlemler")
                df_details = pd.DataFrame(filtered_data)
                st.dataframe(df_details, use_container_width=True)
            
            # İndirme butonları
            st.subheader("📥 Raporu İndir")
            col1, col2 = st.columns(2)
            
            with col1:
                # Excel olarak indir
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Genel özet
                    summary_data = {
                        'Metrik': ['Başlangıç Tarihi', 'Bitiş Tarihi', 'Toplam Gün', 
                                 'Toplam Yatırım', 'Toplam Çekim', 'Net'],
                        'Değer': [
                            start_date.strftime('%Y-%m-%d'),
                            end_date.strftime('%Y-%m-%d'),
                            (end_date - start_date).days + 1,
                            total_deposits,
                            total_withdrawals,
                            total_net
                        ]
                    }
                    pd.DataFrame(summary_data).to_excel(writer, sheet_name='Genel Özet', index=False)
                    
                    # Günlük özet
                    daily_summary.to_excel(writer, sheet_name='Günlük Özet', index=False)
                    
                    # Üye bazında özet
                    if report_type in ["Üye Bazlı Rapor", "Detaylı Rapor"]:
                        df_members.to_excel(writer, sheet_name='Üye Bazında Özet', index=False)
                    
                    # Detaylı işlemler
                    if report_type == "Detaylı Rapor":
                        df_details.to_excel(writer, sheet_name='Detaylı İşlemler', index=False)
                
                excel_data = output.getvalue()
                st.download_button(
                    label="📊 Excel Olarak İndir",
                    data=excel_data,
                    file_name=f"rapor_{start_date}_{end_date}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            
            with col2:
                # CSV olarak indir
                csv_data = df_daily.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📄 CSV Olarak İndir (Günlük Özet)",
                    data=csv_data,
                    file_name=f"gunluk_ozet_{start_date}_{end_date}.csv",
                    mime='text/csv'
                )
            st.error(f"Rapor oluşturulurken hata oluştu: {e}")

def show_settings():
    """Ayarlar sayfası"""
    st.header("⚙️ Ayarlar")
    
    # API Ayarları Sekmesi
    tab1, tab2 = st.tabs(["🔑 API Ayarları", "🔄 GitHub Senkronizasyon"])
    
    with tab1:
        st.subheader("📋 API Token Ayarları")
        
        token_manager = TokenManager()
        token_data = token_manager.load_token()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📋 Mevcut Token Bilgileri")
            st.code(token_data.get('token', 'Token bulunamadı'), language='text')
            st.text(f"API URL: {token_data.get('api_url', '')}")
        
        with col2:
            st.subheader("🔧 Token Güncelleme")
            new_token = st.text_input("Token", value=token_data.get('token', ''), type='password')
            new_api_url = st.text_input("API URL", value=token_data.get('api_url', ''))
            
            if st.button("💾 Token Kaydet", type='primary'):
                if new_token and new_api_url:
                    success = token_manager.save_token(new_token, new_api_url)
                    if success:
                        st.success("✅ Token başarıyla kaydedildi!")
                        st.rerun()
                    else:
                        st.error("❌ Token kaydetme hatası!")
                else:
                    st.error("❌ Lütfen tüm alanları doldurun!")
    
    with tab2:
        st.subheader("🔄 GitHub Otomatik Senkronizasyon")
        
        if not GITHUB_SYNC_AVAILABLE:
            st.warning("⚠️ GitHub senkronizasyon modülü bulunamadı!")
            st.info("📦 GitHub özelliklerini kullanmak için requirements.txt dosyasını GitHub'a yükleyin.")
            return
        
        # GitHub Sync nesnesi oluştur
        github_sync = GitHubSync()
        
        # Repository bilgilerini göster
        repo_info = github_sync.get_repo_info() if github_sync.sync_enabled else None
        if repo_info:
            st.success("✅ GitHub bağlantısı başarılı!")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.info(f"""
                **📁 Repository:** {repo_info['full_name']}
                **🔗 URL:** {repo_info['url']}
                **📅 Son Push:** {repo_info['last_push']}
                **📊 Toplam Commit:** {repo_info['commits']}
                """)
            
            with col2:
                st.subheader("🚀 Senkronizasyon İşlemleri")
                
                if st.button("🔄 Tüm Dosyaları Senkronize Et", type='primary'):
                    github_sync.sync_all_files()
                
                st.markdown("---")
                
                # Tek tek dosya senkronizasyonu
                st.subheader("📁 Tek Dosya Senkronizasyonu")
                
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("📄 btag.py"):
                        github_sync.sync_python_file("btag.py", "btag_affiliate_system.py")
                    
                    if st.button("📊 daily_data.json"):
                        github_sync.sync_json_file("daily_data.json")
                
                with col_btn2:
                    if st.button("👥 members.json"):
                        github_sync.sync_json_file("members.json")
                    
                    if st.button("🔑 token.json"):
                        github_sync.sync_json_file("token.json")
        
        else:
            st.error("❌ GitHub bağlantısı başarısız!")
            st.info("""
            **GitHub Senkronizasyon Özellikleri:**
            - Otomatik dosya yükleme
            - Veri dosyalarını senkronize etme
            - Streamlit Cloud otomatik güncelleme
            - Repository bilgilerini görüntüleme
            """)
        
        st.markdown("---")
        st.subheader("ℹ️ Bilgi")
        st.info("""
        **GitHub Senkronizasyon Nasıl Çalışır:**
        1. 🔄 Yerel değişikliklerinizi GitHub'a otomatik yükler
        2. 🌐 Streamlit Cloud otomatik olarak güncellenir
        3. 📊 Veri dosyaları (JSON) senkronize edilir
        4. 💻 Kod değişiklikleri anında yansır
        
        **Senkronize Edilen Dosyalar:**
        - `btag.py` → `btag_affiliate_system.py`
        - `daily_data.json`
        - `members.json` 
        - `token.json`
        """)

def show_dashboard():
    """Ana sayfa göster"""
    st.header("🏠 Ana Sayfa")
    
    member_manager = MemberManager()
    
    current_month = datetime.now().strftime("%Y-%m")
    st.subheader(f"📅 Mevcut Ay: {datetime.now().strftime('%B %Y')}")
    
    members = member_manager.get_active_members()
    total_members = len(members)
    
    # Günlük verileri yükle
    try:
        with open(member_manager.data_processor.daily_data_file, 'r', encoding='utf-8') as f:
            daily_data = json.load(f)
    except Exception as e:
        print(f"Veri yukleme hatasi: {e}")
        daily_data = {}
        st.error(f"Veri yukleme hatasi: {e}")
    
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
    
    # Aktif/Pasif Üye Dağılımı Pie Chart
    st.markdown("---")
    st.subheader("👥 Üye Durumu Dağılımı")
    
    # Aktif ve pasif üye sayılarını hesapla
    active_members = total_members - passive_members
    
    if total_members > 0:
        col_chart1, col_chart2 = st.columns([2, 1])
        
        with col_chart1:
            # Pie chart verilerini hazırla
            pie_data = {
                'Durum': ['Aktif Üyeler', 'Pasif Üyeler'],
                'Sayı': [active_members, passive_members],
                'Renk': ['#00CC96', '#FF6B6B']
            }
            
            # Pie chart oluştur
            fig_pie = px.pie(
                values=pie_data['Sayı'], 
                names=pie_data['Durum'],
                title='Üye Durumu Dağılımı',
                color_discrete_sequence=['#00CC96', '#FF6B6B']
            )
            
            # Grafik ayarları
            fig_pie.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Sayı: %{value}<br>Oran: %{percent}<extra></extra>'
            )
            
            fig_pie.update_layout(
                showlegend=True,
                height=400,
                font=dict(size=14)
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_chart2:
            st.markdown("### 📊 Detaylar")
            st.markdown(f"**🟢 Aktif Üyeler:** {active_members}")
            st.markdown(f"**🔴 Pasif Üyeler:** {passive_members}")
            st.markdown("---")
            
            if total_members > 0:
                active_percentage = (active_members / total_members) * 100
                passive_percentage = (passive_members / total_members) * 100
                
                st.markdown(f"**Aktif Oran:** {active_percentage:.1f}%")
                st.markdown(f"**Pasif Oran:** {passive_percentage:.1f}%")
                
                # Durum değerlendirmesi
                if active_percentage >= 80:
                    st.success("✅ Mükemmel! Üyelerin çoğu aktif.")
                elif active_percentage >= 60:
                    st.warning("⚠️ İyi durumda, ancak pasif üye sayısı artıyor.")
                else:
                    st.error("🚨 Dikkat! Pasif üye oranı yüksek.")
    else:
        st.info("📝 Henüz üye bulunmuyor.")
    
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
        recent_dates = sorted(daily_data.keys(), key=lambda x: datetime.strptime(x, '%Y-%m-%d'))[-7:]
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
                    processed_data = member_manager.data_processor.process_excel_data(filtered_df)
                    
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
                            success = member_manager.data_processor.save_daily_data(
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
    
    # Üst butonlar
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Tüm Üyeleri Yenile", use_container_width=True):
            with st.spinner("Tüm üyelerin verileri güncelleniyor..."):
                member_manager.update_all_members_kpis()
            st.success("✅ Tüm üyelerin verileri güncellendi!")
            st.rerun()
    
    with col2:
        if st.button("📊 KPI Raporu Oluştur", use_container_width=True):
            # KPI raporu oluşturma işlemleri
            pass
    
    with col3:
        if st.button("📤 Üye Listesini Dışa Aktar", use_container_width=True):
            # Dışa aktarma işlemleri
            pass
    
    # Üye ekleme seçenekleri
    with st.expander("➕ Üye Ekleme", expanded=False):
        tab1, tab2 = st.tabs(["Tekli Ekleme", "Toplu Ekleme"])
        
        with tab1:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                new_member_id = st.text_input("🆔 Üye ID")
            with col2:
                new_username = st.text_input("👤 Kullanıcı Adı")
            with col3:
                new_fullname = st.text_input("📝 İsim Soyisim")
            
            if st.button("➕ Üye Ekle", use_container_width=True):
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
            
            if st.button("➕ Toplu Ekle", use_container_width=True):
                if bulk_ids:
                    id_list = [x.strip() for x in bulk_ids.strip().split('\n') if x.strip()]
                    if id_list:
                        added_count = member_manager.add_members_bulk(id_list)
                        st.success(f"✅ {added_count} üye başarıyla eklendi!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Geçerli bir ID girin!")
                else:
                    st.warning("⚠️ Üye ID'leri girin!")
    
    # Filtreleme ve sıralama
    st.subheader("📋 Üye Listesi")
    
    members = member_manager.get_all_members()
    if members:
        # Filtreleme
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_term = st.text_input("🔍 Üye Ara", placeholder="İsim, kullanıcı adı veya ID ile ara...")
        
        with col2:
            status_filter = st.selectbox("Durum", ["Tümü", "Aktif", "Pasif"])
        
        with col3:
            sort_by = st.selectbox("Sırala", ["ID", "İsim", "Son Yatırım", "Toplam Yatırım"], index=0)
        
        # Filtreleme işlemi
        filtered_members = members
        
        if search_term:
            filtered_members = [
                m for m in filtered_members 
                if (search_term.lower() in m.get('full_name', '').lower() or 
                     search_term.lower() in m.get('username', '').lower() or
                     search_term in str(m.get('member_id', '')))
            ]
        
        if status_filter == "Aktif":
            filtered_members = [m for m in filtered_members if m.get('is_active', True)]
        elif status_filter == "Pasif":
            filtered_members = [m for m in filtered_members if not m.get('is_active', True)]
        
        # Sıralama işlemi
        if sort_by == "ID":
            filtered_members.sort(key=lambda x: int(x.get('member_id', 0)))
        elif sort_by == "İsim":
            filtered_members.sort(key=lambda x: x.get('full_name', '').lower())
        elif sort_by == "Son Yatırım":
            filtered_members.sort(
                key=lambda x: datetime.strptime(x.get('last_deposit_date', '1970-01-01').split('T')[0], '%Y-%m-%d') 
                if x.get('last_deposit_date') and 'T' in x.get('last_deposit_date', '') 
                else datetime.min, 
                reverse=True
            )
        elif sort_by == "Toplam Yatırım":
            filtered_members.sort(key=lambda x: float(x.get('total_deposits', 0)), reverse=True)
        
        # Sayfalama
        items_per_page = 10
        total_pages = (len(filtered_members) + items_per_page - 1) // items_per_page
        
        if not filtered_members:
            st.warning("Filtrelere uygun üye bulunamadı.")
            return
        
        # Sayfa numarası seçimi
        if total_pages > 1:
            page = st.number_input("Sayfa", min_value=1, max_value=total_pages, value=1, step=1)
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(filtered_members))
            current_page_members = filtered_members[start_idx:end_idx]
        else:
            current_page_members = filtered_members
        
        # Üye tablosu
        for member in current_page_members:
            with st.container():
                # Ana satır
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 2, 2, 1, 1, 1, 1])
                
                with col1:
                    st.write(f"🆔 {member.get('member_id', '')}")
                
                with col2:
                    st.write(f"👤 {member.get('username', '')}")
                
                with col3:
                    st.write(f"📝 {member.get('full_name', '')}")
                
                with col4:
                    status = "✅" if member.get('is_active', True) else "❌"
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
                    st.write(f"💵 {float(member.get('total_deposits', 0)):,.2f} {member.get('currency', 'TRY')}")
                
                with col7:
                    if member.get('is_active', True):
                        if st.button(f"🚫", key=f"ban_{member.get('member_id')}"):
                            member_manager.toggle_member_status(member['member_id'])
                            st.success(f"Üye {member.get('username', '')} banlandı!")
                            st.rerun()
                    else:
                        if st.button(f"✅", key=f"unban_{member.get('member_id')}"):
                            member_manager.toggle_member_status(member['member_id'])
                            st.success(f"Üye {member.get('username', '')} aktif edildi!")
                            st.rerun()
                
                # Detay bilgileri
                with st.expander(f"📊 {member.get('username', '')} - Detaylar", expanded=False):
                    tab1, tab2, tab3 = st.tabs(["Genel Bilgiler", "Finansal Bilgiler", "İşlem Geçmişi"])
                    
                    with tab1:
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.subheader("📋 Kişisel Bilgiler")
                            st.write(f"📧 **Email:** {member.get('email', 'Bilinmiyor')}")
                            st.write(f"📞 **Telefon:** {member.get('phone', 'Bilinmiyor')}")
                            st.write(f"🎂 **Doğum Tarihi:** {member.get('birth_date', 'Bilinmiyor')}")
                            st.write(f"👥 **Partner:** {member.get('partner_name', 'Bilinmiyor')}")
                        
                        with col2:
                            st.subheader("📅 Zaman Bilgileri")
                            st.write(f"📅 **Kayıt Tarihi:** {member.get('registration_date', 'Bilinmiyor')}")
                            st.write(f"🕐 **Son Giriş:** {member.get('last_login_date', 'Bilinmiyor')}")
                            st.write(f"💳 **Son Yatırım:** {member.get('last_deposit_date', 'Bilinmiyor')}")
                            st.write(f"🎰 **Son Casino:** {member.get('last_casino_bet', 'Bilinmiyor')}")
                        
                        with col3:
                            st.subheader("⚙️ İşlemler")
                            if st.button(f"🔄 Verileri Güncelle", key=f"refresh_{member.get('member_id')}"):
                                with st.spinner("Veriler güncelleniyor..."):
                                    member_manager.fetch_member_api_data(member['member_id'])
                                    member_manager.update_member_kpis(member['member_id'])
                                st.success("✅ Veriler güncellendi!")
                                st.rerun()
                            
                            if st.button(f"📊 KPI Güncelle", key=f"kpi_{member.get('member_id')}"):
                                with st.spinner("KPI verileri güncelleniyor..."):
                                    if member_manager.update_member_kpis(member['member_id']):
                                        st.success("✅ KPI verileri güncellendi!")
                                    else:
                                        st.error("❌ KPI güncelleme başarısız oldu!")
                                st.rerun()
                    
                    with tab2:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("💰 Bakiye Bilgileri")
                            st.metric("💰 Mevcut Bakiye", f"{float(member.get('balance', 0)):,.2f} {member.get('currency', 'TRY')}")
                            st.metric("💳 Toplam Yatırım", f"{float(member.get('total_deposits', 0)):,.2f} {member.get('currency', 'TRY')}")
                            st.metric("💸 Toplam Çekim", f"{float(member.get('total_withdrawals', 0)):,.2f} {member.get('currency', 'TRY')}")
                        
                        with col2:
                            st.subheader("📊 İstatistikler")
                            st.metric("🔢 Yatırım Sayısı", f"{int(member.get('deposit_count', 0))}")
                            st.metric("🔄 Çekim Sayısı", f"{int(member.get('withdrawal_count', 0))}")
                            st.metric("⏱️ Son Güncelleme", f"{member.get('last_kpi_update', 'Bilinmiyor')}")
                    
                    with tab3:
                        st.subheader("📜 Son İşlemler")
                        # Bu kısımda işlem geçmişi gösterilebilir
                        st.info("İşlem geçmişi özelliği yakında eklenecektir.")
                
                st.markdown("---")
        
        # Sayfalama bilgisi
        if total_pages > 1:
            st.write(f"📄 Sayfa {page}/{total_pages} - Toplam {len(filtered_members)} üye")
        else:
            st.info(f"📊 Toplam {len(filtered_members)} üye gösteriliyor")
    
    else:
        st.warning("Henüz üye eklenmemiş. Üstteki formu kullanarak yeni üye ekleyebilirsiniz.")
    
    # Üye yönetimi işlemleri burada kalacak

def show_reports():
    """Raporlama sayfası"""
    st.header("📊 Raporlama")
    
    member_manager = MemberManager()
    
    # Verileri yükle
    try:
        with open(member_manager.data_processor.daily_data_file, 'r', encoding='utf-8') as f:
            daily_data = json.load(f)
    except Exception as e:
        print(f"Veri yukleme hatasi: {e}")
        daily_data = {}
        st.error(f"Veri yukleme hatasi: {e}")
        st.warning("Henüz veri bulunmuyor.")
        return
    
    if not daily_data:
        st.info("Rapor oluşturmak için önce veri yüklemeniz gerekiyor.")
        return
    
    # Tarih aralığı seçimi
    st.subheader("📅 Rapor Dönemi Seçin")
    col1, col2 = st.columns(2)
    
    available_dates = sorted(daily_data.keys(), key=lambda x: datetime.strptime(x, '%Y-%m-%d'))
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
                        # Tum uyeleri dahil et - aktif kontrolunu gevset
                        # if member_id not in active_member_ids:
                        #     continue
                            
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
    
    member_manager = MemberManager()
    
    # Verileri yükle
    try:
        with open(member_manager.data_processor.daily_data_file, 'r', encoding='utf-8') as f:
            daily_data = json.load(f)
    except Exception as e:
        print(f"Veri yukleme hatasi: {e}")
        daily_data = {}
        st.error(f"Veri yukleme hatasi: {e}")
    
    if not daily_data:
        st.warning("⚠️ Henüz veri bulunmuyor. Önce Excel dosyası yükleyin.")
        return
    
    # Tarih aralığı seçimi
    st.subheader("📅 Tarih Aralığı Seçin")
    col1, col2 = st.columns(2)
    
    available_dates = sorted(daily_data.keys(), key=lambda x: datetime.strptime(x, '%Y-%m-%d'))
    if available_dates:
        with col1:
            start_date = st.date_input(
                "Başlangıç Tarihi",
                value=datetime.strptime(available_dates[0], '%Y-%m-%d').date()
            )
        with col2:
            end_date = st.date_input(
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

def main():
    # Veri yukleme oncesi cache temizle
    clear_streamlit_cache()

# Veri yükleme öncesi cache temizle
if hasattr(st, 'cache_data'):
    st.cache_data.clear()
if hasattr(st, 'cache_resource'):
    st.cache_resource.clear()

    """Ana uygulama fonksiyonu"""
    st.title("📊 BTag Affiliate Takip Sistemi")
    st.markdown("---")
    
    # Üst sekmeler
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏠 Ana Sayfa", 
        "📤 Excel Yükleme", 
        "👥 Üye Yönetimi", 
        "📋 Raporlar", 
        "📊 İstatistikler", 
        "⚙️ Ayarlar"
    ])
    
    with tab1:
        show_dashboard()
    
    with tab2:
        show_excel_upload()
    
    with tab3:
        show_member_management()
    
    with tab4:
        show_reports()
    
    with tab5:
        show_statistics()
    
    with tab6:
        show_settings()

if __name__ == "__main__":
    main()

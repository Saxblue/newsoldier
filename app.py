import streamlit as st
import json
import os
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import io
import base64
import time

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="BTag Affiliate Takip Sistemi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# TOKEN MANAGER CLASS
# =============================================================================
class TokenManager:
    """Token yönetimi için sınıf"""
    
    def __init__(self):
        self.token_file = "token.json"
        self.ensure_token_file()
    
    def ensure_token_file(self):
        """Token dosyasının varlığını kontrol et"""
        if not os.path.exists(self.token_file):
            default_token = {
                "api_token": "8d7974f38c6fae4e66f41dcf6805e648a9fa59c6682788e7fe61a4c8ea5e21e3",
                "github_token": "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",
                "api_url": "https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientWithdrawalRequestsWithTotals",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(default_token, f, ensure_ascii=False, indent=2)
    
    def load_tokens(self):
        """Token dosyasını yükle"""
        try:
            with open(self.token_file, 'r', encoding='utf-8') as f:
                tokens = json.load(f)
                
                # Eski format desteği
                if 'api_token' not in tokens and 'token' in tokens:
                    tokens['api_token'] = tokens.get('token', '')
                
                # Eksik alanları ekle
                if 'github_token' not in tokens:
                    tokens['github_token'] = "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"
                
                if 'api_url' not in tokens:
                    tokens['api_url'] = "https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientWithdrawalRequestsWithTotals"
                
                return tokens
        except Exception as e:
            st.error(f"Token dosyası okuma hatası: {e}")
            return {
                "api_token": "8d7974f38c6fae4e66f41dcf6805e648a9fa59c6682788e7fe61a4c8ea5e21e3",
                "github_token": "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",
                "api_url": "https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientWithdrawalRequestsWithTotals"
            }
    
    def save_tokens(self, tokens):
        """Token dosyasını kaydet"""
        try:
            tokens['updated_at'] = datetime.now().isoformat()
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(tokens, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"Token kaydetme hatası: {e}")
            return False
    
    def get_api_token(self):
        """API token'ını getir"""
        tokens = self.load_tokens()
        return tokens.get('api_token', '8d7974f38c6fae4e66f41dcf6805e648a9fa59c6682788e7fe61a4c8ea5e21e3')
    
    def get_github_token(self):
        """GitHub token'ını getir"""
        tokens = self.load_tokens()
        return tokens.get('github_token', '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')
    
    def get_api_url(self):
        """API URL'ini getir"""
        tokens = self.load_tokens()
        return tokens.get('api_url', 'https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientWithdrawalRequestsWithTotals')

# =============================================================================
# GITHUB MANAGER CLASS
# =============================================================================
class GitHubManager:
    """GitHub entegrasyonu için sınıf"""
    
    def __init__(self, token_manager):
        self.token_manager = token_manager
        self.repo_owner = None
        self.repo_name = None
        self.connected = False
    
    def connect_repository(self, repo_url):
        """GitHub repository'sine bağlan"""
        try:
            # Repository URL'den owner ve name çıkar
            if 'github.com' in repo_url:
                parts = repo_url.replace('https://github.com/', '').replace('.git', '').strip('/').split('/')
                if len(parts) >= 2:
                    self.repo_owner = parts[0]
                    self.repo_name = parts[1]
                    
                    st.info(f"🔍 Repository: {self.repo_owner}/{self.repo_name}")
                    
                    # Token kontrolü
                    github_token = self.token_manager.get_github_token()
                    if not github_token:
                        st.error("❌ GitHub token bulunamadı!")
                        return False
                    
                    # Token formatını kontrol et
                    if not (github_token.startswith('github_pat_') or github_token.startswith('ghp_')):
                        st.warning("⚠️ Token formatı şüpheli. GitHub Personal Access Token'ı kontrol edin.")
                    
                    st.info(f"🔑 Token uzunluğu: {len(github_token)} karakter")
                    
                    # Test bağlantısı
                    test_result = self.test_connection_detailed()
                    if test_result['success']:
                        self.connected = True
                        st.success(f"✅ Başarıyla bağlandı: {self.repo_owner}/{self.repo_name}")
                        return True
                    else:
                        st.error(f"❌ {test_result['error']}")
                        return False
            else:
                st.error("❌ Geçersiz GitHub URL formatı!")
                return False
        except Exception as e:
            st.error(f"GitHub bağlantı hatası: {str(e)}")
            return False
    
    def test_connection(self):
        """GitHub bağlantısını test et"""
        try:
            github_token = self.token_manager.get_github_token()
            if not github_token or not self.repo_owner or not self.repo_name:
                return False
            
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def test_connection_detailed(self):
        """Detaylı GitHub bağlantı testi"""
        try:
            github_token = self.token_manager.get_github_token()
            if not github_token:
                return {'success': False, 'error': 'GitHub token bulunamadı'}
            
            if not self.repo_owner or not self.repo_name:
                return {'success': False, 'error': 'Repository bilgileri eksik'}
            
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'BTag-Affiliate-System'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return {'success': True, 'error': None}
            elif response.status_code == 401:
                return {'success': False, 'error': 'Token geçersiz veya süresi dolmuş'}
            elif response.status_code == 403:
                return {'success': False, 'error': 'Token yetkisi yetersiz'}
            elif response.status_code == 404:
                return {'success': False, 'error': 'Repository bulunamadı veya erişim izni yok'}
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}: {response.text[:100]}'}
                
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Bağlantı zaman aşımı'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'İnternet bağlantısı hatası'}
        except Exception as e:
            return {'success': False, 'error': f'Beklenmeyen hata: {str(e)}'}
    
    def sync_file(self, file_path):
        """Dosyayı GitHub'a sync et"""
        try:
            if not self.connected:
                return False
            
            github_token = self.token_manager.get_github_token()
            
            # Dosya içeriğini oku
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Base64 encode
            encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # GitHub API URL
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/{file_path}"
            
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Mevcut dosya SHA'sını al
            existing_file = requests.get(url, headers=headers)
            
            data = {
                'message': f'Update {file_path} - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                'content': encoded_content
            }
            
            if existing_file.status_code == 200:
                data['sha'] = existing_file.json()['sha']
            
            # Dosyayı gönder
            response = requests.put(url, headers=headers, json=data)
            return response.status_code in [200, 201]
            
        except Exception as e:
            st.error(f"GitHub sync hatası: {str(e)}")
            return False

# =============================================================================
# UTILS CLASS
# =============================================================================
class Utils:
    """Yardımcı fonksiyonlar sınıfı"""
    
    @staticmethod
    def format_currency(amount, currency="TRY"):
        """Para birimi formatla"""
        try:
            if amount is None:
                return "0,00 " + currency
            return f"{float(amount):,.2f} {currency}"
        except (ValueError, TypeError):
            return "0,00 " + currency
    
    @staticmethod
    def format_number(number):
        """Sayı formatla"""
        try:
            if number is None:
                return "0"
            return f"{int(number):,}"
        except (ValueError, TypeError):
            return "0"
    
    @staticmethod
    def format_date(date_str, format_type="short"):
        """Tarih formatla"""
        try:
            if not date_str or date_str in ['', 'None', 'null', None]:
                return "Bilinmiyor"
            
            date_formats = [
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d.%m.%Y',
                '%d.%m.%Y %H:%M:%S'
            ]
            
            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(str(date_str), fmt)
                    break
                except ValueError:
                    continue
            
            if parsed_date:
                if format_type == "short":
                    return parsed_date.strftime('%d.%m.%Y')
                elif format_type == "long":
                    return parsed_date.strftime('%d.%m.%Y %H:%M')
                else:
                    return parsed_date.strftime('%d.%m.%Y %H:%M:%S')
            else:
                return str(date_str)
                
        except Exception:
            return "Geçersiz tarih"
    
    @staticmethod
    def calculate_days_difference(date_str):
        """İki tarih arasındaki gün farkını hesapla"""
        try:
            if not date_str or date_str in ['', 'None', 'null', None]:
                return 999
            
            date_formats = [
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d.%m.%Y',
                '%d.%m.%Y %H:%M:%S'
            ]
            
            target_date = None
            for fmt in date_formats:
                try:
                    target_date = datetime.strptime(str(date_str), fmt)
                    break
                except ValueError:
                    continue
            
            if target_date:
                if target_date.tzinfo is not None:
                    target_date = target_date.replace(tzinfo=None)
                
                diff = datetime.now() - target_date
                return max(0, diff.days)
            else:
                return 999
                
        except Exception:
            return 999
    
    @staticmethod
    def validate_member_id(member_id):
        """Üye ID'sini doğrula"""
        try:
            if not member_id:
                return False
            member_id_str = str(member_id).strip()
            return member_id_str.isdigit() and len(member_id_str) >= 6
        except:
            return False
    
    @staticmethod
    def safe_float(value, default=0.0):
        """Güvenli float çevirme"""
        try:
            if value is None or value == '':
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_int(value, default=0):
        """Güvenli int çevirme"""
        try:
            if value is None or value == '':
                return default
            return int(float(value))
        except (ValueError, TypeError):
            return default

# =============================================================================
# DATA PROCESSOR CLASS
# =============================================================================
class DataProcessor:
    """Veri işleme sınıfı"""
    
    def __init__(self, github_manager=None):
        self.daily_data_file = "daily_data.json"
        self.github_manager = github_manager
        self.ensure_data_files()
    
    def ensure_data_files(self):
        """Veri dosyalarını oluştur"""
        if not os.path.exists(self.daily_data_file):
            with open(self.daily_data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def process_excel_data(self, df, btag_filter=None):
        """Excel verisini işle ve isteğe bağlı BTag filtresi uygula"""
        try:
            # Sütun haritalama - Türkçe ve İngilizce sütun adlarını destekle
            column_mapping = {
                'ID': 'member_id',
                'Kullanıcı Adı': 'username',
                'Username': 'username',
                'User Name': 'username',
                'Müşteri Adı': 'customer_name',
                'Customer Name': 'customer_name',
                'Full Name': 'customer_name',
                'Para Yatırma Sayısı': 'deposit_count',
                'Deposit Count': 'deposit_count',
                'Yatırımlar': 'total_deposits',
                'Deposits': 'total_deposits',
                'Total Deposits': 'total_deposits',
                'Para Çekme Sayısı': 'withdrawal_count',
                'Withdrawal Count': 'withdrawal_count',
                'Para Çekme Miktarı': 'total_withdrawals',
                'Withdrawals': 'total_withdrawals',
                'Total Withdrawals': 'total_withdrawals',
                'BTag': 'btag',
                'B Tag': 'btag',
                'Tag': 'btag',
                'Btag': 'btag'
            }
            
            df_processed = df.copy()
            
            # Sütun adlarını standartlaştır
            original_columns = df_processed.columns.tolist()
            for old_col, new_col in column_mapping.items():
                if old_col in df_processed.columns:
                    df_processed = df_processed.rename(columns={old_col: new_col})
            
            # BTag filtreleme (eğer belirtildiyse)
            if btag_filter:
                if 'btag' in df_processed.columns:
                    original_count = len(df_processed)
                    df_processed = df_processed[df_processed['btag'].astype(str).str.contains(str(btag_filter), case=False, na=False)]
                    filtered_count = len(df_processed)
                    st.info(f"🎯 BTag '{btag_filter}' filtresi uygulandı: {original_count} → {filtered_count} kayıt")
                    
                    if filtered_count == 0:
                        st.warning(f"⚠️ BTag '{btag_filter}' ile eşleşen kayıt bulunamadı!")
                        return None
                else:
                    st.warning(f"⚠️ Excel dosyasında 'BTag' sütunu bulunamadı. Sadece '{btag_filter}' BTag'ına ait üyeler filtrelemek için Excel'de BTag sütunu olmalı.")
                    st.info("💡 BTag sütunu olmadan tüm veriler işlenecek. BTag'a özel filtreleme için Excel'e BTag sütunu ekleyin.")
            
            # Gerekli sütunlar
            required_columns = [
                'member_id', 'username', 'customer_name', 
                'deposit_count', 'total_deposits', 
                'withdrawal_count', 'total_withdrawals'
            ]
            
            # Eksik sütunları ekle
            for col in required_columns:
                if col not in df_processed.columns:
                    if col in ['deposit_count', 'total_deposits', 'withdrawal_count', 'total_withdrawals']:
                        df_processed[col] = 0
                    else:
                        df_processed[col] = ''
            
            # Veri tiplerini düzelt
            numeric_columns = ['deposit_count', 'total_deposits', 'withdrawal_count', 'total_withdrawals']
            for col in numeric_columns:
                df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')
                df_processed[col] = df_processed[col].fillna(0)
            
            string_columns = ['member_id', 'username', 'customer_name']
            for col in string_columns:
                df_processed[col] = df_processed[col].astype(str)
                df_processed[col] = df_processed[col].fillna('')
                # Boş değerleri temizle
                df_processed[col] = df_processed[col].replace('nan', '')
                df_processed[col] = df_processed[col].replace('None', '')
            
            # Boş satırları temizle
            df_processed = df_processed[df_processed['member_id'] != '']
            df_processed = df_processed[df_processed['member_id'] != 'nan']
            
            # Sütun sırasını düzenle
            df_processed = df_processed[required_columns]
            
            # Veri kalitesi kontrolü
            if len(df_processed) == 0:
                st.warning("⚠️ İşlenebilir veri bulunamadı. Lütfen Excel formatını kontrol edin.")
                st.info(f"Orijinal sütunlar: {original_columns}")
                return None
            
            st.info(f"✅ {len(df_processed)} satır veri başarıyla işlendi.")
            return df_processed
            
        except Exception as e:
            st.error(f"Veri işleme hatası: {str(e)}")
            return None
    
    def save_daily_data(self, processed_df, btag, date):
        """Günlük veriyi kaydet"""
        try:
            # Mevcut günlük veriyi yükle
            daily_data = self.load_daily_data()
            
            date_str = date.strftime('%Y-%m-%d')
            
            # Tarih anahtarı yoksa oluştur
            if date_str not in daily_data:
                daily_data[date_str] = {}
            
            # BTag verisini kaydet
            daily_data[date_str][btag] = processed_df.to_dict('records')
            
            # Dosyaya kaydet
            with open(self.daily_data_file, 'w', encoding='utf-8') as f:
                json.dump(daily_data, f, ensure_ascii=False, indent=2)
            
            # GitHub'a sync et (eğer bağlı ise ve otomatik sync aktifse)
            if (self.github_manager and 
                self.github_manager.connected and 
                st.session_state.get('auto_sync_enabled', False)):
                self.github_manager.sync_file(self.daily_data_file)
            
            return True
            
        except Exception as e:
            st.error(f"Veri kaydetme hatası: {str(e)}")
            return False
    
    def load_daily_data(self):
        """Günlük veriyi yükle"""
        try:
            if os.path.exists(self.daily_data_file):
                with open(self.daily_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            st.error(f"Günlük veri yükleme hatası: {str(e)}")
            return {}

# =============================================================================
# MEMBER MANAGER CLASS
# =============================================================================
class MemberManager:
    """Üye yönetimi sınıfı"""
    
    def __init__(self, token_manager, github_manager=None):
        self.members_file = "members.json"
        self.token_manager = token_manager
        self.github_manager = github_manager
        self.ensure_members_file()
    
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
        except Exception as e:
            st.error(f"Üye listesi yükleme hatası: {str(e)}")
            return []
    
    def get_active_members(self):
        """Aktif üyeleri getir"""
        all_members = self.get_all_members()
        return [member for member in all_members if member.get('is_active', True)]
    
    def save_members(self, members):
        """Üye listesini kaydet"""
        try:
            with open(self.members_file, 'w', encoding='utf-8') as f:
                json.dump(members, f, ensure_ascii=False, indent=2)
            
            # GitHub'a sync et (eğer bağlı ise ve otomatik sync aktifse)
            if (self.github_manager and 
                self.github_manager.connected and 
                st.session_state.get('auto_sync_enabled', False)):
                self.github_manager.sync_file(self.members_file)
            
            return True
        except Exception as e:
            st.error(f"Üye listesi kaydetme hatası: {str(e)}")
            return False
    
    def add_member(self, member_id, username, full_name):
        """Yeni üye ekle"""
        try:
            members = self.get_all_members()
            
            # Üye zaten var mı kontrol et
            existing_member = next((m for m in members if m['member_id'] == str(member_id)), None)
            if existing_member:
                st.warning(f"⚠️ Üye zaten mevcut: {username} (ID: {member_id})")
                return False
            
            # Yeni üye verisi oluştur
            new_member = {
                "member_id": str(member_id),
                "username": username or f"User_{member_id}",
                "full_name": full_name or f"Member {member_id}",
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "last_deposit_date": None,
                "days_without_deposit": 999,
                "api_data": {},
                "last_api_update": None,
                "email": "",
                "phone": "",
                "balance": 0,
                "currency": "TRY",
                "total_deposits": 0,
                "total_withdrawals": 0
            }
            
            # Listeye ekle
            members.append(new_member)
            
            # Kaydet
            success = self.save_members(members)
            
            if success:
                # API'den veri çekmeyi dene
                self.fetch_member_api_data(str(member_id))
            
            return success
            
        except Exception as e:
            st.error(f"Üye ekleme hatası: {str(e)}")
            return False
    
    def add_members_bulk(self, member_ids):
        """Toplu üye ekleme"""
        added_count = 0
        failed_ids = []
        
        # Progress bar oluştur
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, member_id in enumerate(member_ids):
            if member_id.strip():
                status_text.text(f"İşleniyor: {member_id.strip()}")
                
                success = self.add_member(
                    member_id.strip(),
                    f"User_{member_id.strip()}",
                    f"Member {member_id.strip()}"
                )
                
                if success:
                    added_count += 1
                    self.fetch_member_api_data(member_id.strip())
                else:
                    failed_ids.append(member_id.strip())
                
                # Progress güncelle
                progress = (i + 1) / len(member_ids)
                progress_bar.progress(progress)
        
        # Progress bar'ı temizle
        progress_bar.empty()
        status_text.empty()
        
        # Sonuçları göster
        if failed_ids:
            st.warning(f"⚠️ {len(failed_ids)} ID eklenemedi: {', '.join(failed_ids[:5])}{'...' if len(failed_ids) > 5 else ''}")
        
        return added_count
    
    def fetch_member_api_data(self, member_id):
        """API'den üye verilerini çek"""
        try:
            api_token = self.token_manager.get_api_token()
            
            if not api_token:
                return None
            
            # API URL'ini oluştur
            api_url = f"https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientById?id={member_id}"
            
            # Request headers
            headers = {
                'Authentication': api_token,
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://backoffice.betconstruct.com/',
                'Origin': 'https://backoffice.betconstruct.com',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # API çağrısı
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # API yanıtını işle
                processed_data = self.process_api_response(data)
                
                if processed_data:
                    # Üye veritabanını güncelle
                    self.update_member_api_data(member_id, processed_data)
                    return processed_data
            else:
                st.warning(f"⚠️ API yanıt hatası ({response.status_code}): {member_id}")
                return None
                
        except Exception as e:
            st.warning(f"⚠️ API çağrısı hatası: {str(e)}")
            return None
    
    def process_api_response(self, api_data):
        """API yanıtını işle ve standartlaştır"""
        try:
            # API yanıtındaki Data kısmını al
            data = api_data.get('Data', {})
            
            if not data:
                return None
            
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
                'total_deposits': 0,
                'total_withdrawals': 0,
                'deposit_count': 0,
                'withdrawal_count': 0
            }
            
            # Son yatırım tarihinden bugüne kadar geçen günleri hesapla
            if processed['last_deposit_date'] and processed['last_deposit_date'] not in ['', 'Bilinmiyor', None]:
                try:
                    date_str = str(processed['last_deposit_date'])
                    if 'T' in date_str:
                        last_deposit = datetime.fromisoformat(date_str.replace('Z', ''))
                    elif '.' in date_str and len(date_str.split('.')) == 3:
                        last_deposit = datetime.strptime(date_str.split(' ')[0], '%d.%m.%Y')
                    else:
                        last_deposit = datetime.fromisoformat(date_str)
                    
                    days_diff = (datetime.now() - last_deposit).days
                    processed['days_without_deposit'] = max(0, days_diff)
                except Exception:
                    processed['days_without_deposit'] = 999
            else:
                processed['days_without_deposit'] = 999
            
            return processed
            
        except Exception as e:
            st.error(f"API yanıt işleme hatası: {str(e)}")
            return None
    
    def update_member_api_data(self, member_id, api_data):
        """Üye API verilerini güncelle"""
        try:
            members = self.get_all_members()
            
            # Üyeyi bul
            member_index = -1
            for i, member in enumerate(members):
                if member['member_id'] == str(member_id):
                    member_index = i
                    break
            
            if member_index >= 0:
                # Mevcut üyeyi güncelle
                members[member_index]['api_data'] = api_data
                members[member_index]['last_api_update'] = datetime.now().isoformat()
                
                # Bazı alanları üye kaydına da kopyala
                if api_data:
                    if api_data.get('username'):
                        members[member_index]['username'] = api_data['username']
                    if api_data.get('full_name'):
                        members[member_index]['full_name'] = api_data['full_name']
                    
                    members[member_index]['email'] = api_data.get('email', '')
                    members[member_index]['phone'] = api_data.get('phone', '')
                    members[member_index]['balance'] = api_data.get('balance', 0)
                    members[member_index]['currency'] = api_data.get('currency', 'TRY')
                    members[member_index]['total_deposits'] = api_data.get('total_deposits', 0)
                    members[member_index]['total_withdrawals'] = api_data.get('total_withdrawals', 0)
                    members[member_index]['last_deposit_date'] = api_data.get('last_deposit_date')
                    members[member_index]['days_without_deposit'] = api_data.get('days_without_deposit', 999)
                
                # Kaydet
                return self.save_members(members)
            
            return False
            
        except Exception as e:
            st.error(f"Üye API veri güncelleme hatası: {str(e)}")
            return False

# =============================================================================
# VISUALIZATION CLASS
# =============================================================================
class Visualization:
    """Veri görselleştirme sınıfı"""
    
    def __init__(self):
        self.default_colors = px.colors.qualitative.Set3
    
    def create_empty_chart(self, message):
        """Boş grafik oluştur"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            height=400
        )
        return fig
    
    def create_member_distribution_charts(self, members):
        """Üye dağılım grafikleri oluştur"""
        try:
            if not members:
                return self.create_empty_chart("Üye verisi bulunamadı")
            
            # Alt grafikler oluştur
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Durum Dağılımı', 'Son Yatırım Analizi', 'Bakiye Dağılımı', 'Günlere Göre Dağılım'),
                specs=[[{"type": "pie"}, {"type": "bar"}],
                       [{"type": "histogram"}, {"type": "bar"}]]
            )
            
            # 1. Durum dağılımı (Pie chart)
            status_counts = {}
            for member in members:
                status = 'Aktif' if member.get('is_active', True) else 'Pasif'
                status_counts[status] = status_counts.get(status, 0) + 1
            
            fig.add_trace(
                go.Pie(
                    labels=list(status_counts.keys()),
                    values=list(status_counts.values()),
                    name="Durum"
                ),
                row=1, col=1
            )
            
            # 2. Son yatırım analizi (Bar chart)
            deposit_ranges = {
                '0-7 gün': 0,
                '8-30 gün': 0,
                '31-90 gün': 0,
                '90+ gün': 0
            }
            
            for member in members:
                days = member.get('days_without_deposit', 999)
                if days <= 7:
                    deposit_ranges['0-7 gün'] += 1
                elif days <= 30:
                    deposit_ranges['8-30 gün'] += 1
                elif days <= 90:
                    deposit_ranges['31-90 gün'] += 1
                else:
                    deposit_ranges['90+ gün'] += 1
            
            fig.add_trace(
                go.Bar(
                    x=list(deposit_ranges.keys()),
                    y=list(deposit_ranges.values()),
                    name="Son Yatırım",
                    marker_color='lightblue'
                ),
                row=1, col=2
            )
            
            # 3. Bakiye dağılımı (Histogram)
            balances = [member.get('balance', 0) for member in members if member.get('balance', 0) > 0]
            
            if balances:
                fig.add_trace(
                    go.Histogram(
                        x=balances,
                        name="Bakiye",
                        marker_color='lightgreen'
                    ),
                    row=2, col=1
                )
            
            # 4. Günlere göre dağılım (Bar chart)
            day_ranges = {
                '0-7': 0, '8-14': 0, '15-30': 0, '31-60': 0, '60+': 0
            }
            
            for member in members:
                days = member.get('days_without_deposit', 999)
                if days <= 7:
                    day_ranges['0-7'] += 1
                elif days <= 14:
                    day_ranges['8-14'] += 1
                elif days <= 30:
                    day_ranges['15-30'] += 1
                elif days <= 60:
                    day_ranges['31-60'] += 1
                else:
                    day_ranges['60+'] += 1
            
            fig.add_trace(
                go.Bar(
                    x=list(day_ranges.keys()),
                    y=list(day_ranges.values()),
                    name="Gün Aralıkları",
                    marker_color='orange'
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                height=600,
                title_text="Üye Dağılım Analizi",
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Üye dağılım grafiği hatası: {str(e)}")
            return self.create_empty_chart("Grafik oluşturulamadı")
    
    def create_top_members_chart(self, members, metric='total_deposits', top_n=10):
        """En iyi üyeler grafiği"""
        try:
            if not members:
                return self.create_empty_chart("Üye verisi bulunamadı")
            
            # Metrik değerlerine göre sırala
            sorted_members = sorted(
                members, 
                key=lambda x: x.get(metric, 0), 
                reverse=True
            )[:top_n]
            
            names = [m.get('username', 'N/A') for m in sorted_members]
            values = [m.get(metric, 0) for m in sorted_members]
            
            metric_labels = {
                'total_deposits': 'Toplam Yatırım (TRY)',
                'balance': 'Bakiye (TRY)',
                'deposit_count': 'Yatırım Sayısı',
                'days_without_deposit': 'Yatırımsız Gün Sayısı'
            }
            
            title = f"En İyi {top_n} Üye - {metric_labels.get(metric, metric)}"
            
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=names,
                        y=values,
                        marker_color='lightblue'
                    )
                ]
            )
            
            fig.update_layout(
                title=title,
                xaxis_title='Üyeler',
                yaxis_title=metric_labels.get(metric, metric),
                height=400,
                xaxis_tickangle=-45
            )
            
            return fig
            
        except Exception as e:
            st.error(f"En iyi üyeler grafiği hatası: {str(e)}")
            return self.create_empty_chart("Grafik oluşturulamadı")

# =============================================================================
# DAILY DATA MANAGER CLASS
# =============================================================================
class DailyDataManager:
    """Günlük veri yönetimi sınıfı"""
    
    def __init__(self):
        self.daily_data_file = "daily_data.json"
        self.ensure_daily_data_file()
    
    def ensure_daily_data_file(self):
        """Günlük veri dosyasını oluştur"""
        if not os.path.exists(self.daily_data_file):
            with open(self.daily_data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def load_daily_data(self):
        """Günlük veriyi yükle"""
        try:
            with open(self.daily_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Günlük veri yükleme hatası: {str(e)}")
            return {}
    
    def save_daily_data(self, data):
        """Günlük veriyi kaydet"""
        try:
            with open(self.daily_data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"Günlük veri kaydetme hatası: {str(e)}")
            return False

# =============================================================================
# MAIN APPLICATION
# =============================================================================
def main():
    """Ana uygulama fonksiyonu"""
    
    # Başlık
    st.title("📊 BTag Affiliate Takip Sistemi")
    st.markdown("---")
    
    # Session state başlatma
    if 'token_manager' not in st.session_state:
        st.session_state.token_manager = TokenManager()
    
    if 'github_manager' not in st.session_state:
        st.session_state.github_manager = GitHubManager(st.session_state.token_manager)
    
    if 'member_manager' not in st.session_state:
        st.session_state.member_manager = MemberManager(
            st.session_state.token_manager, 
            st.session_state.github_manager
        )
    
    if 'visualization' not in st.session_state:
        st.session_state.visualization = Visualization()
    
    if 'daily_data_manager' not in st.session_state:
        st.session_state.daily_data_manager = DailyDataManager()
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Kontrol Paneli")
        
        # Ana menü
        menu_option = st.selectbox(
            "Menü Seçin:",
            [
                "🏠 Ana Sayfa",
                "👥 Üye Yönetimi", 
                "📊 Raporlar",
                "📈 Analizler",
                "🔧 Ayarlar",
                "🔗 GitHub Entegrasyonu"
            ]
        )
        
        st.markdown("---")
        
        # Hızlı bilgiler
        members = st.session_state.member_manager.get_all_members()
        active_members = st.session_state.member_manager.get_active_members()
        
        st.metric("Toplam Üye", len(members))
        st.metric("Aktif Üye", len(active_members))
        
        if members:
            total_balance = sum(m.get('balance', 0) for m in members)
            st.metric("Toplam Bakiye", Utils.format_currency(total_balance))
    
    # Ana içerik
    if menu_option == "🏠 Ana Sayfa":
        show_dashboard()
    elif menu_option == "👥 Üye Yönetimi":
        show_member_management()
    elif menu_option == "📊 Raporlar":
        show_reports()
    elif menu_option == "📈 Analizler":
        show_analytics()
    elif menu_option == "🔧 Ayarlar":
        show_settings()
    elif menu_option == "🔗 GitHub Entegrasyonu":
        show_github_integration()

def show_dashboard():
    """Ana sayfa dashboard"""
    st.header("🏠 Ana Sayfa")
    
    # Özet kartlar
    col1, col2, col3, col4 = st.columns(4)
    
    members = st.session_state.member_manager.get_all_members()
    active_members = st.session_state.member_manager.get_active_members()
    
    with col1:
        st.metric(
            label="Toplam Üye", 
            value=len(members),
            delta=f"+{len([m for m in members if Utils.calculate_days_difference(m.get('created_at', '')) <= 7])} (7 gün)"
        )
    
    with col2:
        st.metric(
            label="Aktif Üye", 
            value=len(active_members),
            delta=f"{len(active_members)/len(members)*100:.1f}%" if members else "0%"
        )
    
    with col3:
        total_balance = sum(m.get('balance', 0) for m in members)
        st.metric(
            label="Toplam Bakiye", 
            value=Utils.format_currency(total_balance, "TRY")
        )
    
    with col4:
        recent_deposits = len([m for m in members if m.get('days_without_deposit', 999) <= 7])
        st.metric(
            label="Son 7 Gün Yatırım", 
            value=recent_deposits,
            delta=f"{recent_deposits/len(members)*100:.1f}%" if members else "0%"
        )
    
    st.markdown("---")
    
    # Grafikler
    if members:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Üye Dağılım Analizi")
            fig = st.session_state.visualization.create_member_distribution_charts(members)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🏆 En İyi 10 Üye (Bakiye)")
            fig = st.session_state.visualization.create_top_members_chart(members, 'balance', 10)
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("📝 Henüz üye verisi bulunmuyor. Üye Yönetimi bölümünden üye ekleyebilirsiniz.")

def show_member_management():
    """Üye yönetimi sayfası"""
    st.header("👥 Üye Yönetimi")
    
    tab1, tab2, tab3 = st.tabs(["👤 Tekil Üye Ekleme", "👥 Toplu Üye Ekleme", "📋 Üye Listesi"])
    
    with tab1:
        st.subheader("👤 Yeni Üye Ekle")
        
        with st.form("add_member_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                member_id = st.text_input("Üye ID", placeholder="123456789")
                username = st.text_input("Kullanıcı Adı", placeholder="kullanici_adi")
            
            with col2:
                full_name = st.text_input("Ad Soyad", placeholder="Ad Soyad")
                
            submitted = st.form_submit_button("➕ Üye Ekle")
            
            if submitted:
                if member_id and Utils.validate_member_id(member_id):
                    success = st.session_state.member_manager.add_member(
                        member_id, username, full_name
                    )
                    if success:
                        st.success(f"✅ Üye başarıyla eklendi: {member_id}")
                        st.rerun()
                    else:
                        st.error("❌ Üye eklenirken hata oluştu!")
                else:
                    st.error("❌ Geçerli bir üye ID girin (en az 6 haneli)!")
    
    with tab2:
        st.subheader("👥 Toplu Üye Ekleme")
        
        # Excel dosyası yükleme
        uploaded_file = st.file_uploader("Excel Dosyası Yükle", type=['xlsx', 'xls'])
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                st.write("📊 Yüklenen Veri:")
                st.dataframe(df.head())
                
                # Sütun seçimi
                if not df.empty:
                    id_column = st.selectbox("Üye ID Sütunu", df.columns)
                    
                    if st.button("📥 Excel'den Üye Ekle"):
                        if id_column in df.columns:
                            member_ids = df[id_column].dropna().astype(str).tolist()
                            valid_ids = [mid for mid in member_ids if Utils.validate_member_id(mid)]
                            
                            if valid_ids:
                                added_count = st.session_state.member_manager.add_members_bulk(valid_ids)
                                st.success(f"✅ {added_count} üye başarıyla eklendi!")
                                st.rerun()
                            else:
                                st.error("❌ Geçerli üye ID bulunamadı!")
            
            except Exception as e:
                st.error(f"❌ Excel dosyası okuma hatası: {str(e)}")
        
        # Manuel ID listesi
        st.markdown("**veya**")
        
        member_ids_text = st.text_area(
            "Üye ID Listesi (her satıra bir ID)",
            placeholder="123456789\n987654321\n456789123",
            height=150
        )
        
        if st.button("📝 Liste'den Üye Ekle"):
            if member_ids_text:
                member_ids = [mid.strip() for mid in member_ids_text.split('\n') if mid.strip()]
                valid_ids = [mid for mid in member_ids if Utils.validate_member_id(mid)]
                
                if valid_ids:
                    added_count = st.session_state.member_manager.add_members_bulk(valid_ids)
                    st.success(f"✅ {added_count} üye başarıyla eklendi!")
                    st.rerun()
                else:
                    st.error("❌ Geçerli üye ID bulunamadı!")
    
    with tab3:
        st.subheader("📋 Üye Listesi")
        
        members = st.session_state.member_manager.get_all_members()
        
        if members:
            # Filtreleme seçenekleri
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_filter = st.selectbox("Durum Filtresi", ["Tümü", "Aktif", "Pasif"])
            
            with col2:
                days_filter = st.selectbox(
                    "Yatırım Filtresi", 
                    ["Tümü", "Son 7 gün", "Son 30 gün", "30+ gün"]
                )
            
            with col3:
                search_term = st.text_input("🔍 Arama", placeholder="Üye ID, kullanıcı adı...")
            
            # Filtreleme uygula
            filtered_members = members.copy()
            
            if status_filter == "Aktif":
                filtered_members = [m for m in filtered_members if m.get('is_active', True)]
            elif status_filter == "Pasif":
                filtered_members = [m for m in filtered_members if not m.get('is_active', True)]
            
            if days_filter == "Son 7 gün":
                filtered_members = [m for m in filtered_members if m.get('days_without_deposit', 999) <= 7]
            elif days_filter == "Son 30 gün":
                filtered_members = [m for m in filtered_members if m.get('days_without_deposit', 999) <= 30]
            elif days_filter == "30+ gün":
                filtered_members = [m for m in filtered_members if m.get('days_without_deposit', 999) > 30]
            
            if search_term:
                filtered_members = [
                    m for m in filtered_members 
                    if search_term.lower() in m.get('member_id', '').lower() or
                       search_term.lower() in m.get('username', '').lower() or
                       search_term.lower() in m.get('full_name', '').lower()
                ]
            
            # Tablo gösterimi
            if filtered_members:
                # DataFrame oluştur
                display_data = []
                for member in filtered_members:
                    display_data.append({
                        'Üye ID': member.get('member_id', ''),
                        'Kullanıcı Adı': member.get('username', ''),
                        'Ad Soyad': member.get('full_name', ''),
                        'Bakiye': Utils.format_currency(member.get('balance', 0)),
                        'Son Yatırım': Utils.format_date(member.get('last_deposit_date')),
                        'Yatırımsız Gün': member.get('days_without_deposit', 999),
                        'Durum': '✅ Aktif' if member.get('is_active', True) else '❌ Pasif',
                        'Oluşturma Tarihi': Utils.format_date(member.get('created_at'))
                    })
                
                df_display = pd.DataFrame(display_data)
                st.dataframe(df_display, use_container_width=True)
                
                st.info(f"📊 Toplam {len(filtered_members)} üye gösteriliyor")
            else:
                st.warning("⚠️ Filtre kriterlerine uygun üye bulunamadı")
        else:
            st.info("📝 Henüz üye eklenmemiş. Yukarıdaki sekmelerden üye ekleyebilirsiniz.")

def show_reports():
    """Raporlar sayfası"""
    st.header("📊 Raporlar")
    
    tab1, tab2, tab3 = st.tabs(["📊 Genel Rapor", "📁 Veri Yükleme", "📤 Veri Export"])
    
    with tab1:
        st.subheader("📊 Genel Durum Raporu")
        
        members = st.session_state.member_manager.get_all_members()
        daily_data = st.session_state.daily_data_manager.load_daily_data()
        
        if members:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Toplam Üye", len(members))
                active_count = len([m for m in members if m.get('is_active', True)])
                st.metric("Aktif Üye", active_count)
            
            with col2:
                total_balance = sum(m.get('balance', 0) for m in members)
                st.metric("Toplam Bakiye", Utils.format_currency(total_balance))
                
                avg_balance = total_balance / len(members) if members else 0
                st.metric("Ortalama Bakiye", Utils.format_currency(avg_balance))
            
            with col3:
                recent_deposits = len([m for m in members if m.get('days_without_deposit', 999) <= 7])
                st.metric("Son 7 Gün Aktif", recent_deposits)
                
                risk_members = len([m for m in members if m.get('days_without_deposit', 999) > 90])
                st.metric("Risk Grubu (90+ gün)", risk_members)
            
            # Risk analizi
            st.subheader("⚠️ Risk Analizi")
            
            risk_analysis = {
                "Düşük Risk (0-7 gün)": len([m for m in members if m.get('days_without_deposit', 999) <= 7]),
                "Orta Risk (8-30 gün)": len([m for m in members if 7 < m.get('days_without_deposit', 999) <= 30]),
                "Yüksek Risk (31-90 gün)": len([m for m in members if 30 < m.get('days_without_deposit', 999) <= 90]),
                "Çok Yüksek Risk (90+ gün)": len([m for m in members if m.get('days_without_deposit', 999) > 90])
            }
            
            for risk_level, count in risk_analysis.items():
                percentage = (count / len(members)) * 100 if members else 0
                st.write(f"**{risk_level}**: {count} üye ({percentage:.1f}%)")
        else:
            st.info("📝 Rapor oluşturmak için önce üye eklemeniz gerekiyor.")
    
    with tab2:
        st.subheader("📁 Excel Veri Yükleme")
        
        # Kullanım kılavuzu
        with st.expander("📖 BTag Filtreleme Kılavuzu"):
            st.markdown("""
            **Excel'de BTag Filtreleme Nasıl Çalışır:**
            
            1. **BTag Sütunu Var İse:** 
               - Excel'de 'BTag', 'B Tag', 'Tag' veya 'Btag' adında sütun olmalı
               - Sistem sadece belirtilen BTag'a ait üyeleri işleyecek
               - Örnek: BTag sütununda 'ABC123' değeri olan satırlar
            
            2. **BTag Sütunu Yok İse:**
               - Tüm Excel verileri işlenir (filtreleme yapılmaz)
               - Uyarı mesajı gösterilir
            
            **Önerilen Excel Formatı:**
            | ID | Kullanıcı Adı | Müşteri Adı | BTag | Yatırımlar | Para Çekme |
            |---|---|---|---|---|---|
            | 12345 | user1 | Ali Veli | ABC123 | 1000 | 500 |
            """)
        
        # BTag ID girişi
        btag_id = st.text_input("BTag ID", placeholder="Örn: 2424878")
        
        # Tarih seçimi
        selected_date = st.date_input("Veri Tarihi", datetime.now())
        
        # Excel dosya yükleme
        uploaded_file = st.file_uploader(
            "Excel Dosyası Seçin", 
            type=['xlsx', 'xls'],
            help="Üye verilerini içeren Excel dosyasını yükleyin"
        )
        
        if uploaded_file and btag_id:
            try:
                # Excel dosyasını oku
                df = pd.read_excel(uploaded_file)
                st.success(f"✅ Dosya başarıyla okundu. {len(df)} satır veri bulundu.")
                
                # Veri önizlemesi
                st.subheader("📋 Veri Önizlemesi")
                st.dataframe(df.head(10))
                
                # Sütun bilgileri
                st.write("**Sütunlar:**", ', '.join(df.columns.tolist()))
                
                # Veri işleme
                data_processor = DataProcessor(st.session_state.github_manager)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("💾 Veriyi İşle ve Kaydet", use_container_width=True):
                        # BTag filtresi ile veriyi işle
                        processed_df = data_processor.process_excel_data(df, btag_filter=btag_id)
                        
                        if processed_df is not None:
                            # Yeni üyeleri kontrol et (sadece bu BTag'a ait olanlar)
                            existing_members = st.session_state.member_manager.get_all_members()
                            existing_ids = set(m.get('member_id', '') for m in existing_members)
                            new_member_ids = []
                            
                            for _, row in processed_df.iterrows():
                                member_id = str(row.get('member_id', ''))
                                if member_id and member_id not in existing_ids:
                                    new_member_ids.append(member_id)
                            
                            # Eğer yeni üyeler varsa kullanıcıya sor
                            if new_member_ids:
                                st.warning(f"⚠️ BTag '{btag_id}' için Excel'de {len(new_member_ids)} yeni üye bulundu!")
                                st.write("**Yeni üyeler:**", ", ".join(new_member_ids[:10]))
                                if len(new_member_ids) > 10:
                                    st.write(f"...ve {len(new_member_ids) - 10} üye daha")
                                
                                add_new_members = st.checkbox(
                                    f"Bu {len(new_member_ids)} yeni üyeyi '{btag_id}' BTag'ı için sisteme ekle",
                                    value=True,
                                    help=f"Excel'deki {btag_id} BTag'ına ait yeni üyeleri sisteme ekler"
                                )
                                
                                if st.button("✅ Onayla ve Kaydet", type="primary"):
                                    # Yeni üyeleri ekle (seçiliyse)
                                    if add_new_members:
                                        for _, row in processed_df.iterrows():
                                            member_id = str(row.get('member_id', ''))
                                            if member_id in new_member_ids:
                                                username = row.get('username', '')
                                                customer_name = row.get('customer_name', '')
                                                st.session_state.member_manager.add_member(
                                                    member_id, username, customer_name
                                                )
                                        st.success(f"✅ {len(new_member_ids)} yeni üye eklendi!")
                                    
                                    # Günlük veriyi kaydet
                                    success = data_processor.save_daily_data(processed_df, btag_id, selected_date)
                                    
                                    if success:
                                        st.success("✅ Veri başarıyla kaydedildi!")
                                        
                                        # İşlenmiş veriyi göster
                                        st.subheader("✅ İşlenmiş Veri")
                                        st.dataframe(processed_df)
                                        
                                        # GitHub sync (eğer bağlı ise)
                                        if st.session_state.github_manager.connected:
                                            st.session_state.github_manager.sync_file("daily_data.json")
                                            if add_new_members:
                                                st.session_state.github_manager.sync_file("members.json")
                                            st.info("🔄 Veri GitHub'a senkronize edildi")
                                    else:
                                        st.error("❌ Veri kaydetme başarısız!")
                            else:
                                # Yeni üye yoksa direkt kaydet
                                success = data_processor.save_daily_data(processed_df, btag_id, selected_date)
                                
                                if success:
                                    st.success("✅ Veri başarıyla kaydedildi!")
                                    
                                    # İşlenmiş veriyi göster
                                    st.subheader("✅ İşlenmiş Veri")
                                    st.dataframe(processed_df)
                                    
                                    # GitHub sync (eğer bağlı ise)
                                    if st.session_state.github_manager.connected:
                                        st.session_state.github_manager.sync_file("daily_data.json")
                                        st.info("🔄 Veri GitHub'a senkronize edildi")
                                else:
                                    st.error("❌ Veri kaydetme başarısız!")
                
                with col2:
                    if st.button("🔍 Sadece Veri Analizi", use_container_width=True):
                        # BTag filtresi ile veriyi analiz et
                        processed_df = data_processor.process_excel_data(df, btag_filter=btag_id)
                        
                        if processed_df is not None:
                            # Yeni üyeleri kontrol et (sadece bu BTag'a ait olanlar)
                            existing_members = st.session_state.member_manager.get_all_members()
                            existing_ids = set(m.get('member_id', '') for m in existing_members)
                            new_member_ids = []
                            
                            for _, row in processed_df.iterrows():
                                member_id = str(row.get('member_id', ''))
                                if member_id and member_id not in existing_ids:
                                    new_member_ids.append(member_id)
                            
                            # Yeni üye bilgisi göster
                            if new_member_ids:
                                st.info(f"ℹ️ BTag '{btag_id}' için Excel'de {len(new_member_ids)} yeni üye tespit edildi.")
                            
                            st.success("✅ Veri analizi tamamlandı!")
                            
                            # Analiz sonuçları
                            st.subheader("📈 Veri Analizi")
                            
                            col_a, col_b, col_c = st.columns(3)
                            
                            with col_a:
                                st.metric("Toplam Üye", len(processed_df))
                                st.metric("Toplam Yatırım", Utils.format_currency(processed_df['total_deposits'].sum()))
                                if new_member_ids:
                                    st.metric("Yeni Üye Sayısı", len(new_member_ids))
                            
                            with col_b:
                                st.metric("Toplam Çekim", Utils.format_currency(processed_df['total_withdrawals'].sum()))
                                st.metric("Net Tutar", Utils.format_currency(processed_df['total_deposits'].sum() - processed_df['total_withdrawals'].sum()))
                            
                            with col_c:
                                st.metric("Ortalama Yatırım", Utils.format_currency(processed_df['total_deposits'].mean()))
                                active_depositors = len(processed_df[processed_df['total_deposits'] > 0])
                                st.metric("Yatırım Yapan Üye", active_depositors)
                            
                            # Yeni üyeler listesi (varsa)
                            if new_member_ids:
                                st.subheader("🆕 Yeni Üyeler")
                                st.write("**Yeni üye ID'leri:**", ", ".join(new_member_ids[:20]))
                                if len(new_member_ids) > 20:
                                    st.write(f"...ve {len(new_member_ids) - 20} üye daha")
                            
                            # İşlenmiş veriyi göster
                            st.subheader("📋 İşlenmiş Veri")
                            st.dataframe(processed_df)
                            
            except Exception as e:
                st.error(f"❌ Dosya okuma hatası: {str(e)}")
        
        elif uploaded_file and not btag_id:
            st.warning("⚠️ Lütfen BTag ID girin")
        elif btag_id and not uploaded_file:
            st.info("📁 Lütfen Excel dosyası yükleyin")
    
    with tab3:
        st.subheader("📤 Veri Export")
        
        export_type = st.selectbox(
            "Export Türü Seçin:",
            ["Üye Listesi", "Günlük Veriler", "Tüm Veriler"]
        )
        
        if export_type == "Üye Listesi":
            members = st.session_state.member_manager.get_all_members()
            
            if members:
                # DataFrame oluştur
                export_data = []
                for member in members:
                    export_data.append({
                        'Üye ID': member.get('member_id', ''),
                        'Kullanıcı Adı': member.get('username', ''),
                        'Ad Soyad': member.get('full_name', ''),
                        'E-posta': member.get('email', ''),
                        'Telefon': member.get('phone', ''),
                        'Bakiye': member.get('balance', 0),
                        'Para Birimi': member.get('currency', 'TRY'),
                        'Toplam Yatırım': member.get('total_deposits', 0),
                        'Toplam Çekim': member.get('total_withdrawals', 0),
                        'Son Yatırım Tarihi': member.get('last_deposit_date', ''),
                        'Yatırımsız Gün': member.get('days_without_deposit', 999),
                        'Durum': 'Aktif' if member.get('is_active', True) else 'Pasif',
                        'Oluşturma Tarihi': member.get('created_at', ''),
                        'Son API Güncelleme': member.get('last_api_update', '')
                    })
                
                df_export = pd.DataFrame(export_data)
                
                # Download butonu
                if st.button("📥 Üye Listesi İndir (Excel)"):
                    # Excel dosyası oluştur
                    output = io.BytesIO()
                    df_export.to_excel(output, engine='openpyxl', sheet_name='Üye Listesi', index=False)
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label="📁 Excel Dosyasını İndir",
                        data=excel_data,
                        file_name=f"uye_listesi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                # Önizleme
                st.subheader("📋 Export Önizlemesi")
                st.dataframe(df_export.head())
                st.info(f"📊 Toplam {len(df_export)} satır export edilecek")
            else:
                st.info("📝 Export edilecek üye verisi bulunamadı")

def show_analytics():
    """Analizler sayfası"""
    st.header("📈 Analizler")
    
    members = st.session_state.member_manager.get_all_members()
    
    if not members:
        st.info("📝 Analiz için önce üye eklemeniz gerekiyor.")
        return
    
    tab1, tab2 = st.tabs(["📊 Üye Analizleri", "🎯 Performans Analizleri"])
    
    with tab1:
        st.subheader("📊 Üye Davranış Analizleri")
        
        # Üye dağılım grafikleri
        fig = st.session_state.visualization.create_member_distribution_charts(members)
        st.plotly_chart(fig, use_container_width=True)
        
        # En iyi üyeler
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏆 En Yüksek Bakiyeli Üyeler")
            fig = st.session_state.visualization.create_top_members_chart(members, 'balance', 10)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("💰 En Çok Yatırım Yapan Üyeler")
            fig = st.session_state.visualization.create_top_members_chart(members, 'total_deposits', 10)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("🎯 Performans Göstergeleri")
        
        # KPI kartları
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            active_ratio = len([m for m in members if m.get('days_without_deposit', 999) <= 7]) / len(members) * 100
            st.metric("Haftalık Aktivite Oranı", f"{active_ratio:.1f}%")
        
        with col2:
            monthly_active = len([m for m in members if m.get('days_without_deposit', 999) <= 30]) / len(members) * 100
            st.metric("Aylık Aktivite Oranı", f"{monthly_active:.1f}%")
        
        with col3:
            total_balance = sum(m.get('balance', 0) for m in members)
            avg_balance = total_balance / len(members)
            st.metric("Ortalama Bakiye", Utils.format_currency(avg_balance))
        
        with col4:
            risk_members = len([m for m in members if m.get('days_without_deposit', 999) > 90])
            risk_ratio = risk_members / len(members) * 100
            st.metric("Risk Oranı (90+ gün)", f"{risk_ratio:.1f}%")

def show_settings():
    """Ayarlar sayfası"""
    st.header("🔧 Ayarlar")
    
    tab1, tab2, tab3 = st.tabs(["🔑 Token Ayarları", "🔧 Genel Ayarlar", "📊 Sistem Bilgileri"])
    
    with tab1:
        st.subheader("🔑 API Token Ayarları")
        
        token_manager = st.session_state.token_manager
        
        # Mevcut token bilgileri
        current_api_token = token_manager.get_api_token()
        current_github_token = token_manager.get_github_token()
        
        st.write("**Mevcut API Token:**", current_api_token[:10] + "..." if current_api_token else "Henüz ayarlanmamış")
        st.write("**Mevcut GitHub Token:**", current_github_token[:15] + "..." if current_github_token else "Henüz ayarlanmamış")
        
        # Token güncelleme
        with st.form("token_update_form"):
            new_api_token = st.text_input("Yeni API Token", type="password", placeholder="API token girin...")
            new_github_token = st.text_input("Yeni GitHub Token", type="password", placeholder="GitHub PAT girin...")
            
            if st.form_submit_button("🔄 Token'ları Güncelle"):
                updated = False
                
                if new_api_token:
                    tokens = token_manager.load_tokens()
                    tokens['api_token'] = new_api_token
                    token_manager.save_tokens(tokens)
                    updated = True
                
                if new_github_token:
                    tokens = token_manager.load_tokens()
                    tokens['github_token'] = new_github_token
                    token_manager.save_tokens(tokens)
                    updated = True
                
                if updated:
                    st.success("✅ Token'lar başarıyla güncellendi!")
                    st.rerun()
                else:
                    st.warning("⚠️ Güncellenecek token bulunamadı")
    
    with tab2:
        st.subheader("🔧 Genel Ayarlar")
        
        # Otomatik sync ayarı
        auto_sync = st.checkbox(
            "🔄 Otomatik GitHub Senkronizasyonu", 
            value=st.session_state.get('auto_sync_enabled', True),
            help="Veriler kaydedildiğinde otomatik olarak GitHub'a senkronize et"
        )
        st.session_state.auto_sync_enabled = auto_sync
        
        # API çağrı limiti
        api_timeout = st.slider("⏱️ API Zaman Aşımı (saniye)", 5, 60, 10)
        st.session_state.api_timeout = api_timeout
        
        # Veri saklama süresi
        data_retention = st.selectbox(
            "📅 Veri Saklama Süresi",
            ["30 gün", "60 gün", "90 gün", "6 ay", "1 yıl", "Sınırsız"],
            index=2
        )
        st.session_state.data_retention = data_retention
    
    with tab3:
        st.subheader("📊 Sistem Bilgileri")
        
        # Dosya boyutları
        file_sizes = {}
        for filename in ["members.json", "daily_data.json", "token.json"]:
            if os.path.exists(filename):
                size = os.path.getsize(filename)
                file_sizes[filename] = f"{size:,} bytes"
            else:
                file_sizes[filename] = "Dosya bulunamadı"
        
        for filename, size in file_sizes.items():
            st.write(f"**{filename}:** {size}")
        
        # Üye istatistikleri
        members = st.session_state.member_manager.get_all_members()
        st.write(f"**Toplam Üye Sayısı:** {len(members)}")
        st.write(f"**Aktif Üye Sayısı:** {len([m for m in members if m.get('is_active', True)])}")
        
        # Günlük veri istatistikleri
        daily_data = st.session_state.daily_data_manager.load_daily_data()
        st.write(f"**Günlük Veri Kayıtları:** {len(daily_data)} gün")
        
        total_btags = set()
        for date_data in daily_data.values():
            total_btags.update(date_data.keys())
        st.write(f"**Toplam BTag Sayısı:** {len(total_btags)}")

def show_github_integration():
    """GitHub entegrasyonu sayfası"""
    st.header("🔗 GitHub Entegrasyonu")
    
    github_manager = st.session_state.github_manager
    
    # Bağlantı durumu
    if github_manager.connected:
        st.success(f"✅ GitHub'a bağlı: {github_manager.repo_name}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Tüm Dosyaları Sync Et"):
                files_to_sync = ["members.json", "daily_data.json", "token.json"]
                success_count = 0
                
                for file_path in files_to_sync:
                    if os.path.exists(file_path):
                        if github_manager.sync_file(file_path):
                            success_count += 1
                
                st.success(f"✅ {success_count} dosya başarıyla sync edildi!")
        
        with col2:
            if st.button("🔧 Bağlantıyı Test Et"):
                if github_manager.test_connection():
                    st.success("✅ GitHub bağlantısı başarılı!")
                else:
                    st.error("❌ GitHub bağlantı testi başarısız!")
        
        # Son sync bilgileri
        st.subheader("📊 Sync Durumu")
        
        sync_status = []
        for filename in ["members.json", "daily_data.json", "token.json"]:
            if os.path.exists(filename):
                mod_time = datetime.fromtimestamp(os.path.getmtime(filename))
                sync_status.append({
                    'Dosya': filename,
                    'Son Değişiklik': mod_time.strftime('%d.%m.%Y %H:%M:%S'),
                    'Boyut': f"{os.path.getsize(filename):,} bytes"
                })
        
        if sync_status:
            df_sync = pd.DataFrame(sync_status)
            st.dataframe(df_sync, use_container_width=True)
    
    else:
        st.warning("⚠️ GitHub'a bağlı değilsiniz")
        
        # Bağlantı formu
        with st.form("github_connect_form"):
            st.subheader("🔗 GitHub Repository Bağlantısı")
            
            repo_url = st.text_input(
                "Repository URL", 
                placeholder="https://github.com/kullanici/repo-adi",
                help="GitHub repository URL'sini girin"
            )
            
            if st.form_submit_button("🔗 Bağlan"):
                if repo_url:
                    success = github_manager.connect_repository(repo_url)
                    if success:
                        st.success("✅ GitHub'a başarıyla bağlandı!")
                        st.rerun()
                    else:
                        st.error("❌ GitHub bağlantısı başarısız! Token ve repository URL'sini kontrol edin.")
                else:
                    st.error("❌ Lütfen repository URL'si girin!")

if __name__ == "__main__":
    main()

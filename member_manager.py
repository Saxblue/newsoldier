import json
import os
import requests
import streamlit as st
from datetime import datetime
import pandas as pd

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
                self.github_manager.is_connected() and 
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
                
                # Önce basit olarak ekle
                success = self.add_member(
                    member_id.strip(),
                    f"User_{member_id.strip()}",
                    f"Member {member_id.strip()}"
                )
                
                if success:
                    added_count += 1
                    # API'den veri çekmeyi dene
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
                'total_deposits': 0,  # Bu bilgiler ayrı API'den gelebilir
                'total_withdrawals': 0,
                'deposit_count': 0,
                'withdrawal_count': 0
            }
            
            # Son yatırım tarihinden bugüne kadar geçen günleri hesapla
            if processed['last_deposit_date'] and processed['last_deposit_date'] not in ['', 'Bilinmiyor', None]:
                try:
                    # Farklı tarih formatlarını dene
                    date_str = str(processed['last_deposit_date'])
                    if 'T' in date_str:
                        # ISO format
                        last_deposit = datetime.fromisoformat(date_str.replace('Z', ''))
                    elif '.' in date_str and len(date_str.split('.')) == 3:
                        # DD.MM.YYYY format
                        last_deposit = datetime.strptime(date_str.split(' ')[0], '%d.%m.%Y')
                    else:
                        # Diğer formatlar için varsayılan parsing
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
                    members[member_index]['last_casino_bet'] = api_data.get('last_casino_bet')
                    members[member_index]['registration_date'] = api_data.get('registration_date', '')
                    members[member_index]['last_login_date'] = api_data.get('last_login_date', '')
                    members[member_index]['partner_name'] = api_data.get('partner_name', '')
                    members[member_index]['birth_date'] = api_data.get('birth_date', '')
                
                # Kaydet
                return self.save_members(members)
            
            return False
            
        except Exception as e:
            st.error(f"Üye API veri güncelleme hatası: {str(e)}")
            return False
    
    def refresh_all_members_api_data(self):
        """Tüm üyelerin API verilerini yenile"""
        try:
            members = self.get_all_members()
            
            if not members:
                st.info("📝 Yenilenecek üye bulunamadı.")
                return 0
            
            api_token = self.token_manager.get_api_token()
            if not api_token:
                st.error("❌ API token bulunamadı!")
                return 0
            
            updated_count = 0
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, member in enumerate(members):
                member_id = member.get('member_id', '')
                username = member.get('username', member_id)
                
                if member_id:
                    status_text.text(f"Yenileniyor: {username} ({member_id})")
                    
                    api_data = self.fetch_member_api_data(member_id)
                    if api_data:
                        updated_count += 1
                
                # Progress güncelle
                progress = (i + 1) / len(members)
                progress_bar.progress(progress)
            
            progress_bar.empty()
            status_text.empty()
            
            return updated_count
            
        except Exception as e:
            st.error(f"Toplu API veri yenileme hatası: {str(e)}")
            return 0
    
    def get_member_by_id(self, member_id):
        """ID'ye göre üye getir"""
        members = self.get_all_members()
        return next((m for m in members if m['member_id'] == str(member_id)), None)
    
    def update_member(self, member_id, updates):
        """Üye bilgilerini güncelle"""
        try:
            members = self.get_all_members()
            
            for i, member in enumerate(members):
                if member['member_id'] == str(member_id):
                    # Güncellemeleri uygula
                    for key, value in updates.items():
                        members[i][key] = value
                    
                    members[i]['updated_at'] = datetime.now().isoformat()
                    
                    return self.save_members(members)
            
            return False
            
        except Exception as e:
            st.error(f"Üye güncelleme hatası: {str(e)}")
            return False
    
    def delete_member(self, member_id):
        """Üyeyi sil"""
        try:
            members = self.get_all_members()
            
            # Üyeyi bul ve sil
            original_count = len(members)
            members = [m for m in members if m['member_id'] != str(member_id)]
            
            if len(members) < original_count:
                return self.save_members(members)
            else:
                return False
            
        except Exception as e:
            st.error(f"Üye silme hatası: {str(e)}")
            return False
    
    def deactivate_member(self, member_id):
        """Üyeyi pasif yap"""
        return self.update_member(member_id, {'is_active': False})
    
    def activate_member(self, member_id):
        """Üyeyi aktif yap"""
        return self.update_member(member_id, {'is_active': True})
    
    def get_members_by_criteria(self, criteria):
        """Kriterlere göre üyeleri filtrele"""
        try:
            members = self.get_all_members()
            filtered_members = []
            
            for member in members:
                match = True
                
                for key, value in criteria.items():
                    if key == 'days_without_deposit_max':
                        if member.get('days_without_deposit', 999) > value:
                            match = False
                            break
                    elif key == 'days_without_deposit_min':
                        if member.get('days_without_deposit', 999) < value:
                            match = False
                            break
                    elif key == 'is_active':
                        if member.get('is_active', True) != value:
                            match = False
                            break
                    elif key in member:
                        if str(member[key]).lower() != str(value).lower():
                            match = False
                            break
                
                if match:
                    filtered_members.append(member)
            
            return filtered_members
            
        except Exception as e:
            st.error(f"Üye filtreleme hatası: {str(e)}")
            return []
    
    def get_member_statistics(self):
        """Üye istatistiklerini getir"""
        try:
            members = self.get_all_members()
            
            stats = {
                'total_members': len(members),
                'active_members': len([m for m in members if m.get('is_active', True)]),
                'members_with_recent_deposits': len([m for m in members if m.get('days_without_deposit', 999) <= 7]),
                'members_without_deposits': len([m for m in members if m.get('days_without_deposit', 999) >= 30]),
                'total_balance': sum(m.get('balance', 0) for m in members),
                'average_days_without_deposit': 0,
                'members_with_email': len([m for m in members if m.get('email', '')]),
                'members_with_phone': len([m for m in members if m.get('phone', '')])
            }
            
            # Ortalama yatırımsız gün hesapla
            if members:
                valid_days = [m.get('days_without_deposit', 999) for m in members if m.get('days_without_deposit', 999) < 999]
                if valid_days:
                    stats['average_days_without_deposit'] = sum(valid_days) / len(valid_days)
            
            return stats
            
        except Exception as e:
            st.error(f"Üye istatistikleri hatası: {str(e)}")
            return {}
    
    def test_api_connection(self):
        """API bağlantısını test et"""
        try:
            api_token = self.token_manager.get_api_token()
            
            if not api_token:
                return False
            
            # Test API çağrısı - örnek bir ID ile
            test_url = "https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientById?id=1"
            
            headers = {
                'Authentication': api_token,
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Referer': 'https://backoffice.betconstruct.com/'
            }
            
            response = requests.get(test_url, headers=headers, timeout=5)
            
            # 200 (başarılı) veya 404 (üye bulunamadı) kabul edilebilir
            return response.status_code in [200, 404]
            
        except Exception:
            return False
    
    def export_members_to_excel(self):
        """Üyeleri Excel'e export et"""
        try:
            members = self.get_all_members()
            
            if not members:
                return None
            
            # DataFrame oluştur
            df = pd.DataFrame(members)
            
            # Tarih sütunlarını düzenle
            date_columns = ['created_at', 'last_api_update', 'registration_date', 'last_login_date']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            st.error(f"Excel export hatası: {str(e)}")
            return None
    
    def import_members_from_excel(self, df):
        """Excel'den üyeleri import et"""
        try:
            imported_count = 0
            
            for _, row in df.iterrows():
                member_id = row.get('member_id', '')
                username = row.get('username', '')
                full_name = row.get('full_name', '')
                
                if member_id:
                    success = self.add_member(member_id, username, full_name)
                    if success:
                        imported_count += 1
            
            return imported_count
            
        except Exception as e:
            st.error(f"Excel import hatası: {str(e)}")
            return 0

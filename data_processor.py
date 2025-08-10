import pandas as pd
import json
import os
import streamlit as st
from datetime import datetime, timedelta

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
    
    def process_excel_data(self, df):
        """Excel verisini işle"""
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
                'Total Withdrawals': 'total_withdrawals'
            }
            
            df_processed = df.copy()
            
            # Sütun adlarını standartlaştır
            original_columns = df_processed.columns.tolist()
            for old_col, new_col in column_mapping.items():
                if old_col in df_processed.columns:
                    df_processed = df_processed.rename(columns={old_col: new_col})
            
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
                self.github_manager.is_connected() and 
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
    
    def get_daily_data_range(self, start_date, end_date):
        """Tarih aralığındaki günlük veriyi getir"""
        try:
            daily_data = self.load_daily_data()
            filtered_data = {}
            
            # Tarih aralığını oluştur
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                if date_str in daily_data:
                    filtered_data[date_str] = daily_data[date_str]
                current_date += timedelta(days=1)
            
            return filtered_data
            
        except Exception as e:
            st.error(f"Tarih aralığı veri getirme hatası: {str(e)}")
            return {}
    
    def get_btag_data(self, btag, date=None):
        """Belirli BTag'in verilerini getir"""
        try:
            daily_data = self.load_daily_data()
            
            if date:
                date_str = date.strftime('%Y-%m-%d')
                if date_str in daily_data and btag in daily_data[date_str]:
                    return daily_data[date_str][btag]
                return []
            else:
                # Tüm tarihlerden BTag verilerini topla
                all_data = []
                for date_str, btags in daily_data.items():
                    if btag in btags:
                        for record in btags[btag]:
                            record['date'] = date_str
                            all_data.append(record)
                return all_data
                
        except Exception as e:
            st.error(f"BTag veri getirme hatası: {str(e)}")
            return []
    
    def get_member_history(self, member_id):
        """Üye geçmişini getir"""
        try:
            daily_data = self.load_daily_data()
            member_history = []
            
            for date_str, btags in daily_data.items():
                for btag, members in btags.items():
                    for member in members:
                        if str(member.get('member_id', '')) == str(member_id):
                            member_data = member.copy()
                            member_data['date'] = date_str
                            member_data['btag'] = btag
                            member_history.append(member_data)
            
            # Tarihe göre sırala
            member_history.sort(key=lambda x: x['date'])
            return member_history
            
        except Exception as e:
            st.error(f"Üye geçmişi getirme hatası: {str(e)}")
            return []
    
    def get_summary_stats(self, start_date=None, end_date=None):
        """Özet istatistikleri getir"""
        try:
            daily_data = self.load_daily_data()
            
            if start_date and end_date:
                daily_data = self.get_daily_data_range(start_date, end_date)
            
            stats = {
                'total_members': set(),
                'total_deposits': 0,
                'total_withdrawals': 0,
                'total_deposit_count': 0,
                'total_withdrawal_count': 0,
                'active_btags': set(),
                'dates_count': len(daily_data)
            }
            
            for date_str, btags in daily_data.items():
                stats['active_btags'].update(btags.keys())
                
                for btag, members in btags.items():
                    for member in members:
                        stats['total_members'].add(member.get('member_id', ''))
                        stats['total_deposits'] += member.get('total_deposits', 0)
                        stats['total_withdrawals'] += member.get('total_withdrawals', 0)
                        stats['total_deposit_count'] += member.get('deposit_count', 0)
                        stats['total_withdrawal_count'] += member.get('withdrawal_count', 0)
            
            # Set'leri sayıya çevir
            stats['total_members'] = len(stats['total_members'])
            stats['active_btags'] = len(stats['active_btags'])
            
            return stats
            
        except Exception as e:
            st.error(f"İstatistik hesaplama hatası: {str(e)}")
            return {}
    
    def export_data_to_excel(self, start_date=None, end_date=None, btag=None):
        """Veriyi Excel'e export et"""
        try:
            daily_data = self.load_daily_data()
            
            if start_date and end_date:
                daily_data = self.get_daily_data_range(start_date, end_date)
            
            all_records = []
            
            for date_str, btags in daily_data.items():
                for btag_id, members in btags.items():
                    if btag and btag != btag_id:
                        continue
                    
                    for member in members:
                        record = member.copy()
                        record['date'] = date_str
                        record['btag'] = btag_id
                        all_records.append(record)
            
            if all_records:
                df = pd.DataFrame(all_records)
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"Excel export hatası: {str(e)}")
            return pd.DataFrame()
    
    def import_data_from_backup(self, backup_data):
        """Backup'tan veri import et"""
        try:
            if isinstance(backup_data, str):
                backup_data = json.loads(backup_data)
            
            # Mevcut veriyi yedekle
            current_data = self.load_daily_data()
            backup_filename = f"backup_before_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(backup_filename, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            
            # Yeni veriyi kaydet
            with open(self.daily_data_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            st.error(f"Backup import hatası: {str(e)}")
            return False
    
    def clean_old_data(self, days_to_keep=90):
        """Eski verileri temizle"""
        try:
            daily_data = self.load_daily_data()
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
            
            cleaned_data = {}
            removed_count = 0
            
            for date_str, btags in daily_data.items():
                if date_str >= cutoff_date:
                    cleaned_data[date_str] = btags
                else:
                    removed_count += 1
            
            if removed_count > 0:
                # Temizlenmiş veriyi kaydet
                with open(self.daily_data_file, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
                
                # GitHub'a sync et
                if (self.github_manager and 
                    self.github_manager.is_connected() and 
                    st.session_state.get('auto_sync_enabled', False)):
                    self.github_manager.sync_file(self.daily_data_file)
                
                return True
            
            return False
            
        except Exception as e:
            st.error(f"Veri temizleme hatası: {str(e)}")
            return False
    
    def get_data_file_count(self):
        """Veri dosyası sayısını getir"""
        try:
            data_files = [self.daily_data_file, "members.json", "token.json"]
            existing_files = sum(1 for f in data_files if os.path.exists(f))
            return existing_files
        except:
            return 0
    
    def validate_data_integrity(self):
        """Veri bütünlüğünü kontrol et"""
        try:
            daily_data = self.load_daily_data()
            issues = []
            
            for date_str, btags in daily_data.items():
                # Tarih formatını kontrol et
                try:
                    datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    issues.append(f"Geçersiz tarih formatı: {date_str}")
                
                for btag, members in btags.items():
                    if not isinstance(members, list):
                        issues.append(f"Geçersiz üye listesi: {date_str}/{btag}")
                        continue
                    
                    for i, member in enumerate(members):
                        if not isinstance(member, dict):
                            issues.append(f"Geçersiz üye verisi: {date_str}/{btag}/{i}")
                            continue
                        
                        # Gerekli alanları kontrol et
                        required_fields = ['member_id', 'username']
                        for field in required_fields:
                            if field not in member:
                                issues.append(f"Eksik alan {field}: {date_str}/{btag}/{i}")
                        
                        # Numerik alanları kontrol et
                        numeric_fields = ['deposit_count', 'total_deposits', 'withdrawal_count', 'total_withdrawals']
                        for field in numeric_fields:
                            if field in member:
                                try:
                                    float(member[field])
                                except (ValueError, TypeError):
                                    issues.append(f"Geçersiz numerik değer {field}: {date_str}/{btag}/{i}")
            
            return issues
            
        except Exception as e:
            return [f"Veri bütünlük kontrolü hatası: {str(e)}"]
    
    def get_btag_list(self):
        """Tüm BTag'leri listele"""
        try:
            daily_data = self.load_daily_data()
            btags = set()
            
            for date_data in daily_data.values():
                btags.update(date_data.keys())
            
            return sorted(list(btags))
        except:
            return []
    
    def get_date_range(self):
        """Veri tarih aralığını getir"""
        try:
            daily_data = self.load_daily_data()
            dates = list(daily_data.keys())
            
            if dates:
                return {
                    'start_date': min(dates),
                    'end_date': max(dates),
                    'total_days': len(dates)
                }
            return None
        except:
            return None

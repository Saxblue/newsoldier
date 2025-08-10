import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, timedelta
import io
import base64

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
            
            # Farklı tarih formatlarını dene
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
                elif format_type == "time_ago":
                    return Utils.time_ago(parsed_date)
                else:
                    return parsed_date.strftime('%d.%m.%Y %H:%M:%S')
            else:
                return str(date_str)
                
        except Exception as e:
            return "Geçersiz tarih"
    
    @staticmethod
    def time_ago(date_obj):
        """Geçen zamanı hesapla"""
        try:
            now = datetime.now()
            if date_obj.tzinfo is not None:
                # Timezone aware datetime'ı naive'e çevir
                date_obj = date_obj.replace(tzinfo=None)
            
            diff = now - date_obj
            
            if diff.days > 0:
                return f"{diff.days} gün önce"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} saat önce"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} dakika önce"
            else:
                return "Az önce"
        except:
            return "Bilinmiyor"
    
    @staticmethod
    def calculate_days_difference(date_str):
        """İki tarih arasındaki gün farkını hesapla"""
        try:
            if not date_str or date_str in ['', 'None', 'null', None]:
                return 999
            
            # Tarih formatlarını dene
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
            
            # Sadece rakamlardan oluşmalı ve en az 6 haneli olmalı
            member_id_str = str(member_id).strip()
            return member_id_str.isdigit() and len(member_id_str) >= 6
        except:
            return False
    
    @staticmethod
    def validate_btag_id(btag_id):
        """BTag ID'sini doğrula"""
        try:
            if not btag_id:
                return False
            
            # Sadece rakamlardan oluşmalı ve en az 4 haneli olmalı
            btag_id_str = str(btag_id).strip()
            return btag_id_str.isdigit() and len(btag_id_str) >= 4
        except:
            return False
    
    @staticmethod
    def clean_text(text):
        """Metin temizle"""
        try:
            if not text:
                return ""
            
            # Boşlukları temizle ve None değerlerini kontrol et
            text = str(text).strip()
            
            if text.lower() in ['none', 'null', 'nan', 'undefined']:
                return ""
            
            return text
        except:
            return ""
    
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
    
    @staticmethod
    def create_download_link(df, filename, file_format="xlsx"):
        """DataFrame için download linki oluştur"""
        try:
            if file_format.lower() == "xlsx":
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Data')
                excel_data = output.getvalue()
                
                b64 = base64.b64encode(excel_data).decode()
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}.xlsx">📥 {filename}.xlsx İndir</a>'
                
            elif file_format.lower() == "csv":
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv">📥 {filename}.csv İndir</a>'
                
            else:
                return "Desteklenmeyen format"
            
            return href
        except Exception as e:
            return f"Download link oluşturma hatası: {str(e)}"
    
    @staticmethod
    def show_success_message(message):
        """Başarı mesajı göster"""
        st.success(f"✅ {message}")
    
    @staticmethod
    def show_error_message(message):
        """Hata mesajı göster"""
        st.error(f"❌ {message}")
    
    @staticmethod
    def show_warning_message(message):
        """Uyarı mesajı göster"""
        st.warning(f"⚠️ {message}")
    
    @staticmethod
    def show_info_message(message):
        """Bilgi mesajı göster"""
        st.info(f"ℹ️ {message}")
    
    @staticmethod
    def create_backup_filename(prefix="backup"):
        """Backup dosya adı oluştur"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{prefix}_{timestamp}"
    
    @staticmethod
    def is_valid_email(email):
        """E-posta adresini doğrula"""
        try:
            import re
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return re.match(pattern, str(email)) is not None
        except:
            return False
    
    @staticmethod
    def is_valid_phone(phone):
        """Telefon numarasını doğrula"""
        try:
            import re
            # Türkiye telefon numarası formatı
            phone_str = str(phone).strip()
            # 90 ile başlayan veya 0 ile başlayan formatlar
            pattern = r'^(90|0)?[1-9][0-9]{9}$'
            return re.match(pattern, phone_str.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')) is not None
        except:
            return False
    
    @staticmethod
    def mask_sensitive_info(text, mask_char="*", visible_chars=4):
        """Hassas bilgiyi maskele"""
        try:
            if not text:
                return ""
            
            text = str(text)
            if len(text) <= visible_chars * 2:
                return mask_char * len(text)
            
            start = text[:visible_chars]
            end = text[-visible_chars:]
            middle = mask_char * (len(text) - visible_chars * 2)
            
            return start + middle + end
        except:
            return mask_char * 8
    
    @staticmethod
    def get_risk_level(days_without_deposit):
        """Risk seviyesi hesapla"""
        try:
            days = Utils.safe_int(days_without_deposit, 999)
            
            if days <= 7:
                return {"level": "Düşük", "color": "green", "score": 1}
            elif days <= 30:
                return {"level": "Orta", "color": "orange", "score": 2}
            elif days <= 90:
                return {"level": "Yüksek", "color": "red", "score": 3}
            else:
                return {"level": "Çok Yüksek", "color": "darkred", "score": 4}
        except:
            return {"level": "Bilinmiyor", "color": "gray", "score": 0}
    
    @staticmethod
    def calculate_member_score(member):
        """Üye puanı hesapla"""
        try:
            score = 0
            
            # Bakiye puanı (0-25 puan)
            balance = Utils.safe_float(member.get('balance', 0))
            if balance > 1000:
                score += 25
            elif balance > 100:
                score += 15
            elif balance > 10:
                score += 5
            
            # Yatırım aktivitesi (0-35 puan)
            days_without_deposit = Utils.safe_int(member.get('days_without_deposit', 999))
            if days_without_deposit <= 7:
                score += 35
            elif days_without_deposit <= 30:
                score += 25
            elif days_without_deposit <= 90:
                score += 15
            elif days_without_deposit <= 180:
                score += 5
            
            # Toplam yatırım (0-25 puan)
            total_deposits = Utils.safe_float(member.get('total_deposits', 0))
            if total_deposits > 10000:
                score += 25
            elif total_deposits > 5000:
                score += 20
            elif total_deposits > 1000:
                score += 15
            elif total_deposits > 100:
                score += 10
            elif total_deposits > 0:
                score += 5
            
            # Son giriş (0-15 puan)
            last_login = member.get('last_login_date')
            if last_login:
                days_since_login = Utils.calculate_days_difference(last_login)
                if days_since_login <= 1:
                    score += 15
                elif days_since_login <= 7:
                    score += 10
                elif days_since_login <= 30:
                    score += 5
            
            return min(score, 100)  # Maksimum 100 puan
            
        except:
            return 0
    
    @staticmethod
    def get_member_category(member):
        """Üye kategorisi belirle"""
        try:
            score = Utils.calculate_member_score(member)
            
            if score >= 80:
                return {"category": "VIP", "color": "gold", "priority": 1}
            elif score >= 60:
                return {"category": "Aktif", "color": "green", "priority": 2}
            elif score >= 40:
                return {"category": "Orta", "color": "orange", "priority": 3}
            elif score >= 20:
                return {"category": "Pasif", "color": "red", "priority": 4}
            else:
                return {"category": "Risk", "color": "darkred", "priority": 5}
                
        except:
            return {"category": "Bilinmiyor", "color": "gray", "priority": 6}
    
    @staticmethod
    def export_data_as_json(data, filename=None):
        """Veriyi JSON olarak export et"""
        try:
            if not filename:
                filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
            
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="{filename}">📥 {filename} İndir</a>'
            
            return href
        except Exception as e:
            return f"JSON export hatası: {str(e)}"
    
    @staticmethod
    def validate_date_range(start_date, end_date):
        """Tarih aralığını doğrula"""
        try:
            if start_date > end_date:
                return False, "Başlangıç tarihi bitiş tarihinden sonra olamaz"
            
            if (end_date - start_date).days > 365:
                return False, "Tarih aralığı 365 günden fazla olamaz"
            
            return True, "Tarih aralığı geçerli"
        except Exception as e:
            return False, f"Tarih doğrulama hatası: {str(e)}"
    
    @staticmethod
    def create_summary_card(title, value, change=None, color="blue"):
        """Özet kart HTML'i oluştur"""
        try:
            card_html = f"""
            <div style="
                background-color: white;
                padding: 15px;
                border-radius: 10px;
                border-left: 4px solid {color};
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin: 10px 0;
            ">
                <h4 style="margin: 0 0 5px 0; color: #333;">{title}</h4>
                <h2 style="margin: 0; color: {color};">{value}</h2>
            """
            
            if change is not None:
                change_color = "green" if change >= 0 else "red"
                change_icon = "↗" if change >= 0 else "↘"
                card_html += f"""
                <p style="margin: 5px 0 0 0; color: {change_color}; font-size: 14px;">
                    {change_icon} {change:+.1f}%
                </p>
                """
            
            card_html += "</div>"
            return card_html
        except:
            return f"<div>Kart oluşturma hatası: {title}</div>"
    
    @staticmethod
    def log_activity(activity_type, description, user_id=None):
        """Aktivite logla"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": activity_type,
                "description": description,
                "user_id": user_id or "system"
            }
            
            log_file = "activity_log.json"
            
            # Mevcut logları yükle
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # Yeni log ekle
            logs.append(log_entry)
            
            # Son 1000 kaydı tut
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # Logları kaydet
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            return True
        except:
            return False
    
    @staticmethod
    def get_system_health():
        """Sistem sağlığını kontrol et"""
        try:
            health = {
                "status": "healthy",
                "checks": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Dosya varlık kontrolü
            required_files = ["daily_data.json", "members.json", "token.json"]
            for file in required_files:
                if os.path.exists(file):
                    health["checks"].append({"file": file, "status": "exists"})
                else:
                    health["checks"].append({"file": file, "status": "missing"})
                    health["status"] = "warning"
            
            # Disk kullanımı kontrolü (basit)
            try:
                import shutil
                total, used, free = shutil.disk_usage(".")
                disk_usage = (used / total) * 100
                
                health["checks"].append({
                    "check": "disk_usage",
                    "value": f"{disk_usage:.1f}%",
                    "status": "ok" if disk_usage < 90 else "warning"
                })
                
                if disk_usage >= 90:
                    health["status"] = "warning"
                    
            except:
                pass
            
            return health
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

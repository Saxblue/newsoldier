import os
import json
import streamlit as st
import requests
from datetime import datetime
import base64

class GitHubManager:
    """GitHub entegrasyonu için sınıf"""
    
    def __init__(self):
        self.token = None
        self.repo_owner = None
        self.repo_name = os.getenv("GITHUB_REPO", "btag-affiliate-system")
        self.data_files = ["daily_data.json", "members.json", "token.json"]
        self.sync_history_file = "sync_history.json"
        self.base_url = "https://api.github.com"
    
    def set_token(self, token):
        """GitHub token'ını ayarla"""
        try:
            if not token:
                return False
            
            self.token = token
            
            # Token'ı test et
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(f"{self.base_url}/user", headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                self.repo_owner = user_data.get('login')
                
                # Session state'e kaydet
                st.session_state.github_token = token
                
                # Repository'yi kontrol et
                success = self.check_repository()
                return success
            elif response.status_code == 401:
                st.error("❌ GitHub token geçersiz! Lütfen token'ınızı kontrol edin.")
                return False
            elif response.status_code == 403:
                st.error("❌ GitHub API rate limit aşıldı veya yetki yetersiz.")
                return False
            else:
                st.error(f"❌ GitHub API hatası ({response.status_code}): {response.text}")
                return False
            
        except Exception as e:
            st.error(f"❌ GitHub token hatası: {str(e)}")
            return False
    
    def set_repo(self, repo_name):
        """Repository'yi ayarla"""
        self.repo_name = repo_name
        return self.check_repository()
    
    def check_repository(self):
        """Repository'yi kontrol et"""
        try:
            if not self.token or not self.repo_name:
                return False
            
            # Eğer repo_name sadece repo adıysa, mevcut kullanıcının repo'su olarak varsay
            if '/' not in self.repo_name:
                full_repo_name = f"{self.repo_owner}/{self.repo_name}"
            else:
                full_repo_name = self.repo_name
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(f"{self.base_url}/repos/{full_repo_name}", headers=headers)
            
            if response.status_code == 200:
                self.repo_name = full_repo_name
                return True
            elif response.status_code == 404:
                # Repository bulunamadı, oluşturmayı dene
                return self.create_repository()
            else:
                st.warning(f"Repository erişim hatası ({response.status_code}): {response.text}")
                return False
                
        except Exception as e:
            st.warning(f"Repository erişim hatası: {str(e)}")
            return False
    
    def create_repository(self):
        """Repository oluştur"""
        try:
            if not self.token:
                return False
            
            # Repository adını al
            repo_name = self.repo_name.split('/')[-1] if '/' in self.repo_name else self.repo_name
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            data = {
                "name": repo_name,
                "description": "BTag Affiliate Takip Sistemi - Otomatik oluşturuldu",
                "private": False,
                "auto_init": True
            }
            
            response = requests.post(f"{self.base_url}/user/repos", headers=headers, json=data)
            
            if response.status_code == 201:
                repo_data = response.json()
                self.repo_name = repo_data.get('full_name')
                st.success(f"✅ Repository oluşturuldu: {self.repo_name}")
                return True
            else:
                error_data = response.json() if response.content else {}
                st.error(f"❌ Repository oluşturma hatası ({response.status_code}): {error_data.get('message', 'Bilinmeyen hata')}")
                return False
            
        except Exception as e:
            st.error(f"❌ Repository oluşturma hatası: {str(e)}")
            return False
    
    def is_connected(self):
        """GitHub bağlantı durumunu kontrol et"""
        return self.token is not None and self.repo_name is not None
    
    def test_connection(self):
        """GitHub bağlantısını test et"""
        try:
            if not self.is_connected():
                return False
            
            # Basit bir test işlemi - repo bilgilerini al
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(f"{self.base_url}/repos/{self.repo_name}", headers=headers)
            return response.status_code == 200
            
        except Exception as e:
            st.error(f"❌ GitHub bağlantı testi başarısız: {str(e)}")
            return False
    
    def get_repo_name(self):
        """Repository adını getir"""
        return self.repo_name
    
    def sync_file(self, file_path, commit_message=None):
        """Tek dosyayı GitHub'a sync et"""
        try:
            if not self.is_connected():
                st.warning("⚠️ GitHub bağlantısı yok, dosya sync edilemedi")
                return False
            
            if not os.path.exists(file_path):
                st.warning(f"⚠️ Dosya bulunamadı: {file_path}")
                return False
            
            # Dosya içeriğini oku
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Commit mesajı oluştur
            if not commit_message:
                commit_message = f"Update {file_path} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Önce dosyanın var olup olmadığını kontrol et
            check_response = requests.get(f"{self.base_url}/repos/{self.repo_name}/contents/{file_path}", headers=headers)
            
            # Content'i base64 encode et
            content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            data = {
                "message": commit_message,
                "content": content_encoded
            }
            
            if check_response.status_code == 200:
                # Dosya var, güncelle
                file_data = check_response.json()
                data["sha"] = file_data["sha"]
                
            # Dosyayı gönder
            response = requests.put(f"{self.base_url}/repos/{self.repo_name}/contents/{file_path}", 
                                  headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                if check_response.status_code == 200:
                    st.success(f"✅ Dosya güncellendi: {file_path}")
                else:
                    st.success(f"✅ Yeni dosya oluşturuldu: {file_path}")
                
                # Sync geçmişini kaydet
                self.log_sync_action(file_path, "upload", commit_message)
                return True
            else:
                error_data = response.json() if response.content else {}
                st.error(f"❌ Dosya sync hatası ({file_path}): {error_data.get('message', response.text)}")
                return False
            
        except Exception as e:
            st.error(f"❌ Dosya sync hatası ({file_path}): {str(e)}")
            return False
    
    def sync_data_files(self):
        """Tüm veri dosyalarını sync et"""
        try:
            if not self.is_connected():
                st.error("❌ GitHub bağlantısı yok!")
                return False
            
            success_count = 0
            
            for file_path in self.data_files:
                if os.path.exists(file_path):
                    if self.sync_file(file_path):
                        success_count += 1
            
            if success_count > 0:
                st.success(f"✅ {success_count} dosya başarıyla sync edildi!")
                return True
            else:
                st.warning("⚠️ Sync edilecek dosya bulunamadı")
                return False
            
        except Exception as e:
            st.error(f"❌ Veri dosyaları sync hatası: {str(e)}")
            return False
    
    def sync_all_files(self):
        """Tüm dosyaları sync et"""
        try:
            if not self.is_connected():
                st.error("❌ GitHub bağlantısı yok!")
                return False
            
            success_count = 0
            total_files = 0
            
            # Veri dosyalarını sync et
            for file_path in self.data_files:
                if os.path.exists(file_path):
                    total_files += 1
                    if self.sync_file(file_path):
                        success_count += 1
            
            # Diğer önemli dosyaları da sync et
            other_files = ["app.py", "github_manager.py", "token_manager.py", "data_processor.py", "member_manager.py", "visualization.py", "utils.py"]
            for file_path in other_files:
                if os.path.exists(file_path):
                    total_files += 1
                    if self.sync_file(file_path):
                        success_count += 1
            
            if total_files > 0:
                success_percentage = (success_count / total_files) * 100
                st.success(f"✅ {success_count}/{total_files} dosya başarıyla sync edildi! (%{success_percentage:.1f})")
                return success_count > 0
            else:
                st.warning("⚠️ Sync edilecek dosya bulunamadı")
                return False
            
        except Exception as e:
            st.error(f"❌ Tüm dosyalar sync hatası: {str(e)}")
            return False
    
    def pull_file(self, file_path):
        """GitHub'dan tek dosya çek"""
        try:
            if not self.is_connected():
                return False
            
            # Dosyayı GitHub'dan al
            file_content = self.repo.get_contents(file_path)
            content = base64.b64decode(file_content.content).decode('utf-8')
            
            # Yerel dosyaya yaz
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Sync geçmişini kaydet
            self.log_sync_action(file_path, "download", f"Pulled from GitHub")
            st.success(f"✅ Dosya çekildi: {file_path}")
            return True
            
        except GithubException as e:
            if e.status == 404:
                st.warning(f"⚠️ Dosya GitHub'da bulunamadı: {file_path}")
            else:
                st.error(f"❌ Dosya çekme hatası ({file_path}, {e.status}): {e.data.get('message', 'Bilinmeyen hata')}")
            return False
        except Exception as e:
            st.error(f"❌ Dosya çekme hatası ({file_path}): {str(e)}")
            return False
    
    def pull_data_files(self):
        """Tüm veri dosyalarını GitHub'dan çek"""
        try:
            if not self.is_connected():
                return False
            
            success_count = 0
            
            for file_path in self.data_files:
                if self.pull_file(file_path):
                    success_count += 1
            
            if success_count > 0:
                st.success(f"✅ {success_count} dosya GitHub'dan çekildi!")
                return True
            else:
                st.warning("⚠️ GitHub'dan çekilecek dosya bulunamadı")
                return False
            
        except Exception as e:
            st.error(f"❌ Veri dosyaları çekme hatası: {str(e)}")
            return False
    
    def get_pending_changes_count(self):
        """Bekleyen değişiklik sayısını getir"""
        try:
            if not self.is_connected():
                return 0
            
            pending_count = 0
            
            for file_path in self.data_files:
                if os.path.exists(file_path):
                    # Dosya boyutuna bakarak değişiklik olup olmadığını kontrol et
                    local_size = os.path.getsize(file_path)
                    
                    try:
                        github_file = self.repo.get_contents(file_path)
                        github_size = github_file.size
                        
                        if local_size != github_size:
                            pending_count += 1
                    except GithubException as e:
                        if e.status == 404:
                            # Dosya GitHub'da yoksa bekleyen değişiklik say
                            pending_count += 1
            
            return pending_count
            
        except Exception as e:
            return 0
    
    def log_sync_action(self, file_path, action, message):
        """Sync işlemini logla"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "file": file_path,
                "action": action,
                "message": message,
                "status": "success"
            }
            
            # Sync geçmişini yükle
            history = self.load_sync_history()
            history.append(log_entry)
            
            # Son 100 kaydı tut
            if len(history) > 100:
                history = history[-100:]
            
            # Geçmişi kaydet
            self.save_sync_history(history)
            
        except Exception as e:
            st.warning(f"⚠️ Sync log hatası: {str(e)}")
    
    def load_sync_history(self):
        """Sync geçmişini yükle"""
        try:
            if os.path.exists(self.sync_history_file):
                with open(self.sync_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except:
            return []
    
    def save_sync_history(self, history):
        """Sync geçmişini kaydet"""
        try:
            with open(self.sync_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.warning(f"⚠️ Sync geçmişi kaydetme hatası: {str(e)}")
    
    def get_sync_history(self):
        """Sync geçmişini getir"""
        return self.load_sync_history()
    
    def create_backup(self, backup_name=None):
        """Veri dosyalarının backup'ını oluştur"""
        try:
            if not self.is_connected():
                return False
            
            if not backup_name:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_data = {}
            
            # Tüm veri dosyalarını backup'a ekle
            for file_path in self.data_files:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        backup_data[file_path] = f.read()
            
            # Backup'ı GitHub'a yükle
            backup_content = json.dumps(backup_data, ensure_ascii=False, indent=2)
            backup_file_path = f"backups/{backup_name}.json"
            
            commit_message = f"Backup created: {backup_name}"
            
            try:
                # Backup dosyası varsa güncelle
                file_content = self.repo.get_contents(backup_file_path)
                self.repo.update_file(
                    backup_file_path,
                    commit_message,
                    backup_content,
                    file_content.sha
                )
            except GithubException as e:
                if e.status == 404:
                    # Backup dosyası yoksa oluştur
                    self.repo.create_file(
                        backup_file_path,
                        commit_message,
                        backup_content
                    )
                else:
                    raise e
            
            st.success(f"✅ Backup oluşturuldu: {backup_name}")
            return True
            
        except Exception as e:
            st.error(f"❌ Backup oluşturma hatası: {str(e)}")
            return False
    
    def restore_backup(self, backup_name):
        """Backup'tan veri dosyalarını geri yükle"""
        try:
            if not self.is_connected():
                return False
            
            backup_file_path = f"backups/{backup_name}.json"
            
            # Backup dosyasını GitHub'dan al
            file_content = self.repo.get_contents(backup_file_path)
            backup_content = base64.b64decode(file_content.content).decode('utf-8')
            backup_data = json.loads(backup_content)
            
            # Backup'tan dosyaları geri yükle
            for file_path, file_content in backup_data.items():
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
            
            st.success(f"✅ Backup geri yüklendi: {backup_name}")
            return True
            
        except Exception as e:
            st.error(f"❌ Backup geri yükleme hatası: {str(e)}")
            return False
    
    def list_backups(self):
        """Mevcut backup'ları listele"""
        try:
            if not self.is_connected():
                return []
            
            backups = []
            
            try:
                contents = self.repo.get_contents("backups")
                if isinstance(contents, list):
                    for content in contents:
                        if content.name.endswith('.json'):
                            backup_name = content.name.replace('.json', '')
                            backups.append({
                                'name': backup_name,
                                'size': content.size,
                                'last_modified': str(content.last_modified) if hasattr(content, 'last_modified') else 'N/A'
                            })
                else:
                    # Tek dosya döndü
                    if contents.name.endswith('.json'):
                        backup_name = contents.name.replace('.json', '')
                        backups.append({
                            'name': backup_name,
                            'size': contents.size,
                            'last_modified': str(contents.last_modified) if hasattr(contents, 'last_modified') else 'N/A'
                        })
            except GithubException as e:
                if e.status == 404:
                    # backups klasörü yok, boş liste döndür
                    pass
                else:
                    st.warning(f"⚠️ Backup listeleme hatası: {e.data.get('message', 'Bilinmeyen hata')}")
            
            return backups
            
        except Exception as e:
            st.error(f"❌ Backup listeleme hatası: {str(e)}")
            return []
    
    def get_repo_stats(self):
        """Repository istatistiklerini getir"""
        try:
            if not self.is_connected():
                return None
            
            stats = {
                'name': self.repo.name,
                'full_name': self.repo.full_name,
                'description': self.repo.description or "Açıklama yok",
                'size': self.repo.size,
                'language': self.repo.language or "Belirtilmemiş",
                'created_at': self.repo.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': self.repo.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                'private': self.repo.private,
                'default_branch': self.repo.default_branch
            }
            
            # Commit sayısını almayı dene (rate limit nedeniyle başarısız olabilir)
            try:
                stats['commits_count'] = self.repo.get_commits().totalCount
            except:
                stats['commits_count'] = "N/A"
            
            return stats
            
        except Exception as e:
            st.error(f"❌ Repository istatistikleri hatası: {str(e)}")
            return None
    
    def get_file_list(self, path=""):
        """Repository'deki dosyaları listele"""
        try:
            if not self.is_connected():
                return []
            
            contents = self.repo.get_contents(path)
            files = []
            
            if isinstance(contents, list):
                for content in contents:
                    files.append({
                        'name': content.name,
                        'path': content.path,
                        'type': content.type,
                        'size': content.size
                    })
            else:
                files.append({
                    'name': contents.name,
                    'path': contents.path,
                    'type': contents.type,
                    'size': contents.size
                })
            
            return files
            
        except Exception as e:
            st.error(f"❌ Dosya listesi hatası: {str(e)}")
            return []

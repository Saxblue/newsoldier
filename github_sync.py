import os
import json
import base64
from datetime import datetime
import streamlit as st

# GitHub kütüphanesini opsiyonel olarak import et
try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    # Import sırasında uyarı gösterme - sadece kullanım sırasında göster

class GitHubSync:
    """GitHub ile otomatik senkronizasyon sınıfı"""
    
    def __init__(self):
        self.token = "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"
        self.repo_name = "Saxblue/newsoldier"
        self.branch = "main"
        
        if not GITHUB_AVAILABLE:
            # PyGithub kütüphanesi mevcut değil - sessizce devre dışı bırak
            self.sync_enabled = False
            return
        
        try:
            self.github = Github(self.token)
            self.repo = self.github.get_repo(self.repo_name)
            self.sync_enabled = True
        except Exception as e:
            # GitHub bağlantı hatası - sessizce devre dışı bırak
            self.sync_enabled = False
    
    def upload_file(self, file_path, content, commit_message=None):
        """Dosyayı GitHub'a yükle veya güncelle"""
        if not self.sync_enabled:
            return False
            
        try:
            if commit_message is None:
                commit_message = f"Auto-update {file_path} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Dosya içeriğini base64'e çevir
            if isinstance(content, str):
                content_bytes = content.encode('utf-8')
            else:
                content_bytes = content
            
            try:
                # Dosya varsa güncelle
                file = self.repo.get_contents(file_path, ref=self.branch)
                self.repo.update_file(
                    path=file_path,
                    message=commit_message,
                    content=content_bytes,
                    sha=file.sha,
                    branch=self.branch
                )
                return True
            except:
                # Dosya yoksa oluştur
                self.repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=content_bytes,
                    branch=self.branch
                )
                return True
                
        except Exception as e:
            st.error(f"GitHub yükleme hatası: {str(e)}")
            return False
    
    def sync_json_file(self, local_file_path, github_file_path=None):
        """JSON dosyasını GitHub'a senkronize et"""
        if github_file_path is None:
            github_file_path = os.path.basename(local_file_path)
        
        try:
            with open(local_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            success = self.upload_file(
                github_file_path, 
                content, 
                f"Update {github_file_path} data"
            )
            
            if success:
                st.success(f"✅ {github_file_path} GitHub'a yüklendi!")
                return True
            else:
                st.error(f"❌ {github_file_path} yüklenemedi!")
                return False
                
        except Exception as e:
            st.error(f"Dosya okuma hatası: {str(e)}")
            return False
    
    def sync_python_file(self, local_file_path, github_file_path=None):
        """Python dosyasını GitHub'a senkronize et"""
        if github_file_path is None:
            github_file_path = os.path.basename(local_file_path)
        
        try:
            with open(local_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            success = self.upload_file(
                github_file_path, 
                content, 
                f"Update {github_file_path} application code"
            )
            
            if success:
                st.success(f"✅ {github_file_path} GitHub'a yüklendi!")
                return True
            else:
                st.error(f"❌ {github_file_path} yüklenemedi!")
                return False
                
        except Exception as e:
            st.error(f"Dosya okuma hatası: {str(e)}")
            return False
    
    def sync_all_files(self):
        """Tüm dosyaları GitHub'a senkronize et"""
        files_to_sync = [
            ("btag.py", "btag_affiliate_system.py", "python"),
            ("daily_data.json", "daily_data.json", "json"),
            ("members.json", "members.json", "json"),
            ("token.json", "token.json", "json")
        ]
        
        success_count = 0
        total_files = len(files_to_sync)
        
        with st.spinner("GitHub'a senkronize ediliyor..."):
            for local_file, github_file, file_type in files_to_sync:
                if os.path.exists(local_file):
                    if file_type == "python":
                        if self.sync_python_file(local_file, github_file):
                            success_count += 1
                    else:
                        if self.sync_json_file(local_file, github_file):
                            success_count += 1
                else:
                    st.warning(f"⚠️ {local_file} dosyası bulunamadı!")
        
        if success_count == total_files:
            st.balloons()
            st.success(f"🎉 Tüm dosyalar ({success_count}/{total_files}) başarıyla GitHub'a yüklendi!")
        else:
            st.warning(f"⚠️ {success_count}/{total_files} dosya yüklendi.")
        
        return success_count == total_files
    
    def get_repo_info(self):
        """Repository bilgilerini getir"""
        if not self.sync_enabled:
            return None
            
        try:
            return {
                "name": self.repo.name,
                "full_name": self.repo.full_name,
                "url": self.repo.html_url,
                "last_push": self.repo.pushed_at.strftime('%Y-%m-%d %H:%M:%S') if self.repo.pushed_at else "Bilinmiyor",
                "commits": self.repo.get_commits().totalCount
            }
        except Exception as e:
            st.error(f"Repository bilgisi alınamadı: {str(e)}")
            return None

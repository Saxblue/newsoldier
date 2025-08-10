import json
import os
import streamlit as st
from datetime import datetime

class TokenManager:
    """Token yönetimi için sınıf"""
    
    def __init__(self):
        self.token_file = "token.json"
        self.ensure_token_file()
    
    def ensure_token_file(self):
        """Token dosyasının varlığını kontrol et"""
        if not os.path.exists(self.token_file):
            # Kullanıcının verdiği güncel token'ları kullan
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
                    tokens['github_token'] = os.getenv("GITHUB_TOKEN", "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")
                
                if 'api_url' not in tokens:
                    tokens['api_url'] = "https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientWithdrawalRequestsWithTotals"
                
                # Eğer token'lar boşsa, kullanıcının verdiği değerleri kullan
                if not tokens.get('api_token'):
                    tokens['api_token'] = "8d7974f38c6fae4e66f41dcf6805e648a9fa59c6682788e7fe61a4c8ea5e21e3"
                
                if not tokens.get('github_token'):
                    tokens['github_token'] = "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"
                
                return tokens
        except Exception as e:
            st.error(f"Token dosyası okuma hatası: {e}")
            # Hata durumunda varsayılan token'ları döndür
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
        api_token = tokens.get('api_token', '')
        
        # Environment variable'dan da kontrol et
        if not api_token:
            api_token = os.getenv("API_TOKEN", "8d7974f38c6fae4e66f41dcf6805e648a9fa59c6682788e7fe61a4c8ea5e21e3")
        
        return api_token
    
    def get_github_token(self):
        """GitHub token'ını getir"""
        tokens = self.load_tokens()
        github_token = tokens.get('github_token', '')
        
        # Environment variable'dan da kontrol et
        if not github_token:
            github_token = os.getenv("GITHUB_TOKEN", "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")
        
        # Session state'den de kontrol et
        if not github_token and hasattr(st.session_state, 'github_token'):
            github_token = st.session_state.github_token
        
        return github_token
    
    def get_api_url(self):
        """API URL'ini getir"""
        tokens = self.load_tokens()
        return tokens.get('api_url', 'https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientWithdrawalRequestsWithTotals')
    
    def save_api_token(self, api_token, api_url=None):
        """API token'ını kaydet"""
        try:
            tokens = self.load_tokens()
            tokens['api_token'] = api_token
            
            if api_url:
                tokens['api_url'] = api_url
            
            # Environment variable olarak da ayarla
            os.environ["API_TOKEN"] = api_token
            
            return self.save_tokens(tokens)
        except Exception as e:
            st.error(f"API token kaydetme hatası: {e}")
            return False
    
    def save_github_token(self, github_token):
        """GitHub token'ını kaydet"""
        try:
            tokens = self.load_tokens()
            tokens['github_token'] = github_token
            
            # Session state'e de kaydet
            st.session_state.github_token = github_token
            
            # Environment variable olarak da ayarla
            os.environ["GITHUB_TOKEN"] = github_token
            
            return self.save_tokens(tokens)
        except Exception as e:
            st.error(f"GitHub token kaydetme hatası: {e}")
            return False
    
    def validate_api_token(self, token):
        """API token'ını doğrula"""
        if not token:
            return False
        
        # Token formatını kontrol et (hex string olmalı)
        try:
            int(token, 16)  # Hex string kontrolü
            return len(token) >= 32  # Minimum token uzunluğu
        except ValueError:
            return False
    
    def validate_github_token(self, token):
        """GitHub token'ını doğrula"""
        if not token:
            return False
        
        # GitHub PAT format kontrolü
        if token.startswith('github_pat_'):
            return len(token) > 20
        elif token.startswith('ghp_'):
            return len(token) == 40
        else:
            # Eski format token'lar için uzunluk kontrolü
            return len(token) >= 20
    
    def get_token_info(self):
        """Token bilgilerini getir"""
        tokens = self.load_tokens()
        
        api_token = tokens.get('api_token', '')
        github_token = tokens.get('github_token', '')
        
        info = {
            'api_token_valid': self.validate_api_token(api_token),
            'github_token_valid': self.validate_github_token(github_token),
            'api_token_length': len(api_token) if api_token else 0,
            'github_token_length': len(github_token) if github_token else 0,
            'api_url': tokens.get('api_url', ''),
            'created_at': tokens.get('created_at', ''),
            'updated_at': tokens.get('updated_at', ''),
            'api_token_masked': self.mask_token(api_token),
            'github_token_masked': self.mask_token(github_token)
        }
        
        return info
    
    def mask_token(self, token):
        """Token'ı maskele"""
        if not token:
            return ""
        
        if len(token) > 8:
            return token[:4] + '*' * (len(token) - 8) + token[-4:]
        else:
            return '*' * len(token)
    
    def reset_tokens(self):
        """Token'ları sıfırla"""
        try:
            default_tokens = {
                "api_token": "",
                "github_token": "",
                "api_url": "https://backofficewebadmin.betconstruct.com/api/tr/Client/GetClientWithdrawalRequestsWithTotals",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            return self.save_tokens(default_tokens)
        except Exception as e:
            st.error(f"Token sıfırlama hatası: {e}")
            return False
    
    def export_tokens(self):
        """Token'ları export et (güvenlik için maskelenmiş)"""
        tokens = self.load_tokens()
        
        # Güvenlik için token'ları maskele
        masked_tokens = {}
        for key, value in tokens.items():
            if 'token' in key.lower() and value:
                masked_tokens[key] = self.mask_token(value)
            else:
                masked_tokens[key] = value
        
        return masked_tokens
    
    def import_tokens(self, token_data):
        """Token'ları import et"""
        try:
            current_tokens = self.load_tokens()
            
            # Sadece geçerli anahtarları güncelle
            valid_keys = ['api_token', 'github_token', 'api_url']
            
            for key in valid_keys:
                if key in token_data and token_data[key]:
                    current_tokens[key] = token_data[key]
            
            return self.save_tokens(current_tokens)
        except Exception as e:
            st.error(f"Token import hatası: {e}")
            return False
    
    def test_tokens(self):
        """Token'ları test et"""
        results = {
            'api_token': False,
            'github_token': False
        }
        
        # API token test
        api_token = self.get_api_token()
        if api_token:
            results['api_token'] = self.validate_api_token(api_token)
        
        # GitHub token test
        github_token = self.get_github_token()
        if github_token:
            results['github_token'] = self.validate_github_token(github_token)
        
        return results
    
    def refresh_tokens(self):
        """Token'ları yeniden yükle"""
        try:
            # Dosyadan yeniden yükle
            tokens = self.load_tokens()
            
            # Environment variable'lara set et
            if tokens.get('api_token'):
                os.environ["API_TOKEN"] = tokens['api_token']
            
            if tokens.get('github_token'):
                os.environ["GITHUB_TOKEN"] = tokens['github_token']
                st.session_state.github_token = tokens['github_token']
            
            return True
        except Exception as e:
            st.error(f"Token yenileme hatası: {e}")
            return False

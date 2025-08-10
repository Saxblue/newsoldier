# token_manager.py
"""
TokenManager: Token'ı alıp doğrulama işlerini yapar.
- Öncelik: Streamlit st.secrets["GITHUB_TOKEN"]
- Sonraki: ENV GITHUB_TOKEN
- Eğer çağıran özel token verirse onu kullanır.
Kullanım: from token_manager import TokenManager
token = TokenManager.get_github_token()
"""
import os
try:
    import streamlit as st
    _HAS_STREAMLIT = True
except Exception:
    _HAS_STREAMLIT = False

class TokenManager:
    @staticmethod
    def get_github_token(fallback: str = None) -> str:
        """
        Öncelikle st.secrets, sonra ENV, sonra fallback.
        """
        token = None
        if _HAS_STREAMLIT:
            try:
                token = st.secrets.get("GITHUB_TOKEN")
            except Exception:
                token = None

        if not token:
            token = os.getenv("GITHUB_TOKEN")

        if not token:
            token = fallback

        if token:
            return token.strip()
        raise RuntimeError("GitHub token bulunamadı. Lütfen st.secrets veya GITHUB_TOKEN env değişkenine ekleyin.")

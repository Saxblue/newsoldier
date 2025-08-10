# github_manager.py
"""
GitHubManager
- Repo'dan dosya okuma
- Repo'ya dosya güncelleme / oluşturma
- Basit bağlantı testi
NOT: Token güvenliği için token'ı doğrudan bu dosyaya koyma. Token'ı
TokenManager/streamlit st.secrets veya ENV üzerinden geçir.
"""
import base64
import json
import requests
from typing import Optional

class GitHubManager:
    def __init__(self, owner: str, repo: str, token: Optional[str] = None, branch: str = "main"):
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.api_base = "https://api.github.com"
        self.token = None
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            self.set_token(token)

    def set_token(self, token: str):
        if not token:
            raise ValueError("Token boş olamaz.")
        self.token = token.strip()
        self.headers["Authorization"] = f"token {self.token}"
        return True

    def _repo_path(self, path: str) -> str:
        # path örn: "daily_data.json"
        return f"{self.api_base}/repos/{self.owner}/{self.repo}/contents/{path}"

    def is_connected(self) -> bool:
        """Basit bağlantı testi: repo bilgilerini almayı dener."""
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}"
        r = requests.get(url, headers=self.headers)
        return r.status_code == 200

    def get_file(self, path: str) -> dict:
        """
        Dosya bilgilerini ve içerik (base64) döner.
        Hata olursa requests.HTTPError fırlatır.
        """
        url = self._repo_path(path)
        params = {"ref": self.branch}
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        return r.json()

    def get_json(self, path: str) -> dict:
        """
        path'teki JSON dosyasının içeriğini parse edip döner.
        Eğer dosya bulunamazsa FileNotFoundError fırlatır.
        """
        try:
            resp = self.get_file(path)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise FileNotFoundError(f"Dosya bulunamadı: {path}")
            raise

        # GitHub content alanı base64 encoded
        content_b64 = resp.get("content", "")
        if not content_b64:
            # boş dosya
            return {}
        payload = base64.b64decode(content_b64.encode()).decode("utf-8")
        # parse JSON
        try:
            return json.loads(payload)
        except Exception:
            # JSON parse edilemiyorsa ham string dönebiliriz
            raise ValueError("Dosya JSON parse edilemedi.")

    def update_json(self, path: str, data: dict, commit_message: str = "Update via API") -> dict:
        """
        path'teki dosyayı günceller veya yoksa oluşturur.
        Dönen değer GitHub API response JSON'udur.
        """
        url = self._repo_path(path)

        # önce mevcut sha'yı al
        sha = None
        try:
            current = self.get_file(path)
            sha = current.get("sha")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                sha = None
            else:
                raise

        content_str = json.dumps(data, ensure_ascii=False, indent=2)
        content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

        payload = {
            "message": commit_message,
            "content": content_b64,
            "branch": self.branch
        }
        if sha:
            payload["sha"] = sha

        r = requests.put(url, headers=self.headers, json=payload)
        # Eğer 401 => token/permission problemi
        if r.status_code == 401:
            raise PermissionError("GitHub: Bad credentials (401). Token yanlış ya da izin yetersiz.")
        r.raise_for_status()
        return r.json()

    def create_file_if_not_exists(self, path: str, data: dict, commit_message: str = "Create file via API"):
        """
        Dosya yoksa oluşturur. Varsa hiçbir şey yapmaz.
        """
        try:
            self.get_file(path)
            return {"status": "exists"}
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return self.update_json(path, data, commit_message=commit_message)
            else:
                raise

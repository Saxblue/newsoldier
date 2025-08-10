# member_manager.py
"""
MemberManager: members.json ile çalışmak için yardımcı fonksiyonlar.
- GitHub üzerinden okuma/yazma
- Local fallback: uygulama çalışırken local cache tutar (isteğe bağlı)
"""
import json
from typing import List, Dict
from data_processor import DataProcessor

class MemberManager:
    def __init__(self, github_manager, file_path: str = "members.json"):
        self.gh = github_manager
        self.file_path = file_path
        self._cache = None

    def load(self) -> List[Dict]:
        try:
            data = self.gh.get_json(self.file_path)
            if isinstance(data, list):
                self._cache = data
                return data
            # bazen dict olabilir -> convert
            if isinstance(data, dict):
                # varsayılan olarak dict -> [] dönüşümü
                self._cache = list(data.values())
                return self._cache
            self._cache = []
            return []
        except FileNotFoundError:
            # dosya yok -> döngüsel boş liste
            self._cache = []
            return []
        except Exception as e:
            raise

    def save(self, members_list: List[Dict], commit_message: str = "Update members"):
        # members_list JSON serileştirilebilir olmalı
        # GitHubManager.update_json kullan
        data = members_list
        return self.gh.update_json(self.file_path, data, commit_message=commit_message)

    def add_member(self, member: Dict):
        if not DataProcessor.validate_member(member):
            raise ValueError("Member objesi geçersiz: en az 'id' ve 'name' olmalı.")
        members = self.load()
        # uniqueness by id
        existing_ids = {m.get("id") for m in members if isinstance(m, dict)}
        if member.get("id") in existing_ids:
            # güncelle
            members = [member if (isinstance(m, dict) and m.get("id")==member.get("id")) else m for m in members]
        else:
            members.append(member)
        return self.save(members, commit_message=f"Add/update member {member.get('id')}")

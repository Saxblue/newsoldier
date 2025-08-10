# data_processor.py
"""
DataProcessor: JSON veri işleme yardımcıları.
- günlük veri ekleme
- basit validate
- timestamp anahtar kullanımı
"""
from datetime import datetime
from typing import Dict, Any

class DataProcessor:
    @staticmethod
    def add_daily_entry(existing: dict, date_key: str, entry: dict) -> dict:
        """
        existing: mevcut daily_data dict (örn: {"2025-08-09": {...}})
        date_key: "YYYY-MM-DD"
        entry: eklenecek dict
        Dönen: güncellenmiş dict
        """
        if not isinstance(existing, dict):
            existing = {}

        # Eğer aynı güne yeni veri varsa, güncelle/merge et (basit)
        if date_key in existing and isinstance(existing[date_key], dict):
            # Basit merge: aynı alanları overwrite eder
            merged = existing[date_key].copy()
            merged.update(entry)
            existing[date_key] = merged
        else:
            existing[date_key] = entry
        return existing

    @staticmethod
    def today_key() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d")

    @staticmethod
    def validate_member(member: Dict[str, Any]) -> bool:
        # Basit validasyon örneği
        if not isinstance(member, dict):
            return False
        if "id" not in member or "name" not in member:
            return False
        return True

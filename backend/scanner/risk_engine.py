"""Risk scoring helpers used by the file scanner."""

from __future__ import annotations


class RiskEngine:
    """Encapsulates the project's file risk heuristics."""

    suspicious_extensions = (".exe", ".bat", ".ps1", ".vbs", ".scr")

    @classmethod
    def is_suspicious_extension(cls, filename: str) -> bool:
        return filename.lower().endswith(cls.suspicious_extensions)

    @staticmethod
    def is_autorun(filename: str) -> bool:
        return filename.lower() == "autorun.inf"

    @staticmethod
    def is_hidden(filename: str) -> bool:
        return filename.startswith(".")

    @staticmethod
    def is_double_extension(filename: str) -> bool:
        return filename.lower().count(".") >= 2

    @staticmethod
    def threat_level(risk_score: int) -> str:
        if risk_score >= 10:
            return "HIGH"
        if risk_score >= 5:
            return "MEDIUM"
        if risk_score > 0:
            return "LOW"
        return "CLEAN"
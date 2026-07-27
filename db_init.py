from config.settings import AppSettings
from backend.database.connection import SQLiteConnectionFactory
from backend.database.malware_repository import MalwareHashRepository


DB_NAME = AppSettings().database_path


def ensure_database(db_path=None):
    """Create and seed the malware hash database if it does not exist."""
    database_path = db_path or DB_NAME
    repository = MalwareHashRepository(SQLiteConnectionFactory(database_path))
    repository.seed()
    return database_path


if __name__ == "__main__":
    path = ensure_database()
    print(f"[+] Database ready: {path}")

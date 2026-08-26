import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
    DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
    
    @classmethod
    def validate_config(cls):
        missing = []
        if not cls.DHAN_CLIENT_ID:
            missing.append("DHAN_CLIENT_ID")
        if not cls.DHAN_ACCESS_TOKEN:
            missing.append("DHAN_ACCESS_TOKEN")
        if missing:
            raise ValueError(f"❌ Missing variables: {', '.join(missing)}. Configure them in Streamlit secrets panel or local .env file.")

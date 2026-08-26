import requests
from config import Config

class DhanService:
    def __init__(self):
        Config.validate_config()
        self.base_url = "https://api.dhan.co/v2"
        self.headers = {
            "access-token": Config.DHAN_ACCESS_TOKEN,
            "client-id": Config.DHAN_CLIENT_ID,
            "Content-Type": "application/json"
        }
    
    def get_ltp(self, security_id, exchange_segment):
        # Dedicated structure wrapper to pass raw token payloads safely
        pass

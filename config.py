import os
from dotenv import load_dotenv

# Load workspace environment variables
load_dotenv()

class Config:
    """Validates and holds application level configurations."""
    DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
    DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
    
    @classmethod
    def validate_config(cls):
        """Ensures application does not boot with critical empty attributes."""
        missing = []
        if not cls.DHAN_CLIENT_ID:
            missing.append("DHAN_CLIENT_ID")
        if not cls.DHAN_ACCESS_TOKEN:
            missing.append("DHAN_ACCESS_TOKEN")
            
        if missing:
            raise ValueError(
                f"❌ Critical environment variables missing: {', '.join(missing)}. "
                f"Please ensure your localized .env file matches .env.example configuration layout."
            )

# Execute verification layer on run entry point
if __name__ == "__main__":
    try:
        Config.validate_config()
        print("✅ Environment properties verified successfully.")
    except ValueError as e:
        print(e)

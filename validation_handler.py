import hmac, hashlib
from dotenv import load_dotenv
import os

# === Load environment variables from .env file ===
load_dotenv('.env')
# WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET').encode('utf-8')
FLASK_API_KEY = os.getenv('FLASK_API_KEY')

class ValidationHandler:

    @staticmethod
    def is_authorized(req):
        """Validate the incoming request's API key."""
        return req.headers.get("X-API-KEY") == FLASK_API_KEY

    # @staticmethod
    # def is_signature_valid(req):
    #     received_sig = req.headers.get("X-Freshservice-Signature", "")
    #     raw_body = req.get_data()  # raw bytes of request body
    #     expected_sig = hmac.new(WEBHOOK_SECRET, raw_body, hashlib.sha256).hexdigest()
    #     return hmac.compare_digest(received_sig, expected_sig)
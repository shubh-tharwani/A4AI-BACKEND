import firebase_admin
from firebase_admin import credentials, auth
import os

cred_path = os.getenv("FIREBASE_CREDENTIALS", "firebase_key.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

def verify_token(token: str):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        return None

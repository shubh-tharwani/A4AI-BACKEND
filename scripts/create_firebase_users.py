import firebase_admin
from firebase_admin import credentials, auth

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)

# Test: Create a test user
user = auth.create_user(email="test@googlea4ai.com", password="123456")
print(user.uid)

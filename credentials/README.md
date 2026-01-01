# Credentials Directory

This directory contains service account credentials and API keys required for the platform to function.

## Required Files

Place the following credential files in this directory:

1. **vertex_ai_key.json**
   - Google Cloud service account key with Vertex AI permissions
   - Required permissions: `aiplatform.endpoints.predict`, `aiplatform.models.predict`

2. **firebase_key.json**
   - Firebase Admin SDK service account key
   - Used for user authentication and management

3. **firestore_key.json**
   - Firestore service account key
   - Required for database operations

## Security Notice

⚠️ **IMPORTANT: Never commit credential files to version control**

- All `.json` files in this directory are automatically ignored by `.gitignore`
- Keep credentials secure and rotate them regularly
- Use different credentials for development and production
- Ensure appropriate IAM permissions are set for each service account

## Getting Credentials

### Google Cloud Console
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to "IAM & Admin" > "Service Accounts"
3. Create or select a service account
4. Click "Keys" > "Add Key" > "Create New Key"
5. Choose JSON format and download

### Firebase Console
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project
3. Go to Project Settings > Service Accounts
4. Click "Generate New Private Key"
5. Save the downloaded JSON file

## Environment Configuration

After placing credentials here, update your `.env` file:

```env
GOOGLE_APPLICATION_CREDENTIALS=credentials/vertex_ai_key.json
FIREBASE_CONFIG=credentials/firebase_key.json
FIRESTORE_CONFIG=credentials/firestore_key.json
```

## Permissions Checklist

Ensure your service accounts have these permissions:

### Vertex AI Service Account
- Vertex AI User
- AI Platform Developer

### Firebase Service Account
- Firebase Admin
- Firebase Authentication Admin

### Firestore Service Account
- Cloud Datastore User
- Cloud Datastore Owner (for admin operations)

For more information, refer to the main README.md setup guide.

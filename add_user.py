"""
One-time script to grant the service account Viewer access to the GA4 property.
Uses the v1alpha Admin API which supports accessBindings (current method).
Run: python add_user.py
"""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
PROPERTY_ID = "537257415"
SERVICE_ACCOUNT_EMAIL = "portfolio-analytics@eminent-clover-496200-i1.iam.gserviceaccount.com"
SCOPES = ["https://www.googleapis.com/auth/analytics.manage.users"]

def main():
    print(f"Loading credentials from: {CREDENTIALS_PATH}")

    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH, scopes=SCOPES
    )

    service = build("analyticsadmin", "v1alpha", credentials=creds)

    body = {
        "roles": ["predefinedRoles/viewer"],
        "user": f"user:{SERVICE_ACCOUNT_EMAIL}",
    }

    print(f"Attempting to add {SERVICE_ACCOUNT_EMAIL} to properties/{PROPERTY_ID}...")

    try:
        result = service.properties().accessBindings().create(
            parent=f"properties/{PROPERTY_ID}",
            body=body
        ).execute()
        print(f"\nSUCCESS!")
        print(f"  Created: {result.get('name')}")
        print(f"  User:    {result.get('user')}")
        print(f"  Roles:   {result.get('roles')}")
        print("\nGo to http://localhost:8000/ -- live data will appear on next refresh!")
    except Exception as e:
        err = str(e)
        if "403" in err:
            print("\nPERMISSION DENIED.")
            print("The service account cannot grant itself access - this must be done")
            print("by furiousdante3@gmail.com (the property owner).")
            print("\nMANUAL STEPS:")
            print("1. Go to https://analytics.google.com/")
            print("2. Click Admin (bottom left gear icon)")
            print("3. Under Property, click 'Property Access Management'")
            print(f"4. Click the blue + button > Add users")
            print(f"5. Paste this email: {SERVICE_ACCOUNT_EMAIL}")
            print("6. Select role: Viewer")
            print("7. Click Add")
        elif "404" in err:
            print(f"\nProperty {PROPERTY_ID} not found. Check your GA4 Property ID.")
        else:
            print(f"\nError: {err}")

if __name__ == "__main__":
    main()

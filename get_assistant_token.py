"""Generate Google Assistant OAuth token.

Opens your browser for Google sign-in.
"""

import json
import os

CREDS_FILE = "credentials.json"
TOKEN_FILE = os.path.expanduser("~/.nico/assistant_token.json")
SCOPE = "https://www.googleapis.com/auth/assistant-sdk-prototype"

from google_auth_oauthlib.flow import InstalledAppFlow

os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)

flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, [SCOPE])
creds = flow.run_local_server(port=0, open_browser=True)

with open(TOKEN_FILE, "w") as f:
    f.write(creds.to_json())

print(f"Token saved to {TOKEN_FILE}")
print(f"Access token (first 50 chars): {creds.token[:50]}...")

"""
One-time OneDrive OAuth authentication.
Run this once before using SOURCE_TYPE=onedrive.

Usage:
  python scripts/onedrive_auth.py
"""
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config

TOKEN_CACHE_FILE = config.TOKEN_CACHE_PATH

try:
    import msal
except ImportError:
    print("Run: pip install msal")
    sys.exit(1)

if not config.ONEDRIVE_CLIENT_ID:
    print("ERROR: Set ONEDRIVE_CLIENT_ID in your .env file first.")
    sys.exit(1)

cache = msal.SerializableTokenCache()
app = msal.PublicClientApplication(
    config.ONEDRIVE_CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{config.ONEDRIVE_TENANT_ID}",
    token_cache=cache,
)

flow = app.initiate_device_flow(scopes=['Files.Read'])
print(flow['message'])
webbrowser.open(flow['verification_uri'])

result = app.acquire_token_by_device_flow(flow)
if 'access_token' in result:
    open(TOKEN_CACHE_FILE, 'w').write(cache.serialize())
    print("\nAuthenticated successfully. Token cached.")
else:
    print(f"\nAuthentication failed: {result.get('error_description')}")
    sys.exit(1)

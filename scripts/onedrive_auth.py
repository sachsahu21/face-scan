"""
One-time OneDrive OAuth authentication.
Run this once before using source.type=onedrive.

Usage:
  python scripts/onedrive_auth.py
"""
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config

try:
    import msal
except ImportError:
    print("Run: pip install msal")
    sys.exit(1)

if not config.ONEDRIVE_CLIENT_ID:
    print("ERROR: onedrive.client_id not set in config/config.yaml (or ONEDRIVE_CLIENT_ID in .env)")
    sys.exit(1)

cache = msal.SerializableTokenCache()
app = msal.PublicClientApplication(
    config.ONEDRIVE_CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{config.ONEDRIVE_TENANT_ID}",
    token_cache=cache,
)

flow = app.initiate_device_flow(scopes=['Files.ReadWrite'])
print(flow['message'])
webbrowser.open(flow['verification_uri'])

result = app.acquire_token_by_device_flow(flow)
if 'access_token' in result:
    cache_path = Path(config.TOKEN_CACHE_PATH)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(cache.serialize())
    print(f"\nAuthenticated. Token cached → {cache_path}")
else:
    print(f"\nAuthentication failed: {result.get('error_description')}")
    sys.exit(1)

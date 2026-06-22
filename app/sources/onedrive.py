"""
OneDrive photo source via Microsoft Graph API.

Setup (one-time):
  1. Register an app at portal.azure.com → Azure AD → App registrations
  2. Add redirect URI: http://localhost:8080
  3. Add API permission: Microsoft Graph → Files.Read (delegated)
  4. Copy Client ID and Tenant ID into .env
  5. Run: python scripts/onedrive_auth.py   (authenticates once, caches token)
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path
from typing import List

from .base import PhotoSource

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import config as _config

TOKEN_CACHE_FILE = _config.TOKEN_CACHE_PATH
GRAPH_BASE = 'https://graph.microsoft.com/v1.0'


class OneDrivePhotoSource(PhotoSource):
    def __init__(self, client_id: str, tenant_id: str, folder: str):
        if not client_id:
            raise ValueError("ONEDRIVE_CLIENT_ID not set in .env")

        self.folder = folder
        self._token = None

        try:
            import msal
        except ImportError:
            raise ImportError("Run: pip install msal requests")

        self._init_auth(client_id, tenant_id)

    def _init_auth(self, client_id: str, tenant_id: str):
        import msal

        cache = msal.SerializableTokenCache()
        if os.path.exists(TOKEN_CACHE_FILE):
            cache.deserialize(open(TOKEN_CACHE_FILE).read())

        self._app = msal.PublicClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            token_cache=cache,
        )

        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(['Files.Read'], account=accounts[0])
            if result and 'access_token' in result:
                self._token = result['access_token']
                self._save_cache(cache)
                return

        raise RuntimeError(
            "OneDrive not authenticated. Run: python scripts/onedrive_auth.py"
        )

    def _save_cache(self, cache):
        if cache.has_state_changed:
            open(TOKEN_CACHE_FILE, 'w').write(cache.serialize())

    def _headers(self):
        return {'Authorization': f'Bearer {self._token}'}

    def list_images(self) -> List[str]:
        import requests

        url = f"{GRAPH_BASE}/me/drive/root:{self.folder}:/children"
        params = {'$top': 1000, '$select': 'id,name,file'}
        items = []

        while url:
            r = requests.get(url, headers=self._headers(), params=params)
            r.raise_for_status()
            data = r.json()
            for item in data.get('value', []):
                mime = item.get('file', {}).get('mimeType', '')
                if mime.startswith('image/'):
                    items.append(item['id'])
            url = data.get('@odata.nextLink')
            params = None

        return items

    def read_image(self, image_id: str) -> np.ndarray:
        import requests

        r = requests.get(
            f"{GRAPH_BASE}/me/drive/items/{image_id}/content",
            headers=self._headers(),
        )
        r.raise_for_status()
        arr = np.frombuffer(r.content, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)

    def get_display_url(self, image_id: str) -> str:
        import requests

        r = requests.get(
            f"{GRAPH_BASE}/me/drive/items/{image_id}/thumbnails/0/large",
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()['url']

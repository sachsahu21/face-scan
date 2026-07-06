"""
OneDrive photo source via Microsoft Graph API.

Setup (one-time):
  1. Register an app at portal.azure.com → Azure AD → App registrations
  2. Add API permission: Microsoft Graph → Files.Read (delegated)
  3. Set client_id in config/config.yaml or ONEDRIVE_CLIENT_ID in .env
  4. Run: python scripts/onedrive_auth.py
"""
import os
import cv2
import numpy as np
from pathlib import Path
from typing import List

from app.sources.base import PhotoSource

GRAPH_BASE = 'https://graph.microsoft.com/v1.0'


class OneDrivePhotoSource(PhotoSource):
    def __init__(self, client_id: str, tenant_id: str, folder: str, token_cache_path: Path):
        if not client_id:
            raise ValueError(
                "OneDrive client_id not set.\n"
                "Add it to config/config.yaml → source.onedrive.client_id\n"
                "or set ONEDRIVE_CLIENT_ID in .env"
            )
        self.folder = folder
        self.token_cache_path = Path(token_cache_path)
        self._token = None

        try:
            import msal
        except ImportError:
            raise ImportError("Run: pip install msal requests")

        self._init_auth(client_id, tenant_id)

    def _init_auth(self, client_id: str, tenant_id: str):
        import msal

        cache = msal.SerializableTokenCache()

        # Load token: file on disk (local) → env var (cloud/HF Spaces)
        if self.token_cache_path.exists():
            cache.deserialize(self.token_cache_path.read_text())
        elif os.getenv('ONEDRIVE_TOKEN_CACHE'):
            cache.deserialize(os.getenv('ONEDRIVE_TOKEN_CACHE'))

        self._app = msal.PublicClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            token_cache=cache,
        )

        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(['Files.ReadWrite'], account=accounts[0])
            if result and 'access_token' in result:
                self._token = result['access_token']
                self._save_cache(cache)
                return

        raise RuntimeError(
            "OneDrive not authenticated.\n"
            "Local:  python scripts/onedrive_auth.py\n"
            "Cloud:  set ONEDRIVE_TOKEN_CACHE secret in HF Space settings"
        )

    def _save_cache(self, cache):
        if cache.has_state_changed:
            self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_cache_path.write_text(cache.serialize())

    def _headers(self):
        return {'Authorization': f'Bearer {self._token}'}

    def list_images(self) -> List[str]:
        """Recursively list all image item IDs under self.folder."""
        import requests

        items = []
        folders_to_scan = [f"{GRAPH_BASE}/me/drive/root:{self.folder}:/children"]

        while folders_to_scan:
            url = folders_to_scan.pop()
            params = {'$top': 1000, '$select': 'id,name,file,folder'}

            while url:
                r = requests.get(url, headers=self._headers(), params=params, timeout=60)
                r.raise_for_status()
                data = r.json()
                for item in data.get('value', []):
                    if item.get('file', {}).get('mimeType', '').startswith('image/'):
                        items.append(item['id'])
                    elif 'folder' in item:
                        # queue subfolder for scanning
                        folders_to_scan.append(
                            f"{GRAPH_BASE}/me/drive/items/{item['id']}/children"
                        )
                url = data.get('@odata.nextLink')
                params = None

        return items

    def read_image(self, image_id: str) -> np.ndarray:
        import requests

        r = requests.get(
            f"{GRAPH_BASE}/me/drive/items/{image_id}/content",
            headers=self._headers(),
            timeout=30,
        )
        r.raise_for_status()
        return cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_COLOR)

    def get_display_url(self, image_id: str) -> str:
        import requests

        r = requests.get(
            f"{GRAPH_BASE}/me/drive/items/{image_id}/thumbnails/0/large",
            headers=self._headers(),
            timeout=15,
        )
        r.raise_for_status()
        return r.json()['url']

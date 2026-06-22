from dotenv import load_dotenv
import os

load_dotenv()

# 'local' or 'onedrive'
SOURCE_TYPE = os.getenv('SOURCE_TYPE', 'local')

# Local source
LOCAL_PHOTOS_DIR = os.getenv('LOCAL_PHOTOS_DIR', './photos')

# OneDrive source (set these when switching to OneDrive)
ONEDRIVE_CLIENT_ID = os.getenv('ONEDRIVE_CLIENT_ID', '')
ONEDRIVE_TENANT_ID = os.getenv('ONEDRIVE_TENANT_ID', 'common')
ONEDRIVE_FOLDER   = os.getenv('ONEDRIVE_FOLDER', '/Pictures')

# Index
INDEX_PATH       = os.getenv('INDEX_PATH', './data/face_index.npz')
SEARCH_THRESHOLD = float(os.getenv('SEARCH_THRESHOLD', '0.35'))
MAX_RESULTS      = int(os.getenv('MAX_RESULTS', '20'))

# Tunnel — set TUNNEL_MODE=true to expose via ngrok (outside WiFi)
TUNNEL_MODE = os.getenv('TUNNEL_MODE', 'false').lower() == 'true'

# Server
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8000'))

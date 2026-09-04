import os
import psycopg2
from psycopg2.extras
import RealDictCursor
import datetime
import random
import sys
import time
from io import BytesIO
from html import escape

# PIL (Pillow) exception handling for Render deployment stability
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from flask import Flask, request, redirect, url_for, session, render_template_string, send_from_directory, jsonify, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "imana_free_interest_microfinance_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

NOTIFICATIONS = []

# --- NEON.TECH / POSTGRESQL DATABASE CONNECTION ---
# Never keep a database password in source code. Configure DATABASE_URL as a
# deployment secret/environment variable instead.
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()

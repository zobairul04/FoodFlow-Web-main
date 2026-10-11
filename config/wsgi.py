"""
WSGI config for FoodFlow project.
Exposes the WSGI callable as a module-level variable named ``application`` and ``app`` (for Vercel).
"""

import os
import shutil
import tempfile
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# In Vercel serverless environment, ensure SQLite db is accessible in writable temp if not using DATABASE_URL
if ('VERCEL' in os.environ or os.environ.get('VERCEL_ENV')) and not os.environ.get('DATABASE_URL'):
    tmp_dir = tempfile.gettempdir()
    tmp_db = os.path.join(tmp_dir, 'db.sqlite3')
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_db = os.path.join(base_dir, 'db.sqlite3')
    if os.path.exists(source_db) and not os.path.exists(tmp_db):
        try:
            shutil.copyfile(source_db, tmp_db)
        except Exception:
            pass

application = get_wsgi_application()

# Vercel serverless entrypoint
app = application

# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for POS Native Desktop Application
# Windowed mode (no console), pywebview embedded desktop window.
#
# Build:
#   pyinstaller POS.spec
#
# Output: dist\POS\POS.exe

import sys
import os
from pathlib import Path

_SPEC_DIR = Path(os.path.dirname(os.path.abspath(sys.argv[0]))) if sys.argv and os.path.isfile(sys.argv[0]) else Path.cwd()

BLOCK_CALLBACK = None

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.lan")

_FIDO2_DIR = None
try:
    import fido2
    _FIDO2_DIR = os.path.dirname(fido2.__file__)
except ImportError:
    pass

a = Analysis(
    ['main.py'],
    pathex=[str(_SPEC_DIR / "megaone")],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('megaone', 'megaone'),
        ('megaone/media', 'megaone/media'),
        ('menu', 'menu'),
        ('orders', 'orders'),
        ('locale', 'locale'),
        ('deployment\\config', 'deployment\\config'),
        ('deployment\\logs', 'deployment\\logs'),
        ('manage.py', '.'),
        ('requirements.txt', '.'),
        ('icon.ico', '.'),
        ('staticfiles', 'staticfiles'),
        ('menu/migrations', 'menu/migrations'),
        ('orders/migrations', 'orders/migrations'),
        ('megaone/users/migrations', 'megaone/users/migrations'),
        ('megaone/apps', 'apps'),
    ] + (
        [(_FIDO2_DIR + '\\public_suffix_list.dat', 'fido2')] if _FIDO2_DIR else []
    ),
    hiddenimports=[
        # Django core
        'django',
        'django.contrib.auth',
        'django.contrib.auth.hashers',
        'django.contrib.auth.password_validation',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django.contrib.admin',
        'django.contrib.admindocs',
        'django.contrib.humanize',
        'django.contrib.sites',
        'django.contrib.sitemaps',
        'django.forms',
        'django.forms.renderers',
        'django.core.cache.backends.locmem',
        'django.core.cache.backends.filebased',
        'django.core.cache.backends.db',
        'django.contrib.sessions.backends.db',
        'django.contrib.sessions.backends.cache',
        'django.core.management',
        'django.core.management.commands.runserver',
        'django.core.management.commands.migrate',
        'django.templatetags.static',
        'django.template.defaultfilters',
        'django.template.loaders.app_directories',
        'django.template.loaders.filesystem',
        'django.template.context_processors',
        'django.db.backends.mysql',
        'django.db.backends.mysql.base',
        'django.db.backends.mysql.client',
        'django.db.backends.mysql.creation',
        'django.db.backends.mysql.features',
        'django.db.backends.mysql.introspection',
        'django.db.backends.mysql.operations',
        'django.db.backends.mysql.schema',
        'django.db.backends.mysql.validation',

        # MySQL client
        'MySQLdb',
        'MySQLdb.connections',
        'MySQLdb.converters',
        'MySQLdb.cursors',
        'MySQLdb.times',
        'MySQLdb._exceptions',
        'MySQLdb.constants',
        'MySQLdb.constants.FIELD_TYPE',

        # WSGI server
        'whitenoise',
        'whitenoise.middleware',
        'waitress',

        # Django apps
        'config',
        'config.urls',
        'config.wsgi',
        'config.settings',
        'config.settings.base',
        'config.settings.lan',
        'megaone',
        'megaone.users',
        'megaone.users.apps',
        'megaone.users.models',
        'megaone.users.views',
        'megaone.users.urls',
        'megaone.users.forms',
        'megaone.users.admin',
        'megaone.users.managers',
        'megaone.users.signals',
        'megaone.users.loyalty_utils',
        'megaone.users.backup_utils',
        'megaone.users.context_processors',
        'megaone.users.adapters',
        'megaone.users.middleware',
        'megaone.users.permissions',
        'megaone.users.inventory_service',
        'megaone.users.templatetags',
        'megaone.users.templatetags.user_extras',
        'menu',
        'menu.apps',
        'menu.models',
        'menu.signals',
        'orders',
        'orders.apps',
        'orders.models',
        'apps',
        'apps.food_delivery',
        'apps.food_delivery.apps',
        'apps.food_delivery.views',
        'apps.food_delivery.urls',
        'apps.food_delivery.admin',

        # Third-party
        'allauth',
        'allauth.account',
        'allauth.socialaccount',
        'allauth.mfa',
        'crispy_forms',
        'crispy_bootstrap5',
        'environ',
        'PIL',
        'PIL.ImageFont',
        'PIL.ImageDraw',
        'PIL.ImageFilter',
        'argon2',
        'sqlite3',

        # Reportlab - PDF generation
        'reportlab',
        'reportlab.lib.units',
        'reportlab.lib.colors',
        'reportlab.lib.utils',
        'reportlab.pdfgen',
        'reportlab.pdfgen.canvas',

        # QR code
        'qrcode',
        'qrcode.constants',

        # Networking / HTTP
        'chardet',
        'charset_normalizer',
        'certifi',
        'idna',
        'urllib3',
        'requests',

        # Redis / caching
        'redis',
        'hiredis',

        # Utility
        'faker',
        'fido2',
        'cryptography',
        'pyphen',
        'babel',

        # pywebview
        'webview',
        'bottle',
        'pythonnet',
        'proxy_tools',
        'clr_loader',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'test',
        'pytest',
        'gunicorn',
        'Collectfasta',
        'storages',
        'anymail',
        'sphinx',
        'ruff',
        'djlint',
        'pre_commit',
        'coverage',
        'ipdb',
        'mypy',
        'django_stubs',
        'django_extensions',
        'debug_toolbar',
        'werkzeug',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='POS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='POS',
)

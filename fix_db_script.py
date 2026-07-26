import os
import sys
from pathlib import Path

# Same setup as manage.py
current_path = Path(__file__).parent.resolve()
sys.path.append(str(current_path / "megaone"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
os.environ["DJANGO_READ_DOT_ENV_FILE"] = "False"

import django
django.setup()

from django.db import connection
from django.utils import timezone
c = connection.cursor()
now = timezone.now()

# Create django_site table if not exists
c.execute("""
    CREATE TABLE IF NOT EXISTS django_site (
        id int NOT NULL AUTO_INCREMENT,
        domain varchar(100) NOT NULL,
        name varchar(50) NOT NULL,
        PRIMARY KEY (id),
        UNIQUE KEY django_site_domain_a2e37b91_uniq (domain)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")

# Insert default site
c.execute("INSERT IGNORE INTO django_site (id, domain, name) VALUES (1, 'example.com', 'example.com')")

# Remove old custom sites migration records
c.execute("DELETE FROM django_migrations WHERE app = 'sites'")

# Insert proper sites migration records
for name in ['0001_initial', '0002_alter_domain_unique', '0003_set_site_domain_and_name']:
    c.execute("INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)", ('sites', name, now))

# Delete mfa records (app removed) and our app records
c.execute("DELETE FROM django_migrations WHERE app = 'mfa'")
c.execute("DELETE FROM django_migrations WHERE app IN ('menu', 'orders', 'users')")

print('Database fixed.')
print('Now run: python manage.py migrate --fake-initial')

from django.db import connection

def is_migration_running():
    """Check if migrations are currently being applied."""
    if connection.settings_dict['NAME'] == ':memory:':
        return True
    try:
        return 'migrate' in connection.introspection.table_names()[-1]
    except Exception:
        return False

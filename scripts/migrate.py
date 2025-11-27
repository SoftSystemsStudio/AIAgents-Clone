"""Helper script to run Alembic migrations programmatically.

Usage:
    python scripts/migrate.py upgrade
    python scripts/migrate.py downgrade -1
"""
import sys
from alembic.config import Config
from alembic import command
import os

HERE = os.path.dirname(os.path.dirname(__file__))
ALEMBIC_INI = os.path.join(HERE, 'alembic.ini')

def main(argv):
    if len(argv) < 2:
        print('Usage: migrate.py <upgrade|downgrade> [target]')
        return 1

    action = argv[1]
    target = argv[2] if len(argv) > 2 else 'head'

    cfg = Config(ALEMBIC_INI)
    # Alembic env.py will read settings to set the URL

    if action == 'upgrade':
        command.upgrade(cfg, target)
    elif action == 'downgrade':
        command.downgrade(cfg, target)
    else:
        print('Unknown action:', action)
        return 2

    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))

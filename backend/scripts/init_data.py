#!/usr/bin/env python3
"""
Initialize database with default data.
Usage: python scripts/init_data.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.init_db import init_db


async def main():
    """Main function."""
    print("=" * 60)
    print("OpsManager Database Initialization")
    print("=" * 60)

    try:
        await init_db()
        print("\n" + "=" * 60)
        print("Initialization completed successfully!")
        print("=" * 60)
        print("\nDefault admin credentials:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\nPlease change the default password after first login!")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

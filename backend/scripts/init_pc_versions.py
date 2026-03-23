#!/usr/bin/env python3
"""
Initialize PC Client version in database.

This script is typically run during database migration or initial setup.
It checks if PC client versions exist, and if not, creates them from
frontend/public/pcinfo files.

Usage:
    python init_pc_versions.py
"""
import asyncio
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("SECRET_KEY", "dev-secret-key-for-init-only")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://opsmanager:opsmanager@192.168.23.36:15432/opsmanager")
os.environ.setdefault("ENVIRONMENT", "production")

from app.config import settings
from app.db.base_class import Base
from app.models.pc_client_version import PCClientVersion
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


def extract_version_from_filename(filename: str) -> str | None:
    """Extract version from filename like PC_5.0.0_modular.vbs"""
    match = re.search(r"PC[_\-]?(\d+\.\d+\.\d+)", filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def get_pcinfo_dir() -> Path:
    """Get the PC info directory path."""
    backend_dir = Path(__file__).parent.parent.parent
    return backend_dir / "frontend" / "public" / "pcinfo"


async def check_existing_versions(session) -> int:
    """Check how many PC client versions exist in database."""
    result = await session.execute(select(PCClientVersion))
    versions = result.scalars().all()
    return len(versions)


async def create_version_if_not_exists(session, version: str, is_active: bool = False) -> bool:
    """Create a PC client version if it doesn't exist."""
    result = await session.execute(
        select(PCClientVersion).where(PCClientVersion.version == version)
    )
    existing = result.scalar_one_or_none()

    if existing:
        print(f"  [SKIP] Version {version} already exists (id={existing.id})")
        return False

    new_version = PCClientVersion(
        version=version,
        release_notes=f"PC Client version {version}",
        is_active=is_active,
        download_url=f"/pcinfo/PC_{version}_modular.vbs"
    )
    session.add(new_version)
    await session.commit()
    print(f"  [CREATED] Version {version}")
    return True


async def init_versions():
    """Initialize PC client versions from frontend files."""
    engine = create_async_engine(settings.async_database_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with async_session() as session:
        existing_count = await check_existing_versions(session)
        print(f"Existing versions in database: {existing_count}")

        if existing_count > 0:
            print("Database already has PC client versions. Skipping initialization.")
            return

        pcinfo_dir = get_pcinfo_dir()
        print(f"PC Info directory: {pcinfo_dir}")

        if not pcinfo_dir.exists():
            print("PC info directory not found. Cannot initialize versions.")
            return

        versions = []
        for vbs_file in pcinfo_dir.glob("PC_*.vbs"):
            version = extract_version_from_filename(vbs_file.name)
            if version:
                versions.append(version)

        if not versions:
            print("No PC client versions found.")
            return

        versions.sort(key=lambda v: [int(x) for x in v.split(".")], reverse=True)

        print(f"Found {len(versions)} version(s): {versions}")

        for i, version in enumerate(versions):
            is_active = (i == 0)
            print(f"Processing version {version} (active={is_active})...")
            await create_version_if_not_exists(session, version, is_active)

        print("\nInitialization complete!")


async def main():
    print("=" * 50)
    print("PC Client Version Initialization")
    print("=" * 50)
    print()

    await init_versions()


if __name__ == "__main__":
    asyncio.run(main())

"""
PC Client version auto-sync on startup.

Automatically syncs PC client versions from frontend/public/pcinfo
to database on application startup.
"""

import re
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pc_client_version import PCClientVersion


def extract_version_from_filename(filename: str) -> str | None:
    """Extract version from filename like PC_5.0.0_modular.vbs"""
    match = re.search(r"PC[_\-]?(\d+\.\d+\.\d+)", filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def get_frontend_pcinfo_dir() -> Path:
    """Get the frontend PC info directory path."""
    backend_dir = Path(__file__).parent.parent.parent.parent
    frontend_pcinfo = backend_dir / "frontend" / "public" / "pcinfo"
    if frontend_pcinfo.exists():
        return frontend_pcinfo
    return None


async def sync_pc_versions_on_startup(db: AsyncSession) -> list[str]:
    """
    Sync PC client versions from frontend/public/pcinfo to database.

    This is called during application startup to ensure the database
    has the latest version information from the frontend files.

    Returns list of synced versions.
    """
    frontend_dir = get_frontend_pcinfo_dir()
    if not frontend_dir:
        return []

    versions = []
    for vbs_file in frontend_dir.glob("PC_*.vbs"):
        version = extract_version_from_filename(vbs_file.name)
        if version:
            versions.append(version)

    if not versions:
        return []

    versions.sort(key=lambda v: [int(x) for x in v.split(".")], reverse=True)

    synced = []
    for i, version in enumerate(versions):
        is_active = i == 0

        result = await db.execute(select(PCClientVersion).where(PCClientVersion.version == version))
        existing = result.scalar_one_or_none()

        if existing:
            if not existing.is_active and is_active:
                existing.is_active = True
                await db.commit()
                synced.append(version)
        else:
            new_version = PCClientVersion(
                version=version,
                release_notes=f"PC Client version {version}",
                is_active=is_active,
                download_url=f"/pcinfo/PC_{version}_modular.vbs",
            )
            db.add(new_version)
            await db.commit()
            synced.append(version)

    if versions and synced:
        await deactivate_old_versions(db, versions)

    return synced


async def deactivate_old_versions(db: AsyncSession, current_versions: list[str]):
    """Deactivate versions that are not in the current list."""
    if not current_versions:
        return

    await db.execute(
        update(PCClientVersion)
        .where(PCClientVersion.version.not_in(current_versions))
        .values(is_active=False)
    )
    await db.commit()

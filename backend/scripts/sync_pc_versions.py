#!/usr/bin/env python3
"""
Sync PC Client versions from frontend/public/pcinfo to database.

This script is run during CI/CD deployment to automatically
update the database with version information from the frontend files.

Usage:
    python sync_pc_versions.py [--dry-run]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx


def extract_version_from_filename(filename: str) -> str | None:
    """Extract version from filename like PC_5.0.0_modular.vbs"""
    match = re.search(r"PC[_\-]?(\d+\.\d+\.\d+)", filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def get_pcinfo_dir() -> Path:
    """Get the PC info directory path."""
    backend_dir = Path(__file__).parent.parent
    return backend_dir / "frontend" / "public" / "pcinfo"


def read_conf_json(pcinfo_dir: Path) -> dict | None:
    """Read Conf.json to get CustInfo."""
    conf_file = pcinfo_dir / "Conf.json"
    if conf_file.exists():
        with open(conf_file, encoding="utf-8") as f:
            return json.load(f)
    return None


def discover_versions(pcinfo_dir: Path) -> list[dict]:
    """Discover PC client versions from VBS files."""
    versions = []

    for vbs_file in pcinfo_dir.glob("PC_*.vbs"):
        version = extract_version_from_filename(vbs_file.name)
        if version:
            versions.append(
                {
                    "version": version,
                    "filename": vbs_file.name,
                    "path": str(vbs_file.relative_to(pcinfo_dir.parent.parent)),
                }
            )

    return sorted(versions, key=lambda x: x["version"], reverse=True)


def sync_version_to_api(
    version: str, api_base: str, api_token: str | None = None, dry_run: bool = False
) -> bool:
    """Sync a single version to the database via API."""
    url = f"{api_base}/api/v1/versions"

    headers = {"Content-Type": "application/json"}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    payload = {
        "version": version,
        "release_notes": f"PC Client version {version}",
        "is_active": True,
        "download_url": f"/pcinfo/PC_{version}_modular.vbs",
    }

    if dry_run:
        print(f"  [DRY-RUN] Would create version {version}")
        print(f"           Payload: {json.dumps(payload, indent=4)}")
        return True

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code == 201:
            print(f"  [OK] Created version {version}")
            return True
        elif response.status_code == 400 and "already exists" in response.text:
            print(f"  [SKIP] Version {version} already exists")
            return True
        else:
            print(f"  [ERROR] Failed to create version {version}: {response.status_code}")
            print(f"          Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  [ERROR] Exception: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Sync PC Client versions to database")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("API_BASE", "http://localhost:8000"),
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--api-token", default=os.environ.get("API_TOKEN"), help="API token for authentication"
    )
    parser.add_argument(
        "--activate-latest",
        action="store_true",
        help="Activate the latest version (deactivate older versions)",
    )

    args = parser.parse_args()

    pcinfo_dir = get_pcinfo_dir()

    if not pcinfo_dir.exists():
        print(f"Error: PC info directory not found: {pcinfo_dir}")
        sys.exit(1)

    print(f"PC Info directory: {pcinfo_dir}")
    print()

    versions = discover_versions(pcinfo_dir)

    if not versions:
        print("No PC client versions found in directory.")
        sys.exit(0)

    print(f"Found {len(versions)} version(s):")
    for v in versions:
        print(f"  - {v['version']} ({v['filename']})")
    print()

    if args.dry_run:
        print("[DRY-RUN MODE - No changes will be made]")
        print()

    success_count = 0
    for v in versions:
        print(f"Processing version {v['version']}...")
        if sync_version_to_api(v["version"], args.api_base, args.api_token, args.dry_run):
            success_count += 1

    print()
    print(f"Summary: {success_count}/{len(versions)} versions synced successfully.")

    if success_count == len(versions):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

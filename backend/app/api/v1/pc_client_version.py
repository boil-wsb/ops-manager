"""
PC Client version management API.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.config import settings
from app.core.logging import get_logger
from app.crud import crud_pc_client_version
from app.schemas.pc_client_version import (
    PCClientVersionCheckResponse,
    PCClientVersionCreate,
    PCClientVersionResponse,
    PCClientVersionUpdate,
)

router = APIRouter(prefix="/pc-client-version")
logger = get_logger(__name__)


@router.get("/version", response_model=PCClientVersionCheckResponse)
async def check_version(
    db: AsyncSession = Depends(deps.get_db),
) -> PCClientVersionCheckResponse:
    """
    Check for PC Client version updates.
    This endpoint is called by the VBS update script.
    Returns the latest active version information.
    """
    version = await crud_pc_client_version.get_active_version(db)
    if not version:
        return PCClientVersionCheckResponse(version="")

    return PCClientVersionCheckResponse(
        version=version.version,
        releaseNotes=version.release_notes,
        downloadUrl=version.download_url,
        files=[],
    )


@router.get("/download", name="download_pc_client")
async def download_personalized_pc_client(
    current_user: Annotated[dict, Depends(deps.get_current_user)],
):
    """
    Download personalized PC info collector package.
    Replaces CustInfo.id in Conf.json with current username.
    """
    import io
    import json
    import zipfile
    from pathlib import Path

    logger.info(f"Download endpoint called by user: {current_user.username}", extra={"action": "terminal.version", "username": current_user.username})

    pcinfo_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "frontend" / "public" / "pcinfo"
    )

    conf_path = pcinfo_dir / "Conf.json"
    logger.info(f"Looking for Conf.json at: {conf_path}", extra={"action": "terminal.version"})
    logger.info(f"Conf.json exists: {conf_path.exists()}", extra={"action": "terminal.version"})
    with open(conf_path, encoding="utf-8") as f:
        conf = json.load(f)

    username = current_user.username
    conf["CustInfo"]["id"] = username

    if "HttpReport" in conf and settings.pcinfo_pushgateway_url:
        conf["HttpReport"]["Endpoint"] = settings.pcinfo_pushgateway_url

    if "UpdateServer" in conf:
        if settings.pcinfo_update_server_host:
            conf["UpdateServer"]["Host"] = settings.pcinfo_update_server_host
        if settings.pcinfo_update_server_port:
            conf["UpdateServer"]["Port"] = str(settings.pcinfo_update_server_port)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in pcinfo_dir.iterdir():
            if file_path.is_file() and file_path.name != "Conf.json":
                zipf.write(file_path, file_path.name)

        conf_json = json.dumps(conf, ensure_ascii=False, indent=2)
        zipf.writestr("Conf.json", conf_json.encode("utf-8"))

    zip_buffer.seek(0)

    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=pcinfo_{username}.zip"},
    )


@router.get("/versions", response_model=list[PCClientVersionResponse])
async def list_versions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(deps.get_db),
) -> list[PCClientVersionResponse]:
    """
    List all PC Client versions with pagination.
    """
    versions = await crud_pc_client_version.get_all_versions(db, skip=skip, limit=limit)
    return versions


@router.post(
    "/versions",
    response_model=PCClientVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_version(
    version_in: PCClientVersionCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
) -> PCClientVersionResponse:
    """
    Create a new PC Client version.
    Requires authentication.
    """
    version = await crud_pc_client_version.create(db, obj_in=version_in)
    return version


@router.get("/versions/{version_id}", response_model=PCClientVersionResponse)
async def get_version(
    version_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
) -> PCClientVersionResponse:
    """
    Get a specific PC Client version by ID.
    Requires authentication.
    """
    version = await crud_pc_client_version.get(db, id=version_id)
    if not version:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.put("/versions/{version_id}", response_model=PCClientVersionResponse)
async def update_version(
    version_id: int,
    version_in: PCClientVersionUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
) -> PCClientVersionResponse:
    """
    Update a PC Client version.
    Requires authentication.
    """
    version = await crud_pc_client_version.get(db, id=version_id)
    if not version:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Version not found")
    version = await crud_pc_client_version.update(db, db_obj=version, obj_in=version_in)
    return version


@router.delete("/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_version(
    version_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Delete a PC Client version.
    Requires authentication.
    """
    version = await crud_pc_client_version.get(db, id=version_id)
    if not version:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Version not found")
    await crud_pc_client_version.remove(db, id=version_id)

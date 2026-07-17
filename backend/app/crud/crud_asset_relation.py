"""
Asset relation CRUD operations and topology data assembly.
"""

import ipaddress
from collections import defaultdict
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.crud.base import CRUDBase
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.asset_relation import AssetRelation, RelationType
from app.schemas.asset_relation import AssetRelationCreate

logger = get_logger(__name__)


def _get_ip_prefix(ip: str | None, segments: int = 3) -> str | None:
    """Return the first N segments of an IPv4 address for subnet grouping.

    Returns None for missing/invalid/non-IPv4 addresses.
    """
    if not ip:
        return None
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        # 可能是 host:port 形式，取冒号前
        host = ip.split(":")[0]
        try:
            addr = ipaddress.ip_address(host)
        except ValueError:
            return None
    if addr.version != 4:
        return None
    parts = str(addr).split(".")
    return ".".join(parts[:segments])


class CRUDAssetRelation(CRUDBase[AssetRelation, AssetRelationCreate, dict[str, Any]]):
    """Asset relation CRUD operations."""

    async def create_manual(
        self, db: AsyncSession, *, obj_in: AssetRelationCreate
    ) -> AssetRelation:
        """Create a manual relation between two assets.

        - Validates both assets exist.
        - Prevents self-relations.
        - Rejects duplicates (same source/target/type).
        - Forces auto_inferred=False for user-created relations.
        """
        if obj_in.source_asset_id == obj_in.target_asset_id:
            raise ValidationError(detail="不能创建资产自身的关联关系")

        # Validate existence
        source = await db.get(Asset, obj_in.source_asset_id)
        if not source:
            raise NotFoundError(detail=f"源资产 {obj_in.source_asset_id} 不存在")
        target = await db.get(Asset, obj_in.target_asset_id)
        if not target:
            raise NotFoundError(detail=f"目标资产 {obj_in.target_asset_id} 不存在")

        relation_type = RelationType(obj_in.relation_type)

        # Check duplicates (either direction for CONNECTED/CUSTOM semantics)
        existing = await db.execute(
            select(AssetRelation).where(
                and_(
                    AssetRelation.source_asset_id == obj_in.source_asset_id,
                    AssetRelation.target_asset_id == obj_in.target_asset_id,
                    AssetRelation.relation_type == relation_type,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(detail="该关联关系已存在")

        relation = AssetRelation(
            source_asset_id=obj_in.source_asset_id,
            target_asset_id=obj_in.target_asset_id,
            relation_type=relation_type,
            auto_inferred=False,
        )
        db.add(relation)
        await db.commit()
        await db.refresh(relation)
        return relation

    async def delete_manual(self, db: AsyncSession, *, edge_id: int) -> bool:
        """Delete a manual relation by id. Auto-inferred relations cannot be deleted."""
        relation = await db.get(AssetRelation, edge_id)
        if not relation:
            raise NotFoundError(detail=f"关联关系 {edge_id} 不存在")
        if relation.auto_inferred:
            raise ValidationError(detail="自动推断的关联关系不可删除")
        await db.delete(relation)
        await db.commit()
        return True

    async def list_all(self, db: AsyncSession) -> list[AssetRelation]:
        """List all relations (manual + auto-inferred stored in DB)."""
        result = await db.execute(select(AssetRelation))
        return list(result.scalars().all())

    async def get_topology(
        self,
        db: AsyncSession,
        *,
        asset_type: str | None = None,
        status: str | None = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Build topology payload: { nodes, edges, groups }.

        Relations are fully auto-inferred (no manual editing):
        - same label -> CONNECTED (edge carries label name + color)
        - same /24 subnet -> CONNECTED

        Metrics are sourced from the latest daily health-check report by default.
        When refresh=True, metrics are fetched live from Prometheus (same logic
        as the health check service) and matched onto assets by instance.

        - Aggregates group counts by asset type.
        """
        query = select(Asset).options(
            selectinload(Asset.owner),
            selectinload(Asset.labels),
        )
        filters = []
        if asset_type:
            filters.append(Asset.asset_type == AssetType(asset_type))
        if status:
            filters.append(Asset.status == AssetStatus(status))
        # 默认排除已退役
        if not status:
            filters.append(Asset.status != AssetStatus.RETIRED)
        if filters:
            query = query.where(and_(*filters))

        result = await db.execute(query)
        assets = list(result.scalars().all())

        # Build nodes (without metrics yet)
        nodes = [self._asset_to_node(a) for a in assets]

        # Fill metrics (wrap in try/except so topology still loads even if metrics fail)
        try:
            if refresh:
                await self._fill_metrics_from_prometheus(assets, nodes)
            else:
                await self._fill_metrics_from_latest_report(db, assets, nodes)
        except Exception as e:
            logger.warning(f"填充拓扑指标失败，指标将留空: {e}", exc_info=True)

        # Build edges (label/idc/subnet based, fully auto-inferred)
        edges = self._build_edges(assets)

        # Group counts by type
        group_counts: dict[str, int] = defaultdict(int)
        for a in assets:
            group_counts[a.asset_type.value] += 1
        groups = [{"type": t, "count": c} for t, c in sorted(group_counts.items())]

        return {"nodes": nodes, "edges": edges, "groups": groups}

    def _asset_to_node(self, asset: Asset) -> dict[str, Any]:
        """Convert an Asset ORM instance to a topology node dict."""
        owner_name = asset.owner_name
        if not owner_name and asset.owner:
            owner_name = asset.owner.username

        labels = [
            {"id": lbl.id, "name": lbl.name, "color": lbl.color or "#1890ff"}
            for lbl in (asset.labels or [])
        ]

        return {
            "id": str(asset.id),
            "name": asset.name,
            "type": asset.asset_type.value,
            "status": asset.status.value,
            "ip_address": asset.ip_address,
            "idc": asset.idc,
            "owner_name": owner_name,
            "os_type": asset.os_type,
            "os_version": asset.os_version,
            "cpu_cores": asset.cpu_cores,
            "memory_gb": asset.memory_gb,
            "disk_gb": asset.disk_gb,
            "labels": labels,
            "metrics": {
                "cpu": None,
                "mem": None,
                "disk": None,
                "load1": None,
                "memory_total_mb": None,
                "disk_total_gb": None,
                "host_status": None,
                "checked_at": None,
            },
        }

    async def _fill_metrics_from_latest_report(
        self, db: AsyncSession, assets: list[Asset], nodes: list[dict[str, Any]]
    ) -> None:
        """Fill node metrics from the latest health-check report details.

        Matching key:
        - server/VM: HealthCheckDetail.instance matches asset.ip_address (host
          part before ':') or asset.prometheus_instance.
        - terminal: instance matches asset.ip_address or asset.hostname.
        """
        from app.models.health_check import HealthCheckDetail, HealthCheckReport

        # Latest report id
        rep_result = await db.execute(
            select(HealthCheckReport.id)
            .order_by(HealthCheckReport.report_time.desc())
            .limit(1)
        )
        report_id = rep_result.scalar_one_or_none()
        if not report_id:
            return

        detail_result = await db.execute(
            select(HealthCheckDetail).where(HealthCheckDetail.report_id == report_id)
        )
        details = list(detail_result.scalars().all())

        # Build lookup by instance string (lowercased)
        detail_by_instance: dict[str, HealthCheckDetail] = {}
        for d in details:
            if d.instance:
                detail_by_instance[d.instance.lower()] = d
                # also index by host part (before ':') for "ip:port" instances
                host = d.instance.split(":")[0]
                if host and host not in detail_by_instance:
                    detail_by_instance[host.lower()] = d

        for asset, node in zip(assets, nodes, strict=False):
            detail = self._match_detail(asset, detail_by_instance)
            if detail:
                node["metrics"] = {
                    "cpu": detail.cpu_usage,
                    "mem": detail.memory_usage,
                    "disk": detail.disk_usage,
                    "load1": detail.load1,
                    "memory_total_mb": detail.memory_total_mb,
                    "disk_total_gb": detail.disk_total_gb,
                    "host_status": detail.host_status,
                    "checked_at": detail.checked_at.isoformat() if detail.checked_at else None,
                }

    def _match_detail(
        self, asset: Asset, detail_by_instance: dict[str, Any]
    ) -> Any:
        """Find a matching health-check detail for an asset."""
        candidates: list[str] = []
        if asset.prometheus_instance:
            candidates.append(asset.prometheus_instance)
            candidates.append(asset.prometheus_instance.split(":")[0])
        if asset.ip_address:
            candidates.append(asset.ip_address)
            candidates.append(asset.ip_address.split(":")[0])
        if getattr(asset, "hostname", None):
            candidates.append(asset.hostname)
        for c in candidates:
            if not c:
                continue
            key = c.lower()
            if key in detail_by_instance:
                return detail_by_instance[key]
        return None

    async def _fill_metrics_from_prometheus(
        self, assets: list[Asset], nodes: list[dict[str, Any]]
    ) -> None:
        """Fetch live metrics from Prometheus (same source as daily health check).

        Falls back silently (empty metrics) if Prometheus is unavailable.
        """
        try:
            from app.services.prometheus.client import get_prometheus_client

            client = get_prometheus_client()
            server_metrics = await client.get_all_nodes_health_check()
            terminal_metrics = await client.get_all_terminals_with_metrics()
        except Exception as e:
            logger.warning(f"实时拉取 Prometheus 指标失败，指标将留空: {e}")
            return

        # Build lookup by instance/nodename/ip/hostname
        server_by_key: dict[str, dict[str, Any]] = {}
        for m in server_metrics:
            inst = m.get("instance", "")
            nodename = m.get("nodename", "")
            for k in (inst, inst.split(":")[0] if inst else "", nodename):
                if k:
                    server_by_key.setdefault(k.lower(), m)

        terminal_by_key: dict[str, dict[str, Any]] = {}
        for m in terminal_metrics:
            inst = m.get("ip_address", "") or m.get("hostname", "")
            hostname = m.get("hostname", "")
            for k in (inst, inst.split(":")[0] if inst else "", hostname):
                if k:
                    terminal_by_key.setdefault(k.lower(), m)

        for asset, node in zip(assets, nodes, strict=False):
            m = None
            if asset.asset_type.value in ("SERVER", "VM", "NETWORK", "STORAGE"):
                m = self._lookup_metric(asset, server_by_key)
            else:  # TERMINAL
                m = self._lookup_metric(asset, terminal_by_key)
            if not m:
                continue
            node["metrics"] = {
                "cpu": m.get("cpu_usage_percent") or m.get("cpu_usage"),
                "mem": m.get("memory_usage_percent") or m.get("memory_usage"),
                "disk": m.get("disk_usage_percent") or m.get("disk_usage"),
                "load1": m.get("load1"),
                "memory_total_mb": round(
                    (m.get("memory_total_mb") or (m.get("memory_total", 0.0) or 0.0)),
                    2,
                )
                if m.get("memory_total_mb")
                else (
                    round((m.get("memory_total", 0.0) or 0.0), 2)
                    if "memory_total" in m
                    else None
                ),
                "disk_total_gb": round(
                    (m.get("disk_total_gb") or (m.get("disk_total", 0.0) or 0.0)),
                    2,
                )
                if m.get("disk_total_gb")
                else (
                    round((m.get("disk_total", 0.0) or 0.0) / 1024 / 1024 / 1024, 2)
                    if "disk_total" in m
                    else None
                ),
                "host_status": None,
                "checked_at": None,
            }

    def _lookup_metric(self, asset: Asset, by_key: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        """Look up a prometheus metric dict for an asset across candidate keys."""
        candidates: list[str] = []
        if asset.prometheus_instance:
            candidates.append(asset.prometheus_instance)
            candidates.append(asset.prometheus_instance.split(":")[0])
        if asset.ip_address:
            candidates.append(asset.ip_address)
            candidates.append(asset.ip_address.split(":")[0])
        if getattr(asset, "hostname", None):
            candidates.append(asset.hostname)
        for c in candidates:
            if not c:
                continue
            hit = by_key.get(c.lower())
            if hit:
                return hit
        return None

    def _build_edges(self, assets: list[Asset]) -> list[dict[str, Any]]:
        """Build fully auto-inferred edges (no manual relations).

        Edge sources, in priority order:
        1. same label -> CONNECTED, carries label name + color
        2. same /24 subnet -> CONNECTED (skipped if label edge already connects the pair)

        Dedup key: (min(src,tgt), max(src,tgt), relation_type).
        Label edges are keyed per (pair, label) so two nodes sharing two labels
        produce two edges.
        """
        # Unordered pair helper
        def pair_key(a_id: str, b_id: str) -> tuple[str, str]:
            return (a_id, b_id) if a_id <= b_id else (b_id, a_id)

        edges_by_key: dict[tuple, dict[str, Any]] = {}
        # Track which unordered pairs already have a label edge (label takes priority over subnet CONNECTED)
        label_pairs: set[tuple[str, str]] = set()

        # 1) Same-label edges
        by_label: dict[int, dict[str, Any]] = {}  # label_id -> {name, color, members}
        for a in assets:
            for lbl in a.labels or []:
                entry = by_label.setdefault(
                    lbl.id, {"name": lbl.name, "color": lbl.color or "#1890ff", "members": []}
                )
                entry["members"].append(a)
        for lbl_id, entry in by_label.items():
            members = entry["members"]
            if len(members) < 2:
                continue
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    a, b = members[i], members[j]
                    src, tgt = str(a.id), str(b.id)
                    pk = pair_key(src, tgt)
                    key = (pk[0], pk[1], RelationType.CONNECTED.value, lbl_id)
                    edges_by_key[key] = {
                        "id": f"label-{lbl_id}-{src}-{tgt}",
                        "source": src,
                        "target": tgt,
                        "relation_type": RelationType.CONNECTED.value,
                        "auto_inferred": True,
                        "label": entry["name"],
                        "label_color": entry["color"],
                    }
                    label_pairs.add(pk)

        # 2) Same /24 subnet edges (only if no label edge already connects the pair)
        by_subnet: dict[str, list[Asset]] = defaultdict(list)
        for a in assets:
            if not a.ip_address:
                continue
            prefix = _get_ip_prefix(a.ip_address, 3)
            if prefix:
                by_subnet[prefix].append(a)
        for members in by_subnet.values():
            if len(members) < 2:
                continue
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    a, b = members[i], members[j]
                    src, tgt = str(a.id), str(b.id)
                    pk = pair_key(src, tgt)
                    if pk in label_pairs:
                        continue
                    key = (pk[0], pk[1], RelationType.CONNECTED.value)
                    if key in edges_by_key:
                        continue
                    edges_by_key[key] = {
                        "id": f"subnet-{src}-{tgt}",
                        "source": src,
                        "target": tgt,
                        "relation_type": RelationType.CONNECTED.value,
                        "auto_inferred": True,
                        "label": None,
                        "label_color": None,
                    }

        return list(edges_by_key.values())


crud_asset_relation = CRUDAssetRelation(AssetRelation)

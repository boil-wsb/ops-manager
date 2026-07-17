"""L2 单元测试: crud_asset.create_with_labels NC-1 修复回归测试.

★ NC-1 修复测试 (第二轮审查) ★

第一性原理覆盖的不变式:
- 时序性: db.flush() 必须在 AssetHistory(asset_id=db_obj.id) 构造之前调用，
  否则 db_obj.id 为 None，触发 NOT NULL 约束违反返回 500。

NC-1 根因:
- I-14 把"先 commit Asset 再 commit AssetHistory"合并为单次 commit
- 合并后遗漏 db.flush()，db.add() 不会立即 INSERT
- 构造 AssetHistory 时 db_obj.id 仍为 None
- await db.commit() 时 NOT NULL 约束违反 → 500
- 资产创建接口整体不可用

修复: 在 AssetHistory 构造前加 await db.flush()。
"""
import importlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# 直接从 sys.modules 取模块对象，避免被 app/crud/__init__.py 的 re-export 覆盖为实例
# 注意：以下 import 必须在 sys.modules 取模块对象之后，故加 noqa: E402
crud_asset_module = sys.modules.get("app.crud.crud_asset")
if crud_asset_module is None:
    # 若尚未导入，先触发导入再取
    crud_asset_module = importlib.import_module("app.crud.crud_asset")

from app.crud.crud_asset import crud_asset  # noqa: E402
from app.schemas.asset import AssetCreate  # noqa: E402


class TestCreateWithLabelsFlushBeforeHistory:
    """NC-1: db.flush() 必须在 AssetHistory 构造前调用."""

    async def test_flush_called_before_history_construction(self):
        """验证 db.flush() 被调用，且调用顺序在 db.add(history) 之前.

        通过追踪 mock_db.flush / mock_db.add 的调用顺序来验证。
        """
        # 用 MagicMock 包装 AsyncMock 以追踪调用顺序
        db = AsyncMock()
        # 关键: 让 flush 调用后 db_obj.id 有值（模拟真实 DB 行为）
        # 通过 side_effect 在 flush 时设置 db_obj.id
        async def _flush_side_effect():
            # flush 时设置 db_obj.id（模拟 DB INSERT 后自增 id 生成）
            # db_obj 已经在 db.add 中加入 session，这里通过遍历 mock 找到它
            for call in db.add.call_args_list:
                obj = call.args[0] if call.args else call[0]
                if hasattr(obj, "asset_id") and obj.asset_id == "TEST-NC1-001":
                    obj.id = 432  # 模拟 DB 生成的 id

        db.flush = AsyncMock(side_effect=_flush_side_effect)
        db.add = MagicMock()  # 同步 mock，便于追踪调用顺序
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock())

        # 构造 AssetCreate（不传 owner_name，避免触发 _resolve_owner_id_by_name）
        asset_in = AssetCreate(
            asset_id="TEST-NC1-001",
            name="NC-1 Test Server",
            asset_type="SERVER",
            status="ACTIVE",
            ip_address="192.168.1.100",
        )

        # patch 模块级函数 _resolve_owner_id_by_name（即使本测试不传 owner_name，
        # 也 patch 以确保测试与外部 DB 状态解耦）
        with patch.object(
            crud_asset_module,
            "_resolve_owner_id_by_name",
            AsyncMock(return_value=(None, False)),
        ):
            # 调用 create_with_labels
            result = await crud_asset.create_with_labels(db=db, obj_in=asset_in, owner_id=None)

        # ★ NC-1 核心断言 1: flush 被调用（修复点存在的证据）
        db.flush.assert_awaited_once()

        # ★ NC-1 核心断言 2: db.add 被调用两次（一次 Asset，一次 AssetHistory）
        assert db.add.call_count == 2, (
            "NC-1: create_with_labels 应该调用 db.add 两次（Asset + AssetHistory）"
        )

        # ★ NC-1 核心断言 3: 返回的 db_obj.id 不为 None（flush 后被填充）
        assert result.id == 432, (
            "NC-1: flush 后 db_obj.id 必须被填充（非 None），"
            "否则 AssetHistory.asset_id 为 None 触发 NOT NULL 约束"
        )

        # ★ NC-1 核心断言 4: 第二次 db.add（AssetHistory）的 asset_id 不为 None
        history_obj = db.add.call_args_list[1].args[0]
        assert history_obj.asset_id == 432, (
            "NC-1: AssetHistory.asset_id 必须等于已 flush 的 db_obj.id（432），"
            "若为 None 则说明 flush 缺失（NC-1 修复前的 bug 状态）"
        )

        # ★ NC-1 核心断言 5: 调用顺序 - add(Asset) → flush → add(AssetHistory) → commit
        # 通过 method_calls 追踪顺序
        method_names = [call[0] for call in db.method_calls]
        # 找到 add(Asset) 和 add(AssetHistory) 在 method_calls 中的位置
        add_calls = [i for i, name in enumerate(method_names) if name == "add"]
        flush_calls = [i for i, name in enumerate(method_names) if name == "flush"]
        commit_calls = [i for i, name in enumerate(method_names) if name == "commit"]

        assert len(add_calls) == 2
        assert len(flush_calls) == 1
        assert len(commit_calls) == 1
        # flush 必须在第一次 add 之后、第二次 add 之前
        assert add_calls[0] < flush_calls[0] < add_calls[1], (
            "NC-1 调用顺序: add(Asset) → flush → add(AssetHistory)，"
            "flush 必须在两次 add 之间"
        )
        # commit 必须在第二次 add 之后
        assert add_calls[1] < commit_calls[0]

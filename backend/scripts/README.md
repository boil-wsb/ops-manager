# Scripts 目录说明

此目录包含开发过程中使用的临时脚本。

## 测试脚本 (test_*.py)

这些是开发调试用的临时测试脚本，已被 `tests/` 目录中的正式测试用例替代。

**状态**: 建议迁移或废弃

| 脚本 | 建议 |
|------|------|
| test_asset_api.py | 迁移到 tests/api/ |
| test_users_api.py | 迁移到 tests/api/ |
| test_it_feedback_api.py | 迁移到 tests/api/ |
| test_prometheus_sync.py | 迁移到 tests/services/ |
| 其他 test_*.py | 考虑废弃 |

## 数据脚本 (check_*.py, fix_*.py, *.py)

这些是一次性使用的维护脚本，用于数据库修复和数据检查。

**建议**: 保留但考虑移至 `scripts/maintenance/` 目录

## 初始化脚本

| 脚本 | 用途 |
|------|------|
| init_data.py | 数据库初始化 |
| create_enum_types.py | 创建枚举类型 |

---

**优化建议**: 建立 `tests/` 目录，使用 pytest 框架统一管理测试。

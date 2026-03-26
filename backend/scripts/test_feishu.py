"""
Test script for Feishu messaging.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.integrations.feishu import FeishuService


def test_text_message():
    print("=" * 50)
    print("Test 1: Send plain text message")
    print("=" * 50)

    if not settings.feishu_enable:
        print("WARNING: Feishu is not enabled")
        return False

    service = FeishuService()
    user_id = "ou_e7e3a761a4bc2e3ae17402c67d7685ae"
    test_message = "【IT管理测试消息】\n这是一条来自 Ops Manager 系统的测试消息。\n时间: 2026-03-23"

    print(f"Sending text message to user: {user_id}")
    try:
        result = service.send_text_message(user_id=user_id, text=test_message)
        print(f"Success! Result: {result}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False


def test_interactive_message():
    print("\n" + "=" * 50)
    print("Test 2: Send interactive card message")
    print("=" * 50)

    if not settings.feishu_enable:
        print("WARNING: Feishu is not enabled")
        return False

    service = FeishuService()
    user_id = "ou_e7e3a761a4bc2e3ae17402c67d7685ae"

    try:
        result = service.send_interactive_message(
            user_id=user_id,
            title="【系统测试通知】",
            content="这是一条卡片消息测试",
            tags=[
                {"label": "测试时间", "value": "2026-03-23"},
                {"label": "测试类型", "value": "飞书集成"},
                {"label": "状态", "value": "成功"},
            ],
        )
        print(f"Success! Result: {result}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False


def test_it_feedback_message():
    print("\n" + "=" * 50)
    print("Test 3: Send IT Feedback resolved notification")
    print("=" * 50)

    if not settings.feishu_enable:
        print("WARNING: Feishu is not enabled")
        return False

    service = FeishuService()
    user_id = "ou_e7e3a761a4bc2e3ae17402c67d7685ae"

    try:
        result = service.send_it_feedback_resolved(
            user_id=user_id,
            feedback_id=12345,
            feedback_content="电脑卡顿严重，开机需要10分钟",
            resolved_by="张三",
            notes="已更换固态硬盘，系统重装",
        )
        print(f"Success! Result: {result}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False


def main():
    print("Feishu Service Testing")
    print(f"Enabled: {settings.feishu_enable}")
    print(f"App ID: {settings.feishu_app_id}")
    print()

    results = []
    results.append(("Text Message", test_text_message()))
    results.append(("Interactive Card", test_interactive_message()))
    results.append(("IT Feedback Notification", test_it_feedback_message()))

    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    for name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  {name}: {status}")

    all_passed = all(success for _, success in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    success = main()
    sys.exit(success)

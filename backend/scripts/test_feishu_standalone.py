"""
Standalone test for Feishu SDK - no project dependencies.
"""
import sys

APP_ID = "cli_a94a4a8cd3241bd7"
APP_SECRET = "UiYalhbNMevKiES2mD2GGbk4VrahTzUp"
USER_ID = "ou_e7e3a761a4bc2e3ae17402c67d7685ae"

import lark_oapi as lark


def test_lark_sdk_import():
    print("=" * 50)
    print("Test 1: Import lark-oapi SDK")
    print("=" * 50)
    try:
        print(f"  SDK imported successfully")
        print(f"  Available modules: im, event, ws")
        return True
    except Exception as e:
        print(f"  Import failed: {e}")
        return False


def test_client_creation():
    print("\n" + "=" * 50)
    print("Test 2: Create Feishu Client")
    print("=" * 50)
    try:
        client = lark.Client.builder() \
            .app_id(APP_ID) \
            .app_secret(APP_SECRET) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        print(f"  Client created successfully")
        return client
    except Exception as e:
        print(f"  Client creation failed: {e}")
        return None


def test_send_text_message(client):
    print("\n" + "=" * 50)
    print("Test 3: Send Text Message")
    print("=" * 50)
    if client is None:
        print("  Skipped - no client")
        return False

    try:
        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

        request = (
            CreateMessageRequest.builder()
            .receive_id_type("open_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(USER_ID)
                .msg_type("text")
                .content(lark.JSON.marshal({"text": "【测试消息】\n这是一条来自SDK的测试消息。\n时间: 2026-03-23"}))
                .build()
            )
            .build()
        )

        response = client.im.v1.message.create(request)

        if response.success():
            print(f"  Message sent successfully!")
            print(f"  Message ID: {response.data.message_id if response.data else 'N/A'}")
            return True
        else:
            print(f"  Failed: {response.code} - {response.msg}")
            return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False


def test_send_interactive_card(client):
    print("\n" + "=" * 50)
    print("Test 4: Send Interactive Card Message")
    print("=" * 50)
    if client is None:
        print("  Skipped - no client")
        return False

    try:
        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

        card_content = {
            "header": {
                "title": {"tag": "plain_text", "content": "【IT反馈处理通知】"},
                "template": "blue",
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": "您的IT反馈（ID: 12345）已处理完成"}},
                {"tag": "div", "text": {"tag": "lark_md", "content": "• 处理人: 张三\n• 反馈内容: 电脑卡顿\n• 处理备注: 已更换硬盘"}},
            ],
        }

        request = (
            CreateMessageRequest.builder()
            .receive_id_type("open_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(USER_ID)
                .msg_type("interactive")
                .content(lark.JSON.marshal(card_content))
                .build()
            )
            .build()
        )

        response = client.im.v1.message.create(request)

        if response.success():
            print(f"  Card message sent successfully!")
            print(f"  Message ID: {response.data.message_id if response.data else 'N/A'}")
            return True
        else:
            print(f"  Failed: {response.code} - {response.msg}")
            return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False


def main():
    print("Feishu SDK Standalone Test")
    print(f"App ID: {APP_ID}")
    print(f"User ID: {USER_ID}")

    results = []

    results.append(("SDK Import", test_lark_sdk_import()))
    client = test_client_creation()
    results.append(("Client Creation", client is not None))
    results.append(("Text Message", test_send_text_message(client)))
    results.append(("Interactive Card", test_send_interactive_card(client)))

    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    for name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  {name}: {status}")

    all_passed = all(success for _, success in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Test sending image to Feishu user.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateImageRequest, CreateImageRequestBody


def get_feishu_client():
    """Get or create Feishu client."""
    return (
        lark.Client.builder()
        .app_id(settings.feishu_app_id)
        .app_secret(settings.feishu_app_secret)
        .log_level(lark.LogLevel.INFO)
        .build()
    )


def upload_image(image_path: str) -> str | None:
    """Upload image to Feishu and return image_key."""
    client = get_feishu_client()

    with open(image_path, "rb") as f:
        request = (
            CreateImageRequest.builder()
            .request_body(
                CreateImageRequestBody.builder()
                .image_type("message")
                .image(f)
                .build()
            )
            .build()
        )

        try:
            response = client.im.v1.image.create(request)

            if response.success():
                image_key = response.data.image_key if response.data else None
                print(f"Image uploaded successfully, image_key: {image_key}")
                return image_key
            else:
                print(f"Failed to upload image: code={response.code}, msg={response.msg}")
                return None
        except Exception as e:
            print(f"Error uploading image: {e}")
            return None


def send_image_message(open_id: str, image_key: str) -> dict:
    """Send image message to user."""
    from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

    client = get_feishu_client()

    content = lark.JSON.marshal({"image_key": image_key})

    request = (
        CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("image")
            .content(content)
            .build()
        )
        .build()
    )

    try:
        response = client.im.v1.message.create(request)

        if response.success():
            message_id = response.data.message_id if response.data else None
            print(f"Image message sent successfully, message_id: {message_id}")
            return {"success": True, "message_id": message_id}
        else:
            print(f"Failed to send image message: code={response.code}, msg={response.msg}")
            return {"success": False, "error": f"{response.code} - {response.msg}"}
    except Exception as e:
        print(f"Error sending image message: {e}")
        return {"success": False, "error": str(e)}


def search_user_by_name(name: str) -> str | None:
    """Search user by name and return open_id."""
    from lark_oapi.api.contact.v3 import GetUserRequest

    client = get_feishu_client()

    users = fetch_all_feishu_users()

    for user in users:
        if name.lower() in user.get("name", "").lower():
            print(f"Found user: {user['name']} (open_id: {user['open_id']})")
            return user["open_id"]

    return None


def fetch_all_feishu_users() -> list:
    """Fetch all users from Feishu app scope."""
    from lark_oapi.api.contact.v3 import ListScopeRequest

    client = get_feishu_client()

    scope_req = ListScopeRequest.builder().user_id_type("open_id").build()
    scope_resp = client.contact.v3.scope.list(scope_req)

    if not scope_resp.success() or not scope_resp.data:
        print(f"Failed to get scope: {scope_resp.msg}")
        return []

    user_ids = scope_resp.data.user_ids or []
    print(f"Found {len(user_ids)} users in scope")

    users = []
    for uid in user_ids:
        try:
            from lark_oapi.api.contact.v3 import GetUserRequest
            req = GetUserRequest.builder().user_id(uid).user_id_type("open_id").build()
            resp = client.contact.v3.user.get(req)

            if resp.success() and resp.data and resp.data.user:
                user = resp.data.user
                users.append({
                    "open_id": getattr(user, "open_id", uid),
                    "name": getattr(user, "name", "Unknown"),
                    "enterprise_email": getattr(user, "enterprise_email", None),
                })
        except Exception as e:
            print(f"Error getting user {uid}: {e}")

    return users


if __name__ == "__main__":
    print("=" * 60)
    print("Feishu Image Send Test")
    print("=" * 60)

    TARGET_NAME = "wangshibin"
    TARGET_OPEN_ID = "ou_e7e3a761a4bc2e3ae17402c67d7685ae"
    TEST_IMAGE_PATH = Path(__file__).parent.parent / "test_image.png"

    if not TEST_IMAGE_PATH.exists():
        print(f"Test image not found: {TEST_IMAGE_PATH}")
        print("Please ensure test_image.png exists in the backend directory")
        sys.exit(1)

    if TARGET_OPEN_ID:
        open_id = TARGET_OPEN_ID
        print(f"\nUsing specified open_id: {open_id}")
    else:
        print(f"\nSearching for user: {TARGET_NAME}")
        open_id = search_user_by_name(TARGET_NAME)

        if not open_id:
            print(f"\nUser '{TARGET_NAME}' not found in Feishu app scope.")
            print("\nAvailable users:")
            users = fetch_all_feishu_users()
            for user in users:
                print(f"  - {user['name']} ({user['open_id']})")
            sys.exit(1)

    print(f"\nFound target user with open_id: {open_id}")

    print(f"\nStep 1: Uploading image...")
    image_key = upload_image(str(TEST_IMAGE_PATH))

    if not image_key:
        print("Failed to upload image")
        sys.exit(1)

    print(f"\nStep 2: Sending image message...")
    result = send_image_message(open_id, image_key)

    if result.get("success"):
        print(f"\n✓ Image sent successfully!")
        print(f"  Message ID: {result.get('message_id')}")
    else:
        print(f"\n✗ Failed to send image: {result.get('error')}")
        sys.exit(1)
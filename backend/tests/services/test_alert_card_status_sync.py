"""
Tests for alert card status sync feature.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestFeishuNotificationServiceSendP2P:
    """Test FeishuNotificationService send_p2p_card_message method."""

    def test_send_p2p_card_message_returns_message_id(self):
        """send_p2p_card_message should return dict with success and message_id."""
        from app.services.alerts.feishu_notification import FeishuNotificationService

        service = FeishuNotificationService()
        service._enabled = True

        mock_response = MagicMock()
        mock_response.success.return_value = True
        mock_response.data = MagicMock()
        mock_response.data.message_id = "om_test123"

        mock_client = MagicMock()
        mock_client.im.v1.message.create.return_value = mock_response
        service._client = mock_client

        result = service.send_p2p_card_message(
            open_id="ou_test",
            card_content={"schema": "2.0", "body": {}},
        )

        assert result["success"] is True
        assert result["message_id"] == "om_test123"

    def test_send_p2p_card_message_returns_false_on_failure(self):
        """send_p2p_card_message should return success=False on failure."""
        from app.services.alerts.feishu_notification import FeishuNotificationService

        service = FeishuNotificationService()
        service._enabled = True

        mock_response = MagicMock()
        mock_response.success.return_value = False
        mock_response.code = 99999
        mock_response.msg = "error"

        mock_client = MagicMock()
        mock_client.im.v1.message.create.return_value = mock_response
        service._client = mock_client

        result = service.send_p2p_card_message(
            open_id="ou_test",
            card_content={"schema": "2.0", "body": {}},
        )

        assert result["success"] is False
        assert result["message_id"] is None


class TestFeishuNotificationServiceUpdateCard:
    """Test FeishuNotificationService update_card_message method."""

    def test_update_card_message_method_exists(self):
        """update_card_message method should exist."""
        from app.services.alerts.feishu_notification import FeishuNotificationService

        service = FeishuNotificationService()
        assert hasattr(service, "update_card_message")

    def test_update_card_message_returns_success(self):
        """update_card_message should return dict with success status."""
        from app.services.alerts.feishu_notification import FeishuNotificationService

        service = FeishuNotificationService()
        service._enabled = True

        mock_response = MagicMock()
        mock_response.success.return_value = True

        mock_client = MagicMock()
        mock_client.im.v1.message.patch.return_value = mock_response
        service._client = mock_client

        result = service.update_card_message(
            open_message_id="om_test123",
            card_content={"schema": "2.0", "body": {}},
        )

        assert result["success"] is True

    def test_update_card_message_returns_error_on_failure(self):
        """update_card_message should return error on failure."""
        from app.services.alerts.feishu_notification import FeishuNotificationService

        service = FeishuNotificationService()
        service._enabled = True

        mock_response = MagicMock()
        mock_response.success.return_value = False
        mock_response.code = 99999
        mock_response.msg = "update failed"

        mock_client = MagicMock()
        mock_client.im.v1.message.patch.return_value = mock_response
        service._client = mock_client

        result = service.update_card_message(
            open_message_id="om_test123",
            card_content={"schema": "2.0", "body": {}},
        )

        assert result["success"] is False
        assert "error" in result


class TestFeishuNotificationServiceBuildResolvedCard:
    """Test FeishuNotificationService build_resolved_card method."""

    def test_build_resolved_card_method_exists(self):
        """build_resolved_card method should exist."""
        from app.services.alerts.feishu_notification import FeishuNotificationService

        service = FeishuNotificationService()
        assert hasattr(service, "build_resolved_card")

    def test_build_resolved_card_contains_recovered_message(self):
        """build_resolved_card should return card without action buttons."""
        from app.services.alerts.feishu_notification import FeishuNotificationService

        service = FeishuNotificationService()

        card = service.build_resolved_card(
            alertname="TestAlert",
            severity="critical",
            instance="192.168.1.1",
        )

        assert card["schema"] == "2.0"
        assert "🟢" in card["header"]["title"]["content"]
        assert card["header"]["template"] == "green"

        elements_text = str(card["body"]["elements"])
        assert "该告警已恢复" in elements_text or "✅" in elements_text

    def test_build_resolved_card_has_no_buttons(self):
        """build_resolved_card should return card without action buttons."""
        from app.services.alerts.feishu_notification import FeishuNotificationService

        service = FeishuNotificationService()

        card = service.build_resolved_card(
            alertname="TestAlert",
            severity="warning",
            instance="192.168.1.1",
        )

        card_str = str(card)
        assert "button" not in card_str.lower()
        assert "知道了" not in card_str
        assert "转交" not in card_str


class TestAlertHistoryModelHasFeishuField:
    """Test AlertHistory model has feishu_open_message_id field."""

    def test_alert_history_has_feishu_open_message_id_field(self):
        """AlertHistory should have feishu_open_message_id attribute."""
        from app.models.alert import AlertHistory

        history = AlertHistory(
            alertname="TestAlert",
            status="firing",
            severity="critical",
            instance="192.168.1.1",
            description="Test description",
        )

        assert hasattr(history, "feishu_open_message_id")

    def test_alert_history_feishu_open_message_id_default_is_none(self):
        """AlertHistory feishu_open_message_id default should be None."""
        from app.models.alert import AlertHistory

        history = AlertHistory(
            alertname="TestAlert",
            status="firing",
            severity="critical",
            instance="192.168.1.1",
            description="Test description",
        )

        assert history.feishu_open_message_id is None

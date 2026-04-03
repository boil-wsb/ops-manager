"""
Test Alertmanager webhook endpoint.
"""
import requests
import json

WEBHOOK_URL = "http://localhost:8000/api/v1/webhook/alertmanager"

payload = {
    "receiver": "feishu_webhook",
    "status": "firing",
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "alertname": "HighDiskUsage",
                "severity": "critical",
                "instance": "192.168.23.36",
                "environment": "production"
            },
            "annotations": {
                "summary": "Disk usage is above 90% on 192.168.23.36",
                "description": "Disk usage is above 90% for the last 5 minutes on DigitalAI server"
            },
            "startsAt": "2026-04-01T12:00:00Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": "http://prometheus:9090/graph?g0.expr=disk_usage_percent > 90"
        }
    ],
    "groupLabels": {"alertname": "HighDiskUsage"},
    "commonLabels": {"severity": "critical", "environment": "production"},
    "commonAnnotations": {"summary": "Disk usage is above 90%"},
    "externalURL": "http://alertmanager:9093"
}

print("Sending test Alertmanager webhook request...")
print(f"URL: {WEBHOOK_URL}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {response.text}")
except requests.exceptions.ConnectionError as e:
    print(f"\nConnection Error: Could not connect to {WEBHOOK_URL}")
    print("Make sure the backend server is running on localhost:8000")
except Exception as e:
    print(f"\nError: {e}")

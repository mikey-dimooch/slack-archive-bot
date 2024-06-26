import os
import pytest
import requests_mock
from archive import fetch_messages, fetch_all_channels, archive_messages

@pytest.fixture
def slack_token(monkeypatch):
    monkeypatch.setenv('SLACK_BOT_TOKEN', 'your-test-slack-token')
    monkeypatch.setenv('SLACK_ARCHIVE_USER_ID', 'test_user_id')

def test_fetch_messages(slack_token, requests_mock):
    channel_id = 'C12345678'
    start_time = 0
    end_time = 9999999999
    mock_response = {
        "ok": True,
        "messages": [
            {"ts": "1234567890.123456", "user": "U12345678", "text": "Hello world"},
        ]
    }
    requests_mock.get(f'https://slack.com/api/conversations.history?channel={channel_id}&oldest={start_time}&latest={end_time}', json=mock_response)
    messages = fetch_messages(channel_id, start_time, end_time)
    assert len(messages) == 1

def test_fetch_all_channels(slack_token, requests_mock):
    mock_response = {
        "ok": True,
        "channels": [
            {"id": "C12345678", "name": "general"},
        ]
    }
    requests_mock.get('https://slack.com/api/conversations.list?types=public_channel,private_channel', json=mock_response)
    channels = fetch_all_channels()
    assert len(channels) == 1

def test_archive_messages(slack_token, requests_mock):
    requests_mock.get('https://slack.com/api/conversations.list?types=public_channel,private_channel', json={
        "ok": True,
        "channels": [
            {"id": "C12345678", "name": "general"},
        ]
    })
    requests_mock.get('https://slack.com/api/conversations.history?channel=C12345678&oldest=0&latest=9999999999', json={
        "ok": True,
        "messages": [
            {"ts": "1234567890.123456", "user": "U12345678", "text": "Hello world"},
        ]
    })
    requests_mock.post('https://slack.com/api/files.upload', json={"ok": True})
    archive_messages()
    assert os.path.exists("slack_archive_2021_05.csv")  # Adjust file name accordingly

if __name__ == "__main__":
    pytest.main()

"""
client.py のユニットテスト。
"""

import pytest
from unittest.mock import Mock, patch
from requests.exceptions import Timeout
import sys
from pathlib import Path

# src/ をパスに追加（パッケージ import 用）
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from win_llm_chat_pyside.client import (
    OpenAiCompatibleClient,
    OllamaClient,
    NetworkError,
    AuthenticationError,
    ResponseFormatError
)
from win_llm_chat_pyside.models import Message


class TestOpenAiCompatibleClient:
    """OpenAiCompatibleClient のテスト。"""
    
    def test_send_chat_success(self):
        """正常系: メッセージ送信が成功する。"""
        client = OpenAiCompatibleClient(
            base_url="http://localhost:11434",
            model="test-model"
        )
        
        messages = [
            Message(role="user", content="Hello")
        ]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hi there!"
                    }
                }
            ]
        }
        
        with patch("requests.post", return_value=mock_response):
            result = client.send_chat(messages)
        
        assert result == "Hi there!"
    
    def test_send_chat_authentication_error(self):
        """認証エラー（401）が発生する。"""
        client = OpenAiCompatibleClient(
            base_url="http://localhost:11434",
            model="test-model",
            api_key="invalid-key"
        )
        
        messages = [Message(role="user", content="Hello")]
        
        mock_response = Mock()
        mock_response.status_code = 401
        
        with patch("requests.post", return_value=mock_response):
            with pytest.raises(AuthenticationError):
                client.send_chat(messages)
    
    def test_send_chat_network_error(self):
        """ネットワークエラーが発生する。"""
        client = OpenAiCompatibleClient(
            base_url="http://localhost:11434",
            model="test-model"
        )
        
        messages = [Message(role="user", content="Hello")]
        
        with patch("requests.post", side_effect=ConnectionError("Connection failed")):
            with pytest.raises(NetworkError):
                client.send_chat(messages)
    
    def test_send_chat_response_format_error(self):
        """レスポンス形式エラーが発生する。"""
        client = OpenAiCompatibleClient(
            base_url="http://localhost:11434",
            model="test-model"
        )
        
        messages = [Message(role="user", content="Hello")]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "invalid": "format"
        }
        mock_response.text = '{"invalid": "format"}'
        
        with patch("requests.post", return_value=mock_response):
            with pytest.raises(ResponseFormatError):
                client.send_chat(messages)


class TestOllamaClient:
    """OllamaClient のテスト。"""
    
    def test_send_chat_success(self):
        """正常系: メッセージ送信が成功する。"""
        client = OllamaClient(
            base_url="http://localhost:11434",
            model="llama3"
        )
        
        messages = [
            Message(role="user", content="Hello")
        ]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "Hello from Ollama!"
            }
        }
        
        with patch("requests.post", return_value=mock_response):
            result = client.send_chat(messages)
        
        assert result == "Hello from Ollama!"
    
    def test_send_chat_network_error(self):
        """ネットワークエラーが発生する。"""
        client = OllamaClient(
            base_url="http://localhost:11434",
            model="llama3"
        )
        
        messages = [Message(role="user", content="Hello")]
        
        with patch("requests.post", side_effect=Timeout()):
            with pytest.raises(NetworkError):
                client.send_chat(messages)


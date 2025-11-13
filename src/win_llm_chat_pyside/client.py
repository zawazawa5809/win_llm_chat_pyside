"""
LLM クライアントの抽象化と実装を提供する。
"""

from typing import Protocol, Optional
import builtins
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError as RequestsConnectionError

from .models import Message


class LlmClientError(Exception):
    """LLM クライアントのエラー基底クラス。"""
    pass


class NetworkError(LlmClientError):
    """ネットワーク接続エラー。"""
    pass


class AuthenticationError(LlmClientError):
    """認証エラー。"""
    pass


class ResponseFormatError(LlmClientError):
    """レスポンス形式エラー。"""
    pass


class BaseLlmClient(Protocol):
    """LLM クライアントのインターフェース。"""
    
    def send_chat(self, messages: list[Message]) -> str:
        """
        メッセージリストを送信し、アシスタントの応答を取得する。
        
        Args:
            messages: 送信するメッセージのリスト
            
        Returns:
            アシスタントの応答文字列（Markdown）
            
        Raises:
            NetworkError: ネットワーク接続エラー
            AuthenticationError: 認証エラー
            ResponseFormatError: レスポンス形式エラー
        """
        ...


class OpenAiCompatibleClient:
    """OpenAI 互換 API クライアント（/v1/chat/completions）。"""
    
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: Optional[str] = None,
        timeout: float | tuple[float, float] = 30
    ):
        """
        Args:
            base_url: API のベース URL（例: http://localhost:11434）
            model: 使用するモデル名
            api_key: API キー（任意）
            timeout: タイムアウト秒数（connect/read のタプルも可）
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        
    def send_chat(self, messages: list[Message]) -> str:
        """
        メッセージを送信し、応答を取得する。
        
        Args:
            messages: 送信するメッセージのリスト
            
        Returns:
            アシスタントの応答文字列
            
        Raises:
            NetworkError: ネットワーク接続エラー
            AuthenticationError: 認証エラー
            ResponseFormatError: レスポンス形式エラー
        """
        endpoint = f"{self.base_url}/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages]
        }
        
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            # ステータスコードチェック
            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError(
                    f"認証エラー（ステータスコード: {response.status_code}）。"
                    "API キーを確認してください。"
                )
            
            if response.status_code != 200:
                raise NetworkError(
                    f"HTTP エラー（ステータスコード: {response.status_code}）: "
                    f"{response.text}"
                )
            
            # レスポンスパース
            try:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content
            except (KeyError, IndexError, ValueError) as e:
                raise ResponseFormatError(
                    f"レスポンス形式が不正です: {e}\n"
                    f"レスポンス: {response.text[:200]}"
                )
                
        except Timeout:
            raise NetworkError(
                f"接続がタイムアウトしました（{self.timeout}秒）。"
                "ネットワーク接続またはサーバーの状態を確認してください。"
            )
        except (RequestsConnectionError, builtins.ConnectionError) as e:
            raise NetworkError(
                f"サーバーへの接続に失敗しました: {e}\n"
                f"ベース URL（{self.base_url}）を確認してください。"
            )
        except RequestException as e:
            raise NetworkError(f"リクエスト中にエラーが発生しました: {e}")


class OllamaClient:
    """Ollama API クライアント（/api/chat）。"""
    
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int = 30
    ):
        """
        Args:
            base_url: API のベース URL（例: http://localhost:11434）
            model: 使用するモデル名
            timeout: タイムアウト秒数
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        
    def send_chat(self, messages: list[Message]) -> str:
        """
        メッセージを送信し、応答を取得する。
        
        Args:
            messages: 送信するメッセージのリスト
            
        Returns:
            アシスタントの応答文字列
            
        Raises:
            NetworkError: ネットワーク接続エラー
            ResponseFormatError: レスポンス形式エラー
        """
        endpoint = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "stream": False
        }
        
        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise NetworkError(
                    f"HTTP エラー（ステータスコード: {response.status_code}）: "
                    f"{response.text}"
                )
            
            # Ollama のレスポンス形式をパース
            try:
                data = response.json()
                content = data["message"]["content"]
                return content
            except (KeyError, ValueError) as e:
                raise ResponseFormatError(
                    f"レスポンス形式が不正です: {e}\n"
                    f"レスポンス: {response.text[:200]}"
                )
                
        except Timeout:
            raise NetworkError(
                f"接続がタイムアウトしました（{self.timeout}秒）。"
            )
        except (RequestsConnectionError, builtins.ConnectionError) as e:
            raise NetworkError(
                f"サーバーへの接続に失敗しました: {e}\n"
                f"ベース URL（{self.base_url}）を確認してください。"
            )
        except RequestException as e:
            raise NetworkError(f"リクエスト中にエラーが発生しました: {e}")



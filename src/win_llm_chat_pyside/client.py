"""
LLM クライアントの抽象化と実装を提供する。
"""

from typing import Protocol, Optional, Iterator
import builtins
import requests  # type: ignore[import-untyped]
from requests.exceptions import RequestException, Timeout, ConnectionError as RequestsConnectionError  # type: ignore[import-untyped]
import json

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
    
    def send_chat(self, messages: list[Message], *, options: Optional[dict] = None) -> str:
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

    def iter_chat(self, messages: list[Message], *, options: Optional[dict] = None) -> Iterator[str]:
        """
        メッセージリストを送信し、アシスタントの応答増分を逐次取得する。
        ストリーム非対応の場合は send_chat の全文を1回だけ yield する。

        Args:
            messages: 送信するメッセージのリスト

        Yields:
            応答テキストの増分
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
        
    def send_chat(self, messages: list[Message], *, options: Optional[dict] = None) -> str:
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
        if options:
            payload.update(self._sanitize_options(options))
        
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

    def iter_chat(self, messages: list[Message], *, options: Optional[dict] = None) -> Iterator[str]:
        """
        OpenAI 互換 API のストリーミング（SSE 風）を処理し、テキスト増分を返す。
        非対応やエラー時は send_chat にフォールバックし、その結果を一括で返す。
        """
        endpoint = f"{self.base_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "stream": True,
        }
        if options:
            payload.update(self._sanitize_options(options))

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout,
                stream=True,
            )
            # 明示的に UTF-8 を指定（自動推定に依存しない）
            response.encoding = "utf-8"

            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError(
                    f"認証エラー（ステータスコード: {response.status_code}）。"
                )
            if response.status_code != 200:
                raise NetworkError(
                    f"HTTP エラー（ステータスコード: {response.status_code}）: {response.text}"
                )

            for raw_line in response.iter_lines(decode_unicode=False):
                if not raw_line:
                    continue
                # OpenAI 互換のストリームは "data: ..." 行
                try:
                    line = raw_line.decode("utf-8", errors="replace")
                except Exception:
                    continue
                if line.startswith("data:"):
                    data_part = line[len("data:"):].strip()
                    if data_part == "[DONE]":
                        break
                    try:
                        obj = json.loads(data_part)
                        delta = obj["choices"][0].get("delta", {}).get("content")
                        if delta:
                            yield delta
                    except (ValueError, KeyError, IndexError):
                        # 形式不正はスキップ（全体停止はしない）
                        continue
        except (Timeout, RequestsConnectionError, RequestException):
            # フォールバックで一括レスポンス
            try:
                full = self.send_chat(messages, options=options)
                if full:
                    yield full
            except Exception:
                # ここでの例外は上位でハンドリングされる想定
                raise

    @staticmethod
    def _sanitize_options(options: dict) -> dict:
        allowed_keys = {"temperature", "top_p", "frequency_penalty", "presence_penalty", "max_tokens"}
        sanitized: dict = {}
        for key in allowed_keys:
            if key in options and options[key] is not None:
                sanitized[key] = options[key]
        return sanitized


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
        
    def send_chat(self, messages: list[Message], *, options: Optional[dict] = None) -> str:
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
        if options:
            payload.update(self._sanitize_options(options))
        
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

    def iter_chat(self, messages: list[Message], *, options: Optional[dict] = None) -> Iterator[str]:
        """
        Ollama の JSON Lines ストリームを処理し、テキスト増分を返す。
        `done: true` を受け取ったら終了する。失敗時は send_chat にフォールバック。
        """
        endpoint = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "stream": True,
        }
        if options:
            payload.update(self._sanitize_options(options))
        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=self.timeout,
                stream=True,
                headers={"Accept": "application/json", "Accept-Charset": "utf-8"},
            )
            # 明示的に UTF-8 を指定
            response.encoding = "utf-8"
            if response.status_code != 200:
                raise NetworkError(
                    f"HTTP エラー（ステータスコード: {response.status_code}）: {response.text}"
                )
            for raw_line in response.iter_lines(decode_unicode=False):
                if not raw_line:
                    continue
                try:
                    line = raw_line.decode("utf-8", errors="replace")
                    obj = json.loads(line)
                except ValueError:
                    continue
                if obj.get("done"):
                    break
                # 代表的な形式: {"message": {"role": "...", "content": "..."}, "done": false, ...}
                message_obj = obj.get("message") or {}
                delta = message_obj.get("content")
                if delta:
                    yield delta
        except (Timeout, RequestsConnectionError, RequestException):
            # フォールバックで一括レスポンス
            try:
                full = self.send_chat(messages, options=options)
                if full:
                    yield full
            except Exception:
                raise

    @staticmethod
    def _sanitize_options(options: dict) -> dict:
        allowed_keys = {"temperature", "top_p"}
        sanitized: dict = {}
        for key in allowed_keys:
            if key in options and options[key] is not None:
                sanitized[key] = options[key]
        return sanitized



from __future__ import annotations


class TelegramClient:
    """Thin abstraction over Telegram send API.

    In production this class should call Telegram Bot API.
    For MVP demo we keep a deterministic fake implementation.
    """

    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> str:
        if not chat_id.startswith("-"):
            raise ValueError("chat_id non valido: deve iniziare con '-' per gruppi/canali")
        if not text.strip():
            raise ValueError("messaggio vuoto")
        if parse_mode not in {"HTML", "MarkdownV2"}:
            raise ValueError("parse_mode non supportato")
        # Emoji support: native unicode, no extra handling required.
        return f"mock-msg-{abs(hash((chat_id, text, parse_mode))) % 100000}"

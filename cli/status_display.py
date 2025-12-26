"""Status display functionality for CLI"""

from rich.table import Table
from utils.storage import TokenStorage


def show_token_status(storage: TokenStorage, console):
    """
    Display detailed token status

    Args:
        storage: TokenStorage instance
        console: Rich console for output
    """
    status = storage.get_status()

    table = Table(title="Token Status Details")
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Has Tokens", "Yes" if status["has_tokens"] else "No")
    table.add_row("Is Expired", "Yes" if status["is_expired"] else "No")

    if status["expires_at"]:
        table.add_row("Expires At", status["expires_at"])
        table.add_row("Time Until Expiry", status["time_until_expiry"])

    table.add_row("Token File", str(storage.token_file))

    console.print(table)
    console.print("\nPress Enter to continue...")
    input()


def get_combined_auth_status(claude_storage: TokenStorage, chatgpt_storage) -> tuple[str, str, str]:
    """
    Get a combined authentication status for both Claude and ChatGPT.

    Args:
        claude_storage: TokenStorage instance for Claude
        chatgpt_storage: ChatGPTTokenStorage instance

    Returns:
        Tuple of (status_label, detail_message, severity)
    """
    c_status = claude_storage.get_status()
    g_status = chatgpt_storage.get_status()

    c_has_valid_token = c_status.get("has_tokens") and not c_status.get("is_expired")
    g_has_valid_token = g_status.get("has_tokens") and not g_status.get("is_expired")

    if c_has_valid_token and g_has_valid_token:
        return "BOTH", "Claude & ChatGPT", "green"
    if c_has_valid_token:
        return "CLAUDE_ONLY", "Claude only", "green"
    if g_has_valid_token:
        return "CHATGPT_ONLY", "ChatGPT only", "green"

    # No valid tokens, determine warning or error
    c_has_any_token = c_status.get("has_tokens")
    g_has_any_token = g_status.get("has_tokens")

    if c_has_any_token or g_has_any_token:
        return "EXPIRED", "Token(s) expired", "yellow"

    return "NONE", "No tokens available", "red"

def get_auth_status(storage: TokenStorage) -> tuple[str, str]:
    """
    Get authentication status and expiry info

    Args:
        storage: TokenStorage instance

    Returns:
        Tuple of (status, detail_message)
    """
    from datetime import datetime

    status = storage.get_status()

    if not status["has_tokens"]:
        return "NO AUTH", "No tokens available"

    if status["is_expired"]:
        return "EXPIRED", f"Expired {status['time_until_expiry']}"

    # Calculate time remaining
    if status["expires_at"]:
        expires_dt = datetime.fromisoformat(status["expires_at"])
        now = datetime.now()
        delta = expires_dt - now

        if delta.total_seconds() < 0:
            return "EXPIRED", "Token expired"

        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)

        if hours > 0:
            time_str = f"{hours}h {minutes}m"
        else:
            time_str = f"{minutes}m"

        return "VALID", f"Expires in {time_str}"

    return "UNKNOWN", "Unable to determine status"

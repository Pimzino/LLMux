"""
Claude usage endpoint - proxies usage data from Anthropic's OAuth API.
"""
import httpx
from fastapi import APIRouter, HTTPException
from oauth import OAuthManager

router = APIRouter()
oauth_manager = OAuthManager()

ANTHROPIC_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"


@router.get("/usage/claude")
async def get_claude_usage():
    """Get Claude usage information when authenticated via OAuth."""
    access_token = await oauth_manager.get_valid_token_async()
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "Not authenticated. Please authenticate via OAuth first."}}
        )

    headers = {
        "authorization": f"Bearer {access_token}",
        "anthropic-beta": "oauth-2025-04-20",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ANTHROPIC_USAGE_URL, headers=headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": {"message": response.text}}
        )

    return response.json()

"""
Pagination utilities supporting opaque pageToken (cursor-based).
This provides a standard interface for paginating collections.
"""

import base64
import json
from typing import Any, List, Optional, Dict, Tuple


class PaginationParams:
    """Parsed pagination parameters."""
    def __init__(self, page_size: int, page_token: Optional[str]):
        self.page_size = page_size
        self.page_token = page_token
        self.offset = self._decode_page_token() if page_token else 0
    
    def _decode_page_token(self) -> int:
        """Decode opaque page token to offset."""
        if not self.page_token:
            return 0
        try:
            decoded = base64.b64decode(self.page_token.encode()).decode()
            data = json.loads(decoded)
            return int(data.get("offset", 0))
        except Exception:
            return 0
    
    @staticmethod
    def encode_page_token(offset: int) -> str:
        """Encode offset into an opaque page token."""
        data = {"offset": offset}
        json_str = json.dumps(data)
        return base64.b64encode(json_str.encode()).decode()


def paginate(
    items: List[Any],
    page_size: int,
    page_token: Optional[str] = None
) -> Tuple[List[Any], Optional[str]]:
    """
    Paginate a list of items.
    
    Returns:
        (items_for_page, next_page_token_or_none)
    """
    params = PaginationParams(page_size, page_token)
    offset = params.offset
    
    # Get the requested page
    page_items = items[offset : offset + page_size]
    
    # Determine if there's a next page
    has_next = (offset + page_size) < len(items)
    next_token = None
    if has_next:
        next_offset = offset + page_size
        next_token = PaginationParams.encode_page_token(next_offset)
    
    return page_items, next_token


def build_pagination_response(
    items: List[Any],
    page_size: int,
    page_token: Optional[str] = None,
    base_url: str = ""
) -> Dict[str, Any]:
    """
    Build a paginated response with HATEOAS links.
    
    Returns:
        {
            "items": [...],
            "pageSize": int,
            "pageToken": optional_token,
            "_links": {
                "self": "...",
                "next": "..." (if has next)
            }
        }
    """
    page_items, next_token = paginate(items, page_size, page_token)
    
    response = {
        "items": page_items,
        "pageSize": page_size,
        "pageToken": page_token,
        "_links": {}
    }
    
    if base_url:
        # Build self link
        self_url = f"{base_url}?pageSize={page_size}"
        if page_token:
            self_url += f"&pageToken={page_token}"
        response["_links"]["self"] = self_url
        
        # Build next link if there's a next page
        if next_token:
            response["_links"]["next"] = f"{base_url}?pageSize={page_size}&pageToken={next_token}"
    
    return response

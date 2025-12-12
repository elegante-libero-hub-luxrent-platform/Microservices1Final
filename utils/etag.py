"""
ETag utilities for conditional request handling (RFC 7232).
Supports If-None-Match (GET/HEAD) and If-Match (POST/PATCH/DELETE).
"""

import hashlib
import json
from typing import Optional, Any


def generate_etag(data: Any) -> str:
    """
    Generate a strong ETag based on JSON representation of data.
    Format: "hash" (without W/ prefix for strong ETags)
    """
    if isinstance(data, dict):
        json_str = json.dumps(data, sort_keys=True, default=str)
    else:
        json_str = json.dumps(data, default=str)
    
    hash_digest = hashlib.sha256(json_str.encode()).hexdigest()
    return f'"{hash_digest}"'


def etag_from_model(model: Any) -> str:
    """
    Generate ETag from a Pydantic model by converting to dict.
    """
    if hasattr(model, "model_dump"):
        data = model.model_dump()
    else:
        data = model.__dict__
    return generate_etag(data)


def parse_etag_header(header: Optional[str]) -> list:
    """
    Parse If-None-Match or If-Match header.
    Returns list of ETags (e.g., ["etag1", "etag2"] or ["*"])
    """
    if not header:
        return []
    
    # Remove spaces and split by comma
    parts = [part.strip() for part in header.split(",")]
    return parts


def should_return_304(if_none_match: Optional[str], current_etag: str) -> bool:
    """
    RFC 7232: If-None-Match for GET/HEAD.
    Return True if should respond with 304 Not Modified.
    """
    if not if_none_match:
        return False
    
    etags = parse_etag_header(if_none_match)
    
    # "*" matches any resource
    if "*" in etags:
        return True
    
    # Check if current ETag matches any in the list
    return current_etag in etags


def should_process_request(if_match: Optional[str], current_etag: str) -> bool:
    """
    RFC 7232: If-Match for POST/PATCH/DELETE.
    Return True if the request should be processed.
    Return False if should respond with 412 Precondition Failed.
    """
    if not if_match:
        # No precondition; allow request
        return True
    
    etags = parse_etag_header(if_match)
    
    # "*" matches if resource exists
    if "*" in etags:
        return True
    
    # Current ETag must match one of the provided ETags
    return current_etag in etags

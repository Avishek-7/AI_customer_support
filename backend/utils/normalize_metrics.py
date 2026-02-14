"""
Prometheus metrics label normalization helpers.
Converts dynamic paths to fixed endpoint names to prevent cardinality explosion.
"""

_PATH_TO_ENDPOINT = {
    # Backend endpoints
    "/chat": "/chat",
    "/chat/stream": "/chat/stream",
    "/health": "/health",
    "/metrics": "/metrics",
    "/conversations": "/conversations",
    "/documents": "/documents",
    "/documents/upload": "/documents/upload",
    "/documents/search": "/documents/search",
    "/vectors": "/vectors",
    "/users": "/users",
    "/auth": "/auth",
    # AI Engine endpoints
    "/query": "/query",
    "/stream": "/stream",
    "/index-document": "/index-document",
    "/update-document": "/update-document",
    "/delete-document": "/delete-document",
    "/inspect-context": "/inspect-context",
    "/critique": "/critique",
    "/regenerate": "/regenerate",
}


def normalize_path_to_endpoint(path: str) -> str:
    """
    Normalize a request path to a fixed endpoint name for metrics labels.
    
    Examples:
        /chat -> /chat
        /conversations/123 -> /conversations
        /documents/456/reindex -> /documents
        /users/789/profile -> /users
    
    Args:
        path: The request path from the URL
    
    Returns:
        A fixed endpoint name suitable for Prometheus labels
    """
    # Handle empty or root-only paths
    if not path or path.strip("/") == "":
        return "/unknown"
    
    # Direct match in mapping
    if path in _PATH_TO_ENDPOINT:
        return _PATH_TO_ENDPOINT[path]
    
    # Extract base path (first two segments)
    parts = path.lstrip("/").split("/")
    if len(parts) >= 2 and parts[1]:
        base = f"/{parts[0]}/{parts[1]}"
        if base in _PATH_TO_ENDPOINT:
            return _PATH_TO_ENDPOINT[base]
    
    # Just the first segment
    if parts and parts[0]:
        base = f"/{parts[0]}"
        if base in _PATH_TO_ENDPOINT:
            return _PATH_TO_ENDPOINT[base]
    
    # Default: return first two segments or first segment
    if len(parts) >= 2 and parts[1]:
        return f"/{parts[0]}/{parts[1]}"
    elif parts and parts[0]:
        return f"/{parts[0]}"
    
    return "/unknown"

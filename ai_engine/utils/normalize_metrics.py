"""
Prometheus metrics label normalization helpers for AI engine.
Converts dynamic paths to fixed endpoint names to prevent cardinality explosion.
"""

_PATH_TO_ENDPOINT = {
    "/": "/",
    "/health": "/health",
    "/metrics": "/metrics",
    "/query": "/query",
    "/stream": "/stream",
    "/index-document": "/index-document",
    "/update-document": "/update-document",
    "/delete-document": "/delete-document",
    "/inspect-context": "/inspect-context",
    "/critique": "/critique",
    "/regenerate": "/regenerate",
    "/debug/document": "/debug/document",
    "/debug/all-documents": "/debug/all-documents",
    "/debug/search-preview": "/debug/search-preview",
}


def normalize_path_to_endpoint(path: str) -> str:
    """
    Normalize a request path to a fixed endpoint name for metrics labels.
    
    Examples:
        /query -> /query
        /delete-document/456 -> /delete-document
        /debug/document/123 -> /debug/document
    
    Args:
        path: The request path from the URL
    
    Returns:
        A fixed endpoint name suitable for Prometheus labels
    """
    # Direct match in mapping
    if path in _PATH_TO_ENDPOINT:
        return _PATH_TO_ENDPOINT[path]
    
    # Extract base path (first two segments for /debug/*, first one for others)
    parts = path.lstrip("/").split("/")
    
    if len(parts) >= 1 and parts[0] == "debug" and len(parts) >= 2:
        # /debug/document/123 -> /debug/document
        base = f"/debug/{parts[1]}"
        if base in _PATH_TO_ENDPOINT:
            return _PATH_TO_ENDPOINT[base]
    
    # Try first segment
    if len(parts) >= 1:
        base = f"/{parts[0]}"
        if base in _PATH_TO_ENDPOINT:
            return _PATH_TO_ENDPOINT[base]
    
    # Fallback: return first two segments if available
    if len(parts) >= 2:
        return f"/{parts[0]}/{parts[1]}"
    elif len(parts) == 1:
        return f"/{parts[0]}"
    
    return "/unknown"

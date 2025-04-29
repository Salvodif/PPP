def normalize_author_for_path(author_name: str) -> str:
    """Normalizes author name for use in file paths."""
    if not author_name:
        return "" # Return empty if author is missing or None
    
    cleaned_name = author_name.strip()
    if cleaned_name.upper() == "AA.VV.":
        return "AAVV"
    else:
        # Remove all dots and return
        return cleaned_name.replace(".", "")
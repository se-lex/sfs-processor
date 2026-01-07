"""
Utility functions for determining doctype (legal document type) for SFS documents.

This module provides functions to classify Swedish legal documents into their
appropriate categories: grundlag (fundamental law), lag (law), or förordning (regulation).
"""

# Sveriges fyra grundlagar med deras SFS-beteckningar
GRUNDLAGAR = {
    '1974:152',    # Regeringsformen (RF)
    '1810:0926',   # Successionsordningen (SO)
    '1949:105',    # Tryckfrihetsförordningen (TF)
    '1991:1469',   # Yttrandefrihetsgrundlagen (YGL)
}


def determine_doctype(beteckning: str, forfattningstyp_namn: str = None) -> str:
    """
    Determine the doctype (legal document type) for an SFS document.

    The function classifies documents into three categories:
    - 'Grundlag': One of Sweden's four fundamental laws
    - 'Lag': Regular laws (förordningar excluded)
    - 'Förordning': Regulations

    Args:
        beteckning: The SFS designation (e.g., "1974:152", "2024:1274")
        forfattningstyp_namn: Optional type name from source data (e.g., "Lag", "Förordning")

    Returns:
        str: One of "Grundlag", "Lag", or "Förordning" (with capital first letter)

    Examples:
        >>> determine_doctype("1974:152", "Lag")
        'Grundlag'
        >>> determine_doctype("2024:1274", "Förordning")
        'Förordning'
        >>> determine_doctype("2010:800", "Lag")
        'Lag'
    """
    # First check if it's one of the fundamental laws
    if beteckning in GRUNDLAGAR:
        return 'Grundlag'

    # If we have explicit type information, use it
    if forfattningstyp_namn:
        # Normalize the type name (case-insensitive matching)
        normalized_type = forfattningstyp_namn.lower()

        if 'förordning' in normalized_type:
            return 'Förordning'
        elif 'lag' in normalized_type:
            return 'Lag'

    # Default fallback: assume it's a law if we can't determine otherwise
    # This is a safe default as most SFS documents are laws
    return 'Lag'


def is_grundlag(beteckning: str) -> bool:
    """
    Check if a document is one of Sweden's four fundamental laws.

    Args:
        beteckning: The SFS designation (e.g., "1974:152")

    Returns:
        bool: True if the document is a grundlag, False otherwise
    """
    return beteckning in GRUNDLAGAR

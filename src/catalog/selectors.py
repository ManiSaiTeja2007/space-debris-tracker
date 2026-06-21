def select_by_name(tles, keyword: str): 
    """
    Select the first TLE whose name contains keyword (case-insensitive).
    """
    key = keyword.lower()
    for name, l1, l2 in tles:
        if key in name.lower():
            return name, l1, l2
    raise ValueError(f"No TLE found for keyword '{keyword}'")


from pathlib import Path
from typing import List, Tuple


def read_tles(tle_path: Path) -> List[Tuple[str, str, str]]:
    """
    Returns list of (name, line1, line2).
    """
    lines = [l.strip() for l in tle_path.read_text().splitlines() if l.strip()]
    out = []
    for i in range(0, len(lines), 3):
        if i + 2 < len(lines):
            out.append((lines[i], lines[i + 1], lines[i + 2]))
    return out

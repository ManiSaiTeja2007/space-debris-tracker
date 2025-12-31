from pathlib import Path 
import requests # ignore: F401

CELESTRAK_ACTIVE = (
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
)

def fetch_active_tles(cache_dir: Path) -> Path:
    """
    Download Active Satellites TLEs from CelesTrak.
    Cached locally to be polite and reproducible.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    tle_path = cache_dir / "active.tle"

    if tle_path.exists():
        return tle_path

    r = requests.get(CELESTRAK_ACTIVE, timeout=15)
    r.raise_for_status()
    tle_path.write_text(r.text)
    return tle_path


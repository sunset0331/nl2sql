"""
Download Spider Dataset

Downloads the Spider benchmark dataset directly from the official GitHub repository.
"""

import os
import urllib.request
from pathlib import Path


# Official Spider dataset URLs from GitHub
SPIDER_DEV_URL = "https://raw.githubusercontent.com/taoyds/spider/master/evaluation_examples/examples/dev.json"
SPIDER_TABLES_URL = "https://raw.githubusercontent.com/taoyds/spider/master/evaluation_examples/examples/tables.json"


def download_file(url: str, output_path: Path) -> bool:
    """Download a file from URL."""
    try:
        print(f"Downloading: {url}")
        urllib.request.urlretrieve(url, output_path)
        size_kb = output_path.stat().st_size / 1024
        print(f"  [OK] Saved: {output_path.name} ({size_kb:.1f} KB)")
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def main():
    """Download Spider dataset files."""
    # Setup output directory
    script_dir = Path(__file__).parent
    output_dir = script_dir / "spider"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 50)
    print("Spider Dataset Download")
    print("=" * 50 + "\n")
    
    # Download files
    dev_path = output_dir / "dev.json"
    tables_path = output_dir / "tables.json"
    
    success = True
    success &= download_file(SPIDER_DEV_URL, dev_path)
    success &= download_file(SPIDER_TABLES_URL, tables_path)
    
    if success:
        # Verify downloads
        import json
        with open(dev_path) as f:
            dev_count = len(json.load(f))
        with open(tables_path) as f:
            tables_count = len(json.load(f))
        
        print("\n" + "=" * 50)
        print("Download Complete!")
        print(f"  - dev.json: {dev_count} examples")
        print(f"  - tables.json: {tables_count} database schemas")
        print("=" * 50 + "\n")
    else:
        print("\n[ERROR] Download failed. Please check your internet connection.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

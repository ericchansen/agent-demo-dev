#!/usr/bin/env python3
"""Download Wide World Importers DW Parquet files for the Fabric Sales Agent demo.

Source: Microsoft Fabric tutorial sample data (public Azure Blob Storage).
Downloads Parquet files locally, with optional future support for direct
Lakehouse upload via the Fabric SDK.

Usage:
    python demo/load-wwi-data.py
    python demo/load-wwi-data.py --output-dir demo/sample-data
    python demo/load-wwi-data.py --workspace-id <guid> --lakehouse-id <guid>
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://fabrictutorialdata.blob.core.windows.net/sampledata/WideWorldImportersDW/parquet"

TABLES: list[str] = [
    "fact_Sale",
    "fact_Order",
    "fact_Purchase",
    "fact_Transaction",
    "fact_Movement",
    "fact_Stock_Holding",
    "dimension_Customer",
    "dimension_Stock_Item",
    "dimension_City",
    "dimension_Employee",
    "dimension_Date",
    "dimension_Supplier",
    "dimension_Payment_Method",
    "dimension_Transaction_Type",
]


def _sizeof_fmt(num_bytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:,.1f} {unit}"
        num_bytes /= 1024  # type: ignore[assignment]
    return f"{num_bytes:,.1f} TB"


def download_table(table: str, output_dir: Path, *, retries: int = 3) -> Path:
    """Download a single Parquet table with retry logic and progress reporting."""
    # WWI tutorial data uses: <base>/<table>/part-00000-<hash>.c000.snappy.parquet
    # but also works with just <base>/<table>.parquet for the consolidated files.
    # Try the directory-style path first, then fall back to flat file.
    urls_to_try = [
        f"{BASE_URL}/{table}/{table}.parquet",
        f"{BASE_URL}/{table}.parquet",
    ]

    dest = output_dir / f"{table}.parquet"
    if dest.exists():
        print(f"  ✓ {table} — already exists ({_sizeof_fmt(dest.stat().st_size)})")
        return dest

    last_error: Exception | None = None
    for url in urls_to_try:
        for attempt in range(1, retries + 1):
            try:
                print(f"  ↓ {table} (attempt {attempt}/{retries}) …", end="", flush=True)
                t0 = time.monotonic()
                urllib.request.urlretrieve(url, dest)  # noqa: S310
                elapsed = time.monotonic() - t0
                size = dest.stat().st_size
                print(f" {_sizeof_fmt(size)} in {elapsed:.1f}s")
                return dest
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code == 404:
                    print(" 404 — trying next URL pattern")
                    break  # skip remaining retries for this URL
                print(f" HTTP {exc.code} — retrying")
            except urllib.error.URLError as exc:
                last_error = exc
                print(f" network error — retrying ({exc.reason})")
            except OSError as exc:
                last_error = exc
                print(f" I/O error — retrying ({exc})")
            time.sleep(2**attempt)  # exponential back-off

    raise RuntimeError(f"Failed to download {table} after trying all URL patterns") from last_error


def download_all(output_dir: Path) -> list[Path]:
    """Download every WWI table, returning paths of successfully downloaded files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nDownloading {len(TABLES)} tables to {output_dir.resolve()}\n")

    downloaded: list[Path] = []
    errors: list[str] = []

    for table in TABLES:
        try:
            path = download_table(table, output_dir)
            downloaded.append(path)
        except RuntimeError as exc:
            errors.append(f"  ✗ {table}: {exc}")
            print(f"  ✗ {table} — FAILED")

    print(f"\n{'─' * 50}")
    print(f"Downloaded: {len(downloaded)}/{len(TABLES)}")
    total_bytes = sum(p.stat().st_size for p in downloaded)
    print(f"Total size: {_sizeof_fmt(total_bytes)}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(e)

    # Copy custom CSV seed-data tables (e.g., quota targets)
    csv_files = copy_custom_csv_tables(output_dir)
    downloaded.extend(csv_files)

    return downloaded


CUSTOM_CSV_TABLES: list[str] = [
    "quota_Target",
]


def copy_custom_csv_tables(output_dir: Path) -> list[Path]:
    """Copy custom CSV seed-data tables into the output directory."""
    sample_dir = Path(__file__).parent / "sample-data"
    copied: list[Path] = []
    for table in CUSTOM_CSV_TABLES:
        src = sample_dir / f"{table}.csv"
        dest = output_dir / f"{table}.csv"
        if not src.exists():
            print(f"  ⚠ {table}.csv not found in {sample_dir}")
            continue
        if dest.exists():
            print(f"  ✓ {table}.csv — already exists")
        else:
            import shutil

            shutil.copy2(src, dest)
            print(f"  ✓ {table}.csv — copied ({_sizeof_fmt(dest.stat().st_size)})")
        copied.append(dest)
    return copied


def print_upload_instructions(output_dir: Path) -> None:
    """Print manual upload instructions for Fabric Lakehouse."""
    print(
        f"""
╔══════════════════════════════════════════════════════════════╗
║  Manual Upload to Microsoft Fabric Lakehouse                ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. Open your Fabric workspace in the browser                ║
║  2. Navigate to your Lakehouse → Files section               ║
║  3. Click "Upload" → "Upload files"                          ║
║  4. Select all .parquet files from:                          ║
║     {str(output_dir.resolve()):<56s} ║
║  5. Once uploaded, right-click each file →                   ║
║     "Load to Tables" to create Delta tables                  ║
║                                                              ║
║  Alternatively, use a Fabric Notebook:                       ║
║                                                              ║
║    import shutil                                             ║
║    tables = {TABLES!r:.46s}║
║    for t in tables:                                          ║
║        src = f"/lakehouse/default/Files/{{t}}.parquet"       ║
║        df = spark.read.parquet(src)                          ║
║        df.write.mode("overwrite")                            ║
║          .format("delta")                                    ║
║          .saveAsTable(t)                                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝"""
    )


def try_fabric_upload(workspace_id: str, lakehouse_id: str, parquet_files: list[Path]) -> bool:
    """Attempt to upload files via the Fabric SDK. Returns True on success."""
    try:
        from sempy import fabric  # type: ignore[import-untyped]

        client = fabric.FabricRestClient()
        print(f"\nUploading to workspace={workspace_id}, lakehouse={lakehouse_id} …")

        for path in parquet_files:
            table_name = path.stem
            print(f"  ↑ {table_name} …", end="", flush=True)
            with open(path, "rb"):
                response = client.post(
                    f"/v1/workspaces/{workspace_id}/lakehouses/{lakehouse_id}/tables/{table_name}/load",
                    json={
                        "relativePath": f"Files/{path.name}",
                        "pathType": "File",
                        "mode": "Overwrite",
                    },
                )
                if response.status_code < 300:
                    print(" ✓")
                else:
                    print(f" HTTP {response.status_code}")
        return True

    except ImportError:
        print("\n⚠  sempy (Fabric SDK) not installed — skipping direct upload.")
        print("   Install with: pip install semantic-link")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"\n⚠  Fabric SDK upload failed: {exc}")
        return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Wide World Importers DW sample data for Fabric demo")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("demo/sample-data"),
        help="Local directory for downloaded Parquet files (default: demo/sample-data)",
    )
    parser.add_argument(
        "--workspace-id",
        default=None,
        help="Fabric workspace GUID (optional — enables direct Lakehouse upload)",
    )
    parser.add_argument(
        "--lakehouse-id",
        default=None,
        help="Fabric Lakehouse GUID (optional — enables direct Lakehouse upload)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download, only attempt Fabric upload of existing files",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    print("=" * 55)
    print("  Wide World Importers DW — Sample Data Loader")
    print("=" * 55)

    if args.skip_download:
        parquet_files = list(args.output_dir.glob("*.parquet"))
        csv_files = copy_custom_csv_tables(args.output_dir)
        parquet_files.extend(csv_files)
        if not parquet_files:
            print(f"No data files found in {args.output_dir}")
            return 1
        print(f"Found {len(parquet_files)} existing data files")
    else:
        parquet_files = download_all(args.output_dir)
        if not parquet_files:
            print("No files were downloaded. Check your network connection.")
            return 1

    # Attempt Fabric SDK upload if IDs provided
    if args.workspace_id and args.lakehouse_id:
        uploaded = try_fabric_upload(args.workspace_id, args.lakehouse_id, parquet_files)
        if uploaded:
            print("\n✓ Data uploaded to Fabric Lakehouse successfully!")
            return 0

    # Fall back to manual instructions
    print_upload_instructions(args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

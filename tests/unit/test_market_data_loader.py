"""Unit tests for the SEC EDGAR market data loader."""

from __future__ import annotations

import importlib.util
import io
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

_LOADER_PATH = Path(__file__).resolve().parents[2] / "demo" / "load-market-data.py"


def _import_loader():
    """Import the loader module from its file path."""
    spec = importlib.util.spec_from_file_location("load_market_data", _LOADER_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def loader():
    """Load the market data loader module once per test module."""
    pytest.importorskip("pandas")
    return _import_loader()


# ---------------------------------------------------------------------------
# GAAP tag normalization
# ---------------------------------------------------------------------------


class TestGAAPTagNormalization:
    """Test that GAAP tags are correctly mapped to normalized columns."""

    def test_revenue_tags_mapped(self, loader):
        """All revenue tag variants should map to 'revenue' column."""
        for tag in loader._GAAP_TAG_MAP["revenue"]:
            col, _pri = loader._TAG_PRIORITY[tag]
            assert col == "revenue", f"{tag} should map to 'revenue', got '{col}'"

    def test_net_income_tags_mapped(self, loader):
        """All net income tag variants should map to 'net_income' column."""
        for tag in loader._GAAP_TAG_MAP["net_income"]:
            col, _pri = loader._TAG_PRIORITY[tag]
            assert col == "net_income", f"{tag} should map to 'net_income', got '{col}'"

    def test_total_assets_tags_mapped(self, loader):
        """All total assets tag variants should map to 'total_assets' column."""
        for tag in loader._GAAP_TAG_MAP["total_assets"]:
            col, _pri = loader._TAG_PRIORITY[tag]
            assert col == "total_assets", f"{tag} should map to 'total_assets', got '{col}'"

    def test_priority_ordering(self, loader):
        """Earlier tags in each list should have lower priority numbers (= higher precedence)."""
        for col_name, tags in loader._GAAP_TAG_MAP.items():
            for i, tag in enumerate(tags):
                _, pri = loader._TAG_PRIORITY[tag]
                assert pri == i, f"{tag} should have priority {i}, got {pri}"

    def test_all_tags_in_frozen_set(self, loader):
        """Every tag in the map should be in _ALL_TAGS."""
        for tags in loader._GAAP_TAG_MAP.values():
            for tag in tags:
                assert tag in loader._ALL_TAGS


# ---------------------------------------------------------------------------
# Company list loading
# ---------------------------------------------------------------------------


class TestCompanyListLoading:
    """Test the company CSV loading function."""

    def test_load_from_repo_csv(self, loader, tmp_path):
        """Load the actual repo companies.csv."""
        csv_path = Path(__file__).resolve().parents[2] / "demo" / "market-data" / "companies.csv"
        if not csv_path.exists():
            pytest.skip("companies.csv not found")

        company_map = loader._load_company_list(csv_path)
        assert len(company_map) >= 40, f"Expected 40+ companies, got {len(company_map)}"

        # Check a well-known company.
        msft_cik = 789019
        if msft_cik in company_map:
            assert company_map[msft_cik]["ticker"] == "MSFT"
            assert "Microsoft" in company_map[msft_cik]["company_name"]

    def test_load_custom_csv(self, loader, tmp_path):
        """Load a minimal custom CSV."""
        csv_path = tmp_path / "test_companies.csv"
        csv_path.write_text(
            "cik,ticker,company_name,sic_code,industry\n12345,TEST,Test Corp,7372,Software & Services\n"
        )
        company_map = loader._load_company_list(csv_path)
        assert 12345 in company_map
        assert company_map[12345]["ticker"] == "TEST"


# ---------------------------------------------------------------------------
# SEC URL construction
# ---------------------------------------------------------------------------


class TestSECURLConstruction:
    """Test that SEC EDGAR URLs are constructed correctly."""

    def test_url_format(self, loader):
        """URL should follow SEC EDGAR quarterly data set pattern."""
        url = f"{loader._EDGAR_BASE}/2024q4.zip"
        assert url == "https://www.sec.gov/files/dera/data/financial-statement-data-sets/2024q4.zip"

    def test_user_agent_set(self, loader):
        """SEC requires a descriptive User-Agent header."""
        assert "FabricSalesAgentAccelerator" in loader._USER_AGENT
        assert "https://" in loader._USER_AGENT


# ---------------------------------------------------------------------------
# Parse and normalize (with synthetic data)
# ---------------------------------------------------------------------------


class TestParseAndNormalize:
    """Test the parse-and-normalize pipeline with synthetic EDGAR data."""

    def _make_test_zip(self) -> bytes:
        """Create a minimal EDGAR-format ZIP with sub.txt and num.txt."""
        sub_data = (
            "adsh\tcik\tname\tform\tfy\tfp\tfiled\n"
            "0001-24-000001\t789019\tMICROSOFT CORP\t10-K\t2024\tFY\t20240730\n"
            "0001-24-000002\t320193\tAPPLE INC\t10-K\t2024\tFY\t20241101\n"
            "0001-24-000003\t99999\tUNKNOWN CORP\t10-K\t2024\tFY\t20241201\n"
        )
        num_data = (
            "adsh\ttag\tversion\tddate\tqtrs\tuom\tvalue\n"
            "0001-24-000001\tRevenues\tus-gaap/2024\t20240630\t4\tUSD\t245122000000\n"
            "0001-24-000001\tNetIncomeLoss\tus-gaap/2024\t20240630\t4\tUSD\t88136000000\n"
            "0001-24-000001\tAssets\tus-gaap/2024\t20240630\t0\tUSD\t512163000000\n"
            "0001-24-000002\tRevenueFromContractWithCustomerExcludingAssessedTax\tus-gaap/2024\t20240928\t4\tUSD\t391035000000\n"
            "0001-24-000002\tNetIncomeLoss\tus-gaap/2024\t20240928\t4\tUSD\t93736000000\n"
            "0001-24-000003\tRevenues\tus-gaap/2024\t20241231\t4\tUSD\t1000000\n"
        )

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("sub.txt", sub_data)
            zf.writestr("num.txt", num_data)
        return buf.getvalue()

    def test_filters_to_known_companies(self, loader):
        """Only companies in the company_map should appear in output."""
        company_map = {
            789019: {"ticker": "MSFT", "company_name": "Microsoft", "sic_code": "7372", "industry": "Software"},
            320193: {"ticker": "AAPL", "company_name": "Apple", "sic_code": "3571", "industry": "Hardware"},
        }

        df = loader._parse_and_normalize(self._make_test_zip(), company_map)
        ciks_in_result = set(df["cik"].unique())

        # CIK 99999 (UNKNOWN CORP) should be filtered out.
        assert 99999 not in ciks_in_result
        assert 789019 in ciks_in_result
        assert 320193 in ciks_in_result

    def test_gaap_normalization_output_columns(self, loader):
        """Output should have normalized revenue, net_income, total_assets columns."""
        company_map = {
            789019: {"ticker": "MSFT", "company_name": "Microsoft", "sic_code": "7372", "industry": "Software"},
            320193: {"ticker": "AAPL", "company_name": "Apple", "sic_code": "3571", "industry": "Hardware"},
        }

        df = loader._parse_and_normalize(self._make_test_zip(), company_map)
        assert "revenue" in df.columns
        assert "net_income" in df.columns
        assert "total_assets" in df.columns

    def test_company_metadata_enriched(self, loader):
        """Output rows should include ticker, company_name from the company map."""
        company_map = {
            789019: {"ticker": "MSFT", "company_name": "Microsoft", "sic_code": "7372", "industry": "Software"},
        }

        df = loader._parse_and_normalize(self._make_test_zip(), company_map)
        msft_rows = df[df["cik"] == 789019]
        assert len(msft_rows) > 0
        assert msft_rows.iloc[0]["ticker"] == "MSFT"
        assert msft_rows.iloc[0]["company_name"] == "Microsoft"

    def test_revenue_value_correct(self, loader):
        """Microsoft's revenue should match the synthetic test data."""
        company_map = {
            789019: {"ticker": "MSFT", "company_name": "Microsoft", "sic_code": "7372", "industry": "Software"},
        }

        df = loader._parse_and_normalize(self._make_test_zip(), company_map)
        msft = df[df["cik"] == 789019].iloc[0]
        assert msft["revenue"] == 245122000000.0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Test error handling in the download function."""

    def test_404_raises_clear_error(self, loader):
        """404 from SEC should raise RuntimeError with helpful message."""
        import urllib.error

        def fake_urlopen(*args, **kwargs):
            raise urllib.error.HTTPError(
                url="https://sec.gov/fake.zip",
                code=404,
                msg="Not Found",
                hdrs=None,  # type: ignore[arg-type]
                fp=None,
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with pytest.raises(RuntimeError, match="not found"):
                loader._download_edgar_zip("9999q9")

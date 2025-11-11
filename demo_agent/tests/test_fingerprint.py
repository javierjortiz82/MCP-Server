"""Unit tests for client fingerprinting and abuse detection.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""

import pytest

from demo_agent.security.fingerprint import FingerprintAnalyzer


@pytest.fixture
def analyzer():
    """Create FingerprintAnalyzer instance."""
    return FingerprintAnalyzer()


def test_generate_fingerprint_basic(analyzer):
    """Test basic fingerprint generation."""
    fp = analyzer.generate_fingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        ip_address="203.0.113.42",
    )

    assert len(fp) == 64  # SHA256 hex is 64 chars
    assert isinstance(fp, str)


def test_generate_fingerprint_consistency(analyzer):
    """Test fingerprint consistency for same input."""
    fp1 = analyzer.generate_fingerprint(
        user_agent="Mozilla/5.0", ip_address="203.0.113.42"
    )
    fp2 = analyzer.generate_fingerprint(
        user_agent="Mozilla/5.0", ip_address="203.0.113.42"
    )

    assert fp1 == fp2


def test_generate_fingerprint_different_input(analyzer):
    """Test different fingerprints for different inputs."""
    fp1 = analyzer.generate_fingerprint(
        user_agent="Mozilla/5.0", ip_address="203.0.113.42"
    )
    fp2 = analyzer.generate_fingerprint(
        user_agent="Chrome/90", ip_address="203.0.113.42"
    )

    assert fp1 != fp2


def test_generate_fingerprint_with_all_fields(analyzer):
    """Test fingerprint with all optional fields."""
    fp = analyzer.generate_fingerprint(
        user_agent="Mozilla/5.0",
        ip_address="203.0.113.42",
        language="en-US",
        timezone="America/New_York",
        canvas_hash="abc123",
    )

    assert len(fp) == 64


def test_analyze_user_agent_legitimate_browser(analyzer):
    """Test legitimate browser detection."""
    browsers = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/91.0",
    ]

    for ua in browsers:
        score = analyzer._analyze_user_agent(ua)
        assert score == 0.0, f"Expected 0.0 for {ua}, got {score}"


def test_analyze_user_agent_automation(analyzer):
    """Test automation tool detection."""
    automation_uas = [
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/91.0 Headless",
        "Mozilla/5.0 PhantomJS/2.1.1",
        "Mozilla/5.0 Selenium/3.141.0",
        "Mozilla/5.0 Puppeteer/v5.5.0",
        "Mozilla/5.0 Playwright/1.3.0",
    ]

    for ua in automation_uas:
        score = analyzer._analyze_user_agent(ua)
        assert score >= 0.7, f"Expected high score for {ua}, got {score}"


def test_analyze_user_agent_vpn(analyzer):
    """Test VPN/proxy detection."""
    vpn_uas = [
        "Mozilla/5.0 VPN Client",
        "Mozilla/5.0 Proxy Server",
        "Mozilla/5.0 TorProject",
        "Mozilla/5.0 AnonymousBrowser",
    ]

    for ua in vpn_uas:
        score = analyzer._analyze_user_agent(ua)
        assert 0.4 <= score <= 0.6, f"Expected VPN score for {ua}, got {score}"


def test_analyze_user_agent_missing(analyzer):
    """Test handling of missing user-agent."""
    score = analyzer._analyze_user_agent("")
    assert 0.0 <= score <= 0.2


def test_analyze_request_rate_normal(analyzer):
    """Test normal request rates."""
    # 0-0.5 req/min = legitimate
    rate_scores = [
        (0.0, 0.0),
        (0.25, 0.0),
        (0.5, 0.0),
    ]

    for rate, expected_score in rate_scores:
        score = analyzer._analyze_request_rate(rate)
        assert (
            score == expected_score
        ), f"Rate {rate}: expected {expected_score}, got {score}"


def test_analyze_request_rate_suspicious(analyzer):
    """Test suspicious request rates."""
    # 5+ req/min = suspicious to abusive
    rate_scores = [
        (5.0, 0.3),  # 5 req/min
        (10.0, 0.6),  # 10 req/min
        (50.0, 1.0),  # 50 req/min
    ]

    for rate, expected_max_score in rate_scores:
        score = analyzer._analyze_request_rate(rate)
        assert score >= 0.3, f"Rate {rate}: expected high score, got {score}"


def test_analyze_ip_rotation_consistent(analyzer):
    """Test consistent IP (no rotation)."""
    current_ip = "203.0.113.42"
    previous_ips = ["203.0.113.42"] * 10

    score = analyzer._analyze_ip_rotation(current_ip, previous_ips)
    assert score == 0.0  # Consistent = no suspicion


def test_analyze_ip_rotation_minor_variation(analyzer):
    """Test minor IP variation."""
    current_ip = "203.0.113.42"
    previous_ips = ["203.0.113.42"] * 19 + ["203.0.113.43"]

    score = analyzer._analyze_ip_rotation(current_ip, previous_ips)
    assert 0.0 <= score <= 0.2  # Minor variation = low suspicion


def test_analyze_ip_rotation_significant(analyzer):
    """Test significant IP rotation (VPN)."""
    current_ip = "203.0.113.42"
    previous_ips = [f"203.0.113.{i}" for i in range(10)]

    score = analyzer._analyze_ip_rotation(current_ip, previous_ips)
    assert score >= 0.6  # Significant rotation = high suspicion


def test_analyze_ip_rotation_complete_rotation(analyzer):
    """Test complete IP rotation (every request different)."""
    current_ip = "203.0.113.100"
    previous_ips = [f"203.0.113.{i}" for i in range(50)]

    score = analyzer._analyze_ip_rotation(current_ip, previous_ips)
    assert score >= 0.8  # Complete rotation = very suspicious


def test_analyze_fingerprint_consistency_consistent(analyzer):
    """Test consistent device fingerprint."""
    current_fp = "abcdef123456"
    previous_fps = ["abcdef123456"] * 10

    score = analyzer._analyze_fingerprint_consistency(current_fp, previous_fps)
    assert score == 0.0  # Fully consistent = no suspicion


def test_analyze_fingerprint_consistency_partial(analyzer):
    """Test partial fingerprint consistency."""
    current_fp = "abcdef123456"
    previous_fps = ["abcdef123456"] * 7 + ["different123"] * 3

    score = analyzer._analyze_fingerprint_consistency(current_fp, previous_fps)
    assert 0.0 <= score <= 0.2  # 70% consistent = low suspicion


def test_analyze_fingerprint_consistency_high_inconsistency(analyzer):
    """Test high fingerprint inconsistency."""
    current_fp = "abcdef123456"
    previous_fps = [f"fingerprint{i}" for i in range(10)]

    score = analyzer._analyze_fingerprint_consistency(current_fp, previous_fps)
    assert score >= 0.5  # Highly inconsistent = suspicious


def test_compute_abuse_score_legitimate(analyzer):
    """Test abuse score for legitimate user."""
    score = analyzer.compute_abuse_score(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0",
        ip_address="203.0.113.42",
        request_rate=0.5,
        ip_reputation=0.0,
        tokens_consumed=500,
        max_tokens=5000,
    )

    assert 0.0 <= score <= 0.2, f"Expected low score for legitimate user, got {score}"


def test_compute_abuse_score_suspicious(analyzer):
    """Test abuse score for suspicious user."""
    score = analyzer.compute_abuse_score(
        user_agent="Mozilla/5.0 Headless",
        ip_address="203.0.113.42",
        request_rate=10.0,
        ip_reputation=0.8,
        tokens_consumed=4500,
        max_tokens=5000,
        previous_ips=["203.0.113.1", "203.0.113.2", "203.0.113.3"],
    )

    assert score >= 0.5, f"Expected high score for suspicious user, got {score}"


def test_compute_abuse_score_likely_bot(analyzer):
    """Test abuse score for likely bot."""
    score = analyzer.compute_abuse_score(
        user_agent="Mozilla/5.0 Selenium",
        ip_address="203.0.113.42",
        request_rate=50.0,
        ip_reputation=0.9,
        tokens_consumed=4950,
        max_tokens=5000,
        previous_ips=[f"203.0.113.{i}" for i in range(20)],
    )

    assert score >= 0.7, f"Expected very high score for bot, got {score}"


def test_is_likely_vpn_with_vpn_ua(analyzer):
    """Test VPN detection with VPN in user-agent."""
    is_vpn = analyzer.is_likely_vpn(
        user_agent="Mozilla/5.0 VPN Client", ip_address="203.0.113.42"
    )

    assert is_vpn is True


def test_is_likely_vpn_with_ip_rotation(analyzer):
    """Test VPN detection with IP rotation."""
    is_vpn = analyzer.is_likely_vpn(
        user_agent="Mozilla/5.0 Chrome/91.0",
        ip_address="203.0.113.42",
        previous_ips=[f"203.0.113.{i}" for i in range(50)],
    )

    assert is_vpn is True


def test_is_likely_vpn_legitimate(analyzer):
    """Test VPN detection for legitimate user."""
    is_vpn = analyzer.is_likely_vpn(
        user_agent="Mozilla/5.0 Chrome/91.0",
        ip_address="203.0.113.42",
        previous_ips=["203.0.113.42"] * 10,
    )

    assert is_vpn is False


def test_get_fingerprint_summary_low_risk(analyzer):
    """Test fingerprint summary for low-risk user."""
    summary = analyzer.get_fingerprint_summary(fingerprint="abc123", abuse_score=0.2)

    assert summary["fingerprint"] == "abc123"
    assert summary["abuse_score"] == 0.2
    assert summary["risk_level"] == "low"
    assert summary["recommendation"] == "Allow"


def test_get_fingerprint_summary_medium_risk(analyzer):
    """Test fingerprint summary for medium-risk user."""
    summary = analyzer.get_fingerprint_summary(fingerprint="def456", abuse_score=0.5)

    assert summary["risk_level"] == "medium"
    assert summary["recommendation"] == "Require CAPTCHA"


def test_get_fingerprint_summary_high_risk(analyzer):
    """Test fingerprint summary for high-risk user."""
    summary = analyzer.get_fingerprint_summary(fingerprint="ghi789", abuse_score=0.8)

    assert summary["risk_level"] == "high"
    assert summary["recommendation"] == "Block"


def test_abuse_score_capped_at_one(analyzer):
    """Test abuse score is capped at 1.0."""
    score = analyzer.compute_abuse_score(
        user_agent="Mozilla/5.0 Headless",
        ip_address="203.0.113.42",
        request_rate=100.0,
        ip_reputation=1.0,
        tokens_consumed=5000,
        max_tokens=5000,
    )

    assert score <= 1.0

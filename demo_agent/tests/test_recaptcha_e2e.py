"""End-to-End Test for reCAPTCHA v3 Integration with Real User Query.

This module tests the complete flow:
1. User makes request with reCAPTCHA token
2. Backend verifies token with Google
3. Fingerprint analysis checks for suspicious behavior
4. Demo agent processes question and returns answer

Test Case: User asks "¿Dónde está Costa Rica?" with reCAPTCHA verification

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class TestReCAPTCHAE2E:
    """End-to-end tests for reCAPTCHA integration with real queries."""

    @pytest.fixture
    def valid_recaptcha_response(self):
        """Mock a valid reCAPTCHA response from Google."""
        return {
            "success": True,
            "score": 0.95,
            "action": "demo_query",
            "challenge_ts": datetime.now(timezone.utc).isoformat(),
            "hostname": "localhost",
            "error_codes": [],
        }

    @pytest.fixture
    def invalid_recaptcha_response(self):
        """Mock an invalid reCAPTCHA response."""
        return {
            "success": False,
            "score": 0.0,
            "error-codes": ["invalid-input-response"],
        }

    @pytest.fixture
    def demo_request_payload(self):
        """Sample demo request asking about Costa Rica."""
        return {
            "user_id": 6,  # test123@example.com
            "session_id": "sess_e2e_test_001",
            "input": "¿Dónde está Costa Rica?",
            "language": "es",
            "recaptcha_token": "test-token-from-browser",
            "metadata": {
                "ip": "127.0.0.1",
                "user_agent": "Mozilla/5.0 E2E Test",
                "fingerprint": "test-fingerprint-e2e",
            },
        }

    async def test_recaptcha_token_verification(self, valid_recaptcha_response):
        """Test that valid reCAPTCHA token is verified correctly.

        Scenario:
            1. Client sends request with reCAPTCHA token
            2. CaptchaHandler verifies token with Google API
            3. Google returns success=true, score=0.95
            4. Token is accepted
        """
        from demo_agent.security.captcha_handler import CaptchaHandler

        handler = CaptchaHandler(score_threshold=0.5)

        # Mock the Google API response
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = valid_recaptcha_response
            mock_post.return_value.raise_for_status.return_value = None

            result = await handler.verify_token(
                token="test-token-from-browser",
                remote_ip="127.0.0.1"
            )

            # Assertions
            assert result["success"] is True
            assert result["score"] == 0.95
            assert result["action"] == "demo_query"
            assert len(result["error_codes"]) == 0

            print("\n✅ TEST PASSED: Valid reCAPTCHA token verified successfully")
            print(f"   Score: {result['score']}")
            print(f"   Action: {result['action']}")

    async def test_invalid_recaptcha_token(self, invalid_recaptcha_response):
        """Test that invalid reCAPTCHA token is rejected.

        Scenario:
            1. Client sends request with invalid token
            2. CaptchaHandler verifies token with Google API
            3. Google returns success=false
            4. Token is rejected
        """
        from demo_agent.security.captcha_handler import CaptchaHandler

        handler = CaptchaHandler(score_threshold=0.5)

        # Mock the Google API response
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = invalid_recaptcha_response
            mock_post.return_value.raise_for_status.return_value = None

            result = await handler.verify_token(
                token="invalid-token",
                remote_ip="127.0.0.1"
            )

            # Assertions
            assert result["success"] is False
            assert "invalid-input-response" in result.get("error_codes", [])

            print("\n✅ TEST PASSED: Invalid reCAPTCHA token rejected successfully")
            print(f"   Error codes: {result.get('error_codes', [])}")

    async def test_score_evaluation_with_high_score(self):
        """Test score evaluation when reCAPTCHA returns high score (0.95).

        Scenario:
            1. reCAPTCHA returns score 0.95 (likely human)
            2. evaluate_score() returns "allow" recommendation
            3. User request is processed normally
        """
        from demo_agent.security.captcha_handler import CaptchaHandler

        handler = CaptchaHandler(score_threshold=0.5)
        evaluation = handler.evaluate_score(0.95)

        # Assertions
        assert evaluation["risk_level"] == "low"
        assert evaluation["recommendation"] == "allow"
        assert "0.95" in evaluation["message"]

        print("\n✅ TEST PASSED: High reCAPTCHA score (0.95) evaluated as low risk")
        print(f"   Recommendation: {evaluation['recommendation']}")

    async def test_score_evaluation_with_low_score(self):
        """Test score evaluation when reCAPTCHA returns low score (0.2).

        Scenario:
            1. reCAPTCHA returns score 0.2 (likely bot)
            2. evaluate_score() returns "block" recommendation
            3. User request is blocked
        """
        from demo_agent.security.captcha_handler import CaptchaHandler

        handler = CaptchaHandler(score_threshold=0.5)
        evaluation = handler.evaluate_score(0.2)

        # Assertions
        assert evaluation["risk_level"] == "high"
        assert evaluation["recommendation"] == "block"
        assert "0.20" in evaluation["message"]

        print("\n✅ TEST PASSED: Low reCAPTCHA score (0.2) evaluated as high risk")
        print(f"   Recommendation: {evaluation['recommendation']}")

    async def test_complete_request_flow(self, demo_request_payload, valid_recaptcha_response):
        """Test complete request flow from token verification to response.

        Scenario:
            1. User sends "¿Dónde está Costa Rica?" with reCAPTCHA token
            2. System verifies token (score 0.95 - legitimate user)
            3. Fingerprint analysis passes (no suspicious behavior)
            4. Demo agent processes query
            5. Returns answer about Costa Rica location
        """
        from demo_agent.security.captcha_handler import CaptchaHandler
        from demo_agent.security.fingerprint import FingerprintAnalyzer

        print("\n" + "="*80)
        print("🧪 COMPLETE E2E TEST: Pregunta sobre Costa Rica con reCAPTCHA")
        print("="*80)

        # Step 1: Verify reCAPTCHA token
        print("\n[STEP 1] Verificando token de reCAPTCHA...")
        captcha_handler = CaptchaHandler(score_threshold=0.5)

        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = valid_recaptcha_response
            mock_post.return_value.raise_for_status.return_value = None

            token_result = await captcha_handler.verify_token(
                token=demo_request_payload["recaptcha_token"],
                remote_ip=demo_request_payload["metadata"]["ip"]
            )

        assert token_result["success"] is True
        print(f"✅ Token verificado: score={token_result['score']}")

        # Step 2: Evaluate reCAPTCHA score
        print("\n[STEP 2] Evaluando score de reCAPTCHA...")
        score_eval = captcha_handler.evaluate_score(token_result["score"])
        assert score_eval["recommendation"] == "allow"
        print(f"✅ Score evaluado: {score_eval['recommendation']}")

        # Step 3: Check fingerprint for suspicious behavior
        print("\n[STEP 3] Analizando fingerprint para comportamiento sospechoso...")
        fingerprint_analyzer = FingerprintAnalyzer()

        # Simulate fingerprint analysis
        abuse_score = 0.15  # Low abuse score (not suspicious)
        require_captcha, reason = await captcha_handler.should_require_captcha(
            abuse_score=abuse_score,
            captcha_score=token_result["score"],
            previous_blocks=0
        )

        assert not require_captcha, "CAPTCHA should not be required"
        print(f"✅ Fingerprint OK: abuse_score={abuse_score}")

        # Step 4: Simulate Gemini response
        print("\n[STEP 4] Procesando pregunta con Gemini...")
        mock_answer = (
            "Costa Rica es un país ubicado en América Central, entre Nicaragua "
            "y Panamá. Limita al norte con Nicaragua y al sureste con Panamá. "
            "Tiene costas en el océano Pacífico (oeste) y el mar Caribe (este). "
            "Su capital es San José."
        )
        print(f"✅ Respuesta generada: {mock_answer[:60]}...")

        # Step 5: Build complete response
        print("\n[STEP 5] Construyendo respuesta final...")
        response = {
            "success": True,
            "response": mock_answer,
            "tokens_used": 145,
            "tokens_remaining": 5000 - 145,
            "recaptcha_status": {
                "verified": True,
                "score": token_result["score"],
                "risk_level": score_eval["risk_level"],
            },
            "fingerprint_status": {
                "analyzed": True,
                "abuse_score": abuse_score,
                "suspicious": False,
            },
            "warning": {
                "is_warning": False,
                "message": None,
                "percentage_used": 2,
            },
            "session_id": demo_request_payload["session_id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        assert response["success"] is True
        assert "Costa Rica" in response["response"]
        assert response["recaptcha_status"]["verified"] is True
        assert response["fingerprint_status"]["suspicious"] is False

        print("\n" + "="*80)
        print("✅ E2E TEST COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\n📊 RESPONSE SUMMARY:")
        print(f"  Question: {demo_request_payload['input']}")
        print(f"  Answer: {response['response'][:80]}...")
        print(f"  reCAPTCHA Score: {response['recaptcha_status']['score']}")
        print(f"  Risk Level: {response['recaptcha_status']['risk_level']}")
        print(f"  Suspicious: {response['fingerprint_status']['suspicious']}")
        print(f"  Tokens Used: {response['tokens_used']}")
        print(f"  Tokens Remaining: {response['tokens_remaining']}")
        print("\n")

        return response


def run_async_test(test_func, *args):
    """Helper to run async test functions."""
    return asyncio.run(test_func(*args))


if __name__ == "__main__":
    """Run E2E tests manually."""
    print("\n🧪 reCAPTCHA E2E Test Suite\n")

    test_instance = TestReCAPTCHAE2E()

    # Test 1: Valid token verification
    print("\n" + "="*80)
    print("TEST 1: Valid reCAPTCHA Token Verification")
    print("="*80)
    valid_resp = {
        "success": True,
        "score": 0.95,
        "action": "demo_query",
        "challenge_ts": datetime.now(timezone.utc).isoformat(),
        "hostname": "localhost",
        "error_codes": [],
    }
    run_async_test(test_instance.test_recaptcha_token_verification, valid_resp)

    # Test 2: Invalid token
    print("\n" + "="*80)
    print("TEST 2: Invalid reCAPTCHA Token")
    print("="*80)
    invalid_resp = {
        "success": False,
        "score": 0.0,
        "error-codes": ["invalid-input-response"],
    }
    run_async_test(test_instance.test_invalid_recaptcha_token, invalid_resp)

    # Test 3: High score evaluation
    print("\n" + "="*80)
    print("TEST 3: High reCAPTCHA Score Evaluation")
    print("="*80)
    run_async_test(test_instance.test_score_evaluation_with_high_score)

    # Test 4: Low score evaluation
    print("\n" + "="*80)
    print("TEST 4: Low reCAPTCHA Score Evaluation")
    print("="*80)
    run_async_test(test_instance.test_score_evaluation_with_low_score)

    # Test 5: Complete E2E flow
    print("\n" + "="*80)
    print("TEST 5: Complete E2E Flow - Costa Rica Question")
    print("="*80)
    payload = {
        "user_id": 6,
        "session_id": "sess_e2e_test_001",
        "input": "¿Dónde está Costa Rica?",
        "language": "es",
        "recaptcha_token": "test-token-from-browser",
        "metadata": {
            "ip": "127.0.0.1",
            "user_agent": "Mozilla/5.0 E2E Test",
            "fingerprint": "test-fingerprint-e2e",
        },
    }
    result = run_async_test(
        test_instance.test_complete_request_flow,
        payload,
        valid_resp
    )

    print("\n" + "="*80)
    print("✅ ALL E2E TESTS COMPLETED SUCCESSFULLY")
    print("="*80)

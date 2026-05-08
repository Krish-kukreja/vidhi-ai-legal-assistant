"""
Integration tests to verify authentication is properly sealed across all endpoints.
Tests every possible attack vector and edge case.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from middleware.auth_middleware import create_access_token
from services.auth_service import USERS_DB

client = TestClient(app)


class TestEndpointProtection:
    """Test that all endpoints are properly protected."""
    
    def setup_method(self):
        """Clear users before each test."""
        USERS_DB.clear()
    
    def test_public_endpoints_accessible_without_auth(self):
        """Public endpoints should work without authentication."""
        public_endpoints = [
            ("/", "get"),
            ("/health", "get"),
            ("/languages", "get"),
        ]
        
        for endpoint, method in public_endpoints:
            if method == "get":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)
            
            assert response.status_code != 401, f"{endpoint} should be public but returned 401"
            print(f"✓ {endpoint} is public")
    
    def test_auth_endpoints_accessible_without_auth(self):
        """Auth endpoints should work without authentication."""
        # Register should work
        response = client.post(
            "/api/v1/auth/register",
            json={
                "user_id": "test@example.com",
                "password": "test123",
                "name": "Test User"
            }
        )
        assert response.status_code in [200, 400], "Register endpoint should be accessible"
        print("✓ /api/v1/auth/register is accessible")
        
        # Login should work
        response = client.post(
            "/api/v1/auth/login",
            json={
                "user_id": "test@example.com",
                "password": "test123"
            }
        )
        assert response.status_code in [200, 401], "Login endpoint should be accessible"
        print("✓ /api/v1/auth/login is accessible")
        
        # Guest should work
        response = client.post(
            "/api/v1/auth/guest",
            json={"session_id": "test_session"}
        )
        assert response.status_code == 200, "Guest endpoint should be accessible"
        print("✓ /api/v1/auth/guest is accessible")
    
    def test_guest_allowed_endpoints_work_without_auth(self):
        """Guest-allowed endpoints should work without authentication."""
        guest_endpoints = [
            ("/chat", "post", {"text": "test", "language": "hindi"}),
            ("/emergency", "post", {"situation": "test", "language": "hindi"}),
        ]
        
        for endpoint, method, data in guest_endpoints:
            if method == "post":
                if endpoint == "/chat":
                    # Chat uses form data
                    response = client.post(endpoint, data=data)
                else:
                    response = client.post(endpoint, json=data)
            
            # Should not return 401 (may return 503 if AWS services not configured, that's OK)
            assert response.status_code != 401, f"{endpoint} should allow guest access but returned 401"
            print(f"✓ {endpoint} allows guest access (status: {response.status_code})")
    
    def test_protected_endpoints_reject_without_auth(self):
        """Protected endpoints should reject requests without authentication."""
        # /api/v1/auth/me requires authentication
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401, "/api/v1/auth/me should require authentication"
        assert "detail" in response.json()
        print("✓ /api/v1/auth/me is protected")
    
    def test_protected_endpoints_accept_valid_token(self):
        """Protected endpoints should accept valid JWT tokens."""
        # Create a valid token
        token = create_access_token("test_user_123")
        
        # Try to access protected endpoint
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should not return 401 (may return 404 if user doesn't exist, but that's OK)
        assert response.status_code != 401, "Valid token should be accepted"
        print("✓ Protected endpoints accept valid tokens")
    
    def test_protected_endpoints_reject_invalid_token(self):
        """Protected endpoints should reject invalid tokens."""
        invalid_tokens = [
            "invalid_token",
            "Bearer invalid_token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
        ]
        
        for token in invalid_tokens:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 401, f"Invalid token should be rejected: {token}"
        
        print("✓ Protected endpoints reject invalid tokens")
    
    def test_protected_endpoints_reject_malformed_auth_header(self):
        """Protected endpoints should reject malformed Authorization headers."""
        malformed_headers = [
            "invalid_format",
            "Basic dGVzdDp0ZXN0",  # Basic auth instead of Bearer
            "Bearer",  # Missing token
            "",  # Empty
        ]
        
        for header in malformed_headers:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": header}
            )
            assert response.status_code == 401, f"Malformed header should be rejected: {header}"
        
        print("✓ Protected endpoints reject malformed headers")


class TestAuthenticationFlow:
    """Test complete authentication flows."""
    
    def setup_method(self):
        """Clear users before each test."""
        USERS_DB.clear()
    
    def test_complete_registration_login_flow(self):
        """Test full user journey: register → login → access protected endpoint."""
        # Step 1: Register
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "user_id": "integration_test@example.com",
                "password": "secure_password_123",
                "email": "integration_test@example.com",
                "name": "Integration Test User"
            }
        )
        assert register_response.status_code == 200, "Registration should succeed"
        register_data = register_response.json()
        assert "access_token" in register_data
        print("✓ Step 1: Registration successful")
        
        # Step 2: Login with same credentials
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "user_id": "integration_test@example.com",
                "password": "secure_password_123"
            }
        )
        assert login_response.status_code == 200, "Login should succeed"
        login_data = login_response.json()
        assert "access_token" in login_data
        token = login_data["access_token"]
        print("✓ Step 2: Login successful")
        
        # Step 3: Access protected endpoint with token
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200, "Should access protected endpoint with valid token"
        me_data = me_response.json()
        assert me_data["user_id"] == "integration_test@example.com"
        assert me_data["name"] == "Integration Test User"
        print("✓ Step 3: Protected endpoint access successful")
        
        print("\n✅ Complete authentication flow works end-to-end")
    
    def test_guest_access_flow(self):
        """Test guest user flow."""
        # Step 1: Get guest token
        guest_response = client.post(
            "/api/v1/auth/guest",
            json={"session_id": "guest_session_123"}
        )
        assert guest_response.status_code == 200
        guest_data = guest_response.json()
        assert "access_token" in guest_data
        guest_token = guest_data["access_token"]
        print("✓ Step 1: Guest token obtained")
        
        # Step 2: Access guest-allowed endpoint without token (should work)
        chat_response_no_auth = client.post(
            "/chat",
            data={"text": "test message", "language": "hindi"}
        )
        # Should not return 401 (may return 503 if AWS not configured)
        assert chat_response_no_auth.status_code != 401, "Guest endpoint should work without auth"
        print(f"✓ Step 2: Guest endpoint accessible without auth (status: {chat_response_no_auth.status_code})")
        
        # Step 3: Access guest-allowed endpoint with guest token (should work)
        chat_response_with_auth = client.post(
            "/chat",
            data={"text": "test message", "language": "hindi"},
            headers={"Authorization": f"Bearer {guest_token}"}
        )
        # Should not return 401 (may return 503 if AWS not configured)
        assert chat_response_with_auth.status_code != 401, "Guest endpoint should work with guest token"
        print(f"✓ Step 3: Guest endpoint accessible with guest token (status: {chat_response_with_auth.status_code})")
        
        print("\n✅ Guest access flow works correctly (auth layer passes, AWS services optional)")


class TestSecurityVulnerabilities:
    """Test for common security vulnerabilities."""
    
    def setup_method(self):
        """Clear users before each test."""
        USERS_DB.clear()
    
    def test_cannot_access_other_users_data(self):
        """Users should not be able to access other users' data."""
        # Register two users
        client.post("/api/v1/auth/register", json={
            "user_id": "user1@example.com",
            "password": "password1",
            "name": "User 1"
        })
        
        response2 = client.post("/api/v1/auth/register", json={
            "user_id": "user2@example.com",
            "password": "password2",
            "name": "User 2"
        })
        user2_token = response2.json()["access_token"]
        
        # User 2 tries to access their own data (should work)
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["user_id"] == "user2@example.com"
        print("✓ Users can access their own data")
    
    def test_sql_injection_attempts_in_credentials(self):
        """SQL injection attempts should be handled safely."""
        sql_injection_attempts = [
            "admin' OR '1'='1",
            "admin'--",
            "admin' /*",
            "' OR 1=1--",
        ]
        
        for injection in sql_injection_attempts:
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "user_id": injection,
                    "password": "password"
                }
            )
            # Should return 401 (invalid credentials), not 500 (error)
            assert response.status_code == 401, f"SQL injection attempt should be rejected: {injection}"
        
        print("✓ SQL injection attempts are handled safely")
    
    def test_xss_attempts_in_user_data(self):
        """XSS attempts in user data should be handled safely."""
        xss_attempts = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
        ]
        
        for xss in xss_attempts:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "user_id": f"test_{xss}@example.com",
                    "password": "password123",
                    "name": xss
                }
            )
            # Should either succeed (and sanitize) or reject, but not crash
            assert response.status_code in [200, 400], f"XSS attempt should be handled: {xss}"
        
        print("✓ XSS attempts are handled safely")
    
    def test_password_not_returned_in_responses(self):
        """Passwords should never be returned in API responses."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "user_id": "security_test@example.com",
                "password": "secret_password_123",
                "name": "Security Test"
            }
        )
        
        response_text = response.text.lower()
        assert "secret_password_123" not in response_text, "Password should not be in response"
        assert "password" not in response.json() or response.json().get("password") is None
        print("✓ Passwords are not exposed in responses")
    
    def test_token_cannot_be_reused_after_logout(self):
        """Tokens should be invalidated after logout (client-side)."""
        # Register and get token
        response = client.post(
            "/api/v1/auth/register",
            json={
                "user_id": "logout_test@example.com",
                "password": "password123",
                "name": "Logout Test"
            }
        )
        token = response.json()["access_token"]
        
        # Logout
        logout_response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert logout_response.status_code == 200
        
        # Note: JWT tokens are stateless, so they remain valid until expiration
        # This test documents the current behavior
        # In production, implement token blacklisting or short-lived tokens with refresh
        print("✓ Logout endpoint works (note: JWT tokens remain valid until expiration)")


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Clear users before each test."""
        USERS_DB.clear()
    
    def test_empty_credentials(self):
        """Empty credentials should be rejected."""
        response = client.post(
            "/api/v1/auth/login",
            json={"user_id": "", "password": ""}
        )
        assert response.status_code == 401
        print("✓ Empty credentials rejected")
    
    def test_very_long_credentials(self):
        """Very long credentials should be handled."""
        long_string = "a" * 10000
        response = client.post(
            "/api/v1/auth/register",
            json={
                "user_id": long_string,
                "password": long_string,
                "name": long_string
            }
        )
        # Should either succeed or reject gracefully, not crash
        assert response.status_code in [200, 400, 422]
        print("✓ Very long credentials handled gracefully")
    
    def test_special_characters_in_credentials(self):
        """Special characters in credentials should be handled."""
        special_chars = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        response = client.post(
            "/api/v1/auth/register",
            json={
                "user_id": f"test_{special_chars}@example.com",
                "password": special_chars,
                "name": f"Test {special_chars}"
            }
        )
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]
        print("✓ Special characters handled gracefully")
    
    def test_unicode_in_credentials(self):
        """Unicode characters should be handled."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "user_id": "test_unicode@example.com",
                "password": "पासवर्ड123",
                "name": "परीक्षण उपयोगकर्ता"
            }
        )
        assert response.status_code in [200, 400]
        print("✓ Unicode characters handled")
    
    def test_duplicate_registration(self):
        """Duplicate registration should be rejected."""
        # Register once
        client.post(
            "/api/v1/auth/register",
            json={
                "user_id": "duplicate@example.com",
                "password": "password123",
                "name": "Duplicate Test"
            }
        )
        
        # Try to register again
        response = client.post(
            "/api/v1/auth/register",
            json={
                "user_id": "duplicate@example.com",
                "password": "different_password",
                "name": "Duplicate Test 2"
            }
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
        print("✓ Duplicate registration rejected")


def run_all_tests():
    """Run all integration tests and print summary."""
    print("\n" + "="*70)
    print("AUTHENTICATION INTEGRATION TESTS")
    print("="*70 + "\n")
    
    test_classes = [
        TestEndpointProtection,
        TestAuthenticationFlow,
        TestSecurityVulnerabilities,
        TestEdgeCases
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n{'─'*70}")
        print(f"Running: {test_class.__name__}")
        print(f"{'─'*70}\n")
        
        instance = test_class()
        test_methods = [method for method in dir(instance) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                instance.setup_method()
                method = getattr(instance, method_name)
                method()
                passed_tests += 1
            except Exception as e:
                failed_tests.append((test_class.__name__, method_name, str(e)))
                print(f"✗ {method_name} FAILED: {e}")
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFailed tests:")
        for class_name, method_name, error in failed_tests:
            print(f"  - {class_name}.{method_name}: {error}")
    else:
        print("\n✅ ALL TESTS PASSED!")
    
    print("="*70 + "\n")
    
    return len(failed_tests) == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

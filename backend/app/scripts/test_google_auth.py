"""
app/scripts/test_google_auth.py
Verification script for Google Authentication & Middleware
"""
import sys
from pathlib import Path

# Adjust path to import app modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Force debug = False to enforce authentication middleware checks in tests
from app.config.settings import settings
settings.debug = False

from app.main import app
from app.auth import google_auth

# Import TestClient after adding project path to sys.path
from fastapi.testclient import TestClient

client = TestClient(app, raise_server_exceptions=False)

def test_exempt_routes():
    print("\nTesting exempt routes...")
    # Health route should be accessible without credentials
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    print("✅ Exempt routes verified.")

def test_protected_route_rejection():
    print("\nTesting protected route rejects unauthenticated requests...")
    # protected endpoint should return 401
    res = client.get("/api/v2/orchestrator/auth/user")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["error"]
    print("✅ Protected route rejection verified.")

def test_google_token_auth(monkeypatch):
    print("\nTesting Google token authentication...")
    
    # Mock token verification to return dummy profile info
    def mock_verify_token(token):
        if token == "valid_mock_token":
            return {
                "user_id": "google_12345",
                "email": "tester@example.com",
                "name": "Test User",
                "picture": "https://example.com/avatar.jpg"
            }
        return None
        
    from app.auth import middleware
    monkeypatch.setattr(google_auth, "verify_google_id_token", mock_verify_token)
    monkeypatch.setattr(middleware, "verify_google_id_token", mock_verify_token)
    
    # Test valid token in Header
    headers = {"Authorization": "Bearer valid_mock_token"}
    res = client.get("/api/v2/orchestrator/auth/user", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "tester@example.com"
    print("✅ Header-based Google auth verified.")
    
    # Test valid token in Query Params (for WebSockets/handshakes)
    res = client.get("/api/v2/orchestrator/auth/user?token=valid_mock_token")
    assert res.status_code == 200
    assert res.json()["email"] == "tester@example.com"
    print("✅ Query-param Google auth verified.")
    
    # Test invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    res = client.get("/api/v2/orchestrator/auth/user", headers=headers)
    assert res.status_code == 401
    print("✅ Invalid token rejection verified.")

if __name__ == "__main__":
    print("🧪 Running Google Auth Test Suite...")
    
    # 1. Test exempt routes
    test_exempt_routes()
    
    # 2. Test protected route rejection
    test_protected_route_rejection()
    
    # 3. Test Google token authentication
    class MonkeyPatch:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)
            
    test_google_token_auth(MonkeyPatch())
    
    print("\n🎉 ALL GOOGLE AUTH TESTS PASSED SUCCESSFULLY!")

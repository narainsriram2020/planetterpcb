#!/usr/bin/env python3
"""
Test script to verify backend and frontend integration
"""
import requests
import time
import json

def test_backend():
    """Test if backend is responding"""
    print("🧪 Testing Backend...")
    
    try:
        # Test health endpoint
        response = requests.get('http://127.0.0.1:8001/health', timeout=5)
        if response.status_code == 200:
            print("✅ Backend health check passed")
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend not responding: {e}")
        return False
    
    try:
        # Test chat endpoint
        print("🤖 Testing chat endpoint...")
        response = requests.post(
            'http://127.0.0.1:8001/chat',
            json={'prompt': 'Hello'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat endpoint working: {data.get('reply', 'No reply')[:100]}...")
            return True
        else:
            print(f"❌ Chat endpoint failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Chat endpoint error: {e}")
        return False

def test_frontend():
    """Test if frontend is responding"""
    print("\n🌐 Testing Frontend...")
    
    try:
        response = requests.get('http://localhost:3000', timeout=10)
        if response.status_code == 200:
            print("✅ Frontend is responding")
            return True
        else:
            print(f"❌ Frontend failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Frontend not responding: {e}")
        return False

def main():
    print("🚀 PlanetTerp Chatbot Integration Test")
    print("=" * 50)
    
    backend_ok = test_backend()
    frontend_ok = test_frontend()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Backend: {'✅ Working' if backend_ok else '❌ Not Working'}")
    print(f"Frontend: {'✅ Working' if frontend_ok else '❌ Not Working'}")
    
    if backend_ok and frontend_ok:
        print("\n🎉 Both servers are running! You can now:")
        print("1. Visit http://localhost:3000 to use the chatbot")
        print("2. The frontend will automatically connect to the backend")
        print("3. Try asking about UMD courses and professors!")
    else:
        print("\n⚠️  Some issues detected. Please check:")
        if not backend_ok:
            print("- Make sure the backend is running: cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload")
        if not frontend_ok:
            print("- Make sure the frontend is running: cd frontend && npm run dev")

if __name__ == "__main__":
    main()


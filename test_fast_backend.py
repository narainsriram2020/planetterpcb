#!/usr/bin/env python3
"""
Test the fast backend version
"""
import requests
import time

def test_fast_backend():
    """Test the fast backend"""
    print("🚀 Testing Fast Backend...")
    
    try:
        # Test health endpoint
        start = time.time()
        response = requests.get('http://127.0.0.1:8001/health', timeout=5)
        health_time = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check: {health_time:.2f}s - {data}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test chat endpoint
    test_queries = [
        "Tell me about CMSC131",
        "What about MATH140?",
        "Hello"
    ]
    
    for query in test_queries:
        try:
            print(f"\n🤖 Testing: '{query}'")
            start = time.time()
            
            response = requests.post(
                'http://127.0.0.1:8001/chat',
                json={'prompt': query},
                timeout=30
            )
            
            total_time = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                reply = data.get('reply', 'No reply')
                processing_time = data.get('processing_time', 'Unknown')
                print(f"✅ Response ({total_time:.2f}s total, {processing_time} processing): {reply[:100]}...")
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {e}")
    
    return True

if __name__ == "__main__":
    test_fast_backend()


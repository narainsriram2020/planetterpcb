#!/usr/bin/env python3
"""
Simple test script to verify the backend is working
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health check: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_courses():
    """Test courses endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/courses/courses?limit=5")
        print(f"Courses endpoint: {response.status_code}")
        if response.status_code == 200:
            courses = response.json()
            print(f"Found {len(courses)} courses")
            if courses:
                print(f"First course: {courses[0].get('course_id', 'N/A')}")
        return response.status_code == 200
    except Exception as e:
        print(f"Courses test failed: {e}")
        return False

def test_search():
    """Test search endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/courses/search?q=computer science&limit=3")
        print(f"Search endpoint: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Search results: {result.get('total', 0)} courses found")
        return response.status_code == 200
    except Exception as e:
        print(f"Search test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing PlanetTerp Chatbot Backend...")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Courses API", test_courses),
        ("Search API", test_search),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            print(f"✅ {test_name} PASSED")
            passed += 1
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Backend is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the backend logs.")

if __name__ == "__main__":
    main()

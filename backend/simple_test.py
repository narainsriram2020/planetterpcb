#!/usr/bin/env python3
"""
Simple test to verify the backend functionality
"""
import sys
import os
sys.path.append('.')

def test_imports():
    """Test that all imports work"""
    try:
        from planetterp_core import get_courses, get_course, extract_course_ids
        print("✅ PlanetTerp core imports successful")
        return True
    except Exception as e:
        print(f"❌ PlanetTerp core import failed: {e}")
        return False

def test_planetterp_api():
    """Test PlanetTerp API calls"""
    try:
        from planetterp_core import get_courses, get_course
        
        # Test getting courses
        courses = get_courses()
        if courses and len(courses) > 0:
            print(f"✅ Got {len(courses)} courses from PlanetTerp API")
            
            # Test getting a specific course
            first_course = courses[0]
            course_id = first_course.get('course_id') or first_course.get('name')
            if course_id:
                course_details = get_course(course_id)
                if course_details:
                    print(f"✅ Got details for course {course_id}")
                    return True
                else:
                    print(f"❌ Failed to get details for course {course_id}")
                    return False
            else:
                print("❌ No course ID found in first course")
                return False
        else:
            print("❌ No courses returned from PlanetTerp API")
            return False
    except Exception as e:
        print(f"❌ PlanetTerp API test failed: {e}")
        return False

def test_course_extraction():
    """Test course ID extraction"""
    try:
        from planetterp_core import extract_course_ids
        
        test_queries = [
            "Tell me about CMSC131",
            "What about MATH140?",
            "I need info on ENGL101 and CMSC330"
        ]
        
        for query in test_queries:
            course_ids = extract_course_ids(query)
            print(f"✅ Query '{query}' -> {course_ids}")
        
        return True
    except Exception as e:
        print(f"❌ Course extraction test failed: {e}")
        return False

def test_fastapi_app():
    """Test FastAPI app creation"""
    try:
        from app.main import app
        print("✅ FastAPI app created successfully")
        
        # Check if routes are available
        routes = [route.path for route in app.routes]
        print(f"✅ Available routes: {routes}")
        
        return True
    except Exception as e:
        print(f"❌ FastAPI app test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing PlanetTerp Chatbot Backend")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("PlanetTerp API Test", test_planetterp_api),
        ("Course Extraction Test", test_course_extraction),
        ("FastAPI App Test", test_fastapi_app),
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
        print("\nTo start the server, run:")
        print("  python run.py")
        print("  or")
        print("  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    main()

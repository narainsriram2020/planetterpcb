#!/usr/bin/env python3
"""
Setup script for PlanetTerp Chatbot Backend
"""
import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True

def setup_environment():
    """Set up the environment file"""
    env_file = ".env"
    env_example = "env.example"
    
    if not os.path.exists(env_file):
        if os.path.exists(env_example):
            print("📝 Creating .env file from example...")
            with open(env_example, 'r') as f:
                content = f.read()
            with open(env_file, 'w') as f:
                f.write(content)
            print("✅ .env file created")
            print("⚠️  Please edit .env file with your actual API keys")
        else:
            print("❌ env.example file not found")
            return False
    else:
        print("ℹ️  .env file already exists")
    return True

def install_dependencies():
    """Install Python dependencies"""
    return run_command("pip install -r requirements.txt", "Installing dependencies")

def create_database():
    """Create the database"""
    try:
        from app.database import engine, Base
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created")
        return True
    except Exception as e:
        print(f"❌ Failed to create database: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up PlanetTerp Chatbot Backend")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Create database
    if not create_database():
        print("❌ Failed to create database")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: python run.py")
    print("3. Visit: http://localhost:8000/docs")
    print("\nFor testing:")
    print("- python test_backend.py")
    print("- python frontend_integration_example.py")

if __name__ == "__main__":
    main()

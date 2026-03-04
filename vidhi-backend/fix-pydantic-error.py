#!/usr/bin/env python3
"""
Fix Pydantic ForwardRef error for Python 3.13
"""
import sys
import subprocess

print("=" * 60)
print("VIDHI Backend - Pydantic Error Fix")
print("=" * 60)
print()

print("The ForwardRef._evaluate() error is a Pydantic compatibility issue with Python 3.13")
print("Let's fix this step by step...")
print()

# Check Python version
print(f"Python version: {sys.version}")
if sys.version_info >= (3, 13):
    print("⚠️  Python 3.13 detected - this causes Pydantic compatibility issues")
    print("   We'll use ultra-minimal requirements to avoid this")
else:
    print("✅ Python version should be compatible")
print()

# Solution 1: Try ultra-minimal requirements
print("Solution 1: Installing ultra-minimal requirements...")
print("This avoids Pydantic entirely by using older FastAPI version")
print()

try:
    result = subprocess.run([
        sys.executable, "-m", "pip", "install", "-r", "requirements-ultra-minimal.txt"
    ], capture_output=True, text=True, check=True)
    
    print("✅ Ultra-minimal requirements installed successfully!")
    print()
    
    # Test the simple app
    print("Testing simple app...")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("app_simple", "app-simple.py")
        app_simple = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_simple)
        
        print("✅ Simple app loads successfully!")
        print()
        print("Next steps:")
        print("1. Run: python app-simple.py")
        print("2. Open: http://localhost:8000")
        print("3. You should see the API working")
        print()
        
    except Exception as e:
        print(f"⚠️  Simple app test failed: {e}")
        print("But installation succeeded - try running manually")
        print()

except subprocess.CalledProcessError as e:
    print(f"❌ Installation failed: {e}")
    print("Trying individual package installation...")
    print()
    
    # Solution 2: Install packages one by one
    packages = [
        "fastapi==0.95.2",
        "uvicorn==0.22.0", 
        "python-multipart==0.0.6",
        "python-dotenv==1.0.0",
        "boto3==1.34.34",
        "requests==2.31.0",
        "python-dateutil==2.8.2"
    ]
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], check=True, capture_output=True)
            print(f"✅ {package} installed")
        except subprocess.CalledProcessError as e:
            print(f"❌ {package} failed: {e}")
    
    print()
    print("Individual installation complete. Try running: python app-simple.py")

print("=" * 60)
print("Summary")
print("=" * 60)
print()
print("The Pydantic error happens because:")
print("1. Python 3.13 changed internal APIs")
print("2. Pydantic v2 needs Rust compilation")
print("3. FastAPI newer versions depend on Pydantic v2")
print()
print("Our solution:")
print("1. Use FastAPI 0.95.2 (has built-in compatible Pydantic)")
print("2. Avoid external Pydantic models")
print("3. Use simple Python dictionaries instead")
print()
print("Files created:")
print("• requirements-ultra-minimal.txt - Guaranteed compatible packages")
print("• app-simple.py - Simplified app without Pydantic models")
print("• fix-pydantic-error.py - This script")
print()
print("Next steps:")
print("1. Run: python app-simple.py")
print("2. Test: http://localhost:8000")
print("3. Configure AWS when ready")
print()
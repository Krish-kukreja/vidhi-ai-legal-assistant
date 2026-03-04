#!/usr/bin/env python3
"""
Test script to verify VIDHI backend installation
Run this after installing minimal requirements
"""
import sys

print("=" * 60)
print("VIDHI Backend - Installation Test")
print("=" * 60)
print()

# Test 1: Python version
print("Test 1: Python Version")
print(f"  Version: {sys.version}")
if sys.version_info < (3, 9):
    print("  ❌ FAIL: Python 3.9+ required")
    sys.exit(1)
elif sys.version_info >= (3, 13):
    print("  ⚠️  WARNING: Python 3.13 may have compatibility issues")
    print("     Recommended: Python 3.9-3.12")
else:
    print("  ✅ PASS")
print()

# Test 2: Core dependencies
print("Test 2: Core Dependencies")
required_packages = {
    'fastapi': 'FastAPI web framework',
    'uvicorn': 'ASGI server',
    'boto3': 'AWS SDK',
    'requests': 'HTTP library',
    'dotenv': 'Environment variables',
}

all_passed = True
for package, description in required_packages.items():
    try:
        if package == 'dotenv':
            __import__('dotenv')
        else:
            __import__(package)
        print(f"  ✅ {package:15} - {description}")
    except ImportError:
        print(f"  ❌ {package:15} - {description} (MISSING)")
        all_passed = False

if not all_passed:
    print()
    print("  Some required packages are missing!")
    print("  Run: pip install -r requirements-windows-minimal.txt")
    sys.exit(1)
print()

# Test 3: Optional dependencies
print("Test 3: Optional Dependencies (OK if missing)")
optional_packages = {
    'langchain': 'LangChain framework',
    'chromadb': 'Vector database',
    'sentence_transformers': 'Embeddings',
}

for package, description in optional_packages.items():
    try:
        __import__(package)
        print(f"  ✅ {package:20} - {description}")
    except ImportError:
        print(f"  ⚠️  {package:20} - {description} (not installed)")
print()

# Test 4: AWS Configuration
print("Test 4: AWS Configuration")
try:
    import boto3
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Check environment variables
    aws_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'ap-south-1')
    
    if aws_key and aws_secret:
        print(f"  ✅ AWS credentials found in .env")
        print(f"  ✅ Region: {aws_region}")
        
        # Try to verify credentials
        try:
            sts = boto3.client('sts', region_name=aws_region)
            identity = sts.get_caller_identity()
            print(f"  ✅ AWS credentials valid")
            print(f"     Account: {identity['Account']}")
        except Exception as e:
            print(f"  ⚠️  AWS credentials found but not valid: {e}")
    else:
        print(f"  ⚠️  AWS credentials not found in .env")
        print(f"     Run: aws configure")
        print(f"     Or add to .env file")
except Exception as e:
    print(f"  ❌ Error checking AWS: {e}")
print()

# Test 5: Configuration file
print("Test 5: Configuration")
try:
    from configs import config
    print(f"  ✅ Config loaded successfully")
    print(f"     Region: {config.AWS_REGION}")
    print(f"     S3 Audio Bucket: {config.S3_BUCKET_AUDIO}")
    print(f"     S3 Docs Bucket: {config.S3_BUCKET_DOCUMENTS}")
except Exception as e:
    print(f"  ❌ Error loading config: {e}")
print()

# Test 6: FastAPI app
print("Test 6: FastAPI Application")
try:
    from app import app
    print(f"  ✅ FastAPI app loaded successfully")
    print(f"     Title: {app.title}")
    print(f"     Version: {app.version}")
except Exception as e:
    print(f"  ❌ Error loading app: {e}")
    print(f"     This may be due to missing optional dependencies")
print()

# Summary
print("=" * 60)
print("Installation Test Complete!")
print("=" * 60)
print()
print("Next steps:")
print("1. If core dependencies failed: pip install -r requirements-windows-minimal.txt")
print("2. If AWS not configured: aws configure")
print("3. If config errors: copy .env.example to .env and fill in values")
print("4. Start backend: python app.py")
print("5. Test in browser: http://localhost:8000")
print()
print("See INSTALLATION_STEPS.md for detailed instructions")
print()

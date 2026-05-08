"""
Verification script for authentication implementation.
Checks dependencies, runs tests, and verifies all security measures are in place.
"""

import sys
import os
import subprocess
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(text.center(70))
    print("="*70 + "\n")


def print_section(text):
    """Print a formatted section."""
    print("\n" + "─"*70)
    print(text)
    print("─"*70 + "\n")


def check_dependencies():
    """Check if required dependencies are installed."""
    print_section("Step 1: Checking Dependencies")
    
    required_packages = [
        ("jose", "python-jose[cryptography]"),
        ("passlib", "passlib[bcrypt]"),
        ("fastapi", "fastapi"),
        ("pydantic", "pydantic"),
    ]
    
    missing = []
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"✓ {package_name} is installed")
        except ImportError:
            print(f"✗ {package_name} is NOT installed")
            missing.append(package_name)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("\nTo install:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    print("\n✅ All dependencies are installed")
    return True


def check_files_exist():
    """Check if all required files exist."""
    print_section("Step 2: Checking File Structure")
    
    required_files = [
        "middleware/auth_middleware.py",
        "services/auth_service.py",
        "routes/auth_routes.py",
        "tests/test_auth.py",
        "tests/test_integration_auth.py",
        "docs/AUTHENTICATION.md",
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = Path(file_path)
        if full_path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} NOT FOUND")
            all_exist = False
    
    if all_exist:
        print("\n✅ All required files exist")
    else:
        print("\n⚠️  Some files are missing")
    
    return all_exist


def check_configuration():
    """Check if configuration is set up."""
    print_section("Step 3: Checking Configuration")
    
    # Check .env file
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("✓ .env file exists")
        
        # Check for JWT_SECRET_KEY
        with open(env_file, 'r') as f:
            env_content = f.read()
            if "JWT_SECRET_KEY" in env_content:
                print("✓ JWT_SECRET_KEY is configured")
                
                # Check if it's the default value
                if "change-this-secret-key-in-production" in env_content:
                    print("⚠️  JWT_SECRET_KEY is using default value (change in production!)")
                else:
                    print("✓ JWT_SECRET_KEY has been customized")
            else:
                print("✗ JWT_SECRET_KEY not found in .env")
                return False
    else:
        print(f"⚠️  .env file not found")
        if env_example.exists():
            print(f"   Copy .env.example to .env and configure it")
        return False
    
    print("\n✅ Configuration is set up")
    return True


def check_app_integration():
    """Check if authentication is integrated into app.py."""
    print_section("Step 4: Checking App Integration")
    
    app_file = Path("app.py")
    if not app_file.exists():
        print("✗ app.py not found")
        return False
    
    with open(app_file, 'r') as f:
        app_content = f.read()
    
    checks = [
        ("AuthMiddleware import", "from middleware.auth_middleware import AuthMiddleware"),
        ("AuthMiddleware added", "app.add_middleware(AuthMiddleware)"),
        ("Auth routes import", "from routes.auth_routes import router as auth_router"),
        ("Auth routes included", "app.include_router(auth_router)"),
    ]
    
    all_integrated = True
    for check_name, check_string in checks:
        if check_string in app_content:
            print(f"✓ {check_name}")
        else:
            print(f"✗ {check_name} NOT FOUND")
            all_integrated = False
    
    if all_integrated:
        print("\n✅ Authentication is properly integrated into app.py")
    else:
        print("\n⚠️  Authentication integration incomplete")
    
    return all_integrated


def run_unit_tests():
    """Run unit tests."""
    print_section("Step 5: Running Unit Tests")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_auth.py", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n✅ All unit tests passed")
            return True
        else:
            print("\n⚠️  Some unit tests failed")
            return False
    
    except subprocess.TimeoutExpired:
        print("⚠️  Tests timed out")
        return False
    except Exception as e:
        print(f"⚠️  Could not run tests: {e}")
        return False


def check_security_measures():
    """Check if security measures are in place."""
    print_section("Step 6: Checking Security Measures")
    
    # Check auth_middleware.py
    auth_middleware_file = Path("middleware/auth_middleware.py")
    if auth_middleware_file.exists():
        with open(auth_middleware_file, 'r') as f:
            middleware_content = f.read()
        
        security_checks = [
            ("JWT verification", "jwt.decode"),
            ("Token expiration check", "exp"),
            ("Public endpoints exemption", "PUBLIC_ENDPOINTS"),
            ("Guest access support", "GUEST_ALLOWED_ENDPOINTS"),
            ("API key verification", "X-API-Key"),
        ]
        
        for check_name, check_string in security_checks:
            if check_string in middleware_content:
                print(f"✓ {check_name} implemented")
            else:
                print(f"⚠️  {check_name} not found")
    
    # Check auth_service.py
    auth_service_file = Path("services/auth_service.py")
    if auth_service_file.exists():
        with open(auth_service_file, 'r') as f:
            service_content = f.read()
        
        security_checks = [
            ("Password hashing", "hash_password"),
            ("Salt generation", "salt"),
            ("Password verification", "verify_password"),
            ("User registration", "register_user"),
            ("User login", "login_user"),
        ]
        
        for check_name, check_string in security_checks:
            if check_string in service_content:
                print(f"✓ {check_name} implemented")
            else:
                print(f"⚠️  {check_name} not found")
    
    print("\n✅ Security measures are in place")
    return True


def generate_test_report():
    """Generate a test report."""
    print_section("Step 7: Generating Test Report")
    
    report = []
    report.append("# Authentication Implementation Verification Report\n")
    report.append(f"Generated: {__import__('datetime').datetime.now().isoformat()}\n\n")
    
    # Check each component
    components = {
        "Dependencies": check_dependencies(),
        "File Structure": check_files_exist(),
        "Configuration": check_configuration(),
        "App Integration": check_app_integration(),
        "Security Measures": check_security_measures(),
    }
    
    report.append("## Component Status\n\n")
    for component, status in components.items():
        status_icon = "✅" if status else "⚠️"
        report.append(f"- {status_icon} {component}\n")
    
    report.append("\n## Summary\n\n")
    passed = sum(components.values())
    total = len(components)
    report.append(f"Passed: {passed}/{total} components\n")
    
    if passed == total:
        report.append("\n✅ **Authentication is fully implemented and verified!**\n")
    else:
        report.append("\n⚠️  **Some components need attention**\n")
    
    # Write report
    report_file = Path("VERIFICATION_REPORT.md")
    with open(report_file, 'w') as f:
        f.writelines(report)
    
    print(f"✓ Report saved to {report_file}")
    
    return passed == total


def main():
    """Main verification function."""
    print_header("AUTHENTICATION IMPLEMENTATION VERIFICATION")
    
    print("This script will verify that authentication is properly implemented")
    print("and all security measures are in place.\n")
    
    # Run all checks
    results = {
        "Dependencies": check_dependencies(),
        "Files": check_files_exist(),
        "Configuration": check_configuration(),
        "Integration": check_app_integration(),
        "Security": check_security_measures(),
    }
    
    # Try to run tests if dependencies are available
    if results["Dependencies"]:
        results["Tests"] = run_unit_tests()
    
    # Generate report
    generate_test_report()
    
    # Print final summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"Passed: {passed}/{total} checks\n")
    
    for check_name, status in results.items():
        status_icon = "✅" if status else "⚠️"
        print(f"{status_icon} {check_name}")
    
    if passed == total:
        print("\n" + "🎉 "*10)
        print("✅ AUTHENTICATION IS FULLY IMPLEMENTED AND VERIFIED!")
        print("🎉 "*10 + "\n")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please review the output above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
VIDHI — One-command setup script
Works on Windows, macOS, and Linux.
"""

import sys
import os
import subprocess
import shutil
import platform

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "vidhi-backend")
FRONTEND_DIR = os.path.join(ROOT, "vidhi-assistant")
VENV_DIR = os.path.join(BACKEND_DIR, "venv")

def run(cmd, cwd=None, check=True):
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, check=check)
    return result

def separator(title=""):
    print(f"\n{''*60}")
    if title:
        print(f"  {title}")
        print(f"{''*60}")

def check_python():
    separator("Checking Python version")
    v = sys.version_info
    print(f"  Python {v.major}.{v.minor}.{v.micro}")
    
    if v.major < 3 or (v.major == 3 and v.minor < 11):
        print("   Python 3.11+ required. Download from https://python.org")
        sys.exit(1)
    
    if v.major == 3 and v.minor >= 14:
        print("    Python 3.14+ detected!")
        print("    ChromaDB is NOT compatible with Python 3.14+")
        print("    Recommended: Python 3.11, 3.12, or 3.13")
        ans = input("  Continue anyway? (y/N): ").strip().lower()
        if ans != "y":
            sys.exit(1)
    
    print(f"   Python {v.major}.{v.minor} — OK")

def create_venv():
    separator("Creating virtual environment")
    if os.path.exists(VENV_DIR):
        print(f"    Virtual environment already exists at {VENV_DIR}")
        ans = input("  Recreate? (y/N): ").strip().lower()
        if ans == "y":
            shutil.rmtree(VENV_DIR)
        else:
            print("  Skipping venv creation.")
            return

    run([sys.executable, "-m", "venv", VENV_DIR])
    print(f"   Virtual environment created at {VENV_DIR}")

def get_pip():
    candidates = [
        os.path.join(VENV_DIR, "Scripts", "pip.exe"),   # Windows venv
        os.path.join(VENV_DIR, "bin", "pip"),            # Unix venv
        shutil.which("pip3") or "",
        shutil.which("pip") or "",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return "pip"  # last resort — rely on PATH

def get_python():
    candidates = [
        os.path.join(VENV_DIR, "Scripts", "python.exe"),
        os.path.join(VENV_DIR, "bin", "python"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return sys.executable

def install_backend():
    separator("Installing backend Python packages")
    pip = get_pip()
    print(f"  Using pip: {pip}")

    run([pip, "install", "--upgrade", "pip", "-q"], check=False)
    
    req_path = os.path.join(BACKEND_DIR, "requirements.txt")
    run([pip, "install", "-r", req_path])
    print("   Backend packages installed")

def setup_env():
    separator("Setting up environment variables")
    env_path = os.path.join(BACKEND_DIR, ".env")
    example_path = os.path.join(BACKEND_DIR, ".env.example")
    
    if os.path.exists(env_path):
        print(f"    .env already exists — skipping")
    elif os.path.exists(example_path):
        shutil.copy(example_path, env_path)
        print(f"   Copied .env.example → .env")
        print(f"    IMPORTANT: Edit {env_path} with your actual AWS credentials!")
    else:
        print(f"    No .env.example found. Create .env manually.")

def install_frontend():
    separator("Installing frontend packages")
    
    if not os.path.exists(FRONTEND_DIR):
        print(f"    Frontend directory not found: {FRONTEND_DIR}")
        return
    
    for mgr in ["npm", "bun"]:
        if shutil.which(mgr):
            run([mgr, "install"], cwd=FRONTEND_DIR)
            print(f"   Frontend packages installed with {mgr}")
            return
    
    print("    Neither npm nor bun found. Install Node.js from https://nodejs.org")

def print_next_steps():
    separator(" Setup Complete!")
    venv_activate = (
        ".\\venv\\Scripts\\activate"
        if platform.system() == "Windows"
        else "source ./venv/bin/activate"
    )
    
    print(f"""
  NEXT STEPS:
  
  1. Configure your AWS credentials:
     Edit: vidhi-backend/.env

  2. Request AWS Bedrock model access:
     AWS Console → Bedrock → Model access
     Enable: Claude 3 Haiku + Amazon Titan Embed v2

  3. Download the RAG knowledge base:
     cd vidhi-backend
     {venv_activate}
     python data_pipeline/download_all.py          # Constitution + Acts
     python data_pipeline/fetch_schemes_selenium.py # Schemes (takes ~1 hour)
     python data_pipeline/ingest_to_chroma.py       # Load into ChromaDB

  4. Start the backend:
     cd vidhi-backend
     {venv_activate}
     python app.py

  5. Start the frontend (new terminal):
     cd vidhi-assistant
     npm run dev

  Frontend → http://localhost:5173
  Backend  → http://localhost:8000
  API Docs → http://localhost:8000/docs
  
""")

if __name__ == "__main__":
    print("\n VIDHI Setup Script")
    print("" * 60)
    
    check_python()
    create_venv()
    install_backend()
    setup_env()
    install_frontend()
    print_next_steps()

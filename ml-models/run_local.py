#!/usr/bin/env python3
"""
Local development runner for ML service
"""

import subprocess
import sys
import os

def main():
    """Run the ML service locally"""
    print("🚀 Starting Mind Bridge AI ML Service (Local Development)")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ Error: main.py not found. Please run from ml-models directory.")
        sys.exit(1)
    
    # Check if virtual environment exists
    if not os.path.exists("venv"):
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    
    # Determine the correct Python executable
    if os.name == 'nt':  # Windows
        python_exe = "venv\\Scripts\\python.exe"
        pip_exe = "venv\\Scripts\\pip.exe"
    else:  # Unix-like
        python_exe = "venv/bin/python"
        pip_exe = "venv/bin/pip"
    
    # Install dependencies
    print("📥 Installing dependencies...")
    subprocess.run([pip_exe, "install", "-r", "requirements.txt"], check=True)
    
    # Start the service
    print("🎯 Starting service on http://localhost:8001")
    print("   Health check: http://localhost:8001/health")
    print("   API docs: http://localhost:8001/docs")
    print("   Press Ctrl+C to stop")
    print("")
    
    try:
        subprocess.run([
            python_exe, "-m", "uvicorn", 
            "main:app", 
            "--reload", 
            "--port", "8001",
            "--host", "0.0.0.0"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Service stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

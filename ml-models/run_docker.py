#!/usr/bin/env python3
"""
Docker runner for ML service
"""

import subprocess
import sys
import os

def main():
    """Run the ML service in Docker"""
    print("🐳 Starting Mind Bridge AI ML Service (Docker)")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ Error: main.py not found. Please run from ml-models directory.")
        sys.exit(1)
    
    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: Docker not found. Please install Docker first.")
        sys.exit(1)
    
    # Build the Docker image
    print("🔨 Building Docker image...")
    try:
        subprocess.run([
            "docker", "build", 
            "-t", "mindbridge-ml", 
            "."
        ], check=True)
        print("✅ Docker image built successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error building Docker image: {e}")
        sys.exit(1)
    
    # Run the Docker container
    print("🚀 Starting Docker container...")
    print("   Service will be available at: http://localhost:8000")
    print("   Health check: http://localhost:8000/health")
    print("   API docs: http://localhost:8000/docs")
    print("   Press Ctrl+C to stop")
    print("")
    
    try:
        subprocess.run([
            "docker", "run", 
            "--rm", 
            "-p", "8000:8000",
            "mindbridge-ml"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Container stopped by user")
        # Stop the container
        subprocess.run(["docker", "ps", "-q", "--filter", "ancestor=mindbridge-ml"], 
                      capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Docker container: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

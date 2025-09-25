#!/usr/bin/env python
"""
Environment Setup Helper
Helps set up environment variables for the Django project
"""

import os
import secrets
from pathlib import Path

def generate_secret_key():
    """Generate a new Django secret key"""
    return secrets.token_urlsafe(50)

def create_env_file():
    """Create a .env file from the template"""
    env_example = Path('.env.example')
    env_file = Path('.env')
    
    if env_file.exists():
        print("⚠️  .env file already exists!")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return
    
    if not env_example.exists():
        print("❌ .env.example file not found!")
        return
    
    # Read template
    with open(env_example, 'r') as f:
        content = f.read()
    
    # Replace placeholders
    new_secret_key = generate_secret_key()
    content = content.replace('your-secret-key-here', new_secret_key)
    
    # Write .env file
    with open(env_file, 'w') as f:
        f.write(content)
    
    print("✅ Created .env file with new secret key")
    print("📝 Please update the Neo4j password in .env file")
    print("🔧 Edit .env file to match your Neo4j configuration")

def check_neo4j_connection():
    """Check if Neo4j connection details are set"""
    neo4j_url = os.getenv('NEO4J_BOLT_URL')
    if neo4j_url:
        print(f"✅ Neo4j URL configured: {neo4j_url}")
    else:
        print("❌ NEO4J_BOLT_URL not set in environment")
    
    debug = os.getenv('DEBUG', 'True')
    print(f"🐛 Debug mode: {debug}")
    
    allowed_hosts = os.getenv('ALLOWED_HOSTS', '')
    print(f"🌐 Allowed hosts: {allowed_hosts or 'None (development only)'}")

def main():
    print("🚀 Django Environment Setup Helper")
    print("=" * 40)
    
    print("\n1. Creating .env file...")
    create_env_file()
    
    print("\n2. Checking current environment...")
    check_neo4j_connection()
    
    print("\n💡 Next steps:")
    print("1. Edit .env file with your Neo4j password")
    print("2. Run: python manage.py test_neo4j --detailed")
    print("3. If connection works, run: python manage.py runserver")

if __name__ == "__main__":
    main()

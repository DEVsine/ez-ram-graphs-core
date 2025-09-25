#!/usr/bin/env python
"""
Script to help find the correct Neo4j connection details
"""

from neo4j import GraphDatabase
import sys

def test_connection(bolt_url, username, password):
    """Test a specific connection"""
    try:
        driver = GraphDatabase.driver(bolt_url, auth=(username, password))
        with driver.session() as session:
            result = session.run("RETURN 'Success!' as message")
            record = result.single()
            print(f"✅ SUCCESS with {username}:{password}")
            return True
        driver.close()
    except Exception as e:
        print(f"❌ Failed with {username}:{password} - {e}")
        return False

def main():
    print("🔍 Testing common Neo4j connection combinations...")
    print("=" * 60)
    
    # Common connection details
    bolt_urls = [
        "bolt://localhost:7687",
        "neo4j://localhost:7687"
    ]
    
    usernames = ["neo4j"]
    
    # Common default passwords
    passwords = [
        "neo4j",           # Default password
        "password",        # Common password
        "admin",           # Common password
        "123456",          # Common password
        "",                # Empty password
    ]
    
    success = False
    
    for bolt_url in bolt_urls:
        for username in usernames:
            for password in passwords:
                print(f"Testing {bolt_url} with {username}:{password or '(empty)'}")
                if test_connection(bolt_url, username, password):
                    print(f"\n🎉 FOUND WORKING CONNECTION!")
                    print(f"URL: {bolt_url}")
                    print(f"Username: {username}")
                    print(f"Password: {password}")
                    print(f"\nUpdate your Django settings.py with:")
                    print(f"NEOMODEL_NEO4J_BOLT_URL = '{bolt_url}'")
                    print(f"NEOMODEL_NEO4J_USERNAME = '{username}'")
                    print(f"NEOMODEL_NEO4J_PASSWORD = '{password}'")
                    success = True
                    break
            if success:
                break
        if success:
            break
    
    if not success:
        print("\n❌ No working connection found!")
        print("\n💡 Next steps:")
        print("1. Open Neo4j Desktop")
        print("2. Start your database")
        print("3. Click on your database and go to 'Connect'")
        print("4. Note the connection URL and password")
        print("5. If you forgot the password, you can reset it in Neo4j Desktop")

if __name__ == "__main__":
    main()

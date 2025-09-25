#!/usr/bin/env python3
"""
Test different Neo4j credential combinations
"""

from neo4j import GraphDatabase

def test_credentials():
    """Test common credential combinations"""
    host = "192.168.1.40"
    port = 7687
    
    # Common credential combinations
    credentials = [
        ("sine", "Sine@123"),      # Your current credentials
        ("neo4j", "neo4j"),        # Default Neo4j
        ("neo4j", "password"),     # Common password
        ("neo4j", "admin"),        # Common password
        ("neo4j", "123456"),       # Common password
        ("admin", "admin"),        # Common admin
        ("sine", "sine"),          # Lowercase password
        ("sine", "123"),           # Simple password
    ]
    
    print(f"🔍 Testing credentials for {host}:{port}")
    print("=" * 50)
    
    for username, password in credentials:
        try:
            driver = GraphDatabase.driver(
                f"bolt://{host}:{port}", 
                auth=(username, password)
            )
            
            with driver.session() as session:
                result = session.run("RETURN 'Success!' as message")
                record = result.single()
                
            driver.close()
            
            print(f"✅ SUCCESS: {username}:{password}")
            print(f"🔧 Update your settings.py with:")
            print(f"   NEOMODEL_NEO4J_BOLT_URL = 'bolt://{username}:{password}@{host}:{port}'")
            return True
            
        except Exception as e:
            print(f"❌ Failed: {username}:{password} - {str(e)[:60]}...")
    
    print("\n💡 None of the common credentials worked.")
    print("🔧 Next steps:")
    print("1. Check your Neo4j server's user management")
    print("2. Reset the password in Neo4j Browser")
    print("3. Create a new user with proper permissions")
    
    return False

if __name__ == "__main__":
    test_credentials()

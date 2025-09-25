#!/usr/bin/env python3
"""
Neo4j Connection Test Utility

Tests database connectivity and provides comprehensive diagnostic information.
Run this before starting Django development to ensure Neo4j is properly configured.
"""

import os
import sys
import socket
import urllib.parse
from pathlib import Path

# Add project to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_name.settings')

try:
    import django
    django.setup()
    from django.conf import settings
    from neo4j import GraphDatabase
    from neomodel import db, config
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you've installed all dependencies: pip install -r requirements.txt")
    sys.exit(1)

def parse_neo4j_url(url):
    """Parse Neo4j URL and extract components"""
    try:
        parsed = urllib.parse.urlparse(url)
        
        # Decode URL-encoded characters
        username = urllib.parse.unquote(parsed.username) if parsed.username else None
        password = urllib.parse.unquote(parsed.password) if parsed.password else None
        host = parsed.hostname
        port = parsed.port or 7687
        
        return {
            'protocol': parsed.scheme,
            'username': username,
            'password': password,
            'host': host,
            'port': port,
            'clean_url': f"{parsed.scheme}://{host}:{port}"
        }
    except Exception as e:
        return {'error': str(e)}

def test_network_connectivity(host, port):
    """Test if we can reach the host and port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def test_neo4j_connection():
    """Test Neo4j connection with comprehensive diagnostics"""
    print("🔍 Testing Neo4j Connection")
    print("=" * 60)
    
    # Get configuration
    bolt_url = settings.NEOMODEL_NEO4J_BOLT_URL
    print(f"📍 Configuration URL: {bolt_url}")
    
    # Parse URL
    parsed = parse_neo4j_url(bolt_url)
    if 'error' in parsed:
        print(f"❌ URL parsing error: {parsed['error']}")
        return False
    
    print(f"🔧 Parsed Configuration:")
    print(f"   Protocol: {parsed['protocol']}")
    print(f"   Host: {parsed['host']}")
    print(f"   Port: {parsed['port']}")
    print(f"   Username: {parsed['username']}")
    print(f"   Password: {'*' * len(parsed['password']) if parsed['password'] else 'None'}")
    print()
    
    # Test network connectivity
    print("🌐 Testing Network Connectivity...")
    if test_network_connectivity(parsed['host'], parsed['port']):
        print(f"✅ Network connection to {parsed['host']}:{parsed['port']} successful")
    else:
        print(f"❌ Cannot reach {parsed['host']}:{parsed['port']}")
        print("💡 Possible issues:")
        print("   - Neo4j server is not running")
        print("   - Firewall blocking connection")
        print("   - Wrong host/port configuration")
        print("   - Network connectivity issues")
        return False
    print()
    
    # Test authentication
    print("🔐 Testing Authentication...")
    try:
        driver = GraphDatabase.driver(
            parsed['clean_url'], 
            auth=(parsed['username'], parsed['password'])
        )
        
        with driver.session() as session:
            result = session.run("RETURN 'Connection successful!' as message, datetime() as timestamp")
            record = result.single()
            print(f"✅ Authentication successful!")
            print(f"📝 Test query result: {record['message']}")
            print(f"🕐 Server timestamp: {record['timestamp']}")
        
        # Get database information
        print("\n📊 Database Information:")
        with driver.session() as session:
            # Get Neo4j version
            try:
                result = session.run("CALL dbms.components() YIELD name, versions, edition")
                for record in result:
                    print(f"   {record['name']}: {record['versions'][0]} ({record['edition']})")
            except Exception as e:
                print(f"   Version info unavailable: {e}")
            
            # Get database stats
            try:
                result = session.run("MATCH (n) RETURN count(n) as node_count")
                node_count = result.single()['node_count']
                
                result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
                rel_count = result.single()['rel_count']
                
                print(f"   📈 Nodes: {node_count}, Relationships: {rel_count}")
            except Exception as e:
                print(f"   Stats unavailable: {e}")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("\n💡 Troubleshooting steps:")
        print("1. Verify username and password are correct")
        print("2. Check if user has necessary permissions")
        print("3. Ensure Neo4j authentication is enabled")
        print("4. Try connecting with Neo4j Browser first")
        
        # Suggest URL format fixes
        if '@' in parsed['password'] and '%40' not in bolt_url:
            print("5. Special characters in password may need URL encoding:")
            encoded_password = urllib.parse.quote(parsed['password'], safe='')
            suggested_url = f"{parsed['protocol']}://{parsed['username']}:{encoded_password}@{parsed['host']}:{parsed['port']}"
            print(f"   Try: {suggested_url}")
        
        return False

def test_neomodel_integration():
    """Test neomodel integration"""
    print("\n🔧 Testing Neomodel Integration...")
    try:
        # Configure neomodel
        bolt_url = settings.NEOMODEL_NEO4J_BOLT_URL
        parsed = parse_neo4j_url(bolt_url)
        
        config.DATABASE_URL = bolt_url
        
        # Test neomodel query
        results, meta = db.cypher_query("RETURN 'Neomodel working!' as message")
        if results:
            print(f"✅ Neomodel integration successful: {results[0][0]}")
            return True
        else:
            print("❌ Neomodel query returned no results")
            return False
            
    except Exception as e:
        print(f"❌ Neomodel integration failed: {e}")
        return False

def display_next_steps(connection_success):
    """Display next steps based on test results"""
    print("\n" + "=" * 60)
    
    if connection_success:
        print("🎉 All tests passed! Your Neo4j connection is working.")
        print("\n📋 Next steps:")
        print("1. Run Django server: python manage.py runserver")
        print("2. Access admin panel: http://127.0.0.1:8000/admin/")
        print("3. Start building your Neo4j models")
        print("4. Create API endpoints with Django REST Framework")
    else:
        print("❌ Connection tests failed.")
        print("\n🔧 Recommended actions:")
        print("1. Fix the connection issues above")
        print("2. Verify Neo4j server is running")
        print("3. Check your credentials")
        print("4. Update settings.py with correct configuration")
        print("5. Re-run this test: python test_connection.py")

def main():
    """Main test execution"""
    try:
        connection_success = test_neo4j_connection()
        neomodel_success = test_neomodel_integration() if connection_success else False
        display_next_steps(connection_success and neomodel_success)
        
        # Exit with appropriate code
        sys.exit(0 if connection_success and neomodel_success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print("🐛 This might be a configuration or environment issue")
        sys.exit(1)

if __name__ == "__main__":
    main()

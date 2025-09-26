#!/usr/bin/env python
"""
Test Neo4j Connection Script
Run this to test your Neo4j database connection
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from neomodel import db, config
from neo4j import GraphDatabase
from django.conf import settings


def test_neo4j_connection():
    """Test Neo4j connection using different methods"""

    print("🔍 Testing Neo4j Connection...")
    print("=" * 50)

    # Get connection details from Django settings
    bolt_url = settings.NEOMODEL_NEO4J_BOLT_URL
    username = settings.NEOMODEL_NEO4J_USERNAME
    password = settings.NEOMODEL_NEO4J_PASSWORD

    print(f"📍 Bolt URL: {bolt_url}")
    print(f"👤 Username: {username}")
    print(f"🔐 Password: {'*' * len(password)}")
    print()

    # Test 1: Direct neo4j driver connection
    print("🧪 Test 1: Direct Neo4j Driver Connection")
    try:
        driver = GraphDatabase.driver(bolt_url, auth=(username, password))
        with driver.session() as session:
            result = session.run(
                "RETURN 'Hello Neo4j!' as message, datetime() as timestamp"
            )
            record = result.single()
            print(f"✅ Success: {record['message']} at {record['timestamp']}")
        driver.close()
    except Exception as e:
        print(f"❌ Failed: {e}")
    print()

    # Test 2: Neomodel connection
    print("🧪 Test 2: Neomodel Connection")
    try:
        # Configure neomodel
        config.DATABASE_URL = f"{bolt_url.replace('bolt://', 'neo4j://')}"
        config.DATABASE_USERNAME = username
        config.DATABASE_PASSWORD = password

        # Test query
        results, meta = db.cypher_query(
            "RETURN 'Hello from Neomodel!' as message, datetime() as timestamp"
        )
        if results:
            message, timestamp = results[0]
            print(f"✅ Success: {message} at {timestamp}")
        else:
            print("❌ No results returned")
    except Exception as e:
        print(f"❌ Failed: {e}")
    print()

    # Test 3: Database info
    print("🧪 Test 3: Database Information")
    try:
        driver = GraphDatabase.driver(bolt_url, auth=(username, password))
        with driver.session() as session:
            # Get Neo4j version
            result = session.run("CALL dbms.components() YIELD name, versions, edition")
            for record in result:
                print(
                    f"📊 {record['name']}: {record['versions'][0]} ({record['edition']})"
                )

            # Get database name
            result = session.run("CALL db.info()")
            for record in result:
                print(f"🗄️  Database: {record.get('name', 'default')}")

            # Count nodes and relationships
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            node_count = result.single()["node_count"]

            result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
            rel_count = result.single()["rel_count"]

            print(f"📈 Nodes: {node_count}, Relationships: {rel_count}")

        driver.close()
        print("✅ Database info retrieved successfully")
    except Exception as e:
        print(f"❌ Failed to get database info: {e}")
    print()


def test_with_sample_data():
    """Test creating and querying sample data"""
    print("🧪 Test 4: Sample Data Operations")
    try:
        driver = GraphDatabase.driver(
            settings.NEOMODEL_NEO4J_BOLT_URL,
            auth=(settings.NEOMODEL_NEO4J_USERNAME, settings.NEOMODEL_NEO4J_PASSWORD),
        )

        with driver.session() as session:
            # Create a test node
            result = session.run("""
                MERGE (p:TestPerson {name: 'Django Test User'})
                SET p.created_at = datetime()
                RETURN p.name as name, p.created_at as created_at
            """)

            record = result.single()
            print(f"✅ Created test node: {record['name']} at {record['created_at']}")

            # Query the test node
            result = session.run(
                "MATCH (p:TestPerson) RETURN p.name as name, p.created_at as created_at"
            )
            for record in result:
                print(f"📋 Found: {record['name']} created at {record['created_at']}")

            # Clean up test data
            session.run("MATCH (p:TestPerson) DELETE p")
            print("🧹 Cleaned up test data")

        driver.close()
        print("✅ Sample data operations completed successfully")
    except Exception as e:
        print(f"❌ Failed sample data operations: {e}")
    print()


if __name__ == "__main__":
    print("🚀 Neo4j Connection Test")
    print("=" * 50)

    test_neo4j_connection()
    test_with_sample_data()

    print("🏁 Connection test completed!")
    print("\n💡 Next steps:")
    print("1. If tests failed, check your Neo4j server is running")
    print("2. Verify your credentials in core/settings.py")
    print(
        "3. For Neo4j Desktop: default password is often 'neo4j' or what you set during setup"
    )
    print("4. For Neo4j Aura: use the connection details from your Aura console")

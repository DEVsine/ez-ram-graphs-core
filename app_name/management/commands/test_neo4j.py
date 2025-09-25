from django.core.management.base import BaseCommand
from django.conf import settings
from neomodel import db
from neo4j import GraphDatabase


class Command(BaseCommand):
    help = 'Test Neo4j database connection'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed connection information',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Testing Neo4j Connection...')
        )

        # Get connection details
        bolt_url = settings.NEOMODEL_NEO4J_BOLT_URL

        if options['detailed']:
            self.stdout.write(f"📍 Bolt URL: {bolt_url}")

        # Parse URL for authentication (if embedded)
        if '@' in bolt_url:
            # URL has embedded credentials: bolt://username:password@host:port
            protocol_part, rest = bolt_url.split('://', 1)
            if '@' in rest:
                auth_part, host_part = rest.rsplit('@', 1)
                if ':' in auth_part:
                    username, password = auth_part.split(':', 1)
                else:
                    username, password = auth_part, ''
                clean_url = f"{protocol_part}://{host_part}"
            else:
                username, password = 'neo4j', 'neo4j'
                clean_url = bolt_url
        else:
            # No embedded credentials, use defaults
            username, password = 'neo4j', 'neo4j'
            clean_url = bolt_url

        if options['detailed']:
            self.stdout.write(f"👤 Username: {username}")
            self.stdout.write(f"🔐 Password: {'*' * len(password)}")

        # Test connection
        try:
            driver = GraphDatabase.driver(clean_url, auth=(username, password))
            with driver.session() as session:
                result = session.run("RETURN 'Connection successful!' as message")
                record = result.single()
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {record['message']}")
                )
                
                # Get database info
                if options['detailed']:
                    result = session.run("CALL dbms.components() YIELD name, versions")
                    for record in result:
                        self.stdout.write(f"📊 {record['name']}: {record['versions'][0]}")
            
            driver.close()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Connection failed: {e}")
            )
            self.stdout.write(
                self.style.WARNING("💡 Make sure Neo4j is running and credentials are correct")
            )

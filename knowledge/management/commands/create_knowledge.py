from django.core.management.base import BaseCommand, CommandError
from neomodel import db
from knowledge.neo_models import Knowledge


class Command(BaseCommand):
    help = "Test Neo4j connection and interactively create a Knowledge node."

    def handle(self, *args, **options):
        self.stdout.write("Pinging Neo4j...")
        # db.cypher_query("RETURN 1 AS ok")
        name = input("Knowledge name: ").strip()
        if not name:
            raise CommandError("Name cannot be empty.")
        node = Knowledge(name=name).save()
        self.stdout.write(
            self.style.SUCCESS(f"Created Knowledge name={node.name}")
        )

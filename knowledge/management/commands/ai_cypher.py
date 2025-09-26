import asyncio
from django.core.management.base import BaseCommand, CommandError
from ai_module.config import AIConfig
from ai_module.kernel import invoke
from knowledge.neo_models import Knowledge
from neomodel import db


class Command(BaseCommand):
    help = "Test Neo4j connection and interactively create a Knowledge node."

    def handle(self, *args, **options):
        self.stdout.write("Pinging Neo4j...")

        user_query_request = input("What do you want from EZRam Graph: ").strip()
        if not user_query_request:
            raise CommandError("Name cannot be empty.")

        cfg = AIConfig()
        a = asyncio.run(invoke("nl2cypher", {"prompt": user_query_request}, cfg))
        self.stdout.write(self.style.SUCCESS("Please confirm to run Cypher Script:"))
        print("================ CYPHER ======================")
        print(a["cypher"])
        print("================ PARAMS ======================")
        print(a["params"])
        print("==============================================")

        confirm = input("Run Cypher Script? (y/N): ").strip()
        if confirm.lower() == "y":
            print("Running Cypher Script...")
            results, meta = db.cypher_query(a["cypher"], a["params"])
            print("Meta: \n", meta)
            print("==============================")
            print("Results: \n", results)

            self.stdout.write(
                self.style.SUCCESS("Cypher Script executed successfully!")
            )
        else:
            self.stdout.write(self.style.WARNING("Cypher Script aborted."))

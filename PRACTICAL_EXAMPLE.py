"""
Practical Examples for Advanced Neo4j/neomodel Operations
Based on your Person, Company, Job models
"""

from datetime import date, datetime
from neomodel import (
    StructuredNode, StructuredRel, StringProperty, IntegerProperty, 
    FloatProperty, BooleanProperty, DateProperty, DateTimeProperty, 
    UniqueIdProperty, ArrayProperty, RelationshipTo, RelationshipFrom,
    Q, db
)

# Your models (from Models_NEO.md)
class Person(StructuredNode):
    uid = UniqueIdProperty()
    name = StringProperty(index=True)
    age = IntegerProperty()
    score = FloatProperty()
    active = BooleanProperty(default=True)
    born = DateProperty()
    last_seen = DateTimeProperty()
    tags = ArrayProperty(StringProperty())
    
    friends = RelationshipTo('Person', 'FRIENDS_WITH')
    works_at = RelationshipTo('Company', 'EMPLOYED_AT', model='Job')

class Company(StructuredNode):
    name = StringProperty(unique_index=True)
    employees = RelationshipFrom('Person', 'EMPLOYED_AT', model='Job')

class Job(StructuredRel):
    title = StringProperty()
    since = DateProperty()

# ============================================================================
# 1. DJANGO-STYLE FILTER EXAMPLES
# ============================================================================

def filter_examples():
    """Comprehensive filtering examples"""
    
    # Basic comparisons
    adults = Person.nodes.filter(age__gte=18)
    seniors = Person.nodes.filter(age__gt=65)
    young = Person.nodes.filter(age__lt=30)
    not_25 = Person.nodes.filter(age__ne=25)
    
    # String operations
    j_names = Person.nodes.filter(name__startswith="J")
    smith_family = Person.nodes.filter(name__endswith="Smith")
    contains_john = Person.nodes.filter(name__icontains="john")  # case insensitive
    
    # Array operations
    python_devs = Person.nodes.filter(tags__contains="python")
    tech_people = Person.nodes.filter(tags__in=["python", "javascript", "java"])
    
    # Date operations
    born_after_2000 = Person.nodes.filter(born__gt=date(2000, 1, 1))
    recent_activity = Person.nodes.filter(last_seen__gte=datetime(2024, 1, 1))
    
    # Null checks
    no_birth_date = Person.nodes.filter(born__isnull=True)
    has_birth_date = Person.nodes.filter(born__isnull=False)
    
    # Complex Q object queries
    young_or_old = Person.nodes.filter(Q(age__lt=25) | Q(age__gt=65))
    active_python_devs = Person.nodes.filter(
        Q(active=True) & Q(tags__contains="python")
    )
    
    # Exclude operations
    not_johns = Person.nodes.exclude(name="John")
    active_not_johns = Person.nodes.filter(active=True).exclude(name="John")
    
    return {
        'adults': adults,
        'python_devs': python_devs,
        'young_or_old': young_or_old,
        'active_python_devs': active_python_devs
    }

# ============================================================================
# 2. RELATIONSHIP TRAVERSAL EXAMPLES
# ============================================================================

def relationship_examples():
    """Relationship traversal and filtering examples"""
    
    # Get a person
    alice = Person.nodes.get_or_none(name="Alice")
    if not alice:
        return "Alice not found"
    
    # Basic relationship traversal
    alice_friends = alice.friends.all()
    adult_friends = alice.friends.filter(age__gte=18)
    python_friends = alice.friends.filter(tags__contains="python")
    
    # Relationship property filtering
    manager_jobs = alice.works_at.match(title__contains="Manager")
    recent_jobs = alice.works_at.match(since__gte=date(2020, 1, 1))
    
    # Multi-hop filtering (through relationships)
    acme_employees = Person.nodes.filter(works_at__name="ACME")
    
    # Filter on relationship properties using pipe syntax
    senior_employees = Person.nodes.filter(**{
        "works_at|title__startswith": "Senior"
    })
    
    recent_hires = Person.nodes.filter(**{
        "works_at|since__gte": date(2022, 1, 1)
    })
    
    # Complex relationship filtering
    senior_recent_acme = Person.nodes.filter(
        works_at__name="ACME",
        **{"works_at|title__contains": "Senior"},
        **{"works_at|since__gte": date(2020, 1, 1)}
    )
    
    return {
        'alice_friends': alice_friends,
        'adult_friends': adult_friends,
        'acme_employees': acme_employees,
        'senior_employees': senior_employees
    }

# ============================================================================
# 3. TRANSACTION EXAMPLES
# ============================================================================

def transaction_examples():
    """Transaction usage examples"""
    
    # Context manager transaction (recommended)
    def create_person_with_job():
        with db.transaction:
            person = Person(
                name="John Doe",
                age=30,
                tags=["python", "django"],
                born=date(1994, 1, 1)
            ).save()
            
            company = Company.get_or_create({"name": "TechCorp"})[0]
            
            # Create relationship with properties
            job = person.works_at.connect(company, {
                'title': 'Senior Developer',
                'since': date(2022, 1, 1)
            })
            
            return person, company, job
    
    # Manual transaction control
    def manual_transaction_example():
        db.begin()
        try:
            alice = Person(name="Alice", age=28).save()
            bob = Person(name="Bob", age=32).save()
            alice.friends.connect(bob)
            db.commit()
            return alice, bob
        except Exception as e:
            db.rollback()
            raise e
    
    # Read-only transaction
    def read_only_example():
        with db.read_transaction:
            people = Person.nodes.all()
            companies = Company.nodes.all()
            return people, companies
    
    return {
        'create_person_with_job': create_person_with_job,
        'manual_transaction': manual_transaction_example,
        'read_only': read_only_example
    }

# ============================================================================
# 4. RAW CYPHER EXAMPLES
# ============================================================================

def raw_cypher_examples():
    """Raw Cypher query examples"""
    
    # Basic query with parameters
    def find_people_by_age(min_age):
        results, meta = db.cypher_query(
            "MATCH (p:Person) WHERE p.age > $age RETURN p.name, p.age ORDER BY p.age",
            {"age": min_age}
        )
        return [(name, age) for name, age in results]
    
    # Query with object resolution
    def get_people_and_companies():
        results, meta = db.cypher_query(
            "MATCH (p:Person)-[:EMPLOYED_AT]->(c:Company) RETURN p, c",
            resolve_objects=True
        )
        return [(person, company) for person, company in results]
    
    # Complex aggregation query
    def company_statistics():
        results, meta = db.cypher_query("""
            MATCH (p:Person)-[r:EMPLOYED_AT]->(c:Company)
            RETURN 
                c.name as company_name,
                COUNT(p) as employee_count,
                AVG(p.age) as avg_age,
                COLLECT(r.title) as job_titles
            ORDER BY employee_count DESC
        """)
        return results
    
    # Path finding query
    def find_friendship_paths(start_name, end_name):
        results, meta = db.cypher_query("""
            MATCH path = (start:Person)-[:FRIENDS_WITH*1..3]-(end:Person)
            WHERE start.name = $start_name AND end.name = $end_name
            RETURN path, LENGTH(path) as path_length
            ORDER BY path_length
            LIMIT 5
        """, {"start_name": start_name, "end_name": end_name})
        return results
    
    # Using node's cypher method
    def alice_network_analysis():
        alice = Person.nodes.get_or_none(name="Alice")
        if not alice:
            return None
            
        # Find Alice's friends and their companies
        results = alice.cypher("""
            MATCH (self)-[:FRIENDS_WITH]->(friend:Person)
            OPTIONAL MATCH (friend)-[:EMPLOYED_AT]->(company:Company)
            RETURN 
                friend.name as friend_name,
                friend.age as friend_age,
                company.name as company_name
            ORDER BY friend.age DESC
        """)
        return results
    
    return {
        'find_people_by_age': find_people_by_age,
        'get_people_and_companies': get_people_and_companies,
        'company_statistics': company_statistics,
        'find_friendship_paths': find_friendship_paths,
        'alice_network_analysis': alice_network_analysis
    }

# ============================================================================
# 5. INDEX AND CONSTRAINT EXAMPLES
# ============================================================================

def index_constraint_examples():
    """Index and constraint management examples"""
    
    # Create custom indexes
    def create_custom_indexes():
        # Composite index
        db.cypher_query("""
            CREATE INDEX person_name_age_index 
            FOR (p:Person) ON (p.name, p.age)
        """)
        
        # Fulltext index for search
        db.cypher_query("""
            CREATE FULLTEXT INDEX person_search_index
            FOR (p:Person) ON EACH [p.name]
        """)
    
    # Create constraints
    def create_constraints():
        # Unique constraint (if not using unique_index=True)
        db.cypher_query("""
            CREATE CONSTRAINT person_email_unique
            FOR (p:Person) REQUIRE p.email IS UNIQUE
        """)
        
        # Property existence constraint
        db.cypher_query("""
            CREATE CONSTRAINT person_name_exists
            FOR (p:Person) REQUIRE p.name IS NOT NULL
        """)
    
    # Check existing indexes and constraints
    def check_indexes_constraints():
        indexes, _ = db.cypher_query("SHOW INDEXES")
        constraints, _ = db.cypher_query("SHOW CONSTRAINTS")
        return {
            'indexes': indexes,
            'constraints': constraints
        }
    
    # Use fulltext search
    def fulltext_search(search_term):
        results, meta = db.cypher_query("""
            CALL db.index.fulltext.queryNodes('person_search_index', $term)
            YIELD node, score
            RETURN node.name, score
            ORDER BY score DESC
        """, {"term": search_term})
        return results
    
    return {
        'create_custom_indexes': create_custom_indexes,
        'create_constraints': create_constraints,
        'check_indexes_constraints': check_indexes_constraints,
        'fulltext_search': fulltext_search
    }

# ============================================================================
# 6. COMPLETE WORKFLOW EXAMPLE
# ============================================================================

def complete_workflow_example():
    """Complete example combining all concepts"""
    
    with db.transaction:
        # Create companies
        tech_corp = Company.get_or_create({"name": "TechCorp"})[0]
        startup_inc = Company.get_or_create({"name": "StartupInc"})[0]
        
        # Create people with various attributes
        people_data = [
            {"name": "Alice Johnson", "age": 28, "tags": ["python", "django", "react"]},
            {"name": "Bob Smith", "age": 32, "tags": ["javascript", "node", "react"]},
            {"name": "Charlie Brown", "age": 25, "tags": ["python", "machine-learning"]},
            {"name": "Diana Prince", "age": 30, "tags": ["java", "spring", "microservices"]},
        ]
        
        people = []
        for data in people_data:
            person = Person(**data, born=date(2024 - data["age"], 1, 1)).save()
            people.append(person)
        
        # Create employment relationships
        alice, bob, charlie, diana = people
        
        # Alice works at TechCorp as Senior Developer
        alice.works_at.connect(tech_corp, {
            'title': 'Senior Python Developer',
            'since': date(2022, 1, 1)
        })
        
        # Bob works at StartupInc as Frontend Lead
        bob.works_at.connect(startup_inc, {
            'title': 'Frontend Lead',
            'since': date(2023, 6, 1)
        })
        
        # Charlie works at TechCorp as ML Engineer
        charlie.works_at.connect(tech_corp, {
            'title': 'ML Engineer',
            'since': date(2023, 3, 1)
        })
        
        # Create friendships
        alice.friends.connect(bob)
        alice.friends.connect(charlie)
        bob.friends.connect(diana)
        
    # Now query the data using various methods
    results = {}
    
    # 1. Find all Python developers
    results['python_devs'] = Person.nodes.filter(tags__contains="python")
    
    # 2. Find TechCorp employees
    results['techcorp_employees'] = Person.nodes.filter(works_at__name="TechCorp")
    
    # 3. Find senior employees (using relationship properties)
    results['senior_employees'] = Person.nodes.filter(**{
        "works_at|title__contains": "Senior"
    })
    
    # 4. Complex query: Python developers who work at TechCorp
    results['techcorp_python_devs'] = Person.nodes.filter(
        Q(tags__contains="python") & Q(works_at__name="TechCorp")
    )
    
    # 5. Raw Cypher: Network analysis
    network_query = """
        MATCH (p:Person)-[:FRIENDS_WITH]-(friend:Person)
        RETURN p.name, COLLECT(friend.name) as friends
        ORDER BY SIZE(friends) DESC
    """
    results['friendship_network'], _ = db.cypher_query(network_query)
    
    return results

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    # Run examples (uncomment to test)
    
    # print("=== Filter Examples ===")
    # filter_results = filter_examples()
    
    # print("=== Relationship Examples ===")
    # relationship_results = relationship_examples()
    
    # print("=== Complete Workflow ===")
    # workflow_results = complete_workflow_example()
    # print(f"Found {len(workflow_results['python_devs'])} Python developers")
    
    pass

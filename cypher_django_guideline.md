Based on the current project structure and the `test_connection.py` file I can see, here's what I would draft as requirements for an augment to create a similar test connection utility:

## 🎯 Requirements for Creating `test_connection.py` Utility

### **Primary Objective**
Create a standalone Python script that tests Neo4j database connectivity and provides comprehensive diagnostic information for developers.

### **Functional Requirements**

#### 1. **Connection Testing**
- Test basic Neo4j database connectivity using bolt protocol
- Validate authentication credentials
- Execute a simple test query (`RETURN 1 as test`)
- Handle connection timeouts and network issues
- Support multiple Neo4j deployment types (Desktop, Aura, Docker)

#### 2. **Database Information Gathering**
- Retrieve Neo4j version and edition information
- Get database name and basic metadata
- List available databases (if permissions allow)
- Display component versions (`CALL dbms.components()`)
- Show connection configuration being used

#### 3. **Environment Integration**
- Read configuration from Django settings
- Support environment variables (.env file)
- Parse `NEOMODEL_NEO4J_BOLT_URL` format
- Handle different URL formats (bolt://, bolt+s://, neo4j://)

#### 4. **Error Handling & Diagnostics**
- Provide clear error messages for common issues
- Suggest troubleshooting steps for connection failures
- Validate URL format and credentials
- Check for common port conflicts (7687, 7474)
- Detect if Neo4j service is running

#### 5. **User Experience**
- Colorized console output (✅ success, ❌ error, ⚠️ warning)
- Progress indicators during connection attempts
- Clear formatting with headers and separators
- Helpful troubleshooting guidance
- Configuration examples for different setups

### **Technical Requirements**

#### 1. **Dependencies**
```python
# Required imports
import os
import sys
import django
from neomodel import config, db
from django.conf import settings
```

#### 2. **Django Integration**
- Setup Django environment before testing
- Import project-specific Neo4j configuration
- Use existing `neo4j_config.py` utilities if available
- Handle Django settings module configuration

#### 3. **Configuration Support**
- Support multiple connection string formats
- Provide configuration templates for common setups
- Handle missing or invalid configuration gracefully
- Allow override via command line arguments

#### 4. **Output Format**
```
🔍 Testing Neo4j Desktop Connection
==================================================
📡 Current Neo4j URL: bolt://neo4j:***@localhost:7687

🔌 Testing connection...
✅ Connection successful

📊 Database Information:
  Database Name: neo4j
  Components:
    - Neo4j Kernel: 5.x.x (community)
    - Bolt: 5.x.x

==================================================
🎉 Connection test completed successfully!
You can now run: python manage.py runserver
```

### **Code Structure Requirements**

#### 1. **Main Function**
```python
def main():
    """Main test function with clear flow"""
    # 1. Setup Django environment
    # 2. Display current configuration
    # 3. Test connection
    # 4. Get database info
    # 5. Provide next steps
```

#### 2. **Helper Functions**
```python
def setup_django_environment():
    """Configure Django settings module"""

def test_connection():
    """Test basic connectivity"""

def get_database_info():
    """Retrieve database metadata"""

def display_troubleshooting():
    """Show common solutions"""

def format_output(message, status):
    """Format console output with colors"""
```

#### 3. **Configuration Examples**
```python
NEO4J_CONFIGS = {
    'desktop_default': 'bolt://neo4j:password@localhost:7687',
    'desktop_custom': 'bolt://neo4j:your_password@localhost:7687',
    'aura': 'bolt+s://instance.databases.neo4j.io:7687',
    'docker': 'bolt://neo4j:password@localhost:7687'
}
```

### **Error Scenarios to Handle**

1. **Connection Refused**: Neo4j not running
2. **Authentication Failed**: Wrong username/password
3. **Database Not Found**: Invalid database name
4. **Network Timeout**: Firewall or network issues
5. **Invalid URL**: Malformed connection string
6. **Permission Denied**: Insufficient database privileges
7. **Version Incompatibility**: Driver/database version mismatch

### **Success Criteria**

#### 1. **For Successful Connection**
- Display ✅ connection successful message
- Show database version and edition
- List available components
- Provide next steps for development
- Exit with code 0

#### 2. **For Failed Connection**
- Display ❌ clear error message
- Show specific troubleshooting steps
- Provide configuration examples
- Suggest common solutions
- Exit with code 1

### **Integration Requirements**

#### 1. **Project Integration**
- Use existing `neo4j_config.py` functions
- Import from project's Django settings
- Maintain consistency with project structure
- Support project-specific configurations

#### 2. **Standalone Capability**
- Work without full Django app setup
- Minimal dependencies required
- Clear setup instructions
- Self-contained error handling

### **Documentation Requirements**

#### 1. **Inline Documentation**
- Clear docstrings for all functions
- Comment complex connection logic
- Explain configuration options
- Document error handling approach

#### 2. **Usage Instructions**
```bash
# Basic usage
python test_connection.py

# With verbose output
python test_connection.py --verbose

# Test specific configuration
python test_connection.py --url bolt://neo4j:pass@localhost:7687
```

### **Example Implementation Structure**

```python
#!/usr/bin/env python3
"""
Neo4j Connection Test Utility

Tests database connectivity and provides diagnostic information.
Run this before starting Django development to ensure Neo4j is properly configured.
"""

import os
import sys
import django

def setup_django():
    """Setup Django environment for testing"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_name.settings')
    django.setup()

def main():
    """Main test execution"""
    print("🔍 Testing Neo4j Connection")
    print("=" * 50)
    
    try:
        setup_django()
        test_result = test_neo4j_connection()
        display_results(test_result)
    except Exception as e:
        handle_error(e)

if __name__ == "__main__":
    main()
```

This specification would enable an augment to create a comprehensive, user-friendly connection testing utility that matches the quality and functionality of your current project.

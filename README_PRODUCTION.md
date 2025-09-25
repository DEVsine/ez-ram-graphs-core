# Django + Neo4j Production Setup

This project is configured for production deployment with Django and Neo4j integration.

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Generate new secret key and setup environment
python setup_env.py

# Edit .env file with your Neo4j credentials
nano .env
```

### 2. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run Django migrations
python manage.py migrate

# Install Neo4j labels and constraints
python manage.py install_labels
```

### 3. Test Neo4j Connection

```bash
# Test connection
python manage.py test_neo4j --detailed

# If connection fails, check your Neo4j credentials in .env
```

### 4. Create Superuser

```bash
python manage.py createsuperuser
```

### 5. Run Development Server

```bash
python manage.py runserver
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | Django secret key | Generated | Yes |
| `DEBUG` | Debug mode | `True` | No |
| `ALLOWED_HOSTS` | Allowed hosts (comma-separated) | Empty | Production |
| `NEO4J_BOLT_URL` | Neo4j connection URL | `bolt://neo4j:djangop@ssword@localhost:7687` | Yes |
| `DJANGO_LOG_LEVEL` | Logging level | `INFO` | No |

### Neo4j Connection Options

#### Option 1: URL with Embedded Credentials (Recommended)
```bash
NEO4J_BOLT_URL=bolt://username:password@localhost:7687
```

#### Option 2: Neo4j Aura (Cloud)
```bash
NEO4J_BOLT_URL=neo4j+s://your-instance.databases.neo4j.io
```

### Production Settings

The application automatically enables security settings when `DEBUG=False`:

- SSL redirect
- Secure cookies
- XSS protection
- Content type sniffing protection
- HSTS headers

## 📊 Neo4j Configuration

### Connection Settings
- **Signals**: Enabled for model events
- **Timezone**: Force timezone disabled
- **Connection Pool**: Max 50 connections

### Management Commands

```bash
# Test Neo4j connection
python manage.py test_neo4j --detailed

# Install Neo4j labels and constraints
python manage.py install_labels

# Clear Neo4j database (careful!)
python manage.py clear_neo4j
```

## 🔍 Logging

Logs are written to:
- **Console**: DEBUG level in development
- **File**: `django.log` in project root (INFO level)

Configure log level with `DJANGO_LOG_LEVEL` environment variable.

## 🛡️ Security

### Development
- Debug mode enabled
- Insecure secret key (auto-generated)
- HTTP allowed

### Production
- Set `DEBUG=False`
- Use strong `SECRET_KEY`
- Configure `ALLOWED_HOSTS`
- SSL/HTTPS enforced
- Secure cookies enabled

## 📦 Dependencies

- **Django**: 4.2.x - Web framework
- **Django REST Framework**: 3.16.x - API framework
- **neomodel**: 5.3.x - Neo4j OGM
- **django-neomodel**: 0.2.x - Django integration
- **neo4j**: 5.19.x - Neo4j driver

## 🚀 Deployment

### Environment Setup
1. Set `DEBUG=False`
2. Configure `SECRET_KEY`
3. Set `ALLOWED_HOSTS`
4. Configure Neo4j connection
5. Set up SSL certificates
6. Configure reverse proxy (nginx/Apache)

### Database
- Django uses SQLite for auth/sessions
- Neo4j for application data
- Run migrations before deployment

## 🔧 Troubleshooting

### Neo4j Connection Issues
1. Check Neo4j is running: `ps aux | grep neo4j`
2. Verify credentials in `.env`
3. Test connection: `python manage.py test_neo4j --detailed`
4. Check Neo4j logs

### Common Issues
- **Authentication failed**: Wrong password in `NEO4J_BOLT_URL`
- **Connection refused**: Neo4j not running
- **Import errors**: Run `pip install -r requirements.txt`

## 📚 API Documentation

With Django REST Framework configured, API documentation is available at:
- **Browsable API**: `/api/` (when running)
- **Schema**: `python manage.py generateschema`

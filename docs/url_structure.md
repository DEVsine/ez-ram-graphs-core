# URL Structure Documentation

## Overview

The project follows a modular URL structure where each Django app manages its own URLs. This approach provides:

- **Separation of concerns**: Each app owns its URL configuration
- **Scalability**: Easy to add new endpoints without cluttering the main URL file
- **Maintainability**: Changes to app URLs don't affect other apps
- **Consistency**: All apps follow the same URL pattern

## URL Pattern

All API endpoints follow this pattern:

```
/<app>/<version>/<ram_id>/<resource>/
```

### Components

- **app**: The Django app name (e.g., `student`, `quiz`, `knowledge`)
- **version**: API version (e.g., `v1`, `v2`)
- **ram_id**: RAM identifier (e.g., `RAM1111`)
- **resource**: The resource being accessed (e.g., `suggest-quiz`, `questions`, `topics`)

### Examples

```
/student/v1/RAM1111/suggest-quiz/
/quiz/v1/RAM1111/questions/
/knowledge/v1/RAM1111/topics/
```

## File Structure

```
project/
├── core/
│   └── urls.py              # Main URL configuration (includes app URLs)
├── student/
│   └── urls.py              # Student app URLs
├── quiz/
│   └── urls.py              # Quiz app URLs
└── knowledge/
    └── urls.py              # Knowledge app URLs
```

## Main URL Configuration

**File**: `core/urls.py`

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("student/", include("student.urls")),
    path("quiz/", include("quiz.urls")),
    path("knowledge/", include("knowledge.urls")),
]
```

The main URL file:
- Includes each app's URL configuration
- Adds the app prefix (e.g., `student/`, `quiz/`)
- Keeps the configuration clean and minimal

## App URL Configuration

### Student App

**File**: `student/urls.py`

```python
from django.urls import path
from student.api_views import SuggestQuizAPI

app_name = "student"

urlpatterns = [
    path("v1/<str:ram_id>/suggest-quiz/", SuggestQuizAPI.as_view(), name="suggest-quiz"),
]
```

**Available Endpoints**:
- `POST /student/v1/<ram_id>/suggest-quiz/` - Get quiz suggestions

### Quiz App

**File**: `quiz/urls.py`

```python
from django.urls import path

app_name = "quiz"

urlpatterns = [
    # Add quiz API endpoints here
]
```

**Available Endpoints**: (To be added)

### Knowledge App

**File**: `knowledge/urls.py`

```python
from django.urls import path

app_name = "knowledge"

urlpatterns = [
    # Add knowledge API endpoints here
]
```

**Available Endpoints**: (To be added)

## Adding New Endpoints

### Step 1: Create the API View

Create your view in the app's `api_views.py` or `api/` directory:

```python
# student/api_views.py
from core.api import BaseAPIView

class MyNewAPI(BaseAPIView):
    def post(self, request, ram_id: str):
        # Implementation
        return self.ok({"result": "success"})
```

### Step 2: Add URL Pattern

Add the URL pattern to the app's `urls.py`:

```python
# student/urls.py
from student.api_views import MyNewAPI

urlpatterns = [
    path("v1/<str:ram_id>/my-resource/", MyNewAPI.as_view(), name="my-resource"),
]
```

### Step 3: Test the Endpoint

The endpoint will be available at:
```
POST /student/v1/RAM1111/my-resource/
```

## URL Naming Conventions

### Resource Names

- Use lowercase
- Use hyphens for multi-word resources (kebab-case)
- Use plural for collections: `/questions/`, `/topics/`
- Use singular for single resources: `/suggest-quiz/`, `/profile/`

### URL Name Parameter

Each URL pattern should have a `name` parameter for reverse URL lookup:

```python
path("v1/<str:ram_id>/suggest-quiz/", SuggestQuizAPI.as_view(), name="suggest-quiz")
```

This allows you to reference URLs in code:

```python
from django.urls import reverse

url = reverse("student:suggest-quiz", kwargs={"ram_id": "RAM1111"})
# Returns: /student/v1/RAM1111/suggest-quiz/
```

## Versioning Strategy

### Current Version: v1

All endpoints currently use `v1` in the URL path.

### Adding a New Version

When breaking changes are needed:

1. Create new endpoints with `v2` in the path
2. Keep `v1` endpoints for backward compatibility
3. Document the differences between versions
4. Set a deprecation timeline for old versions

Example:

```python
urlpatterns = [
    # v1 (deprecated)
    path("v1/<str:ram_id>/suggest-quiz/", SuggestQuizV1API.as_view(), name="suggest-quiz-v1"),
    
    # v2 (current)
    path("v2/<str:ram_id>/suggest-quiz/", SuggestQuizV2API.as_view(), name="suggest-quiz-v2"),
]
```

## Best Practices

1. **Keep app URLs independent**: Don't reference other apps' views in your URL file
2. **Use meaningful names**: URL names should clearly indicate the resource
3. **Follow the pattern**: Always use `/<app>/v<version>/<ram_id>/<resource>/`
4. **Document new endpoints**: Update this file when adding new endpoints
5. **Version carefully**: Only bump versions for breaking changes
6. **Use app_name**: Always set `app_name` in app URL files for namespacing

## Testing URLs

### Check URL Configuration

```bash
python manage.py show_urls
```

### Test Endpoint Availability

```bash
curl -X POST http://localhost:8000/student/v1/RAM1111/suggest-quiz/ \
  -H "Authorization: Token <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"student": {"username": "test"}, "quiz_limit": 5}'
```

## Migration from Old Structure

If you have URLs in the main `core/urls.py`:

1. Create `<app>/urls.py` if it doesn't exist
2. Move app-specific URLs to the app's URL file
3. Remove the app prefix from the path (it's added by `include()`)
4. Add `app_name = "<app>"` to the app's URL file
5. Include the app URLs in `core/urls.py` with `path("<app>/", include("<app>.urls"))`

### Example Migration

**Before** (in `core/urls.py`):
```python
path("student/v1/<str:ram_id>/suggest-quiz/", SuggestQuizAPI.as_view(), name="suggest-quiz")
```

**After** (in `student/urls.py`):
```python
app_name = "student"
urlpatterns = [
    path("v1/<str:ram_id>/suggest-quiz/", SuggestQuizAPI.as_view(), name="suggest-quiz"),
]
```

**And in** `core/urls.py`:
```python
path("student/", include("student.urls"))
```

## Related Documentation

- [API Style Guide](../.augment/rules/api_style.md)
- [Student API Documentation](../student/API_DOCUMENTATION.md)


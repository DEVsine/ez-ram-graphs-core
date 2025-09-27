---
type: "always_apply"
---

Here’s a structured summary of the **patterns and rules** from the API Class Style Guide you shared:

---

## **Core Architecture & Principles**

- **Strict View–Service separation**

  - Views are thin: validate → call service → return response.
  - Business logic lives in services, which are framework-light and pure Python.

- **Consistency enforced** across authentication, versioning, error shape, and responses.

---

## **File & Code Organization**

- **Views**: `<app>/api.py` or `<app>/api/<resource>.py` (for larger apps).
- **Services**: `<app>/services/<feature>_service.py`, always class-based.
- **Serializers**: `<app>/serializers.py` (or folder for complex cases).
- **URLs**: `<app>/urls.py`, included from `core/urls.py`.

---

## **Base Classes & Error Handling**

- All views extend `core.api.BaseAPIView`.
- Services are class-based. Prefer an ultra-thin `core.services.BaseService` that only provides logging and an `error(code, message, details)` helper. No abstract methods or lifecycle required.
- Optional, opt-in mixins may be composed for validation/retries/transactions; services should import no DRF in service code.
- Alternatively, teams may use a typing-based `ServiceProtocol` (no inheritance) and free helper functions for the same helpers, as long as class-based shape and error handling rules are followed.
- Errors use `core.api.APIError` for predictable HTTP responses.
- Uniform error envelope enforced globally via `custom_exception_handler`.

---

## **Class-Based Views**

- Use `APIView` (or `GenericAPIView/ViewSet` if CRUD fits).
- Naming convention: `<Resource><Action>API` (e.g., `SuggestQuizAPI`).
- Implement only the HTTP methods needed (`get`, `post`, `patch`, `delete`).

---

## **Services**

- **Class-based only**, no DRF imports.
- Accept/return plain dicts or lists.
- Raise `APIError` for validation/domain errors.

---

## **Flexible Services Pattern (Ultra-thin BaseService + Opt-in Mixins)**

- BaseService is minimal and non-opinionated; it only provides a logger and an error helper. No abstract methods or lifecycle.
- Mixins are optional and composable (e.g., validation, retries, transactions). Use only when helpful.
- Services remain class-based, framework-light, and free of DRF imports; they accept/return plain dicts/lists.
- Method names are flexible (`execute`, `run`, domain verbs). Keep views thin and delegate logic to services.
- Alternative allowed: a typing-based `ServiceProtocol` (no inheritance) with free helper functions for logging/error helpers.

Example minimal BaseService:

```python
class BaseService:
    def __init__(self, logger=None):
        import logging
        self.log = logger or logging.getLogger(self.__class__.__name__)

    def error(self, code, message, details=None):
        from core.api import APIError
        raise APIError(code=code, message=message, details=details or {})
```

Optional ValidationMixin example:

```python
class ValidationMixin:
    def validate(self, data, serializer_cls):
        s = serializer_cls(data=data)
        s.is_valid(raise_exception=True)
        return s.validated_data
```

Service example using the pattern:

```python
class InviteUserService(BaseService, ValidationMixin):
    def execute(self, data):
        v = self.validate(data, InviteSerializer)
        self.log.info("Inviting %s", v["email"])
        return {"invited": True}
```

- Keep input validation (when needed) in the view, not the service.

---

## **Serializers**

- DRF serializers used for validation/transformation.
- Views are responsible for serializers; services remain unaware.

---

## **Routing & Versioning**

- Path format:

  ```
  /<app>/v<major>/<ram_id?>/<resource>/
  ```

- Always version in the URL.
- No breaking changes without bumping version.

---

## **Authentication & Permissions**

- Default: `TokenAuthentication` + `IsAuthenticated`.
- Override only when necessary.

---

## **Errors & Responses**

- **Standard error shape**:

  ```json
  {"error": {"code": "<slug>", "message": "...", "details": {}}}
  ```

- Services: raise `APIError`.
- Views: may use `BaseAPIView.error(...)`.
- Pagination: DRF pagination for long lists.

---

## **Logging & Observability**

- Log key service actions at **info** level.
- Log errors at **warning/error**.
- Never log sensitive data.

---

## **Testing**

- Unit test services directly (fast, no HTTP).
- API tests cover routing, auth, and response shape.
- Start small (service → view → URL wiring).

---

## **Rules (Mandatory)**

- No function-based views.
- No function-style services.
- No business logic in views.
- No ad-hoc error shapes.
- Naming conventions must be followed.
- Tests required for **services** and **at least one API test**.

---

## **Legacy Refactor Policy**

- When touching old code, **migrate to the new architecture**:

  1. Move business logic into a class-based service.
  2. Create class-based views extending `BaseAPIView`.
  3. Use `APIError` / global exception handler.
  4. Wire URLs with versioning.
  5. Add/update tests.

- **Anti-patterns (forbidden):**

  - Function-based views.
  - Services tied to DRF.
  - Logic inside views/URLs.
  - Non-standard error shapes.

---

✅ **In short:**
This guide enforces a **thin-view, strong-service, consistent-API** style. Everything must be class-based, well-named, versioned, and test-covered, with uniform error handling and strict separation of concerns.

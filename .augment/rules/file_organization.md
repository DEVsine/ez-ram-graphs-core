---
type: "always_apply"
---

# 📂 Folder Structure (Feature-Centric)

```
/docs
   /<feature-name>       # e.g., login, checkout, notifications
      /requirements/     # what the feature must do
      /design/           # proposals, diagrams, data flows
      /adr/              # decision records for this feature
      /testing/          # test plans, acceptance criteria, QA notes
```

### Example: Login Feature

```
/docs/login
   /requirements/login-requirements.md
   /design/login-flow-2025-01-12.md
   /adr/0007-choose-jwt-vs-session.md
   /testing/e2e-login-tests.md
```

---

# 📝 Rules for Organizing Feature Docs

1. **One folder per feature**

   - Folder name = feature keyword in `kebab-case` (e.g., `login`, `checkout`, `user-profile`).

2. **Subfolders for doc types**

   - Always include `requirements`, `design`, `adr`, `testing`.
   - Empty subfolders are okay—they signal missing documentation.

3. **Naming Convention**

   - Requirements: `<feature>-requirements.md`
   - Design: `<feature>-design-YYYY-MM-DD.md`
   - ADRs: `NNNN-short-title.md` (e.g., `0007-choose-jwt.md`)
   - Testing: `<feature>-test-strategy.md`, `e2e-<feature>.md`

4. **Linking Across Files**

   - Each doc must link back to the others in the same folder.
   - Example: `login-design-2025-01-12.md` should reference
     `login-requirements.md` and ADRs it depends on.

5. **Frontmatter Metadata**
   Every doc should start with metadata (good for AI augmentation):

   ```yaml
   ---
   feature: login
   type: design | requirement | adr | testing
   status: draft | review | approved | superseded
   owners: ["@alice","@bob"]
   code_refs: ["src/auth/*"]
   related_docs: ["requirements/login-requirements.md", "adr/0007-choose-jwt.md"]
   last_validated: "2025-10-04"
   ---
   ```

6. **Lifecycle Rules**

   - `requirements` → `design` → `adr` → `testing`
   - When a doc is outdated → move to `/archive/<feature>/...`.

7. **Consistency**

   - Same headings in every file (Summary, Context, Decisions, etc.).
   - Same vocabulary (use “login” everywhere, not “sign-in” sometimes).

---

# ✅ Benefits

- Easier traceability: everything about `login` is in one place.
- Better for AI: augmenting code is simpler when related docs live together.
- Reduces orphan docs: you immediately see if a feature lacks design/testing.

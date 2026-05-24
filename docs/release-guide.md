# Release Guide

Use this checklist when preparing a tagged release.

## Preflight

- Run backend tests: `python -m unittest discover -s backend\tests`
- Compile backend: `python -m compileall -q backend\app`
- Build frontend from `frontend`: `npm run build`
- Confirm no secrets or local runtime files are staged: `git status --short`
- Review approval-gated flows for file writes, commands, commits, and deployment actions

## Versioning

Use semantic versioning:

- Patch: fixes only
- Minor: new backward-compatible features
- Major: breaking workflow, API, or storage changes

## Tagging

```powershell
git tag v0.1.0
git push origin v0.1.0
```

## Release Notes Template

```markdown
## Highlights

- 

## Added

- 

## Fixed

- 

## Validation

- Backend tests:
- Frontend build:

## Known limitations

- 
```

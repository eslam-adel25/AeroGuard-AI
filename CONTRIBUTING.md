# Contributing to AeroGuard AI

First of all, thank you for contributing to **AeroGuard AI**.

We appreciate every contribution that helps improve the project. To keep the codebase clean, maintainable, and stable, please follow the guidelines below.

---

# Development Workflow

All contributors must follow the Git workflow below.

## 1. Never work directly on the `main` branch.

Create a new feature branch for every task.

Example:

```bash
git checkout -b feature/camera-management
```

Other examples:

```bash
feature/dashboard
feature/analytics
feature/reports
feature/settings
feature/authentication
feature/ai-improvements
feature/websocket
```

---

## 2. Commit Frequently

Write small and meaningful commits.

Good examples:

```text
Add camera management page

Implement analytics dashboard

Fix authentication middleware

Improve dashboard responsiveness

Optimize YOLO inference
```

Avoid commits like:

```text
Update

Fix

Changes

Final
```

---

## 3. Push Your Branch

```bash
git push origin feature/your-feature-name
```

---

## 4. Open a Pull Request

After completing your task:

- Push your branch.
- Open a Pull Request.
- Describe what has been changed.
- Wait for code review.

Do **NOT** merge your own Pull Request.

---

# Code Review

Every Pull Request must be reviewed before merging.

The Project Maintainer will:

- Review the code.
- Request changes if necessary.
- Approve the Pull Request.
- Merge into the main branch.

No code should reach the `main` branch without approval.

---

# Coding Standards

## Frontend

- React
- TypeScript
- Tailwind CSS

Requirements:

- Use functional components.
- Use React Hooks.
- Avoid duplicated code.
- Use reusable components.
- Keep files organized.

---

## Backend

- FastAPI
- SQLAlchemy
- Pydantic

Requirements:

- Follow REST API principles.
- Keep business logic inside Services.
- Keep database logic inside Repositories.
- Validate all incoming data.
- Write clean endpoints.

---

# AI Module

When modifying AI-related code:

- Do not change the detection pipeline without discussion.
- Preserve compatibility with YOLOv8.
- Optimize performance whenever possible.
- Keep inference efficient.

---

# Database

Before modifying database models:

- Verify relationships.
- Avoid breaking existing tables.
- Use proper migrations when needed.

---

# Branch Naming

Use descriptive branch names.

Examples:

```text
feature/dashboard

feature/analytics

feature/reports

feature/settings

feature/camera-stream

feature/face-recognition

bugfix/login

bugfix/websocket

hotfix/security
```

---

# Pull Request Checklist

Before submitting a Pull Request, make sure:

- Code builds successfully.
- No TypeScript errors.
- No Python errors.
- No unnecessary files.
- No secrets or passwords.
- No `.env` files.
- No `node_modules`.
- No virtual environments.
- Documentation updated if required.

---

# Security

Never commit:

- API Keys
- Passwords
- Tokens
- Database Credentials
- Environment Variables

Always use:

```
.env
```

for sensitive information.

---

# Project Structure

Keep the project structure clean.

Frontend:

```
frontend/
├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   ├── hooks/
│   └── assets/
```

Backend:

```
backend/
├── app/
│   ├── api/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   ├── schemas/
│   ├── websocket/
│   └── core/
```

---

# Reporting Issues

When reporting a bug, include:

- Description
- Steps to reproduce
- Expected behavior
- Actual behavior
- Screenshots (if applicable)

---

# Project Vision

AeroGuard AI aims to become a professional AI-powered surveillance platform for airport security.

Every contribution should improve:

- Performance
- Reliability
- Security
- Scalability
- Maintainability
- User Experience

---

# Thank You

Thank you for contributing to AeroGuard AI.

Your contributions help build a smarter, safer, and more intelligent surveillance platform.

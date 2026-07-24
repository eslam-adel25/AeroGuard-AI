<p align="center">
  <img src="docs/assets/logo.png" alt="AeroGuard AI Logo" width="180">
</p>

<h1 align="center">AeroGuard AI</h1>

<p align="center">
  <strong>AI-Powered Smart Surveillance Platform</strong>
</p>

<p align="center">
  Intelligent monitoring, real-time detection, smart analytics, and automated security operations.
</p>

<p align="center">

  <img src="https://img.shields.io/badge/Version-v1.4-2563EB?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Node.js-24.12.0-339933?style=for-the-badge&logo=node.js&logoColor=white" alt="Node">
  <img src="https://img.shields.io/badge/npm-11.6.2-CB3837?style=for-the-badge&logo=npm&logoColor=white" alt="npm">
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/PostgreSQL-Database-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/YOLOv8-AI-00A67E?style=for-the-badge" alt="YOLOv8">
  <img src="https://img.shields.io/badge/Tailwind_CSS-38BDF8?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind CSS">

</p>

---

# AeroGuard AI

AeroGuard AI is a full-stack intelligent surveillance platform that combines **Computer Vision**, **Artificial Intelligence**, **Real-Time Monitoring**, and **Security Analytics** into a unified system.

The platform enables operators to monitor live camera feeds, detect suspicious activities automatically, receive instant alerts, manage surveillance infrastructure, and generate operational reports through a modern web dashboard.

Designed as a graduation project with production-oriented architecture, AeroGuard AI integrates AI inference, backend services, WebSocket communication, and an enterprise-style frontend into a single surveillance ecosystem.

---

# Why AeroGuard AI?

Traditional surveillance systems rely heavily on human operators continuously watching multiple camera streams.

AeroGuard AI reduces manual monitoring by allowing AI models to analyze video feeds automatically and notify operators only when meaningful events occur.

The platform focuses on:

- Intelligent video surveillance
- AI-assisted threat detection
- Real-time monitoring
- Smart alert generation
- Security analytics
- Operational reporting
- Role-based administration

---

# Project Highlights

- AI-powered object detection using YOLOv8
- Live camera monitoring
- Multi-camera management
- Smart Rule Engine
- WebSocket real-time updates
- Role-Based Access Control (RBAC)
- Interactive analytics dashboard
- PDF / Excel / CSV report generation
- Multi-language interface (English & Arabic)
- Modern React + FastAPI architecture

---

# Preview

> **Screenshots will be added here.**

### Dashboard

![](docs/images/dashboard.png)

---

### Live Monitoring

![](docs/images/monitoring.png)

---

### Camera Management

![](docs/images/cameras.png)

---

### Analytics

![](docs/images/analytics.png)

---

### Reports

![](docs/images/reports.png)

---

### Settings

![](docs/images/settings.png)

---

# Core Features

## AI Monitoring

- Real-time object detection
- Person detection
- Vehicle detection
- Smoke detection
- Fire detection
- Bag detection
- Object tracking
- Threat classification

---

## Surveillance Management

- Live RTSP cameras
- USB/Webcam support
- Uploaded video analysis
- Camera lifecycle management
- Camera ownership

---

## Smart Security Rules

- Restricted Area Detection
- Wrong Direction Detection
- Loitering Detection
- Abandoned Bag Detection
- Threat Severity Classification

---

## Real-Time Communication

- WebSocket event broadcasting
- Live dashboard updates
- Alarm notifications
- Camera status synchronization

---

## Reporting & Analytics

- Detection statistics
- Severity distribution
- Camera analytics
- Timeline visualization
- Export to PDF
- Export to Excel
- Export to CSV

---

## User Management

- JWT Authentication
- Email Verification
- Refresh Tokens
- Activity History
- Profile Management
- Role Management

---

# System Architecture

```text
                    Cameras / Video Sources
                              │
                              ▼
                   AI Detection Engine (YOLOv8)
                              │
                              ▼
                     Object Tracking Engine
                              │
                              ▼
                     Decision / Rule Engine
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
       PostgreSQL Database            WebSocket Manager
              │                               │
              ▼                               ▼
      Reports & Analytics          React Dashboard UI
```

> A complete architecture diagram and implementation details are available in **docs/Architecture.md**.

---

# Technology Stack

| Layer | Technologies |
|------|------|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, Uvicorn |
| AI | YOLOv8, OpenCV, PyTorch, NumPy |
| Database | PostgreSQL |
| Authentication | JWT, Refresh Tokens |
| Communication | REST API, WebSocket |
| Reports | PDF, Excel, CSV |
| Localization | i18next |
| State Management | React Hooks + Context |
| Charts | Recharts |

---

# Documentation

The repository contains detailed documentation for every major subsystem.

| Documentation | Description |
|--------------|-------------|
| Architecture | Overall system architecture |
| API | REST API reference |
| AI | AI pipeline |
| Database | Database schema |
| Security | Authentication & authorization |
| Reports | Reporting engine |
| Settings | Runtime configuration |
| WebSockets | Live communication |
| Folder Structure | Project organization |

Complete documentation is available inside the **docs/** directory.

---

# Quick Navigation

- Installation
- Running the Backend
- Running the Frontend
- Environment Variables
- API Reference
- AI Pipeline
- Reports
- Analytics
- Security
- Contributing

# Project Structure

```text
AeroGuard-AI
│
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── websocket/
│   │   └── utils/
│   │
│   ├── uploads/
│   ├── tests/
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── hooks/
│   │   ├── i18n/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── types/
│   │   └── utils/
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── docs/
│
├── README.md
└── LICENSE
```

> 📖 A complete description of every folder is available in **docs/FolderStructure.md**.

---

# Quick Start

Get AeroGuard AI running in just a few minutes.

## 1️⃣ Clone the Repository

```bash
git clone https://github.com/eslam-adel25/AeroGuard-AI.git
cd AeroGuard-AI
```

---

## 2️⃣ Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

### Windows

```powershell
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## 3️⃣ Configure Backend Environment

Create a `.env` file inside:

```text
backend/.env
```

Minimum required configuration:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/aeroguard_db

SECRET_KEY=your-secret-key

ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=60
```

> [!TIP]
> Never commit your `.env` file to Git.

---

## 4️⃣ Frontend Setup

Open another terminal.

```bash
cd frontend
```

Install dependencies.

```bash
npm install
```

---

## 5️⃣ Start the Backend

```bash
cd backend

uvicorn app.main:app --reload
```

Backend will be available at:

```
http://localhost:8000
```

Swagger UI:

```
http://localhost:8000/docs
```

ReDoc:

```
http://localhost:8000/redoc
```

---

## 6️⃣ Start the Frontend

```bash
cd frontend

npm run dev
```

Frontend:

```
http://localhost:5173
```

---

# Installation

## Development Environment

The project has been developed and verified using the following software versions.

| Software | Version |
|----------|----------|
| Python | 3.12.0 |
| Node.js | 24.12.0 |
| npm | 11.6.2 |
| PostgreSQL | Local Instance |

> [!NOTE]
> Other versions may work, but the versions above are the officially tested development environment.

---

# Running the Project

Once both servers are running:

Frontend

```
http://localhost:5173
```

Backend

```
http://localhost:8000
```

API Documentation

```
http://localhost:8000/docs
```

WebSocket

```
ws://localhost:8000/ws/dashboard
```

---

# Available Scripts

## Frontend

| Command | Description |
|----------|-------------|
| npm run dev | Start development server |
| npm run build | Production build |
| npm run preview | Preview production build |
| npm run lint | Run ESLint |

---

## Backend

Run development server:

```bash
uvicorn app.main:app --reload
```

Production example:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

# Environment Variables

## Backend

| Variable | Description |
|-----------|-------------|
| DATABASE_URL | PostgreSQL connection string |
| SECRET_KEY | JWT secret key |
| ALGORITHM | JWT algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | Access token lifetime |
| SMTP_HOST | SMTP server |
| SMTP_PORT | SMTP port |
| SMTP_USERNAME | SMTP username |
| SMTP_PASSWORD | SMTP password |
| MAIL_FROM | Sender email |
| FRONTEND_BASE | Frontend URL |
| REQUIRE_EMAIL_VERIFICATION | Enable email verification |

---

## Frontend

| Variable | Description |
|-----------|-------------|
| VITE_API_BASE_URL | Backend API URL |
| VITE_WS_BASE_URL | WebSocket URL |

Example:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1

VITE_WS_BASE_URL=ws://localhost:8000/ws/dashboard
```

---

# Development Workflow

```text
Clone Repository
        │
        ▼
Backend Setup
        │
        ▼
Configure .env
        │
        ▼
Run PostgreSQL
        │
        ▼
Start Backend
        │
        ▼
Start Frontend
        │
        ▼
Open Dashboard
```

---

# Before You Begin

Please ensure the following services are available before launching the application.

✅ PostgreSQL running

✅ Python virtual environment activated

✅ Backend dependencies installed

✅ Frontend dependencies installed

✅ Environment variables configured

✅ Internet connection (for AI model download if required)

---

> [!IMPORTANT]
>
> AeroGuard AI depends on both the FastAPI backend and the React frontend.
>
> Both services must be running simultaneously for the complete platform to function correctly.


# API Overview

AeroGuard AI exposes a RESTful API built with **FastAPI**, providing secure endpoints for authentication, camera management, AI events, reports, analytics, and user settings.

> 📖 Complete endpoint documentation is available in:
>
> **docs/API.md**

---

## API Base URL

Development

```text
http://localhost:8000/api/v1
```

Swagger UI

```text
http://localhost:8000/docs
```

ReDoc

```text
http://localhost:8000/redoc
```

---

## API Modules

| Module | Description |
|----------|-------------|
| Authentication | Login, registration, refresh tokens, email verification |
| Users | Profile management, password, avatar, sessions |
| Cameras | Camera CRUD, streaming, monitoring, zones |
| AI Events | AI detections, screenshots, manual events |
| Reports | Analytics, summaries, report generation, exports |
| Settings | Runtime configuration |
| WebSocket | Live dashboard updates |

---

## Authentication

The backend uses JWT authentication.

Typical flow:

```text
Register
      │
      ▼
Email Verification
      │
      ▼
Login
      │
      ▼
JWT Access Token
      │
      ▼
Protected API Requests
      │
      ▼
Refresh Token
```

---

## WebSocket

Live events are pushed through:

```text
ws://localhost:8000/ws/dashboard
```

Typical event types include:

- ai_event
- new_alert
- alarm_state
- camera_status
- ai_status

---

# AI Pipeline

AeroGuard AI processes every video stream through a multi-stage AI pipeline designed for real-time surveillance.

---

## Processing Flow

```text
Camera Input
      │
      ▼
Frame Capture
      │
      ▼
YOLOv8 Detection
      │
      ▼
Object Tracking
      │
      ▼
Rule Engine
      │
      ▼
Threat Classification
      │
      ▼
Database
      │
      ├────────► Reports
      │
      ├────────► Analytics
      │
      └────────► WebSocket Dashboard
```

---

## Detection Capabilities

Current implementation supports:

- Person Detection
- Vehicle Detection
- Backpack Detection
- Suitcase Detection
- Bag Detection
- Fire Detection
- Smoke Detection
- Object Tracking

---

## Intelligent Rule Engine

The Rule Engine evaluates detections and generates alerts for situations such as:

- Restricted Area Violations
- Wrong Direction Movement
- Loitering Detection
- Abandoned Bag Detection
- Critical Threat Classification

---

## AI Technologies

| Component | Technology |
|-----------|------------|
| Detection | YOLOv8 |
| Vision | OpenCV |
| Deep Learning | PyTorch |
| Numerical Processing | NumPy |

---

> 📖 Additional implementation details:
>
> **docs/AI.md**

---

# Database

The backend uses PostgreSQL through SQLAlchemy ORM.

---

## Main Entities

| Entity | Purpose |
|----------|----------|
| User | User accounts |
| Role | User permissions |
| Camera | Camera information |
| Detection | Detection history |
| AIEvent | Generated AI alerts |
| Tracking | Object tracking |
| Report | Generated reports |
| UserSettings | Runtime preferences |
| RefreshToken | Authentication |
| ActivityLog | User activity |

---

## Database Flow

```text
Detection
      │
      ▼
Database
      │
      ├────────► Reports
      ├────────► Dashboard
      ├────────► Analytics
      └────────► Alert History
```

---

> 📖 Complete schema:
>
> **docs/Database.md**

---

# Security

Security is implemented across multiple layers.

---

## Authentication

- JWT Access Tokens
- Refresh Tokens
- Email Verification
- Password Hashing
- Login Protection

---

## Authorization

- Role-Based Access Control (RBAC)
- Camera Ownership Validation
- Protected API Routes
- Permission Checks

---

## Password Security

Passwords are securely hashed before storage using **bcrypt**.

Passwords are never stored in plaintext.

---

## Transport Security

The backend supports:

- CORS Protection
- Secure HTTP Headers
- Static File Isolation
- JWT Validation

---

## Security Overview

```text
User
   │
   ▼
Authentication
   │
JWT Verification
   │
Permission Check
   │
Business Logic
   │
Database
```

---

> 📖 Additional details:
>
> **docs/Security.md**

---

# Localization

The frontend supports multilingual user interfaces using **i18next**.

Currently supported languages:

| Language | Status |
|-----------|--------|
| English | ✅ |
| Arabic | ✅ |

---

## Features

- Dynamic language switching
- Shared translation resources
- Client-side persistence
- Fully localized interface

---

## Translation Files

```text
frontend/src/i18n/
```

---

> 📖 Documentation:
>
> **docs/Localization.md**

---

# Notifications

AeroGuard AI provides real-time notifications using WebSocket communication.

---

## Notification Sources

- AI Detection Events
- Alarm Status
- Camera Status
- User Actions
- System Events

---

## Notification Flow

```text
AI Detection
      │
      ▼
Rule Engine
      │
      ▼
Database
      │
      ▼
WebSocket
      │
      ▼
Notification Center
      │
      ▼
Dashboard
```

---

## Notification Types

| Type | Description |
|-------|-------------|
| Success | Successful operation |
| Warning | Potential issue |
| Error | Failure |
| Info | Informational |
| Loading | Background operation |

---

> 📖 Complete implementation:
>
> **docs/WebSockets.md**
>
> **docs/Notifications.md**


---

# Reports & Analytics

AeroGuard AI transforms raw AI detections into actionable operational insights through an integrated reporting and analytics system.

## Reports

Generate comprehensive surveillance reports for a selected period.

### Supported Export Formats

| Format | Supported |
|----------|-----------|
| PDF | ✅ |
| Excel (.xlsx) | ✅ |
| CSV | ✅ |

Each report may include:

- Executive summary
- Detection statistics
- Severity distribution
- Camera activity
- Timeline visualization
- Event details
- Export history

> 📖 Complete documentation:
>
> **docs/Reports.md**

---

## Analytics Dashboard

The Analytics Dashboard provides real-time operational visibility.

### Available Metrics

- Total Detections
- Alert Count
- Threat Severity
- Detection Categories
- Camera Activity
- Top Cameras
- Timeline Analysis
- Recent Alerts

---

## Dashboard Overview

The dashboard is designed to give operators immediate awareness of the surveillance environment.

Main widgets include:

- Active Cameras
- Live Monitoring
- Current Alerts
- Detection Timeline
- Threat Distribution
- Camera Statistics
- Recent Activity
- System Status

---

# Documentation Hub

Detailed documentation is available in the **docs/** directory.

| Document | Description |
|----------|-------------|
| Architecture.md | System architecture |
| API.md | REST API documentation |
| AI.md | AI pipeline |
| Database.md | Database schema |
| Security.md | Authentication and authorization |
| Reports.md | Reporting engine |
| Settings.md | Runtime settings |
| FolderStructure.md | Repository organization |
| WebSockets.md | Real-time communication |
| Dependencies.md | External dependencies |
| Installation.md | Installation guide |
| Reference.md | Technical reference |

---

# Project Status

## Current Status

🟢 Active Development

Version:

```
v1.4
```

Project Type:

- Graduation Project
- Computer Vision
- Artificial Intelligence
- Smart Surveillance
- Full Stack Web Application

---

# Roadmap

## Completed

- Full Authentication System
- Email Verification
- Role-Based Access Control
- Camera Management
- AI Detection Pipeline
- WebSocket Communication
- Dashboard
- Analytics
- Reports
- Localization
- Notification System
- Rule Engine Integration

---

## In Progress

- Performance Optimization
- Documentation Improvements
- Production Readiness
- User Experience Enhancements

---

## Future Enhancements

- Docker Support
- Kubernetes Deployment
- Multi-Camera Tracking
- Face Recognition
- Mobile Application
- Cloud Deployment
- Distributed AI Processing
- Advanced Event Correlation

---

# Contributing

Contributions are welcome.

If you would like to contribute:

1. Fork the repository.
2. Create a feature branch.

```bash
git checkout -b feature/my-feature
```

3. Commit your changes.

```bash
git commit -m "feat: add new feature"
```

4. Push the branch.

```bash
git push origin feature/my-feature
```

5. Open a Pull Request.

Please ensure that:

- Code follows the existing style.
- Documentation is updated.
- Changes are focused and well documented.
- New functionality is tested.

---

# License

> [!NOTE]
>
> No license file is currently included in this repository.
>
> Add a LICENSE file (for example, MIT) if you intend to make the project open source.

---

# Author

<p align="center">

## Eslam Adel

Computer Science Student

Frontend Developer

AI & Full Stack Enthusiast

Graduation Project Developer

</p>

<p align="center">

<a href="https://github.com/eslam-adel25">
GitHub Profile
</a>

•

<a href="https://github.com/eslam-adel25/AeroGuard-AI">
Repository
</a>

</p>

---

# Acknowledgements

AeroGuard AI builds upon an excellent open-source ecosystem.

Special thanks to the maintainers of:

- FastAPI
- React
- Vite
- TypeScript
- PostgreSQL
- SQLAlchemy
- PyTorch
- OpenCV
- Ultralytics YOLOv8
- Tailwind CSS
- Recharts
- i18next
- FPDF
- openpyxl

Their work makes projects like AeroGuard AI possible.

---

# Support

If you encounter an issue or have a suggestion:

- Open a GitHub Issue
- Submit a Pull Request
- Contact the repository maintainer

---

<p align="center">

## AeroGuard AI

**AI-Powered Smart Surveillance Platform**

Designed and developed by **Eslam Adel**

Version **1.4**

</p>

<p align="center">

Made with ❤️ using

FastAPI • React • TypeScript • PostgreSQL • YOLOv8

</p>
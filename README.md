# 🛡️ AeroGuard AI

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?style=for-the-badge&logo=postgresql)
![YOLOv8](https://img.shields.io/badge/YOLOv8-AI-red?style=for-the-badge)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-green?style=for-the-badge&logo=opencv)
![License](https://img.shields.io/badge/License-MIT-success?style=for-the-badge)

### AI-Powered Smart Airport Surveillance Platform

Real-time intelligent surveillance system powered by Computer Vision, Deep Learning, and Modern Web Technologies.

</div>

---

# 📌 Overview

**AeroGuard AI** is an intelligent surveillance platform designed to enhance airport security using Artificial Intelligence and Computer Vision.

The system continuously monitors live camera streams, detects security threats in real time, and delivers instant alerts through an interactive dashboard.

Rather than relying solely on human operators, AeroGuard AI assists security teams by providing automated detection, tracking, reporting, and analytics.

---

# ✨ Key Features

## 🎥 Intelligent Video Surveillance

- Real-time camera monitoring
- Live object detection
- AI-powered threat recognition
- Multi-camera management
- Secure streaming

---

## 🧠 Artificial Intelligence

- YOLOv8 Object Detection
- Deep Learning-based Computer Vision
- Face Detection
- Face Recognition
- Real-time AI Inference
- Confidence-based Filtering

---

## 🚨 Security Monitoring

- Threat Detection
- Suspicious Object Detection
- Restricted Zone Monitoring
- Instant Alerts
- Alert Prioritization
- Security Event Logging

---

## 📊 Analytics Dashboard

- Real-time Detection Statistics
- Detection Timeline
- Threat Distribution
- Historical Reports
- AI Performance Metrics
- Interactive Charts

---

## 👤 User Management

- JWT Authentication
- Role-Based Access Control (RBAC)
- Administrator
- Supervisor
- Security Officer

---

## ⚙️ System Management

- Camera Configuration
- AI Configuration
- Detection Threshold Control
- Recording Settings
- Security Policies

---

# 🏗️ System Architecture

```
                Cameras
                   │
                   ▼
           OpenCV Video Stream
                   │
                   ▼
          YOLOv8 AI Detection
                   │
                   ▼
        Threat Decision Engine
                   │
                   ▼
          FastAPI Backend API
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
 PostgreSQL Database     WebSocket Server
        │                     │
        └──────────┬──────────┘
                   ▼
          React Dashboard
```

---

# 🛠️ Tech Stack

## Frontend

- React
- TypeScript
- Tailwind CSS
- Axios
- Recharts
- Lucide Icons

---

## Backend

- FastAPI
- SQLAlchemy
- Pydantic
- JWT Authentication
- WebSocket
- Uvicorn

---

## AI & Computer Vision

- YOLOv8
- OpenCV
- DeepFace
- NumPy
- Pillow

---

## Database

- PostgreSQL

---

## Authentication

- JWT Tokens
- BCrypt Password Hashing
- Role-Based Access Control

---

# 📂 Project Structure

```
AeroGuard-AI/

├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── websocket/
│   └── uploads/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── assets/
│
└── README.md
```

---

# 🔐 Security Features

- JWT Authentication
- Password Hashing (BCrypt)
- Protected API Endpoints
- Secure WebSocket Connections
- Role-Based Authorization
- Input Validation
- SQL Injection Protection

---

# 📈 Current Capabilities

- ✅ User Authentication
- ✅ Dashboard
- ✅ Live Camera Monitoring
- ✅ Real-Time AI Detection
- ✅ WebSocket Communication
- ✅ Reports System
- ✅ Analytics
- ✅ Camera Management
- ✅ User Profiles
- ✅ System Settings

---

# 🚀 Future Improvements

- Multi-Camera Tracking
- Person Re-Identification
- Crowd Density Analysis
- License Plate Recognition
- Drone Surveillance Integration
- AI Behavior Analysis
- SMS Notifications
- Email Alerts
- Mobile Application
- Cloud Deployment

---

# 🎯 Project Goals

- Improve airport security.
- Reduce human monitoring workload.
- Detect threats in real time.
- Provide actionable AI insights.
- Build a scalable smart surveillance platform.

---

# 💻 Installation

## Clone Repository

```bash
git clone https://github.com/eslam-adel25/AeroGuard-AI.git
```

---

## Backend

```bash
cd backend

python -m venv .venv

pip install -r requirements.txt

uvicorn main:app --reload
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

---

# 📸 Screenshots

> Screenshots of the Dashboard, Analytics, Reports, Camera Monitoring, and AI Detection will be added soon.

---

# 👨‍💻 Contributors

- **Eslam Adel**
- Graduation Project Team

---

# 📚 Academic Context

This project is being developed as a Graduation Project for the Faculty of Computers and Artificial Intelligence.

The primary objective is to demonstrate practical applications of Artificial Intelligence, Computer Vision, and Modern Full-Stack Development in airport surveillance systems.

---

# ⭐ Support

If you find this project useful, consider giving it a ⭐ on GitHub.

---

<div align="center">

## AeroGuard AI

### Smart Surveillance. Intelligent Decisions. Safer Airports.

</div>

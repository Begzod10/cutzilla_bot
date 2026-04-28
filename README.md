# Cutzilla Bot & Mini App ✂️🤖

Professional barber booking system integrated with Telegram. This project features a powerful Telegram Bot for notifications and a smooth Telegram Mini App (Web App) for a premium booking experience.

## 🌟 Features

- **Telegram Mini App (TMA)**: A sleek, mobile-first interface for users to browse barbers, view services, and book appointments.
- **Dual-Backend Architecture**: 
  - **Django**: Handles complex administration, database management, and user roles.
  - **FastAPI**: Provides a high-performance asynchronous API for the Mini App and real-time features.
- **Dynamic Booking System**: Real-time availability tracking and seamless booking flow.
- **Referral Program**: Built-in referral system where users can invite friends and earn bonuses.
- **Automated Notifications**: Instant Telegram notifications for booking confirmations and updates.

## 🛠 Tech Stack

- **Backends**: Python ([Django](https://wwww.djangoproject.com/) & [FastAPI](https://fastapi.tiangolo.com/))
- **Frontend**: React, Vite, Lucide Icons, Axios
- **Database**: PostgreSQL
- **Integration**: Telegram Bot API, Telegram WebApps API

## 📁 Repository Structure

To maintain professional standards, the repository is organized as follows:

- `api/`, `apps/`, `core/` - Django backend components.
- `src/` - FastAPI backend source code.
- `mini-app/` - React-based Telegram Mini App source code.
- `scripts/` - Maintenance and utility scripts (database initialization, test data, etc.).
- `archive/` - Archived/legacy components.
- `manage.py` - Django management CLI.
- `requirements.txt` - Project dependencies.

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL
- Node.js & npm (for frontend)

### Initialization

1. **Environment Setup**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual database and secret credentials
   ```

2. **Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Setup**:
   ```bash
   python manage.py migrate
   # Use scripts for specialized setup
   python scripts/setup_database.py
   ```

### Running the Project

- **Django Admin**: `python manage.py runserver`
- **FastAPI Backend**: `uvicorn src.main:app --reload`
- **Frontend (Mini App)**: `cd mini-app && npm run dev`

---
Developed with ❤️ by Begzod (Cutzilla Team)

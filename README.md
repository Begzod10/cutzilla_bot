# Cutzilla Bot & Mini App ✂️🤖

Professional barber booking system integrated with Telegram. This project features a powerful Telegram Bot for notifications and a smooth Telegram Mini App (Web App) for a premium booking experience.

## 🌟 Features

- **Telegram Mini App (TMA)**: A sleek, mobile-first interface for users to browse barbers, view services, and book appointments.
- **Dynamic Booking System**: Real-time availability tracking and seamless booking flow.
- **Referral Program**: Built-in referral system where users can invite friends and earn bonuses.
- **Admin Dashboard**: Comprehensive Django-based administration panel to manage barbers, clients, and bookings.
- **Automated Notifications**: Instant Telegram notifications for booking confirmations and updates.
- **Role-based Access**: Specialized interfaces for Clients, Barbers, and Admins.

## 🛠 Tech Stack

- **Backend**: Python, [Django](https://wwww.djangoproject.com/)
- **Frontend**: React, Vite, Lucide Icons, Axios
- **Database**: SQLite (Development) / PostgreSQL (Production)
- **Integration**: Telegram Bot API, Telegram WebApps API
- **Styling**: Modern CSS with a focus on premium aesthetics (Apple-style design)

## 📁 Project Structure

- `core/` - Django project configuration and settings.
- `apps/` - Django application logic (models, views, serializers).
- `mini-app/` - React-based Telegram Mini App source code.
- `cutzilla_bot/` - Telegram bot interaction logic.
- `src/` - Shared utilities and models.
- `requirements.txt` - Python dependencies.

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js & npm (for frontend)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### Backend Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run migrations:
   ```bash
   python manage.py migrate
   ```

3. Start the server:
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

1. Navigate to the mini-app directory:
   ```bash
   cd mini-app
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the dev server:
   ```bash
   npm run dev
   ```

## 📄 License

This project is licensed under the MIT License.

---
Developed with ❤️ by Begzod (Cutzilla Team)

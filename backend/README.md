# Mind Bridge AI - Backend

A comprehensive FastAPI backend for the Mind Bridge AI mental health and wellness platform.

## Features

- **FastAPI**: Modern, fast web framework for building APIs
- **Socket.IO**: Real-time bidirectional communication
- **PostgreSQL + SQLite**: Primary database with SQLite fallback
- **Redis**: Caching and message broker
- **Celery**: Background task processing
- **JWT Authentication**: Secure user authentication
- **SQLAlchemy**: Database ORM with connection pooling
- **Alembic**: Database migrations
- **Health Checks**: Comprehensive health monitoring

## Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management
├── database.py            # Database connection and session management
├── models.py              # SQLAlchemy models
├── auth.py                # JWT authentication and user management
├── websockets.py          # Socket.IO event handlers
├── celery_app.py          # Celery configuration
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── tasks/                # Background task modules
│   ├── __init__.py
│   ├── ai_processing.py  # AI model inference tasks
│   ├── notifications.py  # Email and notification tasks
│   ├── analytics.py      # Analytics and reporting tasks
│   └── maintenance.py    # System maintenance tasks
└── README.md             # This file
```

## Quick Start

### 1. Prerequisites

- Python 3.8+
- PostgreSQL 15+ (optional, SQLite fallback available)
- Redis 7+
- Docker & Docker Compose (recommended)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/deepakuy/mindbridge-ai-hackathon.git
cd mindbridge-ai-hackathon/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Setup

```bash
# Copy environment template
cp env.example .env

# Edit .env with your configuration
# Key variables to set:
# - SECRET_KEY: Generate a secure random key
# - DATABASE_URL: PostgreSQL connection string
# - REDIS_URL: Redis connection string
```

### 4. Database Setup

```bash
# Initialize database tables
python -c "from database import init_db; init_db()"

# Or run with Alembic (if migrations are set up)
alembic upgrade head
```

### 5. Running the Application

#### Development Mode

```bash
# Start the FastAPI server
python main.py

# In separate terminals, start:
# Redis server
redis-server

# Celery worker
celery -A celery_app worker --loglevel=info

# Celery beat (for scheduled tasks)
celery -A celery_app beat --loglevel=info
```

#### Using Docker Compose

```bash
# From project root
docker-compose up -d

# Check logs
docker-compose logs -f backend
```

### 6. API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - User logout

### Users
- `GET /api/v1/users/me` - Get current user info
- `PUT /api/v1/users/me` - Update user profile
- `POST /api/v1/users/change-password` - Change password

### Chat Sessions
- `GET /api/v1/sessions` - Get user sessions
- `POST /api/v1/sessions` - Create new session
- `GET /api/v1/sessions/{id}` - Get session details
- `PUT /api/v1/sessions/{id}` - Update session
- `DELETE /api/v1/sessions/{id}` - Delete session

### Messages
- `GET /api/v1/sessions/{id}/messages` - Get session messages
- `POST /api/v1/sessions/{id}/messages` - Send message
- `PUT /api/v1/messages/{id}` - Edit message
- `DELETE /api/v1/messages/{id}` - Delete message

## WebSocket Events

### Client Events
- `connect` - Connect to server
- `disconnect` - Disconnect from server
- `join_session` - Join a chat session
- `leave_session` - Leave a chat session
- `send_message` - Send a message
- `typing_start` - Start typing indicator
- `typing_stop` - Stop typing indicator

### Server Events
- `connected` - Connection confirmation
- `session_joined` - Session join confirmation
- `message_received` - New message received
- `ai_response` - AI response generated
- `user_typing` - User typing status
- `notification` - System notification

## Background Tasks

### AI Processing
- `generate_ai_response` - Generate AI response for user message
- `analyze_message_sentiment` - Analyze message sentiment
- `update_model_cache` - Update AI model cache

### Notifications
- `send_welcome_email` - Send welcome email to new users
- `send_weekly_digest` - Send weekly digest to active users
- `send_password_reset_email` - Send password reset email

### Analytics
- `generate_daily_report` - Generate daily analytics report
- `analyze_user_engagement` - Analyze user engagement metrics

### Maintenance
- `cleanup_expired_sessions` - Archive expired sessions
- `backup_user_data` - Create user data backup
- `cleanup_old_logs` - Clean up old log files
- `optimize_database` - Optimize database performance

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `SQLITE_URL` | SQLite fallback database | `sqlite:///./dev.db` |
| `USE_SQLITE_FALLBACK` | Enable SQLite fallback | `true` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `SECRET_KEY` | JWT secret key | `your-secret-key` |
| `DEBUG` | Debug mode | `true` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |

### Database Configuration

The application supports both PostgreSQL and SQLite:

- **Primary**: PostgreSQL with connection pooling
- **Fallback**: SQLite for development/testing
- **Auto-fallback**: Automatically falls back to SQLite if PostgreSQL is unavailable

### Security Features

- JWT-based authentication
- Password hashing with bcrypt
- CORS protection
- Rate limiting
- Input validation with Pydantic
- SQL injection protection with SQLAlchemy

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Code Quality

```bash
# Install development tools
pip install black isort flake8 mypy

# Format code
black .
isort .

# Lint code
flake8 .
mypy .
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

### Environment Variables for Production

```bash
# Production settings
DEBUG=false
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://user:pass@db:5432/mindbridge_prod
REDIS_URL=redis://redis:6379
LOG_LEVEL=INFO
```

## Monitoring

### Health Checks

- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health check with service status

### Logging

- Structured logging with configurable levels
- Request/response logging
- Error tracking and reporting
- Performance metrics

### Metrics

- Database connection pool status
- Celery task queue status
- API response times
- Error rates

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running
   - Verify connection string
   - Check firewall settings

2. **Redis Connection Failed**
   - Ensure Redis server is running
   - Check Redis URL configuration

3. **Celery Tasks Not Processing**
   - Verify Celery worker is running
   - Check Redis broker connection
   - Review task queue status

4. **WebSocket Connection Issues**
   - Check CORS settings
   - Verify authentication token
   - Review network configuration

### Debug Mode

Enable debug mode for detailed logging:

```bash
DEBUG=true LOG_LEVEL=DEBUG python main.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# PlanetTerp Chatbot Backend

A FastAPI backend for the PlanetTerp chatbot that provides intelligent course and professor recommendations for UMD students.

## Features

- **AI-Powered Chat**: Uses Google Gemini AI for natural language conversations
- **Course Search**: Semantic search for UMD courses using sentence transformers
- **Professor Data**: Access to professor ratings, reviews, and course information
- **Grade Analytics**: Recent grade distributions and course performance data
- **User Management**: JWT-based authentication and chat history
- **Caching**: Redis-based caching for improved performance
- **PlanetTerp Integration**: Real-time data from PlanetTerp API

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and configure your settings:

```bash
cp env.example .env
```

Edit `.env` with your configuration:

```env
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///./planet_terp_chatbot.db
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-change-this-in-production
```

### 3. Run the Application

```bash
python run.py
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- **Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/token` - Login and get access token
- `GET /auth/me` - Get current user info

### Chat
- `POST /chat/chats` - Create a new chat
- `GET /chat/chats` - Get user's chats
- `GET /chat/chats/{chat_id}` - Get specific chat
- `POST /chat/chats/{chat_id}/messages` - Send message and get AI response
- `GET /chat/chats/{chat_id}/messages` - Get chat messages
- `DELETE /chat/chats/{chat_id}` - Delete chat

### Courses
- `GET /courses/courses` - Get all courses
- `GET /courses/search` - Search courses
- `GET /courses/{course_id}` - Get course details
- `GET /courses/{course_id}/grades` - Get course grades
- `GET /courses/professors/{professor_name}` - Get professor details
- `GET /courses/extract-course-ids` - Extract course IDs from text

## Architecture

### Services

- **PlanetTerpService**: Handles API calls to PlanetTerp
- **GeminiService**: Manages AI responses using Google Gemini
- **SearchService**: Provides semantic search functionality
- **CacheService**: Manages Redis caching

### Models

- **User**: User authentication and profile
- **Chat**: Chat sessions
- **Message**: Individual chat messages
- **Course**: Course information
- **Professor**: Professor data and reviews
- **Grade**: Grade distributions

### Key Features

1. **Semantic Search**: Uses sentence transformers to understand course queries
2. **Context-Aware Responses**: Maintains chat history for better conversations
3. **Recent Data Focus**: Prioritizes recent grades and reviews (last 4 years)
4. **Caching**: Redis caching for improved performance
5. **Error Handling**: Comprehensive error handling and logging

## Development

### Database Migrations

The application uses SQLAlchemy with automatic table creation. For production, consider using Alembic for migrations.

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Deployment

For production deployment:

1. Use a production database (PostgreSQL recommended)
2. Configure Redis for caching
3. Set up proper CORS origins
4. Use environment variables for sensitive data
5. Enable HTTPS
6. Set up monitoring and logging

## Integration with Frontend

This backend is designed to work with the Streamlit frontend. The API provides:

- RESTful endpoints for all chatbot functionality
- JWT authentication for user sessions
- Real-time course and professor data
- AI-powered chat responses

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

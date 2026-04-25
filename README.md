# 🐢 PlanetTerp Chatbot

A modern, intelligent chatbot for UMD students to get course and professor recommendations. Built with Next.js frontend and FastAPI backend, powered by PlanetTerp data and Google Gemini AI.

## ✨ Features

- **🤖 AI-Powered Chat**: Intelligent responses using Google Gemini AI
- **📚 Course Search**: Find courses by name, department, or description
- **👨‍🏫 Professor Ratings**: Get detailed professor information and ratings
- **📊 Grade Analytics**: View recent grade distributions and course performance
- **🎨 Modern UI**: Beautiful, responsive interface built with Next.js and Tailwind CSS
- **⚡ Real-time**: Fast responses with semantic search capabilities

## 🏗️ Project Structure

```
planet-terp-chatbot-v2/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── main.py         # FastAPI app
│   ├── planetterp_core.py  # Core PlanetTerp integration
│   └── requirements.txt    # Python dependencies
├── frontend/               # Next.js frontend
│   ├── src/
│   │   └── app/           # Next.js app directory
│   └── package.json       # Node.js dependencies
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- Google Gemini API key

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

4. **Start the backend server:**
   ```bash
   python run.py
   # or
   uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

4. **Open your browser:**
   Visit [http://localhost:3000](http://localhost:3000)

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///./planet_terp_chatbot.db
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-change-this-in-production
```

### API Endpoints

- `GET /` - Health check
- `GET /health` - Server status
- `POST /chat` - Send message to chatbot

## 💬 Usage Examples

### Course Information
- "Tell me about CMSC131"
- "What are the prerequisites for MATH140?"
- "Show me computer science courses"

### Professor Recommendations
- "Who are the best professors for CMSC330?"
- "Tell me about Professor Nelson Padua-Perez"
- "Compare professors for MATH241"

### Grade Information
- "What's the average GPA for CMSC131?"
- "Show me grade distributions for MATH140"

## 🛠️ Development

### Backend Development

The backend uses FastAPI with the following key components:

- **PlanetTerp Integration**: Fetches real-time course and professor data
- **Semantic Search**: Uses sentence transformers for intelligent course matching
- **Gemini AI**: Powers the conversational responses
- **Caching**: Redis-based caching for improved performance

### Frontend Development

The frontend is built with:

- **Next.js 15**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Lucide React**: Beautiful icons
- **Framer Motion**: Smooth animations

### Adding New Features

1. **Backend**: Add new endpoints in `backend/app/api/`
2. **Frontend**: Create new components in `frontend/src/components/`
3. **Integration**: Update the API calls in the frontend

## 📦 Deployment

### Backend Deployment

1. **Production Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Setup:**
   - Set production environment variables
   - Configure database (PostgreSQL recommended)
   - Set up Redis for caching

3. **Run with Gunicorn:**
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

### Frontend Deployment

1. **Build the application:**
   ```bash
   npm run build
   ```

2. **Start production server:**
   ```bash
   npm start
   ```

3. **Deploy to Vercel/Netlify:**
   - Connect your repository
   - Set build command: `npm run build`
   - Set output directory: `.next`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [PlanetTerp](https://planetterp.com/) for providing course and professor data
- [Google Gemini AI](https://ai.google.dev/) for intelligent responses
- [University of Maryland](https://umd.edu/) for the amazing community

## 🐛 Troubleshooting

### Common Issues

1. **Backend not starting:**
   - Check if port 8001 is available
   - Verify GEMINI_API_KEY is set correctly
   - Ensure all dependencies are installed

2. **Frontend not connecting to backend:**
   - Verify backend is running on port 8001
   - Check CORS settings in backend
   - Ensure API endpoints are accessible

3. **ML libraries not working:**
   - The app will work without ML libraries (semantic search disabled)
   - For full functionality, install PyTorch and sentence-transformers

### Getting Help

- Check the [Issues](https://github.com/yourusername/planet-terp-chatbot/issues) page
- Create a new issue with detailed error information
- Join the UMD CS community for support

---

**Made with ❤️ for UMD students** 🐢
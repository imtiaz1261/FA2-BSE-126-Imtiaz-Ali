# Personalized Recommendation Chat Assistant

A production-ready AI recommendation system that learns from user preferences and provides personalized conversational recommendations using embeddings, vector databases, and LLMs.

## Features

- **User Profiles**: Track explicit preferences, interests, dislikes, and behavioral signals
- **Embeddings**: OpenAI embeddings with pgvector for semantic similarity
- **Personalized Retrieval**: Vector similarity + preference-based ranking
- **Conversational Memory**: Maintain conversation history and learning
- **Feedback Learning**: Like/reject/rate recommendations to improve future suggestions
- **Multi-User Support**: Different recommendations for different user profiles
- **LLM Explanations**: Understand why each recommendation was selected
- **Production Architecture**: FastAPI backend, Streamlit frontend, PostgreSQL database

## Tech Stack

- **LLM**: OpenAI GPT-4 + Groq Mixtral (fallback)
- **Embeddings**: OpenAI text-embedding-3-small
- **Database**: PostgreSQL + pgvector
- **Backend**: FastAPI
- **Frontend**: Streamlit
- **ORM**: SQLAlchemy

## Project Structure

```
.
├── config.py                 # Configuration and settings
├── models.py                 # SQLAlchemy database models
├── embedding_service.py      # OpenAI embeddings service
├── recommendation_engine.py  # Recommendation logic and ranking
├── user_service.py           # User profile management
├── conversation_service.py   # Conversation and memory management
├── database.py               # Database connection and initialization
├── api.py                    # FastAPI backend
├── streamlit_app.py          # Streamlit frontend
├── catalog_loader.py         # Load sample catalog
├── simulated_users.py        # Create simulated user profiles
├── evaluation.py             # Recommendation quality metrics
├── requirements.txt
├── .env.example
└── README.md
```

## Setup & Installation

1. **Clone and install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL with pgvector**:
   ```bash
   # Create database
   createdb recommendation_db
   
   # Install pgvector extension
   psql recommendation_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database URL and API keys
   ```

4. **Initialize database**:
   ```bash
   python -c "from database import init_db; init_db()"
   ```

5. **Load sample catalog**:
   ```bash
   python catalog_loader.py
   ```

6. **Create simulated users**:
   ```bash
   python simulated_users.py
   ```

## Running the System

### Option 1: Backend API Only (for testing)
```bash
python api.py
# Server runs on http://localhost:8000
```

### Option 2: Full Stack (API + Streamlit)
```bash
# Terminal 1: Start FastAPI
python api.py

# Terminal 2: Start Streamlit
streamlit run streamlit_app.py
```

## API Endpoints

- `GET /health` - Health check
- `GET /users/{user_id}` - Get user profile
- `GET /users/{user_id}/preferences` - Get user preferences
- `POST /chat/{user_id}` - Send message and get recommendations
- `POST /feedback/{user_id}/{item_id}` - Provide feedback on recommendation
- `GET /recommendations/{user_id}` - Get current recommendations
- `GET /profile/{user_id}` - View full user profile with embeddings
- `GET /evaluate` - Get evaluation metrics

## Usage Examples

### 1. Get Recommendations for a User
```bash
curl -X POST http://localhost:8000/chat/user_1 \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to learn Python and machine learning"}'
```

### 2. Provide Feedback
```bash
curl -X POST http://localhost:8000/feedback/user_1/item_5 \
  -H "Content-Type: application/json" \
  -d '{"feedback_type": "like", "rating": 4.5}'
```

### 3. View User Profile
```bash
curl http://localhost:8000/profile/user_1
```

## Simulated Users

### User A (Tech Enthusiast)
- Interests: AI, Python, RAG, Machine Learning, LangChain, Programming
- Behavior: Accepts advanced technical courses, rejects beginner content
- Dislikes: Non-technical entertainment

### User B (Entertainment Lover)
- Interests: Movies, Comedy, Drama, Entertainment, Music
- Behavior: Prefers movies and entertainment, rejects technical content
- Dislikes: Programming, tutorials

## Recommendation Flow

```
User Query
    ↓
Intent Understanding (LLM)
    ↓
Load User Profile + Embeddings
    ↓
Generate Query Embedding
    ↓
Vector Similarity Search (pgvector)
    ↓
Retrieve Candidate Items
    ↓
Apply Preference Filters & Behavioral Signals
    ↓
Rank by: Similarity + Preference + Feedback History
    ↓
LLM Personalized Explanation
    ↓
Return Top-N Recommendations
    ↓
User Feedback Loop (Learning)
    ↓
Update User Profile & Embeddings
```

## Evaluation Metrics

- **Relevance Score**: How relevant recommendations are to user interests
- **Personalization Score**: How much recommendations differ between users
- **Acceptance Rate**: Percentage of recommendations user likes
- **Rejection Rate**: Percentage of recommendations user rejects
- **Top-K Quality**: Quality of top-5 recommendations

## Key Features Demonstrated

1. ✅ User Profile Management with explicit & implicit signals
2. ✅ Embedding-based Personalization
3. ✅ Vector Database (pgvector)
4. ✅ Conversational Memory
5. ✅ Feedback Learning Loop
6. ✅ Multi-User Personalization
7. ✅ LLM Explanations (Explainable AI)
8. ✅ Production-Ready Architecture
9. ✅ Quality Evaluation

## Development Notes

- Uses OpenAI embeddings for high-quality semantic representations
- Falls back to Groq API for LLM if OpenAI unavailable
- Implements semantic similarity with configurable thresholds
- Maintains conversation history for contextual recommendations
- Uses pgvector for efficient similarity search at scale
- Timestamps all interactions for behavioral analysis

## License

MIT

@echo off
echo Setting up GraphRAG system...
echo.

echo 1. Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

echo 2. Installing dependencies...
pip install -r requirements.txt

echo 3. Downloading spaCy model...
python -m spacy download en_core_web_sm

echo 4. Copying environment file...
if not exist .env (
    copy .env.example .env
    echo Please edit .env file and add your OpenAI API key
) else (
    echo .env file already exists
)

echo.
echo Setup complete!
echo.
echo To run the system:
echo 1. Start Neo4j Desktop
echo 2. Create database with password: password123
echo 3. Run: python main.py
echo.
pause
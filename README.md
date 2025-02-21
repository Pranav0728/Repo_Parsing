# Repository Code Parsing

This project parses and analyzes code repositories using `gitingest`. It sets up a FastAPI server to process and store repository data.

## Features
- Parses repository code structure
- Extracts metadata and dependencies
- Provides API endpoints for analysis

## Setup Instructions

### 1. Create a Virtual Environment
First, create and activate a Python virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate    # On Windows
```

### 2. Install Dependencies

After activating the virtual environment, install the required dependencies:

```bash
pip install -r requirements.txt
```

### 3. Run the FastAPI Server

Start the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Usage

1. Ensure the server is running.
2. Send API requests to analyze repository code.
3. Use the provided endpoints for code parsing and insights.
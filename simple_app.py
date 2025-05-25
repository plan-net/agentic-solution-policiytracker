#!/usr/bin/env python3
"""
Simple FastAPI version of Political Monitoring Agent (without Kodosumi).
For development when Kodosumi has dependency conflicts.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(
    title="Political Monitoring Agent (Simple)",
    description="Simple FastAPI version for development",
    version="0.1.0"
)

# Simple HTML form
FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Political Monitoring Agent</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select, textarea { width: 100%; padding: 8px; margin-bottom: 5px; }
        button { background-color: #4CAF50; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        button:hover { background-color: #45a049; }
        .tip { color: #666; font-size: 0.9em; margin-top: 5px; }
    </style>
</head>
<body>
    <h1>📊 Political Document Analysis</h1>
    <p>Analyze political documents for relevance, priority, and topics using distributed AI processing.</p>
    
    <form action="/analyze" method="post">
        <div class="form-group">
            <label for="job_name">📋 Analysis Job Name:</label>
            <input type="text" id="job_name" name="job_name" required placeholder="e.g., Q4 Regulatory Review, GDPR Update Analysis">
            <div class="tip">💡 Use descriptive names to easily identify your analysis results later.</div>
        </div>

        <div class="form-group">
            <label for="priority_threshold">🎯 Priority Threshold (%):</label>
            <input type="number" id="priority_threshold" name="priority_threshold" min="0" max="100" step="5" value="70">
            <div class="tip">📊 Documents scoring above this threshold will be highlighted in your report.</div>
        </div>

        <div class="form-group">
            <label>
                <input type="checkbox" name="include_low_confidence" value="true">
                🔍 Include Low Confidence Results
            </label>
            <div class="tip">Include documents where the AI is less certain about relevance (confidence < 80%)</div>
        </div>

        <div class="form-group">
            <label>
                <input type="checkbox" name="clustering_enabled" value="true" checked>
                🗂️ Enable Topic Clustering
            </label>
            <div class="tip">Automatically group similar documents into topic clusters for better organization</div>
        </div>

        <div class="form-group">
            <label for="storage_mode">💾 Document Storage Location:</label>
            <select id="storage_mode" name="storage_mode">
                <option value="local">📁 Local Files (data/input folder)</option>
                <option value="azure">☁️ Azure Blob Storage (production mode)</option>
            </select>
            <div class="tip">🏠 Local Mode: Uses documents from your local data/input folder</div>
        </div>

        <button type="submit">🚀 Start Analysis</button>
    </form>

    <h2>📚 Quick Links</h2>
    <ul>
        <li><a href="/health">Health Check</a></li>
        <li><a href="/docs">API Documentation</a></li>
    </ul>

    <p><strong>Note:</strong> This is a simplified version for development. For full Kodosumi features, use <code>just dev</code></p>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_form():
    """Display the analysis form."""
    return FORM_HTML

@app.post("/analyze")
async def analyze_documents(
    job_name: str = Form(...),
    priority_threshold: float = Form(70.0),
    include_low_confidence: bool = Form(False),
    clustering_enabled: bool = Form(True),
    storage_mode: str = Form("local")
):
    """Handle form submission - mock analysis for development."""
    
    # Validate inputs
    if not job_name or len(job_name) < 3:
        raise HTTPException(status_code=400, detail="Job name must be at least 3 characters")
    
    if not 0 <= priority_threshold <= 100:
        raise HTTPException(status_code=400, detail="Priority threshold must be between 0 and 100")
    
    if storage_mode not in ["local", "azure"]:
        raise HTTPException(status_code=400, detail="Invalid storage mode")
    
    # Mock response for development
    return {
        "status": "success",
        "message": "Analysis job submitted successfully (mock response)",
        "job_config": {
            "job_name": job_name,
            "priority_threshold": priority_threshold,
            "include_low_confidence": include_low_confidence,
            "clustering_enabled": clustering_enabled,
            "storage_mode": storage_mode
        },
        "note": "This is a development mock. Use 'just dev' for full Kodosumi workflow."
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "political-monitoring-agent-simple",
        "version": "0.1.0",
        "mode": "development"
    }

if __name__ == "__main__":
    print("🚀 Starting Simple FastAPI version...")
    print("🌐 Access at: http://localhost:8000")
    print("📋 Form: http://localhost:8000/")
    print("🔍 Health: http://localhost:8000/health")
    print("📚 Docs: http://localhost:8000/docs")
    print("💡 For full features, use: just dev")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
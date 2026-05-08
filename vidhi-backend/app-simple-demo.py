"""
VIDHI Backend - Lightweight Demo Version
This is a simplified version without heavy ML dependencies for quick testing
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from datetime import datetime

app = FastAPI(title="VIDHI Legal Assistant API - Demo")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    language: str = "en"
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    audio_url: Optional[str] = None
    sources: List[str] = []

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

# Demo responses for different queries
DEMO_RESPONSES = {
    "rights": "As per the Indian Constitution, you have fundamental rights including Right to Equality (Article 14-18), Right to Freedom (Article 19-22), Right against Exploitation (Article 23-24), Right to Freedom of Religion (Article 25-28), Cultural and Educational Rights (Article 29-30), and Right to Constitutional Remedies (Article 32).",
    "tenant": "As a tenant in India, you have several rights: 1) Right to a written rental agreement, 2) Right to privacy and peaceful possession, 3) Protection against arbitrary eviction, 4) Right to basic amenities, 5) Right to get your security deposit back. The Rent Control Acts in various states provide additional protections.",
    "police": "If detained by police, remember your D.K. Basu rights: 1) Right to know grounds of arrest, 2) Right to inform family/friend, 3) Right to legal counsel, 4) Right against torture, 5) Right to medical examination, 6) Right to be produced before magistrate within 24 hours. You can remain silent except for basic identification.",
    "rti": "The Right to Information Act, 2005 empowers citizens to seek information from public authorities. You can file an RTI application by: 1) Writing to the Public Information Officer, 2) Paying ₹10 fee, 3) Response within 30 days. Information related to life and liberty must be provided within 48 hours.",
    "default": "I'm VIDHI, your AI legal assistant. I can help you understand Indian laws, your rights, and legal procedures. Ask me about tenant rights, police procedures, RTI, consumer rights, or any legal topic!"
}

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0-demo"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0-demo"
    }

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint - returns demo responses based on keywords
    """
    message = request.message.lower()
    
    # Determine response based on keywords
    response_text = DEMO_RESPONSES["default"]
    
    if any(word in message for word in ["right", "rights", "fundamental"]):
        response_text = DEMO_RESPONSES["rights"]
    elif any(word in message for word in ["tenant", "rent", "landlord", "evict"]):
        response_text = DEMO_RESPONSES["tenant"]
    elif any(word in message for word in ["police", "arrest", "detention", "custody"]):
        response_text = DEMO_RESPONSES["police"]
    elif any(word in message for word in ["rti", "information", "government"]):
        response_text = DEMO_RESPONSES["rti"]
    
    return {
        "response": response_text,
        "audio_url": None,  # Audio not available in demo mode
        "sources": ["Indian Constitution", "Legal Database"]
    }

@app.post("/api/v1/auth/guest")
async def guest_login():
    """Create guest session"""
    return {
        "user_id": f"guest_{datetime.now().timestamp()}",
        "token": "demo_token",
        "expires_in": 3600
    }

@app.get("/api/v1/schemes")
async def get_schemes():
    """Get government schemes"""
    return {
        "schemes": [
            {
                "name": "PM-KISAN",
                "description": "Direct income support to farmers",
                "eligibility": "Small and marginal farmers"
            },
            {
                "name": "Ayushman Bharat",
                "description": "Health insurance for poor families",
                "eligibility": "Families below poverty line"
            }
        ]
    }

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 VIDHI Backend - Demo Mode")
    print("=" * 60)
    print("✅ Lightweight version without ML dependencies")
    print("✅ Perfect for UI testing and development")
    print("=" * 60)
    print("📍 Server: http://localhost:8000")
    print("📍 Docs: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

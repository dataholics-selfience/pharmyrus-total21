"""
Pharmyrus V6 STEALTH - Production Anti-Detection
FastAPI server with advanced Google Patents and WIPO techniques
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from typing import Optional, List

from app.services.v6_orchestrator import V6StealthOrchestrator, execute_v6_search

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Pharmyrus V6 STEALTH",
    description="Multi-Layer Patent Search with Anti-Detection",
    version="6.0.0 STEALTH"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class PatentSearchRequest(BaseModel):
    molecule_name: str
    brand_name: Optional[str] = None
    target_countries: Optional[List[str]] = None


@app.on_event("startup")
async def startup_event():
    """Startup event"""
    logger.info("=" * 80)
    logger.info("🚀 Pharmyrus V6 STEALTH Starting...")
    logger.info("   Port: 8080")
    logger.info("   Mode: PRODUCTION ANTI-DETECTION")
    logger.info("   Sources: Google Patents (stealth) + WIPO + INPI")
    logger.info("   Techniques:")
    logger.info("     - Fingerprint randomization (canvas, WebGL, fonts, etc.)")
    logger.info("     - Chrome headers with Client Hints")
    logger.info("     - Session management")
    logger.info("     - Gaussian delays (15-30s)")
    logger.info("     - Circuit breaker")
    logger.info("     - User-Agent rotation")
    logger.info("=" * 80)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "6.0.0 STEALTH",
        "mode": "multi_layer",
        "crawlers": ["playwright", "selenium"]
    }


@app.post("/api/v6/search")
async def search_patents(request: PatentSearchRequest):
    """
    V6 STEALTH Patent Search
    
    Advanced anti-detection techniques:
    - Fingerprint randomization (canvas, WebGL, fonts, battery, screen, hardware)
    - Correct Chrome header order with Client Hints
    - Session management with cookies
    - Gaussian delays (15-30s for Google)
    - Circuit breaker pattern
    - User-Agent rotation
    
    Sources:
    - Google Patents (stealth mode)
    - WIPO Patentscope
    - INPI Brazil
    """
    try:
        logger.info(f"🔍 V6 SEARCH: {request.molecule_name}")
        
        result = await execute_v6_search(
            molecule_name=request.molecule_name,
            brand_name=request.brand_name,
            proxy=None  # Can add proxy support later
        )
        
        logger.info(f"✅ DONE: {result['summary']['total_br_patents']} BR patents in {result['execution_time']:.1f}s")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Pharmyrus V6 STEALTH API",
        "version": "6.0.0",
        "mode": "multi_layer_stealth",
        "docs": "/docs",
        "health": "/health",
        "search_endpoint": "/api/v6/search"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

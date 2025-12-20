#!/usr/bin/env python3
"""
Pharmyrus V6 LAYERED - FastAPI Deployment
API endpoints para deploy em Railway ou outro servidor
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import asyncio
from datetime import datetime

from app.services.v6_layered_orchestrator import V6LayeredOrchestrator


# FastAPI app
app = FastAPI(
    title="Pharmyrus V6 LAYERED API",
    description="Multi-layer patent search system with auto-fallback",
    version="6.0.0-LAYERED"
)


# Request models
class SearchRequest(BaseModel):
    molecule_name: str
    brand_name: Optional[str] = None
    target_countries: List[str] = ["BR"]


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


# Global orchestrator instance
orchestrator: Optional[V6LayeredOrchestrator] = None


@app.on_event("startup")
async def startup():
    """Initialize orchestrator on startup"""
    global orchestrator
    orchestrator = V6LayeredOrchestrator()
    print("✅ V6 Layered Orchestrator initialized")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global orchestrator
    if orchestrator:
        await orchestrator.cleanup()
        print("✅ V6 Layered Orchestrator cleaned up")


@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="6.0.0-LAYERED",
        timestamp=datetime.now().isoformat()
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Detailed health check"""
    return HealthResponse(
        status="healthy",
        version="6.0.0-LAYERED",
        timestamp=datetime.now().isoformat()
    )


@app.post("/api/v6/search")
async def search_patents(request: SearchRequest):
    """
    Main endpoint: Complete patent search
    
    Example request:
    {
        "molecule_name": "Darolutamide",
        "brand_name": "Nubeqa",
        "target_countries": ["BR"]
    }
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Execute search
        results = await orchestrator.search(
            molecule_name=request.molecule_name,
            brand_name=request.brand_name,
            target_countries=request.target_countries
        )
        
        return JSONResponse(content={
            "success": True,
            "data": results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@app.get("/api/v6/metrics")
async def get_metrics():
    """Get current system metrics"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Get crawler manager metrics
        manager = orchestrator.crawler_manager
        metrics = manager.get_all_metrics()
        
        return JSONResponse(content={
            "success": True,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )


@app.post("/api/v6/reset-circuits")
async def reset_circuit_breakers():
    """Reset all circuit breakers (admin endpoint)"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        manager = orchestrator.crawler_manager
        
        # Reset all circuits
        for crawler in [manager.playwright_crawler, manager.httpx_crawler, manager.selenium_crawler]:
            if crawler and hasattr(crawler, 'circuit_breaker'):
                crawler.circuit_breaker.reset()
        
        return JSONResponse(content={
            "success": True,
            "message": "All circuit breakers reset",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset circuits: {str(e)}"
        )


# Run with: uvicorn api_deploy:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

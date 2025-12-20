"""
Patent data models
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SearchRequest(BaseModel):
    """Patent search request"""
    molecule_name: str = Field(..., description="Chemical name")
    brand_name: Optional[str] = Field(None, description="Brand name")
    target_countries: List[str] = Field(default=["BR"], description="Target countries")
    search_mode: str = Field(default="comprehensive", description="Search mode")


class PatentResult(BaseModel):
    """Individual patent result"""
    publication_number: str
    title: str
    abstract: Optional[str] = None
    assignee: Optional[str] = None
    inventors: List[str] = Field(default_factory=list)
    filing_date: Optional[str] = None
    publication_date: Optional[str] = None
    status: Optional[str] = None
    patent_type: Optional[str] = None
    link: str
    source: str
    score: int = 0


class MoleculeInfo(BaseModel):
    """Molecule information from PubChem"""
    name: str
    brand: Optional[str] = None
    cid: Optional[int] = None
    cas: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    iupac_name: Optional[str] = None
    smiles: Optional[str] = None
    inchi: Optional[str] = None
    inchi_key: Optional[str] = None
    dev_codes: List[str] = Field(default_factory=list)
    synonyms: List[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Complete search response"""
    molecule_info: MoleculeInfo
    search_strategy: Dict[str, Any]
    wo_processing: Dict[str, Any]
    summary: Dict[str, Any]
    br_patents: List[PatentResult]
    all_patents: List[PatentResult]
    comparison: Dict[str, Any]
    execution_time: float
    timestamp: str

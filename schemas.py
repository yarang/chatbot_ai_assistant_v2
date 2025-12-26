from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import date

class SearchFilters(BaseModel):
    """
    Search filters extracted from the user's natural language query.
    """
    query_text: str = Field(..., description="The actual keyword or semantic query text for vector search.")
    start_date: Optional[date] = Field(None, description="Start date for filtering (inclusive).")
    end_date: Optional[date] = Field(None, description="End date for filtering (inclusive).")
    source_type: Optional[str] = Field(None, description="The source type of the document (e.g., 'notion', 'slack', 'pdf').")
    tags: Optional[List[str]] = Field(None, description="List of tags to filter by.")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query_text": "project roadmap",
                "start_date": "2024-01-01",
                "source_type": "notion"
            }
        }

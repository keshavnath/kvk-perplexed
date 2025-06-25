from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class CompanyDetails(BaseModel):
    """Pydantic model for structured Perplexity response"""
    
    # Industry classifications
    industries: List[str] = Field(
        description="List of industries from predefined options",
        min_length=1,
        max_length=3
    )
    
    # Employee count range
    employee_range: str = Field(
        description="Employee count range from predefined options"
    )
    
    # Location information
    headquarters_location: str = Field(
        description="Primary headquarters location (city, country)"
    )
    
    # Business description
    business_description: str = Field(
        description="Brief description of what the company does",
        max_length=500
    )
    
    # Confidence score
    confidence_score: float = Field(
        description="Confidence score between 0 and 1",
        ge=0.0,
        le=1.0
    )
    
    # Optional URL fields
    homepage_url: Optional[str] = Field(
        default="",
        description="Company homepage URL"
    )
    
    linkedin_url: Optional[str] = Field(
        default="",
        description="Company LinkedIn page URL"
    )
    
    @field_validator('industries')
    @classmethod
    def validate_industries(cls, v):
        valid_industries = {
            "Technology & Software", "Financial Services", "Manufacturing", 
            "Healthcare & Pharmaceuticals", "Energy & Utilities", 
            "Construction & Real Estate", "Transportation & Logistics",
            "Retail & E-commerce", "Food & Beverages", "Education",
            "Professional Services", "Media & Entertainment", 
            "Telecommunications", "Agriculture", "Tourism & Hospitality",
            "Automotive", "Chemical & Materials", "Aerospace & Defense",
            "Government & Public Sector", "Non-profit"
        }
        for industry in v:
            if industry not in valid_industries:
                raise ValueError(f"Invalid industry: {industry}")
        return v
    
    @field_validator('employee_range')
    @classmethod
    def validate_employee_range(cls, v):
        valid_ranges = {
            "1-10", "11-50", "51-200", "201-500", 
            "501-1000", "1001-5000", "5000+", "Not Available"
        }
        if v not in valid_ranges:
            raise ValueError(f"Invalid employee range: {v}")
        return v

# Constants for API prompts
INDUSTRY_OPTIONS = [
    "Technology & Software", "Financial Services", "Manufacturing", 
    "Healthcare & Pharmaceuticals", "Energy & Utilities", 
    "Construction & Real Estate", "Transportation & Logistics",
    "Retail & E-commerce", "Food & Beverages", "Education",
    "Professional Services", "Media & Entertainment", 
    "Telecommunications", "Agriculture", "Tourism & Hospitality",
    "Automotive", "Chemical & Materials", "Aerospace & Defense",
    "Government & Public Sector", "Non-profit"
]

EMPLOYEE_RANGES = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1001-5000", "5000+", "Not Available"]

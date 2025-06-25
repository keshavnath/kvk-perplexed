import os
import json
import logging
from typing import Optional
import requests
from pydantic import ValidationError
from models import CompanyDetails, INDUSTRY_OPTIONS, EMPLOYEE_RANGES
from dotenv import dotenv_values

config = dotenv_values(".env")

logger = logging.getLogger('perplexity')
logger.setLevel(logging.DEBUG)

class PerplexityClient:
    def __init__(self):
        self.api_key = config.get('PERPLEXITY_API_KEY')
        self.model = config.get('PERPLEXITY_MODEL', 'sonar-small')
        self.url = "https://api.perplexity.ai/chat/completions"
        
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not found in .env file")
        
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def get_company_details(self, company_name: str, kvk_number: str) -> Optional[CompanyDetails]:
        """Get company details from Perplexity API"""
        try:
            user_prompt = self._create_user_prompt(company_name, kvk_number)
            system_prompt = self._create_system_prompt()
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 1000,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"schema": CompanyDetails.model_json_schema()},
                }
            }
            
            logger.debug(f"Making API request for {company_name} with model: {self.model}")
            
            response = requests.post(self.url, headers=self.headers, json=payload, timeout=30)
            
            # Log response details for debugging
            logger.debug(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"API Error {response.status_code}: {response.text}")
                return None
            
            response_data = response.json()
            
            # Check if response has expected structure
            if "choices" not in response_data or len(response_data["choices"]) == 0:
                logger.error(f"Unexpected response structure: {response_data}")
                return None
                
            response_text = response_data["choices"][0]["message"]["content"]
            logger.debug(f"Raw response for {company_name}: {response_text}")
            
            return self._parse_response(response_text, company_name)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {company_name}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error getting details for {company_name}: {str(e)}")
            return None

    def _create_system_prompt(self) -> str:
        """Create structured system prompt for Perplexity"""
        prompt = f"""
        You are a Company Information Researcher.
        You will be given the Company Name and KvK Number of a company in the Netherlands. You need to do research using the web and find out information.

        Provide information in this exact JSON format:
        {{
            "industries": ["industry1", "industry2", ...],
            "employee_range": "range",
            "headquarters_location": "city, country",
            "business_description": "brief description",
            "confidence_score": between 0 and 1 e.g. 0.8,
            "homepage_url": "https://company.com",
            "linkedin_url": "https://linkedin.com/company/companyname"
        }}

        Industry options (select 1-3 most relevant):
        {', '.join(INDUSTRY_OPTIONS)}

        Employee range options (select one):
        {', '.join(EMPLOYEE_RANGES)}

        Requirements:
        - confidence_score: 0.0-1.0 based on how certain you are about the information
        - If you cannot find reliable information, return a low confidence_score e.g. below 0.3
        - Keep business_description under 500 characters
        - homepage_url: Company's official website (leave empty string if not found)
        - linkedin_url: Company's LinkedIn page (leave empty string if not found)
        - employee_range: Use "Not Available" if you absolutely cannot determine employee count
        - headquarters_location: Use "Not Available" if you absolutely cannot determine location
        - Use actual company data, not assumptions. If you are estimating instead of finding correct values, decrease the confidence_score.

        Only return the JSON object, no other text.
        Your response will be used to create a database so make sure it follows the structure and requirements.
        """

        return prompt
    
    def _create_user_prompt(self, company_name: str, kvk_number: str) -> str:
        prompt = f"""
        Research the Dutch company "{company_name}" with KvK number {kvk_number}.
        Remember to answer in the required format and choose from the correct options.
        """

        return prompt

    def _parse_response(self, response_text: str, company_name: str) -> Optional[CompanyDetails]:
        """Parse and validate Perplexity response"""
        try:
            # Since we're using structured output, the response should be valid JSON
            data = json.loads(response_text)
            details = CompanyDetails(**data)
            
            logger.info(f"Successfully parsed details for {company_name} (confidence: {details.confidence_score})")
            return details
            
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse response for {company_name}: {str(e)}")
            logger.debug(f"Raw response: {response_text}")
            return None

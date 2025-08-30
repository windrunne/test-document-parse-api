import openai
from fastapi import HTTPException, status
from app.config import settings
import logging
from typing import Dict, Any, Optional
import base64

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        openai.api_key = settings.openai_api_key
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    async def extract_patient_data(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        try:
            base64_content = base64.b64encode(file_content).decode('utf-8')
            
            if filename.lower().endswith('.pdf'):
                prompt = self._get_extraction_prompt()
                response = await self._extract_with_text(file_content, prompt)
            else:
                response = await self._extract_with_vision(base64_content, filename)
            
            extracted_data = self._parse_extraction_response(response)
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting data with OpenAI: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to extract data: {str(e)}"
            )
    
    async def _extract_with_vision(self, base64_content: str, filename: str) -> str:
        try:
            prompt = self._get_extraction_prompt()
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_content}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            return content
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process document with Vision API"
            )
    
    async def _extract_with_text(self, file_content: bytes, prompt: str) -> str:
        try:
            text_content = "PDF content would be extracted here"
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nDocument content: {text_content}"
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Text extraction error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to extract text from document"
            )
    
    def _get_extraction_prompt(self) -> str:
        return """
        Please extract the following patient information from this medical document:
        
        1. Patient's First Name
        2. Patient's Last Name  
        3. Patient's Date of Birth (DOB)
        
        Please respond in the following JSON format:
        {
            "patient_first_name": "extracted first name",
            "patient_last_name": "extracted last name", 
            "patient_dob": "extracted date of birth",
            "confidence": "high/medium/low",
            "notes": "any additional observations"
        }
        
        If any information cannot be found, use "Not Found" as the value.
        Be very careful to extract only the requested information and maintain accuracy.
        """
    
    def _parse_extraction_response(self, response: str) -> Dict[str, Any]:
        try:
            import json
            import re
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                
                data = json.loads(json_str)
                
                required_fields = ['patient_first_name', 'patient_last_name', 'patient_dob']
                for field in required_fields:
                    if field not in data:
                        data[field] = "Not Found"
                
                return data
            else:
                return self._fallback_parsing(response)
                
        except json.JSONDecodeError as e:
            return self._fallback_parsing(response)
        except Exception as e:
            return self._fallback_parsing(response)
    
    def _fallback_parsing(self, response: str) -> Dict[str, Any]:
        lines = response.lower().split('\n')
        
        extracted_data = {
            "patient_first_name": "Not Found",
            "patient_last_name": "Not Found", 
            "patient_dob": "Not Found",
            "confidence": "low",
            "notes": "Used fallback parsing method"
        }
        
        for line in lines:
            if "first name" in line or "first" in line:
                pass
            elif "last name" in line or "last" in line:
                pass
            elif "date of birth" in line or "dob" in line or "birth" in line:
                pass
        
        return extracted_data


try:
    openai_service = OpenAIService()
except ValueError:
    openai_service = None
    logger.warning("OpenAI service not initialized - API key missing")

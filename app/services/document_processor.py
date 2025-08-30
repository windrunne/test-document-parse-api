import fitz  # PyMuPDF
import base64
import io
import asyncio
from PIL import Image
import logging
from typing import Dict, Any, List, Optional
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)


class DocumentProcessor:
   
    def __init__(self):
        self.openai_service = openai_service
    
    async def process_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:        
        try:
            if filename.lower().endswith('.pdf'):
                result = await self._process_pdf(file_content, filename)
                return result
            else:
                result = await self.openai_service.extract_patient_data(file_content, filename)
                return result
                
        except Exception as e:
            import traceback
            return self._get_fallback_result(f"Document processing error: {str(e)}")
    
    async def _process_pdf(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        try:
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            
            if pdf_document.page_count == 0:
                logger.warning("⚠️ PDF has no pages")
                return self._get_fallback_result("PDF has no pages")
            
            text_content = self._extract_text_from_pdf(pdf_document)
            
            if text_content.strip():
                result = await self._extract_from_text(text_content)
                return result
            else:
                result = await self._extract_from_images(pdf_document)
                return result
                
        except fitz.FileDataError as e:
            logger.error(f"❌ PDF file is corrupted or invalid: {e}")
            logger.error(f"📋 FileDataError details: {type(e).__name__}: {str(e)}")
            return self._get_fallback_result(f"PDF file is corrupted: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error processing PDF: {e}")
            logger.error(f"📋 Error details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
            return self._get_fallback_result(f"PDF processing error: {str(e)}")
    
    def _extract_text_from_pdf(self, pdf_document) -> str:
        text_content = ""
        
        for page_num in range(len(pdf_document)):
            try:
                page = pdf_document[page_num]
                page_text = page.get_text()
                text_content += page_text
            except Exception as e:
                continue
        
        return text_content
    
    async def _extract_from_text(self, text_content: str) -> Dict[str, Any]:
        try:
            prompt = self._get_text_extraction_prompt()
            
            response = await self.openai_service._extract_with_text(
                text_content.encode(), 
                prompt
            )
            
            parsed_result = self.openai_service._parse_extraction_response(response)
            return parsed_result
            
        except Exception as e:
            import traceback
            raise
    
    async def _extract_from_images(self, pdf_document) -> Dict[str, Any]:
        try:
            images = self._convert_pdf_to_images(pdf_document)
            
            if not images:
                logger.warning("No images could be extracted from PDF")
                return self._get_fallback_result("No images could be extracted from PDF")
            
            try:
                result = await self._extract_from_images_parallel(images)
                if result:
                    return result
            except Exception as parallel_error:
                logger.error(f"Parallel processing failed: {parallel_error}, falling back to sequential")
            return await self._extract_from_images_sequential(images)
            
        except Exception as e:
            return self._get_fallback_result(f"Image processing error: {str(e)}")
    
    def _convert_pdf_to_images(self, pdf_document, dpi: int = 100) -> List[Image.Image]:
        images = []
        
        for page_num in range(len(pdf_document)):
            try:
                page = pdf_document[page_num]
                
                zoom = dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)
                
                pix = page.get_pixmap(matrix=mat)
                
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                if image.width > 800 or image.height > 800:
                    image.thumbnail((800, 800), Image.Resampling.LANCZOS)
                
                images.append(image)
            except Exception as e:
                continue
        
        return images
    
    def _combine_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not results:
            return {
                "patient_first_name": "Not Found",
                "patient_last_name": "Not Found",
                "patient_dob": "Not Found",
                "confidence": "low",
                "notes": "No data extracted from any page"
            }
        
        best_result = results[0]
        best_score = self._calculate_completeness_score(best_result)
        
        for i, result in enumerate(results[1:], 1):
            score = self._calculate_completeness_score(result)
            if score > best_score:
                best_result = result
                best_score = score
        
        if len(results) > 1:
            best_result["notes"] = f"Processed {len(results)} pages. {best_result.get('notes', '')}"
        return best_result
    
    def _calculate_completeness_score(self, result: Dict[str, Any]) -> int:
        score = 0
        required_fields = ['patient_first_name', 'patient_last_name', 'patient_dob']
        
        for field in required_fields:
            value = result.get(field, "Not Found")
            if value != "Not Found" and value.strip():
                score += 1
                
        return score
    
    async def _extract_from_images_parallel(self, images: List[Image.Image]) -> Optional[Dict[str, Any]]:
        try:
            batch_size = 2
            all_results = []
            
            for batch_start in range(0, len(images), batch_size):
                batch_end = min(batch_start + batch_size, len(images))
                batch_images = images[batch_start:batch_end]
                                
                tasks = []
                for i, image in enumerate(batch_images):
                    page_num = batch_start + i + 1
                    task = self._process_single_image_with_timeout(image, page_num, len(images))
                    tasks.append(task)
                
                try:
                    batch_results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=120.0  # 2 minutes timeout per batch
                    )
                    
                    for i, result in enumerate(batch_results):
                        if isinstance(result, Exception):
                            logger.error(f"Error processing page {batch_start + i + 1}: {result}")
                        else:
                            all_results.append(result)
                            if self._is_good_result(result):
                                return self._combine_results(all_results)
                                
                except asyncio.TimeoutError:
                    continue
            
            if all_results:
                return self._combine_results(all_results)
            else:
                return None
            
        except Exception as e:
            logger.error(f"Parallel processing error: {e}")
            return None
    
    async def _extract_from_images_sequential(self, images: List[Image.Image]) -> Dict[str, Any]:
        try:
            logger.info(f"🔄 Processing {len(images)} pages sequentially")
            all_results = []
            
            for i, image in enumerate(images):
                page_num = i + 1
                logger.info(f"Processing page {page_num} of {len(images)} sequentially")
                
                try:
                    result = await self._process_single_image_with_timeout(image, page_num, len(images))
                    all_results.append(result)
                    
                    if self._is_good_result(result):
                        logger.info(f"Good result found on page {page_num}, stopping early")
                        break
                        
                except Exception as page_error:
                    logger.error(f"Error processing page {page_num}: {page_error}")
                    continue
            
            logger.info(f"Sequential processing completed: {len(all_results)} pages processed")
            
            if all_results:
                return self._combine_results(all_results)
            else:
                return self._get_fallback_result("Failed to process any pages with Vision API")
                
        except Exception as e:
            logger.error(f"Sequential processing error: {e}")
            return self._get_fallback_result(f"Sequential processing failed: {str(e)}")
    
    async def _process_single_image_with_timeout(self, image: Image.Image, page_num: int, total_pages: int) -> Dict[str, Any]:
        try:
            start_time = asyncio.get_event_loop().time()
            logger.info(f"🚀 Starting page {page_num} of {total_pages}")
            logger.info(f"📊 Image details: {image.width}x{image.height}, mode: {image.mode}, format: {image.format}")
            
            logger.info(f"🔄 Converting image to base64...")
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG', optimize=True, quality=85)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            logger.info(f"✅ Image converted to base64: {len(img_base64)} characters")
            
            logger.info(f"🚀 Calling OpenAI Vision API for page {page_num}...")
            result = await asyncio.wait_for(
                self.openai_service._extract_with_vision(img_base64, f"page_{page_num}.png"),
                timeout=60.0  # 1 minute timeout per page
            )
            logger.info(f"✅ Vision API response received: {len(result)} characters")
            logger.info(f"📋 Response preview: {result[:300]}...")
            
            logger.info(f"🔍 Parsing Vision API response...")
            parsed_result = self.openai_service._parse_extraction_response(result)
            logger.info(f"✅ Response parsed successfully: {parsed_result}")
            
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            logger.info(f"✅ Page {page_num} completed in {duration:.2f}s")
            
            return parsed_result
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ Page {page_num} timed out after 60s")
            raise
        except Exception as e:
            logger.error(f"❌ Error processing page {page_num}: {e}")
            logger.error(f"📋 Error details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
            raise
    
    async def _process_single_image(self, image: Image.Image, page_num: int, total_pages: int) -> Dict[str, Any]:
        try:
            start_time = asyncio.get_event_loop().time()
            logger.info(f"🚀 Starting page {page_num} of {total_pages}")
            
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG', optimize=True, quality=85)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            result = await self.openai_service._extract_with_vision(
                img_base64, 
                f"page_{page_num}.png"
            )
            
            parsed_result = self.openai_service._parse_extraction_response(result)
            
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            logger.info(f"✅ Page {page_num} completed in {duration:.2f}s")
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"❌ Error processing page {page_num}: {e}")
            raise
    
    def _is_good_result(self, result: Dict[str, Any]) -> bool:
        logger.info(f"🔍 Evaluating if result is good enough to stop processing...")
        
        score = self._calculate_completeness_score(result)
        confidence = result.get('confidence', 'low')
        
        logger.info(f"📊 Result evaluation - Score: {score}/3, Confidence: {confidence}")
        
        if score >= 2 and confidence == 'high':
            logger.info(f"✅ Good result detected: {score}/3 fields with high confidence - STOPPING")
            return True
        
        if score >= 3:
            logger.info(f"✅ Excellent result detected: {score}/3 fields - STOPPING")
            return True
        
        logger.info(f"❌ Result not good enough: {score}/3 fields, confidence: {confidence} - CONTINUING")
        return False
    
    def _get_fallback_result(self, error_message: str) -> Dict[str, Any]:
        return {
            "patient_first_name": "Not Found",
            "patient_last_name": "Not Found",
            "patient_dob": "Not Found",
            "confidence": "low",
            "notes": f"Processing failed: {error_message}"
        }
    
    def _get_text_extraction_prompt(self) -> str:
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


document_processor = DocumentProcessor()

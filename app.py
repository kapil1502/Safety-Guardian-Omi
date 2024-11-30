import os
import sys
import logging
import traceback
from typing import Dict, Any, Optional

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
import dateutil.parser

class OMIIntegrationWebhook:
    def __init__(self):
        # Logging configuration (simplified for serverless)
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('omi_integration')
        
        # Configuration variables
        self.emergency_keywords = [
            'help', 'emergency', 'danger', 'attacked', 
            'threat', 'scared', 'in trouble', 'omi help'
        ]
    
    def validate_webhook_payload(self, payload: Dict[str, Any]) -> bool:
        """
        Validate the incoming webhook payload
        """
        # Check for required fields
        required_fields = ['transcript', 'created_at']
        
        for field in required_fields:
            if field not in payload:
                self.logger.warning(f"Missing required field: {field}")
                return False
        
        # Additional validation checks
        try:
            # Check transcript length
            if len(payload.get('transcript', '')) > 10000:
                self.logger.warning("Transcript exceeds maximum length")
                return False
            
            # Validate timestamp format
            dateutil.parser.parse(payload['created_at'])
        
        except Exception as e:
            self.logger.error(f"Payload validation failed: {e}")
            return False
        
        return True
    
    def detect_emergency_context(self, transcript: str) -> Optional[Dict[str, Any]]:
        """
        Detect emergency context within the transcript
        """
        # Normalize transcript
        normalized_transcript = transcript.lower()
        
        # Emergency keyword detection
        emergency_detected = any(
            keyword in normalized_transcript 
            for keyword in self.emergency_keywords
        )
        
        if emergency_detected:
            return {
                'type': 'voice_emergency',
                'confidence': self._calculate_emergency_confidence(normalized_transcript),
                'keywords_matched': [
                    keyword for keyword in self.emergency_keywords 
                    if keyword in normalized_transcript
                ]
            }
        
        return None
    
    def _calculate_emergency_confidence(self, transcript: str) -> float:
        """
        Calculate confidence level of emergency detection
        """
        matched_keywords = sum(
            1 for keyword in self.emergency_keywords 
            if keyword in transcript
        )
        
        # Base confidence calculation
        confidence = min(matched_keywords * 0.3, 1.0)
        return confidence
    
    def process_memory_creation_trigger(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process memory creation webhook
        """
        try:
            # Validate payload
            if not self.validate_webhook_payload(payload):
                return {
                    'status': 'error',
                    'message': 'Invalid payload',
                    'error_code': 400
                }
            
            # Extract key information
            transcript = payload.get('transcript', '')
            memory_id = payload.get('id')
            
            # Detect emergency context
            emergency_context = self.detect_emergency_context(transcript)
            
            if emergency_context:
                # Log emergency detection
                self.logger.critical(
                    f"Emergency Detected in Memory {memory_id}: "
                    f"Confidence {emergency_context['confidence']} "
                    f"Keywords: {emergency_context['keywords_matched']}"
                )
            
            # Process additional memory creation logic
            processed_result = {
                'status': 'success',
                'memory_id': memory_id,
                'emergency_detected': emergency_context is not None,
                'additional_metadata': self._extract_additional_metadata(payload)
            }
            
            return processed_result
        
        except Exception as e:
            # Comprehensive error logging
            self.logger.error(
                f"Memory Creation Processing Error: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            
            return {
                'status': 'error',
                'message': str(e),
                'error_code': 500
            }
    
    def _extract_additional_metadata(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract additional metadata from the payload
        """
        return {
            'category': payload.get('structured', {}).get('category'),
            'action_items': payload.get('structured', {}).get('action_items', []),
            'total_segments': len(payload.get('transcript_segments', []))
        }

# Create webhook handler
webhook_handler = OMIIntegrationWebhook()

# Flask Application for Vercel
app = Flask(__name__)

def process_webhook():
    """
    Main webhook endpoint for processing OMI triggers
    """
    try:
        # Validate request
        payload = request.get_json()
        
        if not payload:
            return jsonify({
                'status': 'error',
                'message': 'Invalid request format'
            }), 400
        
        # Process memory creation trigger
        result = webhook_handler.process_memory_creation_trigger(payload)
        
        # Determine response status code
        status_code = 200 if result['status'] == 'success' else result.get('error_code', 500)
        
        return jsonify(result), status_code
    
    except Exception as e:
        webhook_handler.logger.error(
            f"Webhook Processing Error: {e}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'details': str(e)
        }), 500

# Vercel requires a function named `app`
def app(event, context):
    # For POST requests to the webhook
    if event['httpMethod'] == 'POST':
        return process_webhook()
    
    # Handle other HTTP methods
    return {
        'statusCode': 405,
        'body': 'Method Not Allowed'
    }

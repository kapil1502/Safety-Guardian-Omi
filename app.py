import os
import logging
import traceback
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
import requests
import re

class OMIIntegrationWebhook:
    def __init__(self):
        # Logging configuration
        self._setup_logging()
        
        # Configuration variables
        self.emergency_keywords = [
            'help', 'emergency', 'danger', 'attacked', 
            'threat', 'scared', 'in trouble', 'omi help'
        ]
        
        # External service configuration (placeholder)
        self.external_services = {
            'emergency_contact': None,
            'location_service': None,
            'monitoring_service': None
        }
    
    def _setup_logging(self):
        """
        Configure logging with multiple handlers
        """
        # Create logger
        self.logger = logging.getLogger('omi_integration')
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler('omi_integration.log')
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
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
            import dateutil.parser
            dateutil.parser.parse(payload['created_at'])
        
        except Exception as e:
            self.logger.error(f"Payload validation failed: {e}")
            return False
        
        return True
    
    def detect_emergency_context(self, transcript: str) -> Optional[Dict[str, Any]]:
        """
        Detect emergency context within the transcript
        
        Returns:
        - None if no emergency detected
        - Dict with emergency details if detected
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
        # Simple confidence calculation
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
                
                # Trigger emergency protocol
                self._handle_emergency_protocol(payload, emergency_context)
            
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
    
    def _handle_emergency_protocol(self, payload: Dict[str, Any], emergency_context: Dict[str, Any]):
        """
        Execute emergency response protocol
        """
        try:
            # Placeholder for emergency response
            # In a real implementation, this would:
            # 1. Notify emergency contacts
            # 2. Attempt to contact authorities
            # 3. Share location information
            
            emergency_details = {
                'memory_id': payload.get('id'),
                'transcript': payload.get('transcript'),
                'emergency_type': emergency_context.get('type'),
                'confidence': emergency_context.get('confidence')
            }
            
            self.logger.critical(f"EMERGENCY PROTOCOL ACTIVATED: {emergency_details}")
            
            # Simulated notifications (replace with actual implementations)
            self._notify_emergency_contacts(emergency_details)
            self._log_emergency_event(emergency_details)
        
        except Exception as e:
            self.logger.error(f"Emergency Protocol Execution Failed: {e}")
    
    def _notify_emergency_contacts(self, emergency_details: Dict[str, Any]):
        """
        Notify predefined emergency contacts
        """
        # Placeholder for contact notification logic
        pass
    
    def _log_emergency_event(self, emergency_details: Dict[str, Any]):
        """
        Log emergency event to external monitoring service
        """
        # Placeholder for external logging
        pass
    
    def _extract_additional_metadata(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract additional metadata from the payload
        """
        return {
            'category': payload.get('structured', {}).get('category'),
            'action_items': payload.get('structured', {}).get('action_items', []),
            'total_segments': len(payload.get('transcript_segments', []))
        }

# Flask Application Setup
app = Flask(__name__)
webhook_handler = OMIIntegrationWebhook()

@app.route('/webhook', methods=['POST'])
def process_webhook():
    """
    Main webhook endpoint for processing OMI triggers
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Invalid request format'
            }), 400
        
        # Parse incoming payload
        payload = request.get_json()
        
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

# Error Handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'status': 'error', 'message': 'Bad Request'}), 400

@app.errorhandler(500)
def server_error(error):
    return jsonify({'status': 'error', 'message': 'Internal Server Error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

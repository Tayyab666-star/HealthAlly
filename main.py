import os
import functions_framework
import json
import requests
# Note: For Firebase Admin SDK to work in a Cloud Function environment, 
# initialization must be handled carefully.
from firebase_admin import initialize_app, firestore
from google.cloud.firestore import Client, DocumentReference
from flask import jsonify

# --- API Configuration ---
# The API key will be automatically provided by the Canvas environment when deployed.
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"
# NOTE: The Canvas environment will handle key injection for us, so we leave it as an empty string.
API_KEY = os.environ.get("API_KEY", "") 

# --- FIREBASE ADMIN SETUP ---
# Initialize Firebase Admin SDK (required for secure backend access to Firestore)
# Logic to handle both local emulator and deployed environment initialization
try:
    if not firestore._app_instance: 
        initialize_app()
    db: Client = firestore.client()
except ValueError:
    # If already initialized (e.g., in an emulator), just get the client
    db: Client = firestore.client()

def handle_cors(request):
    """Handles CORS preflight requests and sets necessary headers."""
    # If this is an OPTIONS request, send the preflight response
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    # For all other requests, set the necessary CORS header
    return {'Access-Control-Allow-Origin': '*'} 

@functions_framework.http
def pmdc_verify_doctor(request):
    """
    HTTP Cloud Function to securely verify a doctor's PMDC status 
    and update their Firestore profile.
    """
    headers = handle_cors(request)
    if isinstance(headers, tuple): return headers # Return if it was an OPTIONS request

    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return (jsonify({"error": "No JSON payload provided."}), 400, headers)

        doctor_id = request_json.get('doctorId')
        pmdc_number = request_json.get('pmdcNumber')
        app_id = request_json.get('appId') # Used to construct the Firestore path

        if not doctor_id or not pmdc_number or not app_id:
            return (jsonify({"error": "Missing doctorId, pmdcNumber, or appId."}), 400, headers)

        # Mock Verification Logic: PMDC-12345 passes, anything else fails
        is_verified = pmdc_number == "PMDC-12345"
        
        if is_verified:
            # Construct the secure path using the provided appId
            doctor_ref: DocumentReference = db.document(f'artifacts/{app_id}/public/data/doctor_profiles/{doctor_id}')
            
            # Use update for atomic, server-side data modification
            doctor_ref.update({
                'is_pmdc_verified': True,
                'verification_date': firestore.SERVER_TIMESTAMP,
                'pmdc_number_status': 'verified'
            })
            
            return (jsonify({
                "verified": True,
                "message": "PMDC verification successful. Doctor profile updated.",
                "doctorId": doctor_id
            }), 200, headers)
        else:
            return (jsonify({
                "verified": False,
                "message": "PMDC number failed mock verification check. Please check the number and try again.",
                "doctorId": doctor_id
            }), 200, headers)

    except Exception as e:
        print(f"An error occurred during PMDC verification: {e}")
        return (jsonify({"error": f"Internal Server Error: {str(e)}"}), 500, headers)

@functions_framework.http
def ai_symptom_checker(request):
    """
    HTTP Cloud Function to securely call the Gemini API for symptom analysis.
    This function uses a strict system prompt to mitigate health-related risks.
    """
    headers = handle_cors(request)
    if isinstance(headers, tuple): return headers
    headers['Content-Type'] = 'application/json' # Ensure JSON content type for the main response

    try:
        # 1. Input Validation and Parsing
        request_json = request.get_json(silent=True)
        if not request_json:
            return (jsonify({"error": "No JSON payload provided."}), 400, headers)

        symptoms = request_json.get('symptoms')
        language = request_json.get('language', 'English')

        if not symptoms:
            return (jsonify({"error": "Missing symptoms input."}), 400, headers)
            
        # 2. Prepare Gemini API Payload with strong safety constraints
        system_prompt = (
            "You are HealthAlly, a culturally sensitive, preliminary AI health guide. "
            "You MUST be extremely cautious and non-diagnostic. Your response MUST be in the requested language, which is "
            f"'{language}'. "
            "Your response must include three clearly separated sections using markdown bolding and list formatting, in this exact order:\n"
            "1. **IMPORTANT DISCLAIMER:** A bold, explicit warning that you are NOT a doctor and your advice is not a diagnosis. State: 'This information is for informational purposes only. Consult a verified doctor immediately for a diagnosis.'\n"
            "2. **Possible Common Causes:** A list of 3-5 possible, common, non-life-threatening causes for the symptoms.\n"
            "3. **Recommended Next Steps:** Clear, conservative advice, such as 'Monitor symptoms for 24 hours and stay hydrated' or 'Seek immediate medical attention if symptoms worsen or include chest pain/difficulty breathing.'\n"
            "Keep the response professional, empathetic, and focus on the patient's safety. Use concise, clear language."
        )
        
        user_query = f"The patient reports the following symptoms: {symptoms}. Provide a preliminary analysis."

        payload = {
            "contents": [{"parts": [{"text": user_query}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "tools": [{"google_search": {}}] # Use Google Search for grounding
        }

        # 3. Call Gemini API with exponential backoff for reliability
        
        gemini_response = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                gemini_response = requests.post(f"{GEMINI_API_URL}?key={API_KEY}", json=payload)
                gemini_response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
                break # Success
            except requests.exceptions.RequestException as e:
                # Log error silently and retry if not the last attempt
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt) # Exponential backoff: 1s, 2s, 4s...
                else:
                    raise e # Re-raise if all retries fail

        result = gemini_response.json()
        
        # Extract text
        generated_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'Error: Could not retrieve AI analysis.')

        # 4. Return the AI response
        return (jsonify({
            "success": True,
            "analysis": generated_text
        }), 200, headers)

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error calling Gemini API: {http_err}. Response: {getattr(gemini_response, 'text', 'N/A')}")
        return (jsonify({"error": f"AI service error: {http_err}"}), gemini_response.status_code if 'gemini_response' in locals() else 500, headers)
    except Exception as e:
        print(f"An error occurred during AI analysis: {e}")
        return (jsonify({"error": f"Internal Server Error: {str(e)}"}), 500, headers)

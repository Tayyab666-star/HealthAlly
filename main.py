import os
import time
import functions_framework
import json
import requests
from firebase_admin import initialize_app, firestore, get_app, credentials
from google.cloud.firestore import Client, DocumentReference
from flask import jsonify

# --- API Configuration ---
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"
API_KEY = os.environ.get("API_KEY", "")

# --- FIREBASE ADMIN SETUP ---
# Initialize Firebase Admin SDK
try:
    # Try to get existing app
    app = get_app()
    db: Client = firestore.client()
except ValueError:
    # No app exists, initialize it
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the parent directory and look for serviceAccountKey.json
    parent_dir = os.path.dirname(current_dir)
    service_account_path = os.path.join(parent_dir, 'serviceAccountKey.json')
    
    if os.path.exists(service_account_path):
        # Local development with service account key
        cred = credentials.Certificate(service_account_path)
        initialize_app(cred)
    else:
        # Cloud Functions environment (uses default credentials)
        initialize_app()
    
    db: Client = firestore.client()

def handle_cors(request):
    """Handles CORS preflight requests and sets necessary headers."""
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    return {'Access-Control-Allow-Origin': '*'}

@functions_framework.http
def pmdc_verify_doctor(request):
    """
    HTTP Cloud Function to securely verify a doctor's PMDC status 
    and update their Firestore profile.
    """
    headers = handle_cors(request)
    if isinstance(headers, tuple):
        return headers

    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return (jsonify({"error": "No JSON payload provided."}), 400, headers)

        doctor_id = request_json.get('doctorId')
        pmdc_number = request_json.get('pmdcNumber')
        app_id = request_json.get('appId')

        if not doctor_id or not pmdc_number or not app_id:
            return (jsonify({"error": "Missing doctorId, pmdcNumber, or appId."}), 400, headers)

        # Mock Verification Logic
        is_verified = pmdc_number == "PMDC-12345"
        
        if is_verified:
            doctor_ref: DocumentReference = db.document(f'artifacts/{app_id}/public/data/doctor_profiles/{doctor_id}')
            
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
    """
    headers = handle_cors(request)
    if isinstance(headers, tuple):
        return headers
    headers['Content-Type'] = 'application/json'

    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return (jsonify({"error": "No JSON payload provided."}), 400, headers)

        symptoms = request_json.get('symptoms')
        language = request_json.get('language', 'English')

        if not symptoms:
            return (jsonify({"error": "Missing symptoms input."}), 400, headers)
        
        if not API_KEY:
            return (jsonify({"error": "API_KEY not configured."}), 500, headers)
            
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
            "tools": [{"google_search": {}}]
        }

        gemini_response = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                gemini_response = requests.post(f"{GEMINI_API_URL}?key={API_KEY}", json=payload, timeout=30)
                gemini_response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise e

        result = gemini_response.json()
        generated_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'Error: Could not retrieve AI analysis.')

        return (jsonify({
            "success": True,
            "analysis": generated_text
        }), 200, headers)

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error calling Gemini API: {http_err}. Response: {getattr(gemini_response, 'text', 'N/A')}")
        return (jsonify({"error": f"AI service error: {http_err}"}), gemini_response.status_code if gemini_response else 500, headers)
    except Exception as e:
        print(f"An error occurred during AI analysis: {e}")
        return (jsonify({"error": f"Internal Server Error: {str(e)}"}), 500, headers)

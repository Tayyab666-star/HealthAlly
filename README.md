# HealthAlly

🇵🇰 HealthAlly – Your Agentic Digital Health Companion
HealthAlly is an MVP developed to address critical healthcare access gaps in Pakistan. It focuses on providing a secure Electronic Health Record (EHR) platform, enabling professional verification for doctors, and offering preliminary, AI-powered symptom analysis localized for users.

This project aligns with the national goal of digitizing healthcare and improving accessibility, particularly in underserved and rural areas.

✨ MVP Key Features
The current Minimum Viable Product (MVP) implements the foundational authentication, database synchronization, and core AI backend services:

Secure Authentication & User Roles: Supports two primary roles: Patient and Doctor, with secure, anonymous sign-in via Firebase Authentication.

PMDC Verification (Doctor): A Cloud Function validates a mock PMDC number (PMDC-12345) and updates the doctor's public profile status in Firestore in real-time.

Agentic AI Symptom Checker: A Python Cloud Function (ai_symptom_checker) utilizes the Gemini API with Google Search Grounding to provide safety-disclaimed, educational analysis of symptoms. Supports Localization (English/Urdu).

Electronic Health Records (EHR): Real-time data synchronization with Firebase Firestore for patient and doctor profiles.

Responsive Frontend: Built using a single HTML file with Tailwind CSS for a modern, mobile-first design.

🛠️ Tech Stack
Component

Technology

Description

Frontend

HTML5, JavaScript (ES6+), Tailwind CSS

Single-file application for rapid prototyping and deployment.

Backend

Python 3.10, Firebase Cloud Functions

Serverless environment for logic execution and AI services.

Database

Firebase Firestore

NoSQL database used for secure, real-time data storage (EHRs, Profiles).

AI/LLM

Gemini 2.5 Flash

Used by the ai_symptom_checker for grounded, localized analysis.

🚀 Local Setup and Development Guide
Follow these steps to clone the repository and run the full stack locally using the Firebase Emulator Suite.

Prerequisites
You must have the following software installed:

Node.js & npm (Required for Firebase CLI)

Python 3.8+ & pip (Required for Cloud Functions)

Firebase CLI (Install globally: npm install -g firebase-tools)

Step 1: Install Python Dependencies
Navigate to the functions/ directory and install the necessary packages for your Cloud Functions.

# Navigate to the functions directory
cd functions

# Install Python packages from requirements.txt
pip install -r requirements.txt

Step 2: Set the Gemini API Key Environment Variable
For the ai_symptom_checker function to work locally, you must provide your Gemini API key as an environment variable in the terminal session where you run the emulators.

# Set your Gemini API Key (Replace [YOUR_KEY] with your actual key)
export GEMINI_API_KEY="[YOUR_KEY]"

Step 3: Start the Firebase Emulator Suite (The Full Stack)
From the root directory of your project, run the following command. This starts the Hosting server (frontend), the Python Functions server (backend), and the local Firestore database.

# Run the entire stack locally
firebase emulators:start --only hosting,functions,firestore

Upon success, your application will be available at the Hosting URL (typically http://localhost:5000).

✅ Verification and Testing
After starting the emulators, access the Hosting URL and perform the following crucial end-to-end tests:

1. Doctor Verification Test
Role: Doctor

Action: Enter the test PMDC number: PMDC-12345

Expected Result: The frontend instantly updates to display the "VERIFIED" status, and the Firestore document for that user is updated to is_pmdc_verified: true.

2. AI Symptom Check Test
Role: Patient

Action: Enter symptoms (e.g., "stomach pain and dizziness"), select Urdu, and click Check Symptoms.

Expected Result: A response is generated in the Urdu language, which includes a clear non-diagnostic disclaimer and structured advice based on the symptom input.

☁️ Deployment
Once local testing is complete, deploy the entire application using the Firebase CLI. This uploads your static HTML, your Python Cloud Functions, and your Firestore Security Rules.

firebase deploy

🗺️ Future Enhancements
The next steps for the HealthAlly project include:

Medication Reminders: Implementing the Agentic AI Layer for intelligent, personalized medication and refill reminders.

Doctor Search: Developing a function to fetch and display a list of verified doctors to the patient.

Expanded Localization: Integrating support for regional languages like Punjabi and Sindhi.

Family Health Account: Developing the framework to manage multiple family members' records under one profile.

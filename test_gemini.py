
import os
import google.generativeai as genai
from dotenv import load_dotenv

if os.path.exists("ai/.env"):
    load_dotenv("ai/.env")
else:
    print("ai/.env NOT FOUND")

print(f"google-generativeai version: {genai.__version__}")

api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

try:
    print("Listing models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            
    print("\nTesting gemini-1.5-flash...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Hello")
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)

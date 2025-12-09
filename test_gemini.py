# test_gemini.py actualizado
import os
import google.generativeai as genai
from decouple import config

api_key = config('GOOGLE_API_KEY', default='TU_API_KEY') 
genai.configure(api_key=api_key)

print(f"Probando 'gemini-flash-latest'...")
try:
    model = genai.GenerativeModel('gemini-flash-latest')
    response = model.generate_content("Responde solo 'OK' si me lees.")
    print(f"Éxito: {response.text}")
except Exception as e:
    print(f"Error: {e}")
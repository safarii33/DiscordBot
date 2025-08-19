import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_fantasy_prediction(query):
    try:
        prompt = f"Make an NFL fantasy prediction for: {query}"
        response = openai.chat.completions.create(
            model="gpt-5",  # Change to a model you have access to
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error fetching prediction: {e}")
        return None
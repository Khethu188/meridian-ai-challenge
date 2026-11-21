import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


MODEL_NAME = "gemini-3.5-flash-lite"


def main() -> None:
	load_dotenv(Path(__file__).resolve().with_name(".env"))
	api_key = os.getenv("GEMINI_API_KEY")

	if not api_key:
		print("GEMINI_API_KEY is missing. Add it to the .env file beside app.py.")
		return

	try:
		client = genai.Client(api_key=api_key)
		response = client.models.generate_content(
			model=MODEL_NAME,
			contents='Reply with exactly "Connection successful" and nothing else.',
		)
		if response.text:
			print(response.text.strip())
		else:
			print("Gemini returned an empty response.")
	except Exception as error:
		print(f"Gemini connection failed ({type(error).__name__}). Check the API key and network connection.")


if __name__ == "__main__":
	main()

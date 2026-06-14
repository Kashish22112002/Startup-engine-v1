import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables if .env file exists
if os.path.exists(".env"):
    load_dotenv(".env")
else:
    print("Running in SIMULATION MODE by default. Copy .env.example to .env and fill in credentials to run in LIVE MODE.")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

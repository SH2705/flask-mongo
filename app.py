import json
import os
from pathlib import Path
from flask import Flask, jsonify, render_template, request, redirect, url_for
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# --- MongoDB Setup ---
MONGODB_URI = os.getenv("MONGODB_URI", "")
DB_NAME = os.getenv("DB_NAME", "testdb")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "submissions")

mongo_client = None
if MONGODB_URI:
    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
        # Force a quick check to ensure connection details are valid (will raise on failure)
        mongo_client.admin.command("ping")
    except Exception as e:
        # We won't crash the app; the form will show the error if used
        print(f"[WARN] Could not connect to MongoDB: {e}")

def get_collection():
    if not mongo_client:
        raise RuntimeError("MongoDB not connected. Check MONGODB_URI in your .env")
    return mongo_client[DB_NAME][COLLECTION_NAME]

# --- Routes ---

@app.get("/api")
def api_list():
    """Reads from a backend file and returns a JSON list."""
    data_path = Path("data/backend_data.json")
    if not data_path.exists():
        return jsonify({"error": "Data file not found"}), 500
    try:
        with data_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return jsonify({"error": "Data file must contain a JSON list"}), 500
        return jsonify(data), 200
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format in data file"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/")
def form_page():
    """Show the submission form."""
    # Optional: pre-fill with query params on validation errors
    return render_template("form.html", error=request.args.get("error"))

@app.post("/submit")
def submit():
    """Handle form submission: insert into MongoDB. 
       On success: redirect to /success. On error: show same page with error."""
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    # Simple validation
    if not name or not email:
        return render_template("form.html", error="Name and Email are required."), 400

    try:
        col = get_collection()
        doc = {"name": name, "email": email, "message": message}
        col.insert_one(doc)
        # Redirect on success
        return redirect(url_for("success"))
    except Exception as e:
        # Render same page with error, no redirect
        return render_template("form.html", error=f"Submission failed: {e}"), 500

@app.get("/success")
def success():
    """Landing page shown only after successful submission."""
    return render_template("success.html", msg="Data submitted successfully")

if __name__ == "__main__":
    # Run the Flask dev server
    app.run(debug=True)

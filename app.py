from flask import Flask, request, render_template, jsonify
from supabase import create_client
from supabase.lib.client_options import ClientOptions
import os, uuid, hashlib, time
from dotenv import load_dotenv

# Load environment variables (Render uses .env dashboard settings)
load_dotenv()

app = Flask(__name__)

# Read Supabase credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create Supabase client (no timeout arg!)
supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=ClientOptions(schema="public")
)

# Generate user ID based on IP
def get_user_id(req):
    return hashlib.sha256(req.remote_addr.encode()).hexdigest()

# Disable caching
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Connection"] = "close"
    return response

@app.route("/ping")
def ping():
    return "pong"

@app.route("/")
def index():
    user_id = get_user_id(request)
    try:
        data = supabase.table("webhooks").select("*").eq("user_id", user_id).execute().data
    except Exception as e:
        return f"Database error: {str(e)}", 500

    if data:
        path = data[0]["url_path"]
    else:
        path = str(uuid.uuid4())
        try:
            supabase.table("webhooks").insert({"user_id": user_id, "url_path": path}).execute()
        except Exception as e:
            return f"Insertion error: {str(e)}", 500

    return render_template("index.html", webhook_url=f"{request.host_url}webhook/{path}")

@app.route("/webhook/<path>", methods=["POST"])
def webhook(path):
    try:
        result = supabase.table("webhooks").select("*").eq("url_path", path).execute().data
    except Exception as e:
        return f"Path lookup error: {str(e)}", 500

    if not result:
        return "Invalid webhook", 404

    user_id = result[0]["user_id"]
    try:
        payload = request.get_json(force=True)
        supabase.table("messages").insert({"user_id": user_id, "content": payload}).execute()
    except Exception as e:
        return f"Insert error: {str(e)}", 500

    return "OK", 200

@app.route("/fetch")
def fetch():
    start = time.time()
    user_id = get_user_id(request)
    try:
        result = supabase.table("messages").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
    except Exception as e:
        return f"Fetch error: {str(e)}", 500

    duration = time.time() - start
    print(f"/fetch took {duration:.2f} seconds")
    return jsonify(result.data)

# Only for local development; not used in Render
if __name__ == "__main__":
    app.run(debug=True)
    

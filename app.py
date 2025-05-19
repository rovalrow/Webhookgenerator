from flask import Flask, request, render_template, jsonify, redirect
from supabase import create_client
import os, uuid, hashlib
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Supabase connection
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Simple user identifier via IP hash (can be improved with auth)
def get_user_id(req):
    return hashlib.sha256(req.remote_addr.encode()).hexdigest()

@app.route("/")
def index():
    user_id = get_user_id(request)
    data = supabase.table("webhooks").select("*").eq("user_id", user_id).execute().data
    if data:
        path = data[0]["url_path"]
    else:
        path = str(uuid.uuid4())
        supabase.table("webhooks").insert({"user_id": user_id, "url_path": path}).execute()
    return render_template("index.html", webhook_url=f"{request.host_url}webhook/{path}")

@app.route("/webhook/<path>", methods=["POST"])
def webhook(path):
    # Validate the webhook path exists
    result = supabase.table("webhooks").select("*").eq("url_path", path).execute().data
    if not result:
        return "Invalid webhook", 404

    user_id = result[0]["user_id"]
    payload = request.get_json(force=True)
    supabase.table("messages").insert({"user_id": user_id, "content": payload}).execute()
    return "OK", 200

@app.route("/fetch")
def fetch():
    user_id = get_user_id(request)
    result = supabase.table("messages").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
    return jsonify(result.data)
    

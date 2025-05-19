from flask import Flask, render_template, request, jsonify, redirect, url_for
import uuid
from datetime import datetime
from supabase import create_client, Client

# Supabase credentials (replace with your real ones)
supabase_url = "https://your-project-id.supabase.co"
supabase_key = "your-anon-or-service-role-key"
supabase: Client = create_client(supabase_url, supabase_key)

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/create_webhook', methods=['POST'])
def create_webhook():
    user_name = request.form.get("username", "User")
    webhook_id = str(uuid.uuid4())

    supabase.table("temp_webhooks").insert({
        "user_name": user_name,
        "webhook_id": webhook_id,
        "logs": []
    }).execute()

    return redirect(url_for('webhook_page', webhook_id=webhook_id))

@app.route('/webhook/<webhook_id>', methods=['GET'])
def webhook_page(webhook_id):
    data = supabase.table("temp_webhooks").select("*").eq("webhook_id", webhook_id).single().execute()
    if data.data:
        return render_template("webhook.html", webhook_id=webhook_id, user=data.data["user_name"])
    return "Webhook not found", 404

@app.route('/hook/<webhook_id>', methods=['POST'])
def receive_webhook(webhook_id):
    body = request.get_json(force=True)
    entry = {
        "time": datetime.utcnow().isoformat(),
        "content": body
    }

    existing = supabase.table("temp_webhooks").select("logs").eq("webhook_id", webhook_id).single().execute()
    if existing.data:
        logs = existing.data.get("logs", [])
        logs.append(entry)
        supabase.table("temp_webhooks").update({
            "logs": logs
        }).eq("webhook_id", webhook_id).execute()

    return jsonify({"status": "received"}), 200

@app.route('/logs/<webhook_id>', methods=['GET'])
def get_logs(webhook_id):
    data = supabase.table("temp_webhooks").select("logs").eq("webhook_id", webhook_id).single().execute()
    if data.data:
        return jsonify(data.data["logs"])
    return jsonify([])

if __name__ == "__main__":
    app.run(debug=True)

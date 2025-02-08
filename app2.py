import os
import requests
import base64
from flask import Flask, request, jsonify, redirect, session,render_template
from werkzeug.utils import secure_filename
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
print("Loading environment variables...")
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super_secret_key")
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'jpg', 'jpeg', 'png'}

# LinkedIn API Credentials
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")
LINKEDIN_PROFILE_ID = os.getenv("LINKEDIN_PROFILE_ID")

# print(LINKEDIN_CLIENT_ID)
# LinkedIn OAuth URLs
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

# Configure Gemini API
print("Configuring Gemini API...")
genai.configure(api_key=GEMINI_API_KEY)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/login')
def login():
    """Redirects user to LinkedIn OpenID Connect login"""
    SCOPES = "openid profile email w_member_social"
    
    auth_url = (
        f"{LINKEDIN_AUTH_URL}?response_type=code"
        f"&client_id={LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={LINKEDIN_REDIRECT_URI}"
        f"&scope={SCOPES}"
    )
    return redirect(auth_url)
@app.route('/upload_page')
def upload_page():
    """Serves the HTML upload page"""
    return render_template("index.html")

@app.route('/callback')
def callback():
    """Handles LinkedIn OAuth callback and retrieves access & ID tokens."""
    code = request.args.get("code")
    # print("code",code)
    if not code:
        return jsonify({"error": "Authorization code not received"}), 400

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
    }

    response = requests.post(LINKEDIN_TOKEN_URL, data=token_data)
    token_json = response.json()
    print("LinkedIn Token Response:", token_json)
    if "access_token" not in token_json:
        return jsonify({"error": "Failed to get access token", "details": token_json}), 400

    session["linkedin_access_token"] = token_json["access_token"]
    
    # Retrieve OpenID Connect ID Token if available
    id_token = token_json.get("id_token")
    if id_token:
        session["linkedin_id_token"] = id_token
    
    session.modified = True  # Ensure session updates

    return render_template('index.html')
    return jsonify({
        "message": "Login successful!",
        "access_token": token_json["access_token"],
        "id_token": id_token
    })





@app.route('/upload', methods=['GET','POST'])
def upload_media():
    """Handles media uploads and posts to LinkedIn"""
    if "linkedin_access_token" not in session:
        print("USer not Authenticated")
        return jsonify({"error": "User not authenticated. Please log in via /login"}), 401

    if 'media' not in request.files:
        return jsonify({'error': 'No media files provided'}), 400

    media_files = request.files.getlist('media')
    saved_files = []

    for file in media_files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            saved_files.append(filepath)

    # Generate LinkedIn post content
    try:
        content = generate_linkedin_post(saved_files)
        post_result = post_to_linkedin(saved_files, content)
        return jsonify({'message': 'Media posted to LinkedIn', 'content': content, 'post_result': post_result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def generate_linkedin_post(images):
    """Generates a LinkedIn post using Gemini AI"""
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    image_parts = [genai.upload_file(img) for img in images]

    prompt = """You are an AI assistant creating a professional yet engaging LinkedIn post..."""
    response = model.generate_content([prompt] + image_parts)

    return response.text


def post_to_linkedin(media_paths, content):
    """Uploads media and posts content to LinkedIn"""
    access_token = session.get("linkedin_access_token")
    if not access_token:
        raise ValueError("No LinkedIn access token found")

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    uploaded_assets = []

    for media_path in media_paths:
        register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
        is_video = media_path.lower().endswith(('.mp4', '.avi', '.mov'))
        media_recipe = "urn:li:digitalmediaRecipe:feedshare-video" if is_video else "urn:li:digitalmediaRecipe:feedshare-image"

        data = {
            "registerUploadRequest": {
                "recipes": [media_recipe],
                "owner": f"urn:li:person:{LINKEDIN_PROFILE_ID}",
                "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
            }
        }

        response = requests.post(register_url, json=data, headers=headers)
        upload_details = response.json()
        upload_url = upload_details["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = upload_details["value"]["asset"]

        with open(media_path, "rb") as media_file:
            requests.put(upload_url, headers=headers, data=media_file)

        uploaded_assets.append({"status": "READY", "media": asset_urn})

    post_url = "https://api.linkedin.com/v2/ugcPosts"
    post_data = {
        "author": f"urn:li:person:{LINKEDIN_PROFILE_ID}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "MULTIPLE" if len(uploaded_assets) > 1 else ("VIDEO" if is_video else "IMAGE"),
                "media": uploaded_assets
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }

    post_response = requests.post(post_url, json=post_data, headers=headers)
    return post_response.json()


@app.route('/logout')
def logout():
    """Logs the user out and clears the session"""
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    print("Starting Flask server...")
    app.run(debug=True)

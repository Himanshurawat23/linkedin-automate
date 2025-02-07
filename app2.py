# import os
# import requests
# import base64
# from flask import Flask, request, jsonify, redirect, session
# from werkzeug.utils import secure_filename
# import google.generativeai as genai
# from dotenv import load_dotenv
# import cv2

# # Load environment variables
# print("Loading environment variables...")
# load_dotenv()

# app = Flask(__name__)
# app.secret_key = os.getenv("FLASK_SECRET_KEY", "super_secret_key")
# app.config['UPLOAD_FOLDER'] = 'uploads/'
# app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'jpg', 'jpeg', 'png'}

# # Gemini API and LinkedIn credentials
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
# LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
# LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")
# LINKEDIN_PROFILE_ID = os.getenv("LINKEDIN_PROFILE_ID")

# # Configure Gemini
# print("Configuring Gemini API...")
# genai.configure(api_key=GEMINI_API_KEY)

# def allowed_file(filename):
#     print(f"Checking if file {filename} is allowed...")
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# def generate_linkedin_post(images):
#     print("Generating LinkedIn post content using Gemini...")
#     model = genai.GenerativeModel('gemini-1.5-pro-latest')
    
#     # Prepare image parts
#     image_parts = []
#     for img in images:
#         print(f"Uploading image {img} to Gemini...")
#         image_parts.append(genai.upload_file(img))
    
#     prompt = """You are an AI assistant creating a professional yet engaging LinkedIn post..."""
    
#     response = model.generate_content([prompt] + image_parts)
#     print("Post content generated successfully!")
#     return response.text

# @app.route('/upload', methods=['POST'])
# def upload_media():
#     print("Received upload request...")
#     if "linkedin_access_token" not in session:
#         print("User not authenticated!")
#         return jsonify({"error": "User not authenticated. Please log in via /login"}), 401

#     if 'media' not in request.files:
#         print("No media files provided!")
#         return jsonify({'error': 'No media files provided'}), 400

#     media_files = request.files.getlist('media')
    
#     if not media_files:
#         print("No selected files!")
#         return jsonify({'error': 'No selected files'}), 400

#     # Validate and save files
#     saved_files = []
#     for file in media_files:
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             print(f"Saving file to {filepath}...")
#             file.save(filepath)
#             saved_files.append(filepath)

#     # Generate LinkedIn post content
#     try:
#         content = generate_linkedin_post(saved_files)
#         print("Generated LinkedIn post content:", content)
        
#         # Post to LinkedIn
#         post_result = post_to_linkedin(saved_files, content)
#         print("Successfully posted to LinkedIn!")
        
#         return jsonify({
#             'message': 'Media processed and posted to LinkedIn', 
#             'content': content,
#             'post_result': post_result
#         }), 200

#     except Exception as e:
#         print("Error occurred:", str(e))
#         return jsonify({'error': str(e)}), 500

# def post_to_linkedin(media_paths, content):
#     print("Posting media and content to LinkedIn...")
#     access_token = session.get("linkedin_access_token")
#     if not access_token:
#         print("No LinkedIn access token found!")
#         raise ValueError("No LinkedIn access token found")

#     # Asset upload preparation
#     uploaded_assets = []
#     for media_path in media_paths:
#         print(f"Preparing upload session for {media_path}...")
#         register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
#         headers = {
#             "Authorization": f"Bearer {access_token}",
#             "Content-Type": "application/json"
#         }
        
#         is_video = media_path.lower().endswith(('.mp4', '.avi', '.mov'))
#         media_recipe = "urn:li:digitalmediaRecipe:feedshare-video" if is_video else "urn:li:digitalmediaRecipe:feedshare-image"
        
#         data = {
#             "registerUploadRequest": {
#                 "recipes": [media_recipe],
#                 "owner": f"urn:li:person:{LINKEDIN_PROFILE_ID}",
#                 "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
#             }
#         }
        
#         response = requests.post(register_url, json=data, headers=headers)
#         upload_details = response.json()
#         upload_url = upload_details["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
#         asset_urn = upload_details["value"]["asset"]
        
#         print(f"Uploading media {media_path} to LinkedIn...")
#         with open(media_path, "rb") as media_file:
#             upload_response = requests.put(upload_url, headers=headers, data=media_file)
        
#         uploaded_assets.append({"status": "READY", "media": asset_urn})
    
#     print("Creating LinkedIn post...")
#     post_url = "https://api.linkedin.com/v2/ugcPosts"
#     post_data = {
#         "author": f"urn:li:person:{LINKEDIN_PROFILE_ID}",
#         "lifecycleState": "PUBLISHED",
#         "specificContent": {
#             "com.linkedin.ugc.ShareContent": {
#                 "shareCommentary": {"text": content},
#                 "shareMediaCategory": "MULTIPLE" if len(uploaded_assets) > 1 else ("VIDEO" if is_video else "IMAGE"),
#                 "media": uploaded_assets
#             }
#         },
#         "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
#     }

#     post_response = requests.post(post_url, json=post_data, headers=headers)
#     print("LinkedIn post response:", post_response.json())
#     return post_response.json()

# if __name__ == '__main__':
#     print("Ensuring uploads directory exists...")
#     os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
#     print("Starting Flask server...")
#     app.run(debug=True)


import os
import requests
import base64
from flask import Flask, request, jsonify, redirect, session
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
    """Redirects user to LinkedIn OAuth login"""
    auth_url = (
        f"{LINKEDIN_AUTH_URL}?response_type=code"
        f"&client_id={LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={LINKEDIN_REDIRECT_URI}"
        f"&scope=r_liteprofile r_emailaddress w_member_social"
    )
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """Handles LinkedIn OAuth callback and retrieves access token."""
    code = request.args.get("code")
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

    if "access_token" not in token_json:
        return jsonify({"error": "Failed to get access token", "details": token_json}), 400

    session["linkedin_access_token"] = token_json["access_token"]
    session.modified = True  # Ensure session updates

    return jsonify({"message": "Login successful!", "access_token": token_json["access_token"]})


@app.route('/upload', methods=['POST'])
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

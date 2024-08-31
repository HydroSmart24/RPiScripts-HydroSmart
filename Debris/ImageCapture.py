import os
import subprocess
import firebase_admin
from firebase_admin import credentials, firestore, storage
import uuid  # To generate unique filenames
from datetime import datetime

# Path to the Firebase service account JSON file
firebase_credentials_file = os.path.join(os.path.dirname(__file__), '..', 'Firebase', 'serviceAccountKey.json')

# Initialize Firebase Admin SDK with service account credentials
cred = credentials.Certificate(firebase_credentials_file)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'rpiwaterconsumption.appspot.com'
})

db = firestore.client()
bucket = storage.bucket()

def generate_unique_filename(base_name):
    """Generate a unique filename by appending a UUID to the base name."""
    name, ext = os.path.splitext(base_name)
    unique_name = f"{name}_{uuid.uuid4().hex}{ext}"
    return unique_name

def capture_image(image_path="output_image.jpg", retries=3):
    command = [
        "ffmpeg", "-f", "v4l2", "-input_format", "mjpeg", "-video_size", "640x480",
        "-i", "/dev/video0", "-vf", "format=yuv420p", "-vframes", "1", image_path
    ]
    
    attempt = 0
    while attempt < retries:
        try:
            # Run the FFmpeg command to capture the image
            subprocess.run(command, check=True)
            print(f"Image captured successfully: {image_path}")
            return True
        except subprocess.CalledProcessError:
            attempt += 1
            print(f"Failed to capture image on attempt {attempt}. Retrying...")
    
    print("Failed to capture image after all retries.")
    return False

def upload_to_firebase(image_path):
    try:
        # Get the current timestamp
        timestamp = datetime.utcnow().isoformat()

        # Upload the image file to Firebase Storage with metadata
        blob = bucket.blob(f'images/{os.path.basename(image_path)}')
        metadata = {"timestamp": timestamp}  # Add metadata with timestamp
        blob.upload_from_filename(image_path, content_type='image/jpeg')
        blob.metadata = metadata
        blob.patch()  # Apply the metadata

        blob.make_public()  # Optional: Make the file publicly accessible

        # Get the public URL of the image
        image_url = blob.public_url
        print(f"Image uploaded to Firebase Storage: {image_url}")

        # Store the image URL and metadata in Firestore
        document_id = os.path.splitext(os.path.basename(image_path))[0]
        doc_ref = db.collection('images').document(document_id)
        doc_ref.set({
            'image_url': image_url,
            'timestamp': timestamp  # Save the timestamp in Firestore
        })

        print(f"Image URL and metadata uploaded to Firestore: {image_url}")
    except Exception as e:
        print(f"Failed to upload image to Firebase: {e}")

def main():
    # Generate a unique filename before capturing the image
    image_path = generate_unique_filename("output_image.jpg")
    
    if capture_image(image_path):
        upload_to_firebase(image_path)

if __name__ == "__main__":
    main()

import os
import subprocess
import firebase_admin
from firebase_admin import credentials, firestore, storage
import uuid  # To generate unique filenames

# Path to the Firebase service account JSON file
firebase_credentials_file = os.path.join(os.path.dirname(__file__), '..', 'Firebase', 'serviceAccountKey.json')

# Initialize Firebase Admin SDK with service account credentials
cred = credentials.Certificate(firebase_credentials_file)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'rpiwaterconsumption.appspot.com'
})

db = firestore.client()
bucket = storage.bucket()

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

def generate_unique_filename(base_name):
    """Generate a unique filename by appending a UUID to the base name."""
    name, ext = os.path.splitext(base_name)
    unique_name = f"{name}_{uuid.uuid4().hex}{ext}"
    return unique_name

def upload_to_firebase(image_path):
    try:
        # Check if the image already exists in Firebase Storage
        blob = bucket.blob(f'images/{os.path.basename(image_path)}')
        if blob.exists():
            # Generate a new unique filename if the image already exists
            image_path = generate_unique_filename(image_path)
            blob = bucket.blob(f'images/{os.path.basename(image_path)}')

        # Upload the image file to Firebase Storage
        blob.upload_from_filename(image_path)
        blob.make_public()  # Optional: Make the file publicly accessible

        # Get the public URL of the image
        image_url = blob.public_url
        print(f"Image uploaded to Firebase Storage: {image_url}")

        # Store the image URL in Firestore
        document_id = os.path.splitext(os.path.basename(image_path))[0]
        doc_ref = db.collection('images').document(document_id)
        doc_ref.set({'image_url': image_url})

        print(f"Image URL uploaded to Firestore: {image_url}")
    except Exception as e:
        print(f"Failed to upload image to Firebase: {e}")

def main():
    image_path = "output_image.jpg"
    if capture_image(image_path):
        upload_to_firebase(image_path)

if __name__ == "__main__":
    main()

import os
import subprocess
import firebase_admin
from firebase_admin import credentials, firestore

# Path to the Firebase service account JSON file
firebase_credentials_file = os.path.join(os.path.dirname(__file__), '..', 'Firebase', 'serviceAccountKey.json')

# Initialize Firebase Admin SDK with service account credentials
cred = credentials.Certificate(firebase_credentials_file)
firebase_admin.initialize_app(cred)
db = firestore.client()

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
        # Assuming you want to store the image in Firebase Storage
        storage_path = f'images/{os.path.basename(image_path)}'
        storage_ref = db.collection('images').document(storage_path)
        
        # Store image metadata or reference in Firestore
        storage_ref.set({'image_path': storage_path})
        
        print(f"Image metadata uploaded to Firestore: {storage_path}")
    except Exception as e:
        print(f"Failed to upload image metadata to Firestore: {e}")

def main():
    image_path = "output_image.jpg"
    if capture_image(image_path):
        upload_to_firebase(image_path)

if __name__ == "__main__":
    main()

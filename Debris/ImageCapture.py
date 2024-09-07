import os
import subprocess
import firebase_admin
from firebase_admin import credentials, firestore, storage
import uuid  # To generate unique filenames
from datetime import datetime
import pytz  # For timezone handling

# Path to the Firebase service account JSON file
firebase_credentials_file = os.path.join(os.path.dirname(__file__), '..', 'Firebase', 'serviceAccountKey.json')

# Initialize Firebase Admin SDK with service account credentials
cred = credentials.Certificate(firebase_credentials_file)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'rpiwaterconsumption.appspot.com'
})

db = firestore.client()
bucket = storage.bucket()

# Document and collection details
document_id = 'DkIsHAZoGT5XIWKhTKd0'
collection_name = 'relayState'
doc_ref = db.collection(collection_name).document(document_id)

# Function to generate a unique filename
def generate_unique_filename(base_name):
    """Generate a unique filename by appending a UUID to the base name."""
    name, ext = os.path.splitext(base_name)
    unique_name = f"{name}_{uuid.uuid4().hex}{ext}"
    return unique_name

# Function to capture an image
def capture_image(image_path="output_image.jpg", retries=3):
    command = [
        "ffmpeg", "-f", "v4l2", "-input_format", "mjpeg", "-video_size", "640x480",
        "-i", "/dev/video0", "-vf", "format=yuv420p", "-vframes", "1", image_path
    ]
    
    attempt = 0
    while attempt < retries:
        try:
            subprocess.run(command, check=True)
            print(f"Image captured successfully: {image_path}")
            return True
        except subprocess.CalledProcessError:
            attempt += 1
            print(f"Failed to capture image on attempt {attempt}. Retrying...")
    
    print("Failed to capture image after all retries.")
    return False

# Function to upload the image to Firebase Storage and Firestore
def upload_to_firebase(image_path):
    try:
        # Get the current timestamp in local time
        local_timezone = pytz.timezone('Asia/Colombo')  # Adjust to your local timezone
        timestamp = datetime.now(local_timezone).isoformat()  # Local time with timezone info

        # Upload the image file to Firebase Storage with metadata
        blob = bucket.blob(f'images/{os.path.basename(image_path)}')
        metadata = {"timestamp": timestamp}
        blob.upload_from_filename(image_path, content_type='image/jpeg')
        blob.metadata = metadata
        blob.patch()  # Apply the metadata

        # Make the file publicly accessible (optional)
        blob.make_public()

        # Get the public URL of the image
        image_url = blob.public_url

        # Store the image URL and metadata in Firestore
        doc_ref = db.collection('images').document(os.path.splitext(os.path.basename(image_path))[0])
        doc_ref.set({
            'image_url': image_url,
            'timestamp': timestamp
        })

        print(f"Image URL and metadata uploaded to Firestore: {image_url}")

        # Delete the local file after successful upload
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"Local file {image_path} deleted.")
        else:
            print(f"Local file {image_path} not found for deletion.")
            
    except Exception as e:
        print(f"Failed to upload image to Firebase: {e}")

# Function to check the latest distance from avgDistance collection
def check_latest_distance():
    try:
        # Get the most recent document from avgDistance collection, sorted by time
        docs = db.collection('avgDistance').order_by('time', direction=firestore.Query.DESCENDING).limit(1).get()
        if docs:
            latest_doc = docs[0]
            distance = latest_doc.to_dict().get('distance', 100)  # Default to 100 if no value is found
            print(f"Latest distance: {distance}")
            return distance
        else:
            print("No documents found in avgDistance collection.")
            return 100  # Default to 100 if no documents are found
    except Exception as e:
        print(f"Error retrieving latest distance: {e}")
        return 100  # Default to 100 in case of an error

# Firestore document listener function
def on_snapshot(doc_snapshot, changes, read_time):
    for doc in doc_snapshot:
        state = doc.to_dict().get("state")
        print(f"Document state: {state}")

        if state == "OFF":
            print("State changed to OFF. Checking latest distance before capturing image...")
            distance = check_latest_distance()  # Check the latest distance from avgDistance
            if distance <= 40:
                print(f"Distance is {distance}, capturing image...")
                image_path = generate_unique_filename("output_image.jpg")
                if capture_image(image_path):
                    upload_to_firebase(image_path)
            else:
                print(f"Distance is {distance}. Image capture skipped.")
        else:
            print(f"State is still {state}. No action taken.")

# Listen for changes in the document
doc_watch = doc_ref.on_snapshot(on_snapshot)

# Keep the program running to listen for changes
print("Listening for document changes...")
while True:
    try:
        pass  # Keep the script running
    except KeyboardInterrupt:
        print("Stopping the listener...")
        doc_watch.unsubscribe()
        break

import os
import subprocess
import pyrebase

# Initialize Firebase using serviceAccountKey.json
firebase = pyrebase.initialize_app()
storage = firebase.storage()

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
        storage.child(image_path).put(image_path)
        print(f"Image uploaded to Firebase: {image_path}")
    except Exception as e:
        print(f"Failed to upload image to Firebase: {e}")

def main():
    image_path = "output_image.jpg"
    if capture_image(image_path):
        upload_to_firebase(image_path)

if __name__ == "__main__":
    main()

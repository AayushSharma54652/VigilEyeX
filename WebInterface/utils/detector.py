import cv2
import numpy as np
import os
import time
from collections import deque
from keras.models import load_model
from mtcnn.mtcnn import MTCNN
import matplotlib.pyplot as plt
from datetime import datetime
import pytz

class ViolenceDetector:
    def __init__(self, model_path='models/modelnew.h5'):
        """Initialize the violence detector with the trained model."""
        # Load the model if it exists
        self.model = None
        try:
            if os.path.exists(model_path):
                print(f"Loading model from {model_path}...")
                # Suppress warnings during model loading
                import tensorflow as tf
                os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
                tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
                
                self.model = load_model(model_path)
                print("Model loaded successfully!")
            else:
                print(f"Model not found at {model_path}. Please ensure the model file exists.")
        except Exception as e:
            print(f"Error loading model: {e}")
            print("The system will run without violence detection capabilities.")
        
        # Initialize prediction queue for smoothing
        self.Q = deque(maxlen=128)
        
        # Initialize MTCNN for face detection
        self.face_detector = MTCNN()
        
        # Violence detection counters and parameters
        self.violence_counter = 0
        self.violence_threshold = 40  # Same as in your original code
        self.last_alert_time = 0
        self.alert_cooldown = 60  # Seconds between alerts
        
        # Create confidence history for smoothing predictions
        self.confidence_history = []
        self.history_size = 10
        
        # Detection states
        self.current_state = "MONITORING"  # States: MONITORING, WARNING, ALERT
        self.warning_threshold = 0.70  # Higher confidence for warnings
        self.alert_threshold = 0.85  # Very high confidence for alerts
        
    def process_frame(self, frame):
        """
        Process a single frame for violence detection.
        
        Args:
            frame: The input frame to process
            
        Returns:
            processed_frame: The frame with annotations
            is_violence: Boolean indicating if violence is detected
        """
        if self.model is None:
            # If model isn't loaded, just return the original frame
            return frame, False
        
        # Clone the frame for output
        output = frame.copy()
        
        # Get frame dimensions for UI positioning
        height, width = output.shape[:2]
        
        # Preprocess the frame for the model
        processed = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        processed = cv2.resize(processed, (128, 128)).astype("float32")
        processed = processed.reshape(128, 128, 3) / 255
        
        # Make prediction with reduced verbosity
        try:
            # Suppress TensorFlow warnings during prediction
            import tensorflow as tf
            old_level = tf.compat.v1.logging.get_verbosity()
            tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
            
            # Make prediction
            preds = self.model.predict(np.expand_dims(processed, axis=0), verbose=0)[0]
            
            # Restore logging level
            tf.compat.v1.logging.set_verbosity(old_level)
        except Exception as e:
            print(f"Error during prediction: {e}")
            # Return a safe default if prediction fails
            preds = np.array([0.0])
            
        # Add to prediction queue for smoothing
        self.Q.append(preds)
        
        # Get confidence score (probability of violence)
        confidence_score = float(preds[0])
        
        # Add to confidence history for temporal smoothing
        self.confidence_history.append(confidence_score)
        if len(self.confidence_history) > self.history_size:
            self.confidence_history.pop(0)
        
        # Calculate smoothed confidence using recent history
        smoothed_confidence = sum(self.confidence_history) / len(self.confidence_history)
        
        # Determine violence state based on smoothed confidence
        is_violence = smoothed_confidence > 0.50
        is_warning = smoothed_confidence > self.warning_threshold
        is_alert = smoothed_confidence > self.alert_threshold
        
        # Update violence counter based on confidence
        if is_violence:
            self.violence_counter += 1
        else:
            # Decrease counter more slowly than it increases
            self.violence_counter = max(0, self.violence_counter - 0.5)
        
        # Determine if we should trigger an alert
        should_alert = (self.violence_counter >= self.violence_threshold and 
                        (time.time() - self.last_alert_time) > self.alert_cooldown)
        
        # Update state based on counters and thresholds
        if should_alert or is_alert:
            self.current_state = "ALERT"
            self.last_alert_time = time.time()
            # Reset counter partially to avoid continuous alerts
            self.violence_counter = self.violence_threshold // 2
        elif is_warning:
            self.current_state = "WARNING"
        else:
            self.current_state = "MONITORING"
        
        # Draw background rectangle for status display
        status_bg_color = (0, 0, 0)
        status_bg_opacity = 0.7
        status_height = 140
        overlay = output.copy()
        cv2.rectangle(overlay, (0, 0), (width, status_height), status_bg_color, -1)
        cv2.addWeighted(overlay, status_bg_opacity, output, 1 - status_bg_opacity, 0, output)
        
        # Set UI colors based on state
        if self.current_state == "ALERT":
            status_color = (0, 0, 255)  # Red for alert
            status_text = "VIOLENCE ALERT!"
        elif self.current_state == "WARNING":
            status_color = (0, 165, 255)  # Orange for warning
            status_text = "Potential Violence Detected"
        else:
            status_color = (0, 255, 0)  # Green for monitoring
            status_text = "No Violence Detected"
        
        # Add status text and confidence to the output frame
        cv2.putText(output, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, status_color, 3)
        
        confidence_text = f"Confidence: {smoothed_confidence*100:.1f}%"
        cv2.putText(output, confidence_text, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Add counter indicator
        counter_text = f"Alert Counter: {int(self.violence_counter)}/{self.violence_threshold}"
        cv2.putText(output, counter_text, (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # For alert state, add additional visual warning
        if self.current_state == "ALERT":
            # Pulse animation based on time
            pulse = 0.7 + 0.3 * np.sin(time.time() * 5)
            
            # Add alert border
            border_thickness = 15
            border_overlay = output.copy()
            cv2.rectangle(border_overlay, (0, 0), (width, height), (0, 0, 255), border_thickness)
            cv2.addWeighted(border_overlay, pulse, output, 1 - pulse, 0, output)
            
            # Add centered alert message
            alert_text = "ALERT!"
            alert_font = cv2.FONT_HERSHEY_SIMPLEX
            alert_scale = 3
            alert_thickness = 5
            
            # Get text size to center it
            text_size = cv2.getTextSize(alert_text, alert_font, alert_scale, alert_thickness)[0]
            text_x = (width - text_size[0]) // 2
            text_y = (height + text_size[1]) // 2
            
            # Add semi-transparent background
            text_bg_overlay = output.copy()
            text_bg_padding = 20
            cv2.rectangle(text_bg_overlay, 
                         (text_x - text_bg_padding, text_y - text_size[1] - text_bg_padding),
                         (text_x + text_size[0] + text_bg_padding, text_y + text_bg_padding),
                         (0, 0, 0), -1)
            cv2.addWeighted(text_bg_overlay, 0.7, output, 0.3, 0, output)
            
            # Add alert text
            cv2.putText(output, alert_text, (text_x, text_y), 
                       alert_font, alert_scale, (0, 0, 255), alert_thickness)
        
        return output, self.current_state == "ALERT"
    
    def detect_faces(self, image):
        """
        Detect faces in the given image using MTCNN.
        
        Args:
            image: The input image
            
        Returns:
            faces: List of detected face bounding boxes
        """
        # Convert BGR to RGB (MTCNN expects RGB)
        if len(image.shape) == 3 and image.shape[2] == 3:
            if image.dtype == np.uint8:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image  # Assume it's already RGB
        else:
            return []  # Can't process this image
            
        # Detect faces
        try:
            faces = self.face_detector.detect_faces(image_rgb)
            return faces
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return []
    
    def draw_faces(self, image, faces):
        """
        Draw bounding boxes around detected faces.
        
        Args:
            image: The input image
            faces: List of detected face bounding boxes
            
        Returns:
            marked_image: Image with faces marked
        """
        marked_image = image.copy()
        
        for face in faces:
            x, y, width, height = face['box']
            confidence = face['confidence']
            
            # Draw rectangle around face
            cv2.rectangle(marked_image, (x, y), (x + width, y + height), (0, 255, 0), 2)
            
            # Add confidence text
            cv2.putText(marked_image, f"{confidence:.2f}", (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        return marked_image
    
    def extract_face_images(self, image, faces, output_folder):
        """
        Extract each face as a separate image and save to output folder.
        
        Args:
            image: The input image
            faces: List of detected face bounding boxes
            output_folder: Folder to save extracted faces
            
        Returns:
            face_paths: List of paths to saved face images
        """
        face_paths = []
        
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Current timestamp for filenames
        timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y%m%d_%H%M%S')
        
        for i, face in enumerate(faces):
            x, y, width, height = face['box']
            
            # Extract face region
            face_image = image[y:y+height, x:x+width]
            
            # Save face image
            face_path = os.path.join(output_folder, f"face_{timestamp}_{i}.jpg")
            cv2.imwrite(face_path, face_image)
            
            face_paths.append(face_path)
        
        return face_paths
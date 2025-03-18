from flask import Flask, render_template, Response, request, jsonify, redirect, url_for, flash
import cv2
import os
import time
from datetime import datetime
import pytz
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from threading import Thread
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from utils.camera import Camera
from utils.detector import ViolenceDetector
from utils.notifier import EmailNotifier, Notification, NotificationManager
from models import db, User, Camera as CameraModel, Incident as IncidentModel, Face as FaceModel
from forms import LoginForm, RegistrationForm, CameraForm, ProfileForm

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize the violence detector
detector = ViolenceDetector()

# Dictionary to store registered cameras
cameras = {}

# Dictionary to store incidents
incidents = []

# Initialize notification manager
notification_manager = NotificationManager()

# Set up email notification (if credentials are available)
if os.environ.get('EMAIL_SENDER') and os.environ.get('EMAIL_PASSWORD'):
    notification_manager.enable_method('email', True)
    notification_manager.email_notifier.set_credentials(
        os.environ.get('EMAIL_SENDER'),
        os.environ.get('EMAIL_PASSWORD')
    )
    
    # Add default recipients (replace with actual emails)
    default_recipients = os.environ.get('EMAIL_RECIPIENTS', '').split(',')
    for recipient in default_recipients:
        if recipient.strip():
            notification_manager.email_notifier.add_recipient(recipient.strip())

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        # Check if user exists and password is correct
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Redirect to the requested page or the index page
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data
        )
        
        # Make the first user an admin
        if User.query.count() == 0:
            user.is_admin = True
        
        # Save to database
        db.session.add(user)
        db.session.commit()
        
        flash('Your account has been created. You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    
    if request.method == 'GET':
        # Pre-fill the form with current user data
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
    
    if form.validate_on_submit():
        # Check current password if changing password
        if form.new_password.data:
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect.', 'danger')
                return render_template('profile.html', form=form)
            
            # Set new password
            current_user.set_password(form.new_password.data)
        
        # Update other fields
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        
        # Update email (check if it's not already taken by another user)
        if form.email.data != current_user.email:
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user and existing_user.id != current_user.id:
                flash('Email already in use by another account.', 'danger')
                return render_template('profile.html', form=form)
            current_user.email = form.email.data
        
        # Save changes
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', form=form)

# Main routes
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/camera')
@login_required
def camera_page():
    return render_template('camera.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', cameras=cameras)

@app.route('/incidents')
@login_required
def view_incidents():
    return render_template('incidents.html', incidents=incidents)

@app.route('/video_feed')
@login_required
def video_feed():
    """Video streaming route."""
    camera_id = request.args.get('camera_id', 'webcam')
    return Response(gen_frames(camera_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
@login_required
def get_status():
    """API endpoint to get current detection status."""
    # Get current detector state (if available)
    try:
        current_state = detector.current_state.lower() if hasattr(detector, 'current_state') else 'monitoring'
        
        # Get the most recent incident
        last_incident = incidents[-1] if incidents else None
        
        return jsonify({
            'status': current_state,
            'last_incident': last_incident['timestamp'] if last_incident else None,
            'alert_count': len(incidents)
        })
    except Exception as e:
        print(f"Error getting status: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'alert_count': len(incidents)
        })

@app.route('/add_camera', methods=['POST'])
@login_required
def add_camera():
    """Add a new camera to the system."""
    camera_name = request.form.get('name')
    camera_url = request.form.get('url')
    camera_location = request.form.get('location')
    
    if not all([camera_name, camera_url, camera_location]):
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    camera_id = f"camera_{len(cameras) + 1}"
    cameras[camera_id] = {
        'id': camera_id,
        'name': camera_name,
        'url': camera_url,
        'location': camera_location,
        'status': 'active'
    }
    
    return redirect(url_for('dashboard'))

@app.route('/export_incidents', methods=['GET'])
@login_required
def export_incidents():
    """Export incidents as CSV file."""
    import csv
    from io import StringIO
    
    # Create a CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Timestamp', 'Location', 'Faces Detected'])
    
    # Write data
    for incident in incidents:
        writer.writerow([
            incident['id'],
            incident['timestamp'],
            incident['location'],
            'Yes' if incident.get('faces_detected', False) else 'No'
        ])
    
    # Prepare response
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=incidents_report.csv',
            'Content-Type': 'text/csv'
        }
    )
    
    return response

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def notification_settings():
    """Manage notification settings."""
    if request.method == 'POST':
        # Update notification methods
        notification_manager.enable_method('email', request.form.get('email_enabled') == 'on')
        notification_manager.enable_method('browser', request.form.get('browser_enabled') == 'on')
        notification_manager.enable_method('sound', request.form.get('sound_enabled') == 'on')
        
        # Update email settings
        if request.form.get('email_sender') and request.form.get('email_password'):
            notification_manager.email_notifier.set_credentials(
                request.form.get('email_sender'),
                request.form.get('email_password')
            )
        
        # Update email recipients
        recipients = request.form.get('email_recipients', '').split(',')
        notification_manager.email_notifier.recipients = []
        for recipient in recipients:
            if recipient.strip():
                notification_manager.email_notifier.add_recipient(recipient.strip())
        
        return redirect(url_for('notification_settings'))
    
    return render_template('settings.html', 
                          notification_manager=notification_manager,
                          settings=notification_manager.enabled_methods)

# User management routes (admin only)
@app.route('/admin/users')
@login_required
def admin_users():
    """Manage users (admin only)."""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
def toggle_admin(user_id):
    """Toggle admin status for a user."""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent removing admin status from self
    if user.id == current_user.id:
        flash('You cannot remove your own admin privileges.', 'danger')
        return redirect(url_for('admin_users'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    flash(f"Admin status for {user.username} has been {'granted' if user.is_admin else 'revoked'}.", 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete a user."""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting self
    if user.id == current_user.id:
        flash('You cannot delete your own account here.', 'danger')
        return redirect(url_for('admin_users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f"User {user.username} has been deleted.", 'success')
    return redirect(url_for('admin_users'))

def gen_frames(camera_id='webcam'):
    """Generate frames from the specified camera."""
    # Initialize variables for frame rate control
    prev_frame_time = 0
    frame_skip = 0  # Process every frame initially
    
    # Initialize variables for alert state tracking
    current_incident = None
    incident_frames = []  # Store frames during an incident
    max_incident_frames = 30  # Maximum frames to capture during an incident
    incident_active = False
    face_detected = False
    
    try:
        # Use webcam for testing
        if camera_id == 'webcam':
            camera = cv2.VideoCapture(0)
        else:
            # Use the stored camera URL
            if camera_id in cameras:
                camera = cv2.VideoCapture(cameras[camera_id]['url'])
            else:
                # Return a default frame if camera not found
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "Camera not found", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                ret, buffer = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                return
        
        # Check if camera opened successfully
        if not camera.isOpened():
            # Return a default frame if camera failed to open
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "Camera failed to open", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            return
        
        # Set camera properties if available
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Create uploads directory if it doesn't exist
        uploads_dir = os.path.join('static', 'uploads')
        faces_dir = os.path.join(uploads_dir, 'faces')
        os.makedirs(uploads_dir, exist_ok=True)
        os.makedirs(faces_dir, exist_ok=True)
        
        while True:
            try:
                success, frame = camera.read()
                if not success:
                    # If frame read failed, provide an error frame
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, "Camera disconnected", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    ret, buffer = cv2.imencode('.jpg', frame)
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    # Wait a bit before trying again
                    time.sleep(1)
                    continue
                
                # Calculate FPS
                current_time = time.time()
                fps = 1 / (current_time - prev_frame_time) if prev_frame_time > 0 else 30
                prev_frame_time = current_time
                
                # Skip frames if processing is too slow (adjust based on performance)
                frame_skip = (frame_skip + 1) % 2  # Process every other frame (adjust as needed)
                if frame_skip != 0:
                    # Just encode the frame without processing
                    ret, buffer = cv2.imencode('.jpg', frame)
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    continue
                
                # Process the frame for violence detection
                try:
                    processed_frame, is_violence = detector.process_frame(frame)
                except Exception as e:
                    print(f"Error processing frame: {e}")
                    # If processing fails, just display the original frame with an error message
                    processed_frame = frame.copy()
                    cv2.putText(processed_frame, "Processing error", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    is_violence = False
                
                # Handle incident detection and recording
                if is_violence:
                    # If no incident is active, start a new one
                    if not incident_active:
                        timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')
                        incident_id = f"incident_{len(incidents) + 1}"
                        incident_active = True
                        incident_frames = []  # Reset frames collection
                        current_incident = {
                            'id': incident_id,
                            'timestamp': timestamp,
                            'location': cameras.get(camera_id, {'name': 'Webcam'})['name'],
                            'faces_detected': False,
                            'face_paths': []
                        }
                    
                    # Collect frames during the incident (to pick the best one)
                    if len(incident_frames) < max_incident_frames:
                        incident_frames.append(frame.copy())
                    
                    # Detect faces only once during the incident
                    if not face_detected and len(incident_frames) >= 10:  # Wait for a few frames before face detection
                        try:
                            # Detect faces in the current frame
                            faces = detector.detect_faces(frame)
                            
                            if faces:
                                current_incident['faces_detected'] = True
                                
                                # Extract face images
                                face_paths = []
                                for i, face in enumerate(faces):
                                    x, y, width, height = face['box']
                                    # Extract face with some margin
                                    margin = 20
                                    x_start = max(0, x - margin)
                                    y_start = max(0, y - margin)
                                    x_end = min(frame.shape[1], x + width + margin)
                                    y_end = min(frame.shape[0], y + height + margin)
                                    
                                    face_img = frame[y_start:y_end, x_start:x_end]
                                    
                                    # Save face image
                                    face_filename = f"{current_incident['id']}_face_{i+1}.jpg"
                                    face_path = os.path.join('faces', face_filename)
                                    full_face_path = os.path.join(uploads_dir, face_path)
                                    cv2.imwrite(full_face_path, face_img)
                                    face_paths.append(face_path)
                                
                                current_incident['face_paths'] = face_paths
                                face_detected = True
                        except Exception as e:
                            print(f"Error during face detection: {e}")
                
                elif incident_active:
                    # Incident has ended, finalize the recording
                    if incident_frames:
                        try:
                            # Select the middle frame as the representative image (usually clearest)
                            best_frame = incident_frames[len(incident_frames) // 2]
                            
                            # Save the incident image
                            incident_path = f"uploads/{current_incident['id']}.jpg"
                            full_path = os.path.join('static', incident_path)
                            cv2.imwrite(full_path, best_frame)
                            
                            # Add the image path to the incident
                            current_incident['image_path'] = incident_path
                            
                            # Add to incidents list
                            incidents.append(current_incident)
                            
                            # Send notifications through all enabled channels
                            notification = notification_manager.send_notification(current_incident)
                            
                            # Prepare face image URLs if faces were detected
                            face_urls = []
                            if current_incident['faces_detected'] and current_incident['face_paths']:
                                for face_path in current_incident['face_paths']:
                                    try:
                                        face_url = url_for('static', filename=os.path.join('uploads', face_path))
                                        face_urls.append(face_url)
                                    except Exception as e:
                                        print(f"Error creating face URL: {e}")
                            
                            # Emit WebSocket event for real-time notification
                            try:
                                socketio.emit('incident_alert', {
                                    'id': current_incident['id'],
                                    'timestamp': current_incident['timestamp'],
                                    'location': current_incident['location'],
                                    'image_url': url_for('static', filename=current_incident['image_path']),
                                    'faces_detected': current_incident['faces_detected'],
                                    'face_urls': face_urls
                                })
                            except Exception as e:
                                print(f"Error sending WebSocket notification: {e}")
                            
                            # Print for debugging
                            print(f"Incident recorded: {current_incident['id']} with {len(incident_frames)} frames")
                        except Exception as e:
                            print(f"Error saving incident: {e}")
                    
                    # Reset incident state
                    incident_active = False
                    incident_frames = []
                    face_detected = False
                
                # Add FPS to the processed frame
                cv2.putText(processed_frame, f"FPS: {int(fps)}", 
                           (processed_frame.shape[1] - 120, processed_frame.shape[0] - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Encode the processed frame for streaming
                ret, buffer = cv2.imencode('.jpg', processed_frame)
                
                # Yield the frame for the response
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except Exception as e:
                print(f"Error in frame processing loop: {e}")
                # Provide an error frame if an exception occurs
                error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(error_frame, f"Error: {str(e)[:40]}", (20, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                ret, buffer = cv2.imencode('.jpg', error_frame)
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                time.sleep(1)  # Brief pause before continuing
    
    except Exception as e:
        print(f"Critical error in gen_frames: {e}")
        # Final cleanup
        try:
            camera.release()
        except:
            pass

@socketio.on('connect')
def handle_connect():
    """Handle client connection to WebSocket."""
    print('Client connected to WebSocket')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection from WebSocket."""
    print('Client disconnected from WebSocket')

@socketio.on('test_notification')
def handle_test_notification(data):
    """Handle test notification request."""
    # Create a test incident
    test_incident = {
        'id': f'test_{int(time.time())}',
        'timestamp': datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S'),
        'location': data.get('location', 'Test Location'),
        'faces_detected': False,
        'image_path': 'uploads/test_incident.jpg' if os.path.exists('static/uploads/test_incident.jpg') else None
    }
    
    # Send test notification
    notification = notification_manager.send_notification(test_incident)
    
    # Emit response
    emit('test_notification_result', {
        'success': True,
        'message': 'Test notification sent successfully'
    })

# Create database tables before first request
# Note: before_first_request is deprecated in Flask 2.0+
# Use with app.app_context() instead as shown in the main block
@app.before_request
def handle_before_request():
    # This will run before every request
    # We'll perform DB initialization in the main block instead
    pass

if __name__ == '__main__':
    # Create uploads folder if it doesn't exist
    os.makedirs('static/uploads', exist_ok=True)
    os.makedirs('static/uploads/faces', exist_ok=True)
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Create admin user if no users exist
        if User.query.count() == 0:
            admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
            
            admin = User(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print(f"Created default admin user: {admin_username}")
    
    print("Violence Detection System starting up...")
    print("Notification methods enabled:")
    for method, enabled in notification_manager.enabled_methods.items():
        print(f"  - {method}: {'Enabled' if enabled else 'Disabled'}")
    
    # Add a default test image if none exists
    test_image_path = os.path.join('static', 'uploads', 'test_incident.jpg')
    if not os.path.exists(test_image_path):
        try:
            # Create a simple test image
            test_img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(test_img, "TEST INCIDENT", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)
            cv2.imwrite(test_image_path, test_img)
            print(f"Created test incident image at {test_image_path}")
        except Exception as e:
            print(f"Could not create test image: {e}")
    
    # Run the app with SocketIO
    socketio.run(app, debug=True, host='0.0.0.0', allow_unsafe_werkzeug=True)
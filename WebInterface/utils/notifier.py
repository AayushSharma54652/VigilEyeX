import os
import smtplib
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime

class Notification:
    """Base notification class"""
    
    def __init__(self, incident):
        """
        Initialize notification with incident details
        
        Args:
            incident: Dictionary containing incident details
        """
        self.incident = incident
        self.timestamp = incident.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.location = incident.get('location', 'Unknown')
        self.image_path = incident.get('image_path', None)
        self.faces_detected = incident.get('faces_detected', False)
        self.face_paths = incident.get('face_paths', [])
        self.id = incident.get('id', 'unknown')
    
    def get_subject(self):
        """Get notification subject"""
        return f"VIOLENCE ALERT - {self.location} - {self.timestamp}"
    
    def get_message(self):
        """Get notification message"""
        message = f"Violence detected at {self.location} on {self.timestamp}\n"
        message += f"Incident ID: {self.id}\n"
        
        if self.faces_detected:
            num_faces = len(self.face_paths) if self.face_paths else "Unknown number of"
            message += f"{num_faces} faces were detected in this incident.\n"
        else:
            message += f"No faces were detected in this incident.\n"
        
        message += f"\nView full details at: http://localhost:5000/incidents\n"
        
        return message

class EmailNotifier:
    """Email notification service"""
    
    def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587):
        """
        Initialize email notifier
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_sender = os.environ.get('EMAIL_SENDER', '')
        self.email_password = os.environ.get('EMAIL_PASSWORD', '')
        self.recipients = []
        
        # Cooldown mechanism to avoid spamming
        self.last_email_time = 0
        self.email_cooldown = 300  # 5 minutes in seconds
    
    def add_recipient(self, email):
        """Add a recipient email address"""
        if email not in self.recipients:
            self.recipients.append(email)
    
    def remove_recipient(self, email):
        """Remove a recipient email address"""
        if email in self.recipients:
            self.recipients.remove(email)
    
    def set_credentials(self, email, password):
        """Set sender email credentials"""
        self.email_sender = email
        self.email_password = password
    
    def can_send_email(self):
        """Check if cooldown period has passed"""
        return time.time() - self.last_email_time > self.email_cooldown
    
    def send_notification(self, notification, recipients=None):
        """
        Send email notification
        
        Args:
            notification: Notification object
            recipients: Optional list of recipient emails (uses default if None)
        
        Returns:
            bool: True if email was sent, False otherwise
        """
        # Check for credentials and recipients
        if not self.email_sender or not self.email_password:
            print("Email credentials not set")
            return False
        
        # Use provided recipients or default list
        email_recipients = recipients if recipients else self.recipients
        if not email_recipients:
            print("No recipients specified")
            return False
        
        # Check cooldown
        if not self.can_send_email():
            print("Email notification on cooldown")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = ', '.join(email_recipients)
            msg['Subject'] = notification.get_subject()
            
            # Add text part
            text = notification.get_message()
            msg.attach(MIMEText(text, 'plain'))
            
            # Begin HTML email content
            html = f"""
            <html>
            <body>
                <h2>Violence Alert</h2>
                <p>Violence detected at <strong>{notification.location}</strong> on {notification.timestamp}</p>
                <p>Incident ID: {notification.id}</p>
            """
            
            # Add incident image if available
            if notification.image_path and os.path.exists(os.path.join('static', notification.image_path)):
                with open(os.path.join('static', notification.image_path), 'rb') as img_file:
                    img = MIMEImage(img_file.read())
                    img.add_header('Content-ID', f'<image{notification.id}>')
                    img.add_header('Content-Disposition', 'inline', filename=f'incident_{notification.id}.jpg')
                    msg.attach(img)
                
                html += f"""
                <h3>Incident Image:</h3>
                <p><img src="cid:image{notification.id}" style="max-width: 800px; border: 1px solid #ddd;"></p>
                """
            
            # Add face images if available
            if notification.faces_detected and notification.face_paths:
                html += f"<h3>Detected Faces:</h3><div style='display: flex; flex-wrap: wrap; gap: 10px;'>"
                
                for i, face_path in enumerate(notification.face_paths):
                    face_file_path = os.path.join('static', 'uploads', face_path)
                    if os.path.exists(face_file_path):
                        with open(face_file_path, 'rb') as face_file:
                            face_img = MIMEImage(face_file.read())
                            face_cid = f"face{notification.id}_{i}"
                            face_img.add_header('Content-ID', f'<{face_cid}>')
                            face_img.add_header('Content-Disposition', 'inline', 
                                               filename=f'face_{notification.id}_{i}.jpg')
                            msg.attach(face_img)
                        
                        html += f"""
                        <div style="text-align: center;">
                            <img src="cid:{face_cid}" style="width: 150px; border: 2px solid #ff0000; border-radius: 5px;">
                            <p style="margin: 5px 0; font-size: 12px;">Face #{i+1}</p>
                        </div>
                        """
                
                html += "</div>"
            elif notification.faces_detected:
                html += "<p><em>Faces were detected but images are not available.</em></p>"
            else:
                html += "<p><em>No faces were detected in this incident.</em></p>"
            
            # Complete the HTML email
            html += """
            </body>
            </html>
            """
            
            # Attach the HTML content
            msg.attach(MIMEText(html, 'html'))
            
            # Connect to server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_sender, self.email_password)
                server.send_message(msg)
            
            # Update last email time
            self.last_email_time = time.time()
            print(f"Email notification sent to {', '.join(email_recipients)}")
            return True
            
        except Exception as e:
            print(f"Error sending email notification: {e}")
            return False

class NotificationManager:
    """Manages different notification methods"""
    
    def __init__(self):
        """Initialize notification manager"""
        self.email_notifier = EmailNotifier()
        self.enabled_methods = {
            'email': False,
            'browser': True,
            'sound': True
        }
        self.notification_history = []
        self.max_history = 100
    
    def enable_method(self, method, enabled=True):
        """Enable or disable a notification method"""
        if method in self.enabled_methods:
            self.enabled_methods[method] = enabled
    
    def send_notification(self, incident):
        """
        Send notifications through all enabled methods
        
        Args:
            incident: Dictionary containing incident details
        """
        # Create notification object
        notification = Notification(incident)
        
        # Add to history
        self.notification_history.append(notification)
        if len(self.notification_history) > self.max_history:
            self.notification_history.pop(0)
        
        # Send through enabled methods
        if self.enabled_methods.get('email', False):
            # Run email notification in a separate thread to avoid blocking
            threading.Thread(
                target=self.email_notifier.send_notification,
                args=(notification,)
            ).start()
        
        # Return the notification for use with other notification methods
        return notification
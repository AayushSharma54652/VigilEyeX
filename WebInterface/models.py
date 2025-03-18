from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def __init__(self, username, email, password, first_name=None, last_name=None, is_admin=False):
        self.username = username
        self.email = email
        self.set_password(password)
        self.first_name = first_name
        self.last_name = last_name
        self.is_admin = is_admin
    
    def set_password(self, password):
        """Create hashed password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Camera(db.Model):
    """Camera model for storing camera information."""
    
    __tablename__ = 'cameras'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='inactive')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_active = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Camera {self.name}>'

class Incident(db.Model):
    """Incident model for storing incident information."""
    
    __tablename__ = 'incidents'
    
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(50), unique=True, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    location = db.Column(db.String(100), nullable=False)
    camera_id = db.Column(db.Integer, db.ForeignKey('cameras.id'), nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    faces_detected = db.Column(db.Boolean, default=False)
    confidence_score = db.Column(db.Float, nullable=True)
    reviewed = db.Column(db.Boolean, default=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    camera = db.relationship('Camera', backref=db.backref('incidents', lazy=True))
    reviewer = db.relationship('User', backref=db.backref('reviewed_incidents', lazy=True))
    
    def __repr__(self):
        return f'<Incident {self.external_id}>'

class Face(db.Model):
    """Face model for storing detected faces in incidents."""
    
    __tablename__ = 'faces'
    
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incidents.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    confidence_score = db.Column(db.Float, nullable=True)
    
    # Relationship
    incident = db.relationship('Incident', backref=db.backref('faces', lazy=True))
    
    def __repr__(self):
        return f'<Face {self.id} from Incident {self.incident_id}>'
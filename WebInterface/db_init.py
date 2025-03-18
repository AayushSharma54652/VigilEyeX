#!/usr/bin/env python3
"""
Database initialization script for Violence Detection System.
This script creates the database tables and adds initial data.
"""

import os
import sys
from datetime import datetime
import argparse

# Add parent directory to path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import User, Camera, Incident, Face

def initialize_database(drop_all=False):
    """
    Initialize the database schema and add initial data.
    
    Args:
        drop_all: If True, drop all tables before creating them.
    """
    with app.app_context():
        if drop_all:
            print("Dropping all tables...")
            db.drop_all()
        
        print("Creating database tables...")
        db.create_all()
        
        # Create initial admin user if no users exist
        if User.query.count() == 0:
            admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
            
            print(f"Creating admin user: {admin_username}")
            admin = User(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                is_admin=True
            )
            
            db.session.add(admin)
            db.session.commit()
            print("Admin user created!")
        else:
            print("Admin user already exists, skipping...")
        
        # Create demo cameras if no cameras exist
        if Camera.query.count() == 0 and '--with-demo-data' in sys.argv:
            print("Creating demo cameras...")
            cameras = [
                Camera(name="Main Entrance", url="0", location="Front Door"),
                Camera(name="Parking Area", url="rtsp://demo:demo@ipvmdemo.dyndns.org:5541/onvif-media/media.amp?profile=profile_1&sessiontimeout=60&streamtype=unicast", location="Parking Lot"),
                Camera(name="Hallway", url="1", location="Main Hallway")
            ]
            
            db.session.add_all(cameras)
            db.session.commit()
            print(f"Created {len(cameras)} demo cameras!")
        
        print("Database initialization complete!")

def main():
    parser = argparse.ArgumentParser(description='Initialize database for Violence Detection System')
    parser.add_argument('--drop-all', action='store_true', help='Drop all tables before creating them')
    parser.add_argument('--with-demo-data', action='store_true', help='Add demo data to the database')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Violence Detection System - Database Initialization")
    print("=" * 50)
    
    initialize_database(args.drop_all)
    
    print("=" * 50)

if __name__ == '__main__':
    main()
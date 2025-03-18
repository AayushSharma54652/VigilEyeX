import cv2
import threading
import time

class Camera:
    """Camera access wrapper for handling camera streams."""
    
    def __init__(self, camera_id=0, width=640, height=480):
        """
        Initialize camera.
        
        Args:
            camera_id: Camera identifier (0 for webcam, URL for IP camera)
            width: Desired frame width
            height: Desired frame height
        """
        self.camera_id = camera_id
        self.width = width
        self.height = height
        
        self.video = None
        self.is_running = False
        self.frame = None
        self.last_access = time.time()
        
        # Initialize thread
        self.thread = None
    
    def __del__(self):
        """Release resources when object is deleted."""
        self.stop()
    
    def start(self):
        """Start capturing frames from the camera."""
        if self.is_running:
            print("Camera is already running")
            return
        
        # Open camera
        self.video = cv2.VideoCapture(self.camera_id)
        
        # Set resolution
        self.video.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        if not self.video.isOpened():
            raise RuntimeError(f"Could not open camera {self.camera_id}")
        
        # Start thread
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop capturing frames."""
        self.is_running = False
        
        if self.thread is not None:
            self.thread.join(timeout=1)
            self.thread = None
        
        if self.video is not None:
            self.video.release()
            self.video = None
    
    def _capture_loop(self):
        """Continuously capture frames from the camera."""
        while self.is_running:
            ret, frame = self.video.read()
            if ret:
                self.frame = frame
            time.sleep(0.01)  # Small delay to reduce CPU usage
    
    def get_frame(self):
        """Get the current frame from the camera."""
        self.last_access = time.time()
        
        if self.frame is None:
            # If no frame is available yet, return an empty frame
            return None
        
        return self.frame.copy()
    
    def is_active(self):
        """Check if the camera has been accessed recently."""
        # If the camera hasn't been accessed in 10 minutes, consider it inactive
        return time.time() - self.last_access < 600

class CameraManager:
    """Manage multiple camera streams."""
    
    def __init__(self):
        """Initialize the camera manager."""
        self.cameras = {}
    
    def add_camera(self, camera_id, camera_url=None, width=640, height=480):
        """
        Add a camera to the manager.
        
        Args:
            camera_id: Unique identifier for the camera
            camera_url: URL or device ID of the camera
            width: Desired frame width
            height: Desired frame height
        """
        if camera_id in self.cameras:
            return False
        
        # Use provided URL or default to camera ID as integer (for webcams)
        source = camera_url if camera_url else int(camera_id)
        
        try:
            # Create and start camera
            camera = Camera(source, width, height)
            camera.start()
            
            # Add to dictionary
            self.cameras[camera_id] = camera
            return True
        except Exception as e:
            print(f"Error adding camera {camera_id}: {e}")
            return False
    
    def remove_camera(self, camera_id):
        """Remove a camera from the manager."""
        if camera_id in self.cameras:
            # Stop the camera
            self.cameras[camera_id].stop()
            
            # Remove from dictionary
            del self.cameras[camera_id]
            return True
        
        return False
    
    def get_frame(self, camera_id):
        """Get a frame from the specified camera."""
        if camera_id in self.cameras:
            return self.cameras[camera_id].get_frame()
        
        return None
    
    def cleanup_inactive(self):
        """Remove inactive cameras to free resources."""
        inactive = []
        
        # Find inactive cameras
        for camera_id, camera in self.cameras.items():
            if not camera.is_active():
                inactive.append(camera_id)
        
        # Remove them
        for camera_id in inactive:
            self.remove_camera(camera_id)
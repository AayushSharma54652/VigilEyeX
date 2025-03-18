/**
 * Alert functionality for the Violence Detection System
 */

// Create a socket.io connection
const socket = io();

// Store notification permission status
let notificationPermission = Notification.permission;

// Check for notification permission on page load
document.addEventListener('DOMContentLoaded', function() {
    // Request notification permission if not already granted
    if (notificationPermission !== 'granted') {
        Notification.requestPermission().then(function(permission) {
            notificationPermission = permission;
            console.log('Notification permission:', permission);
        });
    }
    
    // Set up alert sound
    window.alertAudio = new Audio('/static/alert.mp3');
    
    // Listen for incident alerts
    socket.on('incident_alert', handleIncidentAlert);
    
    // Update connection status
    socket.on('connect', function() {
        console.log('Connected to alert system');
        updateConnectionStatus(true);
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from alert system');
        updateConnectionStatus(false);
    });
    
    // Add connection status indicator if element exists
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        updateConnectionStatus(socket.connected);
    }
});

/**
 * Update connection status indicator
 * @param {boolean} connected - Whether socket is connected
 */
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    if (!statusElement) return;
    
    if (connected) {
        statusElement.className = 'status-indicator connected';
        statusElement.setAttribute('title', 'Connected to alert system');
    } else {
        statusElement.className = 'status-indicator disconnected';
        statusElement.setAttribute('title', 'Disconnected from alert system');
    }
}

/**
 * Handle incoming incident alert
 * @param {Object} data - Alert data
 */
function handleIncidentAlert(data) {
    console.log('Received incident alert:', data);
    
    // Play alert sound
    if (window.alertAudio) {
        window.alertAudio.play().catch(e => console.error('Error playing alert sound:', e));
    }
    
    // Show browser notification if permission granted
    if (notificationPermission === 'granted') {
        // Prepare notification options
        const notificationOptions = {
            body: `Location: ${data.location}\nTime: ${data.timestamp}`,
            icon: '/static/favicon.ico',
            requireInteraction: true
        };
        
        // Add incident image if available
        if (data.image_url) {
            notificationOptions.image = data.image_url;
        }
        
        // Add face information if available
        if (data.faces_detected) {
            notificationOptions.body += `\n${data.face_urls ? data.face_urls.length : ''} Faces detected`;
        }
        
        // Create and display the notification
        const notification = new Notification('VIOLENCE ALERT!', notificationOptions);
        
        notification.onclick = function() {
            window.open('/incidents', '_blank');
            notification.close();
        };
    }
    
    // Update UI if we're on the camera page
    updateCameraPageUI(data);
}

/**
 * Update camera page UI with alert info
 * @param {Object} data - Alert data
 */
function updateCameraPageUI(data) {
    // Update status indicator if on camera page
    const detectionStatus = document.getElementById('detection-status');
    if (detectionStatus) {
        detectionStatus.className = 'detection-status status-danger';
        detectionStatus.textContent = 'ALERT - Violence Detected!';
        
        // Flash the background
        document.body.classList.add('alert-flash');
        setTimeout(() => {
            document.body.classList.remove('alert-flash');
        }, 1000);
    }
    
    // Update alert counter if present
    const alertCounter = document.getElementById('alert-counter');
    if (alertCounter) {
        const currentCount = parseInt(alertCounter.textContent) || 0;
        alertCounter.textContent = currentCount + 1;
    }
    
    // Show alert banner if not already visible
    showAlertBanner(data);
}

/**
 * Show alert banner on the page
 * @param {Object} data - Alert data
 */
function showAlertBanner(data) {
    // Check if banner already exists
    let banner = document.getElementById('alert-banner');
    
    // Create banner if it doesn't exist
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'alert-banner';
        banner.className = 'alert-banner';
        
        // Create close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'alert-banner-close';
        closeBtn.innerHTML = '&times;';
        closeBtn.onclick = function() {
            document.body.removeChild(banner);
        };
        
        // Create content container
        const content = document.createElement('div');
        content.className = 'alert-banner-content';
        
        // Add elements to banner
        banner.appendChild(closeBtn);
        banner.appendChild(content);
        
        // Add banner to page
        document.body.appendChild(banner);
    }
    
    // Update banner content
    const content = banner.querySelector('.alert-banner-content');
    
    // Build face thumbnail HTML if faces are detected
    let facesHtml = '';
    if (data.faces_detected && data.face_urls && data.face_urls.length > 0) {
        facesHtml = `
            <div class="face-thumbnails">
                <p><strong>Faces Detected:</strong></p>
                <div class="face-grid">
        `;
        
        // Add up to 4 face thumbnails
        const maxFaces = Math.min(4, data.face_urls.length);
        for (let i = 0; i < maxFaces; i++) {
            facesHtml += `<img src="${data.face_urls[i]}" class="face-thumbnail" alt="Detected Face ${i+1}">`;
        }
        
        // Show count if more faces are available
        if (data.face_urls.length > 4) {
            facesHtml += `<div class="more-faces">+${data.face_urls.length - 4}</div>`;
        }
        
        facesHtml += `
                </div>
            </div>
        `;
    }
    
    content.innerHTML = `
        <h3>⚠️ VIOLENCE ALERT!</h3>
        <p><strong>Location:</strong> ${data.location}</p>
        <p><strong>Time:</strong> ${data.timestamp}</p>
        ${facesHtml}
        <a href="/incidents" class="alert-banner-link">View Incident</a>
    `;
    
    // Animate banner entrance
    setTimeout(() => {
        banner.classList.add('visible');
    }, 100);
}
/**
 * Main JavaScript for the Violence Detection System
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Camera status update simulation (for demonstration)
    simulateCameraStatuses();
    
    // Add event listeners for fullscreen view
    const fullscreenButtons = document.querySelectorAll('.btn-fullscreen');
    fullscreenButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const cameraId = this.getAttribute('data-camera-id');
            toggleFullscreen(cameraId);
        });
    });
});

/**
 * Simulate changing camera statuses for demo purposes
 */
function simulateCameraStatuses() {
    const statuses = document.querySelectorAll('.camera-status');
    
    if (statuses.length > 0) {
        // Every 10 seconds, randomly update a camera status
        setInterval(() => {
            const randomIndex = Math.floor(Math.random() * statuses.length);
            const randomStatus = statuses[randomIndex];
            
            // Reset all classes first
            randomStatus.classList.remove('status-active', 'status-inactive', 'status-alert');
            
            // Randomly assign a new status
            const randomValue = Math.random();
            if (randomValue < 0.7) {
                // 70% chance of active
                randomStatus.classList.add('status-active');
                randomStatus.parentElement.textContent = ' Active';
            } else if (randomValue < 0.9) {
                // 20% chance of inactive
                randomStatus.classList.add('status-inactive');
                randomStatus.parentElement.textContent = ' Inactive';
            } else {
                // 10% chance of alert
                randomStatus.classList.add('status-alert');
                randomStatus.parentElement.textContent = ' ALERT!';
            }
            
            // Prepend the status indicator span
            randomStatus.parentElement.prepend(randomStatus);
        }, 10000);
    }
}

/**
 * Toggle fullscreen view for a camera
 * @param {string} cameraId - ID of the camera to view fullscreen
 */
function toggleFullscreen(cameraId) {
    const modal = document.createElement('div');
    modal.classList.add('modal', 'fade');
    modal.setAttribute('tabindex', '-1');
    modal.id = `fullscreen-${cameraId}`;
    
    modal.innerHTML = `
        <div class="modal-dialog modal-fullscreen">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Camera Feed (Fullscreen)</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body p-0 d-flex align-items-center justify-content-center bg-dark">
                    <img src="/video_feed?camera_id=${cameraId}" class="img-fluid" style="max-height: 100vh; max-width: 100%;">
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
    
    modal.addEventListener('hidden.bs.modal', function() {
        document.body.removeChild(modal);
    });
}

/**
 * Filter incidents on the incidents page
 */
function filterIncidents() {
    const statusFilters = {
        new: document.getElementById('status-new')?.checked,
        reviewed: document.getElementById('status-reviewed')?.checked,
        archived: document.getElementById('status-archived')?.checked
    };
    
    const locationFilter = document.querySelector('select[name="location"]')?.value;
    const fromDate = document.querySelector('input[type="date"][name="from"]')?.value;
    const toDate = document.querySelector('input[type="date"][name="to"]')?.value;
    
    // Get all incident rows
    const rows = document.querySelectorAll('.incident-table tbody tr');
    
    rows.forEach(row => {
        let visible = true;
        
        // Filter by status
        const statusBadge = row.querySelector('.badge');
        if (statusBadge) {
            const status = statusBadge.textContent.toLowerCase();
            if ((status.includes('new') && !statusFilters.new) ||
                (status.includes('reviewed') && !statusFilters.reviewed) ||
                (status.includes('archived') && !statusFilters.archived)) {
                visible = false;
            }
        }
        
        // Filter by location
        if (locationFilter && locationFilter !== '') {
            const location = row.querySelector('td:nth-child(3)').textContent;
            if (location !== locationFilter) {
                visible = false;
            }
        }
        
        // Filter by date range (if implemented)
        if (fromDate || toDate) {
            const timestamp = row.querySelector('td:nth-child(2)').textContent;
            const incidentDate = new Date(timestamp);
            
            if (fromDate && new Date(fromDate) > incidentDate) {
                visible = false;
            }
            
            if (toDate && new Date(toDate) < incidentDate) {
                visible = false;
            }
        }
        
        // Show or hide row
        row.style.display = visible ? '' : 'none';
    });
}
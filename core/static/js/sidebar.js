document.addEventListener("DOMContentLoaded", function() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const toggleBtn = document.getElementById('sidebarToggle');
    const closeBtn = document.getElementById('closeSidebar');

    // Open Sidebar
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.add('show');
            overlay.classList.add('show');
        });
    }

    // Close Sidebar (Button)
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            sidebar.classList.remove('show');
            overlay.classList.remove('show');
        });
    }

    // Close Sidebar (Clicking outside on overlay)
    if (overlay) {
        overlay.addEventListener('click', function() {
            sidebar.classList.remove('show');
            overlay.classList.remove('show');
        });
    }
});
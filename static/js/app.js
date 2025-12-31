/**
 * Ink - E-Paper Display Controller
 * Pure Vanilla JS, No Dependencies
 */

const STATE = {
    image: null,
    file: null,
    scale: 1.0,
    x: 0,
    y: 0,
    rotation: 0,
    isDragging: false,
    lastX: 0,
    lastY: 0,
    pointers: new Map(), // Track active pointers for multi-touch
    lastPinchDist: 0,
    canvas: null,
    ctx: null,
    width: 250,
    height: 122
};

document.addEventListener('DOMContentLoaded', () => {
    initCanvas();
    initUpload();
    loadStatus();
    loadDashboardSettings();
});

/* --- View Management --- */
function switchView(viewId) {
    // Buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        if (btn.innerText.toLowerCase().includes(viewId)) btn.classList.add('active');
        else btn.classList.remove('active');
    });

    // Views
    document.querySelectorAll('.view-section').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById('view-' + viewId).classList.add('active');

    if (viewId === 'gallery') loadGallery();
}

/* --- Canvas / Editor Logic --- */
function initCanvas() {
    STATE.canvas = document.getElementById('editorCanvas');
    STATE.ctx = STATE.canvas.getContext('2d', { alpha: false });

    // Set canvas internal resolution
    STATE.canvas.width = STATE.width; // 250
    STATE.canvas.height = STATE.height; // 122

    // Fill black initially
    STATE.ctx.fillStyle = '#1a1a1a';
    STATE.ctx.fillRect(0, 0, STATE.width, STATE.height);

    // Event Listeners
    const c = STATE.canvas;

    // Pointer Events (Mouse + Touch)
    c.addEventListener('pointerdown', handlePointerDown);
    c.addEventListener('pointermove', handlePointerMove);
    c.addEventListener('pointerup', handlePointerUp);
    c.addEventListener('pointercancel', handlePointerUp);
    c.addEventListener('wheel', handleWheel, { passive: false });

    // Prevent default touch actions (scrolling) on canvas
    c.style.touchAction = 'none';
}

function initUpload() {
    const dropZone = document.getElementById('uploadPrompt');
    const input = document.getElementById('fileInput');

    dropZone.addEventListener('click', () => input.click());

    input.addEventListener('change', (e) => {
        if (e.target.files.length) handleFile(e.target.files[0]);
    });

    // Drag & Drop
    document.body.addEventListener('dragover', (e) => e.preventDefault());
    document.body.addEventListener('drop', (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });
}

function handleFile(file) {
    if (!file.type.startsWith('image/')) return showStatus('Not an image', 'error');

    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            STATE.image = img;
            STATE.file = file;
            resetView();
            document.getElementById('uploadPrompt').classList.add('hidden');
            switchView('editor');
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function resetView() {
    if (!STATE.image) return;

    // Fit image to cover
    const scaleX = STATE.width / STATE.image.width;
    const scaleY = STATE.height / STATE.image.height;
    STATE.scale = Math.max(scaleX, scaleY); // Cover

    STATE.x = 0;
    STATE.y = 0;
    STATE.rotation = 0;

    render();
}

function render() {
    if (!STATE.ctx) return;
    const ctx = STATE.ctx;

    // Clear background
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, STATE.width, STATE.height);

    if (!STATE.image) return;

    ctx.save();

    // 1. Translate to center, 2. Pan, 3. Rotate, 4. Zoom
    ctx.translate(STATE.width / 2, STATE.height / 2);
    ctx.translate(STATE.x, STATE.y);
    ctx.rotate(STATE.rotation * Math.PI / 180);
    ctx.scale(STATE.scale, STATE.scale);

    // 5. Draw Image Centered
    ctx.drawImage(
        STATE.image,
        -STATE.image.width / 2,
        -STATE.image.height / 2
    );

    ctx.restore();
}

/* Interactions */
function handlePointerDown(e) {
    STATE.canvas.setPointerCapture(e.pointerId);
    STATE.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    STATE.isDragging = true;

    if (STATE.pointers.size === 2) {
        STATE.lastPinchDist = getPinchDist();
    }
}

function handlePointerMove(e) {
    if (!STATE.isDragging) return;
    const ptr = STATE.pointers.get(e.pointerId);
    if (!ptr) return;

    if (STATE.pointers.size === 1) {
        // Pan
        const dx = e.clientX - ptr.x;
        const dy = e.clientY - ptr.y;

        STATE.x += dx;
        STATE.y += dy;

        STATE.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
        render();
    } else if (STATE.pointers.size === 2) {
        // Pinch
        STATE.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
        const newDist = getPinchDist();
        const delta = newDist - STATE.lastPinchDist;

        // Zoom sensitivity
        STATE.scale *= (1 + delta * 0.005);
        STATE.lastPinchDist = newDist;
        render();
    }
}

function handlePointerUp(e) {
    STATE.pointers.delete(e.pointerId);
    STATE.canvas.releasePointerCapture(e.pointerId);
    if (STATE.pointers.size === 0) {
        STATE.isDragging = false;
    }
}

function handleWheel(e) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    STATE.scale *= delta;
    render();
}

function getPinchDist() {
    const points = Array.from(STATE.pointers.values());
    const dx = points[0].x - points[1].x;
    const dy = points[0].y - points[1].y;
    return Math.sqrt(dx * dx + dy * dy);
}

/* Actions */
function rotate90() {
    STATE.rotation = (STATE.rotation + 90) % 360;
    render();
}

function clearDisplay() {
    fetch('/clear', { method: 'POST' })
        .then(() => showStatus('Display Cleared', 'success'));
}

async function uploadImage() {
    if (!STATE.image || !STATE.file) return showStatus('No image loaded', 'error');

    const btn = document.getElementById('btnUpload');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Sending...';
    btn.disabled = true;

    try {
        const formData = new FormData();
        formData.append('image', STATE.file);
        formData.append('scale', STATE.scale);
        formData.append('offset_x', STATE.x);
        formData.append('offset_y', STATE.y);
        formData.append('rotation', STATE.rotation);

        const res = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            showStatus('Updated Successfully', 'success');
        } else {
            showStatus('Failed: ' + data.error, 'error');
        }
    } catch (e) {
        showStatus('Error: ' + e.message, 'error');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

/* --- Gallery Logic --- */
function loadGallery() {
    const grid = document.getElementById('galleryGrid');
    grid.innerHTML = '<div class="empty-state">Loading...</div>';

    fetch('/gallery')
        .then(r => r.json())
        .then(data => {
            if (!data.success || !data.images?.length) {
                grid.innerHTML = '<div class="empty-state">No images found</div>';
                return;
            }

            grid.innerHTML = '';
            data.images.forEach(img => {
                const item = document.createElement('div');
                item.className = 'gallery-item';
                item.onclick = () => loadGalleryImage(img.name);
                item.innerHTML = `
                    <img class="gallery-thumb" src="/gallery/image/${img.name}" loading="lazy">
                    <div class="gallery-info">
                        <span class="gallery-name">${img.name}</span>
                        <div class="gallery-delete" onclick="event.stopPropagation(); deleteImage('${img.name}')">🗑️</div>
                    </div>
                `;
                grid.appendChild(item);
            });
        });
}

function loadGalleryImage(filename) {
    showStatus('Loading image...', 'info');
    fetch(`/gallery/image/${filename}`)
        .then(res => res.blob())
        .then(blob => {
            const file = new File([blob], filename, { type: blob.type });
            handleFile(file);
        });
}

function uploadToGallery(input) {
    if (!input.files.length) return;
    const formData = new FormData();
    formData.append('image', input.files[0]);

    fetch('/gallery/upload', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(d => {
            if (d.success) loadGallery();
            else showStatus('Upload failed: ' + d.error, 'error');
        });
    input.value = '';
}

function deleteImage(filename) {
    if (!confirm('Delete this image?')) return;
    fetch(`/gallery/delete/${filename}`, { method: 'POST' })
        .then(r => r.json())
        .then(d => {
            if (d.success) loadGallery();
        });
}

/* --- Dashboard Logic --- */
function loadDashboardSettings() {
    fetch('/settings')
        .then(r => r.json())
        .then(s => {
            if (s.city) document.getElementById('dashCity').value = s.city;

            // Handle Unit Radio Buttons
            if (s.units) {
                document.getElementById('dashUnits').value = s.units;
                if (s.units === 'c') document.getElementById('unitC').checked = true;
                if (s.units === 'f') document.getElementById('unitF').checked = true;
            }

            if (s.rotation !== undefined) document.getElementById('dashRotation').value = s.rotation;

            document.getElementById('dashFlipH').checked = !!s.flip_h;
            document.getElementById('dashFlipV').checked = !!s.flip_v;

            document.getElementById('dashHum').checked = !!s.show_humidity;
            document.getElementById('dashWind').checked = !!s.show_wind;
            document.getElementById('dashSun').checked = !!s.show_sun;
        });
}

function updateDashboard() {
    const payload = {
        mode: 'dashboard',
        city: document.getElementById('dashCity').value,
        units: document.getElementById('dashUnits').value,
        rotation: parseInt(document.getElementById('dashRotation').value),
        flip_h: document.getElementById('dashFlipH').checked,
        flip_v: document.getElementById('dashFlipV').checked,
        show_humidity: document.getElementById('dashHum').checked,
        show_wind: document.getElementById('dashWind').checked,
        show_sun: document.getElementById('dashSun').checked
    };

    showStatus('Rendering Dashboard...', 'info');

    // Save settings first
    fetch('/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(() => fetch('/render_dashboard', { method: 'POST' }))
        .then(r => r.json())
        .then(d => {
            if (d.success) showStatus('Dashboard Updated', 'success');
            else showStatus('Render Failed: ' + d.error, 'error');
        });
}

function setUnit(val) {
    document.getElementById('dashUnits').value = val;
}

/* --- System Logic --- */
function renderSystem() {
    showStatus('Scanning System...', 'info');
    fetch('/render_system', { method: 'POST' })
        .then(r => r.json())
        .then(d => {
            if (d.success) showStatus('System Stats Displayed', 'success');
            else showStatus('Error: ' + d.error, 'error');
        });
}

/* --- Message Logic --- */
let currentMsgSize = 'medium';

function setMsgSize(size) {
    currentMsgSize = size;
}

function renderMessage() {
    const text = document.getElementById('msgText').value;
    if (!text) return showStatus('Enter a message first', 'error');

    showStatus('Sending Message...', 'info');
    fetch('/render_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: text,
            font_size: currentMsgSize
        })
    })
        .then(r => r.json())
        .then(d => {
            if (d.success) showStatus('Message Sent', 'success');
            else showStatus('Error: ' + d.error, 'error');
        });
}

/* Helpers */
function showStatus(msg, type = 'info') {
    const el = document.getElementById('statusBar');
    el.textContent = msg;
    el.style.color = type === 'error' ? '#ef4444' : '#a78bfa';
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 3000);
}

function loadStatus() {
    fetch('/settings').then(() => showStatus('Connected')).catch(() => showStatus('Offline', 'error'));
}

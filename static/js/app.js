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
    brightness: 1.0,
    contrast: 1.0,
    isDragging: false,
    lastX: 0,
    lastY: 0,
    lastDist: 0,
    pointers: new Map(), // Track active pointers for multi-touch
    canvas: null,
    ctx: null,
    width: 250,
    height: 122
};

document.addEventListener('DOMContentLoaded', () => {
    initCanvas();
    initUpload();
    initControls();
    loadStatus();
});

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

function initControls() {
    // Buttons will be bound in HTML by onclick, or we can bind here
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

/* Rendering Loop */
function render() {
    if (!STATE.ctx) return;
    const ctx = STATE.ctx;

    // Clear background
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, STATE.width, STATE.height);

    if (!STATE.image) return;

    ctx.save();

    // 1. Translate to center of canvas
    ctx.translate(STATE.width / 2, STATE.height / 2);

    // 2. Apply User Offset (Pan)
    ctx.translate(STATE.x, STATE.y);

    // 3. Apply Rotation (Content Rotation)
    ctx.rotate(STATE.rotation * Math.PI / 180);

    // 4. Apply Scale (Zoom)
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
        // Start Pinch
        STATE.lastDist = getPinchDist();
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

        // Adjust for rotation? No, user drags screen.
        // If I drag right on screen, image moves right on screen.
        STATE.x += dx; // Screen space translation
        STATE.y += dy;

        STATE.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
        render();
    } else if (STATE.pointers.size === 2) {
        // Pinch
        STATE.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
        const newDist = getPinchDist();
        const delta = newDist - STATE.lastDist;

        // Zoom
        STATE.scale *= (1 + delta * 0.005);
        STATE.lastDist = newDist;
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
    if (!STATE.image || !STATE.file) return showStatus('No image selected', 'error');

    const btn = document.getElementById('btnUpload');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Sending...';
    btn.disabled = true;

    try {
        const formData = new FormData();
        formData.append('image', STATE.file);

        // Pass Transform Parameters
        // Note: The Backend needs to replicate the Canvas render logic
        formData.append('scale', STATE.scale);
        formData.append('offset_x', STATE.x);
        formData.append('offset_y', STATE.y);
        formData.append('rotation', STATE.rotation); // Content rotation

        // Use legacy crop params to bypass validation or set defaults
        formData.append('crop_x', 0);
        formData.append('crop_y', 0);
        formData.append('crop_w', STATE.width);
        formData.append('crop_h', STATE.height);

        const res = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await res.json();
        if (data.success) {
            showStatus('Updated Successfully', 'success');
        } else {
            showStatus('Update Failed: ' + data.error, 'error');
        }
    } catch (e) {
        showStatus('Error: ' + e.message, 'error');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

/* UI Helpers */
function showStatus(msg, type = 'info') {
    const el = document.getElementById('statusBar');
    el.textContent = msg;
    el.style.color = type === 'error' ? '#ef4444' : '#a78bfa';
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 3000);
}

function loadStatus() {
    fetch('/settings').then(r => r.json()).then(() => {
        showStatus('Connected');
    }).catch(() => {
        showStatus('Offline', 'error');
    });
}

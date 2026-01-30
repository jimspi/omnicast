// OmniCast - Multi-Format News Distribution Platform
// Frontend Application

// State management
const state = {
    interviewVideoId: null,
    brollVideoId: null,
    currentJobId: null,
    pollInterval: null
};

// DOM Elements
const elements = {
    notes: document.getElementById('notes'),
    interviewFile: document.getElementById('interview-file'),
    brollFile: document.getElementById('broll-file'),
    interviewInfo: document.getElementById('interview-info'),
    brollInfo: document.getElementById('broll-info'),
    interviewUpload: document.getElementById('interview-upload'),
    brollUpload: document.getElementById('broll-upload'),
    processBtn: document.getElementById('process-btn'),
    progressSection: document.getElementById('progress-section'),
    progressPercent: document.getElementById('progress-percent'),
    progressFill: document.getElementById('progress-fill'),
    progressStatus: document.getElementById('progress-status'),
    resultsSection: document.getElementById('results-section'),
    tabContent: document.getElementById('tab-content')
};

// Initialize event listeners
document.addEventListener('DOMContentLoaded', () => {
    initializeFileUploads();
    initializeTabs();
    checkHealth();
});

// Health check
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        if (!data.openai_configured) {
            showNotification('Warning: OpenAI API key not configured. Set OPENAI_API_KEY environment variable.', 'warning');
        }
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

// File upload handlers
function initializeFileUploads() {
    elements.interviewFile.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            await uploadFile(file, 'video', 'interview');
        }
    });

    elements.brollFile.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            await uploadFile(file, 'video', 'broll');
        }
    });

    // Drag and drop support
    ['interview-upload', 'broll-upload'].forEach(id => {
        const card = document.getElementById(id);

        card.addEventListener('dragover', (e) => {
            e.preventDefault();
            card.classList.add('drag-over');
        });

        card.addEventListener('dragleave', () => {
            card.classList.remove('drag-over');
        });

        card.addEventListener('drop', async (e) => {
            e.preventDefault();
            card.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('video/')) {
                const type = id === 'interview-upload' ? 'interview' : 'broll';
                await uploadFile(file, 'video', type);
            }
        });
    });
}

// Upload file to server
async function uploadFile(file, fileType, uploadType) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', fileType);

    const infoElement = uploadType === 'interview' ? elements.interviewInfo : elements.brollInfo;
    const cardElement = uploadType === 'interview' ? elements.interviewUpload : elements.brollUpload;

    infoElement.innerHTML = '<span class="processing">Uploading...</span>';

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const data = await response.json();

        if (uploadType === 'interview') {
            state.interviewVideoId = data.file_id;
        } else {
            state.brollVideoId = data.file_id;
        }

        const sizeMB = (data.size / (1024 * 1024)).toFixed(2);
        infoElement.innerHTML = `<strong>${file.name}</strong><br>Size: ${sizeMB} MB`;
        cardElement.classList.add('has-file');

    } catch (error) {
        infoElement.innerHTML = `<span style="color: var(--danger);">Error: ${error.message}</span>`;
        console.error('Upload error:', error);
    }
}

// Tab navigation
function initializeTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;

            // Update active tab button
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update active pane
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('active');
            });
            document.getElementById(`${tab}-pane`).classList.add('active');
        });
    });
}

// Process story
async function processStory() {
    const notes = elements.notes.value.trim();

    // Validate input
    if (!notes && !state.interviewVideoId && !state.brollVideoId) {
        showNotification('Please provide at least some notes or upload a video.', 'error');
        return;
    }

    // Get selected formats
    const formatCheckboxes = document.querySelectorAll('input[name="format"]:checked');
    const formats = Array.from(formatCheckboxes).map(cb => cb.value).join(',');

    if (!formats) {
        showNotification('Please select at least one output format.', 'error');
        return;
    }

    // Disable button and show progress
    elements.processBtn.disabled = true;
    elements.processBtn.innerHTML = '<div class="spinner"></div> Processing...';
    elements.progressSection.style.display = 'block';
    elements.resultsSection.style.display = 'none';

    try {
        // Submit processing request
        const formData = new FormData();
        formData.append('notes', notes);
        formData.append('output_formats', formats);

        if (state.interviewVideoId) {
            formData.append('interview_video_id', state.interviewVideoId);
        }
        if (state.brollVideoId) {
            formData.append('broll_video_id', state.brollVideoId);
        }

        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Processing failed');
        }

        const data = await response.json();
        state.currentJobId = data.job_id;

        // Start polling for job status
        startPolling();

    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
        resetProcessButton();
    }
}

// Poll for job status
function startPolling() {
    state.pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/job/${state.currentJobId}`);
            const job = await response.json();

            updateProgress(job);

            if (job.status === 'completed' || job.status === 'failed') {
                clearInterval(state.pollInterval);

                if (job.status === 'completed') {
                    displayResults(job);
                } else {
                    showNotification('Processing failed: ' + (job.errors?.join(', ') || 'Unknown error'), 'error');
                }

                resetProcessButton();
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 1000);
}

// Update progress display
function updateProgress(job) {
    elements.progressPercent.textContent = `${job.progress}%`;
    elements.progressFill.style.width = `${job.progress}%`;
    elements.progressStatus.textContent = job.status;
}

// Display results
function displayResults(job) {
    elements.progressSection.style.display = 'none';
    elements.resultsSection.style.display = 'block';

    // Display each format's results
    if (job.outputs.tv) {
        displayTVResults(job.outputs.tv);
    }
    if (job.outputs.web) {
        displayWebResults(job.outputs.web);
    }
    if (job.outputs.social) {
        displaySocialResults(job.outputs.social);
    }
    if (job.outputs.youtube) {
        displayYouTubeResults(job.outputs.youtube);
    }
    if (job.outputs.podcast) {
        displayPodcastResults(job.outputs.podcast);
    }

    // Show first available tab
    const firstFormat = Object.keys(job.outputs)[0];
    if (firstFormat) {
        document.querySelector(`.tab-btn[data-tab="${firstFormat}"]`).click();
    }
}

// Display TV results
function displayTVResults(data) {
    const content = data.script || {};
    const container = document.getElementById('tv-content');

    container.innerHTML = `
        <div class="script-section">
            <h4>Anchor Intro</h4>
            <pre>${escapeHtml(content.anchor_intro || 'N/A')}</pre>
        </div>
        <div class="script-section">
            <h4>VO/SOT Script</h4>
            <pre>${escapeHtml(content.vo_sot_script || 'N/A')}</pre>
        </div>
        <div class="script-section">
            <h4>Package Script</h4>
            <pre>${escapeHtml(content.package_script || 'N/A')}</pre>
        </div>
        <div class="script-section">
            <h4>Anchor Tag</h4>
            <pre>${escapeHtml(content.anchor_tag || 'N/A')}</pre>
        </div>
        <div class="script-section">
            <h4>Total Runtime</h4>
            <pre>${escapeHtml(content.total_runtime || 'N/A')}</pre>
        </div>
    `;

    displayDownloadLinks('tv-downloads', data.files);
}

// Display Web results
function displayWebResults(data) {
    const content = data.content || {};
    const container = document.getElementById('web-content');

    container.innerHTML = `
        <div class="headline">${escapeHtml(content.headline || 'Article')}</div>
        <div class="meta-description">${escapeHtml(content.meta_description || '')}</div>
        <div class="lead">${escapeHtml(content.lead || '')}</div>
        <div class="body">${content.body_html || content.full_article_html || ''}</div>
        <div class="tags">
            ${(content.tags || []).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
        </div>
    `;

    displayDownloadLinks('web-downloads', data.files);
}

// Display Social Media results
function displaySocialResults(data) {
    const content = data.content || {};
    const container = document.getElementById('social-content');

    const videoUrl = data.files?.video;

    container.innerHTML = `
        <div class="phone-frame">
            <div class="phone-screen">
                <div class="video-placeholder">
                    ${videoUrl ?
                        `<video controls src="${videoUrl}"></video>` :
                        '<span style="color: var(--text-muted);">Video Preview</span>'
                    }
                </div>
                <div class="headline-overlay">${escapeHtml(content.headline_overlay || '')}</div>
            </div>
        </div>
        <div class="caption">
            <strong>Caption:</strong>
            <p>${escapeHtml(content.caption || '')}</p>
            <div class="hashtags">${(content.hashtags || []).map(h => `#${h}`).join(' ')}</div>
        </div>
        <div class="script-section" style="margin-top: 20px;">
            <h4>Video Script</h4>
            <pre>${escapeHtml(content.video_script || '')}</pre>
        </div>
        <div class="script-section">
            <h4>Subtitle Segments</h4>
            <pre>${JSON.stringify(content.subtitle_segments || [], null, 2)}</pre>
        </div>
    `;

    displayDownloadLinks('social-downloads', data.files);
}

// Display YouTube results
function displayYouTubeResults(data) {
    const content = data.content || {};
    const container = document.getElementById('youtube-content');

    const videoUrl = data.files?.video;
    const thumbnailUrl = data.files?.thumbnail;

    container.innerHTML = `
        <div class="video-frame">
            ${videoUrl ?
                `<video controls src="${videoUrl}"></video>` :
                (thumbnailUrl ?
                    `<img class="thumbnail-preview" src="${thumbnailUrl}" alt="Thumbnail">` :
                    '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);">Video Preview</div>'
                )
            }
        </div>
        <div class="video-title">${escapeHtml(content.title || '')}</div>
        <div class="video-description">
            <strong>Description:</strong>
            <pre style="white-space: pre-wrap; margin-top: 8px;">${escapeHtml(content.description || '')}</pre>
        </div>
        <div class="timestamps">
            <h4>Timestamps</h4>
            ${(content.timestamps || []).map(ts => `
                <div class="timestamp-item">
                    <span class="timestamp-time">${ts.time || ''}</span>
                    <span>${escapeHtml(ts.label || '')}</span>
                </div>
            `).join('')}
        </div>
        <div class="script-section" style="margin-top: 20px;">
            <h4>Full Script</h4>
            <pre>${escapeHtml(content.full_script || '')}</pre>
        </div>
        <div class="script-section">
            <h4>Tags</h4>
            <pre>${(content.tags || []).join(', ')}</pre>
        </div>
    `;

    displayDownloadLinks('youtube-downloads', data.files);
}

// Display Podcast results
function displayPodcastResults(data) {
    const content = data.content || {};
    const container = document.getElementById('podcast-content');

    const audioUrl = data.files?.audio;

    container.innerHTML = `
        <div class="audio-player">
            <div class="episode-title">${escapeHtml(content.episode_title || 'Podcast Episode')}</div>
            <div class="episode-description">${escapeHtml(content.episode_description || '')}</div>
            ${audioUrl ? `<audio controls src="${audioUrl}"></audio>` : '<p style="margin-top:16px;color:var(--text-muted);">Audio generation pending...</p>'}
        </div>
        <div class="show-notes">
            <h4>Show Notes</h4>
            <pre style="white-space: pre-wrap;">${escapeHtml(content.show_notes || '')}</pre>
        </div>
        <div class="transcript">
            <h4>Transcript</h4>
            <pre style="white-space: pre-wrap;">${escapeHtml(content.transcript || content.full_script || '')}</pre>
        </div>
        <div class="script-section" style="margin-top: 20px;">
            <h4>Full Script</h4>
            <pre>${escapeHtml(content.full_script || '')}</pre>
        </div>
    `;

    displayDownloadLinks('podcast-downloads', data.files);
}

// Display download links
function displayDownloadLinks(containerId, files) {
    const container = document.getElementById(containerId);
    if (!files) {
        container.innerHTML = '';
        return;
    }

    const downloadIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
    </svg>`;

    const links = Object.entries(files).map(([key, url]) => {
        const label = formatLabel(key);
        return `<a href="${url}" class="download-btn" download>${downloadIcon} ${label}</a>`;
    }).join('');

    container.innerHTML = links;
}

// Format label for display
function formatLabel(key) {
    const labels = {
        json: 'JSON Data',
        text: 'Text Script',
        html: 'HTML Article',
        video: 'Video File',
        audio: 'Audio File',
        subtitles: 'Subtitles (SRT)',
        thumbnail: 'Thumbnail',
        description: 'Description',
        script: 'Script',
        show_notes: 'Show Notes',
        transcript: 'Transcript'
    };
    return labels[key] || key.charAt(0).toUpperCase() + key.slice(1);
}

// Reset process button
function resetProcessButton() {
    elements.processBtn.disabled = false;
    elements.processBtn.innerHTML = `
        <span class="btn-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
        </span>
        Generate All Formats
    `;
}

// Show notification
function showNotification(message, type = 'info') {
    // Remove existing notification
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'error' ? 'var(--danger)' : type === 'warning' ? 'var(--accent)' : 'var(--primary)'};
        color: white;
        border-radius: 8px;
        box-shadow: var(--shadow-lg);
        z-index: 1000;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Add slideOut animation
const styleSheet = document.createElement('style');
styleSheet.textContent = `
    @keyframes slideOut {
        from { opacity: 1; transform: translateX(0); }
        to { opacity: 0; transform: translateX(100px); }
    }

    .drag-over {
        border-color: var(--primary) !important;
        background: rgba(99, 102, 241, 0.1) !important;
    }
`;
document.head.appendChild(styleSheet);

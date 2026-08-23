/**
 * Jarvis-Lite 3D Interactive Interface
 * Handles Three.js scene, chat, voice I/O, and API integration
 */

// ============ GLOBAL STATE ============
const AppState = {
    isRecording: false,
    isSpeaking: false,
    messageCount: 0,
    lastTool: '-',
    confidence: 0,
    settings: {
        memoryType: 'buffer',
        voiceBackend: 'gtts',
        language: 'en',
        autoPlayAudio: true
    },
    apiBaseUrl: 'http://localhost:8000', // Change for deployment
    mediaRecorder: null,
    audioChunks: [],
};

// ============ THREE.JS SCENE SETUP ============
let scene, camera, renderer;

function initThreeJS() {
    const canvas = document.getElementById('canvas3d');
    
    // Scene setup
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0e27);
    scene.fog = new THREE.Fog(0x0a0e27, 100, 1000);
    
    // Camera setup
    camera = new THREE.PerspectiveCamera(
        75,
        window.innerWidth / window.innerHeight,
        0.1,
        1000
    );
    camera.position.z = 30;
    
    // Renderer setup
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    
    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);
    
    const pointLight = new THREE.PointLight(0x00d9ff, 1.5);
    pointLight.position.set(20, 20, 20);
    pointLight.castShadow = true;
    scene.add(pointLight);
    
    const pointLight2 = new THREE.PointLight(0x00ff41, 1);
    pointLight2.position.set(-20, -20, 10);
    scene.add(pointLight2);
    
    // Create animated background objects
    createBackgroundObjects();
    
    // Handle window resize
    window.addEventListener('resize', onWindowResize);
    
    // Start animation loop
    animate();
}

function createBackgroundObjects() {
    // Create rotating torus knots for visual effect
    const geometry1 = new THREE.TorusKnotGeometry(8, 2, 100, 16);
    const material1 = new THREE.MeshStandardMaterial({
        color: 0x00d9ff,
        emissive: 0x00d9ff,
        emissiveIntensity: 0.3,
        wireframe: false,
        transparent: true,
        opacity: 0.2
    });
    const torusKnot1 = new THREE.Mesh(geometry1, material1);
    torusKnot1.position.z = -10;
    scene.add(torusKnot1);
    
    // Store for animation
    scene.userData.torusKnot1 = torusKnot1;
    
    // Create second rotating object
    const geometry2 = new THREE.IcosahedronGeometry(6, 4);
    const material2 = new THREE.MeshStandardMaterial({
        color: 0x00ff41,
        emissive: 0x00ff41,
        emissiveIntensity: 0.2,
        wireframe: true,
        transparent: true,
        opacity: 0.15
    });
    const icosahedron = new THREE.Mesh(geometry2, material2);
    icosahedron.position.set(15, 10, -20);
    scene.add(icosahedron);
    
    scene.userData.icosahedron = icosahedron;
    
    // Create particles for atmosphere
    createParticles();
}

function createParticles() {
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCnt = 500;
    
    const posArray = new Float32Array(particlesCnt * 3);
    for (let i = 0; i < particlesCnt * 3; i++) {
        posArray[i] = (Math.random() - 0.5) * 100;
    }
    
    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    
    const particlesMaterial = new THREE.PointsMaterial({
        size: 0.3,
        color: 0x00d9ff,
        transparent: true,
        opacity: 0.4,
        sizeAttenuation: true
    });
    
    const particles = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particles);
    scene.userData.particles = particles;
}

function animate() {
    requestAnimationFrame(animate);
    
    // Rotate background objects
    if (scene.userData.torusKnot1) {
        scene.userData.torusKnot1.rotation.x += 0.0005;
        scene.userData.torusKnot1.rotation.y += 0.0003;
    }
    
    if (scene.userData.icosahedron) {
        scene.userData.icosahedron.rotation.z += 0.0005;
        scene.userData.icosahedron.rotation.x += 0.0002;
    }
    
    if (scene.userData.particles) {
        scene.userData.particles.rotation.y += 0.0001;
    }
    
    renderer.render(scene, camera);
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

// ============ CHAT UI MANAGEMENT ============
function addMessage(role, content, metadata = {}) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    
    let displayContent = content;
    if (metadata.sources && metadata.sources.length > 0) {
        displayContent += `\n\n**Sources:**\n`;
        metadata.sources.forEach(source => {
            const page = source.page ? ` (Page ${source.page})` : '';
            displayContent += `- ${source.document_name}${page}\n`;
        });
    }
    
    // Simple markdown-like formatting
    displayContent = displayContent
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br/>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    messageDiv.innerHTML = `<div class="message-content"><p>${displayContent}</p></div>`;
    chatContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    // Update stats
    if (role === 'user' || role === 'assistant') {
        AppState.messageCount++;
        updateStats(metadata);
    }
}

function updateStats(metadata = {}) {
    document.getElementById('messageCount').textContent = AppState.messageCount;
    
    if (metadata.tool_used) {
        AppState.lastTool = metadata.tool_used;
        document.getElementById('lastTool').textContent = metadata.tool_used;
    }
    
    if (metadata.confidence !== undefined) {
        AppState.confidence = metadata.confidence;
        const confidence = Math.round(metadata.confidence * 100);
        document.getElementById('confidence').textContent = `${confidence}%`;
    }
}

// ============ MESSAGE SENDING ============
async function sendMessage(text = null) {
    const input = document.getElementById('userInput');
    const message = text || input.value.trim();
    
    if (!message) return;
    
    // Clear input
    if (!text) input.value = '';
    
    // Add user message to UI
    addMessage('user', message);
    
    // Send to API
    try {
        const response = await fetch(`${AppState.apiBaseUrl}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                memory_type: AppState.settings.memoryType,
                language: AppState.settings.language
            })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Add assistant message
        const metadata = {
            tool_used: result.tool_used || 'RAG/LLM',
            confidence: result.confidence || 0.8,
            sources: result.sources || []
        };
        
        addMessage('assistant', result.answer, metadata);
        
        // Play audio response if enabled
        if (AppState.settings.autoPlayAudio && result.audio_url) {
            playAudio(result.audio_url);
        }
        
    } catch (error) {
        console.error('Chat error:', error);
        addMessage('system', `Error: ${error.message}`);
    }
}

// ============ VOICE I/O ============
async function initMicrophone() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        AppState.mediaRecorder = new MediaRecorder(stream);
        
        AppState.mediaRecorder.ondataavailable = (event) => {
            AppState.audioChunks.push(event.data);
        };
        
        AppState.mediaRecorder.onstop = async () => {
            await handleRecordingComplete();
        };
        
        return true;
    } catch (error) {
        console.error('Microphone access error:', error);
        alert('Unable to access microphone. Check browser permissions.');
        return false;
    }
}

function toggleRecording() {
    const micBtn = document.getElementById('micBtn');
    
    if (!AppState.isRecording) {
        // Start recording
        if (!AppState.mediaRecorder) {
            initMicrophone().then(success => {
                if (success) startRecording();
            });
        } else {
            startRecording();
        }
    } else {
        // Stop recording
        stopRecording();
    }
}

function startRecording() {
    AppState.audioChunks = [];
    AppState.mediaRecorder.start();
    AppState.isRecording = true;
    
    document.getElementById('micBtn').classList.add('recording');
    document.getElementById('micBtn').textContent = '⏹️ Stop';
}

function stopRecording() {
    AppState.mediaRecorder.stop();
    AppState.isRecording = false;
    
    document.getElementById('micBtn').classList.remove('recording');
    document.getElementById('micBtn').textContent = '🎤 Record';
}

async function handleRecordingComplete() {
    const audioBlob = new Blob(AppState.audioChunks, { type: 'audio/wav' });
    
    try {
        // Send audio to backend for STT
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');
        
        const response = await fetch(`${AppState.apiBaseUrl}/transcribe`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Transcription failed');
        }
        
        const result = await response.json();
        const transcribedText = result.text;
        
        // Add recognized text to input and send
        document.getElementById('userInput').value = transcribedText;
        addMessage('system', `🎤 Recognized: "${transcribedText}"`);
        
        // Auto-send if desired
        setTimeout(() => sendMessage(transcribedText), 500);
        
    } catch (error) {
        console.error('Transcription error:', error);
        addMessage('system', `STT Error: ${error.message}`);
    }
}

function playAudio(audioUrl) {
    const audio = document.getElementById('audioOutput');
    audio.src = audioUrl;
    audio.play().catch(err => console.error('Audio playback error:', err));
}

// ============ SETTINGS MODAL ============
function openSettings() {
    document.getElementById('settingsModal').classList.add('active');
}

function closeSettings() {
    document.getElementById('settingsModal').classList.remove('active');
}

function saveSettings() {
    AppState.settings.memoryType = document.getElementById('memoryType').value;
    AppState.settings.voiceBackend = document.getElementById('voiceBackend').value;
    AppState.settings.language = document.getElementById('language').value;
    
    // Persist to localStorage
    localStorage.setItem('jarvisSettings', JSON.stringify(AppState.settings));
    
    closeSettings();
    addMessage('system', '✓ Settings saved successfully');
}

function loadSettings() {
    const saved = localStorage.getItem('jarvisSettings');
    if (saved) {
        AppState.settings = JSON.parse(saved);
        document.getElementById('memoryType').value = AppState.settings.memoryType;
        document.getElementById('voiceBackend').value = AppState.settings.voiceBackend;
        document.getElementById('language').value = AppState.settings.language;
    }
}

// ============ EVENT LISTENERS ============
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Three.js
    initThreeJS();
    
    // Load saved settings
    loadSettings();
    
    // Chat controls
    document.getElementById('sendBtn').addEventListener('click', () => sendMessage());
    document.getElementById('userInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // Voice controls
    document.getElementById('micBtn').addEventListener('click', toggleRecording);
    document.getElementById('volumeBtn').addEventListener('click', toggleAudioOutput);
    
    // Settings modal
    document.querySelectorAll('[href="#settings"]')[0]?.addEventListener('click', openSettings);
    document.querySelector('.close-btn').addEventListener('click', closeSettings);
    document.querySelector('.action-btn').addEventListener('click', saveSettings);
    
    // Modal close on background click
    document.getElementById('settingsModal').addEventListener('click', (e) => {
        if (e.target.id === 'settingsModal') closeSettings();
    });
    
    // Quick action buttons
    document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const text = e.target.closest('.quick-btn').textContent.trim();
            // Extract actual question from button (skip emoji)
            const lines = text.split('\n');
            const question = lines[lines.length - 1];
            if (question && question.length > 1) {
                sendMessage(question);
            }
        });
    });
});

// ============ UTILITY FUNCTIONS ============
function toggleAudioOutput() {
    AppState.settings.autoPlayAudio = !AppState.settings.autoPlayAudio;
    const volumeBtn = document.getElementById('volumeBtn');
    volumeBtn.style.opacity = AppState.settings.autoPlayAudio ? '1' : '0.5';
    
    const status = AppState.settings.autoPlayAudio ? 'enabled' : 'disabled';
    addMessage('system', `🔊 Audio output ${status}`);
}

// Prevent quick-btn default behavior
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.quick-btn').forEach(btn => {
        // Get the actual text content of quick actions (after the emoji line)
        const originalClick = btn.onclick;
        btn.onclick = function() {
            // Extract the question text from within the quick-btn
            const icon = this.querySelector('.quick-icon');
            const text = this.textContent.replace(icon.textContent, '').trim();
            if (text) {
                sendMessage(text);
            }
            return false;
        };
    });
});

// ============ API FALLBACK FOR DEVELOPMENT ============
/**
 * Mock API responses for offline development.
 * Replace with real API calls when backend is ready.
 */
async function mockChatResponse(message) {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 800));
    
    // Simple intent detection
    let response = {
        answer: "I'm Jarvis-Lite, your AI assistant. I can help you with calculations, weather, document search, and general questions.",
        tool_used: 'RAG/LLM',
        confidence: 0.85,
        sources: [],
        audio_url: null
    };
    
    if (message.toLowerCase().includes('calculate') || /[\d+\-*/]/.test(message)) {
        response.answer = "I can help with calculations, but I need the backend API running. Please set up FastAPI.";
        response.tool_used = 'Calculator';
        response.confidence = 0.9;
    } else if (message.toLowerCase().includes('weather')) {
        response.answer = "Weather queries require the backend API. Please check your configuration.";
        response.tool_used = 'Weather';
        response.confidence = 0.85;
    } else if (message.toLowerCase().includes('document') || message.toLowerCase().includes('search')) {
        response.answer = "Document search requires uploaded files in the backend. Please check your database.";
        response.tool_used = 'Document Search';
        response.confidence = 0.8;
        response.sources = [{ document_name: 'example.pdf', page: 1 }];
    }
    
    return response;
}

// Console helper for testing
window.testChat = async (message) => {
    addMessage('user', message);
    const response = await mockChatResponse(message);
    addMessage('assistant', response.answer, {
        tool_used: response.tool_used,
        confidence: response.confidence,
        sources: response.sources
    });
};

console.log('Jarvis-Lite UI initialized. Try: testChat("Calculate 2+2")');

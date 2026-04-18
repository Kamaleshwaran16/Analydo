// Helper library for interacting with the backend Flask API

const API_BASE_URL = '';

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Upload failed');
    }
    
    return await response.json();
}

async function cleanData() {
    const response = await fetch(`${API_BASE_URL}/clean`, {
        method: 'POST'
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Clean failed');
    }
    
    return await response.json();
}

async function analyzeData() {
    const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'GET'
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Analysis failed');
    }
    
    return await response.json();
}

async function getReport() {
    const response = await fetch(`${API_BASE_URL}/report`, {
        method: 'GET'
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Report generation failed');
    }
    
    return await response.json();
}

async function askChatbot(question) {
    const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question })
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Chatbot request failed');
    }
    
    return await response.json();
}

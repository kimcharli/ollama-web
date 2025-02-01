// Helper function to format bytes
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Model Manager functionality
document.addEventListener('DOMContentLoaded', () => {
    const refreshButton = document.getElementById('refreshModels');
    const browseButton = document.getElementById('browseLibrary');
    const libraryModels = document.getElementById('libraryModels');
    const modelsList = document.getElementById('modelsList');
    const modelSelector = document.getElementById('modelSelector');
    const errorMessage = document.getElementById('errorMessage');
    const ollamaStatus = document.getElementById('ollamaStatus');

    // Helper function to show error
    function showError(message, type = 'error') {
        errorMessage.textContent = message;
        errorMessage.className = type === 'error' ? 'text-red-600 text-sm' : 'text-green-600 text-sm';
        errorMessage.classList.remove('hidden');
        setTimeout(() => {
            errorMessage.classList.add('hidden');
        }, 5000);
    }

    // Fetch local models
    async function fetchLocalModels() {
        try {
            const response = await fetch('/fetch/models', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch models');
            }

            const data = await response.json();
            if (!data.models) {
                throw new Error('Invalid response format');
            }

            // Update model selector
            updateModelSelector(data.models);
        } catch (error) {
            showError('Error fetching models: ' + error.message);
        }
    }

    // Update model selector dropdown
    function updateModelSelector(models) {
        const currentValue = modelSelector.value;
        modelSelector.innerHTML = '';
        
        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select a model';
        modelSelector.appendChild(defaultOption);
        
        // Add model options
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = `${model.name} (${formatBytes(model.size)})`;
            modelSelector.appendChild(option);
        });
        
        // Try to restore previous selection
        if (currentValue && models.some(m => m.name === currentValue)) {
            modelSelector.value = currentValue;
        }

        // If only one model is available, select it
        if (models.length === 1) {
            modelSelector.value = models[0].name;
            // Update hidden model input
            const modelInput = document.getElementById('model');
            if (modelInput) {
                modelInput.value = models[0].name;
            }
        }
    }

    // Browse library models
    async function browseLibrary() {
        try {
            const response = await fetch('/library/models', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch library models');
            }

            const data = await response.json();
            if (!data.models) {
                throw new Error('Invalid response format');
            }

            // Clear and show models list
            modelsList.innerHTML = '';
            libraryModels.classList.remove('hidden');

            // Add models to the list
            data.models.forEach(model => {
                const modelElement = document.createElement('div');
                modelElement.className = 'flex items-center justify-between p-2 hover:bg-gray-50';
                modelElement.innerHTML = `
                    <div class="flex-1">
                        <div class="text-sm font-medium text-gray-900">${model.name}</div>
                        ${model.description ? `<div class="text-xs text-gray-500">${model.description}</div>` : ''}
                    </div>
                    <button class="pull-model-btn ml-4 px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600" data-model="${model.name}">
                        Pull
                    </button>
                `;

                // Add click handler for pull button
                const pullButton = modelElement.querySelector('.pull-model-btn');
                pullButton.addEventListener('click', () => pullModel(model.name));

                modelsList.appendChild(modelElement);
            });
        } catch (error) {
            showError('Error fetching library models: ' + error.message);
        }
    }

    // Pull model
    async function pullModel(modelName) {
        try {
            // First check if the model exists in the library
            const response = await fetch('/pull/model', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                },
                body: JSON.stringify({ name: modelName })
            });

            if (!response.ok) {
                throw new Error('Failed to initiate model pull');
            }

            // Create progress element
            const modelDiv = document.querySelector(`[data-model="${modelName}"]`).closest('.flex');
            const progressDiv = document.createElement('div');
            progressDiv.className = 'mt-2 w-full';
            progressDiv.innerHTML = `
                <div class="text-sm text-gray-600 progress-text">Starting download...</div>
                <div class="mt-1 relative">
                    <div class="overflow-hidden h-2 text-xs flex rounded bg-gray-200">
                        <div class="progress-bar-fill shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-green-500" style="width: 0%"></div>
                    </div>
                </div>
            `;
            modelDiv.appendChild(progressDiv);

            // Set up event source for progress
            const eventSource = new EventSource(`/pull/model?name=${encodeURIComponent(modelName)}`);
            
            eventSource.addEventListener('progress', (event) => {
                const data = JSON.parse(event.data);
                if (data.completed && data.total) {
                    const percent = (data.completed / data.total * 100).toFixed(1);
                    progressDiv.querySelector('.progress-text').textContent = 
                        `${data.status || 'Downloading'}: ${percent}% (${formatBytes(data.completed)} / ${formatBytes(data.total)})`;
                    progressDiv.querySelector('.progress-bar-fill').style.width = `${percent}%`;
                } else {
                    progressDiv.querySelector('.progress-text').textContent = data.status || 'Processing...';
                }
            });

            eventSource.addEventListener('error', (event) => {
                try {
                    const data = JSON.parse(event.data);
                    showError(data.error || 'Error pulling model');
                } catch (e) {
                    showError('Error pulling model');
                }
                eventSource.close();
                progressDiv.remove();
            });

            eventSource.addEventListener('done', (event) => {
                eventSource.close();
                progressDiv.remove();
                showError('Model downloaded successfully', 'success');
                fetchLocalModels(); // Refresh local models
            });

            // Add abort handler
            const abortButton = document.createElement('button');
            abortButton.className = 'mt-1 text-sm text-red-600 hover:text-red-800';
            abortButton.textContent = 'Abort';
            abortButton.onclick = () => {
                eventSource.close();
                progressDiv.remove();
                showError('Pull aborted');
            };
            progressDiv.appendChild(abortButton);

        } catch (error) {
            showError('Error pulling model: ' + error.message);
        }
    }

    // Check Ollama status
    async function checkOllamaStatus() {
        try {
            const response = await fetch('/fetch/models', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                }
            });

            // Update status indicator
            if (response.ok) {
                ollamaStatus.innerHTML = `
                    <span class="relative flex h-3 w-3">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span class="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                    <span class="ml-2 text-sm text-green-600">Ollama Ready</span>
                `;
                return true;
            } else {
                throw new Error('Failed to connect to Ollama');
            }
        } catch (error) {
            ollamaStatus.innerHTML = `
                <span class="relative flex h-3 w-3">
                    <span class="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                </span>
                <span class="ml-2 text-sm text-red-600">Ollama Offline</span>
            `;
            return false;
        }
    }

    // Load current model
    async function loadCurrentModel() {
        try {
            const response = await fetch('/api/current-model');
            if (!response.ok) {
                throw new Error('Failed to fetch current model');
            }

            const data = await response.json();
            if (data.model) {
                modelSelector.value = data.model;
                // Update hidden model input
                const modelInput = document.getElementById('model');
                if (modelInput) {
                    modelInput.value = data.model;
                }
            }
        } catch (error) {
            console.error('Error loading current model:', error);
        }
    }

    // Check status periodically
    async function startStatusCheck() {
        // Initial check
        await checkOllamaStatus();
        
        // Check every 30 seconds
        setInterval(checkOllamaStatus, 30000);
    }

    // Handle model selection
    modelSelector.addEventListener('change', async () => {
        const selectedModel = modelSelector.value;
        if (selectedModel) {
            try {
                const response = await fetch('/api/select-model', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                    },
                    body: JSON.stringify({ model: selectedModel })
                });

                if (!response.ok) {
                    throw new Error('Failed to select model');
                }

                // Update hidden model input
                const modelInput = document.getElementById('model');
                if (modelInput) {
                    modelInput.value = selectedModel;
                }

                const data = await response.json();
                if (data.status === 'success') {
                    showError(`Model ${selectedModel} selected`, 'success');
                } else {
                    throw new Error('Failed to select model');
                }
            } catch (error) {
                console.error('Error selecting model:', error);
                showError('Failed to select model');
            }
        }
    });

    // Event listeners
    browseButton.addEventListener('click', browseLibrary);
    refreshButton.addEventListener('click', fetchLocalModels);
    modelsList.addEventListener('click', (e) => {
        const pullButton = e.target.closest('.pull-model-btn');
        if (pullButton) {
            const modelName = pullButton.dataset.model;
            pullModel(modelName);
        }
    });

    // Initialize
    startStatusCheck();
    loadCurrentModel();
    fetchLocalModels();
});

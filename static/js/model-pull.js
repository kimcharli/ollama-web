class ModelPull extends HTMLElement {
    constructor() {
        super();
        this.isPulling = false;
        this.libraryModels = [];
    }

    connectedCallback() {
        this.render();
        this.setupEventListeners();
        this.fetchLibraryModels();
    }

    render() {
        this.innerHTML = `
            <div class="mt-4">
                <!-- Model Input -->
                <div class="flex space-x-2 mb-3">
                    <div class="flex-1">
                        <input type="text" name="modelName" id="modelName"
                            class="focus:ring-indigo-500 focus:border-indigo-500 block w-full rounded-md sm:text-sm border-gray-300"
                            placeholder="Enter model name (e.g., llama2) or select below">
                    </div>
                    <button type="button" id="pullButton"
                        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white hidden" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" id="loading">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Pull
                    </button>
                </div>

                <!-- Library Models -->
                <div class="mt-3">
                    <h3 class="text-sm font-medium text-gray-700 mb-2">Available Models</h3>
                    <div class="bg-white overflow-hidden shadow rounded-md divide-y divide-gray-200 max-h-60 overflow-y-auto" id="libraryModelsList">
                        <div class="p-4 text-sm text-gray-500">Loading models...</div>
                    </div>
                </div>
                
                <!-- Progress Bar -->
                <div class="hidden mt-3" id="progressContainer">
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="bg-indigo-600 h-2 rounded-full" id="progressBar" style="width: 0%"></div>
                    </div>
                    <p class="mt-1 text-sm text-gray-600" id="progressText">Initializing...</p>
                </div>
            </div>
        `;
    }

    async fetchLibraryModels() {
        const modelsList = this.querySelector('#libraryModelsList');
        try {
            const response = await fetch('/api/library-models');
            if (!response.ok) {
                throw new Error('Failed to fetch library models');
            }

            const data = await response.json();
            this.libraryModels = data.models || [];

            // Update the list
            modelsList.innerHTML = this.libraryModels.length > 0 
                ? this.libraryModels.map(model => `
                    <div class="p-4 hover:bg-gray-50 cursor-pointer model-item" data-model="${model.name}">
                        <div class="flex items-center justify-between">
                            <div>
                                <h4 class="text-sm font-medium text-gray-900">${model.name}</h4>
                                ${model.description ? `<p class="mt-1 text-xs text-gray-500">${model.description}</p>` : ''}
                            </div>
                            <button class="ml-4 inline-flex items-center px-2.5 py-1.5 border border-transparent text-xs font-medium rounded text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                                Select
                            </button>
                        </div>
                    </div>
                `).join('')
                : '<div class="p-4 text-sm text-gray-500">No models available</div>';

            // Add click handlers
            modelsList.querySelectorAll('.model-item').forEach(item => {
                item.addEventListener('click', () => {
                    const modelName = item.dataset.model;
                    const modelInput = this.querySelector('#modelName');
                    if (modelInput) {
                        modelInput.value = modelName;
                    }
                });
            });

        } catch (error) {
            console.error('Error fetching library models:', error);
            modelsList.innerHTML = `
                <div class="p-4 text-sm text-red-500">
                    Failed to load models: ${error.message}
                </div>
            `;
        }
    }

    setupEventListeners() {
        const pullButton = this.querySelector('#pullButton');
        const modelInput = this.querySelector('#modelName');
        const loading = this.querySelector('#loading');
        const progressContainer = this.querySelector('#progressContainer');
        const progressBar = this.querySelector('#progressBar');
        const progressText = this.querySelector('#progressText');

        if (pullButton && modelInput) {
            pullButton.addEventListener('click', async () => {
                if (this.isPulling) return;

                const modelName = modelInput.value.trim();
                if (!modelName) {
                    alert('Please enter a model name or select one from the list');
                    return;
                }

                this.isPulling = true;
                loading.classList.remove('hidden');
                progressContainer.classList.remove('hidden');
                pullButton.disabled = true;

                try {
                    const response = await fetch('/api/pull-model', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ model: modelName })
                    });

                    if (!response.ok) {
                        throw new Error('Failed to start model pull');
                    }

                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    while (true) {
                        const { value, done } = await reader.read();
                        if (done) break;

                        const text = decoder.decode(value);
                        const lines = text.split('\n');

                        for (const line of lines) {
                            if (line.trim() && line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.slice(6));
                                    
                                    if (data.error) {
                                        throw new Error(data.error);
                                    }

                                    // Update progress
                                    if (data.status === 'downloading') {
                                        const completed = data.completed_mb || 0;
                                        const total = data.total_mb || 0;
                                        const percent = data.progress || 0;
                                        progressBar.style.width = `${percent}%`;
                                        progressText.textContent = `Downloading: ${completed}MB / ${total}MB (${percent}%)`;
                                    } else if (data.status === 'verifying') {
                                        progressBar.style.width = `100%`;
                                        progressText.textContent = 'Verifying download...';
                                    } else if (data.status === 'success' || data.status === 'done') {
                                        progressBar.style.width = `100%`;
                                        progressText.textContent = 'Download complete!';
                                        setTimeout(() => {
                                            progressContainer.classList.add('hidden');
                                            // Refresh available models
                                            document.dispatchEvent(new CustomEvent('refresh-models'));
                                        }, 2000);
                                        break;
                                    }
                                } catch (e) {
                                    console.error('Error parsing progress:', e);
                                }
                            }
                        }
                    }
                } catch (error) {
                    console.error('Pull failed:', error);
                    alert(`Pull failed: ${error.message}`);
                    progressText.textContent = `Error: ${error.message}`;
                } finally {
                    this.isPulling = false;
                    loading.classList.add('hidden');
                    pullButton.disabled = false;
                }
            });
        }
    }
}

customElements.define('model-pull', ModelPull);

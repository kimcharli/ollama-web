class ModelSelector extends HTMLElement {
    constructor() {
        super();
        this.models = [];
        this.currentModel = '';
    }

    connectedCallback() {
        this.render();
        this.setupEventListeners();
        this.fetchModels();
    }

    render() {
        this.innerHTML = `
            <div class="flex flex-col">
                <div class="flex items-center space-x-4 mb-3">
                    <div class="flex-grow">
                        <label for="modelSelector" class="block text-sm font-medium text-gray-700">Current Model</label>
                        <select id="modelSelector" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md">
                            <option value="">Select a model</option>
                        </select>
                    </div>
                    <div class="flex-none pt-6">
                        <button id="refreshModels" class="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600">
                            Refresh Models
                        </button>
                    </div>
                </div>
                <div id="errorMessage" class="hidden text-red-600 text-sm"></div>
            </div>
        `;
    }

    setupEventListeners() {
        const modelSelector = this.querySelector('#modelSelector');
        const refreshButton = this.querySelector('#refreshModels');
        const errorMessage = this.querySelector('#errorMessage');

        if (modelSelector) {
            modelSelector.addEventListener('change', async (event) => {
                const model = event.target.value;
                if (!model) return;

                try {
                    const response = await fetch('/api/select-model', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ model: model })
                    });

                    if (!response.ok) {
                        throw new Error('Failed to select model');
                    }

                    const data = await response.json();
                    if (data.error) {
                        throw new Error(data.error);
                    }

                    this.currentModel = model;
                    // Dispatch event for other components
                    this.dispatchEvent(new CustomEvent('model-changed', {
                        bubbles: true,
                        detail: { model: model }
                    }));

                } catch (error) {
                    console.error('Error selecting model:', error);
                    errorMessage.textContent = `Error: ${error.message}`;
                    errorMessage.classList.remove('hidden');
                }
            });
        }

        if (refreshButton) {
            refreshButton.addEventListener('click', () => {
                this.fetchModels();
            });
        }
    }

    async fetchModels() {
        const modelSelector = this.querySelector('#modelSelector');
        const errorMessage = this.querySelector('#errorMessage');

        try {
            const response = await fetch('/api/models');
            if (!response.ok) {
                throw new Error('Failed to fetch models');
            }

            const data = await response.json();
            this.models = data.models || [];

            // Update selector options
            modelSelector.innerHTML = `
                <option value="">Select a model</option>
                ${this.models.map(model => `
                    <option value="${model}" ${model === this.currentModel ? 'selected' : ''}>
                        ${model}
                    </option>
                `).join('')}
            `;

            errorMessage.classList.add('hidden');

        } catch (error) {
            console.error('Error fetching models:', error);
            errorMessage.textContent = `Error: ${error.message}`;
            errorMessage.classList.remove('hidden');
        }
    }

    // Method to get current model
    getCurrentModel() {
        return this.currentModel;
    }
}

customElements.define('model-selector', ModelSelector);

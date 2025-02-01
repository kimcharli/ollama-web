class PromptManager extends HTMLElement {
    constructor() {
        super();
        this.defaultPrompt = '';
        this.promptSuggestions = [];
        this.isAnalyzing = false;
    }

    connectedCallback() {
        this.render();
        this.setupEventListeners();
    }

    render() {
        this.innerHTML = `
            <div class="mb-6 bg-white shadow-lg rounded-lg p-6">
                <h2 class="text-xl font-bold mb-4 text-gray-800">Prompt Manager</h2>
                
                <!-- Prompt Input -->
                <div class="mb-4">
                    <label for="prompt" class="block text-sm font-medium text-gray-700">Enter your prompt</label>
                    <div class="mt-1">
                        <textarea id="prompt" name="prompt" rows="4"
                            class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                            placeholder="Enter your prompt here">${this.defaultPrompt}</textarea>
                    </div>
                </div>
                
                <!-- Prompt Suggestions -->
                <div class="relative inline-block text-left mt-4">
                    <button type="button" id="promptDropdownButton"
                        class="inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                        Suggested Prompts
                        <svg class="-mr-1 ml-2 h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                        </svg>
                    </button>
                    <div id="promptDropdown"
                        class="hidden origin-top-right absolute left-0 mt-2 w-full rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 divide-y divide-gray-100 focus:outline-none z-10">
                        <div class="py-1 max-h-60 overflow-auto" id="promptSuggestionsList">
                        </div>
                    </div>
                </div>

                <!-- Action Buttons -->
                <div class="mt-4 flex justify-end">
                    <button type="button" id="analyzeButton"
                        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white hidden" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" id="loading">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Analyze
                    </button>
                    <button type="button" id="abortButton"
                        class="hidden ml-3 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500">
                        Abort
                    </button>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const promptDropdownButton = this.querySelector('#promptDropdownButton');
        const promptDropdown = this.querySelector('#promptDropdown');
        const promptInput = this.querySelector('#prompt');
        const analyzeButton = this.querySelector('#analyzeButton');
        const abortButton = this.querySelector('#abortButton');
        const loading = this.querySelector('#loading');

        // Toggle dropdown
        if (promptDropdownButton && promptDropdown) {
            promptDropdownButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                promptDropdown.classList.toggle('hidden');
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', (event) => {
                if (!promptDropdownButton.contains(event.target) && !promptDropdown.contains(event.target)) {
                    promptDropdown.classList.add('hidden');
                }
            });
        }

        // Handle analyze button
        if (analyzeButton) {
            analyzeButton.addEventListener('click', () => {
                if (this.isAnalyzing) return;
                
                const prompt = promptInput.value.trim();
                if (!prompt) {
                    alert('Please enter a prompt');
                    return;
                }

                this.dispatchEvent(new CustomEvent('analyze', {
                    detail: {
                        prompt: prompt
                    }
                }));
            });
        }

        // Handle abort button
        if (abortButton) {
            abortButton.addEventListener('click', () => {
                this.dispatchEvent(new CustomEvent('abort'));
            });
        }
    }

    setPromptSuggestions(suggestions) {
        this.promptSuggestions = suggestions;
        const suggestionsList = this.querySelector('#promptSuggestionsList');
        if (suggestionsList) {
            suggestionsList.innerHTML = this.promptSuggestions.map(suggestion => `
                <button type="button"
                    class="text-gray-700 block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 hover:text-gray-900"
                    role="menuitem">${suggestion}</button>
            `).join('');

            // Add click handlers for suggestions
            suggestionsList.querySelectorAll('button').forEach(button => {
                button.addEventListener('click', () => {
                    const promptInput = this.querySelector('#prompt');
                    if (promptInput) {
                        promptInput.value = button.textContent.trim();
                        this.querySelector('#promptDropdown').classList.add('hidden');
                    }
                });
            });
        }
    }

    setDefaultPrompt(prompt) {
        this.defaultPrompt = prompt;
        const promptInput = this.querySelector('#prompt');
        if (promptInput && !promptInput.value) {
            promptInput.value = prompt;
        }
    }

    setAnalyzing(analyzing) {
        this.isAnalyzing = analyzing;
        const analyzeButton = this.querySelector('#analyzeButton');
        const abortButton = this.querySelector('#abortButton');
        const loading = this.querySelector('#loading');

        if (analyzing) {
            analyzeButton.disabled = true;
            loading.classList.remove('hidden');
            abortButton.classList.remove('hidden');
        } else {
            analyzeButton.disabled = false;
            loading.classList.add('hidden');
            abortButton.classList.add('hidden');
        }
    }

    getPrompt() {
        const promptInput = this.querySelector('#prompt');
        return promptInput ? promptInput.value.trim() : '';
    }
}

customElements.define('prompt-manager', PromptManager);

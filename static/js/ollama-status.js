class OllamaStatus extends HTMLElement {
    constructor() {
        super();
        this.checkInterval = null;
    }

    connectedCallback() {
        this.render();
        this.startChecking();
    }

    disconnectedCallback() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }
    }

    render() {
        this.innerHTML = `
            <div class="flex items-center">
                <span class="relative flex h-3 w-3">
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-gray-400 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-3 w-3 bg-gray-500"></span>
                </span>
                <span class="ml-2 text-sm text-gray-500">Checking Ollama...</span>
            </div>
        `;
    }

    async checkStatus() {
        const statusDot = this.querySelector('.relative.flex.h-3.w-3');
        const statusText = this.querySelector('span.text-sm');
        
        try {
            const response = await fetch('/api/ollama-status');
            if (response.ok) {
                const data = await response.json();
                if (data.running) {
                    // Update to green for running
                    statusDot.innerHTML = `
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span class="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    `;
                    statusText.textContent = 'Ollama Running';
                    statusText.classList.remove('text-gray-500', 'text-red-500');
                    statusText.classList.add('text-green-500');
                } else {
                    throw new Error('Ollama not running');
                }
            } else {
                throw new Error('Status check failed');
            }
        } catch (error) {
            // Update to red for not running
            statusDot.innerHTML = `
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
            `;
            statusText.textContent = 'Ollama Not Running';
            statusText.classList.remove('text-gray-500', 'text-green-500');
            statusText.classList.add('text-red-500');
        }
    }

    startChecking() {
        // Check immediately
        this.checkStatus();
        
        // Then check every 30 seconds
        this.checkInterval = setInterval(() => {
            this.checkStatus();
        }, 30000);
    }
}

customElements.define('ollama-status', OllamaStatus);

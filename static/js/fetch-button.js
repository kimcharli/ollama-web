class FetchButton extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        
        // Create styles
        const style = document.createElement('style');
        style.textContent = `
            .fetch-button {
                background-color: #4f46e5;
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 0.375rem;
                border: none;
                font-size: 0.875rem;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            
            .fetch-button:hover {
                background-color: #4338ca;
            }
            
            .fetch-button:disabled {
                background-color: #9ca3af;
                cursor: not-allowed;
            }
            
            .loading {
                opacity: 0.7;
            }
        `;
        
        // Create button
        const button = document.createElement('button');
        button.className = 'fetch-button';
        button.textContent = 'Fetch Models';
        
        // Add elements to shadow DOM
        this.shadowRoot.appendChild(style);
        this.shadowRoot.appendChild(button);
        
        // Bind event listener
        this.button = button;
        this.button.addEventListener('click', () => this.fetchModels());
    }
    
    async fetchModels() {
        try {
            this.setLoading(true);
            
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
            
            // Dispatch custom event with the fetched data
            const event = new CustomEvent('modelsFetched', {
                detail: data,
                bubbles: true,
                composed: true
            });
            this.dispatchEvent(event);
            
        } catch (error) {
            console.error('Error fetching models:', error);
            // Dispatch error event
            const event = new CustomEvent('fetchError', {
                detail: error.message,
                bubbles: true,
                composed: true
            });
            this.dispatchEvent(event);
        } finally {
            this.setLoading(false);
        }
    }
    
    setLoading(isLoading) {
        this.button.disabled = isLoading;
        this.button.classList.toggle('loading', isLoading);
        this.button.textContent = isLoading ? 'Fetching...' : 'Fetch Models';
    }
}

// Register the custom element
customElements.define('fetch-button', FetchButton);

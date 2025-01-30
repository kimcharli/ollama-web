import ollama

# Example usage
image_path = '/Users/ckim/Downloads/image003.png'  # Replace with your image path

# Use Ollama to clean and structure the OCR output
response = ollama.chat(
    model="llama3.2-vision",
    messages=[{
      "role": "user",
    #   "content": "The image is a book cover. Output should be in this format - <Name of the Book>: <Name of the Author>. Do not output anything else",
      "content": "What are there in the file?",
      "images": [image_path]
    }],
)
# Extract cleaned text
cleaned_text = response['message']['content'].strip()
print(cleaned_text)


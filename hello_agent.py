import ollama

print("Testing your local AI agent...\n")

response = ollama.chat(
    model="llama3.2",
    messages=[
        {
            "role": "user",
            "content": "I have these files in my downloads folder: resume.pdf, IMG_001.jpg, notes.txt, budget.xlsx, movie.mp4. How would you organize them into folders? Give me a simple plan."
        }
    ]
)

print(response["message"]["content"])

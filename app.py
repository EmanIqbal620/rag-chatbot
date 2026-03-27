from server import app as application

# For Hugging Face Spaces, use the application object directly
app = application

# The application object 'app' is what Hugging Face will serve
# No need to run uvicorn when deployed to Hugging Face Spaces
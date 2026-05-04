import sys
print("Python version:", sys.version)

try:
    from main import app, config
    print("App created successfully")
    print(f"Host: {config.HOST}")
    print(f"Port: {config.PORT}")
    
    import uvicorn
    print("Starting server...")
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="info")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
from src.main import app

if __name__ == "__main__":
    import uvicorn
    # uvicorn_config = {
    #     "host": "0.0.0.0",
    #     "port": 8000,
    #     "reload": True,  
    #     "workers": 1,   
    #     "log_level": "info",
    #     "access_log": True
    # }
    # uvicorn.run("src.main:app", **uvicorn_config)
    uvicorn.run("src.main:app", host="0.0.0.0", port=1605, reload=False, workers=5)

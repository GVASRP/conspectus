import uvicorn

from app import config

if __name__ == "__main__":
    uvicorn.run("web.main:app", host=config.WEB_HOST, port=config.WEB_PORT)

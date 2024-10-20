from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_login import LoginManager
import os
from dotenv import load_dotenv

load_dotenv()

SECRET = os.getenv('SECRET_KEY', 'mysecret')
USERNAME = os.getenv('APP_USERNAME', 'admin')
PASSWORD = os.getenv('APP_PASSWORD', 'password')

router = APIRouter()
manager = LoginManager(SECRET, token_url='/login', use_cookie=True)

@manager.user_loader
def load_user(username: str):
    if username == USERNAME:
        return {"username": USERNAME}
    return None

@router.get("/login", response_class=HTMLResponse)
async def login_form():
    return """
    <form method="post" action="/login">
        <input type="text" name="username" placeholder="Username" required>
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
    """

# @router.post("/login")
# async def login(request: Request, username: str = Form(...), password: str = Form(...)):
#     if username != USERNAME or password != PASSWORD:
#         raise HTTPException(status_code=401, detail="Invalid username or password")

#     response = RedirectResponse(url='/', status_code=302)
#     manager.set_cookie(response, username, path="/", max_age=3600)
#     return response

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username != USERNAME or password != PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response = RedirectResponse(url='/', status_code=302)
    manager.set_cookie(response, username)
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url='/login', status_code=302)
    manager.set_cookie(response, None, path="/")  # Удаление cookie для выхода
    return response

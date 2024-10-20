from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import get_db
from app.routers import documents
from fastapi import FastAPI, Depends
from app.login import router as login_router, manager

app = FastAPI()

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Инициализация базы данных
get_db()

# Настройка шаблонов
templates = Jinja2Templates(directory="app/templates")

# Подключение роутеров
app.include_router(documents.router)

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



# from fastapi import FastAPI, Request, Depends
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import HTMLResponse, RedirectResponse
# from fastapi.templating import Jinja2Templates
# from app.database import get_db
# from app.routers import documents
# from app.login import router as login_router, manager

# app = FastAPI()

# # Подключение статических файлов
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

# # Инициализация базы данных
# get_db()

# # Настройка шаблонов
# templates = Jinja2Templates(directory="app/templates")

# # Подключение маршрутов для входа и выхода
# app.include_router(login_router)

# # Подключение других маршрутов
# app.include_router(documents.router)

# # Защищённая главная страница — доступна только после аутентификации
# @app.get("/", response_class=HTMLResponse)
# async def home(request: Request, user=Depends(manager)):
#     print(f"Authenticated user: {user}")  # Вывод информации о пользователе в консоль
#     return templates.TemplateResponse("index.html", {"request": request, "user": user})

# # Обработчик для страницы входа, если пользователь не авторизован
# @app.get("/login", response_class=HTMLResponse)
# async def login_page(request: Request):
#     return templates.TemplateResponse("login.html", {"request": request})





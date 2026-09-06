from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from backend.app.config import settings, FRONTEND_DIST, UPLOADS_DIR
from backend.app.database import engine
from backend.app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动定时调度器 (内部有 Windows 文件锁守护，防 reload 重复)
    start_scheduler()
    yield
    # 关闭定时调度器
    stop_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="初中生作业打卡与错题本系统 API",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态资源服务：上传图片
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


from backend.app.schemas import HealthOut
from backend.app.routers import (
    homework,
    mistakes,
    backup,
    settings as app_settings,
    ocr as ocr_router,
    notifications as notifications_router,
    paper as paper_router,
    exams as exams_router,
)
from backend.app.seed import seed_database

# 自动填充初始数据（前提是 Alembic 迁移已执行）
seed_database()

# 注册业务路由
app.include_router(homework.router)
app.include_router(mistakes.router)
app.include_router(backup.router)
app.include_router(app_settings.router)
app.include_router(ocr_router.router)
app.include_router(notifications_router.router)
app.include_router(paper_router.router)
app.include_router(exams_router.router)



# 健康检查端点
@app.get("/api/health", response_model=HealthOut)
def health_check():
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION
    }


# 前端页面托管（SPA 支持）
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 严格拦截 /api 路径，未定义的 API 返回 404 JSON 而非 index.html
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/")
    async def index_placeholder():
        return HTMLResponse(
            """
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>学迹 StudyTrace</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #f8fafc; color: #1e293b; }
                    .card { background: white; padding: 2.5rem; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); text-align: center; max-width: 420px; }
                    h1 { margin: 0 0 0.5rem 0; color: #2563eb; font-size: 1.8rem; }
                    p { color: #64748b; font-size: 0.95rem; line-height: 1.5; }
                    .badge { display: inline-block; background: #dbeafe; color: #1d4ed8; padding: 0.3rem 0.8rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 500; margin-top: 1rem; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>学迹 StudyTrace</h1>
                    <p>后端 API 服务运行正常。前端 Vite 工程正在构建或准备中。</p>
                    <div class="badge">API Status: OK · Port 8000</div>
                </div>
            </body>
            </html>
            """
        )

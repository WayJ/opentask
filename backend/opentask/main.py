import json
import logging
import socket
import sys
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# # from alembic import command
# from alembic.config import Config
from opentask.app import App
from opentask.config import IS_BUNDLED, config
from opentask.models.common.response import SuccessResponse

# ============================================================================
# ⚠️ 旧架构服务（已废弃 - 迁移到 Git + Web 编辑架构 v2.0）
# 新架构使用 GitKnowledgeService，详见 docs/knowledge-base/GIT_WEB_ARCHITECTURE.md
# ============================================================================
# from opentask.services.file_storage import FileStorageService
# from opentask.services.sync_service import SyncService
# from opentask.services.file_watcher import FileWatcherService
# from opentask.services.git_service import GitService
# from opentask.services.auto_commit_service import AutoCommitService
# from opentask.repositories.base import SessionCreator

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# ============================================================================
# 全局服务实例（旧架构 - 已废弃）
# ============================================================================
# file_storage_service: FileStorageService | None = None
# sync_service: SyncService | None = None
# file_watcher_service: FileWatcherService | None = None
# git_service: GitService | None = None
# auto_commit_service: AutoCommitService | None = None


def run_migrations() -> None:
    if IS_BUNDLED:
        path = Path(__file__).parent / "alembic.ini"
    else:
        path = Path(__file__).parent.parent / "alembic.ini"

    alembic_cfg = Config(path)
    loc = alembic_cfg.get_main_option("script_location")
    if loc:
        loc = loc.removeprefix("./")
    else:
        raise Exception("Something went wrong - alembic config is None")

    if IS_BUNDLED:
        loc = Path(__file__).parent / loc

    alembic_cfg.set_main_option("script_location", str(loc))
    alembic_cfg.config_file_name = None  # to prevent alembic from overriding the logs
    command.upgrade(alembic_cfg, "head", sql=False)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # On startup
    # logger.info("知识库系统: Git + Web 编辑架构 v2.0")
    # logger.info("新架构不再使用本地文件系统存储，知识内容存储在 Git 远程仓库")

    # Create data directory if not exists
    Path(config.data_directory).mkdir(parents=True, exist_ok=True)
    if IS_BUNDLED or config.spa_mode:
        run_migrations()
        webbrowser.open("http://localhost:7377", new=2)

    # 用户中心幂等播种：权限点字典 + 系统角色（Phase 3 Task 3）
    # 播种失败 = 桥接角色权限为空 → 权限接口全部 403，
    # 因此显眼报错但不阻断启动（服务本身还能起，问题留给运维排查）
    try:
        from opentask.repositories.base import SessionCreator
        from opentask.services.user_center.seed import seed_user_center

        async with SessionCreator() as session:
            stats = await seed_user_center(session)
        logger.info(
            f"✅ 用户中心播种完成: permissions={stats['permissions']}, "
            f"roles={stats['roles']}"
        )
    except Exception as e:
        logger.error(
            f"❌ 用户中心播种失败（权限接口将全部 403，请检查数据库）: {e}"
        )

    # 启动任务监控服务（规则1: 超时任务自动失败）
    if config.task_monitor_enabled:
        from opentask.services.mission_center.task_monitor import get_task_monitor_service

        task_monitor = get_task_monitor_service(
            check_interval_minutes=config.task_monitor_check_interval_minutes,
            timeout_hours=config.task_monitor_timeout_hours
        )
        await task_monitor.start()
        logger.info(f"✅ 任务监控服务已启动 (检查间隔: {config.task_monitor_check_interval_minutes}分钟, 超时时间: {config.task_monitor_timeout_hours}小时)")
    else:
        logger.info("⏸️ 任务监控服务已禁用 (通过配置 TASK_MONITOR_ENABLED=false)")

    # ============================================================================
    # 旧架构服务初始化（已废弃 - 文件优先架构）
    # 新架构：知识库使用 Git 远程仓库 + GitKnowledgeService
    # 详见: docs/knowledge-base/GIT_WEB_ARCHITECTURE.md
    # ============================================================================
    # # 启动文件优先架构服务（Phase 2 + Phase 3）
    # global file_storage_service, sync_service, file_watcher_service, git_service, auto_commit_service
    # try:
    #     # 创建文件存储服务
    #     file_storage_service = FileStorageService()
    #     logger.info(f"文件存储服务已初始化: {file_storage_service.knowledge_root}")
    #
    #     # 创建数据库会话和同步服务
    #     async with SessionCreator() as db:
    #         sync_service = SyncService(db, file_storage_service)
    #
    #         # 执行全量同步（确保数据库与文件系统一致）
    #         logger.info("开始全量同步知识库...")
    #         await sync_service.full_sync()
    #
    #         # 检查完整性
    #         total_files, synced_files = await sync_service.check_integrity()
    #         logger.info(f"数据完整性: {synced_files}/{total_files} 个文件已同步")
    #
    #     # 创建 Git 服务
    #     git_service = GitService(file_storage_service)
    #     logger.info("Git 服务已初始化")
    #
    #     # 创建自动提交服务（暂不启动后台任务）
    #     # TODO: 实现后台任务管理后再启动
    #     auto_commit_service = AutoCommitService(
    #         db=None,  # 稍后传入
    #         git_service=git_service,
    #         interval=300,  # 5 分钟
    #         enabled=True
    #     )
    #     logger.info("自动提交服务已配置（待启动）")
    #
    #     # 创建并启动文件监控服务
    #     async def sync_callback(file_path: str, deleted: bool = False):
    #         """文件监控回调函数"""
    #         if sync_service:
    #             # 创建新的会话来处理同步
    #             async with SessionCreator() as db:
    #                 sync_service.db = db
    #                 await sync_service.sync_file(file_path, deleted)
    #
    #     # 获取当前事件循环
    #     import asyncio
    #     loop = asyncio.get_running_loop()
    #
    #     file_watcher_service = FileWatcherService(
    #         file_storage_service,
    #         sync_callback,
    #         loop,
    #         debounce_seconds=1.0
    #     )
    #     file_watcher_service.start()
    #     logger.info("文件监控服务已启动")
    #
    # except Exception as e:
    #     logger.error(f"文件优先架构服务启动失败: {e}")
    #     # 不阻止应用启动，只记录错误

    yield

    # ============================================================================
    # 服务停止
    # ============================================================================
    # 停止任务监控服务
    if config.task_monitor_enabled:
        # 注意：这里无法获取到之前启动的 task_monitor 实例
        # 实际使用中，应该将 task_monitor 保存为全局变量或使用单例模式
        # 当前实现中，get_task_monitor_service() 返回的是单例，所以可以获取到
        from opentask.services.mission_center.task_monitor import get_task_monitor_service

        task_monitor = get_task_monitor_service()
        await task_monitor.stop()
        logger.info("✅ 任务监控服务已停止")

    # ============================================================================
    # 旧架构服务停止（已废弃）
    # ============================================================================
    # # On shutdown
    # # 停止文件监控服务
    # if file_watcher_service:
    #     file_watcher_service.stop()
    #     logger.info("文件监控服务已停止")
    #
    # # 停止自动提交服务
    # if auto_commit_service:
    #     auto_commit_service.stop()
    #     logger.info("自动提交服务已停止")


app = App(lifespan=lifespan)  # type: ignore


# 注册工作管理 API 路由
from opentask.api.work_management import router as work_management_router
app.include_router(work_management_router)


@app.get("/healthcheck", response_model_exclude_none=True)
async def healthcheck() -> SuccessResponse[None]:
    return SuccessResponse()


if IS_BUNDLED or config.spa_mode:
    # running in a PyInstaller bundle
    templates = Jinja2Templates(directory=config.templates_path)
    app.mount("/assets", StaticFiles(directory=config.assets_path), name="static")

    @app.get("/{rest_of_path:path}", include_in_schema=False)
    def index(request: Request, rest_of_path: str) -> Response:
        context: dict = {"request": request}
        vite_config_path = config.assets_path / "manifest.json"
        if not vite_config_path.is_file():
            raise HTTPException(status_code=404, detail="Could not find frontend manifest")

        with vite_config_path.open("r") as f:
            vite_config = json.load(f)
            context["VITE_MANIFEST_JS"] = vite_config["index.html"]["file"]
            context["VITE_MANIFEST_CSS"] = vite_config["index.html"]["css"][0]

        return templates.TemplateResponse("index.html.jinja2", context=context)

    def is_port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("0.0.0.0", port)) == 0

    if __name__ == "__main__":
        if not is_port_in_use(7377):

            class NullOutput(object):
                def write(self, _: str) -> None:
                    pass

                def isatty(self) -> bool:
                    return False

            sys.stdout = NullOutput() if sys.stdout is None else sys.stdout
            sys.stderr = NullOutput() if sys.stderr is None else sys.stderr
            uvicorn.run(app, host="0.0.0.0", port=7377)
        else:
            webbrowser.open("http://localhost:7377", new=2)

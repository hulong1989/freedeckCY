# main.py - freedeckCY 插件入口
#
# 只保留天翼下载与本地网页服务所需能力。

import asyncio
import os

import decky

import config
import server_manager
from tianyi_service import LocalWebNotReadyError, TianyiService


class Plugin:
    """freedeckCY 主插件类。"""

    # 本地 HTTP 服务状态
    server_running = False
    server_host = config.DEFAULT_SERVER_HOST
    server_port = config.DEFAULT_SERVER_PORT
    app = None
    runner = None
    site = None

    # 目录状态
    downloads_dir = config.DOWNLOADS_DIR
    decky_send_dir = config.DECKY_SEND_DIR

    # 业务服务
    tianyi_service = None

    # 设置键
    SETTINGS_KEY = config.SETTINGS_KEY
    SETTING_RUNNING = config.SETTING_RUNNING
    SETTING_PORT = config.SETTING_PORT
    SETTING_DOWNLOAD_DIR = config.SETTING_DOWNLOAD_DIR

    async def _main(self):
        """插件主循环。"""
        decky.logger.info("freedeckCY plugin initialized")
        config.logger.info("freedeckCY plugin initialized")

        os.makedirs(self.decky_send_dir, exist_ok=True)
        os.makedirs(self.downloads_dir, exist_ok=True)

        await server_manager.load_settings(self)
        os.makedirs(self.downloads_dir, exist_ok=True)

        self.tianyi_service = TianyiService(self)
        await self.tianyi_service.initialize()

        # 按上次保存的状态恢复本地服务。
        if bool(self.server_running):
            start_result = await server_manager.start_server(self, self.server_port)
            if start_result.get("status") != "success":
                decky.logger.error(
                    "Failed to restore local server: %s",
                    start_result.get("message", "unknown error"),
                )
                self.server_running = False
                await server_manager.save_settings(self)

        # 启动后先跑一次维护：续传上次的下载、补做中断的安装。
        try:
            await self.tianyi_service.maintenance_tick()
        except Exception as exc:
            decky.logger.error("Initial maintenance tick failed: %s", exc)
            config.logger.exception("Initial maintenance tick failed: %s", exc)

        while True:
            await asyncio.sleep(config.MAINTENANCE_INTERVAL_SECONDS)
            # 后台推进下载/安装：不依赖 Decky 面板是否打开，
            # 下载完成、插件重启、解压中断后都能继续。
            service = self.tianyi_service
            if service is None:
                continue
            try:
                await service.maintenance_tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                decky.logger.error("freedeckCY maintenance tick failed: %s", exc)
                config.logger.exception("Maintenance tick failed: %s", exc)

    async def _unload(self):
        """插件卸载时清理服务。"""
        decky.logger.info("Unloading freedeckCY plugin")

        try:
            await server_manager.stop_server(self)
        except Exception as exc:
            decky.logger.error(f"Stop server failed: {exc}")

        if self.tianyi_service is not None:
            try:
                await self.tianyi_service.shutdown()
            except Exception as exc:
                decky.logger.error(f"Stop Tianyi service failed: {exc}")
            self.tianyi_service = None

    async def _uninstall(self):
        """插件卸载钩子。"""
        decky.logger.info("Uninstalling freedeckCY plugin")

    # ------------------------- 本地服务接口 -------------------------

    async def start_server(self, port: int = config.DEFAULT_SERVER_PORT) -> dict:
        """启动本地网页服务。"""
        return await server_manager.start_server(self, port)

    async def stop_server(self) -> dict:
        """停止本地网页服务。"""
        return await server_manager.stop_server(self)

    async def get_server_status(self) -> dict:
        """获取本地网页服务状态。"""
        return await server_manager.get_server_status(self)

    async def set_download_dir(self, path: str) -> dict:
        """更新下载目录并持久化。"""
        try:
            if not isinstance(path, str) or not path.strip():
                return {"status": "error", "message": "无效的目录路径"}

            resolved = os.path.realpath(os.path.expanduser(path.strip()))
            if not resolved:
                return {"status": "error", "message": "无效的目录路径"}
            if os.path.exists(resolved) and not os.path.isdir(resolved):
                return {"status": "error", "message": "目标路径不是文件夹"}

            os.makedirs(resolved, exist_ok=True)
            self.downloads_dir = resolved
            await server_manager.save_settings(self)
            return {"status": "success", "path": self.downloads_dir}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    # ------------------------- 天翼业务接口 -------------------------

    def _get_tianyi_service(self) -> TianyiService:
        """获取已初始化的天翼服务实例。"""
        if self.tianyi_service is None:
            raise RuntimeError("天翼服务未初始化")
        return self.tianyi_service

    async def get_tianyi_panel_state(
        self,
        payload=None,
        poll_mode: str = "",
        visible: bool = True,
        has_focus: bool = True,
    ) -> dict:
        """Decky 主面板状态。"""
        try:
            request_context = {}
            if isinstance(payload, dict):
                request_context.update(payload)
            if poll_mode and "poll_mode" not in request_context:
                request_context["poll_mode"] = poll_mode
            if "visible" not in request_context:
                request_context["visible"] = bool(visible)
            if "has_focus" not in request_context:
                request_context["has_focus"] = bool(has_focus)
            data = await self._get_tianyi_service().get_panel_state(request_context=request_context)
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def get_tianyi_library_url(self) -> dict:
        """本地游戏库页面地址。"""
        try:
            url = await self._get_tianyi_service().get_library_url()
            return {"status": "success", "url": url}
        except LocalWebNotReadyError as exc:
            return {
                "status": "error",
                "message": str(exc),
                "url": "",
                "reason": exc.reason,
                "diagnostics": exc.diagnostics,
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc), "url": ""}

    async def get_tianyi_login_url(self) -> dict:
        """天翼登录页地址。"""
        try:
            url = await self._get_tianyi_service().get_login_url()
            return {"status": "success", "url": url}
        except LocalWebNotReadyError as exc:
            return {
                "status": "error",
                "message": str(exc),
                "url": "",
                "reason": exc.reason,
                "diagnostics": exc.diagnostics,
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc), "url": ""}

    async def clear_tianyi_login(self) -> dict:
        """清理天翼登录态。"""
        try:
            data = await self._get_tianyi_service().clear_login()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def start_baidu_qr_login(self) -> dict:
        """百度网页版扫码登录：获取二维码。"""
        try:
            data = await self._get_tianyi_service().start_baidu_qr_login()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def poll_baidu_qr_login(self) -> dict:
        """轮询百度扫码状态。"""
        try:
            data = await self._get_tianyi_service().poll_baidu_qr_login()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def cancel_baidu_qr_login(self) -> dict:
        try:
            data = await self._get_tianyi_service().cancel_baidu_qr_login()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def clear_baidu_login(self) -> dict:
        try:
            data = await self._get_tianyi_service().clear_baidu_login()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def get_baidu_openapi_authorize_url(self) -> dict:
        """百度网盘开放平台授权链接。"""
        try:
            data = await self._get_tianyi_service().get_baidu_openapi_authorize_url()
            return {"status": "success", "url": str(data.get("url", "") or ""), "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "url": "", "data": {}}

    async def set_baidu_openapi_app(
        self,
        payload=None,
        app_key: str = "",
        secret_key: str = "",
    ) -> dict:
        """保存百度开放平台 App Key/Secret Key。"""
        try:
            if isinstance(payload, dict):
                app_key = str(payload.get("app_key", app_key) or "")
                secret_key = str(payload.get("secret_key", secret_key) or "")
            data = await self._get_tianyi_service().set_baidu_openapi_app(app_key, secret_key)
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def exchange_baidu_openapi_code(self, payload=None, code: str = "") -> dict:
        """用授权码换取百度 OpenAPI token。"""
        try:
            if isinstance(payload, dict):
                code = str(payload.get("code", code) or "")
            data = await self._get_tianyi_service().exchange_baidu_openapi_code(code)
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def clear_baidu_openapi_login(self) -> dict:
        """清除百度 OpenAPI 授权。"""
        try:
            data = await self._get_tianyi_service().clear_baidu_openapi_login()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def set_tianyi_settings(
        self,
        payload=None,
        download_dir: str = "",
        install_dir: str = "",
        split_count: int = 16,
        page_size: int = 50,
        auto_delete_package: bool = False,
        auto_install: bool = True,
        proton_tool: str = "auto",
        cloud_save_auto_upload: bool = True,
        cloud_save_include_emulators: bool = True,
    ) -> dict:
        """保存天翼下载设置。"""
        try:
            if isinstance(payload, dict):
                download_dir = str(payload.get("download_dir", download_dir))
                install_dir = str(payload.get("install_dir", install_dir))
                split_count = int(payload.get("split_count", split_count))
                page_size = int(payload.get("page_size", page_size))
                auto_delete_package = bool(payload.get("auto_delete_package", auto_delete_package))
                auto_install = bool(payload.get("auto_install", auto_install))
                proton_tool = str(payload.get("proton_tool", proton_tool))
                cloud_save_auto_upload = bool(payload.get("cloud_save_auto_upload", cloud_save_auto_upload))
                cloud_save_include_emulators = bool(payload.get("cloud_save_include_emulators", cloud_save_include_emulators))
            elif isinstance(payload, str) and not download_dir:
                download_dir = payload

            data = await self._get_tianyi_service().update_settings(
                download_dir=download_dir,
                install_dir=install_dir,
                split_count=split_count,
                page_size=page_size,
                auto_delete_package=auto_delete_package,
                auto_install=auto_install,
                proton_tool=proton_tool,
                cloud_save_auto_upload=cloud_save_auto_upload,
                cloud_save_include_emulators=cloud_save_include_emulators,
            )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def get_tianyi_storage_options(self) -> dict:
        """下载/安装目录可选的存储位置（内置 + SD 卡）。"""
        try:
            data = await self._get_tianyi_service().get_storage_options()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def run_tianyi_diagnostics(self) -> dict:
        """运行插件自检（网络/运行时/Steam/百度扫码等）。"""
        try:
            data = await self._get_tianyi_service().run_diagnostics(include_network=True)
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def export_tianyi_diagnostics_file(self) -> dict:
        """把诊断包写到下载目录。"""
        try:
            data = await self._get_tianyi_service().export_diagnostics_to_downloads()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def list_tianyi_catalog(self, payload=None, query: str = "", page: int = 1, page_size: int = 20, platform: str = "", category: str = "", sort: str = "") -> dict:
        """原生 QAM 游戏库：分页查询目录。"""
        try:
            if isinstance(payload, dict):
                query = str(payload.get("query", query) or "")
                page = int(payload.get("page", page) or 1)
                page_size = int(payload.get("page_size", page_size) or 20)
                platform = str(payload.get("platform", platform) or "")
                category = str(payload.get("category", category) or "")
                sort = str(payload.get("sort", sort) or "")
            data = await self._get_tianyi_service().list_catalog(
                query=query,
                page=max(1, page),
                page_size=max(1, min(100, page_size)),
                platform=platform,
                category=category,
                sort=sort,
            )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def prepare_tianyi_install(self, payload=None, game_id: str = "", share_url: str = "", file_ids=None) -> dict:
        """原生 QAM：生成安装确认数据。"""
        try:
            if isinstance(payload, dict):
                game_id = str(payload.get("game_id", game_id) or "")
                share_url = str(payload.get("share_url", share_url) or "")
            data = await self._get_tianyi_service().prepare_install(
                game_id=game_id,
                share_url=share_url,
                file_ids=list(file_ids or []),
            )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def start_tianyi_install(self, payload=None, game_id: str = "", share_url: str = "", file_ids=None) -> dict:
        """原生 QAM：确认后开始下载/安装。"""
        try:
            if isinstance(payload, dict):
                game_id = str(payload.get("game_id", game_id) or "")
                share_url = str(payload.get("share_url", share_url) or "")
            data = await self._get_tianyi_service().start_install(
                game_id=game_id,
                share_url=share_url,
                file_ids=list(file_ids or []),
            )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def list_tianyi_installed_games(self) -> dict:
        """原生 QAM：已安装列表。"""
        try:
            data = await self._get_tianyi_service().list_installed_games()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def launch_tianyi_installed_game(self, game_id: str = "") -> dict:
        try:
            data = await self._get_tianyi_service().launch_installed_game(game_id)
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def open_tianyi_installed_folder(self, game_id: str = "") -> dict:
        try:
            data = await self._get_tianyi_service().open_installed_folder(game_id)
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def scan_tianyi_installed_games(self) -> dict:
        """扫描安装目录，补回已安装游戏。"""
        try:
            data = await self._get_tianyi_service().scan_installed_games()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def uninstall_tianyi_installed_game(
        self,
        payload=None,
        game_id: str = "",
        install_path: str = "",
        delete_files: bool = True,
        delete_compatdata: bool = False,
    ) -> dict:
        """卸载已安装游戏并移除记录（可选回收 Proton 前缀）。"""
        try:
            if isinstance(payload, dict):
                game_id = str(payload.get("game_id", game_id))
                install_path = str(payload.get("install_path", install_path))
                if "delete_files" in payload:
                    delete_files = bool(payload.get("delete_files"))
                if "delete_compatdata" in payload:
                    delete_compatdata = bool(payload.get("delete_compatdata"))
            data = await self._get_tianyi_service().uninstall_installed_game(
                game_id=game_id,
                install_path=install_path,
                delete_files=delete_files,
                delete_compatdata=delete_compatdata,
            )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def pause_tianyi_task(self, payload=None, task_id: str = "") -> dict:
        """暂停下载任务。"""
        try:
            if isinstance(payload, dict):
                task_id = str(payload.get("task_id", task_id))
            data = await self._get_tianyi_service().pause_task(task_id)
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def resume_tianyi_task(self, payload=None, task_id: str = "") -> dict:
        """继续下载任务。"""
        try:
            if isinstance(payload, dict):
                task_id = str(payload.get("task_id", task_id))
            data = await self._get_tianyi_service().resume_task(task_id)
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def retry_tianyi_task(self, payload=None, task_id: str = "") -> dict:
        """重试失败/中断的下载任务。"""
        try:
            if isinstance(payload, dict):
                task_id = str(payload.get("task_id", task_id))
            data = await self._get_tianyi_service().retry_task(task_id)
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def preview_tianyi_uninstall(self, payload=None, game_id: str = "", install_path: str = "") -> dict:
        """卸载前预览安装目录 / Proton 前缀占用。"""
        try:
            if isinstance(payload, dict):
                game_id = str(payload.get("game_id", game_id))
                install_path = str(payload.get("install_path", install_path))
            data = await self._get_tianyi_service().preview_uninstall(
                game_id=game_id,
                install_path=install_path,
            )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def remove_tianyi_task(self, payload=None, task_id: str = "") -> dict:
        """移除下载任务（不删除已下载文件）。"""
        try:
            if isinstance(payload, dict):
                task_id = str(payload.get("task_id", task_id))
            data = await self._get_tianyi_service().remove_task(task_id)
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def start_tianyi_cloud_save_upload(self) -> dict:
        """启动云存档上传任务。"""
        try:
            data = await self._get_tianyi_service().start_cloud_save_upload()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def get_tianyi_cloud_save_upload_status(self) -> dict:
        """获取云存档上传任务状态。"""
        try:
            data = await self._get_tianyi_service().get_cloud_save_upload_status()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def list_tianyi_cloud_save_restore_options(self) -> dict:
        """列出可恢复云存档版本。"""
        try:
            data = await self._get_tianyi_service().list_cloud_save_restore_options()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def list_tianyi_cloud_save_restore_entries(
        self,
        payload=None,
        game_id: str = "",
        game_key: str = "",
        game_title: str = "",
        version_name: str = "",
    ) -> dict:
        """读取指定版本可选存档项。"""
        try:
            if isinstance(payload, dict):
                game_id = str(payload.get("game_id", game_id))
                game_key = str(payload.get("game_key", game_key))
                game_title = str(payload.get("game_title", game_title))
                version_name = str(payload.get("version_name", version_name))
            data = await self._get_tianyi_service().list_cloud_save_restore_entries(
                game_id=game_id,
                game_key=game_key,
                game_title=game_title,
                version_name=version_name,
            )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def plan_tianyi_cloud_save_restore(
        self,
        payload=None,
        game_id: str = "",
        game_key: str = "",
        game_title: str = "",
        version_name: str = "",
        selected_entry_ids=None,
        target_dir: str = "",
    ) -> dict:
        """生成云存档恢复计划（冲突探测）。"""
        try:
            if isinstance(payload, dict):
                game_id = str(payload.get("game_id", game_id))
                game_key = str(payload.get("game_key", game_key))
                game_title = str(payload.get("game_title", game_title))
                version_name = str(payload.get("version_name", version_name))
                target_dir = str(payload.get("target_dir", target_dir))
                selected_entry_ids = payload.get("selected_entry_ids", selected_entry_ids)
            rows = selected_entry_ids if isinstance(selected_entry_ids, list) else []
            data = await self._get_tianyi_service().plan_cloud_save_restore(
                game_id=game_id,
                game_key=game_key,
                game_title=game_title,
                version_name=version_name,
                selected_entry_ids=[str(item) for item in rows if str(item).strip()],
                target_dir=target_dir,
            )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def apply_tianyi_cloud_save_restore(
        self,
        payload=None,
        plan_id: str = "",
        confirm_overwrite: bool = False,
    ) -> dict:
        """执行云存档恢复计划。"""
        try:
            if isinstance(payload, dict):
                plan_id = str(payload.get("plan_id", plan_id))
                confirm_overwrite = bool(payload.get("confirm_overwrite", confirm_overwrite))
            data = await self._get_tianyi_service().apply_cloud_save_restore(
                plan_id=plan_id,
                confirm_overwrite=confirm_overwrite,
            )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def get_tianyi_cloud_save_restore_status(self) -> dict:
        """获取云存档恢复任务状态。"""
        try:
            data = await self._get_tianyi_service().get_cloud_save_restore_status()
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def record_tianyi_game_action(
        self,
        payload=None,
        phase: str = "",
        app_id: str = "",
        action_name: str = "",
    ) -> dict:
        """记录 Steam 游戏启动/退出事件（用于游玩时长统计）。"""
        try:
            if isinstance(payload, dict):
                phase = str(payload.get("phase", phase))
                app_id = str(payload.get("app_id", app_id))
                action_name = str(payload.get("action_name", action_name))
            data = await self._get_tianyi_service().record_game_action(
                phase=phase,
                app_id=app_id,
                action_name=action_name,
            )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

    async def get_tianyi_library_game_time_stats(
        self,
        payload=None,
        app_id: str = "",
        title: str = "",
    ) -> dict:
        """获取 Steam 库页面游戏时长（我的游玩/主线/总时长）。"""
        try:
            if isinstance(payload, dict):
                app_id = str(payload.get("app_id", app_id))
                title = str(payload.get("title", title))
            data = await self._get_tianyi_service().get_library_game_time_stats(
                app_id=app_id,
                title=title,
            )
            return {"status": "success", "data": data}
        except Exception as exc:
            return {"status": "error", "message": str(exc), "data": {}}

// @ts-nocheck
import * as SP_REACT from "react";
import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { hasLanguage, setLanguage, translateString, useI18nRoot, useLanguage } from "./i18n";
const SP_JSX = { jsx: _jsx, jsxs: _jsxs, Fragment: _Fragment };
const manifest = {"name":"freedeckCY"};
const API_VERSION = 2;
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
if (!internalAPIConnection) {
    throw new Error('[@decky/api]: Failed to connect to the loader as as the loader API was not initialized. This is likely a bug in Decky Loader.');
}
let api;
try {
    api = internalAPIConnection.connect(API_VERSION, manifest.name);
}
catch {
    api = internalAPIConnection.connect(1, manifest.name);
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version 1. Some features may not work.`);
}
if (api._version != API_VERSION) {
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version ${api._version}. Some features may not work.`);
}
const callable = api.callable;
const routerHook = api.routerHook;
const toaster = {
    toast(options) {
        const next = Object.assign({}, options || {});
        next.title = translateString(String(next.title || ""));
        next.body = translateString(String(next.body || ""));
        return api.toaster.toast(next);
    },
};
const openFilePicker = api.openFilePicker;
const definePlugin = (fn) => {
    return (...args) => {
        return fn(...args);
    };
};

var DefaultContext = {
  color: undefined,
  size: undefined,
  className: undefined,
  style: undefined,
  attr: undefined
};
var IconContext = SP_REACT.createContext && /*#__PURE__*/SP_REACT.createContext(DefaultContext);

var _excluded = ["attr", "size", "title"];
function _objectWithoutProperties(source, excluded) { if (source == null) return {}; var target = _objectWithoutPropertiesLoose(source, excluded); var key, i; if (Object.getOwnPropertySymbols) { var sourceSymbolKeys = Object.getOwnPropertySymbols(source); for (i = 0; i < sourceSymbolKeys.length; i++) { key = sourceSymbolKeys[i]; if (excluded.indexOf(key) >= 0) continue; if (!Object.prototype.propertyIsEnumerable.call(source, key)) continue; target[key] = source[key]; } } return target; }
function _objectWithoutPropertiesLoose(source, excluded) { if (source == null) return {}; var target = {}; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { if (excluded.indexOf(key) >= 0) continue; target[key] = source[key]; } } return target; }
function _extends() { _extends = Object.assign ? Object.assign.bind() : function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; }; return _extends.apply(this, arguments); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), true).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(obj, key, value) { key = _toPropertyKey(key); if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == typeof i ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != typeof t || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r); if ("object" != typeof i) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
function Tree2Element(tree) {
  return tree && tree.map((node, i) => /*#__PURE__*/SP_REACT.createElement(node.tag, _objectSpread({
    key: i
  }, node.attr), Tree2Element(node.child)));
}
function GenIcon(data) {
  return props => /*#__PURE__*/SP_REACT.createElement(IconBase, _extends({
    attr: _objectSpread({}, data.attr)
  }, props), Tree2Element(data.child));
}
function IconBase(props) {
  var elem = conf => {
    var {
        attr,
        size,
        title
      } = props,
      svgProps = _objectWithoutProperties(props, _excluded);
    var computedSize = size || conf.size || "1em";
    var className;
    if (conf.className) className = conf.className;
    if (props.className) className = (className ? className + " " : "") + props.className;
    return /*#__PURE__*/SP_REACT.createElement("svg", _extends({
      stroke: "currentColor",
      fill: "currentColor",
      strokeWidth: "0"
    }, conf.attr, attr, svgProps, {
      className: className,
      style: _objectSpread(_objectSpread({
        color: props.color || conf.color
      }, conf.style), props.style),
      height: computedSize,
      width: computedSize,
      xmlns: "http://www.w3.org/2000/svg"
    }), title && /*#__PURE__*/SP_REACT.createElement("title", null, title), props.children);
  };
  return IconContext !== undefined ? /*#__PURE__*/SP_REACT.createElement(IconContext.Consumer, null, conf => elem(conf)) : elem(DefaultContext);
}

// THIS FILE IS AUTO GENERATED
function FaCloudDownloadAlt (props) {
  return GenIcon({"attr":{"viewBox":"0 0 640 512"},"child":[{"tag":"path","attr":{"d":"M537.6 226.6c4.1-10.7 6.4-22.4 6.4-34.6 0-53-43-96-96-96-19.7 0-38.1 6-53.3 16.2C367 64.2 315.3 32 256 32c-88.4 0-160 71.6-160 160 0 2.7.1 5.4.2 8.1C40.2 219.8 0 273.2 0 336c0 79.5 64.5 144 144 144h368c70.7 0 128-57.3 128-128 0-61.9-44-113.6-102.4-125.4zm-132.9 88.7L299.3 420.7c-6.2 6.2-16.4 6.2-22.6 0L171.3 315.3c-10.1-10.1-2.9-27.3 11.3-27.3H248V176c0-8.8 7.2-16 16-16h48c8.8 0 16 7.2 16 16v112h65.4c14.2 0 21.4 17.2 11.3 27.3z"},"child":[]}]})(props);
}

const SETTINGS_ROUTE = "/freedeckcy/settings";
const LIBRARY_ROUTE = "/freedeckcy/library";
const getTianyiPanelState = callable("get_tianyi_panel_state");
const restartSteamBackend = callable("restart_steam");
const clearSteamRestartPending = callable("clear_steam_restart_pending");
const clearTianyiCatalogUpdateNotice = callable("clear_tianyi_catalog_update_notice");
const getTianyiStorageOptions = callable("get_tianyi_storage_options");
const scanTianyiStorageCleanup = callable("scan_tianyi_storage_cleanup");
const cleanTianyiStorageCleanup = callable("clean_tianyi_storage_cleanup");
const listTianyiCatalog = callable("list_tianyi_catalog");
const refreshTianyiCatalog = callable("refresh_tianyi_catalog");
const updateTianyiCatalog = callable("update_tianyi_catalog");
const prepareTianyiInstall = callable("prepare_tianyi_install");
const startTianyiInstall = callable("start_tianyi_install");
const listTianyiInstalledGames = callable("list_tianyi_installed_games");
const getTianyiInstalledHealth = callable("get_tianyi_installed_health");
const preflightTianyiInstall = callable("preflight_tianyi_install");
const launchTianyiInstalledGame = callable("launch_tianyi_installed_game");
const openTianyiInstalledFolder = callable("open_tianyi_installed_folder");
const repairTianyiInstalledGame = callable("repair_tianyi_installed_game");
const reinstallTianyiInstalledGame = callable("reinstall_tianyi_installed_game");
const reinstallTianyiInstalledGames = callable("reinstall_tianyi_installed_games");
const verifyTianyiInstalledGame = callable("verify_tianyi_installed_game");
const scanTianyiInstalledGames = callable("scan_tianyi_installed_games");
const runTianyiDiagnostics = callable("run_tianyi_diagnostics");
const checkTianyiUpdate = callable("check_tianyi_update");
const downloadTianyiUpdate = callable("download_tianyi_update");
const prepareTianyiUpdateInstall = callable("prepare_tianyi_update_install");
const exportTianyiDiagnosticsFile = callable("export_tianyi_diagnostics_file");
const uninstallTianyiInstalled = callable("uninstall_tianyi_installed_game");
const getTianyiLoginUrl = callable("get_tianyi_login_url");
const setTianyiSettings = callable("set_tianyi_settings");
const clearTianyiLogin = callable("clear_tianyi_login");
const startBaiduQrLogin = callable("start_baidu_qr_login");
const pollBaiduQrLogin = callable("poll_baidu_qr_login");
const cancelBaiduQrLogin = callable("cancel_baidu_qr_login");
const clearBaiduLogin = callable("clear_baidu_login");
const checkBaiduWebHealth = callable("check_baidu_web_health");
const getBaiduOpenapiAuthorizeUrl = callable("get_baidu_openapi_authorize_url");
const setBaiduOpenapiApp = callable("set_baidu_openapi_app");
const exchangeBaiduOpenapiCode = callable("exchange_baidu_openapi_code");
const clearBaiduOpenapiLogin = callable("clear_baidu_openapi_login");
const startTianyiCloudSaveUpload = callable("start_tianyi_cloud_save_upload");
const getTianyiCloudSaveUploadStatus = callable("get_tianyi_cloud_save_upload_status");
const listTianyiCloudSaveRestoreOptions = callable("list_tianyi_cloud_save_restore_options");
const listTianyiCloudSaveRestoreEntries = callable("list_tianyi_cloud_save_restore_entries");
const planTianyiCloudSaveRestore = callable("plan_tianyi_cloud_save_restore");
const applyTianyiCloudSaveRestore = callable("apply_tianyi_cloud_save_restore");
const getTianyiCloudSaveRestoreStatus = callable("get_tianyi_cloud_save_restore_status");
const recordTianyiGameAction = callable("record_tianyi_game_action");
const getTianyiLibraryGameTimeStats = callable("get_tianyi_library_game_time_stats");
const getTianyiCatalogUpdate = callable("get_tianyi_catalog_update");
const getTianyiCoverProxyBase = callable("get_tianyi_cover_proxy_base");
const pauseAllTianyiTasks = callable("pause_all_tianyi_tasks");
const resumeAllTianyiTasks = callable("resume_all_tianyi_tasks");
const retryAllTianyiTasks = callable("retry_all_tianyi_tasks");
const setTianyiSpeedLimit = callable("set_tianyi_speed_limit");
const pauseTianyiTask = callable("pause_tianyi_task");
const resumeTianyiTask = callable("resume_tianyi_task");
const removeTianyiTask = callable("remove_tianyi_task");
const retryTianyiTask = callable("retry_tianyi_task");
const retryTianyiTaskWithFallback = callable("retry_tianyi_task_with_fallback");
const diagnoseTianyiTask = callable("diagnose_tianyi_task");
const previewTianyiUninstall = callable("preview_tianyi_uninstall");
const uninstallTianyiInstalledGame = callable("uninstall_tianyi_installed_game");
const PANEL_REQUEST_TIMEOUT_MS = 6000;
const PANEL_POLL_MODE_ACTIVE = "active";
const PANEL_POLL_MODE_IDLE = "idle";
const PANEL_POLL_MODE_BACKGROUND = "background";
const PANEL_ACTIVE_POLL_MS = 900;
const PANEL_IDLE_POLL_MS = 6000;
const PANEL_BACKGROUND_POLL_MS = 30000;
const EMPTY_SETTINGS = {
    download_dir: "",
    install_dir: "",
    split_count: 16,
    page_size: 50,
    auto_delete_package: false,
    auto_install: true,
    cloud_save_auto_upload: true,
    cloud_save_include_emulators: true,
    catalog_url: "",
};
const EMPTY_CLOUD_SAVE_STATE = {
    stage: "idle",
    message: "未开始",
    reason: "",
    running: false,
    progress: 0,
    current_game: "",
    total_games: 0,
    processed_games: 0,
    uploaded: 0,
    skipped: 0,
    failed: 0,
    results: [],
    last_result: {
        stage: "",
        reason: "",
        message: "",
        started_at: 0,
        finished_at: 0,
        timestamp: "",
        total_games: 0,
        processed_games: 0,
        uploaded: 0,
        skipped: 0,
        failed: 0,
        results: [],
    },
};
const EMPTY_CLOUD_SAVE_RESTORE_STATE = {
    stage: "idle",
    message: "未开始",
    reason: "",
    running: false,
    progress: 0,
    target_game_id: "",
    target_game_title: "",
    target_game_key: "",
    target_version: "",
    selected_entry_ids: [],
    selected_target_dir: "",
    requires_confirmation: false,
    conflict_count: 0,
    conflict_samples: [],
    restored_files: 0,
    restored_entries: 0,
    results: [],
    last_result: {
        status: "",
        reason: "",
        message: "",
        target_dir: "",
        restored_files: 0,
        restored_entries: 0,
        conflicts_overwritten: 0,
        results: [],
    },
};
const PAGE_SIZE_OPTIONS = [20, 30, 50, 80, 100, 150, 200].map((value) => ({
    data: value,
    label: `${value} / 页`,
}));
const EMPTY_BAIDU_OPENAPI_STATE = {
    configured: false,
    logged_in: false,
    user_account: "",
    expires_at: 0,
    message: "未配置",
};
const EMPTY_BAIDU_WEB_STATE = {
    logged_in: false,
    user_account: "",
    message: "未登录",
};
const EMPTY_STATE = {
    login: { logged_in: false, user_account: "", message: "" },
    baidu_login: EMPTY_BAIDU_WEB_STATE,
    baidu_openapi_login: EMPTY_BAIDU_OPENAPI_STATE,
    installed: { total: 0, preview: [] },
    tasks: [],
    settings: EMPTY_SETTINGS,
    library_url: "",
    steam_restart: { pending: false },
    catalog_update_notice: {},
};
function getGamepadTabClassMap() {
    const map = DFL.gamepadTabbedPageClasses;
    if (!map || typeof map !== "object")
        return null;
    return map;
}
function formatSpeed(speed) {
    let value = Number(speed || 0);
    if (!Number.isFinite(value) || value <= 0)
        return "0 B/s";
    const units = ["B/s", "KB/s", "MB/s", "GB/s"];
    let index = 0;
    while (value >= 1024 && index < units.length - 1) {
        value /= 1024;
        index += 1;
    }
    return `${value.toFixed(index === 0 ? 0 : 2)} ${units[index]}`;
}
function formatBytesText(size) {
    let value = Number(size || 0);
    if (!Number.isFinite(value) || value <= 0)
        return "0 B";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let index = 0;
    while (value >= 1024 && index < units.length - 1) {
        value /= 1024;
        index += 1;
    }
    return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}
function formatPlaytimeText(seconds, fallback) {
    const fallbackText = String(fallback || "").trim();
    if (fallbackText)
        return fallbackText;
    const totalSeconds = Math.max(0, Number(seconds || 0));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    if (hours > 0)
        return `${hours} 小时 ${minutes} 分钟`;
    if (minutes > 0)
        return `${minutes} 分钟`;
    return "0 分钟";
}
function clampProgress(progress) {
    const value = Number(progress || 0);
    if (!Number.isFinite(value))
        return 0;
    if (value < 0)
        return 0;
    if (value > 100)
        return 100;
    return value;
}
function errorText(error) {
    if (error && typeof error === "object") {
        const message = String(error.message ?? "").trim();
        if (message)
            return message;
    }
    const text = String(error ?? "").trim();
    return text || "操作失败";
}
function toastError(error) {
    toaster.toast({ title: "freedeckCY", body: errorText(error) });
}
function downloadStatusText(status) {
    const value = String(status || "").toLowerCase();
    if (value === "active")
        return "下载中";
    if (value === "waiting")
        return "等待中";
    if (value === "paused")
        return "已暂停";
    if (value === "complete")
        return "下载完成";
    if (value === "error")
        return "下载失败";
    if (value === "removed")
        return "已移除";
    return status || "未知";
}
function installStatusText(status) {
    const value = String(status || "").toLowerCase();
    if (value === "pending")
        return "待处理";
    if (value === "installing")
        return "安装中";
    if (value === "installed")
        return "已安装";
    if (value === "skipped")
        return "已跳过";
    if (value === "failed")
        return "安装失败";
    return status || "未开始";
}
function progressColors(task) {
    const downloadStatus = String(task.status || "").toLowerCase();
    const installStatus = String(task.install_status || "").toLowerCase();
    if (downloadStatus === "error" || installStatus === "failed") {
        return { track: "rgba(255, 87, 87, 0.2)", fill: "#ff5757", label: "#ffb2b2" };
    }
    if (downloadStatus === "complete" && installStatus === "installed") {
        return { track: "rgba(67, 181, 129, 0.2)", fill: "#43b581", label: "#b8f3d7" };
    }
    if (downloadStatus === "paused") {
        return { track: "rgba(255, 184, 64, 0.22)", fill: "#ffb840", label: "#ffe2a8" };
    }
    return { track: "rgba(208, 188, 255, 0.24)", fill: "#d0bcff", label: "#ece2ff" };
}
function TaskProgressRow(task) {
    const progress = clampProgress(task.progress);
    const colors = progressColors(task);
    const title = task.game_title || task.game_name || task.file_name || "未命名任务";
    const installStatus = String(task.install_status || "").trim();
    const installMessage = String(task.install_message || "").trim();
    const errorReason = String(task.error_reason || "").trim();
    return (SP_JSX.jsxs("div", { style: {
            width: "100%",
            padding: "8px 0",
            display: "flex",
            flexDirection: "column",
            gap: "6px",
        }, children: [SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }, children: [SP_JSX.jsx("div", { style: {
                            fontSize: "14px",
                            fontWeight: 600,
                            lineHeight: 1.35,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            maxWidth: "70%",
                        }, title: title, children: title }), SP_JSX.jsx("div", { style: { fontSize: "11px", color: colors.label }, children: downloadStatusText(task.status) })] }), SP_JSX.jsx("div", { style: {
                    width: "100%",
                    height: "8px",
                    borderRadius: "999px",
                    background: colors.track,
                    overflow: "hidden",
                }, children: SP_JSX.jsx("div", { style: {
                        width: `${progress.toFixed(1)}%`,
                        height: "100%",
                        borderRadius: "999px",
                        background: colors.fill,
                        transition: "width 860ms linear",
                    } }) }), SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", fontSize: "11px", color: "#c9c9c9" }, children: [SP_JSX.jsx("span", { children: `进度 ${progress.toFixed(1)}%` }), SP_JSX.jsx("span", { children: `速度 ${formatSpeed(task.speed)}` })] }), installStatus ? (SP_JSX.jsx("div", { style: { fontSize: "11px", color: "#bcbcbc", lineHeight: 1.4 }, children: `安装：${installStatusText(installStatus)}${installMessage ? ` | ${installMessage}` : ""}` })) : null, errorReason ? (SP_JSX.jsx("div", { style: { fontSize: "11px", color: "#ff8e8e", lineHeight: 1.4 }, children: `错误：${errorReason}` })) : null] }));
}
function getTextFieldValue(eventOrValue) {
    if (typeof eventOrValue === "string")
        return eventOrValue;
    if (eventOrValue && typeof eventOrValue === "object" && "target" in eventOrValue) {
        const target = eventOrValue.target;
        return String(target?.value ?? "");
    }
    return String(eventOrValue ?? "");
}
function openExternalUrl(rawUrl) {
    const url = String(rawUrl || "").trim();
    if (!url)
        return;
    try {
        DFL.Navigation.NavigateToExternalWeb(url);
        return;
    }
    catch {
        // 忽略并回退到备用跳转。
    }
    try {
        const steamClient = window.SteamClient;
        if (steamClient?.Browser?.OpenUrl) {
            steamClient.Browser.OpenUrl(url);
            return;
        }
    }
    catch {
        // 忽略并回退到 window.open。
    }
    const popup = window.open(url, "_blank");
    if (!popup)
        window.location.href = url;
}
function describeOpenError(result, fallback) {
    const message = String(result.message || fallback);
    const reason = String(result.reason || "").trim();
    if (!reason)
        return message;
    if (!result.diagnostics)
        return `${message}（${reason}）`;
    try {
        return `${message}（${reason}）\n${JSON.stringify(result.diagnostics)}`;
    }
    catch {
        return `${message}（${reason}）`;
    }
}
function toPayload(settings) {
    return {
        download_dir: String(settings.download_dir || ""),
        install_dir: String(settings.install_dir || ""),
        split_count: Math.max(1, Math.min(64, Number(settings.split_count || 16))),
        page_size: Math.max(10, Math.min(200, Number(settings.page_size || 50))),
        auto_delete_package: Boolean(settings.auto_delete_package),
        auto_install: true,
        cloud_save_auto_upload: Boolean(settings.cloud_save_auto_upload),
        cloud_save_include_emulators: Boolean(settings.cloud_save_include_emulators),
        catalog_url: String(settings.catalog_url || "").trim(),
    };
}
function normalizeCloudSaveUploadState(raw) {
    const source = raw || {};
    const lastRaw = source.last_result || EMPTY_CLOUD_SAVE_STATE.last_result;
    return {
        ...EMPTY_CLOUD_SAVE_STATE,
        ...source,
        stage: String(source.stage || "idle"),
        message: String(source.message || "未开始"),
        reason: String(source.reason || ""),
        running: Boolean(source.running),
        progress: clampProgress(Number(source.progress || 0)),
        current_game: String(source.current_game || ""),
        total_games: Math.max(0, Number(source.total_games || 0)),
        processed_games: Math.max(0, Number(source.processed_games || 0)),
        uploaded: Math.max(0, Number(source.uploaded || 0)),
        skipped: Math.max(0, Number(source.skipped || 0)),
        failed: Math.max(0, Number(source.failed || 0)),
        results: Array.isArray(source.results) ? source.results : [],
        last_result: {
            ...EMPTY_CLOUD_SAVE_STATE.last_result,
            ...lastRaw,
            stage: String(lastRaw.stage || ""),
            reason: String(lastRaw.reason || ""),
            message: String(lastRaw.message || ""),
            timestamp: String(lastRaw.timestamp || ""),
            started_at: Math.max(0, Number(lastRaw.started_at || 0)),
            finished_at: Math.max(0, Number(lastRaw.finished_at || 0)),
            total_games: Math.max(0, Number(lastRaw.total_games || 0)),
            processed_games: Math.max(0, Number(lastRaw.processed_games || 0)),
            uploaded: Math.max(0, Number(lastRaw.uploaded || 0)),
            skipped: Math.max(0, Number(lastRaw.skipped || 0)),
            failed: Math.max(0, Number(lastRaw.failed || 0)),
            results: Array.isArray(lastRaw.results) ? lastRaw.results : [],
        },
    };
}
function normalizeCloudSaveRestoreState(raw) {
    const source = raw || {};
    const lastRaw = source.last_result || EMPTY_CLOUD_SAVE_RESTORE_STATE.last_result;
    return {
        ...EMPTY_CLOUD_SAVE_RESTORE_STATE,
        ...source,
        stage: String(source.stage || "idle"),
        message: String(source.message || "未开始"),
        reason: String(source.reason || ""),
        running: Boolean(source.running),
        progress: clampProgress(Number(source.progress || 0)),
        target_game_id: String(source.target_game_id || ""),
        target_game_title: String(source.target_game_title || ""),
        target_game_key: String(source.target_game_key || ""),
        target_version: String(source.target_version || ""),
        selected_entry_ids: Array.isArray(source.selected_entry_ids) ? source.selected_entry_ids : [],
        selected_target_dir: String(source.selected_target_dir || ""),
        requires_confirmation: Boolean(source.requires_confirmation),
        conflict_count: Math.max(0, Number(source.conflict_count || 0)),
        conflict_samples: Array.isArray(source.conflict_samples) ? source.conflict_samples : [],
        restored_files: Math.max(0, Number(source.restored_files || 0)),
        restored_entries: Math.max(0, Number(source.restored_entries || 0)),
        results: Array.isArray(source.results) ? source.results : [],
        last_result: {
            ...EMPTY_CLOUD_SAVE_RESTORE_STATE.last_result,
            ...lastRaw,
            status: String(lastRaw.status || ""),
            reason: String(lastRaw.reason || ""),
            message: String(lastRaw.message || ""),
            target_dir: String(lastRaw.target_dir || ""),
            restored_files: Math.max(0, Number(lastRaw.restored_files || 0)),
            restored_entries: Math.max(0, Number(lastRaw.restored_entries || 0)),
            conflicts_overwritten: Math.max(0, Number(lastRaw.conflicts_overwritten || 0)),
            results: Array.isArray(lastRaw.results) ? lastRaw.results : [],
        },
    };
}
function formatBytes(value) {
    let size = Number(value || 0);
    if (!Number.isFinite(size) || size <= 0)
        return "0 B";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let index = 0;
    while (size >= 1024 && index < units.length - 1) {
        size /= 1024;
        index += 1;
    }
    return `${size.toFixed(index === 0 ? 0 : 2)} ${units[index]}`;
}
function cloudSaveStageText(stage) {
    const value = String(stage || "").trim().toLowerCase();
    if (value === "listing")
        return "拉取版本中";
    if (value === "planning")
        return "规划中";
    if (value === "ready")
        return "待确认";
    if (value === "applying")
        return "恢复中";
    if (value === "scanning")
        return "扫描中";
    if (value === "packaging")
        return "打包中";
    if (value === "uploading")
        return "上传中";
    if (value === "completed")
        return "已完成";
    if (value === "failed")
        return "失败";
    return "空闲";
}
const LIBRARY_TIME_CACHE_TTL_MS = 5 * 60 * 1000;
const LIBRARY_TIME_NEGATIVE_CACHE_TTL_MS = 3 * 1000;
const LIBRARY_TIME_RETRY_MS = 3 * 1000;
const LIBRARY_TIME_REFRESH_MS = 2 * 60 * 1000;
const libraryTimeCache = new Map();
function parseGameActionAppIdCandidate(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
        return Math.max(0, Math.trunc(value));
    }
    if (typeof value === "string") {
        const text = value.trim();
        if (/^\d+$/.test(text)) {
            return Math.max(0, Number.parseInt(text, 10));
        }
        return 0;
    }
    if (!value || typeof value !== "object") {
        return 0;
    }
    const obj = value;
    const keys = ["app_id", "appid", "appId", "unAppID", "nAppID", "m_unAppID", "m_nAppID"];
    for (const key of keys) {
        const parsed = parseGameActionAppIdCandidate(obj[key]);
        if (parsed > 0)
            return parsed;
    }
    return 0;
}
function resolveGameActionAppId(args) {
    const ordered = [args[1], args[0], args[2], ...args];
    for (const value of ordered) {
        const parsed = parseGameActionAppIdCandidate(value);
        if (parsed > 0)
            return String(parsed);
    }
    return "";
}
function invalidateLibraryTimeCacheByAppId(appId) {
    const prefix = `${String(appId || "").trim()}::`;
    if (!prefix || prefix === "::")
        return;
    for (const key of Array.from(libraryTimeCache.keys())) {
        if (key.startsWith(prefix)) {
            libraryTimeCache.delete(key);
        }
    }
}
function resolveSteamAppsGameActionApi() {
    if (typeof window === "undefined")
        return null;
    const apps = window.SteamClient?.Apps;
    if (!apps || typeof apps !== "object")
        return null;
    return apps;
}
function installGlobalGameActionReporter() {
    let disposed = false;
    let retryTimer = null;
    let teardownListener = null;
    const clearRetry = () => {
        if (retryTimer === null)
            return;
        if (typeof window !== "undefined") {
            window.clearTimeout(retryTimer);
        }
        retryTimer = null;
    };
    const scheduleRetry = () => {
        if (disposed || retryTimer !== null || typeof window === "undefined")
            return;
        retryTimer = window.setTimeout(() => {
            retryTimer = null;
            tryInstall();
        }, 1500);
    };
    const tryInstall = () => {
        if (disposed || teardownListener)
            return;
        let apps = null;
        try {
            apps = resolveSteamAppsGameActionApi();
        }
        catch {
            scheduleRetry();
            return;
        }
        const registerStart = apps?.RegisterForGameActionStart;
        const registerEnd = apps?.RegisterForGameActionEnd;
        if (typeof registerStart !== "function" || typeof registerEnd !== "function") {
            scheduleRetry();
            return;
        }
        const activeAppIds = new Set();
        const reportAction = (phase, args) => {
            const appId = resolveGameActionAppId(args);
            if (!appId)
                return;
            if (phase === "start") {
                if (activeAppIds.has(appId))
                    return;
                activeAppIds.add(appId);
            }
            else {
                activeAppIds.delete(appId);
            }
            invalidateLibraryTimeCacheByAppId(appId);
            void recordTianyiGameAction({
                phase,
                app_id: appId,
                action_name: "",
            }).catch(() => {
                // 忽略事件上报失败，避免影响主流程。
            });
        };
        let startListener;
        let endListener;
        try {
            startListener = registerStart((...args) => {
                reportAction("start", args);
            });
            endListener = registerEnd((...args) => {
                reportAction("end", args);
            });
        }
        catch {
            scheduleRetry();
            return;
        }
        teardownListener = () => {
            activeAppIds.clear();
            try {
                startListener?.unregister?.();
            }
            catch {
                // 忽略反注册异常。
            }
            try {
                endListener?.unregister?.();
            }
            catch {
                // 忽略反注册异常。
            }
        };
    };
    tryInstall();
    return () => {
        disposed = true;
        clearRetry();
        if (teardownListener) {
            teardownListener();
            teardownListener = null;
        }
    };
}
function hasPositiveLibraryHltb(payload) {
    if (!payload)
        return false;
    const main = Number(payload.main_story_hours || 0);
    const total = Number(payload.total_hours || 0);
    return (Number.isFinite(main) && main > 0) || (Number.isFinite(total) && total > 0);
}
function normalizeHoursText(hoursRaw, fallbackRaw) {
    const fallback = String(fallbackRaw || "").trim();
    if (fallback)
        return fallback;
    const hours = Number(hoursRaw || 0);
    if (!Number.isFinite(hours) || hours <= 0)
        return "-";
    const rounded = Math.round(hours * 10) / 10;
    if (Math.abs(rounded - Math.round(rounded)) < 0.05) {
        return `${Math.round(rounded)} 小时`;
    }
    return `${rounded.toFixed(1)} 小时`;
}
function wrapReactType(node, prop = "type") {
    if (!node || typeof node !== "object")
        return null;
    const owner = node;
    const current = owner[prop];
    if (!current || typeof current !== "object")
        return null;
    const currentMap = current;
    if (Boolean(currentMap.__FREDECK_WRAPPED))
        return currentMap;
    const wrapped = { ...currentMap, __FREDECK_WRAPPED: true };
    owner[prop] = wrapped;
    return wrapped;
}
function afterPatch(object, property, handler) {
    const original = object[property];
    if (typeof original !== "function") {
        return { unpatch: () => { } };
    }
    const originalFn = original;
    const patched = function patchedFunction(...args) {
        const result = originalFn.apply(this, args);
        const next = handler.call(this, args, result);
        return typeof next === "undefined" ? result : next;
    };
    try {
        Object.assign(patched, originalFn);
    }
    catch {
        // 忽略函数属性拷贝失败。
    }
    try {
        Object.defineProperty(patched, "toString", {
            value: () => originalFn.toString(),
            configurable: true,
        });
    }
    catch {
        // 忽略 toString 覆盖失败。
    }
    object[property] = patched;
    return {
        unpatch: () => {
            if (object[property] === patched) {
                object[property] = original;
            }
        },
    };
}
function resolveSpliceTarget(children) {
    if (!children || typeof children !== "object")
        return null;
    const root = children;
    const part1 = root.props;
    const part2 = part1?.children;
    if (!Array.isArray(part2) || part2.length < 2)
        return null;
    const part3 = part2[1];
    const part4 = part3?.props;
    const part5 = part4?.children;
    const part6 = part5?.props;
    const list = part6?.children;
    if (Array.isArray(list))
        return list;
    const visited = new Set();
    const queue = [children];
    while (queue.length > 0) {
        const current = queue.shift();
        if (!current || typeof current !== "object")
            continue;
        if (visited.has(current))
            continue;
        visited.add(current);
        if (Array.isArray(current)) {
            if (current.length > 0) {
                const hasOverviewCarrier = current.some((node) => {
                    if (!node || typeof node !== "object")
                        return false;
                    const nodeProps = node.props;
                    const inner = nodeProps?.children?.props;
                    return typeof inner?.overview !== "undefined" || typeof inner?.details !== "undefined";
                });
                if (hasOverviewCarrier)
                    return current;
            }
            for (const item of current) {
                if (item && typeof item === "object")
                    queue.push(item);
            }
            continue;
        }
        const map = current;
        for (const value of Object.values(map)) {
            if (!value)
                continue;
            if (typeof value === "object")
                queue.push(value);
        }
    }
    return null;
}
function findLibraryInsertIndex(nodes) {
    return nodes.findIndex((child) => {
        if (!child || typeof child !== "object")
            return false;
        const props = child.props;
        if (!props)
            return false;
        const hasFocusFlag = typeof props.childFocusDisabled !== "undefined";
        const hasNavRef = typeof props.navRef !== "undefined";
        const innerProps = props.children?.props;
        const hasDetails = typeof innerProps?.details !== "undefined";
        const hasOverview = typeof innerProps?.overview !== "undefined";
        const hasFastRender = typeof innerProps?.bFastRender !== "undefined";
        return hasFocusFlag && hasNavRef && hasDetails && hasOverview && hasFastRender;
    });
}
function resolveLibraryInsertIndex(nodes) {
    const exact = findLibraryInsertIndex(nodes);
    if (exact >= 0)
        return exact;
    const firstNative = nodes.findIndex((child) => {
        if (!child || typeof child !== "object")
            return false;
        const key = String(child.key || "");
        return !key.startsWith("freedeckcy-library-times-");
    });
    if (firstNative >= 0)
        return Math.min(firstNative + 1, nodes.length);
    return Math.min(1, nodes.length);
}
const LIBRARY_TIME_BLOCK_ID = "freedeckcy-library-times";
function isLibraryTimeNode(child) {
    if (!child || typeof child !== "object")
        return false;
    const childProps = child.props;
    return String(childProps?.id || "") === LIBRARY_TIME_BLOCK_ID;
}
function ensureNodeChildrenArray(node) {
    const props = node.props || {};
    node.props = props;
    const children = props.children;
    if (Array.isArray(children))
        return children;
    if (typeof children === "undefined") {
        const next = [];
        props.children = next;
        return next;
    }
    const next = [children];
    props.children = next;
    return next;
}
function findInReactTreeLike(node, filter) {
    if (!node || typeof node !== "object")
        return null;
    const visited = new Set();
    const queue = [node];
    while (queue.length > 0) {
        const current = queue.shift();
        if (!current || typeof current !== "object")
            continue;
        if (visited.has(current))
            continue;
        visited.add(current);
        if (filter(current))
            return current;
        if (Array.isArray(current)) {
            for (const item of current) {
                if (item && typeof item === "object")
                    queue.push(item);
            }
            continue;
        }
        const map = current;
        const walkKeys = ["props", "children", "child", "sibling"];
        for (const key of walkKeys) {
            const value = map[key];
            if (value && typeof value === "object")
                queue.push(value);
        }
        for (const value of Object.values(map)) {
            if (value && typeof value === "object")
                queue.push(value);
        }
    }
    return null;
}
function resolveStaticClassByKey(key) {
    const root = DFL.staticClasses;
    if (!root || typeof root !== "object")
        return "";
    const visited = new Set();
    const queue = [root];
    while (queue.length > 0) {
        const current = queue.shift();
        if (!current || typeof current !== "object")
            continue;
        if (visited.has(current))
            continue;
        visited.add(current);
        if (Array.isArray(current)) {
            for (const item of current) {
                if (item && typeof item === "object")
                    queue.push(item);
            }
            continue;
        }
        const map = current;
        if (typeof map[key] === "string" && String(map[key]).trim()) {
            return String(map[key]).trim();
        }
        for (const value of Object.values(map)) {
            if (value && typeof value === "object")
                queue.push(value);
        }
    }
    return "";
}
function resolveLibraryOverlayHost(tree) {
    const topCapsuleClass = resolveStaticClassByKey("TopCapsule");
    const headerClass = resolveStaticClassByKey("Header");
    const appDetailsRootClass = resolveStaticClassByKey("AppDetailsRoot");
    const markers = [topCapsuleClass, appDetailsRootClass, headerClass].filter(Boolean);
    const classMatched = findInReactTreeLike(tree, (value) => {
        if (!value || typeof value !== "object")
            return false;
        const props = value.props;
        if (!props)
            return false;
        const className = String(props.className || "");
        const children = props.children;
        if (!className || typeof children === "undefined")
            return false;
        return markers.some((marker) => className.includes(marker));
    });
    if (classMatched)
        return classMatched;
    // 回退：命中包含 overview/details 的容器，确保至少能显示。
    return findInReactTreeLike(tree, (value) => {
        if (!value || typeof value !== "object")
            return false;
        const props = value.props;
        if (!props)
            return false;
        const children = props.children;
        if (!children || typeof children !== "object" || Array.isArray(children))
            return false;
        const inner = children.props;
        return typeof inner?.overview !== "undefined" && typeof inner?.details !== "undefined";
    });
}
function resolveLibraryOverviewNode(tree) {
    return findInReactTreeLike(tree, (value) => {
        if (!value || typeof value !== "object")
            return false;
        const map = value;
        const appId = Math.max(0, Number(map.appid ??
            map.appId ??
            map.unAppID ??
            map.nAppID ??
            map.m_unAppID ??
            map.m_nAppID ??
            0));
        if (!Number.isFinite(appId) || appId <= 0)
            return false;
        const title = String(map.display_name || "").trim() ||
            String(map.name || "").trim() ||
            String(map.app_name || "").trim() ||
            String(map.title || "").trim();
        return Boolean(title);
    });
}
function LibraryTimeBlock({ appId, title }) {
    const appIdText = String(Math.max(0, Number(appId || 0)));
    const titleText = String(title || "").trim();
    const cacheKey = `${appIdText}::${titleText.toLowerCase()}`;
    const initialCached = (() => {
        const cached = libraryTimeCache.get(cacheKey);
        if (!cached)
            return null;
        const ttl = hasPositiveLibraryHltb(cached.payload) ? LIBRARY_TIME_CACHE_TTL_MS : LIBRARY_TIME_NEGATIVE_CACHE_TTL_MS;
        if (Date.now() - cached.updatedAt > ttl) {
            libraryTimeCache.delete(cacheKey);
            return null;
        }
        return cached.payload;
    })();
    const [data, setData] = SP_REACT.useState(initialCached);
    SP_REACT.useEffect(() => {
        let alive = true;
        let timerId = null;
        let inFlight = false;
        const clearTimer = () => {
            if (timerId === null)
                return;
            window.clearTimeout(timerId);
            timerId = null;
        };
        const scheduleNext = (payload) => {
            if (!alive)
                return;
            clearTimer();
            const waitMs = hasPositiveLibraryHltb(payload) ? LIBRARY_TIME_REFRESH_MS : LIBRARY_TIME_RETRY_MS;
            timerId = window.setTimeout(() => {
                void fetchStats();
            }, waitMs);
        };
        const fetchStats = async () => {
            if (!alive || inFlight)
                return;
            if (!appIdText || appIdText === "0")
                return;
            inFlight = true;
            try {
                const result = await withTimeout(getTianyiLibraryGameTimeStats({
                    app_id: appIdText,
                    title: titleText,
                }), 7000, "library_time_stats_timeout");
                if (!alive)
                    return;
                if (result.status !== "success") {
                    scheduleNext(null);
                    return;
                }
                const payload = (result.data || {});
                libraryTimeCache.set(cacheKey, { updatedAt: Date.now(), payload });
                setData(payload);
                scheduleNext(payload);
            }
            catch {
                // 忽略库页面时长读取失败，不影响原页面。
                scheduleNext(null);
            }
            finally {
                inFlight = false;
            }
        };
        if (!appIdText || appIdText === "0") {
            setData(null);
            return () => {
                alive = false;
                clearTimer();
            };
        }
        const cached = libraryTimeCache.get(cacheKey);
        const cachedTtl = cached ? (hasPositiveLibraryHltb(cached.payload) ? LIBRARY_TIME_CACHE_TTL_MS : LIBRARY_TIME_NEGATIVE_CACHE_TTL_MS) : 0;
        if (cached && Date.now() - cached.updatedAt <= cachedTtl) {
            setData(cached.payload);
            // 正缓存按周期刷新；负缓存或未托管立即重查，避免“要等很久才出现”。
            if (hasPositiveLibraryHltb(cached.payload) && cached.payload.managed !== false) {
                scheduleNext(cached.payload);
            }
            else {
                void fetchStats();
            }
            return () => {
                alive = false;
                clearTimer();
            };
        }
        void fetchStats();
        return () => {
            alive = false;
            clearTimer();
        };
    }, [appIdText, cacheKey, titleText]);
    // 只给 freedeckCY 安装记录对应的游戏显示时长；Steam 原有游戏不插入任何时长/日期块。
    if (!data || data.managed !== true)
        return null;
    const myPlaytime = formatPlaytimeText(data.my_playtime_seconds || 0, data.my_playtime_text);
    const mainStory = normalizeHoursText(data.main_story_hours, data.main_story_time_text);
    const totalTime = normalizeHoursText(data.total_hours, data.total_time_text);
    const activeSuffix = data.my_playtime_active ? "（进行中）" : "";
    return (SP_JSX.jsx("div", { id: LIBRARY_TIME_BLOCK_ID, style: {
            position: "absolute",
            top: "14px",
            left: "360px",
            right: "auto",
            zIndex: 40,
            minWidth: "250px",
            maxWidth: "320px",
            padding: "8px 10px",
            borderRadius: 1,
            background: "transparent",
            border: "none",
            boxShadow: "none",
            pointerEvents: "none",
        }, children: SP_JSX.jsxs("div", { style: { display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)", gap: "10px" }, children: [SP_JSX.jsxs("div", { style: { minWidth: 0 }, children: [SP_JSX.jsx("div", { style: { fontSize: "14px", fontWeight: 700, lineHeight: 1.2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }, children: `${myPlaytime}${activeSuffix}` }), SP_JSX.jsx("div", { style: { fontSize: "10px", opacity: 0.84 }, children: "\u5DF2\u73A9\u65F6\u957F" })] }), SP_JSX.jsxs("div", { style: { minWidth: 0 }, children: [SP_JSX.jsx("div", { style: { fontSize: "14px", fontWeight: 700, lineHeight: 1.2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }, children: mainStory }), SP_JSX.jsx("div", { style: { fontSize: "10px", opacity: 0.84 }, children: "\u4E3B\u7EBF\u65F6\u957F" })] }), SP_JSX.jsxs("div", { style: { minWidth: 0 }, children: [SP_JSX.jsx("div", { style: { fontSize: "14px", fontWeight: 700, lineHeight: 1.2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }, children: totalTime }), SP_JSX.jsx("div", { style: { fontSize: "10px", opacity: 0.84 }, children: "\u603B\u65F6\u957F" })] })] }) }));
}
function installLibraryPlaytimePatch() {
    const hookApi = routerHook;
    if (typeof hookApi.addPatch !== "function") {
        return () => { };
    }
    const patchFn = (props) => {
        if (!props || typeof props !== "object")
            return props;
        const propsMap = props;
        const childNode = propsMap.children;
        const childProps = childNode?.props;
        if (!childProps)
            return props;
        const renderFunc = childProps.renderFunc;
        if (typeof renderFunc !== "function")
            return props;
        if (Boolean(renderFunc.__FREDECK_LIBRARY_RENDER_PATCHED))
            return props;
        const renderPatch = afterPatch(childProps, "renderFunc", (_args, ret1) => {
            if (!ret1 || typeof ret1 !== "object")
                return ret1;
            const ret1Map = ret1;
            const contentNode = ret1Map.props;
            const primaryOverview = contentNode?.children?.props
                ?.overview;
            const fallbackOverview = resolveLibraryOverviewNode(ret1Map);
            const overviewNode = primaryOverview || fallbackOverview;
            const gameTitle = String(overviewNode?.display_name || overviewNode?.name || overviewNode?.app_name || overviewNode?.title || "").trim();
            const appId = Math.max(0, Number(overviewNode?.appid ??
                overviewNode?.appId ??
                overviewNode?.unAppID ??
                overviewNode?.nAppID ??
                overviewNode?.m_unAppID ??
                overviewNode?.m_nAppID ??
                0));
            if (!appId)
                return ret1;
            const nodeWithType = contentNode?.children || null;
            const wrappedType = wrapReactType(nodeWithType, "type");
            if (!wrappedType)
                return ret1;
            const typeFn = wrappedType.type;
            if (typeof typeFn !== "function")
                return ret1;
            const typeState = typeFn;
            typeState.__FREDECK_LIBRARY_APP_ID = appId;
            typeState.__FREDECK_LIBRARY_GAME_TITLE = gameTitle;
            if (Boolean(typeState.__FREDECK_LIBRARY_TYPE_PATCHED))
                return ret1;
            const typePatch = afterPatch(wrappedType, "type", (_innerArgs, ret2) => {
                if (!ret2 || typeof ret2 !== "object")
                    return ret2;
                const dynamicType = wrappedType.type;
                const runtimeAppId = Math.max(0, Number(dynamicType.__FREDECK_LIBRARY_APP_ID || appId));
                const runtimeTitle = String(dynamicType.__FREDECK_LIBRARY_GAME_TITLE || gameTitle).trim();
                if (!runtimeAppId)
                    return ret2;
                const nextComponent = (SP_JSX.jsx(LibraryTimeBlock, { appId: runtimeAppId, title: runtimeTitle }, `freedeckcy-library-times-${runtimeAppId}`));
                const overlayHost = resolveLibraryOverlayHost(ret2);
                if (overlayHost) {
                    const hostChildren = ensureNodeChildrenArray(overlayHost);
                    const hostProps = overlayHost.props || {};
                    overlayHost.props = hostProps;
                    const currentStyle = hostProps.style;
                    if (!currentStyle || typeof currentStyle !== "object") {
                        hostProps.style = { position: "relative" };
                    }
                    else {
                        const styleMap = currentStyle;
                        if (!styleMap.position) {
                            hostProps.style = { ...styleMap, position: "relative" };
                        }
                    }
                    const existingInHost = hostChildren.findIndex((child) => isLibraryTimeNode(child));
                    if (existingInHost >= 0) {
                        hostChildren.splice(existingInHost, 1, nextComponent);
                    }
                    else {
                        hostChildren.push(nextComponent);
                    }
                    return ret2;
                }
                const spliceTarget = resolveSpliceTarget(ret2);
                if (!spliceTarget)
                    return ret2;
                const existingInFallback = spliceTarget.findIndex((child) => isLibraryTimeNode(child));
                if (existingInFallback >= 0) {
                    spliceTarget.splice(existingInFallback, 1, nextComponent);
                    return ret2;
                }
                const insertIndex = resolveLibraryInsertIndex(spliceTarget);
                spliceTarget.splice(insertIndex, 0, nextComponent);
                return ret2;
            });
            const patchedType = wrappedType.type;
            patchedType.__FREDECK_LIBRARY_TYPE_PATCHED = true;
            patchedType.__FREDECK_LIBRARY_APP_ID = appId;
            patchedType.__FREDECK_LIBRARY_GAME_TITLE = gameTitle;
            patchedType.__FREDECK_LIBRARY_TYPE_UNPATCH = typePatch.unpatch;
            return ret1;
        });
        const patchedRender = childProps.renderFunc;
        patchedRender.__FREDECK_LIBRARY_RENDER_PATCHED = true;
        patchedRender.__FREDECK_LIBRARY_RENDER_UNPATCH = renderPatch.unpatch;
        return props;
    };
    const patchHandle = hookApi.addPatch("/library/app/:appid", patchFn);
    return () => {
        try {
            hookApi.removePatch?.("/library/app/:appid", patchHandle);
        }
        catch {
            // 忽略移除 patch 异常。
        }
    };
}
async function withTimeout(promise, timeoutMs, timeoutMessage) {
    return new Promise((resolve, reject) => {
        const timer = window.setTimeout(() => {
            reject(new Error(timeoutMessage));
        }, timeoutMs);
        promise
            .then((value) => {
            window.clearTimeout(timer);
            resolve(value);
        })
            .catch((error) => {
            window.clearTimeout(timer);
            reject(error);
        });
    });
}
async function pickFolder(startPath) {
    const base = String(startPath || "/home/deck").trim() || "/home/deck";
    const result = await openFilePicker(1 /* FileSelectionType.FOLDER */, base, false, true);
    return String(result?.realpath || result?.path || "").trim();
}
function isTaskAlreadyInstalled(task) {
    const installStatus = String(task.install_status || "").trim().toLowerCase();
    if (installStatus === "installed")
        return true;
    const downloadStatus = String(task.status || "").trim().toLowerCase();
    if (downloadStatus === "complete" && String(task.installed_path || "").trim())
        return true;
    return false;
}
function isTaskActive(task) {
    const status = String(task.status || "").trim().toLowerCase();
    if (!status)
        return false;
    return !["complete", "error", "removed", "paused"].includes(status);
}
function countActiveTasks(tasks) {
    let count = 0;
    for (const task of tasks || []) {
        if (isTaskActive(task))
            count += 1;
    }
    return count;
}
function resolvePanelPollMode(state) {
    const visible = !document.hidden;
    if (!visible)
        return PANEL_POLL_MODE_BACKGROUND;
    return countActiveTasks(state.tasks || []) > 0 ? PANEL_POLL_MODE_ACTIVE : PANEL_POLL_MODE_IDLE;
}
function pollIntervalByMode(mode) {
    if (mode === PANEL_POLL_MODE_ACTIVE)
        return PANEL_ACTIVE_POLL_MS;
    if (mode === PANEL_POLL_MODE_BACKGROUND)
        return PANEL_BACKGROUND_POLL_MS;
    return PANEL_IDLE_POLL_MS;
}
function InstallPreflightSection({ report, busy, onRun }) {
    const checks = Array.isArray(report?.checks) ? report.checks : [];
    const labels = {
        download_dir: "下载目录",
        install_dir: "安装目录",
        disk_free: "下载盘剩余空间",
        disk_free_install: "安装盘剩余空间",
    };
    return (SP_JSX.jsxs(DFL.PanelSection, { title: "安装环境检查", children: [
            SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.6, opacity: 0.86 }, children: "检查下载/安装目录是否可写、磁盘剩余空间是否充足；开始安装时也会自动检查，异常时仍可选择继续。" }) }),
            SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onRun, disabled: busy, children: busy ? "检查中..." : "检查安装环境" }) }),
            report ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "4px", width: "100%" }, children: [
                        SP_JSX.jsx("div", { style: { fontWeight: 600, color: report.ok ? "#9fe6a8" : "#ffb4a8" }, children: report.ok ? "环境正常" : "环境异常" }),
                        checks.map((check, index) => {
                            const ok = Boolean(check.ok);
                            const label = labels[check.id] || check.id || "检查项";
                            return (SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "1px", fontSize: "11px", lineHeight: 1.5 }, children: [
                                    SP_JSX.jsxs("div", { style: { display: "flex", justifyContent: "space-between", gap: "8px" }, children: [
                                            SP_JSX.jsx("span", { children: label }),
                                            SP_JSX.jsx("span", { style: { color: ok ? "#9fe6a8" : "#ffb4a8" }, children: ok ? "正常" : "异常" }),
                                        ] }),
                                    check.path ? (SP_JSX.jsx("div", { style: { opacity: 0.72, wordBreak: "break-all" }, children: check.path })) : null,
                                    check.message ? (SP_JSX.jsx("div", { style: { color: ok ? "#b9c9d8" : "#ffb4a8" }, children: check.message })) : null,
                                ] }, `${check.id || "check"}-${index}`));
                        }),
                    ] }) })) : null,
        ] }));
}
function StorageCleanupSection({ report, busy, message, onScan, onClean }) {
    const groups = Array.isArray(report?.groups) ? report.groups : [];
    const safeGroups = groups.filter((group) => group.safe && Number(group.count || 0) > 0).map((group) => group.id);
    return (SP_JSX.jsxs(DFL.PanelSection, { title: "存储清理", children: [
            SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.6, opacity: 0.86 }, children: "扫描插件更新包、失败/不支持续传时隔离的坏文件、历史云存档备份；只删除可安全重新获取的文件，历史备份默认保留。" }) }),
            SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onScan, disabled: busy, children: busy ? "扫描中..." : "扫描可清理项" }) }),
            message ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "11px", lineHeight: 1.5, opacity: 0.86, wordBreak: "break-word" }, children: message }) })) : null,
            report ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "2px", width: "100%", fontSize: "12px" }, children: [
                        SP_JSX.jsx("div", { style: { fontWeight: 600, color: Number(report.safe_count || 0) > 0 ? "#ffd479" : "#9fe6a8" }, children: `可安全清理：${formatBytesText(Number(report.safe_bytes || 0))} · ${Number(report.safe_count || 0)} 个文件` }),
                        SP_JSX.jsx("div", { style: { opacity: 0.75, fontSize: "11px" }, children: `全部扫描项：${formatBytesText(Number(report.total_bytes || 0))}` }),
                    ] }) })) : null,
            groups.map((group, groupIndex) => {
                const count = Number(group.count || 0);
                const bytes = Number(group.bytes || 0);
                const items = Array.isArray(group.items) ? group.items : [];
                return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "3px", width: "100%", fontSize: "11px", lineHeight: 1.5 }, children: [
                            SP_JSX.jsxs("div", { style: { display: "flex", justifyContent: "space-between", gap: "8px" }, children: [
                                    SP_JSX.jsx("span", { style: { fontWeight: 600 }, children: group.label || group.id || "清理项" }),
                                    SP_JSX.jsx("span", { style: { color: group.safe ? "#9fe6a8" : "#ffd479" }, children: `${count} 个 · ${formatBytesText(bytes)}${group.safe ? " · 可删" : " · 保留"}` }),
                                ] }),
                            group.description ? (SP_JSX.jsx("div", { style: { opacity: 0.72 }, children: group.description })) : null,
                            items.slice(0, 3).map((item, itemIndex) => (SP_JSX.jsx("div", { style: { opacity: 0.7, wordBreak: "break-all" }, children: item.display_path || item.path || "-" }, `${group.id}-${itemIndex}`))),
                            count > 3 ? (SP_JSX.jsx("div", { style: { opacity: 0.6 }, children: `…另有 ${count - 3} 个` })) : null,
                        ] }) }, `${group.id || "group"}-${groupIndex}`));
            }),
            report && safeGroups.length > 0 ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => onClean(safeGroups), disabled: busy, children: busy ? "处理中..." : "清理可安全删除项" }) })) : null,
        ] }));
}
function SettingsPage() {
    const language = useLanguage();
    const [loading, setLoading] = SP_REACT.useState(true);
    const [saving, setSaving] = SP_REACT.useState(false);
    const [clearingLogin, setClearingLogin] = SP_REACT.useState(false);
    const [scanningInstalled, setScanningInstalled] = SP_REACT.useState(false);
    const [preflightReport, setPreflightReport] = SP_REACT.useState(null);
    const [preflightBusy, setPreflightBusy] = SP_REACT.useState(false);
    const [storageCleanupReport, setStorageCleanupReport] = SP_REACT.useState(null);
    const [storageCleanupBusy, setStorageCleanupBusy] = SP_REACT.useState(false);
    const [storageCleanupMessage, setStorageCleanupMessage] = SP_REACT.useState("");
    const [updatingCatalog, setUpdatingCatalog] = SP_REACT.useState(false);
    const [catalogUpdateMessage, setCatalogUpdateMessage] = SP_REACT.useState("");
    const [diagnosticsReport, setDiagnosticsReport] = SP_REACT.useState(null);
    const [diagnosticsBusy, setDiagnosticsBusy] = SP_REACT.useState(false);
    const [diagnosticsExportBusy, setDiagnosticsExportBusy] = SP_REACT.useState(false);
    const [diagnosticsExportMessage, setDiagnosticsExportMessage] = SP_REACT.useState("");
    const [diagnosticsError, setDiagnosticsError] = SP_REACT.useState("");
    const [updateInfo, setUpdateInfo] = SP_REACT.useState(null);
    const [checkingUpdate, setCheckingUpdate] = SP_REACT.useState(false);
    const [downloadingUpdate, setDownloadingUpdate] = SP_REACT.useState(false);
    const [installingUpdate, setInstallingUpdate] = SP_REACT.useState(false);
    const [updateMessage, setUpdateMessage] = SP_REACT.useState("");
    const [activeTab, setActiveTab] = SP_REACT.useState("paths");
    const [settings, setSettings] = SP_REACT.useState(EMPTY_SETTINGS);
    const [storageOptions, setStorageOptions] = SP_REACT.useState([]);
    const [login, setLogin] = SP_REACT.useState(EMPTY_STATE.login);
    const [baiduWebLogin, setBaiduWebLogin] = SP_REACT.useState(EMPTY_BAIDU_WEB_STATE);
    const [baiduQr, setBaiduQr] = SP_REACT.useState({ stage: "idle" });
    const [baiduQrBusy, setBaiduQrBusy] = SP_REACT.useState(false);
    const [baiduHealth, setBaiduHealth] = SP_REACT.useState(null);
    const [checkingBaiduHealth, setCheckingBaiduHealth] = SP_REACT.useState(false);
    const baiduQrPollBusyRef = SP_REACT.useRef(false);
    const baiduQrPollFailuresRef = SP_REACT.useRef(0);
    const [baiduLogin, setBaiduLogin] = SP_REACT.useState(EMPTY_BAIDU_OPENAPI_STATE);
    const [baiduAppKey, setBaiduAppKey] = SP_REACT.useState("");
    const [baiduSecretKey, setBaiduSecretKey] = SP_REACT.useState("");
    const [baiduAuthCode, setBaiduAuthCode] = SP_REACT.useState("");
    const [baiduBusy, setBaiduBusy] = SP_REACT.useState(false);
    const [cloudSaveUploadState, setCloudSaveUploadState] = SP_REACT.useState(EMPTY_CLOUD_SAVE_STATE);
    const [cloudSaveRestoreState, setCloudSaveRestoreState] = SP_REACT.useState(EMPTY_CLOUD_SAVE_RESTORE_STATE);
    const [startingCloudSaveUpload, setStartingCloudSaveUpload] = SP_REACT.useState(false);
    const [loadingRestoreOptions, setLoadingRestoreOptions] = SP_REACT.useState(false);
    const [loadingRestoreEntries, setLoadingRestoreEntries] = SP_REACT.useState(false);
    const [planningRestore, setPlanningRestore] = SP_REACT.useState(false);
    const [applyingRestore, setApplyingRestore] = SP_REACT.useState(false);
    const [restoreOptions, setRestoreOptions] = SP_REACT.useState([]);
    const [selectedRestoreGameKey, setSelectedRestoreGameKey] = SP_REACT.useState("");
    const [selectedRestoreVersion, setSelectedRestoreVersion] = SP_REACT.useState("");
    const [restoreEntries, setRestoreEntries] = SP_REACT.useState([]);
    const [selectedRestoreEntryIds, setSelectedRestoreEntryIds] = SP_REACT.useState([]);
    const [targetCandidates, setTargetCandidates] = SP_REACT.useState([]);
    const [selectedRestoreTargetDir, setSelectedRestoreTargetDir] = SP_REACT.useState("");
    const [splitDraft, setSplitDraft] = SP_REACT.useState(16);
    const settingsContainerRef = SP_REACT.useRef(null);
    useI18nRoot(settingsContainerRef);
    const tabStabilityCss = SP_REACT.useMemo(() => `
      .freedeckcy-settings-root [class*="TabContentsScroll"],
      .freedeckcy-settings-root [class*="TabContents"],
      .freedeckcy-settings-root [class*="TabContent"],
      .freedeckcy-settings-root [class*="ScrollPanel"] {
        scrollbar-gutter: stable both-edges !important;
        overflow-y: auto !important;
      }
      .freedeckcy-settings-root [class*="TabHeaderRowWrapper"],
      .freedeckcy-settings-root [class*="TabRowTabs"],
      .freedeckcy-settings-root [class*="TabsRowScroll"],
      .freedeckcy-settings-root [class*="TabRow"] {
        transition: none !important;
        animation: none !important;
        scroll-behavior: auto !important;
      }
      .freedeckcy-settings-root [role="tablist"] {
        scroll-behavior: auto !important;
      }
    `, []);
    const selectedRestoreGame = SP_REACT.useMemo(() => restoreOptions.find((item) => item.game_key === selectedRestoreGameKey) || null, [restoreOptions, selectedRestoreGameKey]);
    const restoreVersionOptions = SP_REACT.useMemo(() => (selectedRestoreGame?.versions || []).map((item) => ({
        data: item.version_name,
        label: `${item.display_time || item.version_name} | ${formatBytes(item.size_bytes)}`,
    })), [selectedRestoreGame]);
    SP_REACT.useEffect(() => {
        const classMap = getGamepadTabClassMap();
        if (!classMap)
            return;
        const styleId = "freedeckcy-settings-tabs-no-jitter";
        if (document.getElementById(styleId))
            return;
        const style = document.createElement("style");
        style.id = styleId;
        const rules = [];
        if (classMap.TabsRowScroll) {
            rules.push(`.${classMap.TabsRowScroll}{scroll-behavior:auto !important;}`);
        }
        if (classMap.TabRowTabs) {
            rules.push(`.${classMap.TabRowTabs}{transition:none !important;}`);
            rules.push(`.${classMap.TabRowTabs}{scroll-snap-type:none !important;}`);
        }
        if (classMap.Tab) {
            rules.push(`.${classMap.Tab}{transition:none !important;}`);
        }
        style.textContent = rules.join("\n");
        document.head.appendChild(style);
    }, []);
    SP_REACT.useEffect(() => {
        if (!restoreOptions.length) {
            setSelectedRestoreGameKey("");
            setSelectedRestoreVersion("");
            return;
        }
        const exists = restoreOptions.some((item) => item.game_key === selectedRestoreGameKey);
        if (!exists) {
            const fallback = restoreOptions.find((item) => item.available && item.versions.length > 0);
            setSelectedRestoreGameKey(String(fallback?.game_key || ""));
        }
    }, [restoreOptions, selectedRestoreGameKey]);
    SP_REACT.useEffect(() => {
        if (!selectedRestoreGame) {
            setSelectedRestoreVersion("");
            return;
        }
        const exists = selectedRestoreGame.versions.some((item) => item.version_name === selectedRestoreVersion);
        if (!exists) {
            setSelectedRestoreVersion(String(selectedRestoreGame.versions[0]?.version_name || ""));
        }
    }, [selectedRestoreGame, selectedRestoreVersion]);
    SP_REACT.useEffect(() => {
        setRestoreEntries([]);
        setSelectedRestoreEntryIds([]);
        setTargetCandidates([]);
        setSelectedRestoreTargetDir("");
    }, [selectedRestoreGameKey, selectedRestoreVersion]);
    const refreshStorageOptions = SP_REACT.useCallback(async () => {
        try {
            const result = await withTimeout(getTianyiStorageOptions(), 10000, "读取存储信息超时");
            if (result.status === "success" && result.data) {
                setStorageOptions(Array.isArray(result.data.options) ? result.data.options : []);
            }
        }
        catch {
            // 静默：没有 SD 卡/挂载信息时不影响设置页。
        }
    }, []);
    const refreshSettings = SP_REACT.useCallback(async () => {
        const result = await withTimeout(getTianyiPanelState(), PANEL_REQUEST_TIMEOUT_MS, "读取设置超时，请稍后重试");
        if (result.status !== "success" || !result.data) {
            throw new Error(result.message || "读取设置失败");
        }
        const next = Object.assign({}, EMPTY_SETTINGS, result.data.settings || {});
        setSettings(next);
        setLogin(result.data.login || EMPTY_STATE.login);
        setBaiduWebLogin(result.data.baidu_login || EMPTY_BAIDU_WEB_STATE);
        setBaiduLogin(result.data.baidu_openapi_login || EMPTY_BAIDU_OPENAPI_STATE);
        setSplitDraft(Math.max(1, Math.min(64, Number(next.split_count || 16))));
    }, []);
    const refreshCloudSaveUploadStatus = SP_REACT.useCallback(async () => {
        const result = await withTimeout(getTianyiCloudSaveUploadStatus(), 10000, "读取云存档状态超时");
        if (result.status !== "success") {
            throw new Error(result.message || "读取云存档状态失败");
        }
        const nextState = normalizeCloudSaveUploadState(result.data?.state);
        setCloudSaveUploadState(nextState);
    }, []);
    const refreshCloudSaveRestoreStatus = SP_REACT.useCallback(async () => {
        const result = await withTimeout(getTianyiCloudSaveRestoreStatus(), 10000, "读取恢复状态超时");
        if (result.status !== "success") {
            throw new Error(result.message || "读取恢复状态失败");
        }
        const nextState = normalizeCloudSaveRestoreState(result.data?.state);
        setCloudSaveRestoreState(nextState);
        const restorableIds = Array.isArray(nextState.selected_entry_ids) ? nextState.selected_entry_ids : [];
        if (restorableIds.length > 0) {
            // 函数式更新：不把当前选择写进依赖，避免初始加载 effect 因选择变化反复重跑。
            setSelectedRestoreEntryIds((prev) => (prev.length > 0 ? prev : restorableIds));
        }
    }, []);
    const refreshRestoreOptions = SP_REACT.useCallback(async () => {
        if (loadingRestoreOptions)
            return;
        setLoadingRestoreOptions(true);
        try {
            const result = await withTimeout(listTianyiCloudSaveRestoreOptions(), 20000, "读取云存档列表超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "读取云存档列表失败");
            }
            const games = Array.isArray(result.data.games) ? result.data.games : [];
            setRestoreOptions(games);
            const fallback = games.find((item) => item.available && item.versions.length > 0);
            if (fallback && !selectedRestoreGameKey) {
                setSelectedRestoreGameKey(String(fallback.game_key || ""));
            }
            toaster.toast({ title: "freedeckCY", body: `已刷新云存档版本（游戏 ${games.length} 个）` });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setLoadingRestoreOptions(false);
        }
    }, [loadingRestoreOptions, selectedRestoreGameKey]);
    SP_REACT.useEffect(() => {
        let alive = true;
        (async () => {
            try {
                await refreshSettings();
                await refreshCloudSaveUploadStatus();
                await refreshCloudSaveRestoreStatus();
            }
            catch (error) {
                if (alive)
                    toastError(error);
            }
            finally {
                if (alive)
                    setLoading(false);
            }
        })();
        return () => {
            alive = false;
        };
    }, [refreshSettings, refreshCloudSaveRestoreStatus, refreshCloudSaveUploadStatus]);
    SP_REACT.useEffect(() => {
        if (!cloudSaveUploadState.running)
            return;
        let alive = true;
        let timer = 0;
        const poll = async () => {
            if (!alive)
                return;
            try {
                await refreshCloudSaveUploadStatus();
            }
            catch {
                // 轮询失败时保留当前状态，避免干扰 UI。
            }
            finally {
                if (alive)
                    timer = window.setTimeout(poll, 1200);
            }
        };
        timer = window.setTimeout(poll, 1200);
        return () => {
            alive = false;
            if (timer)
                window.clearTimeout(timer);
        };
    }, [cloudSaveUploadState.running, refreshCloudSaveUploadStatus]);
    SP_REACT.useEffect(() => {
        if (!cloudSaveRestoreState.running)
            return;
        let alive = true;
        let timer = 0;
        const poll = async () => {
            if (!alive)
                return;
            try {
                await refreshCloudSaveRestoreStatus();
            }
            catch {
                // 轮询失败时保留当前状态，避免干扰 UI。
            }
            finally {
                if (alive)
                    timer = window.setTimeout(poll, 1200);
            }
        };
        timer = window.setTimeout(poll, 1200);
        return () => {
            alive = false;
            if (timer)
                window.clearTimeout(timer);
        };
    }, [cloudSaveRestoreState.running, refreshCloudSaveRestoreStatus]);
    const savePatch = SP_REACT.useCallback(async (patch, successMessage = "设置已保存") => {
        if (saving)
            return;
        setSaving(true);
        try {
            const merged = Object.assign({}, settings, patch);
            const result = await withTimeout(setTianyiSettings(toPayload(merged)), 15000, "保存设置超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "保存设置失败");
            }
            const next = Object.assign({}, EMPTY_SETTINGS, result.data || {});
            setSettings(next);
            setSplitDraft(Math.max(1, Math.min(64, Number(next.split_count || 16))));
            toaster.toast({ title: "freedeckCY", body: successMessage });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setSaving(false);
        }
    }, [saving, settings]);
    const onPickDownloadDir = SP_REACT.useCallback(async () => {
        try {
            const selected = await pickFolder(settings.download_dir || "/home/deck");
            if (!selected)
                return;
            await savePatch({ download_dir: selected }, `下载目录已更新：${selected}`);
        }
        catch (error) {
            toaster.toast({ title: "freedeckCY", body: `选择下载目录失败：${errorText(error)}` });
        }
    }, [savePatch, settings.download_dir]);
    const onPickInstallDir = SP_REACT.useCallback(async () => {
        try {
            const selected = await pickFolder(settings.install_dir || settings.download_dir || "/home/deck");
            if (!selected)
                return;
            await savePatch({ install_dir: selected }, `安装目录已更新：${selected}`);
        }
        catch (error) {
            toaster.toast({ title: "freedeckCY", body: `选择安装目录失败：${errorText(error)}` });
        }
    }, [savePatch, settings.download_dir, settings.install_dir]);
    const onSaveSplit = SP_REACT.useCallback(async () => {
        const value = Number(splitDraft);
        if (!Number.isFinite(value) || value < 1 || value > 64) {
            toaster.toast({ title: "freedeckCY", body: "分片数必须在 1 到 64 之间" });
            return;
        }
        await savePatch({ split_count: value }, "下载参数已更新");
    }, [savePatch, splitDraft]);
    SP_REACT.useEffect(() => {
        void refreshStorageOptions();
    }, [refreshStorageOptions]);
    const onUseStorage = SP_REACT.useCallback(async (option, field) => {
        const value = field === "download_dir" ? option.download_dir : option.install_dir;
        await savePatch({ [field]: value }, `${field === "download_dir" ? "下载" : "安装"}目录已切换到：${value}`);
        await refreshStorageOptions();
    }, [refreshStorageOptions, savePatch]);
    const onClearLogin = SP_REACT.useCallback(async () => {
        if (clearingLogin)
            return;
        setClearingLogin(true);
        try {
            const result = await withTimeout(clearTianyiLogin(), 20000, "注销天翼云账号超时");
            if (result.status !== "success") {
                throw new Error(result.message || "注销失败");
            }
            await refreshSettings();
            await refreshCloudSaveUploadStatus();
            await refreshCloudSaveRestoreStatus();
            setRestoreOptions([]);
            setSelectedRestoreGameKey("");
            setSelectedRestoreVersion("");
            setRestoreEntries([]);
            setSelectedRestoreEntryIds([]);
            setTargetCandidates([]);
            setSelectedRestoreTargetDir("");
            const body = String(result.data?.message || "已注销天翼云账号");
            toaster.toast({ title: "freedeckCY", body });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setClearingLogin(false);
        }
    }, [clearingLogin, refreshCloudSaveRestoreStatus, refreshCloudSaveUploadStatus, refreshSettings]);
    SP_REACT.useEffect(() => {
        if (baiduQr.stage !== "waiting" && baiduQr.stage !== "scanned")
            return;
        let cancelled = false;
        const timer = window.setInterval(async () => {
            if (cancelled || baiduQrPollBusyRef.current)
                return;
            baiduQrPollBusyRef.current = true;
            try {
                const result = await withTimeout(pollBaiduQrLogin(), 15000, "轮询百度扫码状态超时");
                if (cancelled)
                    return;
                if (result.status !== "success" || !result.data) {
                    throw new Error(result.message || "轮询百度扫码状态失败");
                }
                baiduQrPollFailuresRef.current = 0;
                const next = result.data;
                setBaiduQr(next);
                if (next.stage === "success") {
                    setBaiduWebLogin({
                        logged_in: true,
                        user_account: String(next.user_account || ""),
                        message: String(next.message || "已登录"),
                    });
                    toaster.toast({ title: "freedeckCY", body: "百度网盘扫码登录成功" });
                    try {
                        await refreshSettings();
                    }
                    catch {
                        // 登录成功优先，设置刷新失败不覆盖成功状态。
                    }
                    // 成功后收起二维码会话，避免「已登录」还停留在扫码成功状态。
                    if (!cancelled)
                        setBaiduQr({ stage: "idle" });
                }
            }
            catch (error) {
                baiduQrPollFailuresRef.current += 1;
                if (baiduQrPollFailuresRef.current >= 3 && !cancelled) {
                    setBaiduQr({
                        stage: "failed",
                        message: `扫码状态连续失败：${errorText(error)}`,
                    });
                }
            }
            finally {
                baiduQrPollBusyRef.current = false;
            }
        }, Math.max(5, Number(baiduQr.interval || 5)) * 1000);
        return () => {
            cancelled = true;
            window.clearInterval(timer);
        };
    }, [baiduQr.stage, baiduQr.interval, refreshSettings]);
    const onStartBaiduQr = SP_REACT.useCallback(async () => {
        if (baiduQrBusy)
            return;
        baiduQrPollFailuresRef.current = 0;
        setBaiduQrBusy(true);
        setBaiduQr({ stage: "starting" });
        toaster.toast({ title: "freedeckCY", body: "正在获取百度二维码..." });
        try {
            const result = await withTimeout(startBaiduQrLogin(), 25000, "获取百度二维码超时（网络/TLS 可能受阻，请稍后重试或运行诊断）");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "获取百度二维码失败");
            }
            if (!result.data.qr_data_url && !result.data.qrcode_url) {
                throw new Error("百度二维码为空");
            }
            setBaiduQr(result.data);
        }
        catch (error) {
            // 失败也要落到 failed，避免 UI 停留在上一轮的二维码/过期提示里没有反馈。
            const message = errorText(error);
            setBaiduQr({ stage: "failed", message });
            toaster.toast({ title: "freedeckCY", body: message });
        }
        finally {
            setBaiduQrBusy(false);
        }
    }, [baiduQrBusy]);
    const onCancelBaiduQr = SP_REACT.useCallback(async () => {
        try {
            await cancelBaiduQrLogin();
        }
        catch {
            // 忽略取消失败。
        }
        setBaiduQr({ stage: "idle" });
    }, []);
    const onClearBaiduWeb = SP_REACT.useCallback(async () => {
        if (baiduQrBusy)
            return;
        setBaiduQrBusy(true);
        try {
            const result = await withTimeout(clearBaiduLogin(), 15000, "退出百度网盘超时");
            if (result.status !== "success")
                throw new Error(result.message || "退出百度网盘失败");
            setBaiduWebLogin(result.data || EMPTY_BAIDU_WEB_STATE);
            setBaiduQr({ stage: "idle" });
            setBaiduHealth(null);
            toaster.toast({ title: "freedeckCY", body: "已退出百度网盘" });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setBaiduQrBusy(false);
        }
    }, [baiduQrBusy]);
    const onCheckBaiduHealth = SP_REACT.useCallback(async () => {
        if (checkingBaiduHealth)
            return;
        setCheckingBaiduHealth(true);
        try {
            const result = await withTimeout(checkBaiduWebHealth(), 30000, "百度登录检查超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "百度登录检查失败");
            }
            setBaiduHealth(result.data);
            toaster.toast({ title: "freedeckCY", body: String(result.data.message || "检查完成"), duration: 5000 });
        }
        catch (error) {
            setBaiduHealth({ ok: false, message: errorText(error), checks: [] });
            toastError(error);
        }
        finally {
            setCheckingBaiduHealth(false);
        }
    }, [checkingBaiduHealth]);
    const onCheckUpdate = SP_REACT.useCallback(async () => {
        if (checkingUpdate)
            return;
        setCheckingUpdate(true);
        setUpdateMessage("");
        try {
            const result = await withTimeout(checkTianyiUpdate(true), 30000, "检查更新超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "检查更新失败");
            }
            setUpdateInfo(result.data);
            const updateText = String(result.data.message || (result.data.has_update ? `发现新版本 ${result.data.latest}` : "当前已是最新版本"));
            setUpdateMessage(result.data.tls_insecure ? `${updateText}（TLS 证书校验失败，已降级）` : updateText);
        }
        catch (error) {
            setUpdateMessage(errorText(error));
        }
        finally {
            setCheckingUpdate(false);
        }
    }, [checkingUpdate]);
    const onDownloadUpdate = SP_REACT.useCallback(async () => {
        if (downloadingUpdate)
            return;
        setDownloadingUpdate(true);
        setUpdateMessage("");
        try {
            const result = await withTimeout(downloadTianyiUpdate(), 300000, "下载更新包超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "下载更新包失败");
            }
            const downloadText = String(result.data.message || "更新包已下载");
            setUpdateMessage(result.data.tls_insecure ? `${downloadText}（TLS 证书校验失败，已降级）` : downloadText);
            toaster.toast({ title: "freedeckCY", body: downloadText, duration: 7000 });
        }
        catch (error) {
            setUpdateMessage(errorText(error));
        }
        finally {
            setDownloadingUpdate(false);
        }
    }, [downloadingUpdate]);
    const onInstallUpdate = SP_REACT.useCallback(async () => {
        if (installingUpdate)
            return;
        setInstallingUpdate(true);
        setUpdateMessage("");
        try {
            const result = await withTimeout(prepareTianyiUpdateInstall(), 30000, "准备更新超时");
            const target = result.data || {};
            if (result.status !== "success" || !target.ok) {
                throw new Error(String(target.message || result.message || "准备更新失败"));
            }
            const backend = window.DeckyBackend;
            if (!backend || typeof backend.call !== "function") {
                throw new Error("当前 Decky 版本不支持自动安装，请使用「下载更新包」后手动安装");
            }
            setUpdateMessage(`正在把 ${target.version || target.latest || "更新"} 交给 Decky 安装...`);
            await backend.call("utilities/install_plugin", target.url, "freedeckCY", target.version || target.latest, target.sha256, target.install_type ?? 2);
            const message = `已发起 ${target.version || target.latest || "更新"} 更新，请在 Decky 弹窗确认安装；完成后插件会自动重新加载。`;
            setUpdateMessage(message);
            toaster.toast({ title: "freedeckCY 更新", body: message, duration: 8000 });
        }
        catch (error) {
            setUpdateMessage(errorText(error));
            toastError(error);
        }
        finally {
            setInstallingUpdate(false);
        }
    }, [installingUpdate]);
    const onRunDiagnostics = SP_REACT.useCallback(async () => {
        if (diagnosticsBusy)
            return;
        setDiagnosticsBusy(true);
        setDiagnosticsError("");
        try {
            const result = await withTimeout(runTianyiDiagnostics(), 90000, "自检超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "自检失败");
            }
            setDiagnosticsReport(result.data);
            const summary = result.data.summary || {};
            toaster.toast({
                title: "freedeckCY 自检",
                body: `OK ${summary.ok || 0} / 警告 ${summary.warn || 0} / 失败 ${summary.fail || 0}`,
            });
        }
        catch (error) {
            // 自检失败时把原因留在页面上，toast 消失后仍能看到。
            const message = errorText(error);
            setDiagnosticsError(message);
            toaster.toast({ title: "freedeckCY", body: message });
        }
        finally {
            setDiagnosticsBusy(false);
        }
    }, [diagnosticsBusy]);
    const onExportDiagnostics = SP_REACT.useCallback(async () => {
        if (diagnosticsExportBusy)
            return;
        setDiagnosticsExportBusy(true);
        setDiagnosticsExportMessage("");
        try {
            const result = await withTimeout(exportTianyiDiagnosticsFile(), 120000, "导出诊断包超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "导出诊断包失败");
            }
            const message = result.data.message || `已导出：${result.data.path || ""}`;
            setDiagnosticsExportMessage(message);
            toaster.toast({ title: "freedeckCY 诊断包", body: message });
        }
        catch (error) {
            const message = errorText(error);
            setDiagnosticsExportMessage(`导出失败：${message}`);
            toaster.toast({ title: "freedeckCY", body: message });
        }
        finally {
            setDiagnosticsExportBusy(false);
        }
    }, [diagnosticsExportBusy]);
    const onScanInstalledSettings = SP_REACT.useCallback(async () => {
        if (scanningInstalled)
            return;
        setScanningInstalled(true);
        try {
            const result = await withTimeout(scanTianyiInstalledGames(), 90000, "扫描已安装游戏超时");
            if (result.status !== "success") {
                throw new Error(result.message || "扫描已安装游戏失败");
            }
            const data = (result.data || {});
            const message = String(data.message || "扫描完成");
            const steamAdded = (Array.isArray(data.added_games)
                ? data.added_games.filter((item) => Boolean(item.steam_added)).length
                : 0) + Number(data.steam_recovered_count || 0);
            toaster.toast({
                title: "freedeckCY",
                body: `${message}${steamAdded ? `（自动加入 Steam：${steamAdded}）` : ""}`,
            });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setScanningInstalled(false);
        }
    }, [scanningInstalled]);
    const onRunPreflight = SP_REACT.useCallback(async () => {
        if (preflightBusy)
            return;
        setPreflightBusy(true);
        try {
            const result = await withTimeout(preflightTianyiInstall(), 20000, "安装环境检查超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "安装环境检查失败");
            }
            setPreflightReport(result.data);
            toaster.toast({ title: "freedeckCY", body: result.data.ok ? "安装环境正常" : "安装环境存在异常，请查看检查结果" });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setPreflightBusy(false);
        }
    }, [preflightBusy]);
    const onScanStorageCleanup = SP_REACT.useCallback(async () => {
        if (storageCleanupBusy)
            return;
        setStorageCleanupBusy(true);
        setStorageCleanupMessage("");
        try {
            const result = await withTimeout(scanTianyiStorageCleanup(), 60000, "扫描清理项超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "扫描清理项失败");
            }
            setStorageCleanupReport(result.data);
            setStorageCleanupMessage(`扫描完成：可安全清理 ${formatBytesText(Number(result.data.safe_bytes || 0))}（${Number(result.data.safe_count || 0)} 个文件）`);
        }
        catch (error) {
            setStorageCleanupMessage(`扫描失败：${errorText(error)}`);
            toastError(error);
        }
        finally {
            setStorageCleanupBusy(false);
        }
    }, [storageCleanupBusy]);
    const onCleanStorageCleanup = SP_REACT.useCallback((categories) => {
        if (storageCleanupBusy)
            return;
        const selected = Array.isArray(categories) ? categories.filter(Boolean) : [];
        if (!selected.length)
            return;
        DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, { strTitle: "清理存储", strDescription: "将删除扫描结果中标记为可安全清理的文件（更新包、隔离的坏文件/半成品）；历史云存档备份不会删除。确定继续？", strOKButtonText: "清理", strCancelButtonText: "取消", onOK: () => {
                void (async () => {
                    setStorageCleanupBusy(true);
                    try {
                        const result = await withTimeout(cleanTianyiStorageCleanup({ categories: selected }), 120000, "清理超时");
                        if (result.status !== "success" || !result.data) {
                            throw new Error(result.message || "清理失败");
                        }
                        const data = result.data;
                        const message = `已清理 ${Number(data.deleted_files || 0)} 个文件，释放 ${formatBytesText(Number(data.freed_bytes || 0))}${data.errors?.length ? `；${data.errors.length} 项跳过` : ""}`;
                        setStorageCleanupMessage(message);
                        toaster.toast({ title: "freedeckCY 清理", body: message });
                        const refreshed = await withTimeout(scanTianyiStorageCleanup(), 60000, "扫描清理项超时");
                        if (refreshed.status === "success" && refreshed.data) {
                            setStorageCleanupReport(refreshed.data);
                        }
                    }
                    catch (error) {
                        setStorageCleanupMessage(`清理失败：${errorText(error)}`);
                        toastError(error);
                    }
                    finally {
                        setStorageCleanupBusy(false);
                    }
                })();
            }, onCancel: () => { } }));
    }, [storageCleanupBusy]);
    const onSaveBaiduApp = SP_REACT.useCallback(async () => {
        if (baiduBusy)
            return;
        setBaiduBusy(true);
        try {
            const result = await withTimeout(setBaiduOpenapiApp({ app_key: baiduAppKey, secret_key: baiduSecretKey }), 15000, "保存百度应用超时");
            if (result.status !== "success")
                throw new Error(result.message || "保存百度应用失败");
            setBaiduLogin(result.data || EMPTY_BAIDU_OPENAPI_STATE);
            toaster.toast({ title: "freedeckCY", body: "百度开放平台应用已保存" });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setBaiduBusy(false);
        }
    }, [baiduAppKey, baiduBusy, baiduSecretKey]);
    const onBaiduAuthorize = SP_REACT.useCallback(async () => {
        if (baiduBusy)
            return;
        setBaiduBusy(true);
        try {
            const result = await withTimeout(getBaiduOpenapiAuthorizeUrl(), 15000, "获取百度授权链接超时");
            if (result.status !== "success")
                throw new Error(result.message || "获取百度授权链接失败");
            const url = String(result.url || result.data?.url || "");
            if (!url)
                throw new Error("百度授权链接为空");
            openExternalUrl(url);
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setBaiduBusy(false);
        }
    }, [baiduBusy]);
    const onExchangeBaiduCode = SP_REACT.useCallback(async () => {
        if (baiduBusy)
            return;
        setBaiduBusy(true);
        try {
            const result = await withTimeout(exchangeBaiduOpenapiCode({ code: baiduAuthCode }), 20000, "百度授权超时");
            if (result.status !== "success")
                throw new Error(result.message || "百度授权失败");
            setBaiduLogin(result.data || EMPTY_BAIDU_OPENAPI_STATE);
            setBaiduAuthCode("");
            toaster.toast({ title: "freedeckCY", body: "百度网盘授权成功" });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setBaiduBusy(false);
        }
    }, [baiduAuthCode, baiduBusy]);
    const onClearBaiduLogin = SP_REACT.useCallback(async () => {
        if (baiduBusy)
            return;
        setBaiduBusy(true);
        try {
            const result = await withTimeout(clearBaiduOpenapiLogin(), 15000, "清除百度授权超时");
            if (result.status !== "success")
                throw new Error(result.message || "清除百度授权失败");
            setBaiduLogin(result.data || EMPTY_BAIDU_OPENAPI_STATE);
            toaster.toast({ title: "freedeckCY", body: "已清除百度网盘授权" });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setBaiduBusy(false);
        }
    }, [baiduBusy]);
    const onStartCloudSaveUpload = SP_REACT.useCallback(async () => {
        if (startingCloudSaveUpload)
            return;
        setStartingCloudSaveUpload(true);
        try {
            const result = await withTimeout(startTianyiCloudSaveUpload(), 20000, "启动云存档上传超时");
            if (result.status !== "success") {
                throw new Error(result.message || "启动云存档上传失败");
            }
            const data = result.data;
            if (data?.state) {
                setCloudSaveUploadState(normalizeCloudSaveUploadState(data.state));
            }
            toaster.toast({ title: "freedeckCY", body: String(data?.message || "云存档上传任务已启动") });
            await refreshCloudSaveUploadStatus();
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setStartingCloudSaveUpload(false);
        }
    }, [refreshCloudSaveUploadStatus, startingCloudSaveUpload]);
    const onLoadRestoreEntries = SP_REACT.useCallback(async () => {
        if (loadingRestoreEntries)
            return;
        if (!selectedRestoreGame || !selectedRestoreVersion) {
            toaster.toast({ title: "freedeckCY", body: "请先选择游戏和版本" });
            return;
        }
        setLoadingRestoreEntries(true);
        try {
            const result = await withTimeout(listTianyiCloudSaveRestoreEntries({
                game_id: String(selectedRestoreGame.game_id || ""),
                game_key: String(selectedRestoreGame.game_key || ""),
                game_title: String(selectedRestoreGame.game_title || ""),
                version_name: String(selectedRestoreVersion || ""),
            }), 25000, "读取可选存档项超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "读取存档项失败");
            }
            const rows = Array.isArray(result.data.entries) ? result.data.entries : [];
            setRestoreEntries(rows);
            setSelectedRestoreEntryIds(rows.map((item) => String(item.entry_id || "")).filter(Boolean));
            setTargetCandidates([]);
            setSelectedRestoreTargetDir("");
            toaster.toast({ title: "freedeckCY", body: `已读取存档项 ${rows.length} 个` });
            await refreshCloudSaveRestoreStatus();
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setLoadingRestoreEntries(false);
        }
    }, [loadingRestoreEntries, refreshCloudSaveRestoreStatus, selectedRestoreGame, selectedRestoreVersion]);
    const toggleRestoreEntry = SP_REACT.useCallback((entryId, checked) => {
        const id = String(entryId || "").trim();
        if (!id)
            return;
        setSelectedRestoreEntryIds((prev) => {
            const set = new Set(prev.map((item) => String(item || "").trim()).filter(Boolean));
            if (checked)
                set.add(id);
            else
                set.delete(id);
            return Array.from(set);
        });
    }, []);
    const runRestoreApply = SP_REACT.useCallback(async (planId, confirmOverwrite) => {
        const normalizedPlanId = String(planId || "").trim();
        if (!normalizedPlanId)
            return;
        setApplyingRestore(true);
        try {
            const result = await withTimeout(applyTianyiCloudSaveRestore({
                plan_id: normalizedPlanId,
                confirm_overwrite: Boolean(confirmOverwrite),
            }), 120000, "执行恢复超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "执行恢复失败");
            }
            toaster.toast({ title: "freedeckCY", body: String(result.data.message || "恢复流程已结束") });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setApplyingRestore(false);
            try {
                await refreshCloudSaveRestoreStatus();
            }
            catch {
                // 恢复已执行；状态刷新失败不向上抛出，避免未处理的 Promise 拒绝。
            }
        }
    }, [refreshCloudSaveRestoreStatus]);
    const onStartCloudSaveRestore = SP_REACT.useCallback(async () => {
        if (planningRestore || applyingRestore)
            return;
        if (!selectedRestoreGame || !selectedRestoreVersion) {
            toaster.toast({ title: "freedeckCY", body: "请先选择要恢复的游戏和版本" });
            return;
        }
        if (!restoreEntries.length) {
            toaster.toast({ title: "freedeckCY", body: "请先读取存档项" });
            return;
        }
        if (!selectedRestoreEntryIds.length) {
            toaster.toast({ title: "freedeckCY", body: "请至少选择一个存档项" });
            return;
        }
        setPlanningRestore(true);
        try {
            const result = await withTimeout(planTianyiCloudSaveRestore({
                game_id: String(selectedRestoreGame.game_id || ""),
                game_key: String(selectedRestoreGame.game_key || ""),
                game_title: String(selectedRestoreGame.game_title || ""),
                version_name: String(selectedRestoreVersion || ""),
                selected_entry_ids: selectedRestoreEntryIds,
                target_dir: String(selectedRestoreTargetDir || ""),
            }), 30000, "生成恢复计划超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "生成恢复计划失败");
            }
            const plan = result.data;
            const nextCandidates = Array.isArray(plan.target_candidates) ? plan.target_candidates : [];
            setTargetCandidates(nextCandidates);
            if (nextCandidates.length === 1) {
                setSelectedRestoreTargetDir(nextCandidates[0]);
            }
            else if (nextCandidates.length > 1 && !selectedRestoreTargetDir) {
                setSelectedRestoreTargetDir(nextCandidates[0]);
            }
            if (!plan.accepted) {
                toaster.toast({ title: "freedeckCY", body: String(plan.message || "请先完成恢复前置步骤") });
                await refreshCloudSaveRestoreStatus();
                return;
            }
            const planId = String(plan.plan_id || "");
            if (!planId) {
                throw new Error("恢复计划缺少 plan_id");
            }
            if (plan.requires_confirmation) {
                const samples = Array.isArray(plan.conflict_samples) ? plan.conflict_samples.slice(0, 5) : [];
                DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, { strTitle: "\u786E\u8BA4\u8986\u76D6\u5B58\u6863", strDescription: `检测到 ${Number(plan.conflict_count || 0)} 个冲突文件，确认后会覆盖原有存档。` +
                        (samples.length ? `\n\n示例：\n${samples.join("\n")}` : ""), strOKButtonText: "\u786E\u8BA4\u8986\u76D6", strCancelButtonText: "\u53D6\u6D88", onOK: () => {
                        void runRestoreApply(planId, true);
                    }, onCancel: () => {
                        void runRestoreApply(planId, false);
                    } }));
            }
            else {
                await runRestoreApply(planId, false);
            }
            await refreshCloudSaveRestoreStatus();
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setPlanningRestore(false);
        }
    }, [
        applyingRestore,
        planningRestore,
        refreshCloudSaveRestoreStatus,
        restoreEntries.length,
        runRestoreApply,
        selectedRestoreEntryIds,
        selectedRestoreGame,
        selectedRestoreTargetDir,
        selectedRestoreVersion,
    ]);
    const cloudSaveSummaryText = SP_REACT.useMemo(() => {
        const current = cloudSaveUploadState;
        if (current.running) {
            const stage = cloudSaveStageText(current.stage);
            return `${stage}：${current.processed_games}/${current.total_games}，成功 ${current.uploaded}，跳过 ${current.skipped}，失败 ${current.failed}`;
        }
        const last = current.last_result;
        if (last && Number(last.finished_at || 0) > 0) {
            const stage = cloudSaveStageText(last.stage);
            return `最近一次：${stage}，成功 ${last.uploaded}，跳过 ${last.skipped}，失败 ${last.failed}`;
        }
        return "尚未执行云存档上传";
    }, [cloudSaveUploadState]);
    const cloudSaveRestoreSummaryText = SP_REACT.useMemo(() => {
        const current = cloudSaveRestoreState;
        if (current.running) {
            const stage = cloudSaveStageText(current.stage);
            return `${stage}：已恢复 ${current.restored_files} 个文件`;
        }
        const last = current.last_result;
        if (last && String(last.message || "").trim()) {
            return `最近一次：${last.message}`;
        }
        return "尚未执行云存档恢复";
    }, [cloudSaveRestoreState]);
    const restoreGameOptions = SP_REACT.useMemo(() => restoreOptions.map((item) => ({
        data: item.game_key,
        label: item.available
            ? `${item.game_title}（${item.versions.length} 个版本）`
            : `${item.game_title}（不可恢复：${item.reason || "无可用版本"}）`,
    })), [restoreOptions]);
    const restoreBusy = saving ||
        clearingLogin ||
        loadingRestoreOptions ||
        loadingRestoreEntries ||
        planningRestore ||
        applyingRestore ||
        cloudSaveRestoreState.running;
    const onUpdateCatalog = SP_REACT.useCallback(async () => {
        if (updatingCatalog)
            return;
        setUpdatingCatalog(true);
        setCatalogUpdateMessage("正在下载服务器最新目录...");
        try {
            const result = await withTimeout(updateTianyiCatalog(), 90000, "更新游戏列表超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "更新游戏列表失败");
            }
            const total = Number(result.data.total || 0);
            if (result.data.updated === false) {
                setCatalogUpdateMessage(`已是最新：${total} 条（服务器没有更新）`);
                toaster.toast({ title: "freedeckCY", body: "游戏列表已是最新，无需下载" });
            }
            else {
                const addedCount = Number(result.data.added_count || 0);
                setCatalogUpdateMessage(`已更新：${total} 条${addedCount > 0 ? `，新增 ${addedCount} 个游戏` : ""}（${result.data.source || "csv"}）`);
                toaster.toast({ title: "freedeckCY", body: `游戏列表已更新：${total} 条${addedCount > 0 ? `，新增 ${addedCount}` : ""}` });
            }
            await refreshSettings();
        }
        catch (error) {
            const message = errorText(error);
            setCatalogUpdateMessage(`更新失败：${message}`);
            toastError(error);
        }
        finally {
            setUpdatingCatalog(false);
        }
    }, [refreshSettings, updatingCatalog]);
    const tabs = SP_REACT.useMemo(() => [
        {
            id: "paths",
            title: "路径",
            content: (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsxs(DFL.PanelSection, { title: "\u6E38\u620F\u76EE\u5F55", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: "\u4ECE\u670D\u52A1\u5668\u4E0B\u8F7D\u6700\u65B0\u7684\u6E38\u620F\u76EE\u5F55 CSV \u5230\u672C\u5730\uFF1B\u4E0B\u8F7D\u6210\u529F\u540E\u4F1A\u7ACB\u5373\u91CD\u65B0\u52A0\u8F7D\u3002" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.TextField, { label: "\u76EE\u5F55\u670D\u52A1\u5668 CSV \u5730\u5740\uFF08\u7559\u7A7A\u7528\u9ED8\u8BA4 GitHub\uFF09", value: settings.catalog_url, onChange: (event) => setSettings((prev) => ({ ...prev, catalog_url: getTextFieldValue(event) })) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => savePatch({ catalog_url: settings.catalog_url }), disabled: saving, children: "\u4FDD\u5B58\u76EE\u5F55\u5730\u5740" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void onUpdateCatalog(), disabled: updatingCatalog || saving, children: updatingCatalog ? "正在检查..." : "检查并更新游戏列表" }) }), catalogUpdateMessage ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "11px", lineHeight: 1.45, opacity: 0.8 }, children: catalogUpdateMessage }) })) : null] }), SP_JSX.jsxs(DFL.PanelSection, { title: "\u4E0B\u8F7D\u76EE\u5F55", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: settings.download_dir || "未设置" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onPickDownloadDir, disabled: saving, children: "\u9009\u62E9\u4E0B\u8F7D\u76EE\u5F55" }) }), storageOptions.filter((item) => item.kind === "internal").map((item) => (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs(DFL.ButtonItem, { layout: "below", onClick: () => void onUseStorage(item, "download_dir"), disabled: saving, children: ["\u4E0B\u8F7D\u5230 ", item.label, "\uFF08\u5269\u4F59 ", item.free_text, "\uFF09"] }) }, `download-${item.mount}`))), storageOptions.filter((item) => item.kind === "external").map((item) => (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs(DFL.ButtonItem, { layout: "below", onClick: () => void onUseStorage(item, "download_dir"), disabled: saving, children: ["\u4E0B\u8F7D\u5230 ", item.label, "\uFF08\u5269\u4F59 ", item.free_text, "\uFF09"] }) }, `download-${item.mount}`))), !storageOptions.some((item) => item.kind === "external") ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "11px", opacity: 0.75 }, children: "\u672A\u68C0\u6D4B\u5230\u53EF\u5199 SD \u5361/\u5916\u7F6E\u5B58\u50A8\uFF08\u8BF7\u5148\u5728 SteamOS/\u7CFB\u7EDF\u4E2D\u6302\u8F7D\uFF09" }) })) : null] }), SP_JSX.jsxs(DFL.PanelSection, { title: "\u5B89\u88C5\u76EE\u5F55", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: settings.install_dir || "未设置" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onPickInstallDir, disabled: saving, children: "\u9009\u62E9\u5B89\u88C5\u76EE\u5F55" }) }), storageOptions.filter((item) => item.kind === "internal").map((item) => (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs(DFL.ButtonItem, { layout: "below", onClick: () => void onUseStorage(item, "install_dir"), disabled: saving, children: ["\u5B89\u88C5\u5230 ", item.label, "\uFF08\u5269\u4F59 ", item.free_text, "\uFF09"] }) }, `install-${item.mount}`))), storageOptions.filter((item) => item.kind === "external").map((item) => (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs(DFL.ButtonItem, { layout: "below", onClick: () => void onUseStorage(item, "install_dir"), disabled: saving, children: ["\u5B89\u88C5\u5230 ", item.label, "\uFF08\u5269\u4F59 ", item.free_text, "\uFF09"] }) }, `install-${item.mount}`)))] })] })),
        },
        {
            id: "cleanup",
            title: "清理",
            content: SP_JSX.jsx(StorageCleanupSection, { report: storageCleanupReport, busy: storageCleanupBusy, message: storageCleanupMessage, onScan: onScanStorageCleanup, onClean: onCleanStorageCleanup }),
        },
        {
            id: "install",
            title: "安装",
            content: (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsxs(DFL.PanelSection, { title: "\u5B89\u88C5\u884C\u4E3A", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ToggleField, { label: "\u5B89\u88C5\u540E\u81EA\u52A8\u5220\u9664\u538B\u7F29\u5305", description: "\u4EC5\u5728\u81EA\u52A8\u5B89\u88C5\u6210\u529F\u540E\u751F\u6548", checked: Boolean(settings.auto_delete_package), onChange: (value) => savePatch({ auto_delete_package: value }), disabled: saving }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5, opacity: 0.86 }, children: "\u4E0B\u8F7D\u5B8C\u6210\u540E\u81EA\u52A8\u5B89\u88C5\u5DF2\u56FA\u5B9A\u5F00\u542F\u3002" }) })] }), SP_JSX.jsxs(DFL.PanelSection, { title: "\u626B\u63CF\u5DF2\u5B89\u88C5", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5, opacity: 0.86 }, children: "\u626B\u63CF\u8BBE\u7F6E\u91CC\u7684\u5B89\u88C5\u76EE\u5F55\u4E00\u5C42\uFF0C\u628A\u76EE\u5F55\u540D\u5339\u914D\u6807\u9898\u7684\u6E38\u620F\u8865\u56DE\u5217\u8868\uFF1BSteam \u91CC\u6CA1\u6709\u7684\u4F1A\u81EA\u52A8\u521B\u5EFA\u5FEB\u6377\u65B9\u5F0F\u3002" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onScanInstalledSettings, disabled: scanningInstalled || saving, children: scanningInstalled ? "扫描中..." : "扫描已安装游戏" }) })] })] })),
        },
        {
            id: "preflight",
            title: "环境",
            content: SP_JSX.jsx(InstallPreflightSection, { report: preflightReport, busy: preflightBusy, onRun: onRunPreflight }),
        },
        {
            id: "download",
            title: "下载",
            content: (SP_JSX.jsxs(DFL.PanelSection, { title: "\u4E0B\u8F7D\u53C2\u6570", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.SliderField, { label: "aria2 \u5206\u7247\u6570", description: "\u5EFA\u8BAE 8~32\uFF0C\u8303\u56F4 1~64", value: Math.max(1, Math.min(64, Number(splitDraft || 16))), min: 1, max: 64, step: 1, showValue: true, editableValue: true, onChange: (value) => setSplitDraft(Math.max(1, Math.min(64, Number(value || 1)))), disabled: saving }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.DropdownItem, { label: "\u5206\u9875\u6570\u91CF", description: "\u6E38\u620F\u5217\u8868\u6BCF\u9875\u663E\u793A\u6761\u6570", rgOptions: PAGE_SIZE_OPTIONS, selectedOption: Math.max(10, Math.min(200, Number(settings.page_size || 50))), disabled: saving, onChange: (option) => {
                                const nextValue = Math.max(10, Math.min(200, Number(option?.data || 50)));
                                if (nextValue === Number(settings.page_size || 50))
                                    return;
                                void savePatch({ page_size: nextValue }, `分页数量已更新：${nextValue} / 页`);
                            } }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onSaveSplit, disabled: saving, children: "\u4FDD\u5B58\u4E0B\u8F7D\u53C2\u6570" }) })] })),
        },
        {
            id: "account",
            title: "账号",
            content: (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsxs(DFL.PanelSection, { title: "\u5929\u7FFC\u4E91\u8D26\u53F7", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: login.logged_in
                                        ? `当前已登录：${login.user_account || "未知账号"}`
                                        : "当前未登录" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onClearLogin, disabled: clearingLogin || saving || !login.logged_in, children: clearingLogin ? "注销中..." : "注销天翼云账号" }) })] }), SP_JSX.jsxs(DFL.PanelSection, { title: "\u767E\u5EA6\u7F51\u76D8\uFF08\u626B\u7801\u767B\u5F55\uFF09", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: baiduWebLogin.logged_in
                                        ? `已登录：${baiduWebLogin.user_account || "百度账号"}`
                                        : "未登录（扫码后使用 BDUSS/Cookie，无需开放平台 App Key）" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void onCheckBaiduHealth(), disabled: checkingBaiduHealth || !baiduWebLogin.logged_in, children: checkingBaiduHealth ? "检查中..." : "检查登录状态" }) }), baiduHealth ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "4px", width: "100%", fontSize: "11px", lineHeight: 1.5 }, children: [SP_JSX.jsx("div", { style: { color: baiduHealth.ok ? "#9fe6a8" : "#ffb4a8", fontWeight: 600 }, children: baiduHealth.message || "检查完成" }), ...(Array.isArray(baiduHealth.checks) ? baiduHealth.checks.map((check, index) => (SP_JSX.jsx("div", { style: { color: check.status === "fail" ? "#ffb4a8" : check.status === "warn" ? "#ffd479" : "#b9c9d8" }, children: `${check.label || check.id || "检查"}：${check.detail || ""}` }, `${check.id || "check"}-${index}`))) : [])] }) })) : null, baiduQr.stage === "failed" || baiduQr.stage === "expired" ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", color: "#ffb4a8", lineHeight: 1.5 }, children: baiduQr.message || "扫码失败，请重试" }) })) : null, baiduQr.stage === "waiting" || baiduQr.stage === "scanned" ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "8px", alignItems: "center" }, children: [baiduQr.qr_data_url ? (SP_JSX.jsx("img", { src: baiduQr.qr_data_url, alt: "\u767E\u5EA6\u626B\u7801\u767B\u5F55", style: { width: "180px", height: "180px", background: "#fff", padding: "8px", borderRadius: "8px" } })) : (SP_JSX.jsxs("div", { style: { fontSize: "12px" }, children: ["\u4E8C\u7EF4\u7801\u56FE\u7247\u52A0\u8F7D\u5931\u8D25\uFF0C\u8BF7\u6253\u5F00\uFF1A", SP_JSX.jsx("div", { style: { wordBreak: "break-all" }, children: baiduQr.qrcode_url })] })), SP_JSX.jsx("div", { style: { fontSize: "12px" }, children: baiduQr.message || "请用百度 App 扫码" }), SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onCancelBaiduQr, children: "\u53D6\u6D88\u626B\u7801" })] }) })) : (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onStartBaiduQr, disabled: baiduQrBusy, children: baiduQrBusy ? "获取中..." : "扫码登录百度网盘" }) })), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onClearBaiduWeb, disabled: baiduQrBusy || !baiduWebLogin.logged_in, children: "\u9000\u51FA\u767E\u5EA6\u7F51\u76D8" }) })] }), SP_JSX.jsxs(DFL.PanelSection, { title: "\u767E\u5EA6\u7F51\u76D8 OpenAPI\uFF08\u53EF\u9009\uFF0C\u9700\u5F00\u53D1\u8005\u8D44\u8D28\uFF09", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: baiduLogin.logged_in
                                        ? `已授权：${baiduLogin.user_account || "百度账号"}`
                                        : baiduLogin.configured
                                            ? "已配置应用，待授权"
                                            : "未配置（去百度网盘开放平台创建应用）" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.TextField, { label: "App Key", value: baiduAppKey, onChange: (event) => setBaiduAppKey(getTextFieldValue(event)) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.TextField, { label: "Secret Key", value: baiduSecretKey, bIsPassword: true, onChange: (event) => setBaiduSecretKey(getTextFieldValue(event)) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onSaveBaiduApp, disabled: baiduBusy, children: "\u4FDD\u5B58\u5E94\u7528" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onBaiduAuthorize, disabled: baiduBusy || !baiduLogin.configured, children: "\u83B7\u53D6\u6388\u6743\u94FE\u63A5" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.TextField, { label: "\u6388\u6743\u7801", description: "\u7C98\u8D34\u767E\u5EA6\u8FD4\u56DE\u7684\u6388\u6743\u7801", value: baiduAuthCode, onChange: (event) => setBaiduAuthCode(getTextFieldValue(event)) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onExchangeBaiduCode, disabled: baiduBusy || !baiduAuthCode.trim(), children: "\u5B8C\u6210\u6388\u6743" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onClearBaiduLogin, disabled: baiduBusy || !baiduLogin.logged_in, children: "\u6E05\u9664\u767E\u5EA6\u6388\u6743" }) })] }), SP_JSX.jsxs(DFL.PanelSection, { title: "\u4E91\u5B58\u6863\u4E0A\u4F20", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ToggleField, { label: "\u6E38\u620F\u9000\u51FA\u540E\u81EA\u52A8\u4E0A\u4F20", description: "\u540E\u53F0\u68C0\u6D4B\u6E38\u620F\u8FDB\u7A0B\uFF0C\u9000\u51FA\u540E\u81EA\u52A8\u6253\u5305\u4E0A\u4F20\uFF1B\u9ED8\u8BA4\u5F00\u542F", checked: Boolean(settings.cloud_save_auto_upload), onChange: (value) => savePatch({ cloud_save_auto_upload: value }), disabled: saving }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ToggleField, { label: "\u5305\u542B\u6A21\u62DF\u5668\u5B58\u6863", description: "GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch \u7684\u5B58\u6863\u4E0E\u8BB0\u5FC6\u5361", checked: Boolean(settings.cloud_save_include_emulators), onChange: (value) => savePatch({ cloud_save_include_emulators: value }), disabled: saving }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onStartCloudSaveUpload, disabled: saving || clearingLogin || startingCloudSaveUpload || !login.logged_in || cloudSaveUploadState.running, children: startingCloudSaveUpload
                                        ? "启动中..."
                                        : cloudSaveUploadState.running
                                            ? "上传进行中..."
                                            : "上传云存档" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: cloudSaveSummaryText }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "11px", lineHeight: 1.5, opacity: 0.88 }, children: `${cloudSaveUploadState.message || "未开始"} | ${clampProgress(cloudSaveUploadState.progress).toFixed(1)}%` }) })] }), SP_JSX.jsxs(DFL.PanelSection, { title: "\u4E91\u5B58\u6863\u4E0B\u8F7D\u6062\u590D", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: refreshRestoreOptions, disabled: !login.logged_in || restoreBusy, children: loadingRestoreOptions ? "刷新中..." : "刷新云存档列表" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.DropdownItem, { label: "\u9009\u62E9\u6E38\u620F", description: "\u6309\u6E38\u620F\u5206\u7EC4\u663E\u793A\u4E91\u7AEF\u7248\u672C", rgOptions: restoreGameOptions, selectedOption: selectedRestoreGameKey, disabled: !login.logged_in || restoreBusy || restoreGameOptions.length <= 0, onChange: (option) => setSelectedRestoreGameKey(String(option?.data || "")) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.DropdownItem, { label: "\u9009\u62E9\u7248\u672C\u65F6\u95F4", description: "\u6309\u65F6\u95F4\u5012\u5E8F", rgOptions: restoreVersionOptions, selectedOption: selectedRestoreVersion, disabled: !login.logged_in || restoreBusy || !selectedRestoreGame || restoreVersionOptions.length <= 0, onChange: (option) => setSelectedRestoreVersion(String(option?.data || "")) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onLoadRestoreEntries, disabled: !login.logged_in || restoreBusy || !selectedRestoreGame || !selectedRestoreVersion, children: loadingRestoreEntries ? "读取中..." : "读取可选存档项" }) }), restoreEntries.length > 0 &&
                                restoreEntries.map((entry) => {
                                    const entryId = String(entry.entry_id || "");
                                    const checked = selectedRestoreEntryIds.includes(entryId);
                                    return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ToggleField, { label: `${entry.entry_name || entryId}${entry.file_count ? `（${entry.file_count} 文件）` : ""}`, checked: checked, onChange: (value) => toggleRestoreEntry(entryId, value), disabled: restoreBusy }) }, `restore_entry_${entryId}`));
                                }), restoreEntries.length > 0 && (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { display: "flex", gap: "8px", width: "100%" }, children: [SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => {
                                                setSelectedRestoreEntryIds(restoreEntries.map((item) => String(item.entry_id || "")).filter(Boolean));
                                            }, disabled: restoreBusy, children: "\u5168\u9009" }), SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => setSelectedRestoreEntryIds([]), disabled: restoreBusy, children: "\u6E05\u7A7A" })] }) })), targetCandidates.length > 1 && (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.DropdownItem, { label: "\u6062\u590D\u76EE\u6807\u76EE\u5F55", description: "\u68C0\u6D4B\u5230\u591A\u4E2A\u5019\u9009\u76EE\u5F55\uFF0C\u8BF7\u660E\u786E\u9009\u62E9", rgOptions: targetCandidates.map((path) => ({ data: path, label: path })), selectedOption: selectedRestoreTargetDir, disabled: restoreBusy, onChange: (option) => setSelectedRestoreTargetDir(String(option?.data || "")) }) })), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onStartCloudSaveRestore, disabled: !login.logged_in || restoreBusy || !selectedRestoreGame || !selectedRestoreVersion || !selectedRestoreEntryIds.length, children: planningRestore ? "规划中..." : applyingRestore ? "恢复中..." : "下载并恢复云存档" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: cloudSaveRestoreSummaryText }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "11px", lineHeight: 1.5, opacity: 0.88 }, children: `${cloudSaveRestoreState.message || "未开始"} | ${clampProgress(cloudSaveRestoreState.progress).toFixed(1)}%` }) })] })] })),
        },
        {
            id: "diagnostics",
            title: "诊断",
            content: (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsxs(DFL.PanelSection, { title: "\u63D2\u4EF6\u66F4\u65B0", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.6, opacity: 0.88 }, children: updateInfo
                                        ? `当前 ${updateInfo.current || "?"} · 最新 ${updateInfo.latest || "?"}`
                                        : "检查自有服务器/GitHub；可直接交给 Decky 安装（需在 Decky 弹窗确认），也可只下载更新包手动安装。" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs(DFL.Focusable, { "flow-children": "row", style: { display: "flex", gap: "8px", width: "100%", alignItems: "center" }, children: [SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onCheckUpdate(), disabled: checkingUpdate || downloadingUpdate, style: { width: "auto", minWidth: "120px", padding: "8px 14px", flex: "0 0 auto" }, children: checkingUpdate ? "检查中..." : "检查更新" }), updateInfo?.has_update ? (SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onInstallUpdate(), disabled: installingUpdate || downloadingUpdate, style: { width: "auto", minWidth: "120px", padding: "8px 14px", flex: "0 0 auto" }, children: installingUpdate ? "准备中..." : "安装更新" })) : null, updateInfo?.has_update ? (SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onDownloadUpdate(), disabled: downloadingUpdate || installingUpdate, style: { width: "auto", minWidth: "120px", padding: "8px 14px", flex: "0 0 auto" }, children: downloadingUpdate ? "下载中..." : "下载更新包" })) : null] }) }), updateMessage ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "11px", lineHeight: 1.5, color: updateInfo?.has_update ? "#ffd479" : "#b9c0cc", wordBreak: "break-word" }, children: updateMessage }) })) : null] }), SP_JSX.jsxs(DFL.PanelSection, { title: "\u63D2\u4EF6\u81EA\u68C0", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.6, opacity: 0.88 }, children: "\u68C0\u67E5\u63D2\u4EF6\u7248\u672C\u3001\u72B6\u6001/\u4E0B\u8F7D/\u5B89\u88C5\u76EE\u5F55\u3001aria2/7zz/node\u3001Steam \u5FEB\u6377\u65B9\u5F0F\u3001SD \u5361\u3001\u7F51\u7EDC\u4E0E\u767E\u5EA6\u626B\u7801\u63A5\u53E3\u3002" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void onRunDiagnostics(), disabled: diagnosticsBusy, children: diagnosticsBusy ? "自检中..." : "运行自检" }) }), diagnosticsError ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.6, color: "#ffb4a8", wordBreak: "break-word" }, children: `自检失败：${diagnosticsError}` }) })) : null, diagnosticsReport ? (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.6 }, children: `v${diagnosticsReport.version || "?"} · ${diagnosticsReport.arch || "-"} · OK ${diagnosticsReport.summary?.ok || 0} / 警告 ${diagnosticsReport.summary?.warn || 0} / 失败 ${diagnosticsReport.summary?.fail || 0} / 跳过 ${diagnosticsReport.summary?.skip || 0}` }) }), (diagnosticsReport.checks || []).map((check, checkIndex) => {
                                        const status = String(check.status || "skip").toLowerCase();
                                        const color = status === "ok"
                                            ? "#9fe6a8"
                                            : status === "warn"
                                                ? "#ffd479"
                                                : status === "fail"
                                                    ? "#ff9a8a"
                                                    : "#b9c0cc";
                                        return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "3px", width: "100%" }, children: [SP_JSX.jsxs("div", { style: { display: "flex", justifyContent: "space-between", gap: "8px" }, children: [SP_JSX.jsx("span", { style: { fontWeight: 600 }, children: check.label || check.id || "-" }), SP_JSX.jsx("span", { style: { color, fontSize: "12px" }, children: status.toUpperCase() })] }), SP_JSX.jsx("div", { style: { fontSize: "12px", opacity: 0.86, wordBreak: "break-word" }, children: check.detail }), check.fix && status !== "ok" ? (SP_JSX.jsx("div", { style: { fontSize: "11px", opacity: 0.7 }, children: `建议：${check.fix}` })) : null] }) }, check.id || `diagnostic-${checkIndex}`));
                                    })] })) : null] }), SP_JSX.jsxs(DFL.PanelSection, { title: "\u8BCA\u65AD\u5305", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.6, opacity: 0.88 }, children: "\u5BFC\u51FA diagnostics.json\u3001self-check.json\u3001\u6700\u65B0 300 \u884C\u65E5\u5FD7\uFF1Bcookie/token \u5DF2\u8131\u654F\uFF0C\u5199\u5230\u4E0B\u8F7D\u76EE\u5F55\u3002" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void onExportDiagnostics(), disabled: diagnosticsExportBusy, children: diagnosticsExportBusy ? "打包中..." : "导出诊断包" }) }), diagnosticsExportMessage ? (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "11px", opacity: 0.82, wordBreak: "break-all" }, children: diagnosticsExportMessage }) })) : null] })] })),
        },
    ], [
        clearingLogin,
        login.logged_in,
        login.user_account,
        onPickDownloadDir,
        onPickInstallDir,
        onUseStorage,
        onClearLogin,
        onStartCloudSaveUpload,
        onSaveSplit,
        savePatch,
        saving,
        cloudSaveSummaryText,
        cloudSaveUploadState.message,
        cloudSaveUploadState.progress,
        cloudSaveUploadState.running,
        startingCloudSaveUpload,
        settings.auto_delete_package,
        settings.page_size,
        settings.download_dir,
        settings.install_dir,
        settings.cloud_save_auto_upload,
        settings.cloud_save_include_emulators,
        settings.catalog_url,
        settings.download_speed_limit,
        splitDraft,
        refreshRestoreOptions,
        restoreBusy,
        loadingRestoreOptions,
        restoreGameOptions,
        selectedRestoreGameKey,
        selectedRestoreVersion,
        selectedRestoreGame,
        restoreVersionOptions,
        onLoadRestoreEntries,
        loadingRestoreEntries,
        restoreEntries,
        selectedRestoreEntryIds,
        toggleRestoreEntry,
        targetCandidates,
        selectedRestoreTargetDir,
        onStartCloudSaveRestore,
        planningRestore,
        applyingRestore,
        cloudSaveRestoreSummaryText,
        cloudSaveRestoreState.message,
        cloudSaveRestoreState.progress,
        updateInfo,
        checkingUpdate,
        downloadingUpdate,
        installingUpdate,
        onInstallUpdate,
        updateMessage,
        onCheckUpdate,
        onDownloadUpdate,
        diagnosticsReport,
        diagnosticsBusy,
        diagnosticsExportBusy,
        diagnosticsExportMessage,
        diagnosticsError,
        onRunDiagnostics,
        onExportDiagnostics,
        storageOptions,
        baiduQr,
        baiduQrBusy,
        baiduWebLogin,
        baiduHealth,
        checkingBaiduHealth,
        onCheckBaiduHealth,
        baiduLogin,
        baiduAppKey,
        baiduSecretKey,
        baiduAuthCode,
        baiduBusy,
        onStartBaiduQr,
        onCancelBaiduQr,
        onClearBaiduWeb,
        onSaveBaiduApp,
        onBaiduAuthorize,
        onExchangeBaiduCode,
        onClearBaiduLogin,
        scanningInstalled,
        onScanInstalledSettings,
        preflightReport,
        preflightBusy,
        onRunPreflight,
        storageCleanupReport,
        storageCleanupBusy,
        storageCleanupMessage,
        onScanStorageCleanup,
        onCleanStorageCleanup,
    ]);
    const focusSettingsTabRow = SP_REACT.useCallback((tabId) => {
        const classMap = getGamepadTabClassMap();
        if (!classMap || !settingsContainerRef.current)
            return;
        const tabClass = classMap.Tab;
        if (!tabClass)
            return;
        let target = null;
        if (tabId) {
            const tabTitle = String(tabs.find((tab) => tab.id === tabId)?.title || "").trim();
            if (tabTitle) {
                const elements = settingsContainerRef.current.querySelectorAll(`.${tabClass}`);
                for (const element of Array.from(elements)) {
                    const item = element;
                    if (String(item.textContent || "").trim() === tabTitle) {
                        target = item;
                        break;
                    }
                }
            }
        }
        if (!target) {
            const activeClass = classMap.Active || classMap.Selected;
            const selector = activeClass ? `.${tabClass}.${activeClass}` : `.${tabClass}`;
            target = settingsContainerRef.current.querySelector(selector);
        }
        target?.focus?.();
    }, [tabs]);
    SP_REACT.useEffect(() => {
        const classMap = getGamepadTabClassMap();
        if (!classMap)
            return;
        const rowClass = classMap.TabsRowScroll || classMap.TabRowTabs;
        if (!rowClass)
            return;
        const handle = window.requestAnimationFrame(() => {
            const root = settingsContainerRef.current;
            if (!root)
                return;
            const row = root.querySelector(`.${rowClass}`);
            if (!row)
                return;
            row.style.scrollBehavior = "auto";
            row.scrollLeft = 0;
        });
        return () => window.cancelAnimationFrame(handle);
    }, [activeTab]);
    const onShowSettingsTab = SP_REACT.useCallback((tabId) => {
        focusSettingsTabRow();
        setActiveTab(tabId);
        window.requestAnimationFrame(() => focusSettingsTabRow(tabId));
    }, [focusSettingsTabRow]);
    if (loading) {
        return (SP_JSX.jsx(DFL.PanelSection, { title: "freedeckCY \u8BBE\u7F6E", children: SP_JSX.jsx(DFL.PanelSectionRow, { children: "\u52A0\u8F7D\u4E2D..." }) }));
    }
    return (SP_JSX.jsxs("div", { ref: settingsContainerRef, "data-fdc-i18n": "1", className: "freedeckcy-settings-root", style: {
            paddingTop: 48,
            paddingBottom: 24,
            minHeight: "100%",
            boxSizing: "border-box",
            overflowX: "hidden",
        }, children: [SP_JSX.jsx("style", { children: tabStabilityCss }), SP_JSX.jsx(LanguageSection, { language: language }), SP_JSX.jsx(DFL.Tabs, { tabs: tabs, activeTab: activeTab, onShowTab: onShowSettingsTab, autoFocusContents: false })] }));
}
function tryRestartSteamViaClient() {
    try {
        const host = window;
        const top = host.top;
        const parent = host.parent;
        for (const candidate of [host.SteamClient, top?.SteamClient, parent?.SteamClient]) {
            const restart = candidate?.User?.StartRestart;
            if (typeof restart === "function") {
                restart(false);
                return true;
            }
        }
    }
    catch {
        // 忽略客户端重启 API 不可用。
    }
    return false;
}
function steamRestartKey(pending) {
    if (!pending)
        return "";
    return `${String(pending.game_id || "")}:${String(pending.app_id || "")}:${String(pending.title || "")}`;
}
async function tryRefreshSteamLibrary() {
    const client = window.SteamClient;
    const apps = client && client.Apps;
    if (!apps)
        return false;
    for (const methodName of ["Refresh", "RefreshApps", "RefreshLibrary"]) {
        const method = apps[methodName];
        if (typeof method !== "function")
            continue;
        try {
            await method.call(apps);
            return true;
        }
        catch { }
    }
    return false;
}
function LanguageChooser() {
    return (SP_JSX.jsxs(DFL.PanelSection, { title: "Language / 语言", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "13px", lineHeight: 1.5 }, children: "选择界面语言 / Choose your interface language" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs(DFL.Focusable, { "flow-children": "row", style: { display: "flex", gap: "8px", width: "100%" }, children: [SP_JSX.jsx(DFL.DialogButton, { onClick: () => setLanguage("zh"), style: { flex: "1 1 0", width: "auto", minWidth: 0, padding: "8px 10px" }, children: "中文" }), SP_JSX.jsx(DFL.DialogButton, { onClick: () => setLanguage("en"), style: { flex: "1 1 0", width: "auto", minWidth: 0, padding: "8px 10px" }, children: "English" })] }) })] }));
}
function LanguageSection({ language }) {
    return (SP_JSX.jsxs(DFL.PanelSection, { title: "Language / 语言", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", opacity: 0.8 }, children: "界面语言 / Interface language" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs(DFL.Focusable, { "flow-children": "row", style: { display: "flex", gap: "8px", width: "100%" }, children: [SP_JSX.jsx(DFL.DialogButton, { onClick: () => setLanguage("zh"), disabled: language === "zh", style: { flex: "1 1 0", width: "auto", minWidth: 0, padding: "8px 10px" }, children: "中文" }), SP_JSX.jsx(DFL.DialogButton, { onClick: () => setLanguage("en"), disabled: language === "en", style: { flex: "1 1 0", width: "auto", minWidth: 0, padding: "8px 10px" }, children: "English" })] }) })] }));
}
function Content() {
    const contentI18nRef = useI18nRoot();
    const [loading, setLoading] = SP_REACT.useState(true);
    const [state, setState] = SP_REACT.useState(EMPTY_STATE);
    const [openingLogin, setOpeningLogin] = SP_REACT.useState(false);
    const [uninstallingKey, setUninstallingKey] = SP_REACT.useState("");
    const [taskActionKey, setTaskActionKey] = SP_REACT.useState("");
    const [restartingSteam, setRestartingSteam] = SP_REACT.useState(false);
    const [refreshingSteamLibrary, setRefreshingSteamLibrary] = SP_REACT.useState(false);
    const [previewingKey, setPreviewingKey] = SP_REACT.useState("");
    const [batchBusy, setBatchBusy] = SP_REACT.useState("");
    const [speedDraft, setSpeedDraft] = SP_REACT.useState("0");
    const syncingRef = SP_REACT.useRef(false);
    const latestStateRef = SP_REACT.useRef(EMPTY_STATE);
    const catalogNoticeRef = SP_REACT.useRef("");
    const dismissedSteamRestartRef = SP_REACT.useRef(new Set());
    const syncState = SP_REACT.useCallback(async (pollMode = PANEL_POLL_MODE_IDLE) => {
        if (syncingRef.current)
            return;
        syncingRef.current = true;
        try {
            const result = await withTimeout(getTianyiPanelState({
                poll_mode: pollMode,
                visible: !document.hidden,
                has_focus: document.hasFocus(),
            }), PANEL_REQUEST_TIMEOUT_MS, "读取面板状态超时，请稍后重试");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "读取状态失败");
            }
            const next = result.data;
            const normalized = {
                login: next.login || EMPTY_STATE.login,
                installed: next.installed || EMPTY_STATE.installed,
                tasks: next.tasks || [],
                settings: Object.assign({}, EMPTY_SETTINGS, next.settings || {}),
                library_url: next.library_url || "",
                power_diagnostics: next.power_diagnostics || {},
                steam_restart: next.steam_restart || { pending: false },
                catalog_update_notice: next.catalog_update_notice || {},
            };
            if (normalized.steam_restart?.pending) {
                const key = steamRestartKey(normalized.steam_restart);
                if (key && dismissedSteamRestartRef.current.has(key)) {
                    normalized.steam_restart = { pending: false };
                }
            }
            latestStateRef.current = normalized;
            setState(normalized);
        }
        finally {
            syncingRef.current = false;
        }
    }, []);
    SP_REACT.useEffect(() => {
        const notice = state.catalog_update_notice || {};
        const count = Number(notice.added_count || 0);
        if (count <= 0)
            return;
        const key = `${notice.updated_at || 0}:${count}`;
        if (catalogNoticeRef.current === key)
            return;
        catalogNoticeRef.current = key;
        const titles = Array.isArray(notice.titles) ? notice.titles.filter(Boolean).slice(0, 3) : [];
        toaster.toast({
            title: "freedeckCY 目录已更新",
            body: `新增 ${count} 个游戏${titles.length ? `：${titles.join("、")}` : ""}`,
            duration: 6000,
        });
        void clearTianyiCatalogUpdateNotice().catch(() => undefined);
    }, [state.catalog_update_notice]);
    SP_REACT.useEffect(() => {
        let alive = true;
        let firstRun = true;
        let timer = 0;
        const clearTimer = () => {
            if (!timer)
                return;
            window.clearTimeout(timer);
            timer = 0;
        };
        const scheduleNext = () => {
            if (!alive)
                return;
            clearTimer();
            const mode = resolvePanelPollMode(latestStateRef.current);
            const delay = pollIntervalByMode(mode);
            timer = window.setTimeout(() => {
                void runPoll(false);
            }, delay);
        };
        const runPoll = async (showErrorToast) => {
            if (!alive)
                return;
            const mode = resolvePanelPollMode(latestStateRef.current);
            try {
                await syncState(mode);
            }
            catch (error) {
                if (showErrorToast && alive) {
                    toastError(error);
                }
            }
            finally {
                if (firstRun) {
                    firstRun = false;
                    if (alive)
                        setLoading(false);
                }
                scheduleNext();
            }
        };
        const handleVisibilityChange = () => {
            if (!alive)
                return;
            clearTimer();
            if (document.hidden) {
                scheduleNext();
                return;
            }
            void runPoll(false);
        };
        const handleFocus = () => {
            if (!alive)
                return;
            clearTimer();
            void runPoll(false);
        };
        const handleBlur = () => {
            if (!alive)
                return;
            clearTimer();
            scheduleNext();
        };
        void runPoll(true);
        document.addEventListener("visibilitychange", handleVisibilityChange);
        window.addEventListener("focus", handleFocus);
        window.addEventListener("blur", handleBlur);
        return () => {
            alive = false;
            clearTimer();
            document.removeEventListener("visibilitychange", handleVisibilityChange);
            window.removeEventListener("focus", handleFocus);
            window.removeEventListener("blur", handleBlur);
        };
    }, [syncState]);
    const onLogin = SP_REACT.useCallback(async () => {
        if (openingLogin)
            return;
        setOpeningLogin(true);
        try {
            const result = await withTimeout(getTianyiLoginUrl(), 20000, "获取登录地址超时，请稍后重试");
            if (result.status !== "success") {
                throw new Error(describeOpenError(result, "获取登录地址失败"));
            }
            openExternalUrl(result.url || result.data?.url || "");
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setOpeningLogin(false);
        }
    }, [openingLogin]);
    const onOpenLibrary = SP_REACT.useCallback(() => {
        try {
            DFL.Router.CloseSideMenus?.();
        }
        catch {
            // 忽略菜单关闭失败。
        }
        // 优先用 QAM 原生 Modal，避免路由未注册时被 Steam 当成网页路径。
        try {
            let modal = null;
            modal = DFL.showModal(SP_JSX.jsx(LibraryPage, { onClose: () => {
                    try {
                        modal?.Close();
                    }
                    catch {
                        // 忽略关闭失败。
                    }
                } }));
            return;
        }
        catch {
            // 继续尝试全屏路由。
        }
        try {
            DFL.Navigation.Navigate(LIBRARY_ROUTE);
        }
        catch (error) {
            toaster.toast({ title: "freedeckCY", body: `打开游戏库失败：${errorText(error)}` });
        }
    }, []);
    const onOpenSettings = SP_REACT.useCallback(() => {
        try {
            DFL.Router.CloseSideMenus?.();
        }
        catch {
            // 忽略菜单关闭失败。
        }
        try {
            DFL.Navigation.Navigate(SETTINGS_ROUTE);
        }
        catch (error) {
            toaster.toast({ title: "freedeckCY", body: `打开设置失败：${errorText(error)}` });
        }
    }, []);
    const installedGames = SP_REACT.useMemo(() => state.installed?.preview || [], [state.installed]);
    const installedGameIds = SP_REACT.useMemo(() => {
        const set = new Set();
        for (const item of installedGames) {
            const gameId = String(item.game_id || "").trim();
            if (gameId)
                set.add(gameId);
        }
        return set;
    }, [installedGames]);
    const visibleTasks = SP_REACT.useMemo(() => (state.tasks || []).filter((task) => {
        if (String(task.status || "").trim().toLowerCase() === "removed")
            return false;
        if (isTaskAlreadyInstalled(task))
            return false;
        const gameId = String(task.game_id || "").trim();
        if (gameId && installedGameIds.has(gameId))
            return false;
        return true;
    }), [installedGameIds, state.tasks]);
    const sortedInstalledGames = SP_REACT.useMemo(() => {
        const list = [...installedGames];
        list.sort((a, b) => String(a.title || "").localeCompare(String(b.title || ""), "zh-Hans-CN", {
            sensitivity: "base",
            numeric: true,
        }));
        return list;
    }, [installedGames]);
    const loginStatusText = SP_REACT.useMemo(() => {
        if (!state.login.logged_in)
            return "没登录";
        const account = String(state.login.user_account || "").trim() || "未知账号";
        return `已登录：${account}（账号）`;
    }, [state.login.logged_in, state.login.user_account]);
    const performUninstallInstalledGame = SP_REACT.useCallback(async (item, deleteCompatdata = false) => {
        const gameId = String(item.game_id || "").trim();
        const installPath = String(item.install_path || "").trim();
        const title = String(item.title || gameId || "该游戏");
        if (!installPath) {
            toaster.toast({ title: "freedeckCY", body: "安装路径为空，无法卸载" });
            return;
        }
        if (uninstallingKey)
            return;
        const key = `${gameId}::${installPath}`;
        setUninstallingKey(key);
        try {
            const result = await withTimeout(uninstallTianyiInstalledGame({
                game_id: gameId,
                install_path: installPath,
                delete_files: true,
                delete_compatdata: Boolean(deleteCompatdata),
            }), 120000, "卸载超时（大目录删除可能较慢，请稍后刷新确认）");
            if (result.status !== "success") {
                throw new Error(result.message || "卸载失败");
            }
            const freedBytes = Number(result.data?.compatdata?.freed_bytes || 0);
            const suffix = deleteCompatdata
                ? freedBytes > 0
                    ? `（已回收 Proton 前缀 ${formatBytesText(freedBytes)}）`
                    : "（含 Proton 前缀）"
                : "";
            toaster.toast({ title: "freedeckCY", body: `已卸载：${title}${suffix}` });
            try {
                await syncState();
            }
            catch {
                // 卸载已成功；列表刷新失败不再弹“卸载失败”误导用户。
            }
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setUninstallingKey("");
        }
    }, [syncState, uninstallingKey]);
    const onUninstallInstalledGame = SP_REACT.useCallback(async (item) => {
        const gameId = String(item.game_id || "").trim();
        const installPath = String(item.install_path || "").trim();
        const title = String(item.title || gameId || "该游戏");
        if (!installPath) {
            toaster.toast({ title: "freedeckCY", body: "安装路径为空，无法卸载" });
            return;
        }
        if (uninstallingKey || previewingKey)
            return;
        const key = `${gameId}::${installPath}`;
        setPreviewingKey(key);
        let preview = null;
        try {
            const result = await withTimeout(previewTianyiUninstall({ game_id: gameId, install_path: installPath }), 15000, "读取卸载信息超时");
            if (result.status === "success")
                preview = result.data ?? null;
        }
        catch {
            preview = null;
        }
        finally {
            setPreviewingKey("");
        }
        const installBytes = Number(preview?.install_size_bytes || 0);
        const compatBytes = Number(preview?.compatdata_size_bytes || 0);
        const lines = [`确定卸载「${title}」吗？`, ""];
        if (installBytes > 0)
            lines.push(`安装目录占用：${formatBytesText(installBytes)}`);
        lines.push(installPath);
        if (compatBytes > 0) {
            lines.push("", `Proton 前缀（compatdata）另占 ${formatBytesText(compatBytes)}，可选择一并删除。`);
        }
        DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, { strTitle: "\u786E\u8BA4\u5378\u8F7D", strDescription: lines.join("\n"), strOKButtonText: compatBytes > 0 ? "仅删游戏文件" : "确认卸载", strMiddleButtonText: compatBytes > 0 ? `连 Proton 前缀一起删（${formatBytesText(compatBytes)}）` : undefined, onMiddleButton: compatBytes > 0
                ? () => {
                    void performUninstallInstalledGame(item, true);
                }
                : undefined, strCancelButtonText: "\u53D6\u6D88", onOK: () => {
                void performUninstallInstalledGame(item, false);
            }, onCancel: () => { } }));
    }, [performUninstallInstalledGame, previewingKey, uninstallingKey]);
    const performTaskAction = SP_REACT.useCallback(async (action, task) => {
        const taskId = String(task.task_id || "").trim();
        if (!taskId)
            return;
        if (taskActionKey)
            return;
        setTaskActionKey(`${action}:${taskId}`);
        try {
            const runner = action === "pause"
                ? pauseTianyiTask
                : action === "resume"
                    ? resumeTianyiTask
                    : action === "retry"
                        ? retryTianyiTask
                        : action === "fallback"
                            ? retryTianyiTaskWithFallback
                            : removeTianyiTask;
            // 重试/换源要重新取直链/重新进入安装，给更长的超时；暂停/继续/移除通常很快。
            const actionTimeoutMs = action === "retry" || action === "fallback" ? 90000 : 20000;
            const result = await withTimeout(runner({ task_id: taskId }), actionTimeoutMs, "任务操作超时，请稍后重试");
            if (result.status !== "success") {
                throw new Error(result.message || "任务操作失败");
            }
            const label = action === "pause"
                ? "已暂停"
                : action === "resume"
                    ? "已继续"
                    : action === "retry"
                        ? "已重新开始"
                        : action === "fallback"
                            ? "已切换下载源"
                            : "已移除";
            toaster.toast({
                title: "freedeckCY",
                body: `${label}：${task.game_title || task.file_name || taskId}`,
            });
            try {
                await syncState(PANEL_POLL_MODE_ACTIVE);
            }
            catch {
                // 操作已成功；刷新失败不覆盖成功提示。
            }
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setTaskActionKey("");
        }
    }, [syncState, taskActionKey]);
    const onDiagnoseTask = SP_REACT.useCallback(async (task) => {
        if (taskActionKey)
            return;
        const taskId = String(task.task_id || "").trim();
        if (!taskId)
            return;
        setTaskActionKey(`diagnose:${taskId}`);
        try {
            const result = await withTimeout(diagnoseTianyiTask({ task_id: taskId }), 20000, "诊断超时");
            if (result.status !== "success")
                throw new Error(result.message || "诊断失败");
            const data = result.data || {};
            const stageLabels = { resolve: "解析链接", download: "下载", extract: "解压", install: "安装" };
            const lines = [
                `阶段：${stageLabels[data.stage] || data.stage || "-"}`,
                `原因：${data.reason || "-"}`,
                "",
                ...(data.suggestions || []).map((item) => `• ${item}`),
            ];
            DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, {
                strTitle: `任务诊断：${data.title || taskId}`,
                strDescription: lines.join("\n"),
                strOKButtonText: "完成",
                strCancelButtonText: "关闭",
                onOK: () => { },
                onCancel: () => { },
            }));
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setTaskActionKey("");
        }
    }, [taskActionKey]);
    const onPauseAllTasks = SP_REACT.useCallback(async () => {
        if (batchBusy)
            return;
        setBatchBusy("pause");
        try {
            const result = await withTimeout(pauseAllTianyiTasks(), 20000, "暂停全部超时");
            if (result.status !== "success")
                throw new Error(result.message || "暂停全部失败");
            toaster.toast({ title: "freedeckCY", body: "已暂停全部下载" });
            await syncState(PANEL_POLL_MODE_ACTIVE);
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setBatchBusy("");
        }
    }, [batchBusy, syncState]);
    const onResumeAllTasks = SP_REACT.useCallback(async () => {
        if (batchBusy)
            return;
        setBatchBusy("resume");
        try {
            const result = await withTimeout(resumeAllTianyiTasks(), 20000, "继续全部超时");
            if (result.status !== "success")
                throw new Error(result.message || "继续全部失败");
            toaster.toast({ title: "freedeckCY", body: "已继续全部下载" });
            await syncState(PANEL_POLL_MODE_ACTIVE);
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setBatchBusy("");
        }
    }, [batchBusy, syncState]);
    const onRetryAllTasks = SP_REACT.useCallback(async () => {
        if (batchBusy)
            return;
        setBatchBusy("retry");
        try {
            const result = await withTimeout(retryAllTianyiTasks(), 600000, "全部重试超时");
            if (result.status !== "success")
                throw new Error(result.message || "全部重试失败");
            const data = result.data || {};
            const attempted = Number(data.attempted || 0);
            const succeeded = Number(data.succeeded || 0);
            const failed = Number(data.failed || 0);
            toaster.toast({
                title: "freedeckCY",
                body: attempted === 0
                    ? "没有失败任务"
                    : `重试完成：成功 ${succeeded} 个${failed > 0 ? `，失败 ${failed} 个` : ""}`,
            });
            await syncState(PANEL_POLL_MODE_ACTIVE);
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setBatchBusy("");
        }
    }, [batchBusy, syncState]);
    const onApplySpeedLimit = SP_REACT.useCallback(async () => {
        if (batchBusy)
            return;
        const value = Math.max(0, Math.min(1024 * 1024, Number.parseInt(speedDraft || "0", 10) || 0));
        setBatchBusy("speed");
        try {
            const result = await withTimeout(setTianyiSpeedLimit({ limit_kb: value }), 15000, "设置限速超时");
            if (result.status !== "success")
                throw new Error(result.message || "设置限速失败");
            toaster.toast({ title: "freedeckCY", body: value > 0 ? `下载限速已设为 ${value} KB/s` : "已取消下载限速" });
            await syncState(PANEL_POLL_MODE_IDLE);
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setBatchBusy("");
        }
    }, [batchBusy, speedDraft, syncState]);
    const onRemoveTask = SP_REACT.useCallback((task) => {
        const taskId = String(task.task_id || "").trim();
        if (!taskId || taskActionKey)
            return;
        const title = task.game_title || task.file_name || "该任务";
        DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, { strTitle: "\u786E\u8BA4\u79FB\u9664\u4EFB\u52A1", strDescription: `确定移除「${title}」吗？\n\n只移除任务记录，不删除已下载文件。`, strOKButtonText: "\u786E\u8BA4\u79FB\u9664", strCancelButtonText: "\u53D6\u6D88", onOK: () => {
                void performTaskAction("remove", task);
            }, onCancel: () => { } }));
    }, [performTaskAction, taskActionKey]);
    const trySteamRefresh = SP_REACT.useCallback(async () => {
        if (refreshingSteamLibrary)
            return;
        setRefreshingSteamLibrary(true);
        try {
            const refreshed = await tryRefreshSteamLibrary();
            if (!refreshed) {
                toaster.toast({ title: "freedeckCY", body: "当前 Steam 不支持免重启刷新，请手动重启", duration: 5000 });
                return;
            }
            await clearSteamRestartPending();
            setState((prev) => ({ ...prev, steam_restart: { pending: false } }));
            toaster.toast({ title: "freedeckCY", body: "已请求 Steam 刷新快捷方式" });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setRefreshingSteamLibrary(false);
        }
    }, [clearSteamRestartPending, refreshingSteamLibrary]);
    const dismissSteamRestart = SP_REACT.useCallback(async () => {
        const pending = state.steam_restart;
        const key = steamRestartKey(pending);
        try {
            const result = await withTimeout(clearSteamRestartPending(), 15000, "清除重启提示超时");
            if (result.status !== "success") {
                throw new Error(result.message || "清除重启提示失败");
            }
        }
        catch (error) {
            toaster.toast({ title: "freedeckCY", body: `稍后处理失败：${errorText(error)}` });
            return false;
        }
        if (key)
            dismissedSteamRestartRef.current.add(key);
        setState((prev) => ({ ...prev, steam_restart: { pending: false } }));
        return true;
    }, [state.steam_restart]);
    const restartSteamNow = SP_REACT.useCallback(async () => {
        if (restartingSteam)
            return;
        setRestartingSteam(true);
        try {
            const result = await withTimeout(restartSteamBackend(), 70000, "重启 Steam 超时");
            if (result.status !== "success" || result.data?.ok === false) {
                throw new Error(String(result.message || result.data?.message || "重启 Steam 失败"));
            }
            const key = steamRestartKey(state.steam_restart);
            if (key)
                dismissedSteamRestartRef.current.add(key);
            setState((prev) => ({ ...prev, steam_restart: { pending: false } }));
            void clearSteamRestartPending().catch(() => undefined);
            toaster.toast({ title: "freedeckCY", body: "已请求重启 Steam" });
        }
        catch (error) {
            if (tryRestartSteamViaClient()) {
                toaster.toast({ title: "freedeckCY", body: "已通过 Steam 客户端请求重启" });
            }
            else {
                toaster.toast({
                    title: "freedeckCY",
                    body: `自动重启失败：${errorText(error)}；请手动重启 Steam`,
                    duration: 6000,
                });
            }
        }
        finally {
            setRestartingSteam(false);
        }
    }, [restartingSteam, state.steam_restart]);
    const language = useLanguage();
    if (!hasLanguage())
        return SP_JSX.jsx(LanguageChooser, {});
    if (loading) {
        return (SP_JSX.jsx(DFL.PanelSection, { children: SP_JSX.jsx(DFL.PanelSectionRow, { children: "\u52A0\u8F7D\u4E2D..." }) }));
    }
    return (SP_JSX.jsxs("div", { ref: contentI18nRef, "data-fdc-i18n": "1", style: { display: "contents" }, children: [SP_JSX.jsx(LanguageSection, { language: language }), SP_JSX.jsxs(DFL.PanelSection, { children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: {
                                width: "100%",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                            }, title: loginStatusText, children: loginStatusText }) }), SP_JSX.jsxs(DFL.PanelSectionRow, { children: [!state.login.logged_in && (SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onLogin, disabled: openingLogin, children: openingLogin ? "登录入口准备中..." : "登录" })), SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onOpenLibrary, disabled: openingLogin, children: "\u6E38\u620F\u5E93" }), SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onOpenSettings, children: "\u8BBE\u7F6E" })] })] }), state.steam_restart?.pending && (SP_JSX.jsxs(DFL.PanelSection, { title: "Steam \u5FEB\u6377\u65B9\u5F0F\u5DF2\u5199\u5165", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.45 }, children: `「${state.steam_restart.title || "游戏"}」已安装并写入 Steam 快捷方式。重启 Steam 后才会显示在库中。` }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs(DFL.Focusable, { style: { display: "flex", gap: "8px", width: "100%" }, children: [SP_JSX.jsx(DFL.DialogButton, { onClick: () => void trySteamRefresh(), disabled: restartingSteam || refreshingSteamLibrary, style: { flex: 1 }, children: refreshingSteamLibrary ? "刷新中..." : "免重启刷新" }), SP_JSX.jsx(DFL.DialogButton, { onClick: () => void restartSteamNow(), disabled: restartingSteam || refreshingSteamLibrary, style: { flex: 1 }, children: restartingSteam ? "正在重启..." : "现在重启" }), SP_JSX.jsx(DFL.DialogButton, { onClick: () => void dismissSteamRestart(), disabled: restartingSteam, style: { flex: 1 }, children: "\u7A0D\u540E" })] }) })] })), visibleTasks.length > 0 && (SP_JSX.jsx(DFL.PanelSection, { title: `下载列表（${visibleTasks.length}）`, children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px", width: "100%" }, children: [SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onPauseAllTasks(), disabled: Boolean(batchBusy), style: { width: "auto", flex: "0 0 auto" }, children: batchBusy === "pause" ? "暂停中..." : "全部暂停" }), SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onResumeAllTasks(), disabled: Boolean(batchBusy), style: { width: "auto", flex: "0 0 auto" }, children: batchBusy === "resume" ? "继续中..." : "全部继续" }), SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onRetryAllTasks(), disabled: Boolean(batchBusy), style: { width: "auto", flex: "0 0 auto" }, children: batchBusy === "retry" ? "重试中..." : "全部重试" }), SP_JSX.jsx("div", { style: { flex: "1 1 120px", minWidth: "100px" }, children: SP_JSX.jsx(DFL.TextField, { label: `限速 KB/s（当前 ${Math.round(Number(state.settings.download_speed_limit || 0) / 1024)}，0 不限）`, value: speedDraft, onChange: (event) => setSpeedDraft(getTextFieldValue(event)) }) }), SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onApplySpeedLimit(), disabled: Boolean(batchBusy), style: { width: "auto", flex: "0 0 auto" }, children: batchBusy === "speed" ? "应用中..." : "应用限速" })] }) }), ...visibleTasks.slice(0, 20).map((task) => {
                    const taskId = String(task.task_id || "");
                    const status = String(task.status || "");
                    const canPause = status === "active" || status === "waiting";
                    const canResume = status === "paused";
                    const canRetry = status === "error" ||
                        String(task.install_status || "") === "failed" ||
                        String(task.install_status || "") === "gave_up";
                    const busy = Boolean(taskActionKey) && taskActionKey.endsWith(taskId);
                    const buttonStyle = {
                        minWidth: "76px",
                        borderRadius: "10px",
                        border: "1px solid rgba(255, 255, 255, 0.22)",
                        background: "rgba(255, 255, 255, 0.12)",
                        color: "#f2f2f2",
                    };
                    return (SP_JSX.jsxs(DFL.PanelSectionRow, { children: [TaskProgressRow(task), SP_JSX.jsxs("div", { style: { display: "flex", gap: "8px", width: "100%", marginTop: "4px" }, children: [canRetry && (SP_JSX.jsx(DFL.Focusable, { style: { flex: 1 }, children: SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onDiagnoseTask(task), onOKButton: () => void onDiagnoseTask(task), disabled: Boolean(taskActionKey), style: buttonStyle, children: busy ? "处理中..." : "诊断" }) })), canPause && (SP_JSX.jsx(DFL.Focusable, { style: { flex: 1 }, children: SP_JSX.jsx(DFL.DialogButton, { onClick: () => void performTaskAction("pause", task), onOKButton: () => void performTaskAction("pause", task), disabled: Boolean(taskActionKey), style: buttonStyle, children: busy ? "处理中..." : "暂停" }) })), canResume && (SP_JSX.jsx(DFL.Focusable, { style: { flex: 1 }, children: SP_JSX.jsx(DFL.DialogButton, { onClick: () => void performTaskAction("resume", task), onOKButton: () => void performTaskAction("resume", task), disabled: Boolean(taskActionKey), style: buttonStyle, children: busy ? "处理中..." : "继续" }) })), canRetry && (SP_JSX.jsx(DFL.Focusable, { style: { flex: 1 }, children: SP_JSX.jsx(DFL.DialogButton, { onClick: () => void performTaskAction("retry", task), onOKButton: () => void performTaskAction("retry", task), disabled: Boolean(taskActionKey), style: {
                                                minWidth: "76px",
                                                borderRadius: "10px",
                                                border: "1px solid rgba(120, 200, 255, 0.45)",
                                                background: "rgba(120, 200, 255, 0.16)",
                                                color: "#dff4ff",
                                            }, children: busy ? "重试中..." : "重试" }) })), canRetry && (SP_JSX.jsx(DFL.Focusable, { style: { flex: 1 }, children: SP_JSX.jsx(DFL.DialogButton, { onClick: () => void performTaskAction("fallback", task), onOKButton: () => void performTaskAction("fallback", task), disabled: Boolean(taskActionKey), style: {
                                                minWidth: "76px",
                                                borderRadius: "10px",
                                                border: "1px solid rgba(255, 196, 120, 0.45)",
                                                background: "rgba(255, 196, 120, 0.14)",
                                                color: "#ffe8c8",
                                            }, children: busy ? "处理中..." : "换源" }) })), SP_JSX.jsx(DFL.Focusable, { style: { flex: 1 }, children: SP_JSX.jsx(DFL.DialogButton, { onClick: () => onRemoveTask(task), onOKButton: () => onRemoveTask(task), disabled: Boolean(taskActionKey), style: {
                                                minWidth: "76px",
                                                borderRadius: "10px",
                                                border: "1px solid rgba(255, 106, 106, 0.4)",
                                                background: "rgba(255, 106, 106, 0.16)",
                                                color: "#ffe8e8",
                                            }, children: "\u79FB\u9664" }) })] })] }, task.task_id));
                })] })), sortedInstalledGames.length > 0 && (SP_JSX.jsx(DFL.PanelSection, { title: `游戏预览（已安装 ${state.installed.total || sortedInstalledGames.length}）`, children: sortedInstalledGames.map((item, index) => {
                    const uninstallKey = `${item.game_id || ""}::${item.install_path || ""}`;
                    const uninstalling = uninstallingKey === uninstallKey;
                    return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px", width: "100%" }, children: [SP_JSX.jsxs("div", { style: { minWidth: 0, flex: 1 }, children: [SP_JSX.jsx("div", { style: {
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap",
                                            }, title: item.title || "未命名游戏", children: item.title || "未命名游戏" }), SP_JSX.jsx("div", { style: { fontSize: "12px" }, children: `${item.size_text || "-"}${item.status ? ` | ${item.status}` : ""}` }), SP_JSX.jsx("div", { style: { fontSize: "12px" }, children: `游玩时长：${formatPlaytimeText(item.playtime_seconds || 0, item.playtime_text)}${item.playtime_active ? "（进行中）" : ""}` }), SP_JSX.jsx("div", { style: {
                                                fontSize: "12px",
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap",
                                            }, title: item.install_path || "-", children: item.install_path || "-" })] }), SP_JSX.jsx(DFL.Focusable, { style: { flex: "0 0 auto" }, children: SP_JSX.jsx(DFL.DialogButton, { onClick: () => onUninstallInstalledGame(item), onOKButton: () => onUninstallInstalledGame(item), disabled: Boolean(uninstallingKey) || uninstalling, style: {
                                            minWidth: "88px",
                                            borderRadius: "10px",
                                            border: "1px solid rgba(255, 255, 255, 0.26)",
                                            background: uninstalling ? "rgba(255, 106, 106, 0.34)" : "rgba(255, 106, 106, 0.2)",
                                            color: "#ffe8e8",
                                        }, children: uninstalling ? "卸载中..." : "卸载" }) })] }) }, `${item.game_id || item.title || "game"}_${index}`));
                }) }))] }));
}
function GameDetailModal(props) {
    const [imageFailed, setImageFailed] = SP_REACT.useState(false);
    const [selectedProviderId, setSelectedProviderId] = SP_REACT.useState("");
    const detailScrollRef = SP_REACT.useRef(null);
    const detailRootRef = SP_REACT.useRef(null);
    useI18nRoot(detailRootRef);
    SP_REACT.useEffect(() => {
        const node = detailScrollRef.current;
        if (!node)
            return;
        node.scrollTop = 0;
        const timer = window.setTimeout(() => { node.scrollTop = 0; }, 80);
        return () => window.clearTimeout(timer);
    }, []);
    const handleDetailButton = SP_REACT.useCallback((evt) => {
        const button = Number(evt?.detail?.button || 0);
        const node = detailScrollRef.current;
        if (!node)
            return;
        if (button === 7 || button === 9) {
            node.scrollBy({ top: -Math.round(node.clientHeight * 0.8), behavior: "smooth" });
        }
        else if (button === 8 || button === 10) {
            node.scrollBy({ top: Math.round(node.clientHeight * 0.8), behavior: "smooth" });
        }
    }, []);
    const handleDetailDirection = SP_REACT.useCallback((evt) => {
        const node = detailScrollRef.current;
        const button = Number(evt?.detail?.button || 0);
        if (!node || (button !== 9 && button !== 10))
            return;
        const step = evt?.detail?.is_repeat ? 120 : 72;
        node.scrollBy({ top: button === 9 ? -step : step, behavior: "smooth" });
    }, []);
    const coverUrl = imageFailed ? "" : String(props.item.cover_portrait_url || props.item.cover_url || "").trim();
    const title = props.item.title || "未命名游戏";
    const parts = title.split("/");
    const primaryTitle = (parts[0] || title).trim();
    const secondaryTitle = parts.slice(1).join(" / ").trim();
    const categoryTags = String(props.item.categories || "")
        .split(/[,，、|/]+/)
        .map((item) => item.trim())
        .filter(Boolean)
        .slice(0, 6);
    const providerOptions = Array.isArray(props.item.providers) && props.item.providers.length
        ? props.item.providers
        : [{
                game_id: props.item.game_id,
                provider: props.item.provider || "other",
                provider_label: props.item.provider_label || "默认网盘",
                title: title,
                size_text: props.item.size_text || "",
            }];
    const activeProvider = providerOptions.find((option) => String(option.game_id || "") === String(selectedProviderId || "")) || providerOptions[0];
    return (SP_JSX.jsxs(DFL.Focusable, { ref: detailRootRef, "data-fdc-i18n": "1", noFocusRing: true, onCancel: props.onClose, onButtonDown: handleDetailButton, onGamepadDirection: handleDetailDirection, onCancelActionDescription: "返回", onOKActionDescription: "选择", className: "fdc-detail", "flow-children": "column", children: [SP_JSX.jsx("div", { className: "fdc-detail-backdrop", style: coverUrl ? { backgroundImage: `url("${coverUrl.replace(/"/g, "%22")}")` } : {} }), SP_JSX.jsxs("div", { ref: detailScrollRef, className: "fdc-detail-scroll", children: [SP_JSX.jsxs("div", { className: "fdc-detail-top", children: [SP_JSX.jsxs("div", { className: "fdc-detail-poster", children: [coverUrl ? (SP_JSX.jsx("img", { src: coverUrl, alt: title, onError: () => setImageFailed(true), decoding: "async" })) : (SP_JSX.jsx("div", { className: "fdc-poster-fallback", children: primaryTitle.slice(0, 2) })), props.installed ? (SP_JSX.jsx("div", { className: "fdc-badge fdc-installed fdc-detail-installed", children: "已安装" })) : null] }), SP_JSX.jsxs("div", { className: "fdc-detail-info", children: [SP_JSX.jsx("div", { className: "fdc-detail-eyebrow", children: "freedeckCY 游戏库" }), SP_JSX.jsx("div", { "data-fdc-i18n-skip": "1", className: "fdc-detail-title", children: primaryTitle }), secondaryTitle ? (SP_JSX.jsx("div", { "data-fdc-i18n-skip": "1", className: "fdc-detail-subtitle", children: secondaryTitle })) : null, SP_JSX.jsxs("div", { className: "fdc-detail-tags", children: [SP_JSX.jsx("span", { children: String(props.item.platform || "pc").toUpperCase() }), SP_JSX.jsx("span", { children: props.item.size_text || "大小未知" }), categoryTags.map((tag) => (SP_JSX.jsx("span", { children: tag }, tag)))] }), SP_JSX.jsx("div", { className: "fdc-detail-description", children: "下载完成后会自动解压并写入 Steam 快捷方式。双网盘资源可以选择更合适的下载源。" })] })] }), SP_JSX.jsxs("div", { className: "fdc-detail-section", children: [SP_JSX.jsx("div", { className: "fdc-detail-section-title", children: "下载源" }), SP_JSX.jsxs(DFL.Focusable, { className: "fdc-source-row", "flow-children": "row", children: [providerOptions.map((option) => (SP_JSX.jsxs(DFL.DialogButton, { className: "fdc-source" + (String(activeProvider?.game_id || "") === String(option.game_id || "") ? " fdc-source-active" : ""), onClick: () => setSelectedProviderId(option.game_id), style: { width: "auto", flex: "1 1 180px", minWidth: "160px", padding: "12px 14px", textAlign: "left" }, children: [SP_JSX.jsx("div", { className: "fdc-source-name", children: option.provider_label || "网盘" }), SP_JSX.jsx("div", { className: "fdc-source-meta", children: option.size_text || props.item.size_text || "大小未知" }), SP_JSX.jsx("div", { className: "fdc-source-check", children: String(activeProvider?.game_id || "") === String(option.game_id || "") ? "已选择" : "选择此源" })] }, option.game_id)))] })] })] }), SP_JSX.jsxs(DFL.Focusable, { className: "fdc-detail-actions", "flow-children": "row", children: [SP_JSX.jsx(DFL.DialogButton, { className: "fdc-install-button", onClick: () => props.onInstall(activeProvider), disabled: props.busy || props.installed, children: props.installed ? "已安装" : props.busy ? "处理中..." : providerOptions.length > 1 ? `安装（${activeProvider?.provider_label || "网盘"}）` : "安装" }), SP_JSX.jsx(DFL.DialogButton, { className: "fdc-secondary-button", onClick: props.onClose, children: "退出" })] })] }));
}
const LIBRARY_CSS = `
.fdc-root { scroll-padding-top: 84px; scroll-padding-bottom: 150px; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; --fdc-bg: #0b0f14; --fdc-panel: rgba(18,26,35,0.84); --fdc-line: rgba(255,255,255,0.10); --fdc-text: #f2f6fb; --fdc-muted: #9eacbb; --fdc-accent: #65d6c0; --fdc-blue: #72b8ff; background: radial-gradient(1100px 520px at 50% -20%, #162a33 0%, var(--fdc-bg) 55%); color: var(--fdc-text); }
.fdc-card-wrap, .fdc-chip, .fdc-button, .fdc-source, .fdc-tab, .fdc-detail-actions button { cursor: pointer; }
.fdc-topbar { position: relative; top: auto; z-index: 40; display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; padding: 10px 12px; margin: 0 -6px 10px; background: rgba(11,15,20,0.94); border-bottom: 1px solid var(--fdc-line); }
.fdc-topbar button, .fdc-search-row button { flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; white-space: nowrap; padding-left: 10px !important; padding-right: 10px !important; }
.fdc-heading { flex: 1 1 180px; min-width: 0; max-width: 100%; display: flex; flex-direction: column; gap: 2px; }
.fdc-title { font-size: 20px; font-weight: 800; letter-spacing: .2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fdc-subtitle { font-size: 11px; color: var(--fdc-muted); }
.fdc-tabs { display: flex; flex-wrap: nowrap; gap: 6px; flex: 0 0 auto; }
.fdc-tab { width: auto; min-width: 0; padding: 7px 13px; white-space: nowrap; border-radius: 999px; border: 1px solid transparent; background: rgba(255,255,255,0.06); color: var(--fdc-muted); }
.fdc-tab-active { border-color: rgba(101,214,192,0.55); background: rgba(101,214,192,0.16); color: #eafff8; }
.fdc-search-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; width: 100%; padding: 2px 6px 8px; }
.fdc-search { flex: 1 1 260px; min-width: 0; width: 0; }
.fdc-search > * { width: 100%; }
.fdc-button { width: auto; flex: 0 0 auto; padding: 8px 14px; border-radius: 9px; border: 1px solid rgba(255,255,255,0.16); background: rgba(255,255,255,0.06); }
.fdc-filter-panel { margin: 0 6px 12px; padding: 10px 12px 12px; border: 1px solid var(--fdc-line); border-radius: 12px; background: var(--fdc-panel); }
.fdc-filter-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 7px; align-items: center; }
.fdc-chip { width: auto !important; min-width: 0 !important; flex: 0 0 auto; padding: 5px 9px !important; min-height: 28px; white-space: nowrap; border-radius: 999px; border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.05); font-size: 11px; color: #dbe6f2; }
.fdc-chip-active { border-color: rgba(101,214,192,0.58); background: rgba(101,214,192,0.16); color: #effffa; }
.fdc-label { font-size: 11px; color: var(--fdc-muted); margin-right: 4px; }
.fdc-hero { position: relative; overflow: hidden; min-height: 238px; margin: 2px 6px 18px; border: 1px solid var(--fdc-line); border-radius: 16px; background: linear-gradient(125deg, #17303a, #0e151d 72%); display: flex; align-items: flex-end; }
.fdc-hero-bg { position: absolute; inset: 0; background-size: cover; background-position: center; opacity: .52; filter: saturate(.9); }
.fdc-hero-shade { position: absolute; inset: 0; background: linear-gradient(90deg, rgba(8,12,17,0.94) 0%, rgba(8,12,17,0.62) 48%, rgba(8,12,17,0.12) 100%), linear-gradient(0deg, rgba(8,12,17,0.72), transparent 60%); }
.fdc-hero-content { position: relative; z-index: 2; padding: 22px 24px 18px; width: min(620px, 100%); display: flex; flex-direction: column; gap: 8px; }
.fdc-hero-eyebrow { color: var(--fdc-accent); font-size: 11px; font-weight: 800; letter-spacing: 1.2px; text-transform: uppercase; }
.fdc-hero-title { font-size: clamp(24px, 4vw, 38px); line-height: 1.06; font-weight: 900; text-shadow: 0 4px 20px rgba(0,0,0,.5); }
.fdc-hero-meta { color: #c8d5e1; font-size: 12px; }
.fdc-hero-actions { display: flex; gap: 8px; margin-top: 6px; }
.fdc-section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin: 0 8px 8px; }
.fdc-section-title { font-size: 15px; font-weight: 800; }
.fdc-section-count { font-size: 11px; color: var(--fdc-muted); }
.fdc-shelf-block { margin-bottom: 18px; }
.fdc-shelf { display: flex; gap: 14px; overflow-x: auto; padding: 10px 16px 12px; scroll-snap-type: none; overflow-anchor: none; -webkit-overflow-scrolling: touch; touch-action: pan-x; overscroll-behavior-x: contain; scrollbar-width: none; -ms-overflow-style: none; }
.fdc-shelf::-webkit-scrollbar { display: none; width: 0; height: 0; }
.fdc-root { scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.22) transparent; }
.fdc-root::-webkit-scrollbar { width: 6px; height: 6px; }
.fdc-root::-webkit-scrollbar-track { background: transparent; }
.fdc-root::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.22); border-radius: 999px; }
.fdc-shelf .fdc-card-wrap { flex: 0 0 auto; }
.fdc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); align-items: start; gap: 18px; padding: 10px 16px 24px; width: 100%; box-sizing: border-box; }
.fdc-grid .fdc-card-wrap { width: 100% !important; }
.fdc-card-wrap, .fdc-shelf-block { scroll-margin-top: 84px; }
.fdc-card-wrap { display: flex; flex-direction: column; gap: 5px; min-width: 0; width: 100%; }
.fdc-card { transition: transform 120ms ease, border-color 120ms ease, box-shadow 120ms ease; }
.fdc-card:hover { border-color: rgba(255,255,255,0.22) !important; }
.fdc-card:focus, .fdc-card:focus-within { outline: 2px solid var(--fdc-accent) !important; outline-offset: 3px !important; transform: translateY(-2px); box-shadow: 0 12px 26px rgba(0,0,0,0.42); }
.fdc-card-cover { position: relative; width: 100%; aspect-ratio: 2 / 3; overflow: hidden; background: linear-gradient(145deg, #1b3540, #0d141b); }
.fdc-card-cover img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; display: block; }
.fdc-card-fallback { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: rgba(242,246,251,.82); font-size: 26px; font-weight: 900; letter-spacing: 2px; background: linear-gradient(145deg, #17313b, #0b1117); }
.fdc-card-shade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(5,9,13,0.0) 45%, rgba(5,9,13,0.30) 100%); pointer-events: none; }
.fdc-badge { position: absolute; top: 7px; z-index: 3; padding: 3px 7px; border-radius: 5px; font-size: 10px; line-height: 1.2; font-weight: 800; letter-spacing: .2px; backdrop-filter: none; }
.fdc-provider { left: 7px; color: #dff9ff; background: rgba(16,68,82,0.92); border: 1px solid rgba(113,224,238,0.35); }
.fdc-provider-baidu { color: #eaf2ff; background: rgba(30,67,122,0.94); border-color: rgba(126,177,255,0.45); }
.fdc-installed { right: 7px; color: #dff7e4; background: rgba(20,105,56,0.94); border: 1px solid rgba(160,255,190,0.45); }
.fdc-card-busy { position: absolute; inset: 0; z-index: 4; display: flex; align-items: center; justify-content: center; background: rgba(7,10,14,0.72); color: #fff; font-size: 12px; font-weight: 800; }
.fdc-card-info { padding: 8px 9px 9px; display: flex; flex-direction: column; gap: 3px; min-height: 50px; }
.fdc-card-title { font-size: 12px; line-height: 1.3; font-weight: 750; color: #f2f6fb; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; word-break: break-word; }
.fdc-card-meta { font-size: 10px; color: var(--fdc-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fdc-skeleton { border-radius: 8px; background: linear-gradient(100deg, rgba(255,255,255,0.055) 20%, rgba(255,255,255,0.13) 38%, rgba(255,255,255,0.055) 56%); background-size: 220% 100%; animation: fdc-shimmer 1.25s ease-in-out infinite; }
.fdc-skeleton-cover { width: 100%; aspect-ratio: 2 / 3; border-radius: 12px; }
.fdc-skeleton-title { height: 12px; width: 86%; margin-top: 9px; }
.fdc-skeleton-meta { height: 9px; width: 58%; margin-top: 6px; }
@keyframes fdc-shimmer { 0% { background-position: 120% 0; } 100% { background-position: -120% 0; } }
.fdc-empty { padding: 34px 12px; text-align: center; color: var(--fdc-muted); font-size: 13px; }
.fdc-footer { display: flex; justify-content: center; align-items: center; gap: 12px; padding: 12px 0 20px; color: var(--fdc-muted); font-size: 11px; }
.fdc-detail { position: relative; width: min(760px, 92vw); margin-top: 40px; max-height: calc(100vh - 150px); overflow: hidden; border-radius: 18px; border: 1px solid rgba(255,255,255,0.12); background: #0c1218; color: var(--fdc-text); display: flex; flex-direction: column; }
.fdc-detail-backdrop { position: absolute; inset: 0; background-size: cover; background-position: center; filter: blur(22px) saturate(1.15); opacity: .34; transform: scale(1.12); }
.fdc-detail-scroll { touch-action: pan-y; -webkit-overflow-scrolling: touch; overscroll-behavior: contain; position: relative; z-index: 2; flex: 1 1 auto; min-height: 0; max-height: none; overflow-y: auto; padding: 14px 20px 12px; background-color: #0c1218; background-image: linear-gradient(180deg, rgba(10,15,20,0.48), rgba(10,15,20,0.94) 46%); }
.fdc-detail-top { display: grid; grid-template-columns: 168px minmax(0, 1fr); gap: 20px; align-items: start; }
.fdc-detail-poster { position: relative; width: 168px; aspect-ratio: 2 / 3; border-radius: 12px; overflow: hidden; border: 1px solid rgba(255,255,255,0.14); background: linear-gradient(145deg, #1b3540, #0d141b); box-shadow: 0 18px 40px rgba(0,0,0,.38); }
.fdc-detail-poster img { width: 100%; height: 100%; object-fit: cover; display: block; }
.fdc-poster-fallback { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 30px; font-weight: 900; color: rgba(242,246,251,.8); }
.fdc-detail-installed { top: 8px; right: 8px; }
.fdc-detail-info { min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.fdc-detail-eyebrow { font-size: 10px; font-weight: 800; letter-spacing: 1.4px; color: var(--fdc-accent); text-transform: uppercase; }
.fdc-detail-title { font-size: clamp(22px, 3.4vw, 34px); line-height: 1.08; font-weight: 900; word-break: break-word; }
.fdc-detail-subtitle { font-size: 13px; color: #b7c4d0; word-break: break-word; }
.fdc-detail-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 2px; }
.fdc-detail-tags span { padding: 4px 8px; border-radius: 5px; font-size: 10px; color: #dbe8f4; background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.10); }
.fdc-detail-description { font-size: 12px; line-height: 1.55; color: #aebdca; max-width: 560px; }
.fdc-detail-section { margin-top: 18px; }
.fdc-detail-section-title { font-size: 12px; font-weight: 800; color: #eaf2fa; margin-bottom: 8px; }
.fdc-source-row { display: flex; flex-wrap: wrap; gap: 8px; }
.fdc-source { border-radius: 10px !important; border: 1px solid rgba(255,255,255,0.14) !important; background: rgba(255,255,255,0.05) !important; color: #eaf2fa !important; }
.fdc-source-active { border-color: rgba(101,214,192,0.78) !important; background: rgba(101,214,192,0.14) !important; box-shadow: inset 0 0 0 1px rgba(101,214,192,0.25); }
.fdc-source-name { font-size: 13px; font-weight: 800; }
.fdc-source-meta { font-size: 11px; color: #9eacbb; margin-top: 3px; }
.fdc-source-check { font-size: 10px; color: #9eacbb; margin-top: 6px; }
.fdc-source-active .fdc-source-check { color: var(--fdc-accent); }
.fdc-detail-actions { position: relative; z-index: 5; flex: 0 0 auto; display: flex; gap: 10px; margin: 0; padding: 10px 20px 14px; border-top: 1px solid rgba(255,255,255,0.10); background: #0c1218; }
.fdc-install-button { flex: 1; min-height: 44px; border-radius: 10px; border: 1px solid rgba(120,255,190,0.42); background: rgba(67,181,129,0.28); color: #eafff3; font-weight: 800; }
.fdc-secondary-button { width: auto; min-width: 90px; min-height: 44px; border-radius: 10px; }
@media (max-height: 600px) { .fdc-detail-scroll { padding: 14px 16px 8px; } .fdc-detail-top { grid-template-columns: 112px minmax(0, 1fr); gap: 12px; } .fdc-detail-poster { width: 112px; } .fdc-detail-title { font-size: 22px; } .fdc-detail-section { margin-top: 8px; } .fdc-detail-section-title { margin-bottom: 5px; } .fdc-detail-description { display: none; } .fdc-source { padding: 8px 11px !important; min-height: 0 !important; } .fdc-source-check { margin-top: 3px; } }
@media (max-width: 760px) { .fdc-topbar { flex-wrap: wrap; } .fdc-heading { order: 2; width: 100%; flex: 1 1 100%; } .fdc-tabs { order: 3; } .fdc-detail-top { grid-template-columns: 128px minmax(0, 1fr); } .fdc-detail-poster { width: 128px; } .fdc-grid { grid-template-columns: repeat(auto-fill, minmax(132px, 1fr)); gap: 13px; } }
@media (prefers-reduced-motion: reduce) { .fdc-card, .fdc-skeleton { transition: none; animation: none; } }
`;
function LibrarySkeletonCard(props) {
    return (SP_JSX.jsxs("div", { className: "fdc-card-wrap", style: { width: props.width ? `${props.width}px` : "100%" }, children: [SP_JSX.jsx("div", { className: "fdc-skeleton fdc-skeleton-cover" }), SP_JSX.jsx("div", { className: "fdc-skeleton fdc-skeleton-title" }), SP_JSX.jsx("div", { className: "fdc-skeleton fdc-skeleton-meta" })] }));
}
function LibraryCoverCard(props) {
    const [imageFailed, setImageFailed] = SP_REACT.useState(false);
    const [proxyFailed, setProxyFailed] = SP_REACT.useState(false);
    const cardRef = SP_REACT.useRef(null);
    const handleCardFocus = SP_REACT.useCallback(() => {
        const node = cardRef.current;
        if (!node)
            return;
        const shelf = node.closest(".fdc-shelf");
        if (shelf) {
            const margin = 14;
            const cardRect = node.getBoundingClientRect();
            const shelfRect = shelf.getBoundingClientRect();
            if (cardRect.left < shelfRect.left + margin) {
                shelf.scrollBy({ left: cardRect.left - (shelfRect.left + margin), behavior: "smooth" });
            }
            else if (cardRect.right > shelfRect.right - margin) {
                shelf.scrollBy({ left: cardRect.right - (shelfRect.right - margin), behavior: "smooth" });
            }
        }
        node.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
    }, []);
    const rawCoverUrl = imageFailed ? "" : String(props.coverUrl || "").trim();
    const coverUrl = rawCoverUrl && props.coverProxyBase && !proxyFailed ? `${props.coverProxyBase}?url=${encodeURIComponent(rawCoverUrl)}` : rawCoverUrl;
    const title = props.title || "未命名游戏";
    const providerLabel = String(props.providerLabel || "").trim();
    const providerClass = providerLabel.includes("百度") ? " fdc-provider-baidu" : providerLabel ? " fdc-provider-tianyi" : "";
    const metaParts = [String(props.platform || "pc").toUpperCase(), String(props.meta || "").trim()].filter(Boolean);
    return (SP_JSX.jsxs("div", { ref: cardRef, className: "fdc-card-wrap", style: { width: props.width ? `${props.width}px` : "100%", scrollMarginTop: "84px" }, children: [SP_JSX.jsxs(DFL.DialogButton, { className: "freedeckcy-cover-card fdc-card", onClick: props.onPress, onGamepadFocus: handleCardFocus, disabled: Boolean(props.disabled), style: { width: "100%", minWidth: 0, boxSizing: "border-box", padding: 0, border: "1px solid rgba(255,255,255,0.10)", borderRadius: "12px", overflow: "hidden", display: "flex", flexDirection: "column", background: "#121a23" }, children: [SP_JSX.jsxs("div", { className: "fdc-card-cover", children: [coverUrl ? (SP_JSX.jsx("img", { src: coverUrl, alt: title, referrerPolicy: "no-referrer", decoding: "async", loading: "lazy", onError: () => { if (rawCoverUrl && coverUrl !== rawCoverUrl) setProxyFailed(true); else setImageFailed(true); } })) : (SP_JSX.jsx("div", { className: "fdc-card-fallback", children: SP_JSX.jsx("span", { children: title.slice(0, 2) }) })), SP_JSX.jsx("div", { className: "fdc-card-shade" }), providerLabel ? (SP_JSX.jsx("div", { className: `fdc-badge fdc-provider${providerClass}`, children: providerLabel })) : null, props.installed ? (SP_JSX.jsx("div", { className: "fdc-badge fdc-installed", children: "已安装" })) : null, props.busyLabel ? (SP_JSX.jsx("div", { className: "fdc-card-busy", children: props.busyLabel })) : null] }), SP_JSX.jsxs("div", { className: "fdc-card-info", children: [SP_JSX.jsx("div", { "data-fdc-i18n-skip": "1", className: "fdc-card-title", title: title, children: title }), SP_JSX.jsx("div", { className: "fdc-card-meta", children: metaParts.join(" · ") })] })] }), props.actions ? (SP_JSX.jsx(DFL.Focusable, { style: { display: "flex", gap: "5px", width: "100%" }, children: props.actions })) : null] }));
}
function LibraryPage({ onClose }) {
    const [tab, setTab] = SP_REACT.useState("catalog");
    const [filtersOpen, setFiltersOpen] = SP_REACT.useState(false);
    const [query, setQuery] = SP_REACT.useState("");
    const [activeQuery, setActiveQuery] = SP_REACT.useState("");
    const [platform, setPlatform] = SP_REACT.useState("");
    const [category, setCategory] = SP_REACT.useState("");
    const [sort, setSort] = SP_REACT.useState("");
    const [page, setPage] = SP_REACT.useState(1);
    const [catalog, setCatalog] = SP_REACT.useState({ total: 0, page: 1, page_size: 20, items: [] });
    const [installed, setInstalled] = SP_REACT.useState({ total: 0, items: [] });
    const installedGameIds = SP_REACT.useMemo(() => {
        const ids = new Set();
        for (const item of installed.items || []) {
            const gameId = String(item.game_id || "").trim();
            if (gameId)
                ids.add(gameId);
        }
        return ids;
    }, [installed.items]);
    const [loadingCatalog, setLoadingCatalog] = SP_REACT.useState(true);
    const [reloadNonce, setReloadNonce] = SP_REACT.useState(0);
    const [loadingInstalled, setLoadingInstalled] = SP_REACT.useState(false);
    const [busyKey, setBusyKey] = SP_REACT.useState("");
    const [healthBusy, setHealthBusy] = SP_REACT.useState(false);
    const [catalogUpdate, setCatalogUpdate] = SP_REACT.useState({ added_count: 0, items: [], updated_at: 0 });
    const [coverProxyBase, setCoverProxyBase] = SP_REACT.useState("");
    const catalogRequestRef = SP_REACT.useRef(0);
    const installedRequestRef = SP_REACT.useRef(0);
    const busyRef = SP_REACT.useRef("");
    const libraryRootRef = SP_REACT.useRef(null);
    useI18nRoot(libraryRootRef);
    const pageSize = 30;
    const handleLibraryButton = SP_REACT.useCallback((evt) => {
        const button = Number(evt?.detail?.button || 0);
        const root = libraryRootRef.current;
        // L1/R1 切换 游戏库/已安装；L2/R2 翻页。
        if (button === 5 || button === 6) {
            setTab((current) => current === "catalog" ? "installed" : "catalog");
            return;
        }
        if (!root)
            return;
        if (button === 7) {
            root.scrollBy({ top: -Math.round(root.clientHeight * 0.8), behavior: "smooth" });
        }
        else if (button === 8) {
            root.scrollBy({ top: Math.round(root.clientHeight * 0.8), behavior: "smooth" });
        }
    }, []);
    const handleLibraryDirection = SP_REACT.useCallback((evt) => {
        const root = libraryRootRef.current;
        const button = Number(evt?.detail?.button || 0);
        if (!root || (button !== 9 && button !== 10))
            return;
        const step = evt?.detail?.is_repeat ? 120 : 72;
        root.scrollBy({ top: button === 9 ? -step : step, behavior: "smooth" });
    }, []);
    SP_REACT.useEffect(() => {
        let cancelled = false;
        getTianyiCatalogUpdate({ max_items: 12 }).then((result) => {
            if (cancelled || result.status !== "success" || !result.data)
                return;
            const data = result.data;
            setCatalogUpdate({
                added_count: Number(data.added_count || 0),
                items: Array.isArray(data.items) ? data.items : [],
                updated_at: Number(data.updated_at || 0),
            });
        }).catch(() => { });
        getTianyiCoverProxyBase().then((result) => {
            if (cancelled || result.status !== "success" || !result.data)
                return;
            setCoverProxyBase(String(result.data.base || ""));
        }).catch(() => { });
        return () => { cancelled = true; };
    }, []);
    // 用 ref 做同步锁：state 更新有延迟，快速连点会绕过 busyKey 判断导致重复请求/互相清 busy。
    const beginBusy = SP_REACT.useCallback((key) => {
        if (busyRef.current)
            return false;
        busyRef.current = key;
        setBusyKey(key);
        return true;
    }, []);
    const endBusy = SP_REACT.useCallback(() => {
        busyRef.current = "";
        setBusyKey("");
    }, []);
    const loadCatalog = SP_REACT.useCallback(async (targetPage, append = false) => {
        const requestSeq = catalogRequestRef.current + 1;
        catalogRequestRef.current = requestSeq;
        setLoadingCatalog(true);
        try {
            const result = await withTimeout(listTianyiCatalog({
                query: activeQuery,
                page: Math.max(1, targetPage),
                page_size: pageSize,
                platform,
                category,
                sort,
            }), 15000, "读取游戏列表超时");
            // 过滤条件/翻页可能并发触发多个请求：只让最后一次请求的结果落地，避免旧响应覆盖新列表。
            if (catalogRequestRef.current !== requestSeq)
                return;
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "读取游戏列表失败");
            }
            const data = result.data;
            const nextPage = {
                total: Number(data.total || 0),
                page: Number(data.page || 1),
                page_size: Number(data.page_size || pageSize),
                platforms: Array.isArray(data.platforms) ? data.platforms : [],
                categories: Array.isArray(data.categories) ? data.categories : [],
                items: Array.isArray(data.items) ? data.items : [],
            };
            if (append) {
                setCatalog((prev) => ({
                    ...nextPage,
                    items: [...prev.items, ...nextPage.items],
                }));
            }
            else {
                setCatalog(nextPage);
            }
            setPage(Number(data.page || 1));
        }
        catch (error) {
            if (catalogRequestRef.current === requestSeq)
                toastError(error);
        }
        finally {
            if (catalogRequestRef.current === requestSeq)
                setLoadingCatalog(false);
        }
    }, [activeQuery, platform, category, sort, reloadNonce]);
    const loadInstalled = SP_REACT.useCallback(async () => {
        const requestSeq = installedRequestRef.current + 1;
        installedRequestRef.current = requestSeq;
        setLoadingInstalled(true);
        try {
            const result = await withTimeout(listTianyiInstalledGames(), 15000, "读取已安装列表超时");
            if (installedRequestRef.current !== requestSeq)
                return;
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "读取已安装列表失败");
            }
            const data = result.data;
            setInstalled({
                total: Number(data.total || 0),
                items: Array.isArray(data.items) ? data.items : [],
            });
        }
        catch (error) {
            if (installedRequestRef.current === requestSeq)
                toastError(error);
        }
        finally {
            if (installedRequestRef.current === requestSeq)
                setLoadingInstalled(false);
        }
    }, []);
    // 搜索词/筛选没变时（例如同一个词再按一次回车）也要能刷新：用 nonce 触发 effect 重新拉取。
    const submitSearch = SP_REACT.useCallback(() => {
        setActiveQuery(query.trim());
        setPage(1);
        setReloadNonce((value) => value + 1);
    }, [query]);
    const resetSearch = SP_REACT.useCallback(() => {
        setQuery("");
        setActiveQuery("");
        setPlatform("");
        setCategory("");
        setSort("");
        setPage(1);
        setReloadNonce((value) => value + 1);
    }, []);
    const loadMore = SP_REACT.useCallback(() => {
        if (loadingCatalog)
            return;
        if (catalog.items.length >= catalog.total)
            return;
        void loadCatalog(page + 1, true);
    }, [catalog.items.length, catalog.total, loadCatalog, loadingCatalog, page]);
    const refreshCatalog = SP_REACT.useCallback(async () => {
        if (tab === "installed") {
            await loadInstalled();
            return;
        }
        if (loadingCatalog)
            return;
        setLoadingCatalog(true);
        try {
            const result = await withTimeout(refreshTianyiCatalog(), 45000, "刷新远程目录超时");
            if (result.status !== "success") {
                throw new Error(result.message || "刷新远程目录失败");
            }
            setPage(1);
            await loadCatalog(1);
            toaster.toast({
                title: "freedeckCY",
                body: `目录已刷新：${result.data?.total ?? 0} 条（${result.data?.source || "unknown"}）`,
            });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            setLoadingCatalog(false);
        }
    }, [loadCatalog, loadInstalled, loadingCatalog, tab]);
    SP_REACT.useEffect(() => {
        void loadCatalog(1);
    }, [loadCatalog]);
    SP_REACT.useEffect(() => {
        if (tab === "installed")
            void loadInstalled();
    }, [tab, loadInstalled]);
    const sortOptions = SP_REACT.useMemo(() => [
        { data: "", label: "默认排序" },
        { data: "title", label: "名称" },
        { data: "size_desc", label: "大小从大到小" },
        { data: "size_asc", label: "大小从小到大" },
    ], []);
    const platformChips = SP_REACT.useMemo(() => [
        { value: "", label: "全部" },
        ...(catalog.platforms || []).map((item) => ({
            value: String(item.value || ""),
            label: String(item.label || item.value || "").toUpperCase(),
        })),
    ], [catalog.platforms]);
    const categoryChips = SP_REACT.useMemo(() => {
        const items = (catalog.categories || []).slice(0, 14).map((item) => ({
            value: String(item.value || ""),
            label: String(item.label || item.value || ""),
        }));
        if (category && !items.some((item) => item.value === category)) {
            items.unshift({ value: category, label: category });
        }
        return items;
    }, [catalog.categories, category]);
    const hasActiveFilters = Boolean(activeQuery || platform || category || sort);
    const categorySections = SP_REACT.useMemo(() => {
        const buckets = new Map();
        for (const item of catalog.items) {
            const firstTag = String(item.categories || "")
                .split(/[,，、|/]+/)
                .map((tag) => tag.trim())
                .find(Boolean);
            const title = firstTag || "其他";
            const bucket = buckets.get(title) || [];
            bucket.push(item);
            buckets.set(title, bucket);
        }
        const sections = Array.from(buckets.entries())
            .filter(([, items]) => items.length >= 2)
            .sort((a, b) => b[1].length - a[1].length)
            .slice(0, 8);
        const sectionIds = new Set(sections.flatMap(([, items]) => items.map((item) => item.game_id)));
        const rest = catalog.items.filter((item) => !sectionIds.has(item.game_id));
        if (rest.length > 0)
            sections.push(["其他", rest]);
        return sections;
    }, [catalog.items]);
    const showShelves = !hasActiveFilters && !activeQuery;
    const onPrepareInstall = SP_REACT.useCallback(async (item) => {
        if (!beginBusy(item.game_id))
            return;
        try {
            const result = await withTimeout(prepareTianyiInstall({ game_id: item.game_id }), 30000, "生成安装计划超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "生成安装计划失败");
            }
            const plan = result.data;
            if (!plan.can_install) {
                throw new Error(plan.message || "磁盘空间不足，无法安装");
            }
            let preflightWarning = "";
            try {
                const preflight = await withTimeout(preflightTianyiInstall(), 15000, "安装环境检查超时");
                const failedChecks = preflight.status === "success" && preflight.data
                    ? (preflight.data.checks || []).filter((check) => !check.ok)
                    : [];
                if (failedChecks.length > 0) {
                    preflightWarning = "\n\n环境检查：\n" + failedChecks.map((check) => `⚠ ${check.message || check.id}`).join("\n");
                }
            }
            catch {
                // 环境检查失败不阻断安装，继续展示安装计划。
            }
            const emulatorText = plan.emulator_info?.name ? `模拟器：${plan.emulator_info.name}` : "PC / Proton";
            const setupText = plan.emulator_info?.setup_hint ? `\n提示：${plan.emulator_info.setup_hint}` : "";
            DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, { strTitle: `安装 ${plan.game_title || item.title}`, strDescription: `下载：${plan.required_download_human || "未知"} → ${plan.download_dir || "-"}\n` +
                    `安装：${plan.required_install_human || "未知"} → ${plan.install_dir || "-"}\n` +
                    `${emulatorText}${setupText}${preflightWarning}`, strOKButtonText: preflightWarning ? "仍然下载" : "开始下载", strCancelButtonText: "\u53D6\u6D88", onOK: () => {
                    void (async () => {
                        try {
                            const started = await withTimeout(startTianyiInstall({ game_id: item.game_id }), 30000, "启动安装超时");
                            if (started.status !== "success") {
                                throw new Error(started.message || "启动安装失败");
                            }
                            toaster.toast({ title: "freedeckCY", body: "已加入下载队列，可在插件主页查看任务进度" });
                        }
                        catch (error) {
                            toastError(error);
                        }
                    })();
                }, onCancel: () => { } }));
        }
        catch (error) {
            toastError(error);
        }
        finally {
            endBusy();
        }
    }, [beginBusy, endBusy]);
    const onLaunchInstalled = SP_REACT.useCallback(async (item) => {
        if (!beginBusy(item.game_id))
            return;
        try {
            const result = await withTimeout(launchTianyiInstalledGame(item.game_id), 20000, "启动游戏超时");
            if (result.status !== "success")
                throw new Error(result.message || "启动失败");
            toaster.toast({ title: "freedeckCY", body: `正在启动 ${item.title}` });
        }
        catch (error) {
            toastError(error);
        }
        finally {
            endBusy();
        }
    }, [beginBusy, endBusy]);
    const onHealthCheck = SP_REACT.useCallback(async () => {
        if (healthBusy)
            return;
        setHealthBusy(true);
        try {
            const result = await withTimeout(getTianyiInstalledHealth(), 120000, "健康检查超时");
            if (result.status !== "success")
                throw new Error(result.message || "健康检查失败");
            const data = result.data || {};
            const bad = (data.items || []).filter((item) => !item.ok);
            const repairable = bad.filter((item) => Boolean(item.game_id) && !item.needs_reinstall);
            const reinstallable = bad.filter((item) => Boolean(item.game_id) && item.needs_reinstall);
            const lines = [`共 ${data.total || 0} 个游戏，正常 ${data.ok || 0} 个，异常 ${bad.length} 个。`];
            bad.slice(0, 12).forEach((item) => lines.push(`❌ ${item.title || item.game_id}${item.needs_reinstall ? " · 需重下" : ""}`));
            if (bad.length > 12) lines.push(`…另有 ${bad.length - 12} 个`);
            if (repairable.length > 0)
                lines.push("", `可修复 ${repairable.length} 个`);
            if (reinstallable.length > 0)
                lines.push("", `需重下 ${reinstallable.length} 个，可点下方「重新下载」`);
            DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, { strTitle: "游戏健康中心", strDescription: lines.join("\n"), strOKButtonText: repairable.length > 0 ? "修复可修复项" : "完成", strMiddleButtonText: reinstallable.length > 0 ? `重新下载（${reinstallable.length}）` : undefined, strCancelButtonText: "关闭", onMiddleButton: () => {
                    if (reinstallable.length === 0)
                        return;
                    void (async () => {
                        setHealthBusy(true);
                        try {
                            const started = await withTimeout(reinstallTianyiInstalledGames({ game_ids: reinstallable.map((item) => item.game_id) }), 600000, "重新下载超时");
                            if (started.status !== "success" || !started.data) {
                                throw new Error(started.message || "重新下载失败");
                            }
                            const startedData = started.data;
                            toaster.toast({
                                title: "freedeckCY",
                                body: startedData.failed > 0
                                    ? `已开始重新下载 ${startedData.started || 0} 个，失败 ${startedData.failed} 个`
                                    : `已开始重新下载 ${startedData.started || 0} 个游戏`,
                            });
                            await loadInstalled();
                        }
                        catch (error) {
                            toastError(error);
                        }
                        finally {
                            setHealthBusy(false);
                        }
                    })();
                }, onOK: () => {
                    if (repairable.length === 0)
                        return;
                    void (async () => {
                        setHealthBusy(true);
                        let repaired = 0;
                        const failed = [];
                        for (const item of repairable) {
                            try {
                                const repairedResult = await withTimeout(repairTianyiInstalledGame(item.game_id), 120000, "修复超时");
                                if (repairedResult.status === "success" && repairedResult.data?.ok)
                                    repaired += 1;
                                else
                                    failed.push(item.title || item.game_id);
                            }
                            catch {
                                failed.push(item.title || item.game_id);
                            }
                        }
                        toaster.toast({ title: "freedeckCY", body: failed.length > 0 ? `修复完成：成功 ${repaired} 个，失败 ${failed.length} 个` : `已修复 ${repaired} 个游戏` });
                        try {
                            await loadInstalled();
                        }
                        catch {
                            // 刷新失败不影响修复结果。
                        }
                        finally {
                            setHealthBusy(false);
                        }
                    })();
                }, onCancel: () => { } }));
        }
        catch (error) { toastError(error); }
        finally { setHealthBusy(false); }
    }, [healthBusy, loadInstalled]);
    const onOpenFolder = SP_REACT.useCallback(async (item) => {
        if (!beginBusy(item.game_id))
            return;
        try {
            const result = await withTimeout(openTianyiInstalledFolder(item.game_id), 20000, "打开目录超时");
            if (result.status !== "success")
                throw new Error(result.message || "打开目录失败");
        }
        catch (error) {
            toastError(error);
        }
        finally {
            endBusy();
        }
    }, [beginBusy, endBusy]);
    const onCheckInstalled = SP_REACT.useCallback(async (item) => {
        if (!beginBusy(item.game_id))
            return;
        try {
            const result = await withTimeout(repairTianyiInstalledGame(item.game_id), 120000, "校验/修复超时");
            if (result.status !== "success")
                throw new Error(result.message || "校验失败");
            const data = result.data || {};
            const after = data.after || data.before || {};
            const labels = {
                install_path: "安装目录",
                executable: "可执行文件",
                rom: "ROM 文件",
                launcher: "启动脚本",
                steam_shortcut: "Steam 快捷方式",
            };
            const lines = (after.checks || []).map((check) => `${check.ok ? "✅" : "❌"} ${labels[check.id] || check.id}${check.message ? `：${check.message}` : ""}`);
            if (after.needs_reinstall)
                lines.unshift("需要重新下载安装。");
            else if (after.ok)
                lines.unshift((data.actions || []).length ? "已执行修复。" : "安装完整，无需修复。");
            else
                lines.unshift("校验发现问题，请打开目录检查。");
            DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, {
                strTitle: "安装校验",
                strDescription: lines.join("\n"),
                strOKButtonText: after.needs_reinstall ? "重新下载" : "完成",
                strCancelButtonText: "关闭",
                onOK: () => {
                    if (after.needs_reinstall)
                        void onPrepareInstall(item);
                },
                onCancel: () => {
                },
            }));
            await loadInstalled();
        }
        catch (error) {
            toastError(error);
        }
        finally {
            endBusy();
        }
    }, [beginBusy, endBusy, loadInstalled, onPrepareInstall]);
    const onUninstall = SP_REACT.useCallback((item) => {
        if (busyRef.current)
            return;
        DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, { strTitle: `卸载 ${item.title}`, strDescription: "\u5C06\u5220\u9664\u5B89\u88C5\u76EE\u5F55\u5E76\u79FB\u9664\u8BB0\u5F55\uFF0C\u662F\u5426\u7EE7\u7EED\uFF1F", strOKButtonText: "\u5378\u8F7D", strCancelButtonText: "\u53D6\u6D88", onOK: () => {
                void (async () => {
                    if (!beginBusy(item.game_id))
                        return;
                    try {
                        const result = await withTimeout(uninstallTianyiInstalled({
                            game_id: item.game_id,
                            install_path: item.install_path,
                            delete_files: true,
                        }), 120000, "卸载超时（大目录删除可能较慢，请稍后刷新确认）");
                        if (result.status !== "success")
                            throw new Error(result.message || "卸载失败");
                        toaster.toast({ title: "freedeckCY", body: `已卸载：${item.title || item.game_id}` });
                        await loadInstalled();
                    }
                    catch (error) {
                        toastError(error);
                    }
                    finally {
                        endBusy();
                    }
                })();
            }, onCancel: () => { } }));
    }, [beginBusy, endBusy, loadInstalled]);
    const handleClose = SP_REACT.useCallback(() => {
        if (onClose) {
            try {
                onClose();
                return;
            }
            catch {
                // onClose 失效时继续走路由返回兜底。
            }
        }
        try {
            DFL.Navigation.NavigateBack();
        }
        catch {
            try {
                DFL.Router.CloseSideMenus?.();
            }
            catch {
                // 忽略关闭失败。
            }
        }
    }, [onClose]);
    const handleSteamLibrary = SP_REACT.useCallback(() => {
        // modal 模式先关弹层；路由模式先留在插件页，导航失败再回退。
        try {
            onClose?.();
        }
        catch {
            // 忽略关闭失败。
        }
        try {
            DFL.Navigation.NavigateToLibraryTab();
            return;
        }
        catch {
            // 继续尝试旧接口。
        }
        try {
            DFL.Router.NavigateToLibraryTab?.();
            return;
        }
        catch {
            // 继续尝试返回。
        }
        if (!onClose) {
            try {
                DFL.Navigation.NavigateBack();
            }
            catch {
                // 忽略关闭失败。
            }
        }
    }, [onClose]);
    const onOpenDetail = SP_REACT.useCallback((item) => {
        let modal = null;
        try {
            modal = DFL.showModal(SP_JSX.jsx(GameDetailModal, { item: item, installed: Boolean(item.game_id && installedGameIds.has(item.game_id)), busy: Boolean(busyKey), onInstall: (selectedItem) => {
                    try {
                        modal?.Close();
                    }
                    catch {
                        // 忽略关闭失败。
                    }
                    void onPrepareInstall(selectedItem || item);
                }, onClose: () => {
                    try {
                        modal?.Close();
                    }
                    catch {
                        // 忽略关闭失败。
                    }
                } }), undefined, {
                strTitle: "游戏详情",
                bNeverPopOut: true,
                fnOnClose: () => {
                    modal = null;
                },
            });
        }
        catch (error) {
            toastError(error);
        }
    }, [busyKey, installedGameIds, onPrepareInstall]);
    const heroItem = catalog.items.find((item) => String(item.cover_url || item.cover_portrait_url || "").trim()) || catalog.items[0] || null;
    const heroCover = heroItem ? String(heroItem.cover_url || heroItem.cover_portrait_url || "").trim() : "";
    const renderCatalogCard = (item, width) => {
        const isInstalled = Boolean(item.game_id && installedGameIds.has(item.game_id));
        const meta = [item.size_text, item.provider_label].filter(Boolean).join(" · ") || "-";
        return (SP_JSX.jsx(LibraryCoverCard, { title: item.title || "未命名游戏", platform: item.platform, meta: meta, providerLabel: item.provider_label || "", coverUrl: item.cover_portrait_url || item.cover_url, installed: isInstalled, busyLabel: busyKey === item.game_id ? "处理中..." : "", disabled: Boolean(busyKey), coverProxyBase: coverProxyBase, onPress: () => onOpenDetail(item), width: width }, item.game_id));
    };
    const renderInstalledCard = (item) => (SP_JSX.jsx(LibraryCoverCard, { title: item.title || "未命名游戏", platform: item.platform, meta: item.playtime_text ? `${item.size_text || "-"} · ${item.playtime_text}` : (item.size_text || "-"), providerLabel: item.provider_label || "", coverUrl: item.cover_portrait_url || item.cover_url, installed: true, disabled: Boolean(busyKey), coverProxyBase: coverProxyBase, onPress: () => void onLaunchInstalled(item), actions: SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onCheckInstalled(item), disabled: Boolean(busyKey), style: { flex: 1, minWidth: 0, padding: "5px 2px", fontSize: "11px" }, children: "校验" }), SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onOpenFolder(item), disabled: Boolean(busyKey), style: { flex: 1, minWidth: 0, padding: "5px 2px", fontSize: "11px" }, children: "目录" }), SP_JSX.jsx(DFL.DialogButton, { onClick: () => onUninstall(item), disabled: Boolean(busyKey), style: { flex: 1, minWidth: 0, padding: "5px 2px", fontSize: "11px", background: "rgba(255,106,106,0.22)" }, children: "卸载" })] }) }, item.game_id));
    const renderSkeletonGrid = (count) => (SP_JSX.jsx(DFL.Focusable, { className: "fdc-grid", "flow-children": "row", children: Array.from({ length: count || 12 }).map((_, index) => (SP_JSX.jsx(LibrarySkeletonCard, {}, `skeleton-${index}`))) }));
    const renderChips = (items, active, onPick) => items.map((item) => {
        const value = String(item.value !== undefined ? item.value : (item.data || ""));
        return (SP_JSX.jsx(DFL.DialogButton, { className: "fdc-chip" + (String(active || "") === value ? " fdc-chip-active" : ""), onClick: () => { onPick(value); setPage(1); }, children: item.label }, `chip:${value || "all"}`));
    });
    return (SP_JSX.jsxs(DFL.Focusable, { ref: libraryRootRef, "data-fdc-i18n": "1", noFocusRing: true, onCancel: handleClose, onButtonDown: handleLibraryButton, onGamepadDirection: handleLibraryDirection, onCancelActionDescription: "返回", onOKActionDescription: "选择", className: "fdc-root", "flow-children": "column", style: {
            height: "100%",
            overflowY: "auto",
            boxSizing: "border-box",
            padding: "40px 14px 160px",
            position: "relative",
            touchAction: "pan-y",
            WebkitOverflowScrolling: "touch",
            overscrollBehavior: "contain",
        }, children: [SP_JSX.jsx("style", { children: LIBRARY_CSS }), SP_JSX.jsx("div", { "aria-hidden": "true", style: { position: "fixed", top: 0, left: 0, right: 0, height: "40px", background: "#0b0f14", zIndex: 50, pointerEvents: "none" } }), SP_JSX.jsx("div", { "aria-hidden": "true", style: { position: "fixed", bottom: 0, left: 0, right: 0, height: "72px", background: "#0b0f14", zIndex: 50, pointerEvents: "none" } }), SP_JSX.jsxs(DFL.Focusable, { className: "fdc-topbar", "flow-children": "row", children: [SP_JSX.jsxs(DFL.Focusable, { "flow-children": "row", style: { display: "flex", gap: "6px", flex: "0 1 auto", minWidth: 0 }, children: [SP_JSX.jsx(DFL.DialogButton, { onClick: handleClose, style: { width: "auto", padding: "8px 14px" }, children: "返回" }), SP_JSX.jsx(DFL.DialogButton, { onClick: handleSteamLibrary, style: { width: "auto", padding: "8px 14px" }, children: "Steam 库" })] }), SP_JSX.jsxs("div", { className: "fdc-heading", children: [SP_JSX.jsx("div", { className: "fdc-title", children: "freedeckCY 游戏库" }), SP_JSX.jsx("div", { className: "fdc-subtitle", children: tab === "catalog" ? `${catalog.total} 款游戏${hasActiveFilters ? " · 已筛选" : ""}` : `${installed.total} 款已安装` })] }), SP_JSX.jsxs(DFL.Focusable, { className: "fdc-tabs", "flow-children": "row", children: [SP_JSX.jsx(DFL.DialogButton, { className: "fdc-tab" + (tab === "catalog" ? " fdc-tab-active" : ""), onClick: () => setTab("catalog"), children: "游戏库" }), SP_JSX.jsxs(DFL.DialogButton, { className: "fdc-tab" + (tab === "installed" ? " fdc-tab-active" : ""), onClick: () => setTab("installed"), children: ["已安装", installed.total ? ` (${installed.total})` : ""] })] }), SP_JSX.jsx(DFL.DialogButton, { className: "fdc-button", onClick: () => void refreshCatalog(), disabled: loadingCatalog || loadingInstalled, children: loadingCatalog || loadingInstalled ? "刷新中..." : "刷新" }), SP_JSX.jsx(DFL.DialogButton, { className: "fdc-button", onClick: () => void onHealthCheck(), disabled: healthBusy, children: healthBusy ? "体检中..." : "体检" })] }), tab === "catalog" ? (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsxs(DFL.Focusable, { className: "fdc-search-row", "flow-children": "row", children: [SP_JSX.jsx("div", { className: "fdc-search", children: SP_JSX.jsx(DFL.TextField, { "aria-label": "搜索游戏", placeholder: "搜索游戏", value: query, onChange: (event) => setQuery(getTextFieldValue(event)), onKeyDown: (event) => { if (event.key === "Enter") submitSearch(); } }) }), SP_JSX.jsx(DFL.DialogButton, { className: "fdc-button", onClick: submitSearch, children: "搜索" }), SP_JSX.jsx(DFL.DialogButton, { className: "fdc-button", onClick: () => setFiltersOpen((value) => !value), children: filtersOpen ? "收起筛选" : "筛选" })] }), filtersOpen ? (SP_JSX.jsxs("div", { className: "fdc-filter-panel", children: [SP_JSX.jsxs(DFL.Focusable, { className: "fdc-filter-row", "flow-children": "row", children: [SP_JSX.jsx("span", { className: "fdc-label", children: "平台" }), renderChips(platformChips, platform, setPlatform)] }), SP_JSX.jsxs(DFL.Focusable, { className: "fdc-filter-row", "flow-children": "row", children: [SP_JSX.jsx("span", { className: "fdc-label", children: "分类" }), renderChips(categoryChips, category, setCategory)] }), SP_JSX.jsxs(DFL.Focusable, { className: "fdc-filter-row", "flow-children": "row", children: [SP_JSX.jsx("span", { className: "fdc-label", children: "排序" }), renderChips(sortOptions, sort, setSort), SP_JSX.jsx(DFL.DialogButton, { className: "fdc-chip", onClick: resetSearch, children: "清空筛选" })] })] })) : null, showShelves && heroItem ? (SP_JSX.jsxs("div", { className: "fdc-hero", children: [SP_JSX.jsx("div", { className: "fdc-hero-bg", style: heroCover ? { backgroundImage: `url("${heroCover.replace(/"/g, "%22")}")` } : {} }), SP_JSX.jsx("div", { className: "fdc-hero-shade" }), SP_JSX.jsxs("div", { className: "fdc-hero-content", children: [SP_JSX.jsx("div", { className: "fdc-hero-eyebrow", children: "推荐 · 最近更新" }), SP_JSX.jsx("div", { "data-fdc-i18n-skip": "1", className: "fdc-hero-title", children: String(heroItem.title || "未命名游戏").split("/")[0] }), SP_JSX.jsx("div", { className: "fdc-hero-meta", children: [String(heroItem.platform || "pc").toUpperCase(), heroItem.size_text, heroItem.provider_label].filter(Boolean).join(" · ") }), SP_JSX.jsxs(DFL.Focusable, { className: "fdc-hero-actions", "flow-children": "row", children: [SP_JSX.jsx(DFL.DialogButton, { onClick: () => onOpenDetail(heroItem), style: { width: "auto", padding: "9px 18px", background: "rgba(101,214,192,0.20)", border: "1px solid rgba(101,214,192,0.55)" }, children: "查看详情" }), catalog.items.length > 1 ? (SP_JSX.jsx(DFL.DialogButton, { onClick: () => setFiltersOpen(true), style: { width: "auto", padding: "9px 18px" }, children: "全部游戏" })) : null] })] })] })) : null, showShelves && catalogUpdate.items.length ? (SP_JSX.jsxs("section", { className: "fdc-shelf-block", children: [SP_JSX.jsxs("div", { className: "fdc-section-head", children: [SP_JSX.jsx("div", { className: "fdc-section-title", children: `最近更新（${catalogUpdate.added_count || catalogUpdate.items.length}）` }), SP_JSX.jsx("div", { className: "fdc-section-count", children: "新加入目录" })] }), SP_JSX.jsx(DFL.Focusable, { className: "fdc-shelf", "flow-children": "row", children: catalogUpdate.items.map((item) => (SP_JSX.jsx(LibraryCoverCard, { title: item.title || "未命名游戏", platform: item.platform, meta: [item.size_text, item.provider_label].filter(Boolean).join(" · ") || "-", providerLabel: item.provider_label || "", coverUrl: item.cover_portrait_url || item.cover_url, installed: Boolean(item.game_id && installedGameIds.has(item.game_id)), busyLabel: busyKey === item.game_id ? "处理中..." : "", disabled: Boolean(busyKey), coverProxyBase: coverProxyBase, onPress: () => onOpenDetail(item), width: 158 }, `recent:${item.game_id}`))) })] })) : null, loadingCatalog && catalog.items.length === 0 ? renderSkeletonGrid(12) : catalog.items.length === 0 ? (SP_JSX.jsx("div", { className: "fdc-empty", children: "没有匹配游戏，试试清空筛选或更换关键词" })) : showShelves ? (SP_JSX.jsxs(SP_JSX.Fragment, { children: [categorySections.map(([sectionTitle, items]) => (SP_JSX.jsxs("section", { className: "fdc-shelf-block", children: [SP_JSX.jsxs("div", { className: "fdc-section-head", children: [SP_JSX.jsx("div", { className: "fdc-section-title", children: sectionTitle }), SP_JSX.jsx("div", { className: "fdc-section-count", children: `${items.length} 款` })] }), SP_JSX.jsx(DFL.Focusable, { className: "fdc-shelf", "flow-children": "row", children: items.map((item) => (SP_JSX.jsx(LibraryCoverCard, { title: item.title || "未命名游戏", platform: item.platform, meta: [item.size_text, item.provider_label].filter(Boolean).join(" · ") || "-", providerLabel: item.provider_label || "", coverUrl: item.cover_portrait_url || item.cover_url, installed: Boolean(item.game_id && installedGameIds.has(item.game_id)), busyLabel: busyKey === item.game_id ? "处理中..." : "", disabled: Boolean(busyKey), coverProxyBase: coverProxyBase, onPress: () => onOpenDetail(item), width: 158 }, item.game_id))) })] }, `shelf:${sectionTitle}`)))] })) : (SP_JSX.jsx(DFL.Focusable, { className: "fdc-grid", "flow-children": "row", children: catalog.items.map((item) => renderCatalogCard(item)) })), catalog.items.length < catalog.total ? (SP_JSX.jsxs("div", { className: "fdc-footer", children: [SP_JSX.jsx(DFL.DialogButton, { onClick: loadMore, disabled: loadingCatalog, style: { width: "auto", padding: "8px 20px" }, children: loadingCatalog ? "加载中..." : "加载更多" }), SP_JSX.jsx("span", { children: `已显示 ${catalog.items.length} / ${catalog.total}` })] })) : null] })) : (SP_JSX.jsxs(SP_JSX.Fragment, { children: [loadingInstalled && installed.items.length === 0 ? renderSkeletonGrid(8) : installed.items.length === 0 ? (SP_JSX.jsx("div", { className: "fdc-empty", children: "还没有已安装游戏" })) : (SP_JSX.jsx(DFL.Focusable, { className: "fdc-grid", "flow-children": "row", children: installed.items.map((item) => renderInstalledCard(item)) }))] }))] }));
}

var index = definePlugin(() => {
    routerHook.addRoute(SETTINGS_ROUTE, SettingsPage);
    routerHook.addRoute(LIBRARY_ROUTE, LibraryPage);
    const unpatchLibraryPlaytime = installLibraryPlaytimePatch();
    let uninstallGameActionReporter = () => { };
    try {
        uninstallGameActionReporter = installGlobalGameActionReporter();
    }
    catch {
        // 忽略全局游戏事件监听初始化失败，避免影响插件主 UI。
    }
    return {
        name: "freedeckCY",
        titleView: SP_JSX.jsx("div", { className: DFL.staticClasses.Title, children: "freedeckCY" }),
        content: SP_JSX.jsx(Content, {}),
        icon: SP_JSX.jsx(FaCloudDownloadAlt, {}),
        onDismount() {
            uninstallGameActionReporter();
            unpatchLibraryPlaytime();
            routerHook.removeRoute(SETTINGS_ROUTE);
            routerHook.removeRoute(LIBRARY_ROUTE);
        },
    };
});

export { index as default };
//# sourceMappingURL=index.js.map

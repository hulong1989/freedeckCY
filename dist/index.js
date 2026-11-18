// @ts-nocheck


const _local_SP_JSX = { jsx: SP_JSX.jsx, jsxs: SP_JSX.jsxs, Fragment: SP_JSX.Fragment };
const manifest = { "name": "freedeckCY" };
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
const toaster = api.toaster;
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
var IconContext = SP_REACT.createContext && /*#__PURE__*/ SP_REACT.createContext(DefaultContext);
var _excluded = ["attr", "size", "title"];
function _objectWithoutProperties(source, excluded) { if (source == null)
    return {}; var target = _objectWithoutPropertiesLoose(source, excluded); var key, i; if (Object.getOwnPropertySymbols) {
    var sourceSymbolKeys = Object.getOwnPropertySymbols(source);
    for (i = 0; i < sourceSymbolKeys.length; i++) {
        key = sourceSymbolKeys[i];
        if (excluded.indexOf(key) >= 0)
            continue;
        if (!Object.prototype.propertyIsEnumerable.call(source, key))
            continue;
        target[key] = source[key];
    }
} return target; }
function _objectWithoutPropertiesLoose(source, excluded) { if (source == null)
    return {}; var target = {}; for (var key in source) {
    if (Object.prototype.hasOwnProperty.call(source, key)) {
        if (excluded.indexOf(key) >= 0)
            continue;
        target[key] = source[key];
    }
} return target; }
function _extends() { _extends = Object.assign ? Object.assign.bind() : function (target) { for (var i = 1; i < arguments.length; i++) {
    var source = arguments[i];
    for (var key in source) {
        if (Object.prototype.hasOwnProperty.call(source, key)) {
            target[key] = source[key];
        }
    }
} return target; }; return _extends.apply(this, arguments); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) {
    var o = Object.getOwnPropertySymbols(e);
    r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o);
} return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) {
    var t = null != arguments[r] ? arguments[r] : {};
    r % 2 ? ownKeys(Object(t), true).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); });
} return e; }
function _defineProperty(obj, key, value) { key = _toPropertyKey(key); if (key in obj) {
    Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true });
}
else {
    obj[key] = value;
} return obj; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == typeof i ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != typeof t || !t)
    return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) {
    var i = e.call(t, r);
    if ("object" != typeof i)
        return i;
    throw new TypeError("@@toPrimitive must return a primitive value.");
} return ("string" === r ? String : Number)(t); }
function Tree2Element(tree) {
    return tree && tree.map((node, i) => /*#__PURE__*/ SP_REACT.createElement(node.tag, _objectSpread({
        key: i
    }, node.attr), Tree2Element(node.child)));
}
function GenIcon(data) {
    return props => /*#__PURE__*/ SP_REACT.createElement(IconBase, _extends({
        attr: _objectSpread({}, data.attr)
    }, props), Tree2Element(data.child));
}
function IconBase(props) {
    var elem = conf => {
        var { attr, size, title } = props, svgProps = _objectWithoutProperties(props, _excluded);
        var computedSize = size || conf.size || "1em";
        var className;
        if (conf.className)
            className = conf.className;
        if (props.className)
            className = (className ? className + " " : "") + props.className;
        return /*#__PURE__*/ SP_REACT.createElement("svg", _extends({
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
        }), title && /*#__PURE__*/ SP_REACT.createElement("title", null, title), props.children);
    };
    return IconContext !== undefined ? /*#__PURE__*/ SP_REACT.createElement(IconContext.Consumer, null, conf => elem(conf)) : elem(DefaultContext);
}
// THIS FILE IS AUTO GENERATED
function FaCloudDownloadAlt(props) {
    return GenIcon({ "attr": { "viewBox": "0 0 640 512" }, "child": [{ "tag": "path", "attr": { "d": "M537.6 226.6c4.1-10.7 6.4-22.4 6.4-34.6 0-53-43-96-96-96-19.7 0-38.1 6-53.3 16.2C367 64.2 315.3 32 256 32c-88.4 0-160 71.6-160 160 0 2.7.1 5.4.2 8.1C40.2 219.8 0 273.2 0 336c0 79.5 64.5 144 144 144h368c70.7 0 128-57.3 128-128 0-61.9-44-113.6-102.4-125.4zm-132.9 88.7L299.3 420.7c-6.2 6.2-16.4 6.2-22.6 0L171.3 315.3c-10.1-10.1-2.9-27.3 11.3-27.3H248V176c0-8.8 7.2-16 16-16h48c8.8 0 16 7.2 16 16v112h65.4c14.2 0 21.4 17.2 11.3 27.3z" }, "child": [] }] })(props);
}
const SETTINGS_ROUTE = "/freedeckcy/settings";
const LIBRARY_ROUTE = "/freedeckcy/library";
const PLUGIN_UI_BUILD = "0.26.36";
const getTianyiPanelState = callable("get_tianyi_panel_state");
const restartSteamBackend = callable("restart_steam");
const clearSteamRestartPending = callable("clear_steam_restart_pending");
const clearTianyiCatalogUpdateNotice = callable("clear_tianyi_catalog_update_notice");
const getTianyiStorageOptions = callable("get_tianyi_storage_options");
const listTianyiCatalog = callable("list_tianyi_catalog");
const refreshTianyiCatalog = callable("refresh_tianyi_catalog");
const updateTianyiCatalog = callable("update_tianyi_catalog");
const prepareTianyiInstall = callable("prepare_tianyi_install");
const startTianyiInstall = callable("start_tianyi_install");
const listTianyiInstalledGames = callable("list_tianyi_installed_games");
const launchTianyiInstalledGame = callable("launch_tianyi_installed_game");
const openTianyiInstalledFolder = callable("open_tianyi_installed_folder");
const scanTianyiInstalledGames = callable("scan_tianyi_installed_games");
const runTianyiDiagnostics = callable("run_tianyi_diagnostics");
const checkTianyiUpdate = callable("check_tianyi_update");
const downloadTianyiUpdate = callable("download_tianyi_update");
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
const setTianyiSpeedLimit = callable("set_tianyi_speed_limit");
const pauseTianyiTask = callable("pause_tianyi_task");
const resumeTianyiTask = callable("resume_tianyi_task");
const removeTianyiTask = callable("remove_tianyi_task");
const retryTianyiTask = callable("retry_tianyi_task");
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
    return (_local_SP_JSX.jsxs("div", { style: {
            width: "100%",
            padding: "8px 0",
            display: "flex",
            flexDirection: "column",
            gap: "6px",
        }, children: [_local_SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }, children: [_local_SP_JSX.jsx("div", { style: {
                            fontSize: "14px",
                            fontWeight: 600,
                            lineHeight: 1.35,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            maxWidth: "70%",
                        }, title: title, children: title }), _local_SP_JSX.jsx("div", { style: { fontSize: "11px", color: colors.label }, children: downloadStatusText(task.status) })] }), _local_SP_JSX.jsx("div", { style: {
                    width: "100%",
                    height: "8px",
                    borderRadius: "999px",
                    background: colors.track,
                    overflow: "hidden",
                }, children: _local_SP_JSX.jsx("div", { style: {
                        width: `${progress.toFixed(1)}%`,
                        height: "100%",
                        borderRadius: "999px",
                        background: colors.fill,
                        transition: "width 860ms linear",
                    } }) }), _local_SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", fontSize: "11px", color: "#c9c9c9" }, children: [_local_SP_JSX.jsx("span", { children: `进度 ${progress.toFixed(1)}%` }), _local_SP_JSX.jsx("span", { children: `速度 ${formatSpeed(task.speed)}` })] }), installStatus ? (_local_SP_JSX.jsx("div", { style: { fontSize: "11px", color: "#bcbcbc", lineHeight: 1.4 }, children: `安装：${installStatusText(installStatus)}${installMessage ? ` | ${installMessage}` : ""}` })) : null, errorReason ? (_local_SP_JSX.jsx("div", { style: { fontSize: "11px", color: "#ff8e8e", lineHeight: 1.4 }, children: `错误：${errorReason}` })) : null] }));
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
    return (_local_SP_JSX.jsx("div", { id: LIBRARY_TIME_BLOCK_ID, style: {
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
        }, children: _local_SP_JSX.jsxs("div", { style: { display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)", gap: "10px" }, children: [_local_SP_JSX.jsxs("div", { style: { minWidth: 0 }, children: [_local_SP_JSX.jsx("div", { style: { fontSize: "14px", fontWeight: 700, lineHeight: 1.2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }, children: `${myPlaytime}${activeSuffix}` }), _local_SP_JSX.jsx("div", { style: { fontSize: "10px", opacity: 0.84 }, children: "\u5DF2\u73A9\u65F6\u957F" })] }), _local_SP_JSX.jsxs("div", { style: { minWidth: 0 }, children: [_local_SP_JSX.jsx("div", { style: { fontSize: "14px", fontWeight: 700, lineHeight: 1.2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }, children: mainStory }), _local_SP_JSX.jsx("div", { style: { fontSize: "10px", opacity: 0.84 }, children: "\u4E3B\u7EBF\u65F6\u957F" })] }), _local_SP_JSX.jsxs("div", { style: { minWidth: 0 }, children: [_local_SP_JSX.jsx("div", { style: { fontSize: "14px", fontWeight: 700, lineHeight: 1.2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }, children: totalTime }), _local_SP_JSX.jsx("div", { style: { fontSize: "10px", opacity: 0.84 }, children: "\u603B\u65F6\u957F" })] })] }) }));
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
                const nextComponent = (_local_SP_JSX.jsx(LibraryTimeBlock, { appId: runtimeAppId, title: runtimeTitle }, `freedeckcy-library-times-${runtimeAppId}`));
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
function SettingsPage() {
    const [loading, setLoading] = SP_REACT.useState(true);
    const [saving, setSaving] = SP_REACT.useState(false);
    const [clearingLogin, setClearingLogin] = SP_REACT.useState(false);
    const [scanningInstalled, setScanningInstalled] = SP_REACT.useState(false);
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
            const result = await withTimeout(checkTianyiUpdate(), 30000, "检查更新超时");
            if (result.status !== "success" || !result.data) {
                throw new Error(result.message || "检查更新失败");
            }
            setUpdateInfo(result.data);
            setUpdateMessage(String(result.data.message || (result.data.has_update ? `发现新版本 ${result.data.latest}` : "当前已是最新版本")));
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
            setUpdateMessage(String(result.data.message || "更新包已下载"));
            toaster.toast({ title: "freedeckCY", body: String(result.data.message || "更新包已下载"), duration: 7000 });
        }
        catch (error) {
            setUpdateMessage(errorText(error));
        }
        finally {
            setDownloadingUpdate(false);
        }
    }, [downloadingUpdate]);
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
                DFL.showModal(_local_SP_JSX.jsx(DFL.ConfirmModal, { strTitle: "\u786E\u8BA4\u8986\u76D6\u5B58\u6863", strDescription: `检测到 ${Number(plan.conflict_count || 0)} 个冲突文件，确认后会覆盖原有存档。` +
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
            content: (_local_SP_JSX.jsxs(_local_SP_JSX.Fragment, { children: [_local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u6E38\u620F\u76EE\u5F55", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: "\u4ECE\u670D\u52A1\u5668\u4E0B\u8F7D\u6700\u65B0\u7684\u6E38\u620F\u76EE\u5F55 CSV \u5230\u672C\u5730\uFF1B\u4E0B\u8F7D\u6210\u529F\u540E\u4F1A\u7ACB\u5373\u91CD\u65B0\u52A0\u8F7D\u3002" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.TextField, { label: "\u76EE\u5F55\u670D\u52A1\u5668 CSV \u5730\u5740\uFF08\u7559\u7A7A\u7528\u9ED8\u8BA4 GitHub\uFF09", value: settings.catalog_url, onChange: (event) => setSettings((prev) => ({ ...prev, catalog_url: getTextFieldValue(event) })) }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => savePatch({ catalog_url: settings.catalog_url }), disabled: saving, children: "\u4FDD\u5B58\u76EE\u5F55\u5730\u5740" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void onUpdateCatalog(), disabled: updatingCatalog || saving, children: updatingCatalog ? "正在检查..." : "检查并更新游戏列表" }) }), catalogUpdateMessage ? (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "11px", lineHeight: 1.45, opacity: 0.8 }, children: catalogUpdateMessage }) })) : null] }), _local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u4E0B\u8F7D\u76EE\u5F55", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: settings.download_dir || "未设置" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onPickDownloadDir, disabled: saving, children: "\u9009\u62E9\u4E0B\u8F7D\u76EE\u5F55" }) }), storageOptions.filter((item) => item.kind === "external").map((item) => (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs(DFL.ButtonItem, { layout: "below", onClick: () => void onUseStorage(item, "download_dir"), disabled: saving, children: ["\u4E0B\u8F7D\u5230 ", item.label, "\uFF08\u5269\u4F59 ", item.free_text, "\uFF09"] }) }, `download-${item.mount}`))), !storageOptions.some((item) => item.kind === "external") ? (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "11px", opacity: 0.75 }, children: "\u672A\u68C0\u6D4B\u5230\u53EF\u5199 SD \u5361/\u5916\u7F6E\u5B58\u50A8\uFF08\u8BF7\u5148\u5728 SteamOS/\u7CFB\u7EDF\u4E2D\u6302\u8F7D\uFF09" }) })) : null] }), _local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u5B89\u88C5\u76EE\u5F55", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: settings.install_dir || "未设置" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onPickInstallDir, disabled: saving, children: "\u9009\u62E9\u5B89\u88C5\u76EE\u5F55" }) }), storageOptions.filter((item) => item.kind === "external").map((item) => (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs(DFL.ButtonItem, { layout: "below", onClick: () => void onUseStorage(item, "install_dir"), disabled: saving, children: ["\u5B89\u88C5\u5230 ", item.label, "\uFF08\u5269\u4F59 ", item.free_text, "\uFF09"] }) }, `install-${item.mount}`)))] })] })),
        },
        {
            id: "install",
            title: "安装",
            content: (_local_SP_JSX.jsxs(_local_SP_JSX.Fragment, { children: [_local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u5B89\u88C5\u884C\u4E3A", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ToggleField, { label: "\u5B89\u88C5\u540E\u81EA\u52A8\u5220\u9664\u538B\u7F29\u5305", description: "\u4EC5\u5728\u81EA\u52A8\u5B89\u88C5\u6210\u529F\u540E\u751F\u6548", checked: Boolean(settings.auto_delete_package), onChange: (value) => savePatch({ auto_delete_package: value }), disabled: saving }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5, opacity: 0.86 }, children: "\u4E0B\u8F7D\u5B8C\u6210\u540E\u81EA\u52A8\u5B89\u88C5\u5DF2\u56FA\u5B9A\u5F00\u542F\u3002" }) })] }), _local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u626B\u63CF\u5DF2\u5B89\u88C5", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5, opacity: 0.86 }, children: "\u626B\u63CF\u8BBE\u7F6E\u91CC\u7684\u5B89\u88C5\u76EE\u5F55\u4E00\u5C42\uFF0C\u628A\u76EE\u5F55\u540D\u5339\u914D\u6807\u9898\u7684\u6E38\u620F\u8865\u56DE\u5217\u8868\uFF1BSteam \u91CC\u6CA1\u6709\u7684\u4F1A\u81EA\u52A8\u521B\u5EFA\u5FEB\u6377\u65B9\u5F0F\u3002" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onScanInstalledSettings, disabled: scanningInstalled || saving, children: scanningInstalled ? "扫描中..." : "扫描已安装游戏" }) })] })] })),
        },
        {
            id: "download",
            title: "下载",
            content: (_local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u4E0B\u8F7D\u53C2\u6570", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.SliderField, { label: "aria2 \u5206\u7247\u6570", description: "\u5EFA\u8BAE 8~32\uFF0C\u8303\u56F4 1~64", value: Math.max(1, Math.min(64, Number(splitDraft || 16))), min: 1, max: 64, step: 1, showValue: true, editableValue: true, onChange: (value) => setSplitDraft(Math.max(1, Math.min(64, Number(value || 1)))), disabled: saving }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.DropdownItem, { label: "\u5206\u9875\u6570\u91CF", description: "\u6E38\u620F\u5217\u8868\u6BCF\u9875\u663E\u793A\u6761\u6570", rgOptions: PAGE_SIZE_OPTIONS, selectedOption: Math.max(10, Math.min(200, Number(settings.page_size || 50))), disabled: saving, onChange: (option) => {
                                const nextValue = Math.max(10, Math.min(200, Number(option?.data || 50)));
                                if (nextValue === Number(settings.page_size || 50))
                                    return;
                                void savePatch({ page_size: nextValue }, `分页数量已更新：${nextValue} / 页`);
                            } }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onSaveSplit, disabled: saving, children: "\u4FDD\u5B58\u4E0B\u8F7D\u53C2\u6570" }) })] })),
        },
        {
            id: "account",
            title: "账号",
            content: (_local_SP_JSX.jsxs(_local_SP_JSX.Fragment, { children: [_local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u5929\u7FFC\u4E91\u8D26\u53F7", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: login.logged_in
                                        ? `当前已登录：${login.user_account || "未知账号"}`
                                        : "当前未登录" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onClearLogin, disabled: clearingLogin || saving || !login.logged_in, children: clearingLogin ? "注销中..." : "注销天翼云账号" }) })] }), _local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u767E\u5EA6\u7F51\u76D8\uFF08\u626B\u7801\u767B\u5F55\uFF09", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: baiduWebLogin.logged_in
                                        ? `已登录：${baiduWebLogin.user_account || "百度账号"}`
                                        : "未登录（扫码后使用 BDUSS/Cookie，无需开放平台 App Key）" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void onCheckBaiduHealth(), disabled: checkingBaiduHealth || !baiduWebLogin.logged_in, children: checkingBaiduHealth ? "检查中..." : "检查登录状态" }) }), baiduHealth ? (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "4px", width: "100%", fontSize: "11px", lineHeight: 1.5 }, children: [_local_SP_JSX.jsx("div", { style: { color: baiduHealth.ok ? "#9fe6a8" : "#ffb4a8", fontWeight: 600 }, children: baiduHealth.message || "检查完成" }), ...(Array.isArray(baiduHealth.checks) ? baiduHealth.checks.map((check, index) => (_local_SP_JSX.jsx("div", { style: { color: check.status === "fail" ? "#ffb4a8" : check.status === "warn" ? "#ffd479" : "#b9c9d8" }, children: `${check.label || check.id || "检查"}：${check.detail || ""}` }, `${check.id || "check"}-${index}`))) : [])] }) })) : null, baiduQr.stage === "failed" || baiduQr.stage === "expired" ? (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", color: "#ffb4a8", lineHeight: 1.5 }, children: baiduQr.message || "扫码失败，请重试" }) })) : null, baiduQr.stage === "waiting" || baiduQr.stage === "scanned" ? (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "8px", alignItems: "center" }, children: [baiduQr.qr_data_url ? (_local_SP_JSX.jsx("img", { src: baiduQr.qr_data_url, alt: "\u767E\u5EA6\u626B\u7801\u767B\u5F55", style: { width: "180px", height: "180px", background: "#fff", padding: "8px", borderRadius: "8px" } })) : (_local_SP_JSX.jsxs("div", { style: { fontSize: "12px" }, children: ["\u4E8C\u7EF4\u7801\u56FE\u7247\u52A0\u8F7D\u5931\u8D25\uFF0C\u8BF7\u6253\u5F00\uFF1A", _local_SP_JSX.jsx("div", { style: { wordBreak: "break-all" }, children: baiduQr.qrcode_url })] })), _local_SP_JSX.jsx("div", { style: { fontSize: "12px" }, children: baiduQr.message || "请用百度 App 扫码" }), _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onCancelBaiduQr, children: "\u53D6\u6D88\u626B\u7801" })] }) })) : (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onStartBaiduQr, disabled: baiduQrBusy, children: baiduQrBusy ? "获取中..." : "扫码登录百度网盘" }) })), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onClearBaiduWeb, disabled: baiduQrBusy || !baiduWebLogin.logged_in, children: "\u9000\u51FA\u767E\u5EA6\u7F51\u76D8" }) })] }), _local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u767E\u5EA6\u7F51\u76D8 OpenAPI\uFF08\u53EF\u9009\uFF0C\u9700\u5F00\u53D1\u8005\u8D44\u8D28\uFF09", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: baiduLogin.logged_in
                                        ? `已授权：${baiduLogin.user_account || "百度账号"}`
                                        : baiduLogin.configured
                                            ? "已配置应用，待授权"
                                            : "未配置（去百度网盘开放平台创建应用）" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.TextField, { label: "App Key", value: baiduAppKey, onChange: (event) => setBaiduAppKey(getTextFieldValue(event)) }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.TextField, { label: "Secret Key", value: baiduSecretKey, bIsPassword: true, onChange: (event) => setBaiduSecretKey(getTextFieldValue(event)) }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onSaveBaiduApp, disabled: baiduBusy, children: "\u4FDD\u5B58\u5E94\u7528" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onBaiduAuthorize, disabled: baiduBusy || !baiduLogin.configured, children: "\u83B7\u53D6\u6388\u6743\u94FE\u63A5" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.TextField, { label: "\u6388\u6743\u7801", description: "\u7C98\u8D34\u767E\u5EA6\u8FD4\u56DE\u7684\u6388\u6743\u7801", value: baiduAuthCode, onChange: (event) => setBaiduAuthCode(getTextFieldValue(event)) }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onExchangeBaiduCode, disabled: baiduBusy || !baiduAuthCode.trim(), children: "\u5B8C\u6210\u6388\u6743" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onClearBaiduLogin, disabled: baiduBusy || !baiduLogin.logged_in, children: "\u6E05\u9664\u767E\u5EA6\u6388\u6743" }) })] }), _local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u4E91\u5B58\u6863\u4E0A\u4F20", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ToggleField, { label: "\u6E38\u620F\u9000\u51FA\u540E\u81EA\u52A8\u4E0A\u4F20", description: "\u540E\u53F0\u68C0\u6D4B\u6E38\u620F\u8FDB\u7A0B\uFF0C\u9000\u51FA\u540E\u81EA\u52A8\u6253\u5305\u4E0A\u4F20\uFF1B\u9ED8\u8BA4\u5F00\u542F", checked: Boolean(settings.cloud_save_auto_upload), onChange: (value) => savePatch({ cloud_save_auto_upload: value }), disabled: saving }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ToggleField, { label: "\u5305\u542B\u6A21\u62DF\u5668\u5B58\u6863", description: "GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch \u7684\u5B58\u6863\u4E0E\u8BB0\u5FC6\u5361", checked: Boolean(settings.cloud_save_include_emulators), onChange: (value) => savePatch({ cloud_save_include_emulators: value }), disabled: saving }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onStartCloudSaveUpload, disabled: saving || clearingLogin || startingCloudSaveUpload || !login.logged_in || cloudSaveUploadState.running, children: startingCloudSaveUpload
                                        ? "启动中..."
                                        : cloudSaveUploadState.running
                                            ? "上传进行中..."
                                            : "上传云存档" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: cloudSaveSummaryText }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "11px", lineHeight: 1.5, opacity: 0.88 }, children: `${cloudSaveUploadState.message || "未开始"} | ${clampProgress(cloudSaveUploadState.progress).toFixed(1)}%` }) })] }), _local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u4E91\u5B58\u6863\u4E0B\u8F7D\u6062\u590D", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: refreshRestoreOptions, disabled: !login.logged_in || restoreBusy, children: loadingRestoreOptions ? "刷新中..." : "刷新云存档列表" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.DropdownItem, { label: "\u9009\u62E9\u6E38\u620F", description: "\u6309\u6E38\u620F\u5206\u7EC4\u663E\u793A\u4E91\u7AEF\u7248\u672C", rgOptions: restoreGameOptions, selectedOption: selectedRestoreGameKey, disabled: !login.logged_in || restoreBusy || restoreGameOptions.length <= 0, onChange: (option) => setSelectedRestoreGameKey(String(option?.data || "")) }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.DropdownItem, { label: "\u9009\u62E9\u7248\u672C\u65F6\u95F4", description: "\u6309\u65F6\u95F4\u5012\u5E8F", rgOptions: restoreVersionOptions, selectedOption: selectedRestoreVersion, disabled: !login.logged_in || restoreBusy || !selectedRestoreGame || restoreVersionOptions.length <= 0, onChange: (option) => setSelectedRestoreVersion(String(option?.data || "")) }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onLoadRestoreEntries, disabled: !login.logged_in || restoreBusy || !selectedRestoreGame || !selectedRestoreVersion, children: loadingRestoreEntries ? "读取中..." : "读取可选存档项" }) }), restoreEntries.length > 0 &&
                                restoreEntries.map((entry) => {
                                    const entryId = String(entry.entry_id || "");
                                    const checked = selectedRestoreEntryIds.includes(entryId);
                                    return (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ToggleField, { label: `${entry.entry_name || entryId}${entry.file_count ? `（${entry.file_count} 文件）` : ""}`, checked: checked, onChange: (value) => toggleRestoreEntry(entryId, value), disabled: restoreBusy }) }, `restore_entry_${entryId}`));
                                }), restoreEntries.length > 0 && (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs("div", { style: { display: "flex", gap: "8px", width: "100%" }, children: [_local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => {
                                                setSelectedRestoreEntryIds(restoreEntries.map((item) => String(item.entry_id || "")).filter(Boolean));
                                            }, disabled: restoreBusy, children: "\u5168\u9009" }), _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => setSelectedRestoreEntryIds([]), disabled: restoreBusy, children: "\u6E05\u7A7A" })] }) })), targetCandidates.length > 1 && (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.DropdownItem, { label: "\u6062\u590D\u76EE\u6807\u76EE\u5F55", description: "\u68C0\u6D4B\u5230\u591A\u4E2A\u5019\u9009\u76EE\u5F55\uFF0C\u8BF7\u660E\u786E\u9009\u62E9", rgOptions: targetCandidates.map((path) => ({ data: path, label: path })), selectedOption: selectedRestoreTargetDir, disabled: restoreBusy, onChange: (option) => setSelectedRestoreTargetDir(String(option?.data || "")) }) })), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onStartCloudSaveRestore, disabled: !login.logged_in || restoreBusy || !selectedRestoreGame || !selectedRestoreVersion || !selectedRestoreEntryIds.length, children: planningRestore ? "规划中..." : applyingRestore ? "恢复中..." : "下载并恢复云存档" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.5 }, children: cloudSaveRestoreSummaryText }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "11px", lineHeight: 1.5, opacity: 0.88 }, children: `${cloudSaveRestoreState.message || "未开始"} | ${clampProgress(cloudSaveRestoreState.progress).toFixed(1)}%` }) })] })] })),
        },
        {
            id: "diagnostics",
            title: "诊断",
            content: (_local_SP_JSX.jsxs(_local_SP_JSX.Fragment, { children: [_local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u63D2\u4EF6\u66F4\u65B0", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.6, opacity: 0.88 }, children: updateInfo
                                        ? `当前 ${updateInfo.current || "?"} · 最新 ${updateInfo.latest || "?"}`
                                        : "检查 GitHub Release，下载并校验更新包；不会自动覆盖运行中的插件。" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs("div", { style: { display: "flex", gap: "8px", width: "100%" }, children: [_local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void onCheckUpdate(), disabled: checkingUpdate || downloadingUpdate, children: checkingUpdate ? "检查中..." : "检查更新" }), updateInfo?.has_update ? (_local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void onDownloadUpdate(), disabled: downloadingUpdate, children: downloadingUpdate ? "下载中..." : "下载更新包" })) : null] }) }), updateMessage ? (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "11px", lineHeight: 1.5, color: updateInfo?.has_update ? "#ffd479" : "#b9c0cc", wordBreak: "break-word" }, children: updateMessage }) })) : null] }), _local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u63D2\u4EF6\u81EA\u68C0", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.6, opacity: 0.88 }, children: "\u68C0\u67E5\u63D2\u4EF6\u7248\u672C\u3001\u72B6\u6001/\u4E0B\u8F7D/\u5B89\u88C5\u76EE\u5F55\u3001aria2/7zz/node\u3001Steam \u5FEB\u6377\u65B9\u5F0F\u3001SD \u5361\u3001\u7F51\u7EDC\u4E0E\u767E\u5EA6\u626B\u7801\u63A5\u53E3\u3002" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void onRunDiagnostics(), disabled: diagnosticsBusy, children: diagnosticsBusy ? "自检中..." : "运行自检" }) }), diagnosticsError ? (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.6, color: "#ffb4a8", wordBreak: "break-word" }, children: `自检失败：${diagnosticsError}` }) })) : null, diagnosticsReport ? (_local_SP_JSX.jsxs(_local_SP_JSX.Fragment, { children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.6 }, children: `v${diagnosticsReport.version || "?"} · ${diagnosticsReport.arch || "-"} · OK ${diagnosticsReport.summary?.ok || 0} / 警告 ${diagnosticsReport.summary?.warn || 0} / 失败 ${diagnosticsReport.summary?.fail || 0} / 跳过 ${diagnosticsReport.summary?.skip || 0}` }) }), (diagnosticsReport.checks || []).map((check, checkIndex) => {
                                        const status = String(check.status || "skip").toLowerCase();
                                        const color = status === "ok"
                                            ? "#9fe6a8"
                                            : status === "warn"
                                                ? "#ffd479"
                                                : status === "fail"
                                                    ? "#ff9a8a"
                                                    : "#b9c0cc";
                                        return (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "3px", width: "100%" }, children: [_local_SP_JSX.jsxs("div", { style: { display: "flex", justifyContent: "space-between", gap: "8px" }, children: [_local_SP_JSX.jsx("span", { style: { fontWeight: 600 }, children: check.label || check.id || "-" }), _local_SP_JSX.jsx("span", { style: { color, fontSize: "12px" }, children: status.toUpperCase() })] }), _local_SP_JSX.jsx("div", { style: { fontSize: "12px", opacity: 0.86, wordBreak: "break-word" }, children: check.detail }), check.fix && status !== "ok" ? (_local_SP_JSX.jsx("div", { style: { fontSize: "11px", opacity: 0.7 }, children: `建议：${check.fix}` })) : null] }) }, check.id || `diagnostic-${checkIndex}`));
                                    })] })) : null] }), _local_SP_JSX.jsxs(DFL.PanelSection, { title: "\u8BCA\u65AD\u5305", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.6, opacity: 0.88 }, children: "\u5BFC\u51FA diagnostics.json\u3001self-check.json\u3001\u6700\u65B0 300 \u884C\u65E5\u5FD7\uFF1Bcookie/token \u5DF2\u8131\u654F\uFF0C\u5199\u5230\u4E0B\u8F7D\u76EE\u5F55\u3002" }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void onExportDiagnostics(), disabled: diagnosticsExportBusy, children: diagnosticsExportBusy ? "打包中..." : "导出诊断包" }) }), diagnosticsExportMessage ? (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "11px", opacity: 0.82, wordBreak: "break-all" }, children: diagnosticsExportMessage }) })) : null] })] })),
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
        return (_local_SP_JSX.jsx(DFL.PanelSection, { title: "freedeckCY \u8BBE\u7F6E", children: _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: "\u52A0\u8F7D\u4E2D..." }) }));
    }
    return (_local_SP_JSX.jsxs("div", { ref: settingsContainerRef, className: "freedeckcy-settings-root", style: {
            paddingTop: 48,
            paddingBottom: 24,
            minHeight: "100%",
            boxSizing: "border-box",
            overflowX: "hidden",
        }, children: [_local_SP_JSX.jsx("style", { children: tabStabilityCss }), _local_SP_JSX.jsx(DFL.Tabs, { tabs: tabs, activeTab: activeTab, onShowTab: onShowSettingsTab, autoFocusContents: false })] }));
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
function Content() {
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
            modal = DFL.showModal(_local_SP_JSX.jsx(LibraryPage, { onClose: () => {
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
        DFL.showModal(_local_SP_JSX.jsx(DFL.ConfirmModal, { strTitle: "\u786E\u8BA4\u5378\u8F7D", strDescription: lines.join("\n"), strOKButtonText: compatBytes > 0 ? "仅删游戏文件" : "确认卸载", strMiddleButtonText: compatBytes > 0 ? `连 Proton 前缀一起删（${formatBytesText(compatBytes)}）` : undefined, onMiddleButton: compatBytes > 0
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
                        : removeTianyiTask;
            // 重试要重新取直链/重新进入安装，给更长的超时；暂停/继续/移除通常很快。
            const actionTimeoutMs = action === "retry" ? 60000 : 20000;
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
        DFL.showModal(_local_SP_JSX.jsx(DFL.ConfirmModal, { strTitle: "\u786E\u8BA4\u79FB\u9664\u4EFB\u52A1", strDescription: `确定移除「${title}」吗？\n\n只移除任务记录，不删除已下载文件。`, strOKButtonText: "\u786E\u8BA4\u79FB\u9664", strCancelButtonText: "\u53D6\u6D88", onOK: () => {
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
    if (loading) {
        return (_local_SP_JSX.jsx(DFL.PanelSection, { children: _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: "\u52A0\u8F7D\u4E2D..." }) }));
    }
    return (_local_SP_JSX.jsxs(_local_SP_JSX.Fragment, { children: [_local_SP_JSX.jsxs(DFL.PanelSection, { children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: {
                                width: "100%",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                            }, title: loginStatusText, children: loginStatusText }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "10px", opacity: 0.55 }, children: `QAM 原生 UI v${PLUGIN_UI_BUILD}` }) }), _local_SP_JSX.jsxs(DFL.PanelSectionRow, { children: [!state.login.logged_in && (_local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onLogin, disabled: openingLogin, children: openingLogin ? "登录入口准备中..." : "登录" })), _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onOpenLibrary, disabled: openingLogin, children: "\u6E38\u620F\u5E93" }), _local_SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: onOpenSettings, children: "\u8BBE\u7F6E" })] })] }), state.steam_restart?.pending && (_local_SP_JSX.jsxs(DFL.PanelSection, { title: "Steam \u5FEB\u6377\u65B9\u5F0F\u5DF2\u5199\u5165", children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.45 }, children: `「${state.steam_restart.title || "游戏"}」已安装并写入 Steam 快捷方式。重启 Steam 后才会显示在库中。` }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs(DFL.Focusable, { style: { display: "flex", gap: "8px", width: "100%" }, children: [_local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => void trySteamRefresh(), disabled: restartingSteam || refreshingSteamLibrary, style: { flex: 1 }, children: refreshingSteamLibrary ? "刷新中..." : "免重启刷新" }), _local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => void restartSteamNow(), disabled: restartingSteam || refreshingSteamLibrary, style: { flex: 1 }, children: restartingSteam ? "正在重启..." : "现在重启" }), _local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => void dismissSteamRestart(), disabled: restartingSteam, style: { flex: 1 }, children: "\u7A0D\u540E" })] }) })] })), visibleTasks.length > 0 && (_local_SP_JSX.jsx(DFL.PanelSection, { title: `下载列表（${visibleTasks.length}）`, children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs("div", { style: { display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px", width: "100%" }, children: [_local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onPauseAllTasks(), disabled: Boolean(batchBusy), style: { width: "auto", flex: "0 0 auto" }, children: batchBusy === "pause" ? "暂停中..." : "全部暂停" }), _local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onResumeAllTasks(), disabled: Boolean(batchBusy), style: { width: "auto", flex: "0 0 auto" }, children: batchBusy === "resume" ? "继续中..." : "全部继续" }), _local_SP_JSX.jsx("div", { style: { flex: "1 1 120px", minWidth: "100px" }, children: _local_SP_JSX.jsx(DFL.TextField, { label: `限速 KB/s（当前 ${Math.round(Number(state.settings.download_speed_limit || 0) / 1024)}，0 不限）`, value: speedDraft, onChange: (event) => setSpeedDraft(getTextFieldValue(event)) }) }), _local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onApplySpeedLimit(), disabled: Boolean(batchBusy), style: { width: "auto", flex: "0 0 auto" }, children: batchBusy === "speed" ? "应用中..." : "应用限速" })] }) }), ...visibleTasks.slice(0, 20).map((task) => {
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
                        return (_local_SP_JSX.jsxs(DFL.PanelSectionRow, { children: [TaskProgressRow(task), _local_SP_JSX.jsxs("div", { style: { display: "flex", gap: "8px", width: "100%", marginTop: "4px" }, children: [canPause && (_local_SP_JSX.jsx(DFL.Focusable, { style: { flex: 1 }, children: _local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => void performTaskAction("pause", task), onOKButton: () => void performTaskAction("pause", task), disabled: Boolean(taskActionKey), style: buttonStyle, children: busy ? "处理中..." : "暂停" }) })), canResume && (_local_SP_JSX.jsx(DFL.Focusable, { style: { flex: 1 }, children: _local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => void performTaskAction("resume", task), onOKButton: () => void performTaskAction("resume", task), disabled: Boolean(taskActionKey), style: buttonStyle, children: busy ? "处理中..." : "继续" }) })), canRetry && (_local_SP_JSX.jsx(DFL.Focusable, { style: { flex: 1 }, children: _local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => void performTaskAction("retry", task), onOKButton: () => void performTaskAction("retry", task), disabled: Boolean(taskActionKey), style: {
                                                    minWidth: "76px",
                                                    borderRadius: "10px",
                                                    border: "1px solid rgba(120, 200, 255, 0.45)",
                                                    background: "rgba(120, 200, 255, 0.16)",
                                                    color: "#dff4ff",
                                                }, children: busy ? "重试中..." : "重试" }) })), _local_SP_JSX.jsx(DFL.Focusable, { style: { flex: 1 }, children: _local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => onRemoveTask(task), onOKButton: () => onRemoveTask(task), disabled: Boolean(taskActionKey), style: {
                                                    minWidth: "76px",
                                                    borderRadius: "10px",
                                                    border: "1px solid rgba(255, 106, 106, 0.4)",
                                                    background: "rgba(255, 106, 106, 0.16)",
                                                    color: "#ffe8e8",
                                                }, children: "\u79FB\u9664" }) })] })] }, task.task_id));
                    })] })), sortedInstalledGames.length > 0 && (_local_SP_JSX.jsx(DFL.PanelSection, { title: `游戏预览（已安装 ${state.installed.total || sortedInstalledGames.length}）`, children: sortedInstalledGames.map((item, index) => {
                    const uninstallKey = `${item.game_id || ""}::${item.install_path || ""}`;
                    const uninstalling = uninstallingKey === uninstallKey;
                    return (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px", width: "100%" }, children: [_local_SP_JSX.jsxs("div", { style: { minWidth: 0, flex: 1 }, children: [_local_SP_JSX.jsx("div", { style: {
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap",
                                            }, title: item.title || "未命名游戏", children: item.title || "未命名游戏" }), _local_SP_JSX.jsx("div", { style: { fontSize: "12px" }, children: `${item.size_text || "-"}${item.status ? ` | ${item.status}` : ""}` }), _local_SP_JSX.jsx("div", { style: { fontSize: "12px" }, children: `游玩时长：${formatPlaytimeText(item.playtime_seconds || 0, item.playtime_text)}${item.playtime_active ? "（进行中）" : ""}` }), _local_SP_JSX.jsx("div", { style: {
                                                fontSize: "12px",
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap",
                                            }, title: item.install_path || "-", children: item.install_path || "-" })] }), _local_SP_JSX.jsx(DFL.Focusable, { style: { flex: "0 0 auto" }, children: _local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => onUninstallInstalledGame(item), onOKButton: () => onUninstallInstalledGame(item), disabled: Boolean(uninstallingKey) || uninstalling, style: {
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
    return (_local_SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "14px", width: "min(560px, 90vw)", maxHeight: "78vh", overflowY: "auto" }, children: [_local_SP_JSX.jsxs("div", { style: { display: "grid", gridTemplateColumns: "156px minmax(0, 1fr)", gap: "16px", alignItems: "start" }, children: [_local_SP_JSX.jsxs("div", { style: {
                            position: "relative",
                            width: "156px",
                            height: "234px",
                            overflow: "hidden",
                            background: libraryCoverGradient(props.item.platform),
                            border: "1px solid rgba(255,255,255,0.10)",
                            boxShadow: "0 14px 34px rgba(0,0,0,0.34)",
                        }, children: [coverUrl ? (_local_SP_JSX.jsx("img", { src: String(coverUrl).replace(/_2x(\.(?:jpg|jpeg|png|webp))/i, "$1"), alt: title, referrerPolicy: "no-referrer", decoding: "async", loading: "lazy", onError: () => setImageFailed(true), style: { width: "100%", height: "100%", objectFit: "cover", display: "block" } })) : (_local_SP_JSX.jsx("div", { style: { display: "flex", alignItems: "center", justifyContent: "center", height: "100%", padding: "16px", textAlign: "center", fontSize: "15px", fontWeight: 700, color: "#eef5fb" }, children: primaryTitle })), props.installed ? (_local_SP_JSX.jsx("div", { style: { position: "absolute", top: "8px", right: "8px", padding: "2px 7px", fontSize: "10px", fontWeight: 700, color: "#dff7e4", background: "rgba(20,105,56,0.92)", border: "1px solid rgba(160,255,190,0.45)" }, children: "\u5DF2\u5B89\u88C5" })) : null] }), _local_SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "12px", minWidth: 0 }, children: [_local_SP_JSX.jsx("div", { style: { fontSize: "24px", lineHeight: 1.2, fontWeight: 800, color: "#f2f6fb", wordBreak: "break-word" }, children: primaryTitle }), secondaryTitle ? (_local_SP_JSX.jsx("div", { style: { fontSize: "13px", lineHeight: 1.4, color: "rgba(236,241,246,0.68)", wordBreak: "break-word" }, children: secondaryTitle })) : null, _local_SP_JSX.jsxs("div", { style: { display: "flex", flexWrap: "wrap", gap: "6px" }, children: [_local_SP_JSX.jsx("span", { style: { padding: "3px 8px", fontSize: "11px", color: "#eaf2fa", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.10)" }, children: String(props.item.platform || "pc").toUpperCase() }), _local_SP_JSX.jsx("span", { style: { padding: "3px 8px", fontSize: "11px", color: "#eaf2fa", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.10)" }, children: props.item.size_text || "大小未知" }), categoryTags.map((tag) => (_local_SP_JSX.jsx("span", { style: { padding: "3px 8px", fontSize: "11px", color: "#dcefff", background: "rgba(83,181,255,0.12)", border: "1px solid rgba(83,181,255,0.22)" }, children: tag }, tag)))] }), _local_SP_JSX.jsx("div", { style: { fontSize: "12px", lineHeight: 1.55, color: "rgba(220,230,240,0.72)" }, children: "\u4E0B\u8F7D\u5B8C\u6210\u540E\u4F1A\u81EA\u52A8\u89E3\u538B\u5E76\u5199\u5165 Steam \u5FEB\u6377\u65B9\u5F0F\uFF1B\u9996\u6B21\u5B89\u88C5\u540E\u6309\u63D0\u793A\u91CD\u542F Steam \u5373\u53EF\u5728\u5E93\u4E2D\u770B\u5230\u3002" })] })] }), _local_SP_JSX.jsxs(DFL.Focusable, { style: { display: "flex", gap: "10px", width: "100%" }, children: [_local_SP_JSX.jsx(DFL.DialogButton, { onClick: props.onInstall, disabled: props.busy || props.installed, style: { flex: 1, minHeight: "42px", background: "rgba(67,181,129,0.24)", border: "1px solid rgba(120,255,180,0.42)", color: "#eafff3" }, children: props.installed ? "已安装" : props.busy ? "处理中..." : "安装" }), _local_SP_JSX.jsx(DFL.DialogButton, { onClick: props.onClose, style: { flex: 1, minHeight: "42px" }, children: "\u9000\u51FA" })] })] }));
}
const LIBRARY_CARD_WIDTH = 133;
const LIBRARY_CARD_HEIGHT = 200;
function libraryCoverGradient(platform) {
    const key = String(platform || "pc").toLowerCase();
    const colors = {
        pc: ["#1d3b53", "#0d1620"],
        fc: ["#5a2d1f", "#1a0f0a"],
        md: ["#233f2b", "#0b160f"],
        gba: ["#3d2b52", "#140d1d"],
        nds: ["#3a3f46", "#111418"],
        psp: ["#243b5a", "#0c1420"],
        ps1: ["#4b3a23", "#17110a"],
        ps2: ["#2f3157", "#0e0f1d"],
        ps3: ["#3c3c3c", "#111111"],
        switch: ["#5a1f24", "#1b090b"],
        "3ds": ["#4a2530", "#170b0f"],
    };
    const pair = colors[key] || colors.pc;
    return `linear-gradient(145deg, ${pair[0]}, ${pair[1]})`;
}
function LibraryCoverCard(props) {
    const [imageFailed, setImageFailed] = SP_REACT.useState(false);
    const [proxyFailed, setProxyFailed] = SP_REACT.useState(false);
    const rawCoverUrl = imageFailed ? "" : String(props.coverUrl || "").trim();
    const coverUrl = rawCoverUrl && props.coverProxyBase && !proxyFailed ? `${props.coverProxyBase}?url=${encodeURIComponent(rawCoverUrl)}` : rawCoverUrl;
    const title = props.title || "未命名游戏";
    const cardRef = SP_REACT.useRef(null);
    SP_REACT.useEffect(() => {
        const node = cardRef.current;
        if (!node)
            return;
        if (!document.getElementById("freedeckcy-cover-focus-style")) {
            const style = document.createElement("style");
            style.id = "freedeckcy-cover-focus-style";
            style.textContent = ".freedeckcy-cover-card:focus,.freedeckcy-cover-card:focus-within{outline:3px solid #65b8ff!important;outline-offset:3px;filter:brightness(1.08)}";
            document.head.appendChild(style);
        }
        const showHint = () => {
            let hint = document.getElementById("freedeckcy-focus-hint");
            if (!hint) {
                hint = document.createElement("div");
                hint.id = "freedeckcy-focus-hint";
                hint.style.cssText = "position:fixed;left:12px;right:12px;bottom:80px;z-index:9999;display:none;align-items:center;gap:12px;padding:9px 12px;background:rgba(18,24,32,.96);border:1px solid rgba(101,184,255,.35);box-shadow:0 6px 20px rgba(0,0,0,.4);pointer-events:none;font-family:inherit";
                document.body.appendChild(hint);
            }
            hint.replaceChildren();
            const left = document.createElement("div");
            left.style.cssText = "min-width:0;flex:1";
            const name = document.createElement("div");
            name.textContent = title;
            name.style.cssText = "font-size:13px;font-weight:700;color:#f2f6fb;overflow:hidden;text-overflow:ellipsis;white-space:nowrap";
            const meta = document.createElement("div");
            meta.textContent = `${String(props.platform || "pc").toUpperCase()} · ${props.meta || "大小未知"}`;
            meta.style.cssText = "font-size:11px;color:#9eacbb;overflow:hidden;text-overflow:ellipsis;white-space:nowrap";
            left.append(name, meta);
            const hintText = document.createElement("div");
            hintText.textContent = "A 选择 / B 返回";
            hintText.style.cssText = "flex:0 0 auto;font-size:11px;color:#b9c9d8";
            hint.append(left, hintText);
            hint.style.display = "flex";
        };
        const hideHint = () => {
            const hint = document.getElementById("freedeckcy-focus-hint");
            if (hint)
                hint.style.display = "none";
        };
        node.addEventListener("focus", showHint, true);
        node.addEventListener("mouseenter", showHint);
        node.addEventListener("blur", hideHint, true);
        node.addEventListener("mouseleave", hideHint);
        return () => {
            node.removeEventListener("focus", showHint, true);
            node.removeEventListener("mouseenter", showHint);
            node.removeEventListener("blur", hideHint, true);
            node.removeEventListener("mouseleave", hideHint);
            hideHint();
        };
    }, [title, props.platform, props.meta]);
    return (_local_SP_JSX.jsxs("div", { style: { width: `${LIBRARY_CARD_WIDTH}px`, display: "flex", flexDirection: "column", gap: "6px" }, children: [_local_SP_JSX.jsxs(DFL.DialogButton, { ref: cardRef, className: "freedeckcy-cover-card", onClick: props.onPress, disabled: Boolean(props.disabled), style: {
                    position: "relative",
                    width: `${LIBRARY_CARD_WIDTH}px`,
                    height: `${LIBRARY_CARD_HEIGHT}px`,
                    padding: 0,
                    border: "1px solid rgba(255,255,255,0.10)",
                    borderRadius: "0",
                    overflow: "hidden",
                    display: "block",
                    background: libraryCoverGradient(props.platform),
                    boxShadow: "0 12px 28px rgba(0,0,0,0.36)",
                }, children: [coverUrl ? (_local_SP_JSX.jsx("img", { src: String(coverUrl).replace(/_2x(\.(?:jpg|jpeg|png|webp))/i, "$1"), alt: title, referrerPolicy: "no-referrer", decoding: "async", loading: "lazy", onError: () => { if (rawCoverUrl && coverUrl !== rawCoverUrl)
                            setProxyFailed(true);
                        else
                            setImageFailed(true); }, style: { position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", display: "block" } })) : (_local_SP_JSX.jsx("div", { style: {
                            position: "absolute",
                            inset: 0,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            padding: "14px",
                            textAlign: "center",
                            fontSize: "14px",
                            lineHeight: 1.35,
                            fontWeight: 700,
                            color: "rgba(242,246,251,0.88)",
                            textShadow: "0 2px 10px rgba(0,0,0,0.45)",
                        }, children: title })), props.installed ? (_local_SP_JSX.jsx("div", { style: {
                            position: "absolute",
                            top: "7px",
                            right: "7px",
                            zIndex: 3,
                            padding: "2px 6px",
                            fontSize: "10px",
                            lineHeight: 1.2,
                            fontWeight: 700,
                            color: "#dff7e4",
                            background: "rgba(20,105,56,0.92)",
                            border: "1px solid rgba(160,255,190,0.45)",
                        }, children: "\u5DF2\u5B89\u88C5" })) : null, _local_SP_JSX.jsxs("div", { style: {
                            position: "absolute",
                            left: 0,
                            right: 0,
                            bottom: 0,
                            zIndex: 2,
                            padding: "28px 9px 9px",
                            background: "linear-gradient(to top, rgba(8,10,14,0.96), rgba(8,10,14,0.72) 55%, rgba(8,10,14,0))",
                        }, children: [_local_SP_JSX.jsx("div", { style: {
                                    fontSize: "12px",
                                    lineHeight: 1.3,
                                    fontWeight: 700,
                                    color: "#f2f6fb",
                                    display: "-webkit-box",
                                    WebkitLineClamp: 2,
                                    WebkitBoxOrient: "vertical",
                                    overflow: "hidden",
                                    wordBreak: "break-word",
                                }, children: title }), _local_SP_JSX.jsxs("div", { style: { marginTop: "3px", fontSize: "10px", lineHeight: 1.25, color: "rgba(220,230,240,0.78)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }, children: [String(props.platform || "pc").toUpperCase(), props.meta ? ` · ${props.meta}` : ""] })] }), props.busyLabel ? (_local_SP_JSX.jsx("div", { style: {
                            position: "absolute",
                            inset: 0,
                            zIndex: 4,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            background: "rgba(7,10,14,0.70)",
                            fontSize: "12px",
                            fontWeight: 700,
                            color: "#fff",
                        }, children: props.busyLabel })) : null] }), props.actions ? (_local_SP_JSX.jsx(DFL.Focusable, { style: { display: "flex", gap: "4px", width: `${LIBRARY_CARD_WIDTH}px` }, children: props.actions })) : null] }));
}
function LibraryPage({ onClose }) {
    const [tab, setTab] = SP_REACT.useState("catalog");
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
    const [catalogUpdate, setCatalogUpdate] = SP_REACT.useState({ added_count: 0, items: [], updated_at: 0 });
    const [coverProxyBase, setCoverProxyBase] = SP_REACT.useState("");
    const catalogRequestRef = SP_REACT.useRef(0);
    const installedRequestRef = SP_REACT.useRef(0);
    const busyRef = SP_REACT.useRef("");
    const pageSize = 30;
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
            const emulatorText = plan.emulator_info?.name ? `模拟器：${plan.emulator_info.name}` : "PC / Proton";
            const setupText = plan.emulator_info?.setup_hint ? `\n提示：${plan.emulator_info.setup_hint}` : "";
            DFL.showModal(_local_SP_JSX.jsx(DFL.ConfirmModal, { strTitle: `安装 ${plan.game_title || item.title}`, strDescription: `下载：${plan.required_download_human || "未知"} → ${plan.download_dir || "-"}\n` +
                    `安装：${plan.required_install_human || "未知"} → ${plan.install_dir || "-"}\n` +
                    `${emulatorText}${setupText}`, strOKButtonText: "\u5F00\u59CB\u4E0B\u8F7D", strCancelButtonText: "\u53D6\u6D88", onOK: () => {
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
    const onUninstall = SP_REACT.useCallback((item) => {
        if (busyRef.current)
            return;
        DFL.showModal(_local_SP_JSX.jsx(DFL.ConfirmModal, { strTitle: `卸载 ${item.title}`, strDescription: "\u5C06\u5220\u9664\u5B89\u88C5\u76EE\u5F55\u5E76\u79FB\u9664\u8BB0\u5F55\uFF0C\u662F\u5426\u7EE7\u7EED\uFF1F", strOKButtonText: "\u5378\u8F7D", strCancelButtonText: "\u53D6\u6D88", onOK: () => {
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
            modal = DFL.showModal(_local_SP_JSX.jsx(GameDetailModal, { item: item, installed: Boolean(item.game_id && installedGameIds.has(item.game_id)), busy: Boolean(busyKey), onInstall: () => {
                    try {
                        modal?.Close();
                    }
                    catch {
                        // 忽略关闭失败。
                    }
                    void onPrepareInstall(item);
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
    return (_local_SP_JSX.jsxs(DFL.Focusable, { noFocusRing: true, onCancel: handleClose, style: {
            height: "100%",
            overflowY: "auto",
            boxSizing: "border-box",
            // SteamOS Game Mode 的库页无论是 showModal 还是路由都是全屏，
            // 都会被 Steam 顶栏/底栏覆盖：顶部固定让出状态栏，底部留出 Steam 菜单。
            padding: "72px 8px 160px",
            background: "#0e1116",
            color: "#f2f6fb",
        }, children: [_local_SP_JSX.jsx("div", { "aria-hidden": "true", style: {
                    position: "fixed",
                    top: 0,
                    left: 0,
                    right: 0,
                    height: "60px",
                    background: "#0e1116",
                    zIndex: 15,
                    pointerEvents: "none",
                } }), _local_SP_JSX.jsx("div", { "aria-hidden": "true", style: {
                    position: "fixed",
                    bottom: 0,
                    left: 0,
                    right: 0,
                    height: "72px",
                    background: "#0e1116",
                    zIndex: 15,
                    pointerEvents: "none",
                } }), _local_SP_JSX.jsxs("div", { style: {
                    position: "relative",
                    zIndex: 20,
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "8px",
                    padding: "8px 0",
                    boxSizing: "border-box",
                    background: "#0e1116",
                }, children: [_local_SP_JSX.jsxs(DFL.Focusable, { onCancel: handleClose, style: { display: "flex", gap: "6px" }, children: [_local_SP_JSX.jsx(DFL.DialogButton, { onClick: handleClose, style: { width: "auto", flex: "0 0 auto", padding: "8px 16px", minHeight: "38px", minWidth: "78px" }, children: "\u8FD4\u56DE" }), _local_SP_JSX.jsx(DFL.DialogButton, { onClick: handleSteamLibrary, style: { width: "auto", flex: "0 0 auto", padding: "8px 16px", minHeight: "38px", minWidth: "92px" }, children: "Steam \u5E93" })] }), _local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => void refreshCatalog(), disabled: loadingCatalog || loadingInstalled, style: { width: "auto", flex: "0 0 auto", padding: "8px 16px", minHeight: "38px", minWidth: "76px" }, children: loadingCatalog || loadingInstalled ? "刷新中..." : "刷新" })] }), _local_SP_JSX.jsx(DFL.PanelSection, { children: _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", width: "100%" }, children: [_local_SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column" }, children: [_local_SP_JSX.jsx("div", { style: { fontSize: "18px", fontWeight: 700 }, children: "freedeckCY \u6E38\u620F\u5E93" }), _local_SP_JSX.jsx("div", { style: { fontSize: "11px", opacity: 0.65 }, children: `原生 UI · v${PLUGIN_UI_BUILD}` })] }), _local_SP_JSX.jsxs(DFL.Focusable, { style: { display: "flex", gap: "6px" }, children: [_local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => setTab("catalog"), style: { padding: "6px 12px", background: tab === "catalog" ? "rgba(255,255,255,0.22)" : undefined }, children: "\u6E38\u620F\u5E93" }), _local_SP_JSX.jsxs(DFL.DialogButton, { onClick: () => setTab("installed"), style: { padding: "6px 12px", background: tab === "installed" ? "rgba(255,255,255,0.22)" : undefined }, children: ["\u5DF2\u5B89\u88C5", installed.total ? `(${installed.total})` : ""] })] })] }) }) }), tab === "catalog" ? (_local_SP_JSX.jsxs(_local_SP_JSX.Fragment, { children: [catalogUpdate.items.length ? (_local_SP_JSX.jsxs(DFL.PanelSection, { title: `\u6700\u8FD1\u66F4\u65B0\uFF08${catalogUpdate.added_count || catalogUpdate.items.length}\uFF09`, children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs("div", { style: { fontSize: "11px", opacity: 0.65, marginBottom: "4px" }, children: ["\u76EE\u5F55\u5DF2\u66F4\u65B0\uFF0C\u65B0\u589E ", catalogUpdate.added_count || catalogUpdate.items.length, " \u4E2A\u6E38\u620F"] }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.Focusable, { style: {
                                        display: "flex",
                                        gap: "20px",
                                        width: "100%",
                                        overflowX: "auto",
                                        padding: "4px 0 12px",
                                        alignItems: "flex-start",
                                    }, children: catalogUpdate.items.map((item) => (_local_SP_JSX.jsx(LibraryCoverCard, { title: item.title || "\u672A\u547D\u540D\u6E38\u620F", platform: item.platform, meta: item.size_text || "-", coverUrl: item.cover_portrait_url || item.cover_url, installed: Boolean(item.game_id && installedGameIds.has(item.game_id)), busyLabel: busyKey === item.game_id ? "\u5904\u7406\u4E2D..." : "", disabled: Boolean(busyKey), coverProxyBase: coverProxyBase, onPress: () => onOpenDetail(item) }, `recent:${item.game_id}`))) }) })] })) : null, _local_SP_JSX.jsxs(DFL.PanelSection, { children: [_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", gap: "8px", width: "100%" }, children: [_local_SP_JSX.jsx("div", { style: { flex: 1, minWidth: 0 }, children: _local_SP_JSX.jsx(DFL.TextField, { label: "\u641C\u7D22\u6E38\u620F", value: query, onChange: (event) => setQuery(getTextFieldValue(event)), onKeyDown: (event) => {
                                                    if (event.key === "Enter")
                                                        submitSearch();
                                                } }) }), _local_SP_JSX.jsx(DFL.DialogButton, { onClick: submitSearch, style: { width: "auto", flex: "0 0 auto", padding: "7px 14px" }, children: "\u641C\u7D22" }), _local_SP_JSX.jsx(DFL.DialogButton, { onClick: resetSearch, style: { width: "auto", flex: "0 0 auto", padding: "7px 14px" }, children: "\u91CD\u7F6E" })] }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.Focusable, { style: { display: "flex", gap: "7px", width: "100%", overflowX: "auto", padding: "2px 0 4px" }, children: platformChips.map((item) => (_local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => { setPlatform(item.value); setPage(1); }, style: {
                                            width: "auto",
                                            flex: "0 0 auto",
                                            padding: "6px 13px",
                                            minHeight: "32px",
                                            background: platform === item.value ? "rgba(106,181,255,0.28)" : undefined,
                                            border: platform === item.value ? "1px solid rgba(140,210,255,0.55)" : undefined,
                                        }, children: item.label }, `platform:${item.value || "all"}`))) }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs(DFL.Focusable, { style: { display: "flex", gap: "7px", width: "100%", overflowX: "auto", padding: "2px 0 4px" }, children: [_local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => { setCategory(""); setPage(1); }, style: { width: "auto", flex: "0 0 auto", padding: "6px 12px", minHeight: "32px", background: !category ? "rgba(255,255,255,0.18)" : undefined }, children: "\u5168\u90E8\u5206\u7C7B" }), categoryChips.map((item) => (_local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => { setCategory(item.value); setPage(1); }, style: {
                                                width: "auto",
                                                flex: "0 0 auto",
                                                padding: "6px 12px",
                                                minHeight: "32px",
                                                background: category === item.value ? "rgba(255,255,255,0.18)" : undefined,
                                            }, children: item.label }, `category:${item.value}`)))] }) }), _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.Focusable, { style: { display: "flex", gap: "7px", width: "100%", overflowX: "auto", padding: "2px 0 4px" }, children: sortOptions.map((item) => (_local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => { setSort(item.data); setPage(1); }, style: {
                                            width: "auto",
                                            flex: "0 0 auto",
                                            padding: "5px 11px",
                                            minHeight: "30px",
                                            fontSize: "11px",
                                            background: sort === item.data ? "rgba(255,255,255,0.16)" : undefined,
                                        }, children: item.label }, `sort:${item.data || "default"}`))) }) })] }), loadingCatalog && catalog.items.length === 0 ? (_local_SP_JSX.jsx(DFL.PanelSection, { children: _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px" }, children: "\u52A0\u8F7D\u4E2D..." }) }) })) : catalog.items.length === 0 ? (_local_SP_JSX.jsx(DFL.PanelSection, { children: _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px" }, children: "\u6CA1\u6709\u5339\u914D\u6E38\u620F" }) }) })) : showShelves ? (_local_SP_JSX.jsx(_local_SP_JSX.Fragment, { children: categorySections.map(([sectionTitle, items]) => (_local_SP_JSX.jsx(DFL.PanelSection, { title: `${sectionTitle}（${items.length}）`, children: _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.Focusable, { style: {
                                        display: "flex",
                                        gap: "20px",
                                        width: "100%",
                                        overflowX: "auto",
                                        padding: "4px 0 12px",
                                        alignItems: "flex-start",
                                    }, children: items.map((item) => (_local_SP_JSX.jsx(LibraryCoverCard, { title: item.title || "未命名游戏", platform: item.platform, meta: item.size_text || "-", coverUrl: item.cover_portrait_url || item.cover_url, installed: Boolean(item.game_id && installedGameIds.has(item.game_id)), busyLabel: busyKey === item.game_id ? "处理中..." : "", disabled: Boolean(busyKey), coverProxyBase: coverProxyBase, onPress: () => onOpenDetail(item) }, item.game_id))) }) }) }, `shelf:${sectionTitle}`))) })) : (_local_SP_JSX.jsx(DFL.PanelSection, { title: `游戏列表（${catalog.total}）`, children: _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.Focusable, { style: {
                                    display: "grid",
                                    gridTemplateColumns: `repeat(5, ${LIBRARY_CARD_WIDTH}px)`,
                                    columnGap: "33px",
                                    rowGap: "37px",
                                    justifyContent: "center",
                                    justifyItems: "center",
                                    width: "100%",
                                    maxWidth: "806px",
                                    margin: "0 auto",
                                    padding: "6px 0 20px",
                                    overflowX: "auto",
                                }, children: catalog.items.map((item) => (_local_SP_JSX.jsx(LibraryCoverCard, { title: item.title || "未命名游戏", platform: item.platform, meta: item.size_text || "-", coverUrl: item.cover_portrait_url || item.cover_url, installed: Boolean(item.game_id && installedGameIds.has(item.game_id)), busyLabel: busyKey === item.game_id ? "处理中..." : "", disabled: Boolean(busyKey), coverProxyBase: coverProxyBase, onPress: () => onOpenDetail(item) }, item.game_id))) }) }) })), catalog.items.length < catalog.total ? (_local_SP_JSX.jsx(DFL.PanelSection, { children: _local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsxs(DFL.Focusable, { style: { display: "flex", alignItems: "center", justifyContent: "center", gap: "12px", width: "100%" }, children: [_local_SP_JSX.jsx(DFL.DialogButton, { onClick: loadMore, disabled: loadingCatalog, style: { width: "auto", padding: "7px 18px" }, children: loadingCatalog ? "加载中..." : "加载更多" }), _local_SP_JSX.jsx("div", { style: { fontSize: "11px", opacity: 0.65 }, children: `已显示 ${catalog.items.length} / ${catalog.total}` })] }) }) })) : null] })) : (_local_SP_JSX.jsxs(DFL.PanelSection, { title: `已安装（${installed.total}）`, children: [loadingInstalled ? (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px" }, children: "\u52A0\u8F7D\u4E2D..." }) })) : null, installed.items.length === 0 ? (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx("div", { style: { fontSize: "12px" }, children: "\u8FD8\u6CA1\u6709\u5DF2\u5B89\u88C5\u6E38\u620F" }) })) : (_local_SP_JSX.jsx(DFL.PanelSectionRow, { children: _local_SP_JSX.jsx(DFL.Focusable, { style: {
                                display: "grid",
                                gridTemplateColumns: `repeat(5, ${LIBRARY_CARD_WIDTH}px)`,
                                columnGap: "33px",
                                rowGap: "37px",
                                justifyContent: "center",
                                justifyItems: "center",
                                width: "100%",
                                maxWidth: "806px",
                                margin: "0 auto",
                                padding: "6px 0 20px",
                                overflowX: "auto",
                            }, children: installed.items.map((item) => (_local_SP_JSX.jsx(LibraryCoverCard, { title: item.title || "未命名游戏", platform: item.platform, meta: item.playtime_text ? `${item.size_text || "-"} · ${item.playtime_text}` : (item.size_text || "-"), coverUrl: item.cover_portrait_url || item.cover_url, installed: true, disabled: Boolean(busyKey), coverProxyBase: coverProxyBase, onPress: () => void onLaunchInstalled(item), actions: _local_SP_JSX.jsxs(_local_SP_JSX.Fragment, { children: [_local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => void onOpenFolder(item), disabled: Boolean(busyKey), style: { flex: 1, minWidth: 0, padding: "4px 2px", fontSize: "11px" }, children: "\u76EE\u5F55" }), _local_SP_JSX.jsx(DFL.DialogButton, { onClick: () => onUninstall(item), disabled: Boolean(busyKey), style: { flex: 1, minWidth: 0, padding: "4px 2px", fontSize: "11px", background: "rgba(255,106,106,0.22)" }, children: "\u5378\u8F7D" })] }) }, item.game_id))) }) }))] }))] }));
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
        titleView: _local_SP_JSX.jsx("div", { className: DFL.staticClasses.Title, children: "freedeckCY" }),
        content: _local_SP_JSX.jsx(Content, {}),
        icon: _local_SP_JSX.jsx(FaCloudDownloadAlt, {}),
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

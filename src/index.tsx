import {
  ButtonItem,
  ConfirmModal,
  DialogButton,
  Focusable,
  Navigation,
  PanelSection,
  PanelSectionRow,
  Router,
  DropdownItem,
  SliderField,
  Tabs,
  ToggleField,
  TextField,
  showModal,
  staticClasses,
} from "@decky/ui";
import * as DeckyUiNS from "@decky/ui";
import {
  FileSelectionType,
  callable,
  definePlugin,
  openFilePicker,
  routerHook,
  toaster,
} from "@decky/api";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { FaCloudDownloadAlt } from "react-icons/fa";

type ApiStatus = "success" | "error";
const SETTINGS_ROUTE = "/freedeckcy/settings";
const LIBRARY_ROUTE = "/freedeckcy/library";
const PLUGIN_UI_BUILD = "0.26.3";

interface ApiResponse<T> {
  status: ApiStatus;
  message?: string;
  data?: T;
  url?: string;
  reason?: string;
  diagnostics?: unknown;
}

interface LoginState {
  logged_in: boolean;
  user_account: string;
  message: string;
}

interface InstalledGameItem {
  game_id: string;
  title: string;
  install_path: string;
  size_text?: string;
  status?: string;
  steam_app_id?: number;
  playtime_seconds?: number;
  playtime_text?: string;
  playtime_sessions?: number;
  playtime_last_played_at?: number;
  playtime_active?: boolean;
}

interface InstalledState {
  total: number;
  preview: InstalledGameItem[];
}

interface TaskItem {
  task_id: string;
  game_id: string;
  game_title?: string;
  game_name?: string;
  file_name: string;
  status: string;
  progress: number;
  speed: number;
  error_reason?: string;
  install_status?: string;
  install_message?: string;
  installed_path?: string;
}

interface SettingsState {
  download_dir: string;
  install_dir: string;
  split_count: number;
  page_size: number;
  auto_delete_package: boolean;
  auto_install: boolean;
  cloud_save_auto_upload: boolean;
  cloud_save_include_emulators: boolean;
}

interface BaiduWebLoginState {
  logged_in: boolean;
  user_account: string;
  message: string;
}

interface BaiduQrState {
  stage: string;
  user_account?: string;
  qr_data_url?: string;
  qrcode_url?: string;
  expires_at?: number;
  interval?: number;
  message?: string;
}

interface BaiduOpenApiLoginState {
  configured: boolean;
  logged_in: boolean;
  user_account: string;
  expires_at: number;
  message: string;
}

interface SteamRestartState {
  pending: boolean;
  game_id?: string;
  title?: string;
  app_id?: number;
}

interface PanelState {
  login: LoginState;
  baidu_login?: BaiduWebLoginState;
  baidu_openapi_login?: BaiduOpenApiLoginState;
  installed: InstalledState;
  tasks: TaskItem[];
  settings: SettingsState;
  library_url: string;
  power_diagnostics?: Record<string, unknown>;
  steam_restart?: SteamRestartState;
}

interface SettingsPayload {
  download_dir: string;
  install_dir: string;
  split_count: number;
  page_size: number;
  auto_delete_package: boolean;
  auto_install: boolean;
  cloud_save_auto_upload: boolean;
  cloud_save_include_emulators: boolean;
}

interface StorageOption {
  kind: string;
  label: string;
  mount: string;
  download_dir: string;
  install_dir: string;
  free_bytes: number;
  total_bytes: number;
  free_text: string;
  total_text: string;
}

interface StorageOptionsState {
  internal?: StorageOption;
  external?: StorageOption[];
  options?: StorageOption[];
}

interface DiagnosticCheck {
  id: string;
  label: string;
  status: string;
  detail: string;
  fix?: string;
}

interface DiagnosticsReport {
  generated_at: number;
  version: string;
  arch: string;
  summary: { ok?: number; warn?: number; fail?: number; skip?: number };
  checks: DiagnosticCheck[];
}

interface CatalogItem {
  game_id: string;
  title: string;
  platform: string;
  categories: string;
  size_text: string;
  cover_url?: string;
  cover_portrait_url?: string;
}

interface CatalogPage {
  total: number;
  page: number;
  page_size: number;
  platforms?: { value: string; label: string; count: number }[];
  categories?: { value: string; label: string; count: number }[];
  items: CatalogItem[];
}

interface InstalledItem {
  game_id: string;
  title: string;
  install_path: string;
  status: string;
  size_text: string;
  platform: string;
  steam_app_id: number;
  playtime_text?: string;
  playtime_active?: boolean;
  exists?: boolean;
  cover_url?: string;
  cover_portrait_url?: string;
  categories?: string;
}

interface InstalledList {
  total: number;
  items: InstalledItem[];
}

interface InstallPlanData {
  game_title?: string;
  provider?: string;
  platform?: string;
  can_install?: boolean;
  required_download_human?: string;
  required_install_human?: string;
  download_dir?: string;
  install_dir?: string;
  emulator_info?: { name?: string; setup_hint?: string; bios_required?: boolean; bios_present?: boolean };
  message?: string;
}

interface UrlResponse {
  url: string;
}

interface ClearLoginResponse {
  logged_in: boolean;
  user_account: string;
  message: string;
}

interface CloudSaveUploadItem {
  game_id: string;
  game_title: string;
  game_key: string;
  status: string;
  reason: string;
  cloud_path: string;
}

interface CloudSaveLastResult {
  stage: string;
  reason: string;
  message: string;
  started_at: number;
  finished_at: number;
  timestamp: string;
  total_games: number;
  processed_games: number;
  uploaded: number;
  skipped: number;
  failed: number;
  results: CloudSaveUploadItem[];
}

interface CloudSaveUploadState {
  stage: string;
  message: string;
  reason: string;
  running: boolean;
  progress: number;
  current_game: string;
  total_games: number;
  processed_games: number;
  uploaded: number;
  skipped: number;
  failed: number;
  results: CloudSaveUploadItem[];
  last_result: CloudSaveLastResult;
}

interface CloudSaveUploadStartData {
  accepted: boolean;
  message: string;
  state: CloudSaveUploadState;
}

interface CloudSaveUploadStatusData {
  state: CloudSaveUploadState;
}

interface CloudSaveRestoreEntry {
  entry_id: string;
  entry_name: string;
  archive_rel_path?: string;
  file_count?: number;
}

interface CloudSaveRestoreVersion {
  version_name: string;
  timestamp: number;
  display_time: string;
  size_bytes: number;
  file_id?: string;
}

interface CloudSaveRestoreGameOption {
  game_id: string;
  game_title: string;
  game_key: string;
  versions: CloudSaveRestoreVersion[];
  available: boolean;
  reason: string;
}

interface CloudSaveRestoreOptionsData {
  games: CloudSaveRestoreGameOption[];
  updated_at: number;
}

interface CloudSaveRestoreEntriesData {
  game_id: string;
  game_key: string;
  game_title: string;
  version_name: string;
  entries: CloudSaveRestoreEntry[];
}

interface CloudSaveRestorePlanData {
  accepted: boolean;
  plan_id?: string;
  message: string;
  reason: string;
  requires_confirmation: boolean;
  conflict_count: number;
  conflict_samples: string[];
  target_candidates: string[];
  selected_target_dir: string;
  selected_entry_ids: string[];
  available_entries: CloudSaveRestoreEntry[];
  restorable_files: number;
  restorable_entries: number;
}

interface CloudSaveRestoreApplyData {
  status: string;
  reason: string;
  message: string;
  target_dir: string;
  restored_files: number;
  restored_entries: number;
  conflicts_overwritten: number;
}

interface CloudSaveRestoreResultItem {
  entry_id: string;
  entry_name: string;
  status: string;
  reason: string;
  file_count: number;
}

interface CloudSaveRestoreLastResult {
  status: string;
  reason: string;
  message: string;
  target_dir: string;
  restored_files: number;
  restored_entries: number;
  conflicts_overwritten: number;
  results: CloudSaveRestoreResultItem[];
}

interface CloudSaveRestoreState {
  stage: string;
  message: string;
  reason: string;
  running: boolean;
  progress: number;
  target_game_id: string;
  target_game_title: string;
  target_game_key: string;
  target_version: string;
  selected_entry_ids: string[];
  selected_target_dir: string;
  requires_confirmation: boolean;
  conflict_count: number;
  conflict_samples: string[];
  restored_files: number;
  restored_entries: number;
  results: CloudSaveRestoreResultItem[];
  last_result: CloudSaveRestoreLastResult;
}

interface CloudSaveRestoreStatusData {
  state: CloudSaveRestoreState;
}

interface UninstallInstalledPayload {
  game_id: string;
  install_path: string;
  delete_files: boolean;
  delete_compatdata?: boolean;
}

interface UninstallPreviewData {
  game_id: string;
  title: string;
  install_path: string;
  install_size_bytes: number;
  steam_app_id: number;
  compatdata_paths: string[];
  compatdata_size_bytes: number;
}

interface LibraryGameTimeStatsData {
  managed: boolean;
  reason?: string;
  message?: string;
  app_id?: number;
  game_id?: string;
  title?: string;
  my_playtime_seconds?: number;
  my_playtime_text?: string;
  my_playtime_active?: boolean;
  main_story_hours?: number;
  main_story_time_text?: string;
  total_hours?: number;
  total_time_text?: string;
}

const getTianyiPanelState = callable<[Record<string, unknown>?], ApiResponse<PanelState>>("get_tianyi_panel_state");
const getTianyiStorageOptions = callable<[], ApiResponse<StorageOptionsState>>("get_tianyi_storage_options");
const listTianyiCatalog = callable<[Record<string, unknown>], ApiResponse<CatalogPage>>("list_tianyi_catalog");
const prepareTianyiInstall = callable<[Record<string, unknown>], ApiResponse<InstallPlanData>>("prepare_tianyi_install");
const startTianyiInstall = callable<[Record<string, unknown>], ApiResponse<Record<string, unknown>>>("start_tianyi_install");
const listTianyiInstalledGames = callable<[], ApiResponse<InstalledList>>("list_tianyi_installed_games");
const launchTianyiInstalledGame = callable<[string], ApiResponse<Record<string, unknown>>>("launch_tianyi_installed_game");
const openTianyiInstalledFolder = callable<[string], ApiResponse<Record<string, unknown>>>("open_tianyi_installed_folder");
const scanTianyiInstalledGames = callable<[], ApiResponse<Record<string, unknown>>>("scan_tianyi_installed_games");
const runTianyiDiagnostics = callable<[], ApiResponse<DiagnosticsReport>>("run_tianyi_diagnostics");
const exportTianyiDiagnosticsFile = callable<[], ApiResponse<{ path?: string; filename?: string; size?: number; message?: string }>>("export_tianyi_diagnostics_file");
const uninstallTianyiInstalled = callable<[Record<string, unknown>], ApiResponse<Record<string, unknown>>>("uninstall_tianyi_installed_game");
const getTianyiLoginUrl = callable<[], ApiResponse<UrlResponse>>("get_tianyi_login_url");
const setTianyiSettings = callable<[SettingsPayload], ApiResponse<SettingsState>>("set_tianyi_settings");
const clearTianyiLogin = callable<[], ApiResponse<ClearLoginResponse>>("clear_tianyi_login");
const startBaiduQrLogin = callable<[], ApiResponse<BaiduQrState>>("start_baidu_qr_login");
const pollBaiduQrLogin = callable<[], ApiResponse<BaiduQrState>>("poll_baidu_qr_login");
const cancelBaiduQrLogin = callable<[], ApiResponse<BaiduQrState>>("cancel_baidu_qr_login");
const clearBaiduLogin = callable<[], ApiResponse<BaiduWebLoginState>>("clear_baidu_login");
const getBaiduOpenapiAuthorizeUrl = callable<[], ApiResponse<UrlResponse>>("get_baidu_openapi_authorize_url");
const setBaiduOpenapiApp = callable<[Record<string, string>], ApiResponse<BaiduOpenApiLoginState>>(
  "set_baidu_openapi_app",
);
const exchangeBaiduOpenapiCode = callable<[Record<string, string>], ApiResponse<BaiduOpenApiLoginState>>(
  "exchange_baidu_openapi_code",
);
const clearBaiduOpenapiLogin = callable<[], ApiResponse<BaiduOpenApiLoginState>>("clear_baidu_openapi_login");
const startTianyiCloudSaveUpload = callable<[], ApiResponse<CloudSaveUploadStartData>>("start_tianyi_cloud_save_upload");
const getTianyiCloudSaveUploadStatus = callable<[], ApiResponse<CloudSaveUploadStatusData>>(
  "get_tianyi_cloud_save_upload_status",
);
const listTianyiCloudSaveRestoreOptions = callable<[], ApiResponse<CloudSaveRestoreOptionsData>>(
  "list_tianyi_cloud_save_restore_options",
);
const listTianyiCloudSaveRestoreEntries = callable<
  [{ game_id: string; game_key: string; game_title: string; version_name: string }],
  ApiResponse<CloudSaveRestoreEntriesData>
>("list_tianyi_cloud_save_restore_entries");
const planTianyiCloudSaveRestore = callable<
  [{ game_id: string; game_key: string; game_title: string; version_name: string; selected_entry_ids: string[]; target_dir?: string }],
  ApiResponse<CloudSaveRestorePlanData>
>("plan_tianyi_cloud_save_restore");
const applyTianyiCloudSaveRestore = callable<
  [{ plan_id: string; confirm_overwrite: boolean }],
  ApiResponse<CloudSaveRestoreApplyData>
>("apply_tianyi_cloud_save_restore");
const getTianyiCloudSaveRestoreStatus = callable<[], ApiResponse<CloudSaveRestoreStatusData>>(
  "get_tianyi_cloud_save_restore_status",
);
const recordTianyiGameAction = callable<
  [{ phase: string; app_id: string; action_name?: string }],
  ApiResponse<Record<string, unknown>>
>("record_tianyi_game_action");
const getTianyiLibraryGameTimeStats = callable<
  [{ app_id: string; title?: string }],
  ApiResponse<LibraryGameTimeStatsData>
>("get_tianyi_library_game_time_stats");
const pauseTianyiTask = callable<[{ task_id: string }], ApiResponse<Record<string, unknown>>>("pause_tianyi_task");
const resumeTianyiTask = callable<[{ task_id: string }], ApiResponse<Record<string, unknown>>>("resume_tianyi_task");
const removeTianyiTask = callable<[{ task_id: string }], ApiResponse<Record<string, unknown>>>("remove_tianyi_task");
const retryTianyiTask = callable<[{ task_id: string }], ApiResponse<Record<string, unknown>>>("retry_tianyi_task");
const previewTianyiUninstall = callable<
  [{ game_id: string; install_path: string }],
  ApiResponse<UninstallPreviewData>
>("preview_tianyi_uninstall");
const uninstallTianyiInstalledGame = callable<[UninstallInstalledPayload], ApiResponse<Record<string, unknown>>>(
  "uninstall_tianyi_installed_game",
);
const PANEL_REQUEST_TIMEOUT_MS = 6000;
const PANEL_POLL_MODE_ACTIVE = "active";
const PANEL_POLL_MODE_IDLE = "idle";
const PANEL_POLL_MODE_BACKGROUND = "background";
type PanelPollMode = typeof PANEL_POLL_MODE_ACTIVE | typeof PANEL_POLL_MODE_IDLE | typeof PANEL_POLL_MODE_BACKGROUND;
const PANEL_ACTIVE_POLL_MS = 900;
const PANEL_IDLE_POLL_MS = 6000;
const PANEL_BACKGROUND_POLL_MS = 30000;

const EMPTY_SETTINGS: SettingsState = {
  download_dir: "",
  install_dir: "",
  split_count: 16,
  page_size: 50,
  auto_delete_package: false,
  auto_install: true,
  cloud_save_auto_upload: true,
  cloud_save_include_emulators: true,
};

const EMPTY_CLOUD_SAVE_STATE: CloudSaveUploadState = {
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

const EMPTY_CLOUD_SAVE_RESTORE_STATE: CloudSaveRestoreState = {
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

const EMPTY_BAIDU_OPENAPI_STATE: BaiduOpenApiLoginState = {
  configured: false,
  logged_in: false,
  user_account: "",
  expires_at: 0,
  message: "未配置",
};

const EMPTY_BAIDU_WEB_STATE: BaiduWebLoginState = {
  logged_in: false,
  user_account: "",
  message: "未登录",
};

const EMPTY_STATE: PanelState = {
  login: { logged_in: false, user_account: "", message: "" },
  baidu_login: EMPTY_BAIDU_WEB_STATE,
  baidu_openapi_login: EMPTY_BAIDU_OPENAPI_STATE,
  installed: { total: 0, preview: [] },
  tasks: [],
  settings: EMPTY_SETTINGS,
  library_url: "",
  steam_restart: { pending: false },
};

interface GamepadTabClassMap {
  TabsRowScroll?: string;
  TabRowTabs?: string;
  Tab?: string;
  Active?: string;
  Selected?: string;
}

function getGamepadTabClassMap(): GamepadTabClassMap | null {
  const map = (DeckyUiNS as unknown as { gamepadTabbedPageClasses?: GamepadTabClassMap }).gamepadTabbedPageClasses;
  if (!map || typeof map !== "object") return null;
  return map;
}

function formatSpeed(speed: number): string {
  let value = Number(speed || 0);
  if (!Number.isFinite(value) || value <= 0) return "0 B/s";
  const units = ["B/s", "KB/s", "MB/s", "GB/s"];
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(index === 0 ? 0 : 2)} ${units[index]}`;
}

function formatBytesText(size: number): string {
  let value = Number(size || 0);
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatPlaytimeText(seconds: number, fallback?: string): string {
  const fallbackText = String(fallback || "").trim();
  if (fallbackText) return fallbackText;
  const totalSeconds = Math.max(0, Number(seconds || 0));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) return `${hours} 小时 ${minutes} 分钟`;
  if (minutes > 0) return `${minutes} 分钟`;
  return "0 分钟";
}

function clampProgress(progress: number): number {
  const value = Number(progress || 0);
  if (!Number.isFinite(value)) return 0;
  if (value < 0) return 0;
  if (value > 100) return 100;
  return value;
}

function errorText(error: unknown): string {
  if (error && typeof error === "object") {
    const message = String((error as { message?: unknown }).message ?? "").trim();
    if (message) return message;
  }
  const text = String(error ?? "").trim();
  return text || "操作失败";
}

function toastError(error: unknown): void {
  toaster.toast({ title: "freedeckCY", body: errorText(error) });
}

function downloadStatusText(status: string): string {
  const value = String(status || "").toLowerCase();
  if (value === "active") return "下载中";
  if (value === "waiting") return "等待中";
  if (value === "paused") return "已暂停";
  if (value === "complete") return "下载完成";
  if (value === "error") return "下载失败";
  if (value === "removed") return "已移除";
  return status || "未知";
}

function installStatusText(status: string): string {
  const value = String(status || "").toLowerCase();
  if (value === "pending") return "待处理";
  if (value === "installing") return "安装中";
  if (value === "installed") return "已安装";
  if (value === "skipped") return "已跳过";
  if (value === "failed") return "安装失败";
  return status || "未开始";
}

function progressColors(task: TaskItem): { track: string; fill: string; label: string } {
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

function TaskProgressRow(task: TaskItem) {
  const progress = clampProgress(task.progress);
  const colors = progressColors(task);
  const title = task.game_title || task.game_name || task.file_name || "未命名任务";
  const installStatus = String(task.install_status || "").trim();
  const installMessage = String(task.install_message || "").trim();
  const errorReason = String(task.error_reason || "").trim();

  return (
    <div
      style={{
        width: "100%",
        padding: "8px 0",
        display: "flex",
        flexDirection: "column",
        gap: "6px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
        <div
          style={{
            fontSize: "14px",
            fontWeight: 600,
            lineHeight: 1.35,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            maxWidth: "70%",
          }}
          title={title}
        >
          {title}
        </div>
        <div style={{ fontSize: "11px", color: colors.label }}>{downloadStatusText(task.status)}</div>
      </div>

      <div
        style={{
          width: "100%",
          height: "8px",
          borderRadius: "999px",
          background: colors.track,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${progress.toFixed(1)}%`,
            height: "100%",
            borderRadius: "999px",
            background: colors.fill,
            transition: "width 860ms linear",
          }}
        />
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", fontSize: "11px", color: "#c9c9c9" }}>
        <span>{`进度 ${progress.toFixed(1)}%`}</span>
        <span>{`速度 ${formatSpeed(task.speed)}`}</span>
      </div>

      {installStatus ? (
        <div style={{ fontSize: "11px", color: "#bcbcbc", lineHeight: 1.4 }}>
          {`安装：${installStatusText(installStatus)}${installMessage ? ` | ${installMessage}` : ""}`}
        </div>
      ) : null}
      {errorReason ? (
        <div style={{ fontSize: "11px", color: "#ff8e8e", lineHeight: 1.4 }}>{`错误：${errorReason}`}</div>
      ) : null}
    </div>
  );
}

function getTextFieldValue(eventOrValue: unknown): string {
  if (typeof eventOrValue === "string") return eventOrValue;
  if (eventOrValue && typeof eventOrValue === "object" && "target" in eventOrValue) {
    const target = (eventOrValue as { target?: { value?: unknown } }).target;
    return String(target?.value ?? "");
  }
  return String(eventOrValue ?? "");
}

function openExternalUrl(rawUrl: string): void {
  const url = String(rawUrl || "").trim();
  if (!url) return;

  try {
    Navigation.NavigateToExternalWeb(url);
    return;
  } catch {
    // 忽略并回退到备用跳转。
  }

  try {
    const steamClient = (window as unknown as {
      SteamClient?: { Browser?: { OpenUrl?: (u: string) => void } };
    }).SteamClient;
    if (steamClient?.Browser?.OpenUrl) {
      steamClient.Browser.OpenUrl(url);
      return;
    }
  } catch {
    // 忽略并回退到 window.open。
  }

  const popup = window.open(url, "_blank");
  if (!popup) window.location.href = url;
}

function describeOpenError(result: ApiResponse<UrlResponse>, fallback: string): string {
  const message = String(result.message || fallback);
  const reason = String(result.reason || "").trim();
  if (!reason) return message;
  if (!result.diagnostics) return `${message}（${reason}）`;
  try {
    return `${message}（${reason}）\n${JSON.stringify(result.diagnostics)}`;
  } catch {
    return `${message}（${reason}）`;
  }
}

function toPayload(settings: SettingsState): SettingsPayload {
  return {
    download_dir: String(settings.download_dir || ""),
    install_dir: String(settings.install_dir || ""),
    split_count: Math.max(1, Math.min(64, Number(settings.split_count || 16))),
    page_size: Math.max(10, Math.min(200, Number(settings.page_size || 50))),
    auto_delete_package: Boolean(settings.auto_delete_package),
    auto_install: true,
    cloud_save_auto_upload: Boolean(settings.cloud_save_auto_upload),
    cloud_save_include_emulators: Boolean(settings.cloud_save_include_emulators),
  };
}

function normalizeCloudSaveUploadState(raw: Partial<CloudSaveUploadState> | undefined): CloudSaveUploadState {
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

function normalizeCloudSaveRestoreState(raw: Partial<CloudSaveRestoreState> | undefined): CloudSaveRestoreState {
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

function formatBytes(value: number): string {
  let size = Number(value || 0);
  if (!Number.isFinite(size) || size <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 2)} ${units[index]}`;
}

function cloudSaveStageText(stage: string): string {
  const value = String(stage || "").trim().toLowerCase();
  if (value === "listing") return "拉取版本中";
  if (value === "planning") return "规划中";
  if (value === "ready") return "待确认";
  if (value === "applying") return "恢复中";
  if (value === "scanning") return "扫描中";
  if (value === "packaging") return "打包中";
  if (value === "uploading") return "上传中";
  if (value === "completed") return "已完成";
  if (value === "failed") return "失败";
  return "空闲";
}

type AnyFunction = (...args: unknown[]) => unknown;

interface PatchHandle {
  unpatch: () => void;
}

const LIBRARY_TIME_CACHE_TTL_MS = 5 * 60 * 1000;
const LIBRARY_TIME_NEGATIVE_CACHE_TTL_MS = 3 * 1000;
const LIBRARY_TIME_RETRY_MS = 3 * 1000;
const LIBRARY_TIME_REFRESH_MS = 2 * 60 * 1000;
const libraryTimeCache = new Map<string, { updatedAt: number; payload: LibraryGameTimeStatsData }>();

interface SteamAppsGameActionApi {
  RegisterForGameActionStart?: (cb: (...args: unknown[]) => void) => { unregister?: () => void };
  RegisterForGameActionEnd?: (cb: (...args: unknown[]) => void) => { unregister?: () => void };
}

function parseGameActionAppIdCandidate(value: unknown): number {
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

  const obj = value as Record<string, unknown>;
  const keys = ["app_id", "appid", "appId", "unAppID", "nAppID", "m_unAppID", "m_nAppID"];
  for (const key of keys) {
    const parsed = parseGameActionAppIdCandidate(obj[key]);
    if (parsed > 0) return parsed;
  }
  return 0;
}

function resolveGameActionAppId(args: unknown[]): string {
  const ordered = [args[1], args[0], args[2], ...args];
  for (const value of ordered) {
    const parsed = parseGameActionAppIdCandidate(value);
    if (parsed > 0) return String(parsed);
  }
  return "";
}

function invalidateLibraryTimeCacheByAppId(appId: string): void {
  const prefix = `${String(appId || "").trim()}::`;
  if (!prefix || prefix === "::") return;
  for (const key of Array.from(libraryTimeCache.keys())) {
    if (key.startsWith(prefix)) {
      libraryTimeCache.delete(key);
    }
  }
}

function resolveSteamAppsGameActionApi(): SteamAppsGameActionApi | null {
  if (typeof window === "undefined") return null;
  const apps = (
    window as unknown as {
      SteamClient?: { Apps?: SteamAppsGameActionApi };
    }
  ).SteamClient?.Apps;
  if (!apps || typeof apps !== "object") return null;
  return apps;
}

function installGlobalGameActionReporter(): () => void {
  let disposed = false;
  let retryTimer: number | null = null;
  let teardownListener: (() => void) | null = null;

  const clearRetry = () => {
    if (retryTimer === null) return;
    if (typeof window !== "undefined") {
      window.clearTimeout(retryTimer);
    }
    retryTimer = null;
  };

  const scheduleRetry = () => {
    if (disposed || retryTimer !== null || typeof window === "undefined") return;
    retryTimer = window.setTimeout(() => {
      retryTimer = null;
      tryInstall();
    }, 1500);
  };

  const tryInstall = () => {
    if (disposed || teardownListener) return;

    let apps: SteamAppsGameActionApi | null = null;
    try {
      apps = resolveSteamAppsGameActionApi();
    } catch {
      scheduleRetry();
      return;
    }

    const registerStart = apps?.RegisterForGameActionStart;
    const registerEnd = apps?.RegisterForGameActionEnd;
    if (typeof registerStart !== "function" || typeof registerEnd !== "function") {
      scheduleRetry();
      return;
    }

    const activeAppIds = new Set<string>();
    const reportAction = (phase: "start" | "end", args: unknown[]) => {
      const appId = resolveGameActionAppId(args);
      if (!appId) return;

      if (phase === "start") {
        if (activeAppIds.has(appId)) return;
        activeAppIds.add(appId);
      } else {
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

    let startListener: { unregister?: () => void } | undefined;
    let endListener: { unregister?: () => void } | undefined;
    try {
      startListener = registerStart((...args: unknown[]) => {
        reportAction("start", args);
      });
      endListener = registerEnd((...args: unknown[]) => {
        reportAction("end", args);
      });
    } catch {
      scheduleRetry();
      return;
    }

    teardownListener = () => {
      activeAppIds.clear();
      try {
        startListener?.unregister?.();
      } catch {
        // 忽略反注册异常。
      }
      try {
        endListener?.unregister?.();
      } catch {
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

function hasPositiveLibraryHltb(payload: LibraryGameTimeStatsData | null | undefined): boolean {
  if (!payload) return false;
  const main = Number(payload.main_story_hours || 0);
  const total = Number(payload.total_hours || 0);
  return (Number.isFinite(main) && main > 0) || (Number.isFinite(total) && total > 0);
}

function normalizeHoursText(hoursRaw: number | undefined, fallbackRaw: string | undefined): string {
  const fallback = String(fallbackRaw || "").trim();
  if (fallback) return fallback;
  const hours = Number(hoursRaw || 0);
  if (!Number.isFinite(hours) || hours <= 0) return "-";
  const rounded = Math.round(hours * 10) / 10;
  if (Math.abs(rounded - Math.round(rounded)) < 0.05) {
    return `${Math.round(rounded)} 小时`;
  }
  return `${rounded.toFixed(1)} 小时`;
}

function wrapReactType(node: unknown, prop = "type"): Record<string, unknown> | null {
  if (!node || typeof node !== "object") return null;
  const owner = node as Record<string, unknown>;
  const current = owner[prop];
  if (!current || typeof current !== "object") return null;
  const currentMap = current as Record<string, unknown>;
  if (Boolean(currentMap.__FREDECK_WRAPPED)) return currentMap;
  const wrapped: Record<string, unknown> = { ...currentMap, __FREDECK_WRAPPED: true };
  owner[prop] = wrapped;
  return wrapped;
}

function afterPatch(object: Record<string, unknown>, property: string, handler: (args: unknown[], ret: unknown) => unknown): PatchHandle {
  const original = object[property];
  if (typeof original !== "function") {
    return { unpatch: () => {} };
  }

  const originalFn = original as AnyFunction;
  const patched: AnyFunction = function patchedFunction(this: unknown, ...args: unknown[]) {
    const result = originalFn.apply(this, args);
    const next = handler.call(this, args, result);
    return typeof next === "undefined" ? result : next;
  };

  try {
    Object.assign(patched, originalFn);
  } catch {
    // 忽略函数属性拷贝失败。
  }
  try {
    Object.defineProperty(patched, "toString", {
      value: () => originalFn.toString(),
      configurable: true,
    });
  } catch {
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

function resolveSpliceTarget(children: unknown): unknown[] | null {
  if (!children || typeof children !== "object") return null;
  const root = children as Record<string, unknown>;
  const part1 = root.props as Record<string, unknown> | undefined;
  const part2 = part1?.children as unknown[];
  if (!Array.isArray(part2) || part2.length < 2) return null;
  const part3 = part2[1] as Record<string, unknown> | undefined;
  const part4 = part3?.props as Record<string, unknown> | undefined;
  const part5 = part4?.children as Record<string, unknown> | undefined;
  const part6 = part5?.props as Record<string, unknown> | undefined;
  const list = part6?.children;
  if (Array.isArray(list)) return list;

  const visited = new Set<object>();
  const queue: unknown[] = [children];
  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || typeof current !== "object") continue;
    if (visited.has(current as object)) continue;
    visited.add(current as object);

    if (Array.isArray(current)) {
      if (current.length > 0) {
        const hasOverviewCarrier = current.some((node) => {
          if (!node || typeof node !== "object") return false;
          const nodeProps = (node as Record<string, unknown>).props as Record<string, unknown> | undefined;
          const inner = (nodeProps?.children as Record<string, unknown> | undefined)?.props as Record<string, unknown> | undefined;
          return typeof inner?.overview !== "undefined" || typeof inner?.details !== "undefined";
        });
        if (hasOverviewCarrier) return current;
      }
      for (const item of current) {
        if (item && typeof item === "object") queue.push(item);
      }
      continue;
    }

    const map = current as Record<string, unknown>;
    for (const value of Object.values(map)) {
      if (!value) continue;
      if (typeof value === "object") queue.push(value);
    }
  }

  return null;
}

function findLibraryInsertIndex(nodes: unknown[]): number {
  return nodes.findIndex((child) => {
    if (!child || typeof child !== "object") return false;
    const props = (child as Record<string, unknown>).props as Record<string, unknown> | undefined;
    if (!props) return false;
    const hasFocusFlag = typeof props.childFocusDisabled !== "undefined";
    const hasNavRef = typeof props.navRef !== "undefined";
    const innerProps = (props.children as Record<string, unknown> | undefined)?.props as Record<string, unknown> | undefined;
    const hasDetails = typeof innerProps?.details !== "undefined";
    const hasOverview = typeof innerProps?.overview !== "undefined";
    const hasFastRender = typeof innerProps?.bFastRender !== "undefined";
    return hasFocusFlag && hasNavRef && hasDetails && hasOverview && hasFastRender;
  });
}

function resolveLibraryInsertIndex(nodes: unknown[]): number {
  const exact = findLibraryInsertIndex(nodes);
  if (exact >= 0) return exact;

  const firstNative = nodes.findIndex((child) => {
    if (!child || typeof child !== "object") return false;
    const key = String((child as Record<string, unknown>).key || "");
    return !key.startsWith("freedeckcy-library-times-");
  });
  if (firstNative >= 0) return Math.min(firstNative + 1, nodes.length);

  return Math.min(1, nodes.length);
}

const LIBRARY_TIME_BLOCK_ID = "freedeckcy-library-times";

function isLibraryTimeNode(child: unknown): boolean {
  if (!child || typeof child !== "object") return false;
  const childProps = (child as Record<string, unknown>).props as Record<string, unknown> | undefined;
  return String(childProps?.id || "") === LIBRARY_TIME_BLOCK_ID;
}

function ensureNodeChildrenArray(node: Record<string, unknown>): unknown[] {
  const props = (node.props as Record<string, unknown> | undefined) || {};
  node.props = props;
  const children = props.children;
  if (Array.isArray(children)) return children;
  if (typeof children === "undefined") {
    const next: unknown[] = [];
    props.children = next;
    return next;
  }
  const next: unknown[] = [children];
  props.children = next;
  return next;
}

function findInReactTreeLike(node: unknown, filter: (value: unknown) => boolean): Record<string, unknown> | null {
  if (!node || typeof node !== "object") return null;
  const visited = new Set<object>();
  const queue: unknown[] = [node];
  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || typeof current !== "object") continue;
    if (visited.has(current as object)) continue;
    visited.add(current as object);

    if (filter(current)) return current as Record<string, unknown>;

    if (Array.isArray(current)) {
      for (const item of current) {
        if (item && typeof item === "object") queue.push(item);
      }
      continue;
    }

    const map = current as Record<string, unknown>;
    const walkKeys = ["props", "children", "child", "sibling"];
    for (const key of walkKeys) {
      const value = map[key];
      if (value && typeof value === "object") queue.push(value);
    }
    for (const value of Object.values(map)) {
      if (value && typeof value === "object") queue.push(value);
    }
  }
  return null;
}

function resolveStaticClassByKey(key: string): string {
  const root = staticClasses as unknown;
  if (!root || typeof root !== "object") return "";
  const visited = new Set<object>();
  const queue: unknown[] = [root];
  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || typeof current !== "object") continue;
    if (visited.has(current as object)) continue;
    visited.add(current as object);

    if (Array.isArray(current)) {
      for (const item of current) {
        if (item && typeof item === "object") queue.push(item);
      }
      continue;
    }

    const map = current as Record<string, unknown>;
    if (typeof map[key] === "string" && String(map[key]).trim()) {
      return String(map[key]).trim();
    }
    for (const value of Object.values(map)) {
      if (value && typeof value === "object") queue.push(value);
    }
  }
  return "";
}

function resolveLibraryOverlayHost(tree: unknown): Record<string, unknown> | null {
  const topCapsuleClass = resolveStaticClassByKey("TopCapsule");
  const headerClass = resolveStaticClassByKey("Header");
  const appDetailsRootClass = resolveStaticClassByKey("AppDetailsRoot");
  const markers = [topCapsuleClass, appDetailsRootClass, headerClass].filter(Boolean);

  const classMatched = findInReactTreeLike(tree, (value) => {
    if (!value || typeof value !== "object") return false;
    const props = (value as Record<string, unknown>).props as Record<string, unknown> | undefined;
    if (!props) return false;
    const className = String(props.className || "");
    const children = props.children;
    if (!className || typeof children === "undefined") return false;
    return markers.some((marker) => className.includes(marker));
  });
  if (classMatched) return classMatched;

  // 回退：命中包含 overview/details 的容器，确保至少能显示。
  return findInReactTreeLike(tree, (value) => {
    if (!value || typeof value !== "object") return false;
    const props = (value as Record<string, unknown>).props as Record<string, unknown> | undefined;
    if (!props) return false;
    const children = props.children;
    if (!children || typeof children !== "object" || Array.isArray(children)) return false;
    const inner = (children as Record<string, unknown>).props as Record<string, unknown> | undefined;
    return typeof inner?.overview !== "undefined" && typeof inner?.details !== "undefined";
  });
}

function resolveLibraryOverviewNode(tree: unknown): Record<string, unknown> | null {
  return findInReactTreeLike(tree, (value) => {
    if (!value || typeof value !== "object") return false;
    const map = value as Record<string, unknown>;
    const appId = Math.max(
      0,
      Number(
        map.appid ??
          map.appId ??
          map.unAppID ??
          map.nAppID ??
          map.m_unAppID ??
          map.m_nAppID ??
          0,
      ),
    );
    if (!Number.isFinite(appId) || appId <= 0) return false;
    const title =
      String(map.display_name || "").trim() ||
      String(map.name || "").trim() ||
      String(map.app_name || "").trim() ||
      String(map.title || "").trim();
    return Boolean(title);
  });
}


function LibraryTimeBlock({ appId, title }: { appId: number; title: string }) {
  const appIdText = String(Math.max(0, Number(appId || 0)));
  const titleText = String(title || "").trim();
  const cacheKey = `${appIdText}::${titleText.toLowerCase()}`;
  const initialCached = (() => {
    const cached = libraryTimeCache.get(cacheKey);
    if (!cached) return null;
    const ttl = hasPositiveLibraryHltb(cached.payload) ? LIBRARY_TIME_CACHE_TTL_MS : LIBRARY_TIME_NEGATIVE_CACHE_TTL_MS;
    if (Date.now() - cached.updatedAt > ttl) {
      libraryTimeCache.delete(cacheKey);
      return null;
    }
    return cached.payload;
  })();

  const [data, setData] = useState<LibraryGameTimeStatsData | null>(initialCached);

  useEffect(() => {
    let alive = true;
    let timerId: number | null = null;
    let inFlight = false;

    const clearTimer = () => {
      if (timerId === null) return;
      window.clearTimeout(timerId);
      timerId = null;
    };

    const scheduleNext = (payload: LibraryGameTimeStatsData | null) => {
      if (!alive) return;
      clearTimer();
      const waitMs = hasPositiveLibraryHltb(payload) ? LIBRARY_TIME_REFRESH_MS : LIBRARY_TIME_RETRY_MS;
      timerId = window.setTimeout(() => {
        void fetchStats();
      }, waitMs);
    };

    const fetchStats = async () => {
      if (!alive || inFlight) return;
      if (!appIdText || appIdText === "0") return;
      inFlight = true;
      try {
        const result = await withTimeout(
          getTianyiLibraryGameTimeStats({
            app_id: appIdText,
            title: titleText,
          }),
          7000,
          "library_time_stats_timeout",
        );
        if (!alive) return;
        if (result.status !== "success") {
          scheduleNext(null);
          return;
        }
        const payload = (result.data || {}) as LibraryGameTimeStatsData;
        libraryTimeCache.set(cacheKey, { updatedAt: Date.now(), payload });
        setData(payload);
        scheduleNext(payload);
      } catch {
        // 忽略库页面时长读取失败，不影响原页面。
        scheduleNext(null);
      } finally {
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
      } else {
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
  if (!data || data.managed !== true) return null;
  const myPlaytime = formatPlaytimeText(data.my_playtime_seconds || 0, data.my_playtime_text);
  const mainStory = normalizeHoursText(data.main_story_hours, data.main_story_time_text);
  const totalTime = normalizeHoursText(data.total_hours, data.total_time_text);
  const activeSuffix = data.my_playtime_active ? "（进行中）" : "";

  return (
    <div
      id={LIBRARY_TIME_BLOCK_ID}
      style={{
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
      }}
    >
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)", gap: "10px" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: "14px", fontWeight: 700, lineHeight: 1.2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {`${myPlaytime}${activeSuffix}`}
          </div>
          <div style={{ fontSize: "10px", opacity: 0.84 }}>已玩时长</div>
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: "14px", fontWeight: 700, lineHeight: 1.2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {mainStory}
          </div>
          <div style={{ fontSize: "10px", opacity: 0.84 }}>主线时长</div>
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: "14px", fontWeight: 700, lineHeight: 1.2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {totalTime}
          </div>
          <div style={{ fontSize: "10px", opacity: 0.84 }}>总时长</div>
        </div>
      </div>
    </div>
  );
}

function installLibraryPlaytimePatch(): () => void {
  const hookApi = routerHook as unknown as {
    addPatch?: (route: string, patcher: (props: unknown) => unknown) => unknown;
    removePatch?: (route: string, patcher: unknown) => void;
  };
  if (typeof hookApi.addPatch !== "function") {
    return () => {};
  }

  const patchFn = (props: unknown) => {
    if (!props || typeof props !== "object") return props;
    const propsMap = props as Record<string, unknown>;
    const childNode = propsMap.children as Record<string, unknown> | undefined;
    const childProps = childNode?.props as Record<string, unknown> | undefined;
    if (!childProps) return props;

    const renderFunc = childProps.renderFunc;
    if (typeof renderFunc !== "function") return props;
    if (Boolean((renderFunc as unknown as Record<string, unknown>).__FREDECK_LIBRARY_RENDER_PATCHED)) return props;

    const renderPatch = afterPatch(childProps, "renderFunc", (_args, ret1) => {
      if (!ret1 || typeof ret1 !== "object") return ret1;
      const ret1Map = ret1 as Record<string, unknown>;
      const contentNode = ret1Map.props as Record<string, unknown> | undefined;
      const primaryOverview = ((contentNode?.children as Record<string, unknown> | undefined)?.props as Record<string, unknown> | undefined)
        ?.overview as Record<string, unknown> | undefined;
      const fallbackOverview = resolveLibraryOverviewNode(ret1Map);
      const overviewNode = primaryOverview || fallbackOverview;
      const gameTitle = String(
        overviewNode?.display_name || overviewNode?.name || overviewNode?.app_name || overviewNode?.title || "",
      ).trim();
      const appId = Math.max(
        0,
        Number(
          overviewNode?.appid ??
            overviewNode?.appId ??
            overviewNode?.unAppID ??
            overviewNode?.nAppID ??
            overviewNode?.m_unAppID ??
            overviewNode?.m_nAppID ??
            0,
        ),
      );
      if (!appId) return ret1;

      const nodeWithType = (contentNode?.children as Record<string, unknown> | undefined) || null;
      const wrappedType = wrapReactType(nodeWithType, "type");
      if (!wrappedType) return ret1;
      const typeFn = wrappedType.type;
      if (typeof typeFn !== "function") return ret1;
      const typeState = typeFn as unknown as Record<string, unknown>;
      typeState.__FREDECK_LIBRARY_APP_ID = appId;
      typeState.__FREDECK_LIBRARY_GAME_TITLE = gameTitle;
      if (Boolean(typeState.__FREDECK_LIBRARY_TYPE_PATCHED)) return ret1;

      const typePatch = afterPatch(wrappedType, "type", (_innerArgs, ret2) => {
        if (!ret2 || typeof ret2 !== "object") return ret2;
        const dynamicType = wrappedType.type as Record<string, unknown>;
        const runtimeAppId = Math.max(0, Number(dynamicType.__FREDECK_LIBRARY_APP_ID || appId));
        const runtimeTitle = String(dynamicType.__FREDECK_LIBRARY_GAME_TITLE || gameTitle).trim();
        if (!runtimeAppId) return ret2;
        const nextComponent = (
          <LibraryTimeBlock key={`freedeckcy-library-times-${runtimeAppId}`} appId={runtimeAppId} title={runtimeTitle} />
        );

        const overlayHost = resolveLibraryOverlayHost(ret2);
        if (overlayHost) {
          const hostChildren = ensureNodeChildrenArray(overlayHost);
          const hostProps = (overlayHost.props as Record<string, unknown> | undefined) || {};
          overlayHost.props = hostProps;
          const currentStyle = hostProps.style;
          if (!currentStyle || typeof currentStyle !== "object") {
            hostProps.style = { position: "relative" };
          } else {
            const styleMap = currentStyle as Record<string, unknown>;
            if (!styleMap.position) {
              hostProps.style = { ...styleMap, position: "relative" };
            }
          }

          const existingInHost = hostChildren.findIndex((child) => isLibraryTimeNode(child));
          if (existingInHost >= 0) {
            hostChildren.splice(existingInHost, 1, nextComponent);
          } else {
            hostChildren.push(nextComponent);
          }
          return ret2;
        }

        const spliceTarget = resolveSpliceTarget(ret2);
        if (!spliceTarget) return ret2;
        const existingInFallback = spliceTarget.findIndex((child) => isLibraryTimeNode(child));
        if (existingInFallback >= 0) {
          spliceTarget.splice(existingInFallback, 1, nextComponent);
          return ret2;
        }

        const insertIndex = resolveLibraryInsertIndex(spliceTarget);
        spliceTarget.splice(insertIndex, 0, nextComponent);
        return ret2;
      });

      const patchedType = wrappedType.type as Record<string, unknown>;
      patchedType.__FREDECK_LIBRARY_TYPE_PATCHED = true;
      patchedType.__FREDECK_LIBRARY_APP_ID = appId;
      patchedType.__FREDECK_LIBRARY_GAME_TITLE = gameTitle;
      patchedType.__FREDECK_LIBRARY_TYPE_UNPATCH = typePatch.unpatch;
      return ret1;
    });

    const patchedRender = childProps.renderFunc as Record<string, unknown>;
    patchedRender.__FREDECK_LIBRARY_RENDER_PATCHED = true;
    patchedRender.__FREDECK_LIBRARY_RENDER_UNPATCH = renderPatch.unpatch;
    return props;
  };

  const patchHandle = hookApi.addPatch("/library/app/:appid", patchFn);
  return () => {
    try {
      hookApi.removePatch?.("/library/app/:appid", patchHandle);
    } catch {
      // 忽略移除 patch 异常。
    }
  };
}

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number, timeoutMessage: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
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

async function pickFolder(startPath: string): Promise<string> {
  const base = String(startPath || "/home/deck").trim() || "/home/deck";
  const result = await openFilePicker(FileSelectionType.FOLDER, base, false, true);
  return String(result?.realpath || result?.path || "").trim();
}

function isTaskAlreadyInstalled(task: TaskItem): boolean {
  const installStatus = String(task.install_status || "").trim().toLowerCase();
  if (installStatus === "installed") return true;
  const downloadStatus = String(task.status || "").trim().toLowerCase();
  if (downloadStatus === "complete" && String(task.installed_path || "").trim()) return true;
  return false;
}

function isTaskActive(task: TaskItem): boolean {
  const status = String(task.status || "").trim().toLowerCase();
  if (!status) return false;
  return !["complete", "error", "removed", "paused"].includes(status);
}

function countActiveTasks(tasks: TaskItem[]): number {
  let count = 0;
  for (const task of tasks || []) {
    if (isTaskActive(task)) count += 1;
  }
  return count;
}

function resolvePanelPollMode(state: PanelState): PanelPollMode {
  const visible = !document.hidden;
  if (!visible) return PANEL_POLL_MODE_BACKGROUND;
  return countActiveTasks(state.tasks || []) > 0 ? PANEL_POLL_MODE_ACTIVE : PANEL_POLL_MODE_IDLE;
}

function pollIntervalByMode(mode: PanelPollMode): number {
  if (mode === PANEL_POLL_MODE_ACTIVE) return PANEL_ACTIVE_POLL_MS;
  if (mode === PANEL_POLL_MODE_BACKGROUND) return PANEL_BACKGROUND_POLL_MS;
  return PANEL_IDLE_POLL_MS;
}

function SettingsPage() {
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [clearingLogin, setClearingLogin] = useState<boolean>(false);
  const [scanningInstalled, setScanningInstalled] = useState<boolean>(false);
  const [diagnosticsReport, setDiagnosticsReport] = useState<DiagnosticsReport | null>(null);
  const [diagnosticsBusy, setDiagnosticsBusy] = useState<boolean>(false);
  const [diagnosticsExportBusy, setDiagnosticsExportBusy] = useState<boolean>(false);
  const [diagnosticsExportMessage, setDiagnosticsExportMessage] = useState<string>("");
  const [diagnosticsError, setDiagnosticsError] = useState<string>("");
  const [activeTab, setActiveTab] = useState<string>("paths");
  const [settings, setSettings] = useState<SettingsState>(EMPTY_SETTINGS);
  const [storageOptions, setStorageOptions] = useState<StorageOption[]>([]);
  const [login, setLogin] = useState<LoginState>(EMPTY_STATE.login);
  const [baiduWebLogin, setBaiduWebLogin] = useState<BaiduWebLoginState>(EMPTY_BAIDU_WEB_STATE);
  const [baiduQr, setBaiduQr] = useState<BaiduQrState>({ stage: "idle" });
  const [baiduQrBusy, setBaiduQrBusy] = useState<boolean>(false);
  const baiduQrPollBusyRef = useRef<boolean>(false);
  const baiduQrPollFailuresRef = useRef<number>(0);
  const [baiduLogin, setBaiduLogin] = useState<BaiduOpenApiLoginState>(EMPTY_BAIDU_OPENAPI_STATE);
  const [baiduAppKey, setBaiduAppKey] = useState<string>("");
  const [baiduSecretKey, setBaiduSecretKey] = useState<string>("");
  const [baiduAuthCode, setBaiduAuthCode] = useState<string>("");
  const [baiduBusy, setBaiduBusy] = useState<boolean>(false);
  const [cloudSaveUploadState, setCloudSaveUploadState] = useState<CloudSaveUploadState>(EMPTY_CLOUD_SAVE_STATE);
  const [cloudSaveRestoreState, setCloudSaveRestoreState] = useState<CloudSaveRestoreState>(EMPTY_CLOUD_SAVE_RESTORE_STATE);
  const [startingCloudSaveUpload, setStartingCloudSaveUpload] = useState<boolean>(false);
  const [loadingRestoreOptions, setLoadingRestoreOptions] = useState<boolean>(false);
  const [loadingRestoreEntries, setLoadingRestoreEntries] = useState<boolean>(false);
  const [planningRestore, setPlanningRestore] = useState<boolean>(false);
  const [applyingRestore, setApplyingRestore] = useState<boolean>(false);
  const [restoreOptions, setRestoreOptions] = useState<CloudSaveRestoreGameOption[]>([]);
  const [selectedRestoreGameKey, setSelectedRestoreGameKey] = useState<string>("");
  const [selectedRestoreVersion, setSelectedRestoreVersion] = useState<string>("");
  const [restoreEntries, setRestoreEntries] = useState<CloudSaveRestoreEntry[]>([]);
  const [selectedRestoreEntryIds, setSelectedRestoreEntryIds] = useState<string[]>([]);
  const [targetCandidates, setTargetCandidates] = useState<string[]>([]);
  const [selectedRestoreTargetDir, setSelectedRestoreTargetDir] = useState<string>("");
  const [splitDraft, setSplitDraft] = useState<number>(16);
  const settingsContainerRef = useRef<HTMLDivElement | null>(null);
  const tabStabilityCss = useMemo(
    () => `
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
    `,
    [],
  );
  const selectedRestoreGame = useMemo(
    () => restoreOptions.find((item) => item.game_key === selectedRestoreGameKey) || null,
    [restoreOptions, selectedRestoreGameKey],
  );
  const restoreVersionOptions = useMemo(
    () => (selectedRestoreGame?.versions || []).map((item) => ({
      data: item.version_name,
      label: `${item.display_time || item.version_name} | ${formatBytes(item.size_bytes)}`,
    })),
    [selectedRestoreGame],
  );

  useEffect(() => {
    const classMap = getGamepadTabClassMap();
    if (!classMap) return;
    const styleId = "freedeckcy-settings-tabs-no-jitter";
    if (document.getElementById(styleId)) return;
    const style = document.createElement("style");
    style.id = styleId;
    const rules: string[] = [];
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

  useEffect(() => {
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

  useEffect(() => {
    if (!selectedRestoreGame) {
      setSelectedRestoreVersion("");
      return;
    }
    const exists = selectedRestoreGame.versions.some((item) => item.version_name === selectedRestoreVersion);
    if (!exists) {
      setSelectedRestoreVersion(String(selectedRestoreGame.versions[0]?.version_name || ""));
    }
  }, [selectedRestoreGame, selectedRestoreVersion]);

  useEffect(() => {
    setRestoreEntries([]);
    setSelectedRestoreEntryIds([]);
    setTargetCandidates([]);
    setSelectedRestoreTargetDir("");
  }, [selectedRestoreGameKey, selectedRestoreVersion]);

  const refreshStorageOptions = useCallback(async () => {
    try {
      const result = await withTimeout(getTianyiStorageOptions(), 10000, "读取存储信息超时");
      if (result.status === "success" && result.data) {
        setStorageOptions(Array.isArray(result.data.options) ? result.data.options : []);
      }
    } catch {
      // 静默：没有 SD 卡/挂载信息时不影响设置页。
    }
  }, []);

  const refreshSettings = useCallback(async () => {
    const result = await withTimeout(
      getTianyiPanelState(),
      PANEL_REQUEST_TIMEOUT_MS,
      "读取设置超时，请稍后重试",
    );
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

  const refreshCloudSaveUploadStatus = useCallback(async () => {
    const result = await withTimeout(getTianyiCloudSaveUploadStatus(), 10000, "读取云存档状态超时");
    if (result.status !== "success") {
      throw new Error(result.message || "读取云存档状态失败");
    }
    const nextState = normalizeCloudSaveUploadState(result.data?.state);
    setCloudSaveUploadState(nextState);
  }, []);

  const refreshCloudSaveRestoreStatus = useCallback(async () => {
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

  const refreshRestoreOptions = useCallback(async () => {
    if (loadingRestoreOptions) return;
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
    } catch (error) {
      toastError(error);
    } finally {
      setLoadingRestoreOptions(false);
    }
  }, [loadingRestoreOptions, selectedRestoreGameKey]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        await refreshSettings();
        await refreshCloudSaveUploadStatus();
        await refreshCloudSaveRestoreStatus();
      } catch (error) {
        if (alive) toastError(error);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [refreshSettings, refreshCloudSaveRestoreStatus, refreshCloudSaveUploadStatus]);

  useEffect(() => {
    if (!cloudSaveUploadState.running) return;
    let alive = true;
    let timer = 0;
    const poll = async () => {
      if (!alive) return;
      try {
        await refreshCloudSaveUploadStatus();
      } catch {
        // 轮询失败时保留当前状态，避免干扰 UI。
      } finally {
        if (alive) timer = window.setTimeout(poll, 1200);
      }
    };
    timer = window.setTimeout(poll, 1200);
    return () => {
      alive = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [cloudSaveUploadState.running, refreshCloudSaveUploadStatus]);

  useEffect(() => {
    if (!cloudSaveRestoreState.running) return;
    let alive = true;
    let timer = 0;
    const poll = async () => {
      if (!alive) return;
      try {
        await refreshCloudSaveRestoreStatus();
      } catch {
        // 轮询失败时保留当前状态，避免干扰 UI。
      } finally {
        if (alive) timer = window.setTimeout(poll, 1200);
      }
    };
    timer = window.setTimeout(poll, 1200);
    return () => {
      alive = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [cloudSaveRestoreState.running, refreshCloudSaveRestoreStatus]);

  const savePatch = useCallback(
    async (patch: Partial<SettingsState>, successMessage = "设置已保存") => {
      if (saving) return;
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
      } catch (error) {
        toastError(error);
      } finally {
        setSaving(false);
      }
    },
    [saving, settings],
  );

  const onPickDownloadDir = useCallback(async () => {
    try {
      const selected = await pickFolder(settings.download_dir || "/home/deck");
      if (!selected) return;
      await savePatch({ download_dir: selected }, `下载目录已更新：${selected}`);
    } catch (error) {
      toaster.toast({ title: "freedeckCY", body: `选择下载目录失败：${errorText(error)}` });
    }
  }, [savePatch, settings.download_dir]);

  const onPickInstallDir = useCallback(async () => {
    try {
      const selected = await pickFolder(settings.install_dir || settings.download_dir || "/home/deck");
      if (!selected) return;
      await savePatch({ install_dir: selected }, `安装目录已更新：${selected}`);
    } catch (error) {
      toaster.toast({ title: "freedeckCY", body: `选择安装目录失败：${errorText(error)}` });
    }
  }, [savePatch, settings.download_dir, settings.install_dir]);

  const onSaveSplit = useCallback(async () => {
    const value = Number(splitDraft);
    if (!Number.isFinite(value) || value < 1 || value > 64) {
      toaster.toast({ title: "freedeckCY", body: "分片数必须在 1 到 64 之间" });
      return;
    }
    await savePatch({ split_count: value }, "下载参数已更新");
  }, [savePatch, splitDraft]);

  useEffect(() => {
    void refreshStorageOptions();
  }, [refreshStorageOptions]);

  const onUseStorage = useCallback(
    async (option: StorageOption, field: "download_dir" | "install_dir") => {
      const value = field === "download_dir" ? option.download_dir : option.install_dir;
      await savePatch({ [field]: value }, `${field === "download_dir" ? "下载" : "安装"}目录已切换到：${value}`);
      await refreshStorageOptions();
    },
    [refreshStorageOptions, savePatch],
  );

  const onClearLogin = useCallback(async () => {
    if (clearingLogin) return;
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
    } catch (error) {
      toastError(error);
    } finally {
      setClearingLogin(false);
    }
  }, [clearingLogin, refreshCloudSaveRestoreStatus, refreshCloudSaveUploadStatus, refreshSettings]);

  useEffect(() => {
    if (baiduQr.stage !== "waiting" && baiduQr.stage !== "scanned") return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      if (cancelled || baiduQrPollBusyRef.current) return;
      baiduQrPollBusyRef.current = true;
      try {
        const result = await withTimeout(
          pollBaiduQrLogin(),
          15000,
          "轮询百度扫码状态超时",
        );
        if (cancelled) return;
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
          } catch {
            // 登录成功优先，设置刷新失败不覆盖成功状态。
          }
          // 成功后收起二维码会话，避免「已登录」还停留在扫码成功状态。
          if (!cancelled) setBaiduQr({ stage: "idle" });
        }
      } catch (error) {
        baiduQrPollFailuresRef.current += 1;
        if (baiduQrPollFailuresRef.current >= 3 && !cancelled) {
          setBaiduQr({
            stage: "failed",
            message: `扫码状态连续失败：${errorText(error)}`,
          });
        }
      } finally {
        baiduQrPollBusyRef.current = false;
      }
    }, Math.max(5, Number(baiduQr.interval || 5)) * 1000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [baiduQr.stage, baiduQr.interval, refreshSettings]);

  const onStartBaiduQr = useCallback(async () => {
    if (baiduQrBusy) return;
    baiduQrPollFailuresRef.current = 0;
    setBaiduQrBusy(true);
    setBaiduQr({ stage: "starting" });
    toaster.toast({ title: "freedeckCY", body: "正在获取百度二维码..." });
    try {
      const result = await withTimeout(
        startBaiduQrLogin(),
        25000,
        "获取百度二维码超时（网络/TLS 可能受阻，请稍后重试或运行诊断）",
      );
      if (result.status !== "success" || !result.data) {
        throw new Error(result.message || "获取百度二维码失败");
      }
      if (!result.data.qr_data_url && !result.data.qrcode_url) {
        throw new Error("百度二维码为空");
      }
      setBaiduQr(result.data);
    } catch (error) {
      // 失败也要落到 failed，避免 UI 停留在上一轮的二维码/过期提示里没有反馈。
      const message = errorText(error);
      setBaiduQr({ stage: "failed", message });
      toaster.toast({ title: "freedeckCY", body: message });
    } finally {
      setBaiduQrBusy(false);
    }
  }, [baiduQrBusy]);

  const onCancelBaiduQr = useCallback(async () => {
    try {
      await cancelBaiduQrLogin();
    } catch {
      // 忽略取消失败。
    }
    setBaiduQr({ stage: "idle" });
  }, []);

  const onClearBaiduWeb = useCallback(async () => {
    if (baiduQrBusy) return;
    setBaiduQrBusy(true);
    try {
      const result = await withTimeout(clearBaiduLogin(), 15000, "退出百度网盘超时");
      if (result.status !== "success") throw new Error(result.message || "退出百度网盘失败");
      setBaiduWebLogin(result.data || EMPTY_BAIDU_WEB_STATE);
      setBaiduQr({ stage: "idle" });
      toaster.toast({ title: "freedeckCY", body: "已退出百度网盘" });
    } catch (error) {
      toastError(error);
    } finally {
      setBaiduQrBusy(false);
    }
  }, [baiduQrBusy]);

  const onRunDiagnostics = useCallback(async () => {
    if (diagnosticsBusy) return;
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
    } catch (error) {
      // 自检失败时把原因留在页面上，toast 消失后仍能看到。
      const message = errorText(error);
      setDiagnosticsError(message);
      toaster.toast({ title: "freedeckCY", body: message });
    } finally {
      setDiagnosticsBusy(false);
    }
  }, [diagnosticsBusy]);

  const onExportDiagnostics = useCallback(async () => {
    if (diagnosticsExportBusy) return;
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
    } catch (error) {
      const message = errorText(error);
      setDiagnosticsExportMessage(`导出失败：${message}`);
      toaster.toast({ title: "freedeckCY", body: message });
    } finally {
      setDiagnosticsExportBusy(false);
    }
  }, [diagnosticsExportBusy]);

  const onScanInstalledSettings = useCallback(async () => {
    if (scanningInstalled) return;
    setScanningInstalled(true);
    try {
      const result = await withTimeout(scanTianyiInstalledGames(), 90000, "扫描已安装游戏超时");
      if (result.status !== "success") {
        throw new Error(result.message || "扫描已安装游戏失败");
      }
      const data = (result.data || {}) as Record<string, unknown>;
      const message = String(data.message || "扫描完成");
      const steamAdded = (Array.isArray(data.added_games)
        ? (data.added_games as Record<string, unknown>[]).filter((item) => Boolean(item.steam_added)).length
        : 0) + Number(data.steam_recovered_count || 0);
      toaster.toast({
        title: "freedeckCY",
        body: `${message}${steamAdded ? `（自动加入 Steam：${steamAdded}）` : ""}`,
      });
    } catch (error) {
      toastError(error);
    } finally {
      setScanningInstalled(false);
    }
  }, [scanningInstalled]);

  const onSaveBaiduApp = useCallback(async () => {
    if (baiduBusy) return;
    setBaiduBusy(true);
    try {
      const result = await withTimeout(
        setBaiduOpenapiApp({ app_key: baiduAppKey, secret_key: baiduSecretKey }),
        15000,
        "保存百度应用超时",
      );
      if (result.status !== "success") throw new Error(result.message || "保存百度应用失败");
      setBaiduLogin(result.data || EMPTY_BAIDU_OPENAPI_STATE);
      toaster.toast({ title: "freedeckCY", body: "百度开放平台应用已保存" });
    } catch (error) {
      toastError(error);
    } finally {
      setBaiduBusy(false);
    }
  }, [baiduAppKey, baiduBusy, baiduSecretKey]);

  const onBaiduAuthorize = useCallback(async () => {
    if (baiduBusy) return;
    setBaiduBusy(true);
    try {
      const result = await withTimeout(getBaiduOpenapiAuthorizeUrl(), 15000, "获取百度授权链接超时");
      if (result.status !== "success") throw new Error(result.message || "获取百度授权链接失败");
      const url = String(result.url || result.data?.url || "");
      if (!url) throw new Error("百度授权链接为空");
      openExternalUrl(url);
    } catch (error) {
      toastError(error);
    } finally {
      setBaiduBusy(false);
    }
  }, [baiduBusy]);

  const onExchangeBaiduCode = useCallback(async () => {
    if (baiduBusy) return;
    setBaiduBusy(true);
    try {
      const result = await withTimeout(
        exchangeBaiduOpenapiCode({ code: baiduAuthCode }),
        20000,
        "百度授权超时",
      );
      if (result.status !== "success") throw new Error(result.message || "百度授权失败");
      setBaiduLogin(result.data || EMPTY_BAIDU_OPENAPI_STATE);
      setBaiduAuthCode("");
      toaster.toast({ title: "freedeckCY", body: "百度网盘授权成功" });
    } catch (error) {
      toastError(error);
    } finally {
      setBaiduBusy(false);
    }
  }, [baiduAuthCode, baiduBusy]);

  const onClearBaiduLogin = useCallback(async () => {
    if (baiduBusy) return;
    setBaiduBusy(true);
    try {
      const result = await withTimeout(clearBaiduOpenapiLogin(), 15000, "清除百度授权超时");
      if (result.status !== "success") throw new Error(result.message || "清除百度授权失败");
      setBaiduLogin(result.data || EMPTY_BAIDU_OPENAPI_STATE);
      toaster.toast({ title: "freedeckCY", body: "已清除百度网盘授权" });
    } catch (error) {
      toastError(error);
    } finally {
      setBaiduBusy(false);
    }
  }, [baiduBusy]);

  const onStartCloudSaveUpload = useCallback(async () => {
    if (startingCloudSaveUpload) return;
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
    } catch (error) {
      toastError(error);
    } finally {
      setStartingCloudSaveUpload(false);
    }
  }, [refreshCloudSaveUploadStatus, startingCloudSaveUpload]);

  const onLoadRestoreEntries = useCallback(async () => {
    if (loadingRestoreEntries) return;
    if (!selectedRestoreGame || !selectedRestoreVersion) {
      toaster.toast({ title: "freedeckCY", body: "请先选择游戏和版本" });
      return;
    }
    setLoadingRestoreEntries(true);
    try {
      const result = await withTimeout(
        listTianyiCloudSaveRestoreEntries({
          game_id: String(selectedRestoreGame.game_id || ""),
          game_key: String(selectedRestoreGame.game_key || ""),
          game_title: String(selectedRestoreGame.game_title || ""),
          version_name: String(selectedRestoreVersion || ""),
        }),
        25000,
        "读取可选存档项超时",
      );
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
    } catch (error) {
      toastError(error);
    } finally {
      setLoadingRestoreEntries(false);
    }
  }, [loadingRestoreEntries, refreshCloudSaveRestoreStatus, selectedRestoreGame, selectedRestoreVersion]);

  const toggleRestoreEntry = useCallback((entryId: string, checked: boolean) => {
    const id = String(entryId || "").trim();
    if (!id) return;
    setSelectedRestoreEntryIds((prev) => {
      const set = new Set(prev.map((item) => String(item || "").trim()).filter(Boolean));
      if (checked) set.add(id);
      else set.delete(id);
      return Array.from(set);
    });
  }, []);

  const runRestoreApply = useCallback(
    async (planId: string, confirmOverwrite: boolean) => {
      const normalizedPlanId = String(planId || "").trim();
      if (!normalizedPlanId) return;
      setApplyingRestore(true);
      try {
        const result = await withTimeout(
          applyTianyiCloudSaveRestore({
            plan_id: normalizedPlanId,
            confirm_overwrite: Boolean(confirmOverwrite),
          }),
          120000,
          "执行恢复超时",
        );
        if (result.status !== "success" || !result.data) {
          throw new Error(result.message || "执行恢复失败");
        }
        toaster.toast({ title: "freedeckCY", body: String(result.data.message || "恢复流程已结束") });
      } catch (error) {
        toastError(error);
      } finally {
        setApplyingRestore(false);
        try {
          await refreshCloudSaveRestoreStatus();
        } catch {
          // 恢复已执行；状态刷新失败不向上抛出，避免未处理的 Promise 拒绝。
        }
      }
    },
    [refreshCloudSaveRestoreStatus],
  );

  const onStartCloudSaveRestore = useCallback(async () => {
    if (planningRestore || applyingRestore) return;
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
      const result = await withTimeout(
        planTianyiCloudSaveRestore({
          game_id: String(selectedRestoreGame.game_id || ""),
          game_key: String(selectedRestoreGame.game_key || ""),
          game_title: String(selectedRestoreGame.game_title || ""),
          version_name: String(selectedRestoreVersion || ""),
          selected_entry_ids: selectedRestoreEntryIds,
          target_dir: String(selectedRestoreTargetDir || ""),
        }),
        30000,
        "生成恢复计划超时",
      );
      if (result.status !== "success" || !result.data) {
        throw new Error(result.message || "生成恢复计划失败");
      }

      const plan = result.data;
      const nextCandidates = Array.isArray(plan.target_candidates) ? plan.target_candidates : [];
      setTargetCandidates(nextCandidates);
      if (nextCandidates.length === 1) {
        setSelectedRestoreTargetDir(nextCandidates[0]);
      } else if (nextCandidates.length > 1 && !selectedRestoreTargetDir) {
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
        showModal(
          <ConfirmModal
            strTitle="确认覆盖存档"
            strDescription={
              `检测到 ${Number(plan.conflict_count || 0)} 个冲突文件，确认后会覆盖原有存档。` +
              (samples.length ? `\n\n示例：\n${samples.join("\n")}` : "")
            }
            strOKButtonText="确认覆盖"
            strCancelButtonText="取消"
            onOK={() => {
              void runRestoreApply(planId, true);
            }}
            onCancel={() => {
              void runRestoreApply(planId, false);
            }}
          />,
        );
      } else {
        await runRestoreApply(planId, false);
      }
      await refreshCloudSaveRestoreStatus();
    } catch (error) {
      toastError(error);
    } finally {
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

  const cloudSaveSummaryText = useMemo(() => {
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

  const cloudSaveRestoreSummaryText = useMemo(() => {
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

  const restoreGameOptions = useMemo(
    () =>
      restoreOptions.map((item) => ({
        data: item.game_key,
        label: item.available
          ? `${item.game_title}（${item.versions.length} 个版本）`
          : `${item.game_title}（不可恢复：${item.reason || "无可用版本"}）`,
      })),
    [restoreOptions],
  );

  const restoreBusy =
    saving ||
    clearingLogin ||
    loadingRestoreOptions ||
    loadingRestoreEntries ||
    planningRestore ||
    applyingRestore ||
    cloudSaveRestoreState.running;

  const tabs = useMemo(
    () => [
      {
        id: "paths",
        title: "路径",
        content: (
          <>
            <PanelSection title="下载目录">
              <PanelSectionRow>
                <div style={{ fontSize: "12px", lineHeight: 1.5 }}>{settings.download_dir || "未设置"}</div>
              </PanelSectionRow>
              <PanelSectionRow>
                <ButtonItem layout="below" onClick={onPickDownloadDir} disabled={saving}>
                  选择下载目录
                </ButtonItem>
              </PanelSectionRow>
              {storageOptions.filter((item) => item.kind === "external").map((item) => (
                <PanelSectionRow key={`download-${item.mount}`}>
                  <ButtonItem
                    layout="below"
                    onClick={() => void onUseStorage(item, "download_dir")}
                    disabled={saving}
                  >
                    下载到 {item.label}（剩余 {item.free_text}）
                  </ButtonItem>
                </PanelSectionRow>
              ))}
              {!storageOptions.some((item) => item.kind === "external") ? (
                <PanelSectionRow>
                  <div style={{ fontSize: "11px", opacity: 0.75 }}>未检测到可写 SD 卡/外置存储（请先在 SteamOS/系统中挂载）</div>
                </PanelSectionRow>
              ) : null}
            </PanelSection>
            <PanelSection title="安装目录">
              <PanelSectionRow>
                <div style={{ fontSize: "12px", lineHeight: 1.5 }}>{settings.install_dir || "未设置"}</div>
              </PanelSectionRow>
              <PanelSectionRow>
                <ButtonItem layout="below" onClick={onPickInstallDir} disabled={saving}>
                  选择安装目录
                </ButtonItem>
              </PanelSectionRow>
              {storageOptions.filter((item) => item.kind === "external").map((item) => (
                <PanelSectionRow key={`install-${item.mount}`}>
                  <ButtonItem
                    layout="below"
                    onClick={() => void onUseStorage(item, "install_dir")}
                    disabled={saving}
                  >
                    安装到 {item.label}（剩余 {item.free_text}）
                  </ButtonItem>
                </PanelSectionRow>
              ))}
            </PanelSection>
          </>
        ),
      },
      {
        id: "install",
        title: "安装",
        content: (
          <>
          <PanelSection title="安装行为">
            <PanelSectionRow>
              <ToggleField
                label="安装后自动删除压缩包"
                description="仅在自动安装成功后生效"
                checked={Boolean(settings.auto_delete_package)}
                onChange={(value: boolean) => savePatch({ auto_delete_package: value })}
                disabled={saving}
              />
            </PanelSectionRow>
            <PanelSectionRow>
              <div style={{ fontSize: "12px", lineHeight: 1.5, opacity: 0.86 }}>
                下载完成后自动安装已固定开启。
              </div>
            </PanelSectionRow>
          </PanelSection>
          <PanelSection title="扫描已安装">
            <PanelSectionRow>
              <div style={{ fontSize: "12px", lineHeight: 1.5, opacity: 0.86 }}>
                扫描设置里的安装目录一层，把目录名匹配标题的游戏补回列表；Steam 里没有的会自动创建快捷方式。
              </div>
            </PanelSectionRow>
            <PanelSectionRow>
              <ButtonItem layout="below" onClick={onScanInstalledSettings} disabled={scanningInstalled || saving}>
                {scanningInstalled ? "扫描中..." : "扫描已安装游戏"}
              </ButtonItem>
            </PanelSectionRow>
          </PanelSection>
          </>
        ),
      },
      {
        id: "download",
        title: "下载",
        content: (
          <PanelSection title="下载参数">
            <PanelSectionRow>
              <SliderField
                label="aria2 分片数"
                description="建议 8~32，范围 1~64"
                value={Math.max(1, Math.min(64, Number(splitDraft || 16)))}
                min={1}
                max={64}
                step={1}
                showValue
                editableValue
                onChange={(value: number) => setSplitDraft(Math.max(1, Math.min(64, Number(value || 1))))}
                disabled={saving}
              />
            </PanelSectionRow>
            <PanelSectionRow>
              <DropdownItem
                label="分页数量"
                description="游戏列表每页显示条数"
                rgOptions={PAGE_SIZE_OPTIONS}
                selectedOption={Math.max(10, Math.min(200, Number(settings.page_size || 50)))}
                disabled={saving}
                onChange={(option) => {
                  const nextValue = Math.max(10, Math.min(200, Number(option?.data || 50)));
                  if (nextValue === Number(settings.page_size || 50)) return;
                  void savePatch({ page_size: nextValue }, `分页数量已更新：${nextValue} / 页`);
                }}
              />
            </PanelSectionRow>
            <PanelSectionRow>
              <ButtonItem layout="below" onClick={onSaveSplit} disabled={saving}>
                保存下载参数
              </ButtonItem>
            </PanelSectionRow>
          </PanelSection>
        ),
      },
      {
        id: "account",
        title: "账号",
        content: (
          <>
            <PanelSection title="天翼云账号">
              <PanelSectionRow>
                <div style={{ fontSize: "12px", lineHeight: 1.5 }}>
                  {login.logged_in
                    ? `当前已登录：${login.user_account || "未知账号"}`
                    : "当前未登录"}
                </div>
              </PanelSectionRow>
              <PanelSectionRow>
                <ButtonItem
                  layout="below"
                  onClick={onClearLogin}
                  disabled={clearingLogin || saving || !login.logged_in}
                >
                  {clearingLogin ? "注销中..." : "注销天翼云账号"}
                </ButtonItem>
              </PanelSectionRow>
            </PanelSection>

            <PanelSection title="百度网盘（扫码登录）">
              <PanelSectionRow>
                <div style={{ fontSize: "12px", lineHeight: 1.5 }}>
                  {baiduWebLogin.logged_in
                    ? `已登录：${baiduWebLogin.user_account || "百度账号"}`
                    : "未登录（扫码后使用 BDUSS/Cookie，无需开放平台 App Key）"}
                </div>
              </PanelSectionRow>
              {baiduQr.stage === "failed" || baiduQr.stage === "expired" ? (
                <PanelSectionRow>
                  <div style={{ fontSize: "12px", color: "#ffb4a8", lineHeight: 1.5 }}>
                    {baiduQr.message || "扫码失败，请重试"}
                  </div>
                </PanelSectionRow>
              ) : null}
              {baiduQr.stage === "waiting" || baiduQr.stage === "scanned" ? (
                <PanelSectionRow>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "center" }}>
                    {baiduQr.qr_data_url ? (
                      <img
                        src={baiduQr.qr_data_url}
                        alt="百度扫码登录"
                        style={{ width: "180px", height: "180px", background: "#fff", padding: "8px", borderRadius: "8px" }}
                      />
                    ) : (
                      <div style={{ fontSize: "12px" }}>
                        二维码图片加载失败，请打开：
                        <div style={{ wordBreak: "break-all" }}>{baiduQr.qrcode_url}</div>
                      </div>
                    )}
                    <div style={{ fontSize: "12px" }}>{baiduQr.message || "请用百度 App 扫码"}</div>
                    <ButtonItem layout="below" onClick={onCancelBaiduQr}>
                      取消扫码
                    </ButtonItem>
                  </div>
                </PanelSectionRow>
              ) : (
                <PanelSectionRow>
                  <ButtonItem layout="below" onClick={onStartBaiduQr} disabled={baiduQrBusy}>
                    {baiduQrBusy ? "获取中..." : "扫码登录百度网盘"}
                  </ButtonItem>
                </PanelSectionRow>
              )}
              <PanelSectionRow>
                <ButtonItem layout="below" onClick={onClearBaiduWeb} disabled={baiduQrBusy || !baiduWebLogin.logged_in}>
                  退出百度网盘
                </ButtonItem>
              </PanelSectionRow>
            </PanelSection>

            <PanelSection title="百度网盘 OpenAPI（可选，需开发者资质）">
              <PanelSectionRow>
                <div style={{ fontSize: "12px", lineHeight: 1.5 }}>
                  {baiduLogin.logged_in
                    ? `已授权：${baiduLogin.user_account || "百度账号"}`
                    : baiduLogin.configured
                      ? "已配置应用，待授权"
                      : "未配置（去百度网盘开放平台创建应用）"}
                </div>
              </PanelSectionRow>
              <PanelSectionRow>
                <TextField
                  label="App Key"
                  value={baiduAppKey}
                  onChange={(event) => setBaiduAppKey(getTextFieldValue(event))}
                />
              </PanelSectionRow>
              <PanelSectionRow>
                <TextField
                  label="Secret Key"
                  value={baiduSecretKey}
                  bIsPassword={true}
                  onChange={(event) => setBaiduSecretKey(getTextFieldValue(event))}
                />
              </PanelSectionRow>
              <PanelSectionRow>
                <ButtonItem layout="below" onClick={onSaveBaiduApp} disabled={baiduBusy}>
                  保存应用
                </ButtonItem>
              </PanelSectionRow>
              <PanelSectionRow>
                <ButtonItem layout="below" onClick={onBaiduAuthorize} disabled={baiduBusy || !baiduLogin.configured}>
                  获取授权链接
                </ButtonItem>
              </PanelSectionRow>
              <PanelSectionRow>
                <TextField
                  label="授权码"
                  description="粘贴百度返回的授权码"
                  value={baiduAuthCode}
                  onChange={(event) => setBaiduAuthCode(getTextFieldValue(event))}
                />
              </PanelSectionRow>
              <PanelSectionRow>
                <ButtonItem layout="below" onClick={onExchangeBaiduCode} disabled={baiduBusy || !baiduAuthCode.trim()}>
                  完成授权
                </ButtonItem>
              </PanelSectionRow>
              <PanelSectionRow>
                <ButtonItem layout="below" onClick={onClearBaiduLogin} disabled={baiduBusy || !baiduLogin.logged_in}>
                  清除百度授权
                </ButtonItem>
              </PanelSectionRow>
            </PanelSection>

            <PanelSection title="云存档上传">
              <PanelSectionRow>
                <ToggleField
                  label="游戏退出后自动上传"
                  description="后台检测游戏进程，退出后自动打包上传；默认开启"
                  checked={Boolean(settings.cloud_save_auto_upload)}
                  onChange={(value: boolean) => savePatch({ cloud_save_auto_upload: value })}
                  disabled={saving}
                />
              </PanelSectionRow>
              <PanelSectionRow>
                <ToggleField
                  label="包含模拟器存档"
                  description="GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch 的存档与记忆卡"
                  checked={Boolean(settings.cloud_save_include_emulators)}
                  onChange={(value: boolean) => savePatch({ cloud_save_include_emulators: value })}
                  disabled={saving}
                />
              </PanelSectionRow>
              <PanelSectionRow>
                <ButtonItem
                  layout="below"
                  onClick={onStartCloudSaveUpload}
                  disabled={saving || clearingLogin || startingCloudSaveUpload || !login.logged_in || cloudSaveUploadState.running}
                >
                  {startingCloudSaveUpload
                    ? "启动中..."
                    : cloudSaveUploadState.running
                      ? "上传进行中..."
                      : "上传云存档"}
                </ButtonItem>
              </PanelSectionRow>
              <PanelSectionRow>
                <div style={{ fontSize: "12px", lineHeight: 1.5 }}>{cloudSaveSummaryText}</div>
              </PanelSectionRow>
              <PanelSectionRow>
                <div style={{ fontSize: "11px", lineHeight: 1.5, opacity: 0.88 }}>
                  {`${cloudSaveUploadState.message || "未开始"} | ${clampProgress(cloudSaveUploadState.progress).toFixed(1)}%`}
                </div>
              </PanelSectionRow>
            </PanelSection>

            <PanelSection title="云存档下载恢复">
              <PanelSectionRow>
                <ButtonItem
                  layout="below"
                  onClick={refreshRestoreOptions}
                  disabled={!login.logged_in || restoreBusy}
                >
                  {loadingRestoreOptions ? "刷新中..." : "刷新云存档列表"}
                </ButtonItem>
              </PanelSectionRow>
              <PanelSectionRow>
                <DropdownItem
                  label="选择游戏"
                  description="按游戏分组显示云端版本"
                  rgOptions={restoreGameOptions}
                  selectedOption={selectedRestoreGameKey}
                  disabled={!login.logged_in || restoreBusy || restoreGameOptions.length <= 0}
                  onChange={(option) => setSelectedRestoreGameKey(String(option?.data || ""))}
                />
              </PanelSectionRow>
              <PanelSectionRow>
                <DropdownItem
                  label="选择版本时间"
                  description="按时间倒序"
                  rgOptions={restoreVersionOptions}
                  selectedOption={selectedRestoreVersion}
                  disabled={!login.logged_in || restoreBusy || !selectedRestoreGame || restoreVersionOptions.length <= 0}
                  onChange={(option) => setSelectedRestoreVersion(String(option?.data || ""))}
                />
              </PanelSectionRow>
              <PanelSectionRow>
                <ButtonItem
                  layout="below"
                  onClick={onLoadRestoreEntries}
                  disabled={!login.logged_in || restoreBusy || !selectedRestoreGame || !selectedRestoreVersion}
                >
                  {loadingRestoreEntries ? "读取中..." : "读取可选存档项"}
                </ButtonItem>
              </PanelSectionRow>

              {restoreEntries.length > 0 &&
                restoreEntries.map((entry) => {
                  const entryId = String(entry.entry_id || "");
                  const checked = selectedRestoreEntryIds.includes(entryId);
                  return (
                    <PanelSectionRow key={`restore_entry_${entryId}`}>
                      <ToggleField
                        label={`${entry.entry_name || entryId}${entry.file_count ? `（${entry.file_count} 文件）` : ""}`}
                        checked={checked}
                        onChange={(value: boolean) => toggleRestoreEntry(entryId, value)}
                        disabled={restoreBusy}
                      />
                    </PanelSectionRow>
                  );
                })}

              {restoreEntries.length > 0 && (
                <PanelSectionRow>
                  <div style={{ display: "flex", gap: "8px", width: "100%" }}>
                    <ButtonItem
                      layout="below"
                      onClick={() => {
                        setSelectedRestoreEntryIds(
                          restoreEntries.map((item) => String(item.entry_id || "")).filter(Boolean),
                        );
                      }}
                      disabled={restoreBusy}
                    >
                      全选
                    </ButtonItem>
                    <ButtonItem
                      layout="below"
                      onClick={() => setSelectedRestoreEntryIds([])}
                      disabled={restoreBusy}
                    >
                      清空
                    </ButtonItem>
                  </div>
                </PanelSectionRow>
              )}

              {targetCandidates.length > 1 && (
                <PanelSectionRow>
                  <DropdownItem
                    label="恢复目标目录"
                    description="检测到多个候选目录，请明确选择"
                    rgOptions={targetCandidates.map((path) => ({ data: path, label: path }))}
                    selectedOption={selectedRestoreTargetDir}
                    disabled={restoreBusy}
                    onChange={(option) => setSelectedRestoreTargetDir(String(option?.data || ""))}
                  />
                </PanelSectionRow>
              )}

              <PanelSectionRow>
                <ButtonItem
                  layout="below"
                  onClick={onStartCloudSaveRestore}
                  disabled={!login.logged_in || restoreBusy || !selectedRestoreGame || !selectedRestoreVersion || !selectedRestoreEntryIds.length}
                >
                  {planningRestore ? "规划中..." : applyingRestore ? "恢复中..." : "下载并恢复云存档"}
                </ButtonItem>
              </PanelSectionRow>
              <PanelSectionRow>
                <div style={{ fontSize: "12px", lineHeight: 1.5 }}>{cloudSaveRestoreSummaryText}</div>
              </PanelSectionRow>
              <PanelSectionRow>
                <div style={{ fontSize: "11px", lineHeight: 1.5, opacity: 0.88 }}>
                  {`${cloudSaveRestoreState.message || "未开始"} | ${clampProgress(cloudSaveRestoreState.progress).toFixed(1)}%`}
                </div>
              </PanelSectionRow>
            </PanelSection>
          </>
        ),
      },
      {
        id: "diagnostics",
        title: "诊断",
        content: (
          <>
            <PanelSection title="插件自检">
              <PanelSectionRow>
                <div style={{ fontSize: "12px", lineHeight: 1.6, opacity: 0.88 }}>
                  检查插件版本、状态/下载/安装目录、aria2/7zz/node、Steam 快捷方式、SD 卡、网络与百度扫码接口。
                </div>
              </PanelSectionRow>
              <PanelSectionRow>
                <ButtonItem layout="below" onClick={() => void onRunDiagnostics()} disabled={diagnosticsBusy}>
                  {diagnosticsBusy ? "自检中..." : "运行自检"}
                </ButtonItem>
              </PanelSectionRow>
              {diagnosticsError ? (
                <PanelSectionRow>
                  <div style={{ fontSize: "12px", lineHeight: 1.6, color: "#ffb4a8", wordBreak: "break-word" }}>
                    {`自检失败：${diagnosticsError}`}
                  </div>
                </PanelSectionRow>
              ) : null}
              {diagnosticsReport ? (
                <>
                  <PanelSectionRow>
                    <div style={{ fontSize: "12px", lineHeight: 1.6 }}>
                      {`v${diagnosticsReport.version || "?"} · ${diagnosticsReport.arch || "-"} · OK ${diagnosticsReport.summary?.ok || 0} / 警告 ${diagnosticsReport.summary?.warn || 0} / 失败 ${diagnosticsReport.summary?.fail || 0} / 跳过 ${diagnosticsReport.summary?.skip || 0}`}
                    </div>
                  </PanelSectionRow>
                  {(diagnosticsReport.checks || []).map((check, checkIndex) => {
                    const status = String(check.status || "skip").toLowerCase();
                    const color =
                      status === "ok"
                        ? "#9fe6a8"
                        : status === "warn"
                          ? "#ffd479"
                          : status === "fail"
                            ? "#ff9a8a"
                            : "#b9c0cc";
                    return (
                      <PanelSectionRow key={check.id || `diagnostic-${checkIndex}`}>
                        <div style={{ display: "flex", flexDirection: "column", gap: "3px", width: "100%" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", gap: "8px" }}>
                            <span style={{ fontWeight: 600 }}>{check.label || check.id || "-"}</span>
                            <span style={{ color, fontSize: "12px" }}>{status.toUpperCase()}</span>
                          </div>
                          <div style={{ fontSize: "12px", opacity: 0.86, wordBreak: "break-word" }}>{check.detail}</div>
                          {check.fix && status !== "ok" ? (
                            <div style={{ fontSize: "11px", opacity: 0.7 }}>{`建议：${check.fix}`}</div>
                          ) : null}
                        </div>
                      </PanelSectionRow>
                    );
                  })}
                </>
              ) : null}
            </PanelSection>

            <PanelSection title="诊断包">
              <PanelSectionRow>
                <div style={{ fontSize: "12px", lineHeight: 1.6, opacity: 0.88 }}>
                  导出 diagnostics.json、self-check.json、最新 300 行日志；cookie/token 已脱敏，写到下载目录。
                </div>
              </PanelSectionRow>
              <PanelSectionRow>
                <ButtonItem layout="below" onClick={() => void onExportDiagnostics()} disabled={diagnosticsExportBusy}>
                  {diagnosticsExportBusy ? "打包中..." : "导出诊断包"}
                </ButtonItem>
              </PanelSectionRow>
              {diagnosticsExportMessage ? (
                <PanelSectionRow>
                  <div style={{ fontSize: "11px", opacity: 0.82, wordBreak: "break-all" }}>{diagnosticsExportMessage}</div>
                </PanelSectionRow>
              ) : null}
            </PanelSection>
          </>
        ),
      },
    ],
    [
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
    ],
  );

  const focusSettingsTabRow = useCallback(
    (tabId?: string) => {
      const classMap = getGamepadTabClassMap();
      if (!classMap || !settingsContainerRef.current) return;
      const tabClass = classMap.Tab;
      if (!tabClass) return;

      let target: HTMLElement | null = null;
      if (tabId) {
        const tabTitle = String(tabs.find((tab) => tab.id === tabId)?.title || "").trim();
        if (tabTitle) {
          const elements = settingsContainerRef.current.querySelectorAll(`.${tabClass}`);
          for (const element of Array.from(elements)) {
            const item = element as HTMLElement;
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
        target = settingsContainerRef.current.querySelector(selector) as HTMLElement | null;
      }
      target?.focus?.();
    },
    [tabs],
  );

  useEffect(() => {
    const classMap = getGamepadTabClassMap();
    if (!classMap) return;
    const rowClass = classMap.TabsRowScroll || classMap.TabRowTabs;
    if (!rowClass) return;
    const handle = window.requestAnimationFrame(() => {
      const root = settingsContainerRef.current;
      if (!root) return;
      const row = root.querySelector(`.${rowClass}`) as HTMLElement | null;
      if (!row) return;
      row.style.scrollBehavior = "auto";
      row.scrollLeft = 0;
    });
    return () => window.cancelAnimationFrame(handle);
  }, [activeTab]);

  const onShowSettingsTab = useCallback(
    (tabId: string) => {
      focusSettingsTabRow();
      setActiveTab(tabId);
      window.requestAnimationFrame(() => focusSettingsTabRow(tabId));
    },
    [focusSettingsTabRow],
  );

  if (loading) {
    return (
      <PanelSection title="freedeckCY 设置">
        <PanelSectionRow>加载中...</PanelSectionRow>
      </PanelSection>
    );
  }

  return (
    <div
      ref={settingsContainerRef}
      className="freedeckcy-settings-root"
      style={{
        paddingTop: 48,
        paddingBottom: 24,
        minHeight: "100%",
        boxSizing: "border-box",
        overflowX: "hidden",
      }}
    >
      <style>{tabStabilityCss}</style>
      <Tabs tabs={tabs} activeTab={activeTab} onShowTab={onShowSettingsTab} autoFocusContents={false} />
    </div>
  );
}

function tryRestartSteamViaClient(): boolean {
  try {
    const host = window as unknown as {
      SteamClient?: { User?: { StartRestart?: (forceShutdown: boolean) => void } };
      top?: unknown;
      parent?: unknown;
    };
    const top = host.top as typeof host | null;
    const parent = host.parent as typeof host | null;
    for (const candidate of [host.SteamClient, top?.SteamClient, parent?.SteamClient]) {
      const restart = candidate?.User?.StartRestart;
      if (typeof restart === "function") {
        restart(false);
        return true;
      }
    }
  } catch {
    // 忽略客户端重启 API 不可用。
  }
  return false;
}

function Content() {
  const [loading, setLoading] = useState<boolean>(true);
  const [state, setState] = useState<PanelState>(EMPTY_STATE);
  const [openingLogin, setOpeningLogin] = useState<boolean>(false);
  const [uninstallingKey, setUninstallingKey] = useState<string>("");
  const [taskActionKey, setTaskActionKey] = useState<string>("");
  const [previewingKey, setPreviewingKey] = useState<string>("");
  const syncingRef = useRef<boolean>(false);
  const latestStateRef = useRef<PanelState>(EMPTY_STATE);
  const restartPromptOpenRef = useRef<boolean>(false);
  const restartPromptShownRef = useRef<Set<string>>(new Set());

  const syncState = useCallback(async (pollMode: PanelPollMode = PANEL_POLL_MODE_IDLE) => {
    if (syncingRef.current) return;
    syncingRef.current = true;
    try {
      const result = await withTimeout(
        getTianyiPanelState({
          poll_mode: pollMode,
          visible: !document.hidden,
          has_focus: document.hasFocus(),
        }),
        PANEL_REQUEST_TIMEOUT_MS,
        "读取面板状态超时，请稍后重试",
      );
      if (result.status !== "success" || !result.data) {
        throw new Error(result.message || "读取状态失败");
      }
      const next = result.data;
      const normalized: PanelState = {
        login: next.login || EMPTY_STATE.login,
        installed: next.installed || EMPTY_STATE.installed,
        tasks: next.tasks || [],
        settings: Object.assign({}, EMPTY_SETTINGS, next.settings || {}),
        library_url: next.library_url || "",
        power_diagnostics: next.power_diagnostics || {},
        steam_restart: next.steam_restart || { pending: false },
      };
      latestStateRef.current = normalized;
      setState(normalized);
    } finally {
      syncingRef.current = false;
    }
  }, []);

  useEffect(() => {
    const pending = state.steam_restart;
    if (!pending?.pending) return;
    if (restartPromptOpenRef.current) return;
    const title = String(pending.title || "游戏").trim() || "游戏";
    const key = `${String(pending.game_id || "")}:${String(pending.app_id || "")}:${title}`;
    if (restartPromptShownRef.current.has(key)) return;
    restartPromptShownRef.current.add(key);
    restartPromptOpenRef.current = true;

    let modal: { Close: () => void } | null = null;
    try {
      modal = showModal(
        <ConfirmModal
          strTitle="重启 Steam"
          strDescription={`「${title}」已安装并写入 Steam 快捷方式。\n\n现在重启 Steam 会立即出现在库中；也可以选择稍后手动重启。`}
          strOKButtonText="现在重启"
          strCancelButtonText="稍后"
          onOK={() => {
            try {
              modal?.Close();
            } catch {
              // 忽略关闭失败。
            }
            if (tryRestartSteamViaClient()) {
              toaster.toast({ title: "freedeckCY", body: "正在重启 Steam..." });
            } else {
              toaster.toast({ title: "freedeckCY", body: "无法自动重启，请手动重启 Steam 后查看游戏" });
            }
          }}
          onCancel={() => {
            try {
              modal?.Close();
            } catch {
              // 忽略关闭失败。
            }
          }}
        />,
        undefined,
        {
          strTitle: "重启 Steam",
          bNeverPopOut: true,
          fnOnClose: () => {
            restartPromptOpenRef.current = false;
          },
        },
      );
    } catch {
      restartPromptOpenRef.current = false;
    }
  }, [state.steam_restart]);

  useEffect(() => {
    let alive = true;
    let firstRun = true;
    let timer = 0;

    const clearTimer = () => {
      if (!timer) return;
      window.clearTimeout(timer);
      timer = 0;
    };

    const scheduleNext = () => {
      if (!alive) return;
      clearTimer();
      const mode = resolvePanelPollMode(latestStateRef.current);
      const delay = pollIntervalByMode(mode);
      timer = window.setTimeout(() => {
        void runPoll(false);
      }, delay);
    };

    const runPoll = async (showErrorToast: boolean) => {
      if (!alive) return;
      const mode = resolvePanelPollMode(latestStateRef.current);
      try {
        await syncState(mode);
      } catch (error) {
        if (showErrorToast && alive) {
          toastError(error);
        }
      } finally {
        if (firstRun) {
          firstRun = false;
          if (alive) setLoading(false);
        }
        scheduleNext();
      }
    };

    const handleVisibilityChange = () => {
      if (!alive) return;
      clearTimer();
      if (document.hidden) {
        scheduleNext();
        return;
      }
      void runPoll(false);
    };

    const handleFocus = () => {
      if (!alive) return;
      clearTimer();
      void runPoll(false);
    };

    const handleBlur = () => {
      if (!alive) return;
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

  const onLogin = useCallback(async () => {
    if (openingLogin) return;
    setOpeningLogin(true);
    try {
      const result = await withTimeout(getTianyiLoginUrl(), 20000, "获取登录地址超时，请稍后重试");
      if (result.status !== "success") {
        throw new Error(describeOpenError(result, "获取登录地址失败"));
      }
      openExternalUrl(result.url || result.data?.url || "");
    } catch (error) {
      toastError(error);
    } finally {
      setOpeningLogin(false);
    }
  }, [openingLogin]);

  const onOpenLibrary = useCallback(() => {
    try {
      Router.CloseSideMenus?.();
    } catch {
      // 忽略菜单关闭失败。
    }
    // 优先用 QAM 原生 Modal，避免路由未注册时被 Steam 当成网页路径。
    try {
      let modal: { Close: () => void } | null = null;
      modal = showModal(
        <LibraryPage
          onClose={() => {
            try {
              modal?.Close();
            } catch {
              // 忽略关闭失败。
            }
          }}
        />,
      );
      return;
    } catch {
      // 继续尝试全屏路由。
    }
    try {
      Navigation.Navigate(LIBRARY_ROUTE);
    } catch (error) {
      toaster.toast({ title: "freedeckCY", body: `打开游戏库失败：${errorText(error)}` });
    }
  }, []);

  const onOpenSettings = useCallback(() => {
    try {
      Router.CloseSideMenus?.();
    } catch {
      // 忽略菜单关闭失败。
    }
    try {
      Navigation.Navigate(SETTINGS_ROUTE);
    } catch (error) {
      toaster.toast({ title: "freedeckCY", body: `打开设置失败：${errorText(error)}` });
    }
  }, []);

  const installedGames = useMemo(() => state.installed?.preview || [], [state.installed]);
  const installedGameIds = useMemo(() => {
    const set = new Set<string>();
    for (const item of installedGames) {
      const gameId = String(item.game_id || "").trim();
      if (gameId) set.add(gameId);
    }
    return set;
  }, [installedGames]);
  const visibleTasks = useMemo(
    () =>
      (state.tasks || []).filter((task) => {
        if (isTaskAlreadyInstalled(task)) return false;
        const gameId = String(task.game_id || "").trim();
        if (gameId && installedGameIds.has(gameId)) return false;
        return true;
      }),
    [installedGameIds, state.tasks],
  );
  const sortedInstalledGames = useMemo(() => {
    const list = [...installedGames];
    list.sort((a, b) =>
      String(a.title || "").localeCompare(String(b.title || ""), "zh-Hans-CN", {
        sensitivity: "base",
        numeric: true,
      }),
    );
    return list;
  }, [installedGames]);
  const loginStatusText = useMemo(() => {
    if (!state.login.logged_in) return "没登录";
    const account = String(state.login.user_account || "").trim() || "未知账号";
    return `已登录：${account}（账号）`;
  }, [state.login.logged_in, state.login.user_account]);

  const performUninstallInstalledGame = useCallback(
    async (item: InstalledGameItem, deleteCompatdata = false) => {
      const gameId = String(item.game_id || "").trim();
      const installPath = String(item.install_path || "").trim();
      const title = String(item.title || gameId || "该游戏");
      if (!installPath) {
        toaster.toast({ title: "freedeckCY", body: "安装路径为空，无法卸载" });
        return;
      }
      if (uninstallingKey) return;

      const key = `${gameId}::${installPath}`;
      setUninstallingKey(key);
      try {
        const result = await withTimeout(
          uninstallTianyiInstalledGame({
            game_id: gameId,
            install_path: installPath,
            delete_files: true,
            delete_compatdata: Boolean(deleteCompatdata),
          }),
          120000,
          "卸载超时（大目录删除可能较慢，请稍后刷新确认）",
        );
        if (result.status !== "success") {
          throw new Error(result.message || "卸载失败");
        }
        const freedBytes = Number(
          (result.data as { compatdata?: { freed_bytes?: number } } | undefined)?.compatdata?.freed_bytes || 0,
        );
        const suffix = deleteCompatdata
          ? freedBytes > 0
            ? `（已回收 Proton 前缀 ${formatBytesText(freedBytes)}）`
            : "（含 Proton 前缀）"
          : "";
        toaster.toast({ title: "freedeckCY", body: `已卸载：${title}${suffix}` });
        try {
          await syncState();
        } catch {
          // 卸载已成功；列表刷新失败不再弹“卸载失败”误导用户。
        }
      } catch (error) {
        toastError(error);
      } finally {
        setUninstallingKey("");
      }
    },
    [syncState, uninstallingKey],
  );

  const onUninstallInstalledGame = useCallback(
    async (item: InstalledGameItem) => {
      const gameId = String(item.game_id || "").trim();
      const installPath = String(item.install_path || "").trim();
      const title = String(item.title || gameId || "该游戏");
      if (!installPath) {
        toaster.toast({ title: "freedeckCY", body: "安装路径为空，无法卸载" });
        return;
      }
      if (uninstallingKey || previewingKey) return;

      const key = `${gameId}::${installPath}`;
      setPreviewingKey(key);
      let preview: UninstallPreviewData | null = null;
      try {
        const result = await withTimeout(
          previewTianyiUninstall({ game_id: gameId, install_path: installPath }),
          15000,
          "读取卸载信息超时",
        );
        if (result.status === "success") preview = result.data ?? null;
      } catch {
        preview = null;
      } finally {
        setPreviewingKey("");
      }

      const installBytes = Number(preview?.install_size_bytes || 0);
      const compatBytes = Number(preview?.compatdata_size_bytes || 0);
      const lines: string[] = [`确定卸载「${title}」吗？`, ""];
      if (installBytes > 0) lines.push(`安装目录占用：${formatBytesText(installBytes)}`);
      lines.push(installPath);
      if (compatBytes > 0) {
        lines.push("", `Proton 前缀（compatdata）另占 ${formatBytesText(compatBytes)}，可选择一并删除。`);
      }

      showModal(
        <ConfirmModal
          strTitle="确认卸载"
          strDescription={lines.join("\n")}
          strOKButtonText={compatBytes > 0 ? "仅删游戏文件" : "确认卸载"}
          strMiddleButtonText={
            compatBytes > 0 ? `连 Proton 前缀一起删（${formatBytesText(compatBytes)}）` : undefined
          }
          onMiddleButton={
            compatBytes > 0
              ? () => {
                  void performUninstallInstalledGame(item, true);
                }
              : undefined
          }
          strCancelButtonText="取消"
          onOK={() => {
            void performUninstallInstalledGame(item, false);
          }}
          onCancel={() => {}}
        />,
      );
    },
    [performUninstallInstalledGame, previewingKey, uninstallingKey],
  );

  const performTaskAction = useCallback(
    async (action: "pause" | "resume" | "remove" | "retry", task: TaskItem) => {
      const taskId = String(task.task_id || "").trim();
      if (!taskId) return;
      if (taskActionKey) return;

      setTaskActionKey(`${action}:${taskId}`);
      try {
        const runner =
          action === "pause"
            ? pauseTianyiTask
            : action === "resume"
              ? resumeTianyiTask
              : action === "retry"
                ? retryTianyiTask
                : removeTianyiTask;
        // 重试要重新取直链/重新进入安装，给更长的超时；暂停/继续/移除通常很快。
        const actionTimeoutMs = action === "retry" ? 60000 : 20000;
        const result = await withTimeout(
          runner({ task_id: taskId }),
          actionTimeoutMs,
          "任务操作超时，请稍后重试",
        );
        if (result.status !== "success") {
          throw new Error(result.message || "任务操作失败");
        }
        const label =
          action === "pause"
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
        } catch {
          // 操作已成功；刷新失败不覆盖成功提示。
        }
      } catch (error) {
        toastError(error);
      } finally {
        setTaskActionKey("");
      }
    },
    [syncState, taskActionKey],
  );

  const onRemoveTask = useCallback(
    (task: TaskItem) => {
      const taskId = String(task.task_id || "").trim();
      if (!taskId || taskActionKey) return;
      const title = task.game_title || task.file_name || "该任务";
      showModal(
        <ConfirmModal
          strTitle="确认移除任务"
          strDescription={`确定移除「${title}」吗？\n\n只移除任务记录，不删除已下载文件。`}
          strOKButtonText="确认移除"
          strCancelButtonText="取消"
          onOK={() => {
            void performTaskAction("remove", task);
          }}
          onCancel={() => {}}
        />,
      );
    },
    [performTaskAction, taskActionKey],
  );

  if (loading) {
    return (
      <PanelSection>
        <PanelSectionRow>加载中...</PanelSectionRow>
      </PanelSection>
    );
  }

  return (
    <>
      <PanelSection>
        <PanelSectionRow>
          <div
            style={{
              width: "100%",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={loginStatusText}
          >
            {loginStatusText}
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <div style={{ fontSize: "10px", opacity: 0.55 }}>{`QAM 原生 UI v${PLUGIN_UI_BUILD}`}</div>
        </PanelSectionRow>
        <PanelSectionRow>
          {!state.login.logged_in && (
            <ButtonItem layout="below" onClick={onLogin} disabled={openingLogin}>
              {openingLogin ? "登录入口准备中..." : "登录"}
            </ButtonItem>
          )}
          <ButtonItem layout="below" onClick={onOpenLibrary} disabled={openingLogin}>
            游戏库
          </ButtonItem>
          <ButtonItem layout="below" onClick={onOpenSettings}>设置</ButtonItem>
        </PanelSectionRow>
      </PanelSection>

      {visibleTasks.length > 0 && (
        <PanelSection title={`下载列表（${visibleTasks.length}）`}>
          {visibleTasks.slice(0, 20).map((task) => {
            const taskId = String(task.task_id || "");
            const status = String(task.status || "");
            const canPause = status === "active" || status === "waiting";
            const canResume = status === "paused";
            const canRetry = status === "error" || String(task.install_status || "") === "failed";
            const busy = Boolean(taskActionKey) && taskActionKey.endsWith(taskId);
            const buttonStyle = {
              minWidth: "76px",
              borderRadius: "10px",
              border: "1px solid rgba(255, 255, 255, 0.22)",
              background: "rgba(255, 255, 255, 0.12)",
              color: "#f2f2f2",
            } as const;
            return (
              <PanelSectionRow key={task.task_id}>
                {TaskProgressRow(task)}
                <div style={{ display: "flex", gap: "8px", width: "100%", marginTop: "4px" }}>
                  {canPause && (
                    <Focusable style={{ flex: 1 }}>
                      <DialogButton
                        onClick={() => void performTaskAction("pause", task)}
                        onOKButton={() => void performTaskAction("pause", task)}
                        disabled={Boolean(taskActionKey)}
                        style={buttonStyle}
                      >
                        {busy ? "处理中..." : "暂停"}
                      </DialogButton>
                    </Focusable>
                  )}
                  {canResume && (
                    <Focusable style={{ flex: 1 }}>
                      <DialogButton
                        onClick={() => void performTaskAction("resume", task)}
                        onOKButton={() => void performTaskAction("resume", task)}
                        disabled={Boolean(taskActionKey)}
                        style={buttonStyle}
                      >
                        {busy ? "处理中..." : "继续"}
                      </DialogButton>
                    </Focusable>
                  )}
                  {canRetry && (
                    <Focusable style={{ flex: 1 }}>
                      <DialogButton
                        onClick={() => void performTaskAction("retry", task)}
                        onOKButton={() => void performTaskAction("retry", task)}
                        disabled={Boolean(taskActionKey)}
                        style={{
                          minWidth: "76px",
                          borderRadius: "10px",
                          border: "1px solid rgba(120, 200, 255, 0.45)",
                          background: "rgba(120, 200, 255, 0.16)",
                          color: "#dff4ff",
                        }}
                      >
                        {busy ? "重试中..." : "重试"}
                      </DialogButton>
                    </Focusable>
                  )}
                  <Focusable style={{ flex: 1 }}>
                    <DialogButton
                      onClick={() => onRemoveTask(task)}
                      onOKButton={() => onRemoveTask(task)}
                      disabled={Boolean(taskActionKey)}
                      style={{
                        minWidth: "76px",
                        borderRadius: "10px",
                        border: "1px solid rgba(255, 106, 106, 0.4)",
                        background: "rgba(255, 106, 106, 0.16)",
                        color: "#ffe8e8",
                      }}
                    >
                      移除
                    </DialogButton>
                  </Focusable>
                </div>
              </PanelSectionRow>
            );
          })}
        </PanelSection>
      )}

      {sortedInstalledGames.length > 0 && (
        <PanelSection title={`游戏预览（已安装 ${state.installed.total || sortedInstalledGames.length}）`}>
          {sortedInstalledGames.map((item, index) => {
            const uninstallKey = `${item.game_id || ""}::${item.install_path || ""}`;
            const uninstalling = uninstallingKey === uninstallKey;
            return (
              <PanelSectionRow key={`${item.game_id || item.title || "game"}_${index}`}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px", width: "100%" }}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div
                      style={{
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={item.title || "未命名游戏"}
                    >
                      {item.title || "未命名游戏"}
                    </div>
                    <div style={{ fontSize: "12px" }}>
                      {`${item.size_text || "-"}${item.status ? ` | ${item.status}` : ""}`}
                    </div>
                    <div style={{ fontSize: "12px" }}>
                      {`游玩时长：${formatPlaytimeText(item.playtime_seconds || 0, item.playtime_text)}${
                        item.playtime_active ? "（进行中）" : ""
                      }`}
                    </div>
                    <div
                      style={{
                        fontSize: "12px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={item.install_path || "-"}
                    >
                      {item.install_path || "-"}
                    </div>
                  </div>
                  <Focusable style={{ flex: "0 0 auto" }}>
                    <DialogButton
                      onClick={() => onUninstallInstalledGame(item)}
                      onOKButton={() => onUninstallInstalledGame(item)}
                      disabled={Boolean(uninstallingKey) || uninstalling}
                      style={{
                        minWidth: "88px",
                        borderRadius: "10px",
                        border: "1px solid rgba(255, 255, 255, 0.26)",
                        background: uninstalling ? "rgba(255, 106, 106, 0.34)" : "rgba(255, 106, 106, 0.2)",
                        color: "#ffe8e8",
                      }}
                    >
                      {uninstalling ? "卸载中..." : "卸载"}
                    </DialogButton>
                  </Focusable>
                </div>
              </PanelSectionRow>
            );
          })}
        </PanelSection>
      )}
    </>
  );
}


const LIBRARY_CARD_WIDTH = 133;
const LIBRARY_CARD_HEIGHT = 200;

function libraryCoverGradient(platform: string): string {
  const key = String(platform || "pc").toLowerCase();
  const colors: Record<string, [string, string]> = {
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

interface LibraryCoverCardProps {
  title: string;
  platform: string;
  meta?: string;
  coverUrl?: string;
  installed?: boolean;
  busyLabel?: string;
  disabled?: boolean;
  onPress: () => void;
  actions?: ReactNode;
}

function LibraryCoverCard(props: LibraryCoverCardProps) {
  const [imageFailed, setImageFailed] = useState<boolean>(false);
  const coverUrl = imageFailed ? "" : String(props.coverUrl || "").trim();
  const title = props.title || "未命名游戏";
  return (
    <div style={{ width: `${LIBRARY_CARD_WIDTH}px`, display: "flex", flexDirection: "column", gap: "6px" }}>
      <DialogButton
        onClick={props.onPress}
        disabled={Boolean(props.disabled)}
        style={{
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
        }}
      >
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={title}
            referrerPolicy="no-referrer"
            decoding="async"
            onError={() => setImageFailed(true)}
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          />
        ) : (
          <div
            style={{
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
            }}
          >{title}</div>
        )}
        {props.installed ? (
          <div
            style={{
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
            }}
          >已安装</div>
        ) : null}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 2,
            padding: "28px 9px 9px",
            background: "linear-gradient(to top, rgba(8,10,14,0.96), rgba(8,10,14,0.72) 55%, rgba(8,10,14,0))",
          }}
        >
          <div
            style={{
              fontSize: "12px",
              lineHeight: 1.3,
              fontWeight: 700,
              color: "#f2f6fb",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              wordBreak: "break-word",
            }}
          >{title}</div>
          <div style={{ marginTop: "3px", fontSize: "10px", lineHeight: 1.25, color: "rgba(220,230,240,0.78)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {String(props.platform || "pc").toUpperCase()}{props.meta ? ` · ${props.meta}` : ""}
          </div>
        </div>
        {props.busyLabel ? (
          <div
            style={{
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
            }}
          >{props.busyLabel}</div>
        ) : null}
      </DialogButton>
      {props.actions ? (
        <Focusable style={{ display: "flex", gap: "4px", width: `${LIBRARY_CARD_WIDTH}px` }}>
          {props.actions}
        </Focusable>
      ) : null}
    </div>
  );
}

function LibraryPage({ onClose }: { onClose?: () => void }) {
  const [tab, setTab] = useState<"catalog" | "installed">("catalog");
  const [query, setQuery] = useState<string>("");
  const [activeQuery, setActiveQuery] = useState<string>("");
  const [platform, setPlatform] = useState<string>("");
  const [category, setCategory] = useState<string>("");
  const [sort, setSort] = useState<string>("");
  const [page, setPage] = useState<number>(1);
  const [catalog, setCatalog] = useState<CatalogPage>({ total: 0, page: 1, page_size: 20, items: [] });
  const [installed, setInstalled] = useState<InstalledList>({ total: 0, items: [] });
  const [loadingCatalog, setLoadingCatalog] = useState<boolean>(true);
  const [reloadNonce, setReloadNonce] = useState<number>(0);
  const [loadingInstalled, setLoadingInstalled] = useState<boolean>(false);
  const [busyKey, setBusyKey] = useState<string>("");
  const catalogRequestRef = useRef<number>(0);
  const installedRequestRef = useRef<number>(0);
  const busyRef = useRef<string>("");
  const pageSize = 30;

  // 用 ref 做同步锁：state 更新有延迟，快速连点会绕过 busyKey 判断导致重复请求/互相清 busy。
  const beginBusy = useCallback((key: string): boolean => {
    if (busyRef.current) return false;
    busyRef.current = key;
    setBusyKey(key);
    return true;
  }, []);
  const endBusy = useCallback(() => {
    busyRef.current = "";
    setBusyKey("");
  }, []);

  const loadCatalog = useCallback(
    async (targetPage: number) => {
      const requestSeq = catalogRequestRef.current + 1;
      catalogRequestRef.current = requestSeq;
      setLoadingCatalog(true);
      try {
        const result = await withTimeout(
          listTianyiCatalog({
            query: activeQuery,
            page: Math.max(1, targetPage),
            page_size: pageSize,
            platform,
            category,
            sort,
          }),
          15000,
          "读取游戏列表超时",
        );
        // 过滤条件/翻页可能并发触发多个请求：只让最后一次请求的结果落地，避免旧响应覆盖新列表。
        if (catalogRequestRef.current !== requestSeq) return;
        if (result.status !== "success" || !result.data) {
          throw new Error(result.message || "读取游戏列表失败");
        }
        const data = result.data;
        setCatalog({
          total: Number(data.total || 0),
          page: Number(data.page || 1),
          page_size: Number(data.page_size || pageSize),
          platforms: Array.isArray(data.platforms) ? data.platforms : [],
          categories: Array.isArray(data.categories) ? data.categories : [],
          items: Array.isArray(data.items) ? data.items : [],
        });
        setPage(Number(data.page || 1));
      } catch (error) {
        if (catalogRequestRef.current === requestSeq) toastError(error);
      } finally {
        if (catalogRequestRef.current === requestSeq) setLoadingCatalog(false);
      }
    },
    [activeQuery, platform, category, sort, reloadNonce],
  );

  const loadInstalled = useCallback(async () => {
    const requestSeq = installedRequestRef.current + 1;
    installedRequestRef.current = requestSeq;
    setLoadingInstalled(true);
    try {
      const result = await withTimeout(listTianyiInstalledGames(), 15000, "读取已安装列表超时");
      if (installedRequestRef.current !== requestSeq) return;
      if (result.status !== "success" || !result.data) {
        throw new Error(result.message || "读取已安装列表失败");
      }
      const data = result.data;
      setInstalled({
        total: Number(data.total || 0),
        items: Array.isArray(data.items) ? data.items : [],
      });
    } catch (error) {
      if (installedRequestRef.current === requestSeq) toastError(error);
    } finally {
      if (installedRequestRef.current === requestSeq) setLoadingInstalled(false);
    }
  }, []);

  // 搜索词/筛选没变时（例如同一个词再按一次回车）也要能刷新：用 nonce 触发 effect 重新拉取。
  const submitSearch = useCallback(() => {
    setActiveQuery(query.trim());
    setPage(1);
    setReloadNonce((value) => value + 1);
  }, [query]);

  const resetSearch = useCallback(() => {
    setQuery("");
    setActiveQuery("");
    setPlatform("");
    setCategory("");
    setSort("");
    setPage(1);
    setReloadNonce((value) => value + 1);
  }, []);

  useEffect(() => {
    void loadCatalog(1);
  }, [loadCatalog]);

  useEffect(() => {
    if (tab === "installed") void loadInstalled();
  }, [tab, loadInstalled]);

  const platformOptions = useMemo(
    () => [{ data: "", label: "全部平台" }, ...(catalog.platforms || []).map((item) => ({
      data: String(item.value || ""),
      label: `${item.label || item.value}（${item.count || 0}）`,
    }))],
    [catalog.platforms],
  );
  const categoryOptions = useMemo(
    () => [{ data: "", label: "全部分类" }, ...(catalog.categories || []).slice(0, 30).map((item) => ({
      data: String(item.value || ""),
      label: String(item.label || item.value || ""),
    }))],
    [catalog.categories],
  );
  const sortOptions = useMemo(
    () => [
      { data: "", label: "默认排序" },
      { data: "title", label: "名称" },
      { data: "size_desc", label: "大小从大到小" },
      { data: "size_asc", label: "大小从小到大" },
    ],
    [],
  );

  const onPrepareInstall = useCallback(async (item: CatalogItem) => {
    if (!beginBusy(item.game_id)) return;
    try {
      const result = await withTimeout(
        prepareTianyiInstall({ game_id: item.game_id }),
        30000,
        "生成安装计划超时",
      );
      if (result.status !== "success" || !result.data) {
        throw new Error(result.message || "生成安装计划失败");
      }
      const plan = result.data;
      if (!plan.can_install) {
        throw new Error(plan.message || "磁盘空间不足，无法安装");
      }
      const emulatorText = plan.emulator_info?.name ? `模拟器：${plan.emulator_info.name}` : "PC / Proton";
      const setupText = plan.emulator_info?.setup_hint ? `\n提示：${plan.emulator_info.setup_hint}` : "";
      showModal(
        <ConfirmModal
          strTitle={`安装 ${plan.game_title || item.title}`}
          strDescription={
            `下载：${plan.required_download_human || "未知"} → ${plan.download_dir || "-"}\n` +
            `安装：${plan.required_install_human || "未知"} → ${plan.install_dir || "-"}\n` +
            `${emulatorText}${setupText}`
          }
          strOKButtonText="开始下载"
          strCancelButtonText="取消"
          onOK={() => {
            void (async () => {
              try {
                const started = await withTimeout(
                  startTianyiInstall({ game_id: item.game_id }),
                  30000,
                  "启动安装超时",
                );
                if (started.status !== "success") {
                  throw new Error(started.message || "启动安装失败");
                }
                toaster.toast({ title: "freedeckCY", body: "已加入下载队列，可在插件主页查看任务进度" });
              } catch (error) {
                toastError(error);
              }
            })();
          }}
          onCancel={() => {}}
        />,
      );
    } catch (error) {
      toastError(error);
    } finally {
      endBusy();
    }
  }, [beginBusy, endBusy]);

  const onLaunchInstalled = useCallback(async (item: InstalledItem) => {
    if (!beginBusy(item.game_id)) return;
    try {
      const result = await withTimeout(launchTianyiInstalledGame(item.game_id), 20000, "启动游戏超时");
      if (result.status !== "success") throw new Error(result.message || "启动失败");
      toaster.toast({ title: "freedeckCY", body: `正在启动 ${item.title}` });
    } catch (error) {
      toastError(error);
    } finally {
      endBusy();
    }
  }, [beginBusy, endBusy]);

  const onOpenFolder = useCallback(async (item: InstalledItem) => {
    if (!beginBusy(item.game_id)) return;
    try {
      const result = await withTimeout(openTianyiInstalledFolder(item.game_id), 20000, "打开目录超时");
      if (result.status !== "success") throw new Error(result.message || "打开目录失败");
    } catch (error) {
      toastError(error);
    } finally {
      endBusy();
    }
  }, [beginBusy, endBusy]);

  const onUninstall = useCallback((item: InstalledItem) => {
    if (busyRef.current) return;
    showModal(
      <ConfirmModal
        strTitle={`卸载 ${item.title}`}
        strDescription="将删除安装目录并移除记录，是否继续？"
        strOKButtonText="卸载"
        strCancelButtonText="取消"
        onOK={() => {
          void (async () => {
            if (!beginBusy(item.game_id)) return;
            try {
              const result = await withTimeout(uninstallTianyiInstalled({
                game_id: item.game_id,
                install_path: item.install_path,
                delete_files: true,
              }), 120000, "卸载超时（大目录删除可能较慢，请稍后刷新确认）");
              if (result.status !== "success") throw new Error(result.message || "卸载失败");
              toaster.toast({ title: "freedeckCY", body: `已卸载：${item.title || item.game_id}` });
              await loadInstalled();
            } catch (error) {
              toastError(error);
            } finally {
              endBusy();
            }
          })();
        }}
        onCancel={() => {}}
      />,
    );
  }, [beginBusy, endBusy, loadInstalled]);

  const handleClose = useCallback(() => {
    if (onClose) {
      try {
        onClose();
        return;
      } catch {
        // onClose 失效时继续走路由返回兜底。
      }
    }
    try {
      Navigation.NavigateBack();
    } catch {
      try {
        Router.CloseSideMenus?.();
      } catch {
        // 忽略关闭失败。
      }
    }
  }, [onClose]);

  const handleSteamLibrary = useCallback(() => {
    // modal 模式先关弹层；路由模式先留在插件页，导航失败再回退。
    try {
      onClose?.();
    } catch {
      // 忽略关闭失败。
    }
    try {
      Navigation.NavigateToLibraryTab();
      return;
    } catch {
      // 继续尝试旧接口。
    }
    try {
      Router.NavigateToLibraryTab?.();
      return;
    } catch {
      // 继续尝试返回。
    }
    if (!onClose) {
      try {
        Navigation.NavigateBack();
      } catch {
        // 忽略关闭失败。
      }
    }
  }, [onClose]);

  const totalPages = Math.max(1, Math.ceil(catalog.total / Math.max(1, catalog.page_size || pageSize)));

  return (
    <Focusable
      noFocusRing
      onCancel={handleClose}
      style={{
        height: "100%",
        overflowY: "auto",
        boxSizing: "border-box",
        // SteamOS Game Mode 的库页无论是 showModal 还是路由都是全屏，
        // 都会被 Steam 顶栏/底栏覆盖：顶部固定让出状态栏，底部留出 Steam 菜单。
        padding: "72px 8px 160px",
        background: "#0e1116",
        color: "#f2f6fb",
      }}
    >
      <div
        aria-hidden="true"
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          height: "60px",
          background: "#0e1116",
          zIndex: 15,
          pointerEvents: "none",
        }}
      />
      <div
        aria-hidden="true"
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          height: "72px",
          background: "#0e1116",
          zIndex: 15,
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "sticky",
          top: "64px",
          zIndex: 20,
          display: "flex",
          justifyContent: "space-between",
          gap: "8px",
          padding: "8px 0",
          background: "#0e1116",
          backdropFilter: "blur(8px)",
        }}
      >
        <Focusable onCancel={handleClose} style={{ display: "flex", gap: "6px" }}>
          <DialogButton onClick={handleClose} style={{ width: "auto", flex: "0 0 auto", padding: "8px 16px", minHeight: "38px", minWidth: "78px" }}>返回</DialogButton>
          <DialogButton onClick={handleSteamLibrary} style={{ width: "auto", flex: "0 0 auto", padding: "8px 16px", minHeight: "38px", minWidth: "92px" }}>Steam 库</DialogButton>
        </Focusable>
        <DialogButton
          onClick={() => { if (tab === "catalog") void loadCatalog(page); else void loadInstalled(); }}
          disabled={loadingCatalog || loadingInstalled}
          style={{ width: "auto", flex: "0 0 auto", padding: "8px 16px", minHeight: "38px", minWidth: "76px" }}
        >{loadingCatalog || loadingInstalled ? "刷新中..." : "刷新"}</DialogButton>
      </div>
      <PanelSection>
        <PanelSectionRow>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", width: "100%" }}>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ fontSize: "18px", fontWeight: 700 }}>freedeckCY 游戏库</div>
              <div style={{ fontSize: "11px", opacity: 0.65 }}>{`原生 UI · v${PLUGIN_UI_BUILD}`}</div>
            </div>
            <Focusable style={{ display: "flex", gap: "6px" }}>
              <DialogButton onClick={handleClose} style={{ padding: "6px 12px" }}>返回</DialogButton>
              <DialogButton
                onClick={() => setTab("catalog")}
                style={{ padding: "6px 12px", background: tab === "catalog" ? "rgba(255,255,255,0.22)" : undefined }}
              >游戏库</DialogButton>
              <DialogButton
                onClick={() => setTab("installed")}
                style={{ padding: "6px 12px", background: tab === "installed" ? "rgba(255,255,255,0.22)" : undefined }}
              >已安装{installed.total ? `(${installed.total})` : ""}</DialogButton>
              <DialogButton
                onClick={() => { if (tab === "catalog") void loadCatalog(page); else void loadInstalled(); }}
                disabled={loadingCatalog || loadingInstalled}
                style={{ padding: "6px 12px" }}
              >{loadingCatalog || loadingInstalled ? "刷新中..." : "刷新"}</DialogButton>
            </Focusable>
          </div>
        </PanelSectionRow>
      </PanelSection>

      {tab === "catalog" ? (
        <>
          <PanelSection title="搜索与筛选">
            <PanelSectionRow>
              <TextField
                label="搜索游戏"
                value={query}
                onChange={(event) => setQuery(getTextFieldValue(event))}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    submitSearch();
                  }
                }}
              />
            </PanelSectionRow>
            <PanelSectionRow>
              <Focusable style={{ display: "flex", gap: "6px" }}>
                <DialogButton
                  onClick={submitSearch}
                  style={{ padding: "6px 12px" }}
                >搜索</DialogButton>
                <DialogButton
                  onClick={resetSearch}
                  style={{ padding: "6px 12px" }}
                >重置</DialogButton>
              </Focusable>
            </PanelSectionRow>
            <PanelSectionRow>
              <DropdownItem
                label="平台"
                rgOptions={platformOptions}
                selectedOption={platform}
                onChange={(option) => { setPlatform(String(option?.data || "")); setPage(1); }}
              />
            </PanelSectionRow>
            <PanelSectionRow>
              <DropdownItem
                label="分类"
                rgOptions={categoryOptions}
                selectedOption={category}
                onChange={(option) => { setCategory(String(option?.data || "")); setPage(1); }}
              />
            </PanelSectionRow>
            <PanelSectionRow>
              <DropdownItem
                label="排序"
                rgOptions={sortOptions}
                selectedOption={sort}
                onChange={(option) => { setSort(String(option?.data || "")); setPage(1); }}
              />
            </PanelSectionRow>
          </PanelSection>

          <PanelSection title={`游戏列表（${catalog.total}）`}>
            {loadingCatalog ? (
              <PanelSectionRow><div style={{ fontSize: "12px" }}>加载中...</div></PanelSectionRow>
            ) : catalog.items.length === 0 ? (
              <PanelSectionRow><div style={{ fontSize: "12px" }}>没有匹配游戏</div></PanelSectionRow>
            ) : (
              <PanelSectionRow>
                <Focusable
                  style={{
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
                  }}
                >
                  {catalog.items.map((item) => (
                    <LibraryCoverCard
                      key={item.game_id}
                      title={item.title || "未命名游戏"}
                      platform={item.platform}
                      meta={item.size_text || "-"}
                      coverUrl={item.cover_portrait_url || item.cover_url}
                      busyLabel={busyKey === item.game_id ? "处理中..." : ""}
                      disabled={Boolean(busyKey)}
                      onPress={() => void onPrepareInstall(item)}
                    />
                  ))}
                </Focusable>
              </PanelSectionRow>
            )}
            <PanelSectionRow>
              <Focusable style={{ display: "flex", gap: "8px", alignItems: "center", justifyContent: "center", width: "100%" }}>
                <DialogButton
                  onClick={() => void loadCatalog(page - 1)}
                  disabled={loadingCatalog || page <= 1}
                  style={{ padding: "6px 12px" }}
                >上一页</DialogButton>
                <div style={{ fontSize: "12px" }}>{`${page} / ${totalPages}`}</div>
                <DialogButton
                  onClick={() => void loadCatalog(page + 1)}
                  disabled={loadingCatalog || page >= totalPages}
                  style={{ padding: "6px 12px" }}
                >下一页</DialogButton>
              </Focusable>
            </PanelSectionRow>
          </PanelSection>
        </>
      ) : (
        <PanelSection title={`已安装（${installed.total}）`}>
          {loadingInstalled ? (
            <PanelSectionRow><div style={{ fontSize: "12px" }}>加载中...</div></PanelSectionRow>
          ) : null}
          {installed.items.length === 0 ? (
            <PanelSectionRow><div style={{ fontSize: "12px" }}>还没有已安装游戏</div></PanelSectionRow>
          ) : (
            <PanelSectionRow>
              <Focusable
                style={{
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
                }}
              >
                {installed.items.map((item) => (
                  <LibraryCoverCard
                    key={item.game_id}
                    title={item.title || "未命名游戏"}
                    platform={item.platform}
                    meta={item.playtime_text ? `${item.size_text || "-"} · ${item.playtime_text}` : (item.size_text || "-")}
                    coverUrl={item.cover_portrait_url || item.cover_url}
                    installed
                    disabled={Boolean(busyKey)}
                    onPress={() => void onLaunchInstalled(item)}
                    actions={
                      <>
                        <DialogButton
                          onClick={() => void onOpenFolder(item)}
                          disabled={Boolean(busyKey)}
                          style={{ flex: 1, minWidth: 0, padding: "4px 2px", fontSize: "11px" }}
                        >目录</DialogButton>
                        <DialogButton
                          onClick={() => onUninstall(item)}
                          disabled={Boolean(busyKey)}
                          style={{ flex: 1, minWidth: 0, padding: "4px 2px", fontSize: "11px", background: "rgba(255,106,106,0.22)" }}
                        >卸载</DialogButton>
                      </>
                    }
                  />
                ))}
              </Focusable>
            </PanelSectionRow>
          )}
        </PanelSection>
      )}
    </Focusable>
  );
}

export default definePlugin(() => {
  routerHook.addRoute(SETTINGS_ROUTE, SettingsPage);
  routerHook.addRoute(LIBRARY_ROUTE, LibraryPage);
  const unpatchLibraryPlaytime = installLibraryPlaytimePatch();
  let uninstallGameActionReporter = () => {};
  try {
    uninstallGameActionReporter = installGlobalGameActionReporter();
  } catch {
    // 忽略全局游戏事件监听初始化失败，避免影响插件主 UI。
  }

  return {
    name: "freedeckCY",
    titleView: <div className={staticClasses.Title}>freedeckCY</div>,
    content: <Content />,
    icon: <FaCloudDownloadAlt />,
    onDismount() {
      uninstallGameActionReporter();
      unpatchLibraryPlaytime();
      routerHook.removeRoute(SETTINGS_ROUTE);
      routerHook.removeRoute(LIBRARY_ROUTE);
    },
  };
});

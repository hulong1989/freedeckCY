const { createApp } = window.Vue;

function buildUrl(path, query = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    url.searchParams.set(key, String(value));
  });
  return url.toString();
}

async function apiGet(path, query = {}) {
  const resp = await fetch(buildUrl(path, query), {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  return resp.json();
}

async function apiPost(path, body = {}) {
  const resp = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  return resp.json();
}

createApp({
  data() {
    return {
      settings: {
        download_dir: "",
        install_dir: "",
        split_count: 16,
        page_size: 50,
      },
      list: { total: 0, page: 1, page_size: 50, items: [] },
      categories: [],
      activeCategory: "",
      platforms: [],
      activePlatform: "",
      mode: "catalog",
      installed: { total: 0, items: [] },
      sort: "",
      sortOptions: ["", "title", "size_desc", "size_asc"],
      sortLabels: { "": "默认", title: "名称", size_desc: "大小↓", size_asc: "大小↑" },
      diagnosticsBusy: false,
      updateBusy: false,
      confirmDialog: { visible: false, title: "", message: "", action: null },
      confirmReturnIndex: 0,
      query: "",
      activeQuery: "",
      showResults: false,
      hintText: "",
      message: "",
      coverCache: {},
      coverMetaCache: {},
      coverPending: {},
      coverMissCache: {},
      focusedIndex: 0,
      gamepadTimer: null,
      gamepadPressed: {},
      gamepadRepeatState: {},
      gamepadPollMs: 160,
      installDialog: {
        visible: false,
        loading: false,
        submitting: false,
        plan: null,
        game: null,
      },
    };
  },
  computed: {
    totalPages() {
      const total = Number(this.list.total || 0);
      const pageSize = Number(this.list.page_size || 50);
      if (total <= 0 || pageSize <= 0) return 1;
      return Math.max(1, Math.ceil(total / pageSize));
    },
    platformChips() {
      const chips = [{ value: "", label: "全部平台", count: 0 }];
      for (const item of this.platforms || []) {
        const value = String(item && item.value ? item.value : "").trim();
        if (!value) continue;
        chips.push({
          value,
          label: String((item && item.label) || value),
          count: Number((item && item.count) || 0),
        });
      }
      return chips;
    },
    filterChips() {
      const chips = [{ value: "", label: "全部分类", count: 0 }];
      for (const item of this.categories || []) {
        const value = String(item && item.value ? item.value : "").trim();
        if (!value) continue;
        chips.push({
          value,
          label: String((item && item.label) || value),
          count: Number((item && item.count) || 0),
        });
      }
      return chips;
    },
    sortLabel() {
      return this.sortLabels[this.sort] || "默认";
    },
    modalCanConfirm() {
      if (!this.installDialog.plan) return false;
      if (this.installDialog.loading || this.installDialog.submitting) return false;
      return this.storageEnough(this.installDialog.plan);
    },
  },
  mounted() {
    this.bootstrap();
    window.addEventListener("keydown", this.onGlobalKeyDown, { passive: false });
    window.addEventListener("gamepadconnected", this.onGamepadConnected);
    window.addEventListener("gamepaddisconnected", this.onGamepadDisconnected);
    document.addEventListener("visibilitychange", this.onVisibilityChange);
    window.addEventListener("focus", this.onWindowFocus);
    window.addEventListener("blur", this.onWindowBlur);
    this.syncGamepadPolling();
    this.setFocusIndex(0, { scroll: false });
  },
  beforeUnmount() {
    window.removeEventListener("keydown", this.onGlobalKeyDown);
    window.removeEventListener("gamepadconnected", this.onGamepadConnected);
    window.removeEventListener("gamepaddisconnected", this.onGamepadDisconnected);
    document.removeEventListener("visibilitychange", this.onVisibilityChange);
    window.removeEventListener("focus", this.onWindowFocus);
    window.removeEventListener("blur", this.onWindowBlur);
    this.stopGamepadPolling();
  },
  methods: {
    onVisibilityChange() {
      this.syncGamepadPolling();
    },
    onWindowFocus() {
      this.syncGamepadPolling();
    },
    onWindowBlur() {
      this.syncGamepadPolling();
    },
    syncGamepadPolling() {
      const shouldRun = !document.hidden && document.hasFocus();
      if (!shouldRun) {
        this.stopGamepadPolling();
        return;
      }
      this.startGamepadPolling();
    },
    flash(text) {
      this.message = String(text || "");
      if (!this.message) return;
      setTimeout(() => {
        this.message = "";
      }, 2400);
    },
    formatShareAttempt(item) {
      if (!item || typeof item !== "object") return "";
      const profile = String(item.profile || item.step || "").trim();
      const method = String(item.method || "").trim().toUpperCase();
      const host = String(item.host || "").trim();
      const endpoint = String(item.endpoint || "").trim().replace("/api/open/share/", "");
      const status = Number(item.status || 0);
      const reason = String(item.message || "").trim();
      const tags = [profile, method, host].filter(Boolean).join(" ");
      const endpointPart = endpoint ? ` ${endpoint}` : "";
      const statusPart = Number.isFinite(status) && status > 0 ? ` status=${status}` : "";
      const reasonPart = reason ? ` ${reason}` : "";
      return `${tags}${endpointPart}${statusPart}${reasonPart}`.trim();
    },
    summarizeShareAttempts(diagnostics) {
      const attempts = Array.isArray(diagnostics && diagnostics.attempts) ? diagnostics.attempts : [];
      if (!attempts.length) return "";
      const failed = attempts.filter((item) => item && item.ok === false);
      const head = failed[0] || attempts[0] || {};
      const tail = failed[failed.length - 1] || attempts[attempts.length - 1] || {};
      const headText = this.formatShareAttempt(head);
      const tailText = this.formatShareAttempt(tail);
      const failedCount = failed.length;
      let text = `已尝试 ${attempts.length} 条链路，失败 ${failedCount} 条`;
      if (headText) text += `；首个关键尝试：${headText}`;
      if (tailText && tailText !== headText) text += `；最后关键尝试：${tailText}`;
      return text;
    },
    buildPrepareInstallError(result) {
      const base = String((result && result.message) || "安装准备失败").trim();
      const diagnostics = (result && result.diagnostics) || {};
      const attempts = Array.isArray(diagnostics.attempts) ? diagnostics.attempts : [];
      if (!attempts.length) return base;
      const headline = base.includes("shareId") ? base : `${base}（未获取shareId）`;
      const summary = this.summarizeShareAttempts(diagnostics);
      return summary ? `${headline}。${summary}` : headline;
    },
    normalizePath(path) {
      return String(path || "")
        .trim()
        .replace(/\\/g, "/")
        .replace(/\/+$/, "")
        .toLowerCase();
    },
    toNum(value) {
      const num = Number(value || 0);
      return Number.isFinite(num) ? Math.max(0, num) : 0;
    },
    samePathOrNest(pathA, pathB) {
      if (!pathA || !pathB) return false;
      if (pathA === pathB) return true;
      return pathA.startsWith(`${pathB}/`) || pathB.startsWith(`${pathA}/`);
    },
    isSameStorage(plan) {
      if (!plan || typeof plan !== "object") return false;
      const downloadDir = this.normalizePath(plan.download_dir);
      const installDir = this.normalizePath(plan.install_dir);
      if (this.samePathOrNest(downloadDir, installDir)) return true;

      const freeDownload = this.toNum(plan.free_download_bytes);
      const freeInstall = this.toNum(plan.free_install_bytes);
      if (freeDownload > 0 && freeInstall > 0) {
        const diff = Math.abs(freeDownload - freeInstall);
        if (diff <= 64 * 1024 * 1024) return true;
      }
      return false;
    },
    totalRequiredBytes(plan) {
      return this.toNum(plan && plan.required_download_bytes) + this.toNum(plan && plan.required_install_bytes);
    },
    totalRequiredFormula(plan) {
      const packText = this.formatBytes(this.toNum(plan && plan.required_download_bytes));
      const gameText = this.formatBytes(this.toNum(plan && plan.required_install_bytes));
      return `压缩包（${packText}）+游戏本体（${gameText}）`;
    },
    totalFreeBytes(plan) {
      if (!plan || typeof plan !== "object") return 0;
      const freeDownload = this.toNum(plan.free_download_bytes);
      const freeInstall = this.toNum(plan.free_install_bytes);
      if (freeDownload > 0 && freeInstall > 0) {
        return Math.min(freeDownload, freeInstall);
      }
      return Math.max(freeDownload, freeInstall);
    },
    combinedSpaceOk(plan) {
      const need = this.totalRequiredBytes(plan);
      const free = this.totalFreeBytes(plan);
      if (need <= 0) return Boolean(plan && plan.can_install);
      return free >= need;
    },
    storageEnough(plan) {
      if (!plan || typeof plan !== "object") return false;
      if (this.isSameStorage(plan)) return this.combinedSpaceOk(plan);
      return this.downloadSpaceOk(plan) && this.installSpaceOk(plan);
    },
    freeSpaceLabel(plan) {
      if (!plan || typeof plan !== "object") return "-";
      if (this.isSameStorage(plan)) {
        return this.formatBytes(this.totalFreeBytes(plan));
      }
      const freeDownload = this.formatBytes(this.toNum(plan.free_download_bytes));
      const freeInstall = this.formatBytes(this.toNum(plan.free_install_bytes));
      return `下载盘 ${freeDownload} / 安装盘 ${freeInstall}`;
    },
    storageChipLabel(plan) {
      return this.storageEnough(plan) ? "充足" : "不足";
    },
    storageChipClass(plan) {
      return this.storageEnough(plan) ? "chip-good" : "chip-bad";
    },
    protonTierFor(item) {
      const key = this.getCoverCacheKey(item);
      if (!key) return "";
      const meta = this.coverMetaCache[key];
      if (!meta || typeof meta !== "object") return "";
      return String(meta.proton_tier || "").trim();
    },
    protonTierLabel(tierRaw) {
      const tier = String(tierRaw || "").trim().toLowerCase();
      if (!tier) return "未知";
      if (["platinum", "gold", "native"].includes(tier)) return "绿标";
      if (["silver", "bronze"].includes(tier)) return "黄标";
      if (["borked", "unsupported"].includes(tier)) return "红标";
      return tier.toUpperCase();
    },
    protonTierClass(tierRaw) {
      const tier = String(tierRaw || "").trim().toLowerCase();
      if (["platinum", "gold", "native"].includes(tier)) return "tier-green";
      if (["silver", "bronze"].includes(tier)) return "tier-yellow";
      if (["borked", "unsupported"].includes(tier)) return "tier-red";
      return "tier-neutral";
    },
    protonBadgeClass(tierRaw) {
      const tier = String(tierRaw || "").trim().toLowerCase();
      if (["platinum", "gold", "native"].includes(tier)) return "tier-good";
      if (["silver", "bronze"].includes(tier)) return "tier-mid";
      if (["borked", "unsupported"].includes(tier)) return "tier-bad";
      return "tier-unknown";
    },
    protonBadgeMark(tierRaw) {
      const tier = String(tierRaw || "").trim().toLowerCase();
      if (["platinum", "gold", "native"].includes(tier)) return "✓";
      if (["silver", "bronze"].includes(tier)) return "!";
      if (["borked", "unsupported"].includes(tier)) return "×";
      return "?";
    },
    downloadSpaceOk(plan) {
      if (!plan || typeof plan !== "object") return false;
      const free = this.toNum(plan.free_download_bytes);
      const need = this.toNum(plan.required_download_bytes);
      if (free > 0 || need > 0) return free >= need;
      return Boolean(plan.download_dir_ok);
    },
    installSpaceOk(plan) {
      if (!plan || typeof plan !== "object") return false;
      const free = this.toNum(plan.free_install_bytes);
      const need = this.toNum(plan.required_install_bytes);
      if (free > 0 || need > 0) return free >= need;
      return Boolean(plan.install_dir_ok);
    },
    async bootstrap() {
      try {
        const result = await apiGet("/api/tianyi/state");
        if (result.status !== "success") return;
        const data = result.data || {};
        this.settings = Object.assign({}, this.settings, data.settings || {});
        if (!this.settings.page_size) this.settings.page_size = 50;
        if (!this.settings.split_count) this.settings.split_count = 16;
        if (!this.settings.install_dir) this.settings.install_dir = this.settings.download_dir || "";
      } catch (_error) {
        // 状态读取失败不阻断浏览流程。
      }
      await this.reloadList(1);
      await this.reloadInstalled();
    },
    platformChipCount() {
      if (!this.showResults || this.mode !== "catalog") return 0;
      return this.platformChips.length > 1 ? this.platformChips.length : 0;
    },
    categoryChipCount() {
      if (!this.showResults || this.mode !== "catalog") return 0;
      return this.filterChips.length > 1 ? this.filterChips.length : 0;
    },
    filterChipCount() {
      return this.platformChipCount() + this.categoryChipCount();
    },
    cardStartIndex() {
      return 2 + this.filterChipCount();
    },
    selectPlatform(value) {
      const next = String(value || "").trim();
      this.activePlatform = next;
      void this.reloadList(1);
    },
    selectCategory(value) {
      const next = String(value || "").trim();
      if (next === this.activeCategory) {
        void this.reloadList(1);
        return;
      }
      this.activeCategory = next;
      void this.reloadList(1);
    },
    getFocusableCount() {
      if (this.confirmDialog.visible) {
        return 2;
      }
      if (this.installDialog.visible) {
        return 2;
      }
      const cardCount = this.showResults ? Number(this.list.items.length || 0) : 0;
      return 2 + this.filterChipCount() + Math.max(0, cardCount);
    },
    getCardColumns() {
      const cards = Array.from(document.querySelectorAll(".game-card"));
      if (cards.length <= 1) return 1;
      const firstTop = cards[0].getBoundingClientRect().top;
      let columns = 0;
      for (const card of cards) {
        const top = card.getBoundingClientRect().top;
        if (Math.abs(top - firstTop) <= 6) {
          columns += 1;
        }
      }
      return Math.max(1, columns || 1);
    },
    focusElementByIndex(index, options = {}) {
      const scroll = options.scroll !== false;
      let el = null;
      if (this.confirmDialog.visible) {
        el = index <= 0 ? document.getElementById("confirm-cancel") : document.getElementById("confirm-ok");
      } else if (this.installDialog.visible) {
        el = index <= 0 ? document.getElementById("install-cancel") : document.getElementById("install-confirm");
      } else if (index === 0) {
        el = document.getElementById("search-input");
      } else if (index === 1) {
        el = document.getElementById("search-button");
      } else {
        const platformCount = this.platformChipCount();
        const categoryCount = this.categoryChipCount();
        if (platformCount > 0 && index < 2 + platformCount) {
          el = document.querySelector(`.platform-filter-chip[data-platform-index="${index - 2}"]`);
        } else if (categoryCount > 0 && index < 2 + platformCount + categoryCount) {
          el = document.querySelector(`.filter-chip[data-chip-index="${index - 2 - platformCount}"]`);
        } else {
          const cardIndex = index - this.cardStartIndex();
          el = document.querySelector(`.game-card[data-card-index="${cardIndex}"]`);
        }
      }
      if (!el || typeof el.focus !== "function") return;
      try {
        el.focus({ preventScroll: true });
      } catch (_error) {
        el.focus();
      }
      if (scroll && !this.installDialog.visible && index >= 2 && typeof el.scrollIntoView === "function") {
        el.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
      }
    },
    setFocusIndex(index, options = {}) {
      const total = this.getFocusableCount();
      if (total <= 0) return;
      const next = Math.max(0, Math.min(total - 1, Number(index || 0)));
      this.focusedIndex = next;
      this.$nextTick(() => this.focusElementByIndex(next, options));
    },
    moveFocus(direction) {
      if (this.confirmDialog.visible) {
        if (["left", "up"].includes(direction)) this.setFocusIndex(0, { scroll: false });
        if (["right", "down"].includes(direction)) this.setFocusIndex(1, { scroll: false });
        return;
      }
      if (this.installDialog.visible) {
        if (["left", "up"].includes(direction)) this.setFocusIndex(0, { scroll: false });
        if (["right", "down"].includes(direction)) this.setFocusIndex(1, { scroll: false });
        return;
      }

      const total = this.getFocusableCount();
      if (total <= 0) return;

      const platformStart = 2;
      const platformCount = this.platformChipCount();
      const platformEnd = platformStart + platformCount - 1;
      const categoryStart = platformStart + platformCount;
      const categoryCount = this.categoryChipCount();
      const categoryEnd = categoryStart + categoryCount - 1;
      const cardStart = this.cardStartIndex();
      const hasPlatforms = platformCount > 0;
      const hasCategories = categoryCount > 0;
      const hasCards = total > cardStart;
      const columns = this.getCardColumns();
      let next = this.focusedIndex;

      const inPlatforms = hasPlatforms && next >= platformStart && next <= platformEnd;
      const inCategories = hasCategories && next >= categoryStart && next <= categoryEnd;

      if (direction === "left") {
        if (inPlatforms) {
          next = next > platformStart ? next - 1 : 1;
        } else if (inCategories) {
          next = next > categoryStart ? next - 1 : hasPlatforms ? platformEnd : 1;
        } else if (next > cardStart) {
          next -= 1;
        } else if (next === 1) {
          next = 0;
        }
      } else if (direction === "right") {
        if (next === 0) {
          next = 1;
        } else if (inPlatforms) {
          if (next < platformEnd) next += 1;
          else if (hasCategories) next = categoryStart;
          else if (hasCards) next = cardStart;
        } else if (inCategories) {
          if (next < categoryEnd) next += 1;
          else if (hasCards) next = cardStart;
        } else if (next >= cardStart && next < total - 1) {
          next += 1;
        }
      } else if (direction === "up") {
        if (inPlatforms) {
          next = 0;
        } else if (inCategories) {
          next = hasPlatforms ? platformStart : 0;
        } else if (next >= cardStart) {
          const up = next - columns;
          if (up >= cardStart) next = up;
          else if (hasCategories) next = categoryStart;
          else if (hasPlatforms) next = platformStart;
          else next = 0;
        } else if (next === 1) {
          next = 0;
        }
      } else if (direction === "down") {
        if (next === 0) {
          next = 1;
        } else if (next === 1) {
          if (hasPlatforms) next = platformStart;
          else if (hasCategories) next = categoryStart;
          else if (hasCards) next = cardStart;
        } else if (inPlatforms) {
          if (hasCategories) next = categoryStart;
          else if (hasCards) next = cardStart;
        } else if (inCategories) {
          if (hasCards) next = cardStart;
        } else if (next >= cardStart) {
          next = Math.min(total - 1, next + columns);
        }
      }

      this.setFocusIndex(next);
    },
    async activateFocused() {
      if (this.confirmDialog.visible) {
        if (this.focusedIndex <= 0) {
          this.closeConfirm();
        } else {
          this.confirmAction();
        }
        return;
      }
      if (this.installDialog.visible) {
        if (this.focusedIndex <= 0) {
          this.closeInstallDialog();
          return;
        }
        await this.confirmInstall();
        return;
      }
      if (this.mode === "installed") {
        const item = this.focusedInstalledItem();
        if (item) await this.launchInstalled(item);
        return;
      }
      const index = this.focusedIndex;
      if (index <= 1) {
        await this.reloadList(1);
        return;
      }
      const platformCount = this.platformChipCount();
      if (platformCount > 0 && index < 2 + platformCount) {
        const chip = this.platformChips[index - 2];
        this.selectPlatform(chip ? chip.value : "");
        return;
      }
      const categoryCount = this.categoryChipCount();
      if (categoryCount > 0 && index < 2 + platformCount + categoryCount) {
        const chip = this.filterChips[index - 2 - platformCount];
        this.selectCategory(chip ? chip.value : "");
        return;
      }
      const cardIndex = index - this.cardStartIndex();
      const item = this.list.items[cardIndex];
      if (item) {
        await this.openInstallConfirm(item);
      }
    },
    handleBackAction() {
      if (this.confirmDialog.visible) {
        this.closeConfirm();
        return;
      }
      if (this.installDialog.visible) {
        this.closeInstallDialog();
        return;
      }
      if (this.mode === "installed") {
        void this.switchMode("catalog");
        return;
      }
      this.setFocusIndex(0, { scroll: false });
    },
    onGlobalKeyDown(event) {
      const key = String(event.key || "");
      const target = event.target;
      const typing = Boolean(
        target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable),
      );
      if (typing) {
        if (key === "Escape") this.handleBackAction();
        return;
      }

      if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter", "Escape", "PageUp", "PageDown"].includes(key)) {
        event.preventDefault();
      }

      if (key === "ArrowUp") this.moveFocus("up");
      if (key === "ArrowDown") this.moveFocus("down");
      if (key === "ArrowLeft") this.moveFocus("left");
      if (key === "ArrowRight") this.moveFocus("right");
      if (key === "Enter") this.activateFocused();
      if (key === "Escape") this.handleBackAction();
      if (key === "x" || key === "X") this.toggleMode();
      if (key === "y" || key === "Y") {
        if (this.mode === "installed") this.openFocusedInstalledFolder();
        else this.cycleSort();
      }
      if ((key === "o" || key === "O") && this.mode === "installed") this.openFocusedInstalledFolder();
      if (key === "Delete" && this.mode === "installed") this.askFocusedUninstall();
      if (key === "PageUp") this.gotoPage(this.list.page - 1);
      if (key === "PageDown") this.gotoPage(this.list.page + 1);
    },
    pressEdge(name, pressed, callback) {
      const wasPressed = Boolean(this.gamepadPressed[name]);
      if (pressed && !wasPressed) {
        callback();
      }
      this.gamepadPressed[name] = Boolean(pressed);
    },
    repeatDirectional(name, pressed, callback, nowTs) {
      const repeatDelay = 260;
      const repeatInterval = 110;
      const state = this.gamepadRepeatState[name] || { active: false, nextAt: 0 };
      if (!pressed) {
        state.active = false;
        state.nextAt = 0;
        this.gamepadRepeatState[name] = state;
        return;
      }
      if (!state.active) {
        callback();
        state.active = true;
        state.nextAt = nowTs + repeatDelay;
        this.gamepadRepeatState[name] = state;
        return;
      }
      if (nowTs >= state.nextAt) {
        callback();
        state.nextAt = nowTs + repeatInterval;
      }
      this.gamepadRepeatState[name] = state;
    },
    readPrimaryGamepad() {
      if (!navigator.getGamepads) return null;
      const pads = navigator.getGamepads();
      if (!pads) return null;
      for (const pad of pads) {
        if (pad) return pad;
      }
      return null;
    },
    pollGamepad() {
      const pad = this.readPrimaryGamepad();
      if (!pad) return;

      const buttons = pad.buttons || [];
      const axes = pad.axes || [];
      const axisX = Number(axes[0] || 0);
      const axisY = Number(axes[1] || 0);
      const deadzone = 0.56;
      const nowTs = Date.now();

      const up = Boolean(buttons[12] && buttons[12].pressed) || axisY <= -deadzone;
      const down = Boolean(buttons[13] && buttons[13].pressed) || axisY >= deadzone;
      const left = Boolean(buttons[14] && buttons[14].pressed) || axisX <= -deadzone;
      const right = Boolean(buttons[15] && buttons[15].pressed) || axisX >= deadzone;
      const a = Boolean(buttons[0] && buttons[0].pressed);
      const b = Boolean(buttons[1] && buttons[1].pressed);
      const x = Boolean(buttons[2] && buttons[2].pressed);
      const y = Boolean(buttons[3] && buttons[3].pressed);
      const l1 = Boolean(buttons[4] && buttons[4].pressed);
      const r1 = Boolean(buttons[5] && buttons[5].pressed);

      this.repeatDirectional("up", up, () => this.moveFocus("up"), nowTs);
      this.repeatDirectional("down", down, () => this.moveFocus("down"), nowTs);
      this.repeatDirectional("left", left, () => this.moveFocus("left"), nowTs);
      this.repeatDirectional("right", right, () => this.moveFocus("right"), nowTs);
      this.pressEdge("a", a, () => this.activateFocused());
      this.pressEdge("b", b, () => this.handleBackAction());
      this.pressEdge("x", x, () => this.toggleMode());
      this.pressEdge("y", y, () => {
        if (this.confirmDialog.visible || this.installDialog.visible) return;
        if (this.mode === "installed") this.openFocusedInstalledFolder();
        else this.cycleSort();
      });
      this.pressEdge("l1", l1, () => this.gotoPage(this.list.page - 1));
      this.pressEdge("r1", r1, () => this.gotoPage(this.list.page + 1));
    },
    startGamepadPolling() {
      if (this.gamepadTimer) return;
      if (document.hidden || !document.hasFocus()) return;
      this.gamepadTimer = window.setInterval(() => this.pollGamepad(), this.gamepadPollMs);
    },
    stopGamepadPolling() {
      if (!this.gamepadTimer) return;
      window.clearInterval(this.gamepadTimer);
      this.gamepadTimer = null;
      this.gamepadPressed = {};
      this.gamepadRepeatState = {};
    },
    onGamepadConnected() {
      this.startGamepadPolling();
    },
    onGamepadDisconnected() {
      const pad = this.readPrimaryGamepad();
      if (!pad) {
        this.gamepadPressed = {};
        this.gamepadRepeatState = {};
      }
    },
    async reloadList(page = 1) {
      const q = this.query.trim();
      this.showResults = true;
      this.activeQuery = q;
      this.hintText = q ? "" : "浏览全部资源（可按平台/分类筛选）";

      const result = await apiGet("/api/tianyi/catalog", {
        q,
        page,
        page_size: this.settings.page_size,
        category: this.activeCategory || "",
        platform: this.activePlatform || "",
        sort: this.sort || "",
      });
      if (result.status !== "success") {
        this.flash(result.message || "加载失败");
        this.setFocusIndex(0, { scroll: false });
        return;
      }

      this.list = Object.assign({ total: 0, page: 1, page_size: 50, items: [] }, result.data || {});
      this.categories = Array.isArray(this.list.categories) ? this.list.categories : this.categories;
      this.platforms = Array.isArray(this.list.platforms) ? this.list.platforms : this.platforms;
      const pages = this.totalPages;
      if (Number(this.list.page || 1) > pages) {
        await this.reloadList(pages);
        return;
      }
      const scope = [];
      if (this.activePlatform) scope.push(`平台「${this.activePlatform.toUpperCase()}」`);
      if (this.activeCategory) scope.push(`分类「${this.activeCategory}」`);
      const prefix = scope.length ? `（${scope.join("，")}）` : "";
      if (q) {
        this.hintText = `已显示“${q}”的搜索结果${prefix}`;
      } else {
        this.hintText = `共 ${this.list.total} 条资源${prefix}，第 ${this.list.page} / ${pages} 页`;
      }
      if (!this.list.items || this.list.items.length === 0) {
        this.setFocusIndex(0, { scroll: false });
      } else {
        this.setFocusIndex(this.cardStartIndex(), { scroll: true });
        void this.prefetchCovers(this.list.items);
      }
    },
    async reloadInstalled() {
      const result = await apiGet("/api/tianyi/installed");
      if (result.status !== "success") {
        this.flash(result.message || "读取已安装列表失败");
        return;
      }
      this.installed = Object.assign({ total: 0, items: [] }, result.data || {});
      this.showResults = true;
      if (this.mode === "installed") {
        if (this.installed.items.length) {
          this.setFocusIndex(2, { scroll: true });
          void this.prefetchCovers(this.installed.items);
        } else {
          this.setFocusIndex(0, { scroll: false });
        }
      }
    },
    async switchMode(mode) {
      const next = mode === "installed" ? "installed" : "catalog";
      if (this.mode === next) return;
      this.mode = next;
      this.focusedIndex = 0;
      if (next === "installed") {
        await this.reloadInstalled();
      } else {
        await this.reloadList(1);
      }
    },
    toggleMode() {
      if (this.confirmDialog.visible || this.installDialog.visible) return;
      void this.switchMode(this.mode === "catalog" ? "installed" : "catalog");
    },
    async gotoPage(page) {
      if (this.mode !== "catalog") return;
      if (this.installDialog.visible || this.confirmDialog.visible) return;
      const target = Math.max(1, Math.min(this.totalPages, Number(page || 1)));
      if (target === Number(this.list.page || 1)) return;
      await this.reloadList(target);
    },
    cycleSort() {
      if (this.mode !== "catalog" || this.confirmDialog.visible || this.installDialog.visible) return;
      const current = this.sortOptions.indexOf(this.sort);
      this.sort = this.sortOptions[(current + 1) % this.sortOptions.length];
      void this.reloadList(1);
    },
    async launchInstalled(item) {
      if (!item || !item.game_id) return;
      try {
        const result = await apiPost("/api/tianyi/installed/launch", { game_id: item.game_id });
        if (result.status !== "success") throw new Error(result.message || "启动失败");
        this.flash(`已请求 Steam 启动：${item.title || item.game_id}`);
      } catch (error) {
        this.flash(String((error && error.message) || error));
      }
    },
    async openInstalledFolder(item) {
      if (!item || !item.game_id) return;
      try {
        const result = await apiPost("/api/tianyi/installed/open-folder", { game_id: item.game_id });
        if (result.status !== "success") throw new Error(result.message || "打开目录失败");
        this.flash("已请求打开安装目录");
      } catch (error) {
        this.flash(String((error && error.message) || error));
      }
    },
    askUninstallInstalled(item) {
      if (!item) return;
      const title = item.title || item.game_id || "该游戏";
      this.showConfirm(
        "卸载游戏",
        `确定卸载「${title}」吗？\n\n将删除安装目录：\n${item.install_path}\n\n如需同时回收 Proton 前缀，请到 QAM 面板卸载。`,
        () => this.performUninstallInstalled(item),
      );
    },
    async performUninstallInstalled(item) {
      try {
        const result = await apiPost("/api/tianyi/installed/uninstall", {
          game_id: item.game_id,
          install_path: item.install_path,
          delete_files: true,
        });
        if (result.status !== "success") throw new Error(result.message || "卸载失败");
        this.flash(`已卸载：${item.title || item.game_id}`);
        await this.reloadInstalled();
        await this.reloadList(this.list.page || 1);
      } catch (error) {
        this.flash(String((error && error.message) || error));
      }
    },
    focusedInstalledItem() {
      if (this.mode !== "installed") return null;
      const index = this.focusedIndex - this.cardStartIndex();
      return this.installed.items[index] || null;
    },
    openFocusedInstalledFolder() {
      if (this.confirmDialog.visible || this.installDialog.visible) return;
      const item = this.focusedInstalledItem();
      if (item) void this.openInstalledFolder(item);
    },
    askFocusedUninstall() {
      if (this.confirmDialog.visible || this.installDialog.visible) return;
      const item = this.focusedInstalledItem();
      if (item) this.askUninstallInstalled(item);
    },
    showConfirm(title, message, action) {
      this.confirmReturnIndex = this.focusedIndex;
      this.confirmDialog = {
        visible: true,
        title: String(title || ""),
        message: String(message || ""),
        action: typeof action === "function" ? action : null,
      };
      this.setFocusIndex(1, { scroll: false });
    },
    closeConfirm() {
      this.confirmDialog = { visible: false, title: "", message: "", action: null };
      this.setFocusIndex(this.confirmReturnIndex || 0, { scroll: false });
    },
    confirmAction() {
      const action = this.confirmDialog.action;
      const returnIndex = this.confirmReturnIndex || 0;
      this.confirmDialog = { visible: false, title: "", message: "", action: null };
      if (typeof action === "function") void action();
      this.setFocusIndex(returnIndex, { scroll: false });
    },
    openDiagnostics() {
      if (this.diagnosticsBusy) return;
      this.diagnosticsBusy = true;
      const link = document.createElement("a");
      link.href = "/api/tianyi/diagnostics/export";
      link.download = "freedeckcy-diagnostics.zip";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => {
        this.diagnosticsBusy = false;
        this.flash("诊断包已开始下载");
      }, 1500);
    },
    async checkUpdate() {
      if (this.updateBusy) return;
      this.updateBusy = true;
      try {
        const result = await apiGet("/api/tianyi/update-check");
        const info = result && result.data ? result.data : {};
        if (result.status !== "success" || info.ok === false) {
          this.flash(info.message || result.message || "检查更新失败");
          return;
        }
        if (info.has_update) {
          this.showConfirm(
            "发现新版本",
            `当前 v${info.current}，最新 v${info.latest}。是否打开 Release 页面？`,
            () => window.open(info.url, "_blank"),
          );
        } else {
          this.flash(`已是最新版本（v${info.current}）`);
        }
      } catch (error) {
        this.flash(String(error));
      } finally {
        this.updateBusy = false;
      }
    },
    getCoverCacheKey(item) {
      return String((item && item.game_id) || (item && item.title) || "").trim();
    },
    extractBuiltInCover(item) {
      const candidateKeys = ["cover_url", "cover", "image_url", "image", "pic_url", "pic", "thumbnail", "poster"];
      for (const key of candidateKeys) {
        const value = String((item && item[key]) || "").trim();
        if (!value) continue;
        if (value.startsWith("http://") || value.startsWith("https://") || value.startsWith("/")) {
          return value;
        }
      }
      return "";
    },
    buildSteamCoverCandidates(appIdRaw) {
      const appId = Number(appIdRaw || 0);
      if (!Number.isFinite(appId) || appId <= 0) return [];
      const id = Math.floor(appId);
      return [
        `https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/${id}/library_600x900_2x.jpg`,
        `https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/${id}/library_600x900.jpg`,
        `https://cdn.cloudflare.steamstatic.com/steam/apps/${id}/library_600x900_2x.jpg`,
        `https://cdn.cloudflare.steamstatic.com/steam/apps/${id}/library_600x900.jpg`,
        `https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/${id}/capsule_616x353.jpg`,
      ];
    },
    collectCoverCandidates(item) {
      const candidates = [];
      const seen = new Set();
      const push = (value) => {
        const url = String(value || "").trim();
        if (!url) return;
        if (
          !url.startsWith("http://")
          && !url.startsWith("https://")
          && !url.startsWith("/")
          && !url.startsWith("data:image/")
        ) {
          return;
        }
        if (seen.has(url)) return;
        seen.add(url);
        candidates.push(url);
      };

      const cacheKey = this.getCoverCacheKey(item);
      const meta = (cacheKey && this.coverMetaCache[cacheKey] && typeof this.coverMetaCache[cacheKey] === "object")
        ? this.coverMetaCache[cacheKey]
        : null;
      const appId = Number(
        (meta && meta.app_id) || (item && item.steam_appid) || (item && item.app_id) || 0,
      );

      push(item && item.cover_portrait_url);
      push(item && item.cover_url);
      push(meta && meta.square_cover_url);
      this.buildSteamCoverCandidates(appId).forEach((url) => push(url));
      push(meta && meta.cover_url);
      push(this.extractBuiltInCover(item));
      push(cacheKey && this.coverCache[cacheKey]);

      return candidates;
    },
    async prefetchCovers(items) {
      const queue = Array.isArray(items) ? items.filter(Boolean) : [];
      if (!queue.length) return;
      const workerCount = Math.max(1, Math.min(4, queue.length));
      let cursor = 0;
      const worker = async () => {
        while (cursor < queue.length) {
          const current = queue[cursor];
          cursor += 1;
          await this.fetchCoverForItem(current);
        }
      };
      const workers = Array.from({ length: workerCount }, () => worker());
      await Promise.all(workers);
    },
    async fetchCoverForItem(item, options = {}) {
      const cacheKey = this.getCoverCacheKey(item);
      if (!cacheKey) return;
      const force = Boolean(options && options.force);
      if (this.coverPending[cacheKey]) return;
      if (!force && this.coverMissCache[cacheKey]) return;
      if (force && this.coverMissCache[cacheKey]) delete this.coverMissCache[cacheKey];

      const builtInCover = this.extractBuiltInCover(item);
      if (builtInCover) {
        this.coverCache[cacheKey] = builtInCover;
        return;
      }

      this.coverPending[cacheKey] = true;
      try {
        const result = await apiGet("/api/tianyi/catalog/cover", {
          game_id: String((item && item.game_id) || ""),
          title: String((item && item.title) || ""),
          categories: String((item && item.categories) || ""),
        });
        const data = (result && result.data && typeof result.data === "object") ? result.data : {};
        const coverUrl = String(data.cover_url || "").trim();
        const squareCoverUrl = String(data.square_cover_url || "").trim();
        const protonTier = String(data.protondb_tier || "").trim();
        const appId = Number(data.app_id || 0);
        this.coverMetaCache[cacheKey] = {
          app_id: Number.isFinite(appId) ? appId : 0,
          proton_tier: protonTier,
          cover_url: coverUrl,
          square_cover_url: squareCoverUrl,
        };

        if (result && result.status === "success") {
          const preferred = this.collectCoverCandidates(item)[0] || "";
          if (preferred) {
            this.coverCache[cacheKey] = preferred;
          }
          if (preferred || coverUrl || squareCoverUrl || protonTier || appId > 0) {
            return;
          }
        }
        this.coverMissCache[cacheKey] = true;
      } catch (_error) {
        this.coverMissCache[cacheKey] = true;
      } finally {
        delete this.coverPending[cacheKey];
      }
    },
    coverFor(item) {
      const cacheKey = this.getCoverCacheKey(item);
      const candidates = this.collectCoverCandidates(item);
      if (candidates.length > 0) {
        const first = candidates[0];
        if (cacheKey) {
          this.coverCache[cacheKey] = first;
          if (!this.coverPending[cacheKey] && !this.coverMissCache[cacheKey]) {
            const meta = this.coverMetaCache[cacheKey];
            if (!meta || !meta.square_cover_url) {
              void this.fetchCoverForItem(item);
            }
          }
        }
        return first;
      }

      const placeholder = this.buildPlaceholderCover(item);
      if (cacheKey) {
        this.coverCache[cacheKey] = placeholder;
        if (!this.coverPending[cacheKey] && !this.coverMissCache[cacheKey]) {
          void this.fetchCoverForItem(item);
        }
      }
      return placeholder;
    },
    onCoverError(event, item) {
      if (!event || !event.target) return;
      const img = event.target;
      const attemptedRaw = String(img.dataset.coverAttempts || "").trim();
      const attempted = attemptedRaw ? attemptedRaw.split("||").filter(Boolean) : [];
      const current = String(img.getAttribute("src") || "").trim();
      if (current && !attempted.includes(current)) attempted.push(current);

      const candidates = this.collectCoverCandidates(item);
      const next = candidates.find((url) => !attempted.includes(url));
      if (next) {
        img.dataset.coverAttempts = [...attempted, next].join("||");
        img.src = next;
        return;
      }

      const cacheKey = this.getCoverCacheKey(item);
      if (cacheKey) this.coverMissCache[cacheKey] = true;
      img.src = this.buildPlaceholderCover(item);
    },
    buildPlaceholderCover(item) {
      const title = String((item && item.title) || "freedeckCY").trim();
      const category = String((item && item.categories) || "游戏").trim();
      const initials = title
        .replace(/\s+/g, " ")
        .split(/[\/\s\-_:]+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part.slice(0, 1).toUpperCase())
        .join("");
      const main = (initials || "G").slice(0, 2);
      const escapedTitle = title.replace(/[&<>"]/g, "");
      const escapedCategory = category.replace(/[&<>"]/g, "");
      const svg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#222222" />
      <stop offset="100%" stop-color="#0f0f0f" />
    </linearGradient>
  </defs>
  <rect width="600" height="600" fill="url(#bg)" />
  <circle cx="520" cy="110" r="140" fill="#303030" opacity="0.4" />
  <circle cx="120" cy="540" r="170" fill="#2a2a2a" opacity="0.35" />
  <text x="300" y="290" text-anchor="middle" font-size="118" fill="#f0f0f0" font-family="Roboto, Noto Sans SC, Microsoft YaHei" font-weight="500">${main}</text>
  <text x="44" y="498" font-size="30" fill="#d8d8d8" font-family="Roboto, Noto Sans SC, Microsoft YaHei">${escapedCategory}</text>
  <text x="44" y="542" font-size="22" fill="#bdbdbd" font-family="Roboto, Noto Sans SC, Microsoft YaHei">${escapedTitle.slice(0, 28)}</text>
</svg>`;
      return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
    },
    async openInstallConfirm(item) {
      if (!item || !item.game_id) return;
      const platform = String(item.platform || "pc").toLowerCase();
      const emulatorPlatforms = new Set(["pc", "gba", "psp", "nds"]);
      if (!emulatorPlatforms.has(platform)) {
        this.flash(`当前支持 PC / GBA / PSP / NDS，${platform.toUpperCase()} 暂未接入模拟器`);
        return;
      }
      void this.fetchCoverForItem(item, { force: true });
      this.installDialog.visible = true;
      this.installDialog.loading = true;
      this.installDialog.submitting = false;
      this.installDialog.plan = null;
      this.installDialog.game = item;
      this.setFocusIndex(0, { scroll: false });

      const result = await apiPost("/api/tianyi/install/prepare", {
        game_id: item.game_id,
        share_url: String(item.down_url || ""),
        download_dir: this.settings.download_dir,
        install_dir: this.settings.install_dir,
      });
      this.installDialog.loading = false;
      if (result.status !== "success") {
        const errorText = this.buildPrepareInstallError(result);
        this.flash(errorText);
        this.closeInstallDialog(true);
        return;
      }
      this.installDialog.plan = result.data || null;
      if (this.installDialog.plan && this.installDialog.plan.install_dir) {
        this.settings.install_dir = String(this.installDialog.plan.install_dir || this.settings.install_dir || "");
      }
      this.setFocusIndex(this.modalCanConfirm ? 1 : 0, { scroll: false });
    },
    closeInstallDialog(force = false) {
      if (!force && this.installDialog.submitting) return;
      this.installDialog.visible = false;
      this.installDialog.loading = false;
      this.installDialog.submitting = false;
      this.installDialog.plan = null;
      this.installDialog.game = null;
      this.setFocusIndex(0, { scroll: false });
    },
    async confirmInstall() {
      if (!this.installDialog.plan || !this.modalCanConfirm) return;
      this.installDialog.submitting = true;
      const plan = this.installDialog.plan;
      const fileIds = Array.isArray(plan.files)
        ? plan.files.map((item) => String((item && item.file_id) || "")).filter(Boolean)
        : [];

      const result = await apiPost("/api/tianyi/install/start", {
        game_id: String(plan.game_id || ""),
        share_url: String(plan.share_url || (this.installDialog.game && this.installDialog.game.down_url) || ""),
        file_ids: fileIds,
        split_count: this.settings.split_count,
        download_dir: this.settings.download_dir,
        install_dir: this.settings.install_dir,
      });
      this.installDialog.submitting = false;
      if (result.status !== "success") {
        this.flash(result.message || "创建安装任务失败");
        return;
      }
      this.flash("安装任务已创建，正在下载");
      this.closeInstallDialog(true);
    },
    formatBytes(bytes) {
      const num = Number(bytes || 0);
      if (!Number.isFinite(num) || num <= 0) return "0 B";
      const units = ["B", "KB", "MB", "GB", "TB"];
      let value = num;
      let idx = 0;
      while (value >= 1024 && idx < units.length - 1) {
        value /= 1024;
        idx += 1;
      }
      if (idx === 0) return `${Math.floor(value)} ${units[idx]}`;
      return `${value.toFixed(2)} ${units[idx]}`;
    },
    formatBytesCompact(bytes) {
      const num = Number(bytes || 0);
      if (!Number.isFinite(num) || num <= 0) return "0B";
      if (num >= 1024 ** 3) return `${(num / (1024 ** 3)).toFixed(2)}G`;
      if (num >= 1024 ** 2) return `${(num / (1024 ** 2)).toFixed(2)}M`;
      if (num >= 1024) return `${(num / 1024).toFixed(2)}K`;
      return `${Math.floor(num)}B`;
    },
    splitModalTitle(title) {
      const raw = String(title || "").replace(/\s+/g, " ").trim();
      if (!raw) {
        return { cn: "-", en: "GAME INSTALL" };
      }

      const sepParts = raw
        .split(/[\/|｜]/)
        .map((part) => part.trim())
        .filter(Boolean);
      if (sepParts.length >= 2) {
        const cn = (sepParts[0].match(/[\u3400-\u9FFF0-9A-Za-z：:·《》、（）()\-]+/g) || [sepParts[0]]).join("").trim() || "-";
        const en = sepParts.slice(1).join(" ").replace(/[^A-Za-z0-9\s:.'\-&!?()]/g, " ").replace(/\s+/g, " ").trim().toUpperCase() || "GAME INSTALL";
        return { cn, en };
      }

      const cnParts = raw.match(/[\u3400-\u9FFF0-9：:·《》、（）()]+/g) || [];
      const cn = cnParts.join("").trim() || raw;
      const englishMatches = raw.match(/[A-Za-z][A-Za-z0-9\s:.'\-&!?()]+/g) || [];
      const en = englishMatches.join(" ").replace(/\s+/g, " ").trim().toUpperCase();
      return { cn, en: en || "GAME INSTALL" };
    },
    modalChineseTitle(title) {
      return this.splitModalTitle(title).cn || "-";
    },
    modalEnglishTitle(title) {
      return this.splitModalTitle(title).en || "GAME INSTALL";
    },
    statusClass(ok) {
      return ok ? "space-ok" : "space-bad";
    },
  },
}).mount("#app");

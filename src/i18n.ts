// @ts-nocheck
import * as React from "react";
import { EN } from "./i18n.en";

export type Language = "zh" | "en";

const LANGUAGE_KEY = "freedeckcy.language";
const ATTRIBUTES = ["placeholder", "title", "aria-label", "aria-description"];
const CJK = /[\u3400-\u9fff]/;
const listeners = new Set<() => void>();
const originalText = new WeakMap<Text, string>();
const originalAttributes = new WeakMap<Element, Record<string, string>>();
const trackedText = new Set<Text>();

export function getLanguage(): Language {
    try {
        return localStorage.getItem(LANGUAGE_KEY) === "en" ? "en" : "zh";
    }
    catch {
        return "zh";
    }
}

export function hasLanguage(): boolean {
    try {
        return localStorage.getItem(LANGUAGE_KEY) === "zh" || localStorage.getItem(LANGUAGE_KEY) === "en";
    }
    catch {
        return false;
    }
}

export function setLanguage(language: Language): void {
    try {
        localStorage.setItem(LANGUAGE_KEY, language);
    }
    catch {
        // localStorage 不可用时本次会话仍切换。
    }
    applyLanguage();
    listeners.forEach((listener) => listener());
}

export function useLanguage(): Language {
    const [language, setCurrent] = React.useState<Language>(getLanguage);
    React.useEffect(() => {
        const listener = () => setCurrent(getLanguage());
        listeners.add(listener);
        return () => listeners.delete(listener);
    }, []);
    return language;
}

function translatePatterns(value: string): string {
    let output = value;
    const rules: Array<[RegExp, string]> = [
        [/(\d[\d,]*)\s*款游戏/g, "$1 games"],
        [/(\d[\d,]*)\s*款已安装/g, "$1 installed"],
        [/(\d[\d,]*)\s*款/g, "$1 items"],
        [/已显示\s*(\d+)\s*\/\s*(\d+)/g, "Showing $1 / $2"],
        [/第\s*(\d+)\s*\/\s*(\d+)\s*页/g, "Page $1 / $2"],
        [/剩余\s*([^）)]+)/g, "Free $1"],
        [/已登录[:：]\s*/g, "Signed in: "],
        [/未登录/g, "Not signed in"],
        [/(\d+)\s*分钟/g, "$1 min"],
        [/(\d+)\s*秒/g, "$1 s"],
        [/(\d+)\s*个文件/g, "$1 files"],
        [/(\d+)\s*个/g, "$1"],
    ];
    for (const [pattern, replacement] of rules) {
        output = output.replace(pattern, replacement);
    }
    return output;
}

export function translateString(value: string): string {
    if (!value || !CJK.test(value))
        return value;
    const exact = EN[value];
    if (exact !== undefined)
        return exact;
    let output = translatePatterns(value);
    if (output !== value && !CJK.test(output))
        return output;
    // 对拼接文案做短语级兜底：长词优先，避免“安装失败”被“安装”拆开。
    const keys = Object.keys(EN).filter((key) => key.length > 1 && CJK.test(key)).sort((a, b) => b.length - a.length);
    for (const key of keys) {
        if (output.includes(key))
            output = output.split(key).join(EN[key]);
    }
    return output;
}

function inScope(element: Element | null): boolean {
    try {
        return Boolean(element && element.closest("[data-fdc-i18n]"));
    }
    catch {
        return false;
    }
}

function translateTextNode(node: Text): void {
    if (!inScope(node.parentElement))
        return;
    if (getLanguage() === "en") {
        const current = node.nodeValue || "";
        if (!CJK.test(current))
            return;
        const original = originalText.get(node);
        if (original !== undefined && current === translateString(original))
            return;
        originalText.set(node, current);
        trackedText.add(node);
        const translated = translateString(current);
        if (translated !== current)
            node.nodeValue = translated;
        return;
    }
    const original = originalText.get(node);
    if (original !== undefined && node.nodeValue !== original) {
        node.nodeValue = original;
        trackedText.delete(node);
    }
}

function translateElementAttributes(element: Element): void {
    if (!inScope(element))
        return;
    let originals = originalAttributes.get(element);
    if (!originals) {
        originals = {};
        originalAttributes.set(element, originals);
    }
    for (const name of ATTRIBUTES) {
        const current = element.getAttribute(name);
        if (getLanguage() === "en") {
            if (!current || !CJK.test(current))
                continue;
            if (originals[name] === undefined || current !== translateString(originals[name]))
                originals[name] = current;
            const translated = translateString(originals[name]);
            if (translated !== current)
                element.setAttribute(name, translated);
        }
        else if (originals[name] !== undefined && current !== originals[name]) {
            element.setAttribute(name, originals[name]);
        }
    }
}

function scan(root: ParentNode): void {
    if (!root)
        return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node = walker.nextNode();
    while (node) {
        translateTextNode(node as Text);
        node = walker.nextNode();
    }
    if (root instanceof Element)
        translateElementAttributes(root);
    const elements = root.querySelectorAll ? root.querySelectorAll("*") : [];
    for (const element of Array.from(elements))
        translateElementAttributes(element);
}

export function applyLanguage(): void {
    if (typeof document === "undefined")
        return;
    if (getLanguage() !== "en") {
        for (const node of Array.from(trackedText)) {
            const original = originalText.get(node);
            if (original !== undefined && node.nodeValue !== original)
                node.nodeValue = original;
        }
    }
    scan(document.body);
}

let observerStarted = false;
function startObserver(): void {
    if (observerStarted || typeof document === "undefined")
        return;
    if (!document.body) {
        window.setTimeout(startObserver, 250);
        return;
    }
    observerStarted = true;
    const observer = new MutationObserver(() => {
        window.clearTimeout((window as any).__fdcI18nTimer);
        (window as any).__fdcI18nTimer = window.setTimeout(() => scan(document.body), 0);
    });
    observer.observe(document.body, {
        subtree: true,
        childList: true,
        characterData: true,
        attributes: true,
        attributeFilter: ATTRIBUTES,
    });
    applyLanguage();
}

if (typeof window !== "undefined")
    window.setTimeout(startObserver, 0);

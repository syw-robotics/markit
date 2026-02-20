#!/usr/bin/env python3
"""
Live Markdown Preview Server
实时 Markdown 预览服务器 - HTML 渲染，支持导出 PDF
"""

import os
import time
import yaml
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

PREVIEW_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{md_filename}</title>
    <link id="hljs-theme" rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
    <style>
        :root {
{css_vars}
            --bg-color: #f8f9fa;
            --border-color: #e2e8f0;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans CJK SC", sans-serif;
            background: var(--bg-color);
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        header {
            background: var(--header-bg);
            color: var(--header-text);
            height: {topbar_height}px;
            padding: 0 1.5rem;
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            align-items: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            flex-shrink: 0;
            position: relative;
            z-index: 100;
            transition: height 0.2s, padding 0.2s, opacity 0.2s;
            overflow: hidden;
        }

        header.hidden {
            height: 0 !important;
            padding: 0 !important;
            opacity: 0;
            box-shadow: none;
        }

        .header-toggle {
            position: fixed;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            z-index: 200;
            background: var(--header-bg);
            color: white;
            border: none;
            border-radius: 0 0 6px 6px;
            padding: 0 0.75rem;
            height: 14px;
            font-size: 0.6rem;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.2s, height 0.2s;
            line-height: 14px;
        }

        .header-toggle:hover { opacity: 1; height: 18px; line-height: 18px; }
        .header-toggle.peek { opacity: 0.7; }

        button {
            background: rgba(255,255,255,0.2);
            color: white;
            border: 1px solid rgba(255,255,255,0.3);
            padding: 0 0.75rem;
            height: {btn_height}px;
            line-height: 1;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.82rem;
            transition: all 0.2s;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
        }

        button:hover { background: rgba(255,255,255,0.3); }
        button.primary { background: #3182ce; border-color: #3182ce; }
        button.primary:hover { background: #2b6cb0; }

        .header-left { display: flex; gap: 0.5rem; align-items: center; }
        .header-filename { font-size: 0.9rem; font-weight: 600; text-align: center; opacity: 0.95; }
        .header-actions { display: flex; gap: 0.5rem; align-items: center; justify-content: flex-end; }

        @media print {
            header, .header-toggle, .toast { display: none !important; }
            body { height: auto !important; overflow: visible !important; background: white !important; }
            main { overflow: visible !important; height: auto !important; min-height: 0 !important; flex: none !important; display: block !important; background: white !important; padding: 0 !important; }
            .preview-content { box-shadow: none !important; margin: 0 auto !important; background: white !important; }
            .preview-content .table td, .preview-content .table th { background: transparent !important; }
        }

        main {
            flex: 1;
            overflow-y: auto;
            display: flex;
            justify-content: center;
            background: #e8eaed;
        }

        .preview-content {
            width: 100%;
            max-width: 860px;
            padding: 2.5rem 2rem;
            background: white;
            box-shadow: 0 0 12px rgba(0,0,0,0.08);
            margin: 1.5rem auto;
            align-self: flex-start;
            position: relative;
        }

        .preview-content .title {
            font-size: var(--font-size-title);
            color: var(--color-title);
            text-align: center;
            margin-bottom: var(--spacing-title-after);
            line-height: 1.3;
        }

        .preview-content .heading {
            font-size: var(--font-size-heading);
            color: var(--color-heading);
            margin-top: var(--spacing-heading-before);
            margin-bottom: var(--spacing-heading-after);
            line-height: 1.4;
        }

        .preview-content .subheading {
            font-size: var(--font-size-subheading);
            color: var(--color-subheading);
            margin-top: var(--spacing-subheading-before);
            margin-bottom: var(--spacing-subheading-after);
            line-height: 1.5;
        }

        .preview-content .subsubheading {
            font-size: var(--font-size-subsubheading);
            color: var(--color-subheading);
            margin-top: var(--spacing-subheading-before);
            margin-bottom: var(--spacing-subheading-after);
            line-height: 1.5;
        }

        .preview-content .paragraph {
            font-size: var(--font-size-normal);
            color: var(--color-text);
            margin-bottom: var(--spacing-normal-after);
            line-height: 1.6;
        }

        .preview-content .quote {
            border-left: 3px solid var(--color-heading);
            margin: 0.5rem 0 var(--spacing-normal-after) 0;
            padding: 0.4rem 1rem;
            color: #666;
            font-style: italic;
            background: #f9f9f9;
            border-radius: 0 4px 4px 0;
        }

        body.dark .preview-content .quote { background: #2d3748; color: #a0aec0; }

        .preview-content .code-wrapper {
            position: relative;
            margin-bottom: var(--spacing-code-after);
        }

        .preview-content .copy-btn {
            position: absolute;
            top: 0.4rem;
            right: 0.5rem;
            padding: 0.25rem;
            width: 26px;
            height: 26px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255,255,255,0.8);
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
            color: #555;
            opacity: 0;
            transition: opacity 0.15s;
        }

        .preview-content .code-wrapper:hover .copy-btn { opacity: 1; }

        .preview-content .code-block {
            background: var(--color-code-bg);
            margin: 0;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            overflow-x: auto;
        }

        .preview-content .code-block code {
            font-size: var(--font-size-code);
            line-height: 1.5;
            font-family: "SF Mono", "Consolas", "Monaco", monospace;
            background: none;
            padding: 0;
        }

        .preview-content .code-wrapper[data-lang] .code-block { padding-top: 1.8rem; }

        .preview-content .lang-label {
            position: absolute;
            top: 0.45rem;
            left: 1rem;
            font-size: 0.72rem;
            font-family: -apple-system, sans-serif;
            color: #888;
            display: flex;
            align-items: center;
            pointer-events: none;
        }

        .preview-content .list { margin-left: 1.25rem; margin-bottom: 0.5rem; }

        .preview-content .list li {
            font-size: var(--font-size-normal);
            color: var(--color-text);
            line-height: 1.6;
            margin-bottom: 0.25rem;
        }

        .preview-content .list li::marker { color: var(--color-subheading); }

        .preview-content .table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: var(--font-size-normal);
        }

        .preview-content .table thead { background: var(--color-table-header); }

        .preview-content .table th {
            color: var(--color-table-header-text);
            padding: 0.75rem;
            text-align: left;
            font-size: var(--font-size-table-header);
            font-weight: 500;
        }

        .preview-content .table td {
            background: var(--color-table-row);
            padding: 0.5rem 0.75rem;
            border: 1px solid var(--color-table-border);
        }

        .preview-content .divider {
            border: none;
            border-top: 1px solid var(--border-color);
            margin: 1.5rem 0;
        }

        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #f1f1f1; }
        ::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #a1a1a1; }

        body.dark {
{dark_css_vars}
        }

        body.dark main { background: var(--bg-color); }
        body.dark .preview-content { background: var(--surface-color); box-shadow: 0 0 12px rgba(0,0,0,0.4); color: var(--color-text); }
        body.dark .preview-content .code-block { background: var(--color-code-bg); }
        body.dark .preview-content .copy-btn { background: rgba(45,55,72,0.9); border-color: var(--color-table-border); color: var(--color-text); }
        body.dark .preview-content .table td { background: var(--color-table-row); color: var(--color-text); }
        body.dark .preview-content .list li { color: var(--color-text); }
        body.dark .preview-content .paragraph { color: var(--color-text); }
        body.dark .hljs { background: var(--color-code-bg); color: var(--color-code-text); }

        .toast {
            position: fixed;
            top: 4.5rem;
            left: 50%;
            transform: translateX(-50%) translateY(-1rem);
            background: #1a202c;
            color: #e2e8f0;
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            font-size: 0.85rem;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
            opacity: 0;
            transition: opacity 0.2s, transform 0.2s;
            pointer-events: none;
            max-width: 80vw;
            word-break: break-all;
            z-index: 9999;
        }
        .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
        .toast .toast-label { color: #68d391; font-weight: 600; margin-right: 0.4rem; }
        .toast.error .toast-label { color: #fc8181; }

        .theme-dropdown {
            position: fixed;
            top: auto;
            left: auto;
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            overflow: hidden;
            z-index: 500;
            min-width: 160px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
            display: none;
        }
        .theme-dropdown.open { display: block; }

        .toc-panel {
            position: fixed;
            top: 50%;
            left: 0;
            transform: translateY(-50%);
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 0 8px 8px 0;
            z-index: 500;
            width: 220px;
            max-height: 70vh;
            overflow-y: auto;
            box-shadow: 4px 0 16px rgba(0,0,0,0.2);
            display: none;
            padding: 0.5rem 0;
        }
        .toc-panel.open { display: block; }
        .toc-item {
            padding: 0.35rem 1rem;
            font-size: 0.85rem;
            color: var(--color-text);
            cursor: pointer;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .toc-item:hover { background: rgba(255,255,255,0.15); }
        .toc-item.h2 { padding-left: 1.75rem; font-size: 0.82rem; color: var(--color-heading); }
        .toc-item.h3 { padding-left: 2.5rem; font-size: 0.78rem; color: var(--color-subheading); }
        .toc-item.h4 { padding-left: 3.25rem; font-size: 0.74rem; color: var(--color-subheading); opacity: 0.7; }
        .theme-dropdown-item {
            padding: 0.5rem 1rem;
            font-size: 0.82rem;
            color: var(--color-text);
            cursor: pointer;
            white-space: nowrap;
        }
        .theme-dropdown-item:hover { background: rgba(100,100,100,0.12); }
        .theme-dropdown-item.active { color: #4a9eff; font-weight: 600; background: rgba(74,158,255,0.15); }
        #theme-btn-wrap { position: relative; display: inline-flex; }

        .kb-modal-overlay {
            display: none;
            position: fixed; inset: 0;
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .kb-modal-overlay.open { display: flex; }
        .kb-modal {
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            padding: 1.25rem 1.5rem;
            min-width: 280px;
            max-width: 90vw;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            color: var(--color-text);
        }
        .kb-modal h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.75rem; color: var(--color-heading); letter-spacing: 0.05em; text-transform: uppercase; }
        .kb-row { display: flex; justify-content: space-between; align-items: center; padding: 0.3rem 0; font-size: 1rem; gap: 2rem; color: var(--color-text); }
        .kb-row + .kb-row { border-top: 1px solid rgba(255,255,255,0.1); }
        .kb-key { background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25); border-radius: 4px; padding: 0.1rem 0.45rem; font-family: monospace; font-size: 0.95rem; color: var(--color-subheading); white-space: nowrap; }
    </style>
</head>
<body>
    <button class="header-toggle" id="header-toggle" onclick="toggleHeader()">▲</button>
    <header id="header">
        <div class="header-left" id="header-left"></div>
        <div class="header-filename">{md_filename}</div>
        <div class="header-actions" id="header-actions"></div>
    </header>
    <main id="main">
        <div class="preview-content" id="preview"></div>
    </main>
    <div class="kb-modal-overlay" id="kb-overlay" onclick="if(event.target===this)this.classList.remove('open')">
        <div class="kb-modal" id="kb-modal"></div>
    </div>
    <div id="toc-panel" class="toc-panel"></div>

    <script>
        const preview = document.getElementById('preview');
        const mainEl = document.getElementById('main');
        const headerEl = document.getElementById('header');
        const headerToggle = document.getElementById('header-toggle');

        // --- 按钮布局配置 ---
        const btnLayout = {btn_layout};

        let autoRefresh = true;
        let lastHtml = '';
        let exportStatus = null;
        let lang = '{init_lang}';

        const i18n = {
            zh: { autoOn: '自动刷新', autoOff: '✕ 已暂停', export: '导出 PDF', langBtn: '中/EN',
                  kb_title: '快捷键', kb_export: '导出 PDF', kb_dark: '切换暗色模式',
                  kb_theme: '切换主题', kb_topbar: '显示/隐藏顶栏', kb_auto: '切换自动刷新', kb_lang: '切换语言', kb_toc: '目录' },
            en: { autoOn: 'Auto Refresh', autoOff: '✕ Paused', export: 'Export PDF', langBtn: 'EN/中',
                  kb_title: 'Keybindings', kb_export: 'Export PDF', kb_dark: 'Toggle dark mode',
                  kb_theme: 'Switch theme', kb_topbar: 'Toggle topbar', kb_auto: 'Toggle auto refresh', kb_lang: 'Toggle language', kb_toc: 'Table of contents' }
        };
        function t(key) { return i18n[lang][key]; }

        const copyIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;
        const checkIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;

        const deviconMap = {
            python: 'python', javascript: 'javascript', js: 'javascript',
            typescript: 'typescript', ts: 'typescript', cpp: 'cplusplus',
            'c++': 'cplusplus', c: 'c', java: 'java', go: 'go',
            rust: 'rust', bash: 'bash', sh: 'bash', shell: 'bash',
            html: 'html5', css: 'css3', json: 'json', yaml: 'yaml',
            sql: 'mysql', docker: 'docker', kotlin: 'kotlin', swift: 'swift',
            ruby: 'ruby', php: 'php', r: 'r', scala: 'scala',
        };

        // --- 按钮定义 ---
        const hljsTheme = document.getElementById('hljs-theme');
        let darkBtn, autoRefreshBtn;

        const btnDefs = {
            dark: () => {
                const b = document.createElement('button');
                b.id = 'dark-btn';
                b.onclick = toggleDark;
                darkBtn = b;
                return b;
            },
            lang: () => {
                const b = document.createElement('button');
                b.id = 'lang-btn';
                b.onclick = toggleLang;
                return b;
            },
            auto_refresh: () => {
                const b = document.createElement('button');
                b.id = 'auto-refresh-btn';
                b.onclick = toggleAutoRefresh;
                autoRefreshBtn = b;
                return b;
            },
            export_pdf: () => {
                const b = document.createElement('button');
                b.className = 'primary';
                b.onclick = exportPDF;
                return b;
            },
            theme_switcher: () => {
                const wrap = document.createElement('div');
                wrap.id = 'theme-btn-wrap';
                const b = document.createElement('button');
                b.id = 'theme-btn';
                b.textContent = '🎨';
                b.onclick = toggleThemeDropdown;
                const dd = document.createElement('div');
                dd.className = 'theme-dropdown';
                dd.id = 'theme-dropdown';
                wrap.appendChild(b);
                wrap.appendChild(dd);
                return wrap;
            },
            keybindings: () => {
                const b = document.createElement('button');
                b.id = 'kb-btn';
                b.textContent = '⌨';
                b.onclick = toggleKbModal;
                return b;
            },
            toc: () => {
                const wrap = document.createElement('div');
                wrap.id = 'toc-btn-wrap';
                const b = document.createElement('button');
                b.id = 'toc-btn';
                b.textContent = '☰';
                b.onclick = toggleToc;
                wrap.appendChild(b);
                return wrap;
            },
        };

        function buildButtons() {
            const left = document.getElementById('header-left');
            const right = document.getElementById('header-actions');
            (btnLayout.left || []).forEach(id => { if (btnDefs[id]) left.appendChild(btnDefs[id]()); });
            (btnLayout.right || []).forEach(id => { if (btnDefs[id]) right.appendChild(btnDefs[id]()); });
        }

        // --- 功能函数 ---
        function toggleHeader() {
            const hidden = headerEl.classList.toggle('hidden');
            headerToggle.textContent = hidden ? '▼' : '▲';
        }

        document.addEventListener('mousemove', e => {
            if (headerEl.classList.contains('hidden')) {
                headerToggle.classList.toggle('peek', e.clientY < 20);
            } else {
                headerToggle.classList.toggle('peek', e.clientY < headerEl.offsetHeight);
            }
        });

        let currentTheme = '{init_theme_name}';
        let currentDarkVars = {};  // populated by selectTheme, used by toggleDark

        function applyDarkVars(isDark) {
            const root = document.documentElement;
            if (isDark && Object.keys(currentDarkVars).length) {
                Object.entries(currentDarkVars).forEach(([k, v]) => root.style.setProperty(k, v));
            } else if (!isDark) {
                // restore light vars by reloading from server
                fetch('/api/theme').then(r => r.json()).then(vars => {
                    Object.entries(vars).forEach(([k, v]) => {
                        if (!k.startsWith('--font-size') && !k.startsWith('--spacing'))
                            root.style.setProperty(k, v);
                    });
                });
            }
        }

        function toggleDark() {
            document.body.classList.toggle('dark');
            const isDark = document.body.classList.contains('dark');
            hljsTheme.href = isDark
                ? 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css'
                : 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css';
            applyDarkVars(isDark);
            applyLang();
        }

        function toggleThemeDropdown() {
            const dd = document.getElementById('theme-dropdown');
            if (dd.classList.contains('open')) { dd.classList.remove('open'); return; }
            const btn = document.getElementById('theme-btn');
            const rect = btn.getBoundingClientRect();
            dd.style.left = rect.left + 'px';
            dd.style.top = (rect.bottom + 4) + 'px';
            dd.innerHTML = '<div class="theme-dropdown-item" style="color:#888;font-size:0.75rem">Loading...</div>';
            dd.classList.add('open');
            fetch('/api/themes').then(r => r.json()).then(themes => {
                dd.innerHTML = themes.map(t =>
                    `<div class="theme-dropdown-item${t.name === currentTheme ? ' active' : ''}" onclick="selectTheme('${t.name}')">${t.label}</div>`
                ).join('');
                themeNavIdx = themes.findIndex(t => t.name === currentTheme);
                const items = dd.querySelectorAll('.theme-dropdown-item');
                if (themeNavIdx >= 0) items[themeNavIdx].style.background = 'rgba(74,158,255,0.15)';
            });
        }

        function selectTheme(name) {
            document.getElementById('theme-dropdown').classList.remove('open');
            if (name === currentTheme) return;
            fetch('/api/set-theme?name=' + encodeURIComponent(name))
                .then(r => r.json()).then(vars => {
                    currentTheme = name;
                    currentDarkVars = vars.dark || {};
                    delete vars.dark;
                    const root = document.documentElement;
                    const isDark = document.body.classList.contains('dark');
                    Object.entries(isDark ? currentDarkVars : vars).forEach(([k, v]) => root.style.setProperty(k, v));
                });
        }

        document.addEventListener('click', e => {
            const wrap = document.getElementById('theme-btn-wrap');
            if (wrap && !wrap.contains(e.target)) document.getElementById('theme-dropdown').classList.remove('open');
        });

        function toggleLang() {
            lang = lang === 'zh' ? 'en' : 'zh';
            applyLang();
        }

        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            if (autoRefreshBtn) {
                autoRefreshBtn.textContent = autoRefresh ? t('autoOn') : t('autoOff');
                autoRefreshBtn.style.background = autoRefresh ? '' : 'rgba(255,100,100,0.3)';
            }
        }

        function applyLang() {
            if (autoRefreshBtn) autoRefreshBtn.textContent = autoRefresh ? t('autoOn') : t('autoOff');
            if (darkBtn) darkBtn.textContent = document.body.classList.contains('dark') ? '☀️' : '🌙';
            const langBtn = document.getElementById('lang-btn');
            if (langBtn) langBtn.textContent = t('langBtn');
            const exportBtn = document.querySelector('.primary');
            if (exportBtn) exportBtn.textContent = t('export');
            preview.querySelectorAll('.copy-btn').forEach(b => {
                if (!b.classList.contains('copied')) b.innerHTML = copyIcon;
            });
            renderKbModal();
        }

        function kbRow(key, desc) {
            return key ? `<div class="kb-row"><span>${desc}</span><span class="kb-key">${key}</span></div>` : '';
        }

        function renderKbModal() {
            const modal = document.getElementById('kb-modal');
            if (!modal) return;
            modal.innerHTML = `<h3>${t('kb_title')}</h3>` +
                kbRow(hotkeys.export_pdf, t('kb_export')) +
                kbRow(hotkeys.toggle_dark, t('kb_dark')) +
                kbRow(hotkeys.toggle_theme, t('kb_theme')) +
                kbRow(hotkeys.toggle_topbar, t('kb_topbar')) +
                kbRow(hotkeys.toggle_auto_refresh, t('kb_auto')) +
                kbRow(hotkeys.toggle_lang, t('kb_lang')) +
                kbRow(hotkeys.toggle_toc, t('kb_toc'));
        }

        function toggleKbModal() {
            const overlay = document.getElementById('kb-overlay');
            const isOpen = overlay.classList.toggle('open');
            if (isOpen) renderKbModal();
        }

        function toggleToc() {
            const panel = document.getElementById('toc-panel');
            if (panel.classList.contains('open')) { panel.classList.remove('open'); return; }
            const headings = preview.querySelectorAll('h1,h2,h3,h4');
            if (!headings.length) { panel.innerHTML = '<div class="toc-item" style="color:#718096">No headings</div>'; }
            else {
                headings.forEach((h, idx) => { if (!h.id) h.id = 'heading-' + idx; });
                panel.innerHTML = Array.from(headings).map(h => {
                    const cls = {H1:'',H2:' h2',H3:' h3',H4:' h4'}[h.tagName] || '';
                    return `<div class="toc-item${cls}" onclick="document.getElementById('${h.id}').scrollIntoView({behavior:'smooth'})">${h.textContent}</div>`;
                }).join('');
            }
            panel.classList.add('open');
        }

        let contentZoom = {init_zoom};
        function applyZoom() { mainEl.style.zoom = contentZoom; }
        applyZoom();
        document.addEventListener('wheel', e => {
            if (!e.ctrlKey) return;
            e.preventDefault();
            contentZoom = Math.min(3, Math.max(0.3, contentZoom + (e.deltaY < 0 ? 0.1 : -0.1)));
            applyZoom();
        }, { passive: false });
        document.addEventListener('keydown', e => {
            if (!e.ctrlKey) return;
            if (e.key === '=' || e.key === '+') { e.preventDefault(); contentZoom = Math.min(3, contentZoom + 0.1); applyZoom(); }
            if (e.key === '-') { e.preventDefault(); contentZoom = Math.max(0.3, contentZoom - 0.1); applyZoom(); }
            if (e.key === '0') { e.preventDefault(); contentZoom = 1.0; applyZoom(); }
        });

        function addCopyButtons() {
            preview.querySelectorAll('.code-wrapper').forEach(wrapper => {
                if (wrapper.querySelector('.copy-btn')) return;
                const rawLang = wrapper.dataset.lang;
                if (rawLang && !wrapper.querySelector('.lang-label')) {
                    const label = document.createElement('span');
                    label.className = 'lang-label';
                    const slug = deviconMap[rawLang.toLowerCase()];
                    const display = rawLang.charAt(0).toUpperCase() + rawLang.slice(1).toLowerCase();
                    label.innerHTML = slug
                        ? `<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/${slug}/${slug}-original.svg" width="13" height="13" style="vertical-align:middle;margin-right:3px"> ${display}`
                        : display;
                    wrapper.appendChild(label);
                }
                const btn = document.createElement('button');
                btn.className = 'copy-btn';
                btn.innerHTML = copyIcon;
                btn.onclick = () => {
                    navigator.clipboard.writeText(wrapper.querySelector('code').innerText).then(() => {
                        btn.innerHTML = checkIcon;
                        btn.classList.add('copied');
                        setTimeout(() => { btn.innerHTML = copyIcon; btn.classList.remove('copied'); }, 1500);
                    });
                };
                wrapper.appendChild(btn);
            });
        }

        function loadContent() {
            fetch('/api/content')
                .then(r => r.json())
                .then(data => {
                    if (data.html !== lastHtml) {
                        lastHtml = data.html;
                        preview.innerHTML = data.html;
                        preview.querySelectorAll('pre code[class]').forEach(el => hljs.highlightElement(el));
                        addCopyButtons();
                        mermaid.run({ nodes: preview.querySelectorAll('.mermaid') });
                        renderMathInElement(preview, { delimiters: [
                            {left: '$$', right: '$$', display: true},
                            {left: '$', right: '$', display: false}
                        ], throwOnError: false });
                    }
                });
        }

        let toastTimer = null;
        function showToast(label, msg, isError) {
            let toast = document.getElementById('toast');
            if (!toast) {
                toast = document.createElement('div');
                toast.id = 'toast';
                toast.className = 'toast';
                document.body.appendChild(toast);
            }
            toast.className = 'toast' + (isError ? ' error' : '');
            toast.innerHTML = `<span class="toast-label">${label}</span>${msg}`;
            requestAnimationFrame(() => toast.classList.add('show'));
            clearTimeout(toastTimer);
            toastTimer = setTimeout(() => { toast.classList.remove('show'); }, 5000);
        }

        function exportPDF() {
            if (exportStatus) return;
            exportStatus = true;
            showToast('⏳', lang === 'zh' ? '正在生成 PDF...' : 'Generating PDF...', false);
            fetch('/api/export-pdf')
                .then(r => r.ok ? r.text() : Promise.reject())
                .then(path => { showToast('✅', (lang === 'zh' ? '导出 PDF 到 ' : 'Exported PDF to ') + path, false); })
                .catch(() => { showToast('❌', lang === 'zh' ? '导出失败' : 'Export failed', true); })
                .finally(() => { exportStatus = null; });
        }

        // --- 快捷键 ---
        const hotkeys = {hotkeys};
        let themeNavIdx = -1;

        document.addEventListener('keydown', e => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.ctrlKey || e.metaKey || e.altKey) return;
            const k = e.key.toLowerCase();
            const dd = document.getElementById('theme-dropdown');
            const ddOpen = dd && dd.classList.contains('open');
            const kbOpen = document.getElementById('kb-overlay').classList.contains('open');

            // kb modal: k or Escape closes
            if (kbOpen) {
                if (e.key === 'Escape' || (hotkeys.keybindings && k === hotkeys.keybindings)) toggleKbModal();
                return;
            }

            // theme dropdown: arrow nav, t or Escape closes
            if (ddOpen) {
                const items = dd.querySelectorAll('.theme-dropdown-item');
                if (e.key === 'ArrowDown') { e.preventDefault(); themeNavIdx = (themeNavIdx + 1) % items.length; items.forEach((el, i) => el.style.background = i === themeNavIdx ? 'rgba(74,158,255,0.15)' : ''); }
                else if (e.key === 'ArrowUp') { e.preventDefault(); themeNavIdx = (themeNavIdx - 1 + items.length) % items.length; items.forEach((el, i) => el.style.background = i === themeNavIdx ? 'rgba(74,158,255,0.15)' : ''); }
                else if (e.key === 'Enter' && themeNavIdx >= 0) { e.preventDefault(); items[themeNavIdx].click(); themeNavIdx = -1; }
                else if (e.key === 'Escape' || (hotkeys.toggle_theme && k === hotkeys.toggle_theme)) { dd.classList.remove('open'); themeNavIdx = -1; }
                return;
            }

            if (hotkeys.export_pdf && k === hotkeys.export_pdf) exportPDF();
            else if (hotkeys.toggle_dark && k === hotkeys.toggle_dark) toggleDark();
            else if (hotkeys.toggle_theme && k === hotkeys.toggle_theme) { themeNavIdx = -1; toggleThemeDropdown(); }
            else if (hotkeys.toggle_topbar && k === hotkeys.toggle_topbar) toggleHeader();
            else if (hotkeys.toggle_auto_refresh && k === hotkeys.toggle_auto_refresh) toggleAutoRefresh();
            else if (hotkeys.toggle_lang && k === hotkeys.toggle_lang) toggleLang();
            else if (hotkeys.keybindings && k === hotkeys.keybindings) toggleKbModal();
            else if (hotkeys.toggle_toc && k === hotkeys.toggle_toc) toggleToc();
        });

        // --- 初始化 ---
        buildButtons();
        if ('{init_theme}' === 'dark') toggleDark();
        if ('{init_topbar}' === 'false') toggleHeader();
        applyLang();
        loadContent();
        setInterval(() => { if (autoRefresh) loadContent(); }, 1500);
    </script>
</body>
</html>
"""

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
from threading import Thread
import webbrowser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import socket
import re


class ThemeManager:
    """主题管理器"""

    def __init__(self, config_dir=None):
        self.base_dir = config_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
        self.config = self._load_config()

    def _load_config(self):
        main_cfg_path = os.path.join(self.base_dir, 'config.yaml')
        if not os.path.exists(main_cfg_path):
            # 兼容旧路径
            old = os.path.join(os.path.dirname(self.base_dir), 'theme_config.yaml')
            if os.path.exists(old):
                with open(old, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            return {}
        with open(main_cfg_path, 'r', encoding='utf-8') as f:
            main = yaml.safe_load(f) or {}
        theme_name = main.get('theme', 'default')
        theme_path = os.path.join(self.base_dir, 'themes', f'{theme_name}.yaml')
        if not os.path.exists(theme_path):
            theme_path = os.path.join(self.base_dir, 'themes', 'default.yaml')
        theme_cfg = {}
        if os.path.exists(theme_path):
            with open(theme_path, 'r', encoding='utf-8') as f:
                theme_cfg = yaml.safe_load(f) or {}
        # 合并：main 中的 preview/buttons/font_sizes/spacing 保留，theme 文件提供颜色等
        result = dict(theme_cfg)
        result['preview'] = main.get('preview', {})
        result['buttons'] = main.get('buttons', {})
        result['font_sizes'] = main.get('font_sizes', theme_cfg.get('font_sizes', {}))
        result['spacing'] = main.get('spacing', theme_cfg.get('spacing', {}))
        result['hotkeys'] = main.get('hotkeys', {})
        result['theme'] = theme_name
        result['author'] = main.get('author', '')
        result['pdf'] = main.get('pdf', {})
        return result

    def get_color(self, key, default='#000000'):
        """获取颜色"""
        return self.config.get('colors', {}).get(key, default)

    def get_font_size(self, key, default=11):
        """获取字体大小"""
        return self.config.get('font_sizes', {}).get(key, default)

    def get_spacing(self, key, default=0.2):
        """获取间距"""
        return self.config.get('spacing', {}).get(key, default)

    def get_output_filename(self):
        """获取输出文件名"""
        return self.config.get('output', {}).get('filename', 'output.pdf')

    def to_html_vars(self):
        """转换为 HTML CSS 变量"""
        return {
            '--color-title': self.get_color('title', '#1a365d'),
            '--color-heading': self.get_color('heading', '#2c5282'),
            '--color-subheading': self.get_color('subheading', '#2f855a'),
            '--color-text': self.get_color('text', '#1a202c'),
            '--color-code-bg': self.get_color('code_bg', '#f7fafc'),
            '--color-code-text': self.get_color('code_text', '#1a202c'),
            '--color-table-header': self.get_color('table_header', '#2c5282'),
            '--color-table-header-text': self.get_color('table_header_text', '#ffffff'),
            '--color-table-row': self.get_color('table_row', '#ebf8ff'),
            '--color-table-border': self.get_color('table_border', '#a0aec0'),
            '--color-link': self.get_color('link', '#3182ce'),
            '--header-bg': self.get_color('topbar_bg', 'linear-gradient(135deg, #1a365d 0%, #2c5282 100%)'),
            '--header-text': self.get_color('topbar_text', '#ffffff'),

            '--font-size-title': self.get_font_size('title', 28),
            '--font-size-heading': self.get_font_size('heading', 18),
            '--font-size-subheading': self.get_font_size('subheading', 14),
            '--font-size-subsubheading': self.get_font_size('subsubheading', 12),
            '--font-size-normal': self.get_font_size('normal', 11),
            '--font-size-code': self.get_font_size('code', 9),
            '--font-size-table-header': self.get_font_size('table_header', 12),

            '--spacing-title-after': self.get_spacing('title_after', 0.5),
            '--spacing-heading-before': self.get_spacing('heading_before', 0.4),
            '--spacing-heading-after': self.get_spacing('heading_after', 0.3),
            '--spacing-subheading-before': self.get_spacing('subheading_before', 0.3),
            '--spacing-subheading-after': self.get_spacing('subheading_after', 0.2),
            '--spacing-normal-after': self.get_spacing('normal_after', 0.2),
            '--spacing-code-after': self.get_spacing('spacing_after', 0.3),
        }

    def _get_dark(self, key, default):
        return self.config.get('dark_colors', {}).get(key, default)

    def to_dark_html_vars(self):
        """转换为 dark mode CSS 变量"""
        return {
            '--color-title': self._get_dark('title', '#90cdf4'),
            '--color-heading': self._get_dark('heading', '#63b3ed'),
            '--color-subheading': self._get_dark('subheading', '#68d391'),
            '--color-text': self._get_dark('text', '#e2e8f0'),
            '--color-code-bg': self._get_dark('code_bg', '#2d3748'),
            '--color-code-text': self._get_dark('code_text', '#e2e8f0'),
            '--color-table-header': self._get_dark('table_header', '#2c5282'),
            '--color-table-header-text': self._get_dark('table_header_text', '#e2e8f0'),
            '--color-table-row': self._get_dark('table_row', '#1e3a5f'),
            '--color-table-border': self._get_dark('table_border', '#4a5568'),
            '--bg-color': self._get_dark('bg', '#1a1a2e'),
            '--surface-color': self._get_dark('surface', '#1e2433'),
            '--header-bg': self._get_dark('topbar_bg', 'linear-gradient(135deg, #1a365d 0%, #2c5282 100%)'),
            '--header-text': self._get_dark('topbar_text', '#ffffff'),
        }


class MarkdownToHTML:
    """Markdown 转 HTML"""

    def __init__(self, theme):
        self.theme = theme

    def _escape_html(self, text):
        """转义 HTML 特殊字符，保护 LaTeX 公式不被转义"""
        placeholders = []
        def save(m):
            placeholders.append(m.group(0))
            return f'\x00MATH{len(placeholders)-1}\x00'
        text = re.sub(r'\$\$[\s\S]*?\$\$|\$[^$\n]+?\$', save, text)
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        for i, formula in enumerate(placeholders):
            text = text.replace(f'\x00MATH{i}\x00', formula)
        return text

    def _inline(self, text):
        """处理内联 Markdown 格式"""
        # 保护行内代码不被其他规则处理
        codes = []
        def save_code(m):
            codes.append(f'<code>{self._escape_html(m.group(1))}</code>')
            return f'\x00CODE{len(codes)-1}\x00'
        text = re.sub(r'`([^`]+)`', save_code, text)
        # 加粗斜体 ***text***
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        # 加粗 **text**
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # 斜体 *text*
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        # 删除线 ~~text~~
        text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)
        # 链接 [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color:var(--color-link)">\1</a>', text)
        # 还原行内代码
        for i, code in enumerate(codes):
            text = text.replace(f'\x00CODE{i}\x00', code)
        return text

    def _format_code(self, code):
        """格式化代码 - 过滤注释"""
        lines = code.split('\n')
        result = []
        for line in lines:
            # 过滤 Python 注释（# 开头的）
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            # 过滤 C++/JS 注释（// 开头的）
            if stripped.startswith('//'):
                continue
            # 过滤块注释（/* ... */ 和 <!-- ... -->）
            if stripped.startswith('/*') or stripped.startswith('<!--'):
                continue
            result.append('<code class="line">' + self._escape_html(line.rstrip()) + '</code>')
        return '\n'.join(result)

    def parse(self, markdown_content):
        """解析 Markdown 为 HTML"""
        lines = markdown_content.split('\n')
        i = 0
        n = len(lines)
        html = []
        in_list = False
        in_ordered = False

        def close_list():
            nonlocal in_list, in_ordered
            if in_list:
                html.append('</ol>' if in_ordered else '</ul>')
                in_list = False
                in_ordered = False

        while i < n:
            line = lines[i]

            # 空行
            if not line.strip():
                i += 1
                continue

            # 标题
            if line.startswith('# '):
                if in_list:
                    close_list()
                html.append(f'<h1 class="title">{self._inline(self._escape_html(line[2:].strip()))}</h1>')

            elif line.startswith('## '):
                if in_list:
                    close_list()
                html.append(f'<h2 class="heading">{self._inline(self._escape_html(line[3:].strip()))}</h2>')

            elif line.startswith('### '):
                if in_list:
                    close_list()
                html.append(f'<h3 class="subheading">{self._inline(self._escape_html(line[4:].strip()))}</h3>')

            elif line.startswith('#### '):
                if in_list:
                    close_list()
                html.append(f'<h4 class="subsubheading">{self._inline(self._escape_html(line[5:].strip()))}</h4>')

            elif line.startswith('##### '):
                if in_list:
                    close_list()
                html.append(f'<h4 class="subsubheading">{self._inline(self._escape_html(line[6:].strip()))}</h4>')

            # 引用块
            elif line.startswith('>'):
                if in_list:
                    close_list()
                quote_lines = []
                while i < n and lines[i].startswith('>'):
                    quote_lines.append(lines[i].lstrip('>').strip())
                    i += 1
                html.append(f'<blockquote class="quote">{self._inline(self._escape_html(" ".join(quote_lines)))}</blockquote>')
                continue

            # 代码块
            elif line.strip().startswith('```'):
                lang = line.strip()[3:].strip()
                code_lines = []
                i += 1
                while i < n and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                if code_lines:
                    code = '\n'.join(code_lines)
                    if in_list:
                        close_list()
                    if lang.lower() == 'mermaid':
                        html.append(f'<div class="mermaid">{self._escape_html(code)}</div>')
                    else:
                        lang_attr = f' data-lang="{self._escape_html(lang)}"' if lang else ''
                        lang_class = f' class="{self._escape_html(lang)}"' if lang else ''
                        html.append(f'<div class="code-wrapper"{lang_attr}><pre class="code-block"><code{lang_class}>{self._escape_html(code)}</code></pre></div>')

            # 列表
            elif re.match(r'^\s*[-*]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                is_ordered = bool(re.match(r'^\s*\d+\.\s+', line))
                match = re.match(r'^\s*[-*]\s+(.+)', line) or re.match(r'^\s*\d+\.\s+(.+)', line)
                if match:
                    if not in_list:
                        tag = 'ol' if is_ordered else 'ul'
                        html.append(f'<{tag} class="list">')
                        in_list = True
                        in_ordered = is_ordered
                    elif is_ordered != in_ordered:
                        html.append('</ol>' if in_ordered else '</ul>')
                        tag = 'ol' if is_ordered else 'ul'
                        html.append(f'<{tag} class="list">')
                        in_ordered = is_ordered
                    html.append(f'<li>{self._inline(self._escape_html(match.group(1)))}</li>')
                i += 1
                continue

            # 表格
            elif '|' in line and i + 1 < n and '|' in lines[i + 1]:
                if in_list:
                    close_list()
                table_data = []
                while i < n and '|' in lines[i]:
                    row = [cell.strip() for cell in lines[i].split('|')[1:-1]]
                    if row and row[0] and not all(re.match(r'^[-:]+$', c) for c in row):
                        table_data.append(row)
                    i += 1
                if len(table_data) > 1:
                    html.append('<table class="table">')
                    # 表头
                    html.append('<thead><tr>')
                    for cell in table_data[0]:
                        html.append(f'<th>{self._inline(self._escape_html(cell))}</th>')
                    html.append('</tr></thead>')
                    # 表体
                    html.append('<tbody>')
                    for row in table_data[1:]:
                        html.append('<tr>')
                        for cell in row:
                            html.append(f'<td>{self._inline(self._escape_html(cell))}</td>')
                        html.append('</tr>')
                    html.append('</tbody></table>')
                continue

            # 分隔线
            elif line.strip() == '---':
                if in_list:
                    close_list()
                html.append('<hr class="divider">')

            # 原始 HTML 块
            elif line.strip().startswith('<'):
                if in_list:
                    close_list()
                raw_lines = [line]
                i += 1
                while i < n and lines[i].strip() and not lines[i].startswith('#') and \
                      lines[i].strip() != '---' and not lines[i].strip().startswith('```'):
                    raw_lines.append(lines[i])
                    i += 1
                html.append('\n'.join(raw_lines))
                continue

            # 普通段落
            else:
                if in_list:
                    close_list()
                para_lines = [line]
                i += 1
                while i < n and lines[i].strip() and not lines[i].startswith('#') and \
                      lines[i].strip() != '---' and '|' not in lines[i] and \
                      not lines[i].strip().startswith('<'):
                    para_lines.append(lines[i])
                    i += 1
                text = ' '.join(para_lines)
                html.append(f'<p class="paragraph">{self._inline(self._escape_html(text))}</p>')
                continue

            i += 1

        if in_list:
            close_list()

        return '\n'.join(html)


class CacheManager:
    """缓存管理器"""
    def __init__(self):
        self.cache = {}

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value):
        self.cache[key] = value

    def clear(self):
        self.cache.clear()


class FileWatcher(FileSystemEventHandler):
    """文件监听器"""

    def __init__(self, on_change):
        super().__init__()
        self.on_change = on_change
        self.last_modified = 0
        self.debounce_time = 0.5

    def on_modified(self, event):
        if event.src_path.endswith('.md') or event.src_path.endswith('.yaml'):
            current_time = time.time()
            if current_time - self.last_modified > self.debounce_time:
                self.last_modified = current_time
                filename = os.path.basename(event.src_path)
                print(f"[预览] 检测到变化: {filename}")
                if self.on_change:
                    self.on_change()


class PreviewHTTPRequestHandler(SimpleHTTPRequestHandler):
    """HTTP 请求处理器"""

    def __init__(self, *args, cache_manager=None, theme_manager=None, md_file='main.md', **kwargs):
        self.cache = cache_manager
        self.theme = theme_manager
        self.md_file = md_file
        super().__init__(*args, **kwargs)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/' or path == '/preview':
            self._serve_preview()
        elif path == '/api/content':
            self._serve_content()
        elif path == '/api/theme':
            self._serve_theme()
        elif path == '/api/themes':
            self._serve_themes()
        elif path == '/api/set-theme':
            self._set_theme()
        elif path == '/api/export-pdf':
            self._export_pdf()
        else:
            super().do_GET()

    def _serve_preview(self):
        """提供预览页面"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()

        html = self._get_preview_html()
        self.wfile.write(html.encode('utf-8'))

    def _get_preview_html(self):
        """获取预览页面 HTML"""
        import json as _json
        css_vars = self.theme.to_html_vars()
        dark_vars = self.theme.to_dark_html_vars()
        md_filename = os.path.basename(self.md_file)

        preview_cfg = self.theme.config.get('preview', {})
        topbar_height = preview_cfg.get('topbar_height', 44)
        btn_height = max(topbar_height - 16, 24)
        init_lang = preview_cfg.get('lang', 'zh')
        init_theme = preview_cfg.get('theme', 'light')
        init_topbar = 'true' if preview_cfg.get('topbar_visible', True) else 'false'
        init_zoom = str(preview_cfg.get('zoom', 1.0))
        init_theme_name = self.theme.config.get('theme', 'default')

        btn_cfg = self.theme.config.get('buttons', {})
        btn_left = btn_cfg.get('left', ['dark', 'lang'])
        btn_right = btn_cfg.get('right', ['auto_refresh', 'export_pdf'])
        btn_layout_json = _json.dumps({'left': btn_left, 'right': btn_right})

        def build_vars(d):
            lines = []
            for k, v in d.items():
                if k.startswith('--spacing'):
                    lines.append(f'            {k}: {v}rem;')
                elif k.startswith('--font-size'):
                    lines.append(f'            {k}: {v}px;')
                else:
                    lines.append(f'            {k}: {v};')
            return '\n'.join(lines)

        root_vars = build_vars(css_vars)
        dark_css_vars = build_vars(dark_vars)

        hotkeys = self.theme.config.get('hotkeys', {})
        hotkeys_json = _json.dumps({
            'export_pdf': hotkeys.get('export_pdf', 'p'),
            'toggle_dark': hotkeys.get('toggle_dark', 'd'),
            'toggle_theme': hotkeys.get('toggle_theme', 'c'),
            'toggle_topbar': hotkeys.get('toggle_topbar', 'b'),
            'toggle_auto_refresh': hotkeys.get('toggle_auto_refresh', 'a'),
            'keybindings': hotkeys.get('keybindings', 'k'),
            'toggle_lang': hotkeys.get('toggle_lang', 'l'),
            'toggle_toc': hotkeys.get('toggle_toc', 't'),
        })

        template = PREVIEW_TEMPLATE

        return (template
                .replace('{md_filename}', md_filename)
                .replace('{css_vars}', root_vars)
                .replace('{dark_css_vars}', dark_css_vars)
                .replace('{topbar_height}', str(topbar_height))
                .replace('{btn_height}', str(btn_height))
                .replace('{init_lang}', init_lang)
                .replace('{init_theme}', init_theme)
                .replace('{init_topbar}', init_topbar)
                .replace('{init_zoom}', init_zoom)
                .replace('{btn_layout}', btn_layout_json)
                .replace('{init_theme_name}', init_theme_name)
                .replace('{hotkeys}', hotkeys_json)
                )

    def _serve_content(self):
        """提供内容 API"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()

        if os.path.exists(self.md_file):
            with open(self.md_file, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        else:
            raw_content = ''

        parser = MarkdownToHTML(self.theme)
        html_content = parser.parse(raw_content)

        import json
        response = json.dumps({'html': html_content})
        self.wfile.write(response.encode('utf-8'))

    def _serve_theme(self):
        """提供主题 API"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()

        import json
        response = json.dumps(self.theme.to_html_vars())
        self.wfile.write(response.encode('utf-8'))

    def _serve_themes(self):
        """列出所有可用主题"""
        import json
        themes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'themes')
        themes = []
        for f in sorted(os.listdir(themes_dir)):
            if f.endswith('.yaml'):
                name = f[:-5]
                with open(os.path.join(themes_dir, f), 'r', encoding='utf-8') as fh:
                    cfg = yaml.safe_load(fh) or {}
                themes.append({'name': name, 'label': cfg.get('name', name)})
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(themes).encode('utf-8'))

    def _set_theme(self):
        """切换主题并返回新颜色 CSS 变量"""
        import json
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(self.path).query)
        name = qs.get('name', [''])[0]
        themes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'themes')
        theme_path = os.path.join(themes_dir, f'{name}.yaml')
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        if os.path.exists(theme_path):
            theme_cfg = yaml.safe_load(open(theme_path, encoding='utf-8'))
            self.theme.config['colors'] = theme_cfg.get('colors', {})
            self.theme.config['dark_colors'] = theme_cfg.get('dark_colors', {})
            color_vars = {k: v for k, v in self.theme.to_html_vars().items()
                          if not k.startswith('--font-size') and not k.startswith('--spacing')}
            color_vars['dark'] = self.theme.to_dark_html_vars()
            self.wfile.write(json.dumps(color_vars).encode('utf-8'))
        else:
            self.wfile.write(b'')

    def _export_pdf(self):
        """导出 PDF"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()

        try:
            from playwright.sync_api import sync_playwright
            import queue
            md_stem = os.path.splitext(os.path.basename(self.md_file))[0]
            out_pdf = os.path.join(os.path.dirname(self.md_file), md_stem + '.pdf')
            server_port = self.server.server_address[1]
            author = self.theme.config.get('author', '')
            pdf_cfg = self.theme.config.get('pdf', {})
            margin_bottom = pdf_cfg.get('margin_bottom', '1.5cm')
            result_q = queue.Queue()

            def run():
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch()
                        page = browser.new_page()
                        page.goto(f'http://localhost:{server_port}/', wait_until='domcontentloaded')
                        page.wait_for_function("document.querySelector('#preview') && document.querySelector('#preview').children.length > 0")
                        page.wait_for_timeout(1000)
                        page.evaluate("""() => {
                            const c = document.querySelector('.preview-content');
                            const h = c ? c.scrollHeight : document.body.scrollHeight;
                            document.body.style.cssText += ';height:auto!important;min-height:0!important;overflow:visible!important;background:white!important';
                            const main = document.querySelector('main');
                            if (main) main.style.cssText += ';height:auto!important;min-height:0!important;flex:none!important;background:white!important';
                        }""")
                        page.pdf(path=out_pdf, format='A4', print_background=True,
                                 margin={'top': '1cm', 'bottom': margin_bottom, 'left': '1cm', 'right': '1cm'},
                                 display_header_footer=True,
                                 header_template='<span></span>',
                                 footer_template=f'<div style="position:relative;width:100%;font-size:10px;color:#888;padding:0 1.2cm;box-sizing:border-box;"><span style="position:absolute;left:1.2cm;color:#888;">{author}</span><span style="position:absolute;right:1.2cm;color:#888;"><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
                        browser.close()
                    result_q.put(('ok', out_pdf))
                except Exception as e:
                    result_q.put(('err', str(e)))
                    result_q.put(('err', str(e)))

            t = Thread(target=run, daemon=True)
            t.start()
            t.join(timeout=60)

            status, val = result_q.get()
            if status == 'ok':
                self.wfile.write(val.encode('utf-8'))
            else:
                self.wfile.write(f'PDF 生成失败: {val}'.encode('utf-8'))
        except Exception as e:
            self.wfile.write(f'PDF 生成失败: {str(e)}'.encode('utf-8'))


class PreviewServer:
    """预览服务器"""

    def __init__(self, port=8000, md_file='main.md'):
        self.port = port
        self.md_file = os.path.abspath(md_file)
        self.server = None
        self.config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
        self.theme = ThemeManager(self.config_dir)
        self.cache = CacheManager()

    def _get_available_port(self):
        """获取可用端口"""
        for port in range(self.port, self.port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                continue
        raise RuntimeError("无法找到可用端口")

    def start(self):
        """启动服务器"""
        available_port = self._get_available_port()

        # 保存引用供内部类使用
        cache_ref = self.cache
        theme_ref = self.theme
        md_file_ref = self.md_file

        # 创建自定义 handler
        class Handler(PreviewHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                kwargs['cache_manager'] = cache_ref
                kwargs['theme_manager'] = theme_ref
                kwargs['md_file'] = md_file_ref
                super().__init__(*args, **kwargs)

        # 创建服务器（allow_reuse_address 确保停止后端口立即释放）
        ThreadedHTTPServer.allow_reuse_address = True
        self.server = ThreadedHTTPServer(('localhost', available_port), Handler)

        # 启动文件监听器
        watch_dir = os.path.dirname(self.md_file)
        observer = Observer()
        observer.schedule(FileWatcher(self._on_file_change), watch_dir, recursive=False)
        # 监听 config 目录
        if os.path.isdir(self.config_dir):
            observer.schedule(FileWatcher(self._on_config_change), self.config_dir, recursive=True)
        observer.start()

        # 显示访问信息
        url = f"http://localhost:{available_port}"
        print("=" * 60)
        print("🚀 Markdown 实时预览服务器")
        print("=" * 60)
        print(f"📁 工作目录: {os.getcwd()}")
        print(f"🌐 访问地址: {url}")
        print("=" * 60)
        print("编辑器功能:")
        print("  • 切换浅色/深色模式")
        print("  • 切换中英文")
        print("  • 自动刷新")
        print("  • 切换Light/Dark Mode")
        print("  • 点击「导出 PDF」生成 PDF 文件")
        print("=" * 60)
        print("按 Ctrl+C 停止服务器")
        print("=" * 60)

        # 自动打开浏览器
        try:
            webbrowser.open(url)
        except:
            pass

        # 启动服务器
        try:
            self.server.serve_forever()
        finally:
            self.server.server_close()

    def _on_file_change(self):
        """文件变化回调"""
        self.cache.clear()

    def _on_config_change(self):
        """配置文件变化回调，重新加载主题"""
        self.theme.config = self.theme._load_config()
        self.cache.clear()
        print("[预览] 配置已重新加载")


def main():
    """主函数"""
    import sys
    md_file = sys.argv[1] if len(sys.argv) > 1 else 'main.md'
    md_file = os.path.abspath(md_file)
    server = PreviewServer(md_file=md_file)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[预览] 服务器已停止")


if __name__ == "__main__":
    main()

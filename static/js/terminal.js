const TerminalManager = {
    term: null,
    ws: null,
    fitAddon: null,
    _resizeTimeout: null,

    start(vulnId) {
        this.stop();
        App.closeTerminal();

        const container = document.getElementById('terminal-container');
        if (!container) return;
        container.innerHTML = '';

        const term = new Terminal({
            cursorBlink: true,
            fontSize: 13,
            fontFamily: "'JetBrains Mono', 'Consolas', monospace",
            theme: {
                background: '#0d1117',
                foreground: '#e6edf3',
                cursor: '#58a6ff',
                selectionBackground: 'rgba(88, 166, 255, 0.3)',
            },
            rows: 16,
            cols: 100,
            scrollback: 5000,
        });

        const fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(container);

        // 延迟 fit 等待 DOM 渲染
        setTimeout(() => {
            try { fitAddon.fit(); } catch(e) {}
        }, 200);

        this.term = term;
        this.fitAddon = fitAddon;

        // WebSocket 连接
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${location.host}/api/ranges/${vulnId}/terminal`;

        term.writeln('\x1b[33m正在连接终端...\x1b[0m');

        try {
            const ws = new WebSocket(wsUrl);
            this.ws = ws;

            ws.onopen = () => {
                term.writeln('\x1b[32m--- 终端已连接 ---\x1b[0m\r\n');
            };

            ws.onmessage = (event) => {
                term.write(event.data);
            };

            ws.onclose = (event) => {
                term.writeln('\r\n\x1b[31m--- 终端连接已断开 ---\x1b[0m');
            };

            ws.onerror = (event) => {
                term.writeln('\r\n\x1b[31m--- 终端连接错误 ---\x1b[0m');
            };

            term.onData((data) => {
                if (ws.readyState === WebSocket.OPEN) {
                    try {
                        ws.send(data);
                    } catch (e) {
                        // 忽略发送失败
                    }
                }
            });

            // 监听窗口大小变化
            this._resizeHandler = () => {
                clearTimeout(this._resizeTimeout);
                this._resizeTimeout = setTimeout(() => {
                    try { fitAddon.fit(); } catch(e) {}
                }, 150);
            };
            window.addEventListener('resize', this._resizeHandler);

        } catch (e) {
            term.writeln(`\x1b[31m终端初始化失败: ${e.message}\x1b[0m`);
        }
    },

    stop() {
        if (this._resizeHandler) {
            window.removeEventListener('resize', this._resizeHandler);
            this._resizeHandler = null;
        }
        if (this._resizeTimeout) {
            clearTimeout(this._resizeTimeout);
            this._resizeTimeout = null;
        }
        if (this.ws) {
            try { this.ws.close(); } catch(e) {}
            this.ws = null;
        }
        if (this.term) {
            try { this.term.dispose(); } catch(e) {}
            this.term = null;
        }
        this.fitAddon = null;
    },
};

// 终端标签切换时初始化
$(document).ready(() => {
    $('a[href="#tab-terminal"]').on('shown.bs.tab', () => {
        if (App.currentVulnId && !TerminalManager.term) {
            TerminalManager.start(App.currentVulnId);
        }
    });
});

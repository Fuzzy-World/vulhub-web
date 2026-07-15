const App = {
    currentPage: 'vulns',
    currentVulnId: null,
    logEventSource: null,
    terminalInstance: null,

    async init() {
        const token = API.getToken();
        if (token) {
            const result = await API.verify();
            if (result.valid) {
                this.showMain();
                return;
            }
        }
        this.showLogin();
    },

    showLogin() {
        $('#page-login').removeClass('d-none');
        $('#page-main').addClass('d-none');
        this.checkAuthStatus();
    },

    showMain() {
        $('#page-login').addClass('d-none');
        $('#page-main').removeClass('d-none');
        this.switchPage('vulns');
    },

    async checkAuthStatus() {
        const result = await API.authStatus();
        if (result.initialized) {
            $('#login-form-init').addClass('d-none');
            $('#login-form-login').removeClass('d-none');
        } else {
            $('#login-form-init').removeClass('d-none');
            $('#login-form-login').addClass('d-none');
        }
    },

    switchPage(page) {
        this.currentPage = page;
        this.closeLogStream();
        this.closeTerminal();

        $('.nav-tab').removeClass('active');
        $(`.nav-tab[data-page="${page}"]`).addClass('active');

        // 隐藏所有页面
        $('.content-page').removeClass('active').addClass('d-none');

        if (page === 'vulns') {
            $('#content-vulns').removeClass('d-none').addClass('active');
            VulnsPage.load();
        } else if (page === 'detail') {
            $('#content-detail').removeClass('d-none').addClass('active');
            DetailPage.load(this.currentVulnId);
        } else if (page === 'running') {
            $('#content-running').removeClass('d-none').addClass('active');
            RunningPage.load();
        } else if (page === 'settings') {
            $('#content-settings').removeClass('d-none').addClass('active');
            SettingsPage.load();
        }
    },

    closeLogStream() {
        if (this.logEventSource) {
            this.logEventSource.close();
            this.logEventSource = null;
        }
    },

    closeTerminal() {
        if (this.terminalInstance) {
            this.terminalInstance.dispose();
            this.terminalInstance = null;
        }
    },

    toast(message, type = 'info') {
        const icons = {
            success: 'bi-check-circle-fill',
            error: 'bi-x-circle-fill',
            warning: 'bi-exclamation-triangle-fill',
            info: 'bi-info-circle-fill',
        };
        const id = 'toast-' + Date.now();
        const html = `<div class="custom-toast ${type}" id="${id}">
            <i class="bi ${icons[type]}"></i>
            <span>${message}</span>
        </div>`;
        $('#toast-container').append(html);
        setTimeout(() => $(`#${id}`).fadeOut(300, function() { $(this).remove(); }), 3000);
    },

    confirm(message) {
        return new Promise((resolve) => {
            $('#confirm-message').html(message);
            const modal = new bootstrap.Modal($('#confirmModal')[0]);
            $('#confirm-ok').off('click').on('click', () => {
                modal.hide();
                resolve(true);
            });
            modal.show();
        });
    },

    formatUptime(seconds) {
        if (seconds < 60) return `${seconds}秒`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`;
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        return `${h}时${m}分`;
    },

    renderStatusBadge(status) {
        const labels = {
            unbuilt: '未构建', built: '已构建', running: '运行中',
            building: '构建中', starting: '启动中', destroying: '销毁中',
        };
        const isProgress = ['building', 'starting', 'destroying'].includes(status);
        const icon = isProgress ? '<span class="spinner-border spinner-border-sm me-1" style="width:10px;height:10px;border-width:2px"></span>' : `<span class="status-dot ${status.replace('ing','t')}"></span>`;
        const cls = isProgress ? status : status;
        return `<span class="status-badge ${cls}">${icon}${labels[status] || status}</span>`;
    },

    /**
     * 轮询任务状态，完成后回调
     * @param {number} taskId - 任务 ID
     * @param {function} onComplete - 完成回调 (task) => void
     * @param {function} onProgress - 进度回调 (task) => void（可选）
     */
    pollTask(taskId, onComplete, onProgress = null) {
        const interval = 2000; // 2秒轮询一次
        const maxAttempts = 600; // 最多20分钟
        let attempts = 0;

        const poll = async () => {
            attempts++;
            try {
                const task = await API.getTask(taskId);
                if (onProgress) onProgress(task);

                if (task.status === 'success' || task.status === 'failed') {
                    onComplete(task);
                    return;
                }
                if (task.error) {
                    onComplete({ ...task, status: 'failed' });
                    return;
                }
            } catch (e) {
                // 网络错误继续轮询
            }

            if (attempts < maxAttempts) {
                setTimeout(poll, interval);
            } else {
                onComplete({ status: 'failed', log_content: '任务超时' });
            }
        };

        // 首次延迟1秒开始
        setTimeout(poll, 1000);
    },
};

// ===== 事件绑定 =====
$(document).ready(() => {
    App.init();

    // 登录
    $('#btn-login').on('click', async () => {
        const password = $('#login-password').val();
        if (!password) return;
        const result = await API.login(password);
        if (result.success) {
            API.setToken(result.token);
            App.showMain();
        } else {
            const $msg = $('#login-message');
            $msg.text(result.message || '登录失败').removeClass('d-none');
            setTimeout(() => $msg.addClass('d-none'), 3000);
        }
    });

    // 初始化密码
    $('#btn-init-password').on('click', async () => {
        const password = $('#init-password').val();
        if (!password || password.length < 4) {
            App.toast('密码长度不能少于4位', 'warning');
            return;
        }
        const result = await API.initPassword(password);
        if (result.success) {
            API.setToken(result.token);
            App.showMain();
            App.toast('管理员密码设置成功', 'success');
        } else {
            App.toast(result.message || '初始化失败', 'error');
        }
    });

    // Enter 键登录
    $('#login-password, #init-password').on('keypress', (e) => {
        if (e.which === 13) {
            if ($('#login-form-login').is(':visible')) {
                $('#btn-login').click();
            } else {
                $('#btn-init-password').click();
            }
        }
    });

    // 退出
    $('#btn-logout').on('click', () => {
        API.clearToken();
        App.showLogin();
    });

    // 页面切换
    $(document).on('click', '.nav-tab', (e) => {
        e.preventDefault();
        const page = $(e.currentTarget).data('page');
        if (page) App.switchPage(page);
    });

    // 侧边栏切换
    $('#sidebar-toggle').on('click', () => {
        $('#sidebar').toggleClass('show');
    });

    // 侧边栏收起
    $('#btn-sidebar-collapse').on('click', () => {
        $('#sidebar').addClass('collapsed');
        $('#btn-sidebar-expand').addClass('visible');
    });

    // 侧边栏展开
    $('#btn-sidebar-expand').on('click', () => {
        $('#sidebar').removeClass('collapsed');
        $('#btn-sidebar-expand').removeClass('visible');
    });
});

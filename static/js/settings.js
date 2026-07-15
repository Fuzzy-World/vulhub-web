const SettingsPage = {
    async load() {
        this.loadSettings();
        this.loadDockerInfo();
    },

    async loadSettings() {
        const settings = await API.getSettings();
        if (!settings) return;

        $('#setting-vulhub-path').val(settings.vulhub_root_path || '');
        $('#setting-server-port').val(settings.server_port || 8088);
        $('#setting-admin-password').val('');
        $('#setting-remove-image').prop('checked', settings.default_remove_image !== false);
        $('#setting-idle-timeout').val(settings.idle_timeout_hours || 0);
        $('#setting-scan-cron').val(settings.scan_cron || '0 */6 * * *');
        $('#setting-cleanup-cron').val(settings.cleanup_cron || '0 2 * * *');
    },

    async loadDockerInfo() {
        const info = await API.getDockerInfo();
        if (!info) return;

        $('#docker-disk').text(info.disk_usage_gb || 0);
        $('#docker-images').text(info.total_images || 0);
        $('#docker-running').text(info.running_containers || 0);
        $('#docker-stopped').text(info.stopped_containers || 0);

        const badge = $('#docker-status-badge');
        if (info.error) {
            badge.addClass('error');
        } else {
            badge.removeClass('error');
        }
    },

    async save() {
        const data = {
            vulhub_root_path: $('#setting-vulhub-path').val().trim(),
            server_port: parseInt($('#setting-server-port').val()) || 8088,
            default_remove_image: $('#setting-remove-image').is(':checked'),
            idle_timeout_hours: parseInt($('#setting-idle-timeout').val()) || 0,
            scan_cron: $('#setting-scan-cron').val().trim(),
            cleanup_cron: $('#setting-cleanup-cron').val().trim(),
        };

        const password = $('#setting-admin-password').val().trim();
        if (password) {
            data.admin_password = password;
        }

        const result = await API.updateSettings(data);
        if (result.success) {
            App.toast('设置保存成功', 'success');
            // 如果设置了 vulhub 路径，自动扫描
            if (data.vulhub_root_path) {
                App.toast('正在扫描漏洞库...', 'info');
                const scanResult = await API.scanVulns();
                if (scanResult.success) {
                    App.toast(`扫描完成：新增 ${scanResult.added}，更新 ${scanResult.updated}`, 'success');
                }
            }
        } else {
            App.toast(result.message || '保存失败', 'error');
        }
    },
};

// ===== 事件绑定 =====
$(document).ready(() => {
    // 保存设置
    $('#btn-save-settings').on('click', () => {
        SettingsPage.save();
    });

    // Docker 操作
    $('#btn-cleanup-stopped').on('click', async () => {
        const confirmed = await App.confirm('确认清理所有停止的容器？');
        if (confirmed) {
            const result = await API.cleanupDocker({ remove_stopped: true });
            App.toast(`清理完成：移除 ${result.removed_containers} 个容器`, 'success');
            SettingsPage.loadDockerInfo();
        }
    });

    $('#btn-cleanup-dangling').on('click', async () => {
        const confirmed = await App.confirm('确认清理所有悬空镜像？');
        if (confirmed) {
            const result = await API.cleanupDocker({ remove_dangling: true });
            App.toast(`清理完成：移除 ${result.removed_images} 个镜像`, 'success');
            SettingsPage.loadDockerInfo();
        }
    });

    $('#btn-cleanup-cache').on('click', async () => {
        const confirmed = await App.confirm('确认清理构建缓存？');
        if (confirmed) {
            await API.cleanupDocker({ remove_cache: true });
            App.toast('缓存清理完成', 'success');
            SettingsPage.loadDockerInfo();
        }
    });

    $('#btn-destroy-all').on('click', async () => {
        const confirmed = await App.confirm('确认销毁所有运行中的靶机？此操作不可恢复！');
        if (confirmed) {
            const result = await API.destroyAllRunning();
            App.toast(`销毁完成：${result.destroyed} 个靶机`, 'success');
            SettingsPage.loadDockerInfo();
        }
    });
});

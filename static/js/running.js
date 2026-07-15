const RunningPage = {
    async load() {
        this.loadRunning();
    },

    async loadRunning() {
        const ranges = await API.getRunningRanges();
        this.renderTable(ranges);
    },

    renderTable(ranges) {
        if (!ranges || ranges.length === 0) {
            $('#running-table-body').html(`<tr><td colspan="7">
                <div class="empty-state">
                    <i class="bi bi-emoji-smile"></i>
                    <p>当前没有运行中的靶机</p>
                </div>
            </td></tr>`);
            return;
        }

        let html = '';
        for (const r of ranges) {
            html += `<tr>
                <td><input type="checkbox" class="running-checkbox" data-id="${r.id}"></td>
                <td><span class="cve-id">${r.cve_id}</span></td>
                <td>${r.name}</td>
                <td>${App.formatUptime(r.uptime_seconds)}</td>
                <td>
                    <a href="${r.access_url}" target="_blank" class="access-url-link">${r.access_url}</a>
                    <button class="btn btn-sm btn-outline-secondary py-0 px-1" style="font-size:11px"
                        onclick="navigator.clipboard.writeText('${r.access_url}');App.toast('已复制','success')">
                        <i class="bi bi-clipboard"></i>
                    </button>
                </td>
                <td data-container-id="${r.container_id || ''}" class="resource-cell">
                    <div class="resource-bar"><span>CPU</span><div class="progress"><div class="progress-bar bg-info" style="width:0%"></div></div><span class="cpu-val">-</span></div>
                    <div class="resource-bar mt-1"><span>MEM</span><div class="progress"><div class="progress-bar bg-warning" style="width:0%"></div></div><span class="mem-val">-</span></div>
                </td>
                <td>
                    <div class="d-flex gap-1">
                        <button class="btn btn-action btn-detail" data-id="${r.id}" data-action="detail">日志</button>
                        <button class="btn btn-action btn-detail" data-id="${r.id}" data-action="terminal">终端</button>
                        <button class="btn btn-action btn-destroy" data-id="${r.id}" data-action="destroy">销毁</button>
                    </div>
                </td>
            </tr>`;
        }
        $('#running-table-body').html(html);

        // 异步加载资源占用（不阻塞渲染）
        this.loadResources(ranges);
    },

    async loadResources(ranges) {
        for (const r of ranges) {
            if (!r.container_id) continue;
            try {
                const res = await API.request(`/api/ranges/resource/${r.container_id}`);
                const $cell = $(`td[data-container-id="${r.container_id}"]`);
                if ($cell.length && res) {
                    const cpu = Math.min(res.cpu_percent || 0, 100);
                    const mem = res.memory_usage_mb || 0;
                    $cell.find('.progress-bar.bg-info').css('width', cpu + '%');
                    $cell.find('.cpu-val').text(cpu + '%');
                    $cell.find('.progress-bar.bg-warning').css('width', Math.min(mem / 500 * 100, 100) + '%');
                    $cell.find('.mem-val').text(mem + 'MB');
                }
            } catch (e) {
                // 忽略，保持默认显示
            }
        }
    },
};

// ===== 事件绑定 =====
$(document).ready(() => {
    // 刷新
    $('#btn-refresh-running').on('click', () => {
        RunningPage.load();
    });

    // 全选
    $('#select-all-running').on('change', (e) => {
        $('.running-checkbox').prop('checked', $(e.target).prop('checked'));
    });

    // 批量销毁
    $('#btn-batch-destroy').on('click', async () => {
        const ids = [];
        $('.running-checkbox:checked').each((_, el) => {
            ids.push(parseInt($(el).data('id')));
        });
        if (ids.length === 0) {
            App.toast('请先选择要销毁的靶机', 'warning');
            return;
        }
        const confirmed = await App.confirm(`确认批量销毁 ${ids.length} 个靶机？`);
        if (confirmed) {
            const result = await API.batchDestroy(ids, true);
            App.toast(`销毁完成：成功 ${result.success} / ${result.total}`, result.success > 0 ? 'success' : 'error');
            RunningPage.load();
        }
    });

    // 操作按钮
    $(document).on('click', '#content-running .btn-action', async (e) => {
        const id = $(e.currentTarget).data('id');
        const action = $(e.currentTarget).data('action');

        if (action === 'detail') {
            App.currentVulnId = id;
            App.switchPage('detail');
        } else if (action === 'terminal') {
            App.currentVulnId = id;
            App.switchPage('detail');
            // 切换到终端标签
            setTimeout(() => {
                $('a[href="#tab-terminal"]').tab('show');
                TerminalManager.start(id);
            }, 500);
        } else if (action === 'destroy') {
            const confirmed = await App.confirm('确认销毁该靶机？');
            if (confirmed) {
                const result = await API.destroyRange(id, true);
                App.toast(result.success ? '销毁成功' : '销毁失败', result.success ? 'success' : 'error');
                RunningPage.load();
            }
        }
    });
});

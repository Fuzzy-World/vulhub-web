const DetailPage = {
    vulnId: null,
    vulnData: null,

    async load(vulnId) {
        this.vulnId = vulnId;
        if (!vulnId) return;

        const vuln = await API.getVuln(vulnId);
        if (!vuln || vuln.error) {
            App.toast('漏洞不存在', 'error');
            App.switchPage('vulns');
            return;
        }
        this.vulnData = vuln;
        this.renderInfo(vuln);
        this.loadReadme(vulnId);
        this.startLogStream(vulnId);
    },

    async renderInfo(vuln) {
        let accessHtml = '';
        if (vuln.status === 'running') {
            try {
                const status = await API.getRangeStatus(vuln.id);
                if (status.access_url) {
                    accessHtml = `<a class="detail-access-url" href="${status.access_url}" target="_blank">
                        <i class="bi bi-box-arrow-up-right"></i>${status.access_url}
                    </a>
                    <button class="btn btn-sm btn-outline-secondary" onclick="navigator.clipboard.writeText('${status.access_url}');App.toast('已复制','success')">
                        <i class="bi bi-clipboard"></i>
                    </button>`;
                }
            } catch (e) {}
        }

        let actionHtml = '';
        const isBusy = ['building', 'starting', 'destroying'].includes(vuln.status);
        if (isBusy) {
            const label = vuln.status === 'building' ? '构建中' : vuln.status === 'starting' ? '启动中' : '销毁中';
            actionHtml = `<button class="btn btn-sm" disabled><span class="spinner-border spinner-border-sm me-1"></span>${label}...</button>`;
        } else if (vuln.status === 'unbuilt') {
            actionHtml = `<button class="btn btn-sm btn-build" id="detail-btn-build">构建镜像</button>`;
        } else if (vuln.status === 'built') {
            actionHtml = `<button class="btn btn-sm btn-start" id="detail-btn-start">启动靶场</button>
                <button class="btn btn-sm btn-destroy" id="detail-btn-destroy">销毁</button>`;
        } else if (vuln.status === 'running') {
            actionHtml = `<button class="btn btn-sm btn-destroy" id="detail-btn-destroy">销毁靶场</button>`;
        }

        $('#detail-info').html(`
            <span class="detail-cve">${vuln.cve_id}</span>
            <span class="detail-category">${vuln.category}</span>
            ${App.renderStatusBadge(vuln.status)}
            ${accessHtml}
            <div class="ms-auto d-flex gap-2">${actionHtml}</div>
        `);

        // 绑定操作按钮
        $('#detail-btn-build').off('click').on('click', async () => {
            const result = await API.buildRange(vuln.id);
            if (!result.success) {
                App.toast(result.message || '提交失败', 'error');
                return;
            }
            App.toast('构建任务已提交，请等待...', 'info');
            this.renderInfo({...vuln, status: 'building'});
            App.pollTask(result.task_id, (task) => {
                if (task.status === 'success') {
                    App.toast(`构建成功，耗时 ${task.duration_seconds || 0}s`, 'success');
                } else {
                    App.toast(`构建失败：${(task.log_content || '').substring(0, 200)}`, 'error');
                }
                this.load(vuln.id);
            });
        });

        $('#detail-btn-start').off('click').on('click', async () => {
            const result = await API.startRange(vuln.id);
            if (!result.success) {
                App.toast(result.message || '提交失败', 'error');
                return;
            }
            App.toast('启动任务已提交，请等待...', 'info');
            this.renderInfo({...vuln, status: 'starting'});
            App.pollTask(result.task_id, (task) => {
                if (task.status === 'success') {
                    App.toast(`启动成功，耗时 ${task.duration_seconds || 0}s`, 'success');
                } else {
                    App.toast(`启动失败：${(task.log_content || '').substring(0, 200)}`, 'error');
                }
                this.load(vuln.id);
            });
        });

        $('#detail-btn-destroy').off('click').on('click', async () => {
            const confirmed = await App.confirm('确认销毁该靶场？<br><br><div class="form-check form-switch mb-2"><input class="form-check-input" type="checkbox" id="destroy-remove-image" checked><label class="form-check-label" for="destroy-remove-image" style="font-size:13px;color:var(--text-secondary)">同步删除镜像（释放磁盘）</label></div>');
            if (confirmed) {
                const removeImage = $('#destroy-remove-image').is(':checked');
                const result = await API.destroyRange(vuln.id, removeImage);
                if (!result.success) {
                    App.toast(result.message || '提交失败', 'error');
                    return;
                }
                App.toast('销毁任务已提交，请等待...', 'info');
                this.renderInfo({...vuln, status: 'destroying'});
                App.pollTask(result.task_id, (task) => {
                    if (task.status === 'success') {
                        App.toast(`销毁成功，耗时 ${task.duration_seconds || 0}s`, 'success');
                    } else {
                        App.toast(`销毁失败：${(task.log_content || '').substring(0, 200)}`, 'error');
                    }
                    this.load(vuln.id);
                });
            }
        });
    },

    async loadReadme(vulnId) {
        const result = await API.getReadme(vulnId);
        if (result && result.html) {
            $('#detail-readme').html(result.html);
        } else {
            $('#detail-readme').html('<div class="empty-state"><i class="bi bi-file-earmark-text"></i><p>暂无文档</p></div>');
        }
    },

    startLogStream(vulnId) {
        App.closeLogStream();
        const url = `/api/ranges/${vulnId}/logs?tail=100`;
        const es = new EventSource(url);
        es.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.log) {
                    const panel = document.getElementById('log-panel');
                    panel.textContent += data.log + '\n';
                    panel.scrollTop = panel.scrollHeight;
                }
            } catch (e) {}
        };
        es.onerror = () => {
            // 连接失败时静默处理
        };
        App.logEventSource = es;
    },
};

// 返回按钮
$(document).ready(() => {
    $('#btn-back-vulns').on('click', () => {
        App.switchPage('vulns');
    });
});

const VulnsPage = {
    page: 1,
    pageSize: 20,
    category: 'all',
    status: 'all',
    year: 'all',
    keyword: '',

    async load() {
        this.loadCategories();
        this.loadYears();
        this.loadVulns();
    },

    async loadCategories() {
        const categories = await API.getCategories();
        let html = `<div class="category-item ${this.category === 'all' ? 'active' : ''}" data-category="all">
            <i class="bi bi-grid-3x3-gap"></i>
            <span>全部</span>
            <span class="badge" id="category-all-count">${categories.reduce((s, c) => s + c.count, 0)}</span>
        </div>`;

        const icons = {
            log4j: 'bi-journal-code', shiro: 'bi-shield-check', fastjson: 'bi-lightning',
            struts2: 'bi-diagram-3', tomcat: 'bi-server', weblogic: 'bi-hdd-stack',
            spring: 'bi-leaf', redis: 'bi-database', nginx: 'bi-globe',
            activemq: 'bi-envelope', mysql: 'bi-database', apache: 'bi-globe2',
        };

        for (const cat of categories) {
            const icon = icons[cat.name] || 'bi-bug';
            html += `<div class="category-item ${this.category === cat.name ? 'active' : ''}" data-category="${cat.name}">
                <i class="bi ${icon}"></i>
                <span>${cat.name}</span>
                <span class="badge">${cat.count}</span>
            </div>`;
        }
        $('#category-list').html(html);

        // 分类点击
        $(document).off('click', '.category-item').on('click', '.category-item', (e) => {
            const cat = $(e.currentTarget).data('category');
            this.category = cat;
            this.page = 1;
            this.loadVulns();
            $('.category-item').removeClass('active');
            $(e.currentTarget).addClass('active');
        });
    },

    async loadYears() {
        const years = await API.getYears();
        let html = '<option value="all">全部年份</option>';
        for (const y of years) {
            html += `<option value="${y}" ${this.year === y ? 'selected' : ''}>${y}</option>`;
        }
        $('#filter-year').html(html);
    },

    async loadVulns() {
        const params = {
            page: this.page,
            page_size: this.pageSize,
        };
        if (this.category !== 'all') params.category = this.category;
        if (this.status !== 'all') params.status = this.status;
        if (this.year !== 'all') params.year = this.year;
        if (this.keyword) params.keyword = this.keyword;

        const result = await API.getVulns(params);
        this.renderTable(result.items || []);
        this.renderPagination(result.total || 0);
    },

    renderTable(items) {
        if (items.length === 0) {
            $('#vuln-table-body').html(`<tr><td colspan="6">
                <div class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <p>暂无漏洞数据，请先在设置中配置 Vulhub 根目录并扫描</p>
                </div>
            </td></tr>`);
            return;
        }

        let html = '';
        for (const item of items) {
            const desc = item.description ? (item.description.length > 80 ? item.description.substring(0, 80) + '...' : item.description) : '-';
            let actions = '';

            if (item.status === 'unbuilt') {
                actions = `<button class="btn btn-action btn-build" data-id="${item.id}" data-action="build">构建</button>`;
            } else if (item.status === 'built') {
                actions = `<button class="btn btn-action btn-start" data-id="${item.id}" data-action="start">启动</button>
                    <button class="btn btn-action btn-destroy" data-id="${item.id}" data-action="destroy">销毁</button>`;
            } else if (item.status === 'running') {
                actions = `<button class="btn btn-action btn-destroy" data-id="${item.id}" data-action="destroy">销毁</button>`;
            }

            html += `<tr>
                <td><span class="cve-id">${item.cve_id}</span></td>
                <td>${item.name}</td>
                <td style="color:var(--text-secondary);font-size:12px">${desc}</td>
                <td><span class="category-tag">${item.category}</span></td>
                <td>${App.renderStatusBadge(item.status)}</td>
                <td>
                    <div class="d-flex gap-1 flex-wrap">
                        ${actions}
                        <button class="btn btn-action btn-detail" data-id="${item.id}" data-action="detail">详情</button>
                    </div>
                </td>
            </tr>`;
        }
        $('#vuln-table-body').html(html);
    },

    renderPagination(total) {
        const totalPages = Math.ceil(total / this.pageSize);
        if (totalPages <= 1) {
            $('#vuln-pagination').html('');
            return;
        }

        let html = '';
        if (this.page > 1) {
            html += `<button class="page-btn" data-page="${this.page - 1}"><i class="bi bi-chevron-left"></i></button>`;
        }
        for (let i = Math.max(1, this.page - 2); i <= Math.min(totalPages, this.page + 2); i++) {
            html += `<button class="page-btn ${i === this.page ? 'active' : ''}" data-page="${i}">${i}</button>`;
        }
        if (this.page < totalPages) {
            html += `<button class="page-btn" data-page="${this.page + 1}"><i class="bi bi-chevron-right"></i></button>`;
        }
        $('#vuln-pagination').html(html);
    },
};

// ===== 事件绑定 =====
$(document).ready(() => {
    // 筛选
    $('#filter-status').on('change', (e) => {
        VulnsPage.status = $(e.target).val();
        VulnsPage.page = 1;
        VulnsPage.loadVulns();
    });

    $('#filter-year').on('change', (e) => {
        VulnsPage.year = $(e.target).val();
        VulnsPage.page = 1;
        VulnsPage.loadVulns();
    });

    // 搜索
    $('#btn-search').on('click', () => {
        VulnsPage.keyword = $('#search-keyword').val().trim();
        VulnsPage.page = 1;
        VulnsPage.loadVulns();
    });

    $('#search-keyword').on('keypress', (e) => {
        if (e.which === 13) {
            VulnsPage.keyword = $(e.target).val().trim();
            VulnsPage.page = 1;
            VulnsPage.loadVulns();
        }
    });

    // 分页
    $(document).on('click', '.page-btn', (e) => {
        const page = $(e.currentTarget).data('page');
        if (page) {
            VulnsPage.page = page;
            VulnsPage.loadVulns();
        }
    });

    // 扫描
    $('#btn-scan').on('click', async () => {
        App.toast('开始扫描漏洞库...', 'info');
        const result = await API.scanVulns();
        if (result.success) {
            App.toast(`扫描完成：新增 ${result.added}，更新 ${result.updated}，移除 ${result.removed}`, 'success');
            VulnsPage.load();
        } else {
            App.toast(result.message || '扫描失败', 'error');
        }
    });

    // 操作按钮
    $(document).on('click', '.btn-action', async (e) => {
        const id = $(e.currentTarget).data('id');
        const action = $(e.currentTarget).data('action');
        const $row = $(e.currentTarget).closest('tr');

        if (action === 'detail') {
            App.currentVulnId = id;
            App.switchPage('detail');
            return;
        }

        if (action === 'build') {
            // 立即更新行：状态→构建中，按钮→禁用
            $row.find('td:nth-child(5)').html(App.renderStatusBadge('building'));
            $row.find('td:nth-child(6) .d-flex').html(
                '<button class="btn btn-action" disabled><span class="spinner-border spinner-border-sm me-1"></span>构建中...</button>'
            );
            const result = await API.buildRange(id);
            if (!result.success) {
                App.toast(result.message || '提交构建失败', 'error');
                VulnsPage.loadVulns();
                return;
            }
            App.toast('构建任务已提交，请等待...', 'info');
            // 轮询任务状态
            App.pollTask(result.task_id, (task) => {
                if (task.status === 'success') {
                    App.toast(`构建成功，耗时 ${task.duration_seconds || 0}s`, 'success');
                } else {
                    App.toast(`构建失败：${(task.log_content || '').substring(0, 200)}`, 'error');
                }
                VulnsPage.loadVulns();
            });
        } else if (action === 'start') {
            $row.find('td:nth-child(5)').html(App.renderStatusBadge('starting'));
            $row.find('td:nth-child(6) .d-flex').html(
                '<button class="btn btn-action" disabled><span class="spinner-border spinner-border-sm me-1"></span>启动中...</button>'
            );
            const result = await API.startRange(id);
            if (!result.success) {
                App.toast(result.message || '提交启动失败', 'error');
                VulnsPage.loadVulns();
                return;
            }
            App.toast('启动任务已提交，请等待...', 'info');
            App.pollTask(result.task_id, (task) => {
                if (task.status === 'success') {
                    App.toast(`启动成功，耗时 ${task.duration_seconds || 0}s`, 'success');
                } else {
                    App.toast(`启动失败：${(task.log_content || '').substring(0, 200)}`, 'error');
                }
                VulnsPage.loadVulns();
            });
        } else if (action === 'destroy') {
            const confirmed = await App.confirm(
                '确认销毁该靶场？<br><br>' +
                '<div class="form-check form-switch mb-2">' +
                '<input class="form-check-input" type="checkbox" id="destroy-remove-image" checked>' +
                '<label class="form-check-label" for="destroy-remove-image" style="font-size:13px;color:var(--text-secondary)">同步删除镜像（释放磁盘）</label>' +
                '</div>'
            );
            if (confirmed) {
                const removeImage = $('#destroy-remove-image').is(':checked');
                $row.find('td:nth-child(5)').html(App.renderStatusBadge('destroying'));
                $row.find('td:nth-child(6) .d-flex').html(
                    '<button class="btn btn-action" disabled><span class="spinner-border spinner-border-sm me-1"></span>销毁中...</button>'
                );
                const result = await API.destroyRange(id, removeImage);
                if (!result.success) {
                    App.toast(result.message || '提交销毁失败', 'error');
                    VulnsPage.loadVulns();
                    return;
                }
                App.toast('销毁任务已提交，请等待...', 'info');
                App.pollTask(result.task_id, (task) => {
                    if (task.status === 'success') {
                        const imgInfo = removeImage ? '，已删除镜像' : '';
                        App.toast(`销毁成功${imgInfo}，耗时 ${task.duration_seconds || 0}s`, 'success');
                    } else {
                        App.toast(`销毁失败：${(task.log_content || '').substring(0, 200)}`, 'error');
                    }
                    VulnsPage.loadVulns();
                });
            }
        }
    });
});

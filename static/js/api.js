const API = {
    token: null,

    setToken(token) {
        this.token = token;
        document.cookie = `token=${token};path=/;max-age=${72 * 3600}`;
    },

    getToken() {
        if (this.token) return this.token;
        const match = document.cookie.match(/token=([^;]+)/);
        if (match) {
            this.token = match[1];
            return this.token;
        }
        return null;
    },

    clearToken() {
        this.token = null;
        document.cookie = 'token=;path=/;max-age=0';
    },

    async request(url, options = {}) {
        const token = this.getToken();
        const headers = { ...options.headers };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        if (options.body && typeof options.body === 'object') {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(options.body);
        }
        const resp = await fetch(url, { ...options, headers });
        if (resp.status === 401) {
            this.clearToken();
            App.showLogin();
            throw new Error('未授权');
        }
        return resp.json();
    },

    // Auth
    async login(password) {
        return this.request('/api/auth/login', { method: 'POST', body: { password } });
    },
    async initPassword(password) {
        return this.request('/api/auth/init', { method: 'POST', body: { password } });
    },
    async verify() {
        return this.request('/api/auth/verify');
    },
    async authStatus() {
        return this.request('/api/auth/status');
    },

    // Vulns
    async getVulns(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/api/vulns?${query}`);
    },
    async scanVulns() {
        return this.request('/api/vulns/scan', { method: 'POST' });
    },
    async getCategories() {
        return this.request('/api/vulns/categories');
    },
    async getYears() {
        return this.request('/api/vulns/years');
    },
    async getVuln(id) {
        return this.request(`/api/vulns/${id}`);
    },
    async getReadme(id) {
        return this.request(`/api/vulns/${id}/readme`);
    },

    // Ranges
    async buildRange(id) {
        return this.request(`/api/ranges/${id}/build`, { method: 'POST' });
    },
    async startRange(id) {
        return this.request(`/api/ranges/${id}/start`, { method: 'POST' });
    },
    async stopRange(id) {
        return this.request(`/api/ranges/${id}/stop`, { method: 'POST' });
    },
    async destroyRange(id, removeImage = false) {
        return this.request(`/api/ranges/${id}/destroy`, { method: 'POST', body: { remove_image: removeImage } });
    },
    async getRangeStatus(id) {
        return this.request(`/api/ranges/${id}/status`);
    },
    async getRunningRanges() {
        return this.request('/api/ranges/running');
    },
    async batchDestroy(ids, removeImage = false) {
        return this.request('/api/ranges/batch-destroy', { method: 'POST', body: { vuln_ids: ids, remove_image: removeImage } });
    },

    // Docker
    async getDockerInfo() {
        return this.request('/api/docker/info');
    },
    async cleanupDocker(data) {
        return this.request('/api/docker/cleanup', { method: 'POST', body: data });
    },
    async destroyAllRunning() {
        return this.request('/api/docker/destroy-all', { method: 'POST' });
    },

    // Settings
    async getSettings() {
        return this.request('/api/settings');
    },
    async updateSettings(data) {
        return this.request('/api/settings', { method: 'POST', body: data });
    },

    // Tasks
    async getTasks(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/api/tasks?${query}`);
    },
    async getTask(id) {
        return this.request(`/api/tasks/${id}`);
    },
};

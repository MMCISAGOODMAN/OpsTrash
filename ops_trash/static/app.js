const I18N = {
  zh: {
    refresh: '刷新',
    stat_count: '总文件数',
    stat_size: '总占用',
    stat_today: '今日删除数',
    stat_expired: '过期文件',
    search_placeholder: '搜索文件名或路径...',
    bulk_restore: '批量恢复',
    clean_expired: '清理过期',
    col_id: 'ID',
    col_path: '原路径',
    col_deleted: '删除时间',
    col_size: '大小',
    col_user: '用户',
    col_actions: '操作',
    restore: '恢复',
    empty_trash: '回收站为空',
    confirm_clean: '确认清理过期文件？',
    select_items: '请选择项目',
    restore_ok: '恢复成功',
    restore_fail: '恢复失败',
    bulk_restore_done: '批量恢复完成',
    cleaned: '已清理 {removed} 个，释放 {freed}',
    user_label: '用户: {user}',
  },
  en: {
    refresh: 'Refresh',
    stat_count: 'Total Files',
    stat_size: 'Total Size',
    stat_today: 'Deleted Today',
    stat_expired: 'Expired',
    search_placeholder: 'Search by name or path...',
    bulk_restore: 'Bulk Restore',
    clean_expired: 'Clean Expired',
    col_id: 'ID',
    col_path: 'Original Path',
    col_deleted: 'Deleted At',
    col_size: 'Size',
    col_user: 'User',
    col_actions: 'Actions',
    restore: 'Restore',
    empty_trash: 'Trash is empty',
    confirm_clean: 'Clean expired files?',
    select_items: 'Please select items',
    restore_ok: 'Restored successfully',
    restore_fail: 'Restore failed',
    bulk_restore_done: 'Bulk restore completed',
    cleaned: 'Removed {removed} file(s), freed {freed}',
    user_label: 'User: {user}',
  },
};

let lang = localStorage.getItem('ops_trash_lang') || (navigator.language.startsWith('zh') ? 'zh' : 'en');
let cachedFiles = [];

function t(key, vars = {}) {
  let s = (I18N[lang] && I18N[lang][key]) || key;
  for (const [k, v] of Object.entries(vars)) {
    s = s.replace(`{${k}}`, v);
  }
  return s;
}

function applyI18n() {
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.querySelectorAll('.lang-switch [data-lang]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });
}

function toast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast-msg ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

async function apiGet(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

async function apiPost(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

function humanSize(n) {
  if (n < 1024) return n + ' B';
  const units = ['KB', 'MB', 'GB', 'TB'];
  let i = 0;
  n /= 1024;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return n.toFixed(2) + ' ' + units[i];
}

function renderRows(files) {
  const tbody = document.getElementById('files-body');
  const empty = document.getElementById('empty-state');
  tbody.innerHTML = '';

  if (!files.length) {
    empty.classList.remove('d-none');
    return;
  }
  empty.classList.add('d-none');

  for (const f of files) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><input data-id="${f.id}" class="row-check" type="checkbox"></td>
      <td>${f.id}</td>
      <td class="path-cell" title="${escapeHtml(f.original_path)}">${escapeHtml(f.original_path)}</td>
      <td>${escapeHtml(f.deleted_at || '')}</td>
      <td>${humanSize(f.size || 0)}</td>
      <td>${escapeHtml(f.user || '')}</td>
      <td><button class="btn btn-sm btn-success restore-btn" data-id="${f.id}">${t('restore')}</button></td>
    `;
    tbody.appendChild(tr);
  }
  attachHandlers();
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function filterFiles(query) {
  const q = query.trim().toLowerCase();
  if (!q) return cachedFiles;
  return cachedFiles.filter(f =>
    (f.original_path || '').toLowerCase().includes(q) ||
    (f.trash_name || '').toLowerCase().includes(q)
  );
}

async function refresh() {
  try {
    const [list, stats] = await Promise.all([apiGet('/api/list'), apiGet('/api/stats')]);
    cachedFiles = list.files || [];

    document.getElementById('stat-count').innerText = stats.total_files ?? 0;
    document.getElementById('stat-size').innerText = humanSize(stats.total_size || 0);
    document.getElementById('stat-today').innerText = stats.today_count ?? 0;
    document.getElementById('stat-expired').innerText = stats.expired ?? 0;

    const userEl = document.getElementById('current-user');
    if (stats.current_user) {
      userEl.textContent = t('user_label', { user: stats.current_user });
      userEl.classList.remove('d-none');
    }

    const q = document.getElementById('search-input').value;
    renderRows(filterFiles(q));
  } catch (e) {
    toast(String(e.message || e), 'error');
  }
}

function attachHandlers() {
  document.querySelectorAll('.restore-btn').forEach(b => {
    b.onclick = async () => {
      const id = parseInt(b.dataset.id, 10);
      try {
        const res = await apiPost('/api/restore', { ids: [id] });
        const item = res.results && res.results[0];
        if (item && item.status.startsWith('ok')) {
          toast(t('restore_ok'), 'success');
          refresh();
        } else {
          toast(t('restore_fail') + ': ' + JSON.stringify(res), 'error');
        }
      } catch (e) {
        toast(String(e.message || e), 'error');
      }
    };
  });
}

document.getElementById('refresh-btn').onclick = refresh;
document.getElementById('refresh2').onclick = refresh;

document.getElementById('clean-expired').onclick = async () => {
  if (!confirm(t('confirm_clean'))) return;
  try {
    const res = await apiPost('/api/clean', { days: 7 });
    toast(t('cleaned', { removed: res.removed, freed: humanSize(res.freed || 0) }), 'success');
    refresh();
  } catch (e) {
    toast(String(e.message || e), 'error');
  }
};

document.getElementById('bulk-restore').onclick = async () => {
  const checks = Array.from(document.querySelectorAll('.row-check'))
    .filter(c => c.checked)
    .map(c => parseInt(c.dataset.id, 10));
  if (!checks.length) {
    toast(t('select_items'), 'error');
    return;
  }
  try {
    await apiPost('/api/restore', { ids: checks });
    toast(t('bulk_restore_done'), 'success');
    refresh();
  } catch (e) {
    toast(String(e.message || e), 'error');
  }
};

document.getElementById('select-all').onchange = e => {
  const checked = e.target.checked;
  document.querySelectorAll('.row-check').forEach(c => { c.checked = checked; });
};

document.getElementById('search-input').oninput = e => {
  renderRows(filterFiles(e.target.value));
};

document.querySelectorAll('.lang-switch [data-lang]').forEach(btn => {
  btn.onclick = () => {
    lang = btn.dataset.lang;
    localStorage.setItem('ops_trash_lang', lang);
    applyI18n();
    renderRows(filterFiles(document.getElementById('search-input').value));
  };
});

applyI18n();
refresh();

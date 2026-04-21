(function () {
  const page = document.querySelector('.dashboard-page');
  if (!page) return;

  const endpoints = {
    list: page.dataset.listUrl,
    add: page.dataset.addUrl,
    delete: page.dataset.deleteUrl,
    refresh: page.dataset.refreshUrl,
    view: page.dataset.viewUrl,
  };

  const input = document.getElementById('add-input');
  const addBtn = document.getElementById('add-btn');
  const tbody = document.getElementById('tbody');
  const countEl = document.getElementById('count');
  const toast = document.getElementById('toast');
  const statsGrid = document.getElementById('stats-grid');

  let pollTimer = null;
  let profiles = [];
  let activeFilter = 'all';

  function esc(v) {
    var s = String(v || '');
    s = s.replace(/&/g, '&amp;');
    s = s.replace(/</g, '&lt;');
    s = s.replace(/>/g, '&gt;');
    s = s.replace(/"/g, '&quot;');
    return s;
  }

  function relTime(ts) {
    if (!ts) return '—';
    var delta = Math.floor(Date.now() / 1000 - ts);
    if (delta < 60) return 'Just now';
    if (delta < 3600) return Math.floor(delta / 60) + 'm ago';
    if (delta < 86400) return Math.floor(delta / 3600) + 'h ago';
    return Math.floor(delta / 86400) + 'd ago';
  }

  function showToast(msg, type) {
    toast.textContent = msg;
    toast.className = 'toast show' + (type ? ' ' + type : '');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(function () {
      toast.className = 'toast';
    }, 3000);
  }

  function badge(status) {
    if (status === 'done') return '<span class="badge badge-done">● Done</span>';
    if (status === 'scraping') return '<span class="badge badge-scraping">◌ Scraping…</span>';
    if (status === 'error') return '<span class="badge badge-error">✕ Error</span>';
    return '<span class="badge badge-pending">○ Pending</span>';
  }

  function goToProfile(url) {
    window.location = endpoints.view + '?url=' + encodeURIComponent(url);
  }

  function renderRow(p) {
    var avatar;
    if (p.has_photo) {
      avatar = '<img class="avatar" src="/api/profiles/photo?url=' + encodeURIComponent(p.url) + '" alt="">';
    } else {
      var initial = (p.name || '?')[0].toUpperCase();
      avatar = '<div class="avatar-placeholder">' + esc(initial) + '</div>';
    }

    var chips = '';
    if (p.open_to_work) chips += '<span class="chip chip-work">Open to Work</span>';
    if (p.open_to_hiring) chips += '<span class="chip chip-hiring">Hiring</span>';
    var chipsHtml = chips ? '<div class="profile-chips">' + chips + '</div>' : '';

    var isDone = p.status === 'done';
    var rowClass = isDone ? 'clickable' : '';
    var rowAttrs = isDone ? ' data-url="' + esc(p.url) + '" data-action="view"' : '';

    var refreshSvg = '<svg viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>';
    var trashSvg = '<svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>';

    return '<tr class="' + rowClass + '"' + rowAttrs + '>' +
      '<td><div class="profile-cell">' + avatar +
        '<div><div class="profile-name">' + esc(p.name || 'Unknown') + '</div>' +
        '<div class="profile-url">' + esc(p.url) + '</div>' + chipsHtml + '</div></div></td>' +
      '<td><div class="headline-cell">' + esc(p.headline || '—') + '</div></td>' +
      '<td>' + badge(p.status) + '</td>' +
      '<td class="time-cell">' + relTime(p.scraped_at) + '</td>' +
      '<td><div class="actions">' +
        '<button class="icon-btn" type="button" title="Refresh" data-action="refresh" data-url="' + esc(p.url) + '">' + refreshSvg + '</button>' +
        '<button class="icon-btn danger" type="button" title="Delete" data-action="delete" data-url="' + esc(p.url) + '">' + trashSvg + '</button>' +
      '</div></td></tr>';
  }

  function renderTable(list, emptyMsg) {
    countEl.textContent = list.length;

    if (!list.length) {
      var msg = emptyMsg || 'No profiles yet. Add a LinkedIn URL above.';
      tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state">' +
        '<svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>' +
        '<p>' + esc(msg) + '</p></div></td></tr>';
      return;
    }

    var html = '';
    for (var i = 0; i < list.length; i++) {
      html += renderRow(list[i]);
    }
    tbody.innerHTML = html;
  }

  function applyFilter() {
    var list = profiles;
    var empty = 'No profiles yet. Add a LinkedIn URL above.';

    if (activeFilter === 'open_to_work') {
      list = [];
      for (var i = 0; i < profiles.length; i++) {
        if (profiles[i].open_to_work) list.push(profiles[i]);
      }
      empty = 'No profiles marked as Open to Work.';
    } else if (activeFilter === 'hiring') {
      list = [];
      for (var j = 0; j < profiles.length; j++) {
        if (profiles[j].open_to_hiring) list.push(profiles[j]);
      }
      empty = 'No profiles marked as Hiring.';
    }

    renderTable(list, empty);
  }

  function renderStats(list) {
    var done = [];
    for (var i = 0; i < list.length; i++) {
      if (list[i].status === 'done') done.push(list[i]);
    }

    if (!done.length) {
      statsGrid.hidden = true;
      statsGrid.innerHTML = '';
      return;
    }

    statsGrid.hidden = false;

    var work = 0;
    var hiring = 0;
    for (var k = 0; k < done.length; k++) {
      if (done[k].open_to_work) work++;
      if (done[k].open_to_hiring) hiring++;
    }

    var workPct = Math.round((work / done.length) * 100);
    var hiringPct = Math.round((hiring / done.length) * 100);

    statsGrid.innerHTML =
      '<div class="stat-box stat-total">' +
        '<div class="stat-label">Total Profiles</div>' +
        '<div class="stat-count">' + done.length + '</div>' +
      '</div>' +
      '<div class="stat-box stat-work">' +
        '<div class="stat-label">Open to Work</div>' +
        '<div class="stat-count">' + work + '</div>' +
        '<div class="stat-share">' + workPct + '% of profiles</div>' +
      '</div>' +
      '<div class="stat-box stat-hiring">' +
        '<div class="stat-label">Hiring</div>' +
        '<div class="stat-count">' + hiring + '</div>' +
        '<div class="stat-share">' + hiringPct + '% of profiles</div>' +
      '</div>';
  }

  async function loadProfiles() {
    const res = await fetch(endpoints.list);
    if (!res.ok) return;

    profiles = await res.json();
    renderStats(profiles);
    applyFilter();

    clearTimeout(pollTimer);
    var busy = false;
    for (var i = 0; i < profiles.length; i++) {
      if (profiles[i].status === 'pending' || profiles[i].status === 'scraping') {
        busy = true;
        break;
      }
    }
    if (busy) pollTimer = setTimeout(loadProfiles, 3000);
  }

  async function onAdd() {
    var url = input.value.trim();
    if (!url || !url.startsWith('https://www.linkedin.com/in/')) {
      showToast('Enter a valid LinkedIn profile URL', 'error');
      return;
    }

    addBtn.disabled = true;
    try {
      const res = await fetch(endpoints.add, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url }),
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || 'Error', 'error');
        return;
      }
      input.value = '';
      showToast('Profile added — scraping in background…');
      loadProfiles();
    } catch (err) {
      showToast('Network error', 'error');
    } finally {
      addBtn.disabled = false;
    }
  }

  function onRefresh(url) {
    window.AppDialog.confirm({
      title: 'Recheck profile',
      message: 'This will scrape the profile again and overwrite the cached data.',
      confirmText: 'Recheck'
    }, function (ok) {
      if (!ok) return;
      fetch(endpoints.refresh, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
      }).then(function (res) {
        if (res.ok) {
          showToast('Re-scraping started…');
          loadProfiles();
        } else {
          showToast('Refresh failed', 'error');
        }
      });
    });
  }

  function onDelete(url) {
    window.AppDialog.confirm({
      title: 'Delete profile',
      message: 'This will permanently remove the profile and its cached data from the database.',
      confirmText: 'Delete',
      destructive: true
    }, function (ok) {
      if (!ok) return;
      fetch(endpoints.delete, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
      }).then(function (res) {
        if (res.ok) {
          showToast('Profile deleted');
          loadProfiles();
        } else {
          showToast('Delete failed', 'error');
        }
      });
    });
  }

  var filterBtns = document.querySelectorAll('.filter-btn');
  for (var i = 0; i < filterBtns.length; i++) {
    filterBtns[i].addEventListener('click', function (e) {
      var all = document.querySelectorAll('.filter-btn');
      for (var j = 0; j < all.length; j++) all[j].classList.remove('active');
      e.currentTarget.classList.add('active');
      activeFilter = e.currentTarget.dataset.filter;
      applyFilter();
    });
  }

  tbody.addEventListener('click', function (e) {
    var el = e.target.closest('[data-action]');
    if (!el) return;
    var action = el.dataset.action;
    var url = el.dataset.url;
    if (!url) return;

    if (action === 'view') return goToProfile(url);
    if (action === 'refresh') return onRefresh(url);
    if (action === 'delete') return onDelete(url);
  });

  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') onAdd();
  });

  addBtn.addEventListener('click', onAdd);

  renderTable([], 'No profiles yet. Add a LinkedIn URL above.');
  loadProfiles();
})();

(function () {
  var modal = document.getElementById('app-modal');
  if (!modal) return;

  var titleEl = document.getElementById('app-modal-title');
  var messageEl = document.getElementById('app-modal-message');
  var confirmBtn = document.getElementById('app-modal-confirm');
  var cancelBtn = document.getElementById('app-modal-cancel');
  var closeBtn = document.getElementById('app-modal-close');
  var card = modal.querySelector('.modal-card');

  var activeCallback = null;

  function hide(result) {
    if (!activeCallback) return;
    var cb = activeCallback;
    activeCallback = null;
    modal.hidden = true;
    document.body.style.overflow = '';
    cb(result);
  }

  window.AppDialog = {
    confirm: function (opts, done) {
      opts = opts || {};
      titleEl.textContent = opts.title || 'Confirm action';
      messageEl.textContent = opts.message || '';
      confirmBtn.textContent = opts.confirmText || 'Continue';

      var cls = 'modal-btn modal-btn-primary';
      if (opts.destructive) cls = 'modal-btn modal-btn-danger';
      confirmBtn.className = cls;

      activeCallback = done;
      modal.hidden = false;
      document.body.style.overflow = 'hidden';
      confirmBtn.focus();
    }
  };

  confirmBtn.addEventListener('click', function () { hide(true); });
  cancelBtn.addEventListener('click', function () { hide(false); });
  closeBtn.addEventListener('click', function () { hide(false); });

  modal.addEventListener('click', function (e) {
    if (!card.contains(e.target)) hide(false);
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !modal.hidden) hide(false);
  });

  document.addEventListener('click', function (e) {
    var link = e.target.closest('[data-signout-link]');
    if (!link) return;
    e.preventDefault();
    var href = link.href;
    window.AppDialog.confirm({
      title: 'Sign out',
      message: 'Your current session will end and you will be redirected to the login page.',
      confirmText: 'Sign out',
      destructive: true
    }, function (ok) {
      if (ok) window.location.href = href;
    });
  });
})();

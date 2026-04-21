document.querySelectorAll('.profile-avatar[data-fallback]').forEach((img) => {
  img.addEventListener('error', function () {
    const fallback = document.createElement('div');
    fallback.className = 'avatar-fallback';
    fallback.textContent = this.dataset.fallback || '?';
    this.replaceWith(fallback);
  });
});

document.querySelectorAll('[data-desc-toggle]').forEach((btn) => {
  btn.addEventListener('click', function () {
    const target = document.getElementById(this.dataset.descToggle);
    if (!target) return;
    const open = target.classList.toggle('open');
    this.textContent = open ? 'Show less' : 'Show more';
  });
});

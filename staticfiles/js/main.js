// Minimal frontend helpers

document.addEventListener('DOMContentLoaded', function () {
  // Example: confirm deletion
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (ev) {
      if (!confirm(el.getAttribute('data-confirm'))) ev.preventDefault();
    });
  });
});

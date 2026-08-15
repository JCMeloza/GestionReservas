// Menú hamburguesa: alterna la visibilidad del menú en móvil (JS vanilla mínimo)
(function () {
  var toggle = document.querySelector('.nav-toggle');
  var menu = document.querySelector('.nav-menu');
  if (!toggle || !menu) return;

  function closeMenu() {
    menu.classList.remove('nav-menu--open');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Abrir menú');
  }

  toggle.addEventListener('click', function () {
    var isOpen = menu.classList.toggle('nav-menu--open');
    toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    toggle.setAttribute('aria-label', isOpen ? 'Cerrar menú' : 'Abrir menú');
  });

  // Al pulsar un enlace en móvil, cerrar el menú
  menu.addEventListener('click', function (event) {
    if (event.target.closest('a')) closeMenu();
  });
})();

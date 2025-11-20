document.addEventListener('DOMContentLoaded', () => {
  /* NAV HAMBURGER */
  const navToggle = document.getElementById('navToggle');
  const mainNav = document.getElementById('mainNav');

  if (navToggle && mainNav) {
    navToggle.addEventListener('click', () => {
      navToggle.classList.toggle('active');
      mainNav.classList.toggle('open');
    });
  }

  /* AUTH MODAL */
  const authModal = document.getElementById('authModal');
  const areaLink = document.getElementById('area-riservata-link');
  const authClose = document.getElementById('authClose');

  function openAuth() {
    if (!authModal) return;
    authModal.classList.add('open');
    document.body.style.overflow = 'hidden';

    // di default mostra il tab "Accedi"
    const loginTabLink = document.querySelector('.auth-tab-group .auth-tab:first-child a');
    if (loginTabLink) {
      loginTabLink.click();
    }
  }

  function closeAuth() {
    if (!authModal) return;
    authModal.classList.remove('open');
    document.body.style.overflow = '';
  }

  if (areaLink) {
    areaLink.addEventListener('click', (e) => {
      e.preventDefault();
      openAuth();
    });
  }

  if (authClose) {
    authClose.addEventListener('click', closeAuth);
  }

  if (authModal) {
    authModal.addEventListener('click', (e) => {
      if (e.target === authModal) {
        closeAuth();
      }
    });
  }

  /* TAB LOGIN / REGISTRAZIONE */
  const tabLinks = document.querySelectorAll('.auth-tab-group .auth-tab a');
  const panes = document.querySelectorAll('.auth-tab-content .auth-pane');

  if (tabLinks.length && panes.length) {
    tabLinks.forEach((link) => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = link.getAttribute('href').replace('#', '');

        // attiva tab
        document.querySelectorAll('.auth-tab-group .auth-tab')
          .forEach((li) => li.classList.remove('active'));
        link.parentElement.classList.add('active');

        // mostra il pane giusto
        panes.forEach((pane) => {
          pane.classList.toggle('active', pane.id === targetId);
        });
      });
    });
  }

  /* LABEL FLOTANTI NEI CAMPI AUTH */
  const authInputs = document.querySelectorAll('.auth-field input');

  authInputs.forEach((input) => {
    const label = input.nextElementSibling;
    if (!label) return;

    const update = () => {
      if (input.value.trim() !== '') {
        label.classList.add('active');
      } else {
        label.classList.remove('active');
      }
    };

    input.addEventListener('focus', () => {
      label.classList.add('highlight');
    });

    input.addEventListener('blur', () => {
      label.classList.remove('highlight');
      update();
    });

    input.addEventListener('input', update);

    // inizializza (utile se il browser precompila)
    update();
  });
});





document.addEventListener('DOMContentLoaded', () => {
  // -------------------------
  // NAVBAR / HAMBURGER
  // -------------------------
  const navToggle = document.getElementById('navToggle');
  const mainNav   = document.getElementById('mainNav');

  if (navToggle && mainNav) {
    // apre/chiude menu mobile
    navToggle.addEventListener('click', () => {
      navToggle.classList.toggle('active');
      mainNav.classList.toggle('open');
    });

    // quando clicchi un link del menu, chiudi il menu (su mobile)
    mainNav.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        navToggle.classList.remove('active');
        mainNav.classList.remove('open');
      });
    });
  }

  // -------------------------
  // MODAL AREA RISERVATA
  // -------------------------
  const authModal     = document.getElementById('authModal');
  const authContainer = document.getElementById('authContainer');
  const authClose     = document.getElementById('authClose');
  const areaLink      = document.getElementById('area-riservata-link');
  const goToLogin     = document.getElementById('goToLogin');
  const goToRegister  = document.getElementById('goToRegister');

  function openAuthModal(showRegister = false) {
    if (!authModal || !authContainer) return;
    authModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    if (showRegister) {
      authContainer.classList.add('right-panel-active');
    } else {
      authContainer.classList.remove('right-panel-active');
    }
  }

  function closeAuthModal() {
    if (!authModal || !authContainer) return;
    authModal.style.display = 'none';
    document.body.style.overflow = '';
  }

  // click su "AREA RISERVATA" nella navbar
  if (areaLink) {
    areaLink.addEventListener('click', (e) => {
      e.preventDefault();
      openAuthModal(false); // di default mostra il blocco LOGIN
    });
  }

  // bottone X per chiudere
  if (authClose) {
    authClose.addEventListener('click', (e) => {
      e.preventDefault();
      closeAuthModal();
    });
  }

  // chiusura cliccando fuori dal box
  if (authModal) {
    authModal.addEventListener('click', (e) => {
      if (e.target === authModal) {
        closeAuthModal();
      }
    });
  }

  // ESC per chiudere
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeAuthModal();
    }
  });

  // switch LOGIN / REGISTER
  if (goToLogin) {
    goToLogin.addEventListener('click', (e) => {
      e.preventDefault();
      authContainer.classList.remove('right-panel-active');
    });
  }

  if (goToRegister) {
    goToRegister.addEventListener('click', (e) => {
      e.preventDefault();
      authContainer.classList.add('right-panel-active');
    });
  }
});


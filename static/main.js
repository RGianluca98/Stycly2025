// main.js

document.addEventListener('DOMContentLoaded', () => {
  // NAVBAR MOBILE
  const navToggle = document.getElementById('navToggle');
  const mainNav   = document.getElementById('mainNav');

  if (navToggle && mainNav) {
    navToggle.addEventListener('click', () => {
      navToggle.classList.toggle('active');
      mainNav.classList.toggle('open');
      document.body.classList.toggle('nav-open');
    });

    // Chiudi menu quando clicchi su un link
    mainNav.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        mainNav.classList.remove('open');
        navToggle.classList.remove('active');
        document.body.classList.remove('nav-open');
      });
    });
  }

  // MODAL AUTH (Area riservata)
  const areaRiservataLink = document.getElementById('area-riservata-link');
  const authModal         = document.getElementById('authModal');
  const authContainer     = document.getElementById('authContainer');
  const authClose         = document.getElementById('authClose');
  const goToLogin         = document.getElementById('goToLogin');
  const goToRegister      = document.getElementById('goToRegister');

  function openAuthModal() {
    if (!authModal) return;
    authModal.classList.add('show');
    document.body.classList.add('nav-open');
  }

  function closeAuthModal() {
    if (!authModal) return;
    authModal.classList.remove('show');
    document.body.classList.remove('nav-open');
  }

  if (areaRiservataLink) {
    areaRiservataLink.addEventListener('click', (e) => {
      e.preventDefault();
      openAuthModal();
    });
  }

  if (authClose) {
    authClose.addEventListener('click', () => {
      closeAuthModal();
    });
  }

  // Chiudi cliccando fuori dal contenuto
  if (authModal && authContainer) {
    authModal.addEventListener('click', (e) => {
      if (!authContainer.contains(e.target)) {
        closeAuthModal();
      }
    });
  }

  // Switch login/register
  if (goToLogin && goToRegister && authContainer) {
    goToRegister.addEventListener('click', () => {
      authContainer.classList.add('right-panel-active');
    });

    goToLogin.addEventListener('click', () => {
      authContainer.classList.remove('right-panel-active');
    });
  }
});




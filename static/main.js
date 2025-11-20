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
  const authModal     = document.getElementById('authModal');
  const authContainer = document.getElementById('authContainer');
  const areaLink      = document.getElementById('area-riservata-link');
  const authClose     = document.getElementById('authClose');
  const goToLogin     = document.getElementById('goToLogin');
  const goToRegister  = document.getElementById('goToRegister');

  function openAuth() {
  if (!authModal) return;
  authModal.classList.add('open');
  document.body.style.overflow = 'hidden';
  if (authContainer) authContainer.classList.remove('right-panel-active');

  // Pulisce sempre tutti i campi del modal ad ogni apertura
  const inputs = authModal.querySelectorAll('input');
  inputs.forEach(input => {
    if (input.type === 'password' || input.type === 'text' || input.type === 'email') {
      input.value = '';
    }
  });
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

  if (goToLogin && authContainer) {
    goToLogin.addEventListener('click', () => {
      authContainer.classList.remove('right-panel-active');
    });
  }

  if (goToRegister && authContainer) {
    goToRegister.addEventListener('click', () => {
      authContainer.classList.add('right-panel-active');
    });
  }
});

  /* LABEL FLOTANTI NEL MODAL AUTH */
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

    // inizializza stato corretto se il browser ha messo valori
    update();
  });




document.addEventListener('DOMContentLoaded', () => {
  /* ================================
   *  NAV HAMBURGER
   * ============================== */
  const navToggle = document.getElementById('navToggle');
  const mainNav   = document.getElementById('mainNav');

  if (navToggle && mainNav) {
    navToggle.addEventListener('click', () => {
      navToggle.classList.toggle('active');
      mainNav.classList.toggle('open');
    });
  }

  /* ================================
   *  AUTH MODAL (login / register)
   * ============================== */
  const authModal  = document.getElementById('authModal');
  const areaLink   = document.getElementById('area-riservata-link');
  const authClose  = document.getElementById('authClose');
  const tabButtons = document.querySelectorAll('.auth-tab');
  const panels     = document.querySelectorAll('.auth-panel');

  function activateTab(targetId) {
    // attiva il bottone
    tabButtons.forEach(btn => {
      const t = btn.getAttribute('data-target');
      if (t === targetId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // mostra il pannello corrispondente
    panels.forEach(panel => {
      if (panel.id === targetId) {
        panel.classList.add('active');
      } else {
        panel.classList.remove('active');
      }
    });
  }

  function openAuth(defaultTabId = 'loginPanel') {
    if (!authModal) return;
    authModal.classList.add('open');
    document.body.style.overflow = 'hidden';
    // di default vai sulla tab login
    activateTab(defaultTabId);
    initFloatingLabels(); // assicura label corrette
  }

  function closeAuth() {
    if (!authModal) return;
    authModal.classList.remove('open');
    document.body.style.overflow = '';
  }

  if (areaLink) {
    areaLink.addEventListener('click', (e) => {
      e.preventDefault();
      openAuth('loginPanel');
    });
  }

  if (authClose) {
    authClose.addEventListener('click', closeAuth);
  }

  if (authModal) {
    // chiusura cliccando fuori dalla card
    authModal.addEventListener('click', (e) => {
      if (e.target === authModal) {
        closeAuth();
      }
    });
  }

  // click sulle tab
  if (tabButtons.length) {
    tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-target');
        if (targetId) {
          activateTab(targetId);
        }
      });
    });
  }

  /* ================================
   *  LABEL FLOTTANTI (login / register)
   * ============================== */
  function initFloatingLabels() {
    const inputs = document.querySelectorAll(
      '.auth-field-wrap input, .auth-field-wrap textarea'
    );

    inputs.forEach(input => {
      const label = input.previousElementSibling;
      if (!label) return;

      const update = () => {
        if (input.value.trim() === '') {
          label.classList.remove('active');
        } else {
          label.classList.add('active');
        }
      };

      input.addEventListener('focus', () => {
        label.classList.add('highlight');
        if (input.value.trim() !== '') {
          label.classList.add('active');
        }
      });

      input.addEventListener('blur', () => {
        label.classList.remove('highlight');
        if (input.value.trim() === '') {
          label.classList.remove('active');
        }
      });

      input.addEventListener('input', update);

      // stato iniziale se il browser compila qualcosa
      update();
    });
  }

  // inizializza una volta (nel caso in cui il modal parta già aperto)
  initFloatingLabels();
});




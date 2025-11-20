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
    // attiva il bottone giusto
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

    // mostra il modal
    authModal.classList.add('open');
    document.body.style.overflow = 'hidden';

    // reset dei campi (login + register) ogni volta che apro il modal
    const inputs = authModal.querySelectorAll('input, textarea');
    inputs.forEach(input => {
      input.value = '';
    });

    // attivo di default la tab di login
    activateTab(defaultTabId);

    // riallineo le label flottanti allo stato vuoto
    initFloatingLabels();
  }

  function closeAuth() {
    if (!authModal) return;
    authModal.classList.remove('open');
    document.body.style.overflow = '';
  }

  // click su "AREA RISERVATA" ➜ apri direttamente LOGIN
  if (areaLink) {
    areaLink.addEventListener('click', (e) => {
      e.preventDefault();
      openAuth('loginPanel'); // forza sempre il pannello login
    });
  }

  if (authClose) {
    authClose.addEventListener('click', closeAuth);
  }

  if (authModal) {
    // chiusura cliccando sullo sfondo scuro
    authModal.addEventListener('click', (e) => {
      if (e.target === authModal) {
        closeAuth();
      }
    });
  }

  // click sulle tab "Accedi" / "Registrati"
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
   *  USER MENU DROPDOWN
   * ============================== */
  const userMenu = document.querySelector('.user-menu');
  const userMenuToggle = document.querySelector('.user-menu-toggle');

  if (userMenu && userMenuToggle) {
    userMenuToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      userMenu.classList.toggle('open');
    });

    document.addEventListener('click', () => {
      userMenu.classList.remove('open');
    });

    // evita chiusura se clicco dentro il dropdown
    const dropdown = userMenu.querySelector('.user-menu-dropdown');
    if (dropdown) {
      dropdown.addEventListener('click', (e) => {
        e.stopPropagation();
      });
    }
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
          label.classList.remove('highlight');
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

      // stato iniziale (utile se il browser ha provato ad autocompilare)
      update();
    });
  }

  // inizializzazione generale (nel caso il modal sia già visibile)
  initFloatingLabels();

  /* ================================
   *  FLASH TOAST (auto-hide)
   * ============================== */
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(flash => {
    // chiudo al click
    flash.addEventListener('click', () => {
      flash.classList.add('flash-hide');
      setTimeout(() => flash.remove(), 300);
    });

    // auto-hide dopo 4 secondi
    setTimeout(() => {
      flash.classList.add('flash-hide');
      setTimeout(() => flash.remove(), 300);
    }, 4000);
  });
});





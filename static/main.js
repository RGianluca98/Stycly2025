// MAIN.JS - Gestione header "blob", menu overlay e modal login/register

document.addEventListener("DOMContentLoaded", () => {
  // HEADER BLOB MENU
  const header = document.querySelector(".stycly-header.overlay-header");
  const burger = document.querySelector(".burger");

  if (burger && header) {
    burger.addEventListener("click", () => {
      header.classList.toggle("clicked");
    });
  }

  // Selezione voci menu nel blob (solo highlight + chiusura)
  const navItems = document.querySelectorAll(".overlay-nav ul li");

  navItems.forEach((li) => {
    li.addEventListener("click", () => {
      navItems.forEach((item) => {
        item.classList.remove("selected");
        item.classList.add("notselected");
      });
      li.classList.add("selected");
      li.classList.remove("notselected");

      // chiudi il menu dopo il click (se non è AREA RISERVATA)
      const link = li.querySelector("a");
      if (link && !link.dataset.authOpen && header.classList.contains("clicked")) {
        header.classList.remove("clicked");
      }
    });
  });

  // --------- MODAL LOGIN / REGISTER (AREA RISERVATA) ---------
  const areaRiservataLink = document.querySelector('[data-auth-open="true"]');
  const authModal = document.getElementById("auth-modal");
  const authContainer = document.getElementById("auth-container");
  const authCloseBtn = document.getElementById("auth-close-btn");
  const signUpBtn = document.getElementById("signUp");
  const signInBtn = document.getElementById("signIn");

  // Apri modal
  if (areaRiservataLink && authModal) {
    areaRiservataLink.addEventListener("click", (e) => {
      e.preventDefault();
      authModal.style.display = "flex";
      // chiudo il menu overlay se è aperto
      if (header && header.classList.contains("clicked")) {
        header.classList.remove("clicked");
      }
    });
  }

  // Chiudi modal (bottone X)
  if (authCloseBtn && authModal) {
    authCloseBtn.addEventListener("click", () => {
      authModal.style.display = "none";
    });
  }

  // Chiudi modal cliccando sullo sfondo scuro
  if (authModal) {
    authModal.addEventListener("click", (e) => {
      if (e.target === authModal) {
        authModal.style.display = "none";
      }
    });
  }

  // Switch SignUp / SignIn
  if (signUpBtn && authContainer) {
    signUpBtn.addEventListener("click", () => {
      authContainer.classList.add("right-panel-active");
    });
  }
  if (signInBtn && authContainer) {
    signInBtn.addEventListener("click", () => {
      authContainer.classList.remove("right-panel-active");
    });
  }
});

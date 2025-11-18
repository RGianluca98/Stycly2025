// main.js

document.addEventListener("DOMContentLoaded", () => {
  // -----------------------------
  // NAVBAR: dropdown "Wardrobe"
  // -----------------------------
  document.querySelectorAll(".stycly-nav-dropdown-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const parent = btn.closest(".stycly-nav-dropdown-parent");
      const isOpen = parent.classList.contains("open");
      document
        .querySelectorAll(".stycly-nav-dropdown-parent")
        .forEach((p) => p.classList.remove("open"));
      if (!isOpen) {
        parent.classList.add("open");
      }
    });
  });

  // Chiudi dropdown cliccando fuori
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".stycly-nav-dropdown-parent")) {
      document
        .querySelectorAll(".stycly-nav-dropdown-parent")
        .forEach((p) => p.classList.remove("open"));
    }
  });

  // -----------------------------
  // NAVBAR: hamburger (mobile)
  // -----------------------------
  const burger = document.querySelector(".stycly-nav-hamburger");
  const nav = document.querySelector(".stycly-nav");

  if (burger && nav) {
    burger.addEventListener("click", () => {
      burger.classList.toggle("active");
      nav.classList.toggle("open");
    });

    // chiudi il menu quando clicchi su un link
    nav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        burger.classList.remove("active");
        nav.classList.remove("open");
      });
    });

    // se si torna a desktop, assicuriamoci che la nav sia visibile
    window.addEventListener("resize", () => {
      if (window.innerWidth > 700) {
        nav.classList.remove("open");
        burger.classList.remove("active");
      }
    });
  }

  // -----------------------------
  // MODALE HOME: scelta Wardrobe
  // -----------------------------
  const wardrobeModal = document.getElementById("wardrobe-modal");
  const wardrobeCta = document.getElementById("wardrobe-cta");
  const wardrobeCloseBtn = wardrobeModal
    ? wardrobeModal.querySelector(".stycly-modal-close")
    : null;

  if (wardrobeModal && wardrobeCta && wardrobeCloseBtn) {
    wardrobeCta.addEventListener("click", () => {
      wardrobeModal.style.display = "flex";
    });

    wardrobeCloseBtn.addEventListener("click", () => {
      wardrobeModal.style.display = "none";
    });

    wardrobeModal.addEventListener("click", (e) => {
      if (e.target === wardrobeModal) {
        wardrobeModal.style.display = "none";
      }
    });
  }

  // -----------------------------
  // MODALE AUTH: Area riservata
  // -----------------------------
  const authModal = document.getElementById("auth-modal");
  const openAuthBtn = document.getElementById("open-auth-modal");
  const authContainer = document.getElementById("container");
  const signUpButton = document.getElementById("signUp");
  const signInButton = document.getElementById("signIn");

  if (openAuthBtn && authModal && authContainer) {
    // apri modale
    openAuthBtn.addEventListener("click", () => {
      authModal.style.display = "flex";
      authContainer.classList.remove("right-panel-active");
    });

    // chiudi cliccando fuori
    authModal.addEventListener("click", (e) => {
      if (e.target === authModal) {
        authModal.style.display = "none";
      }
    });
  }

  if (signUpButton && authContainer) {
    signUpButton.addEventListener("click", () => {
      authContainer.classList.add("right-panel-active");
    });
  }

  if (signInButton && authContainer) {
    signInButton.addEventListener("click", () => {
      authContainer.classList.remove("right-panel-active");
    });
  }

  // -----------------------------
  // GSAP wave animation
  // -----------------------------
  if (window.gsap && window.MorphSVGPlugin) {
    const firstWave = document.getElementById("squiggle");
    if (firstWave) {
      window.gsap.to(firstWave, {
        duration: 2,
        repeat: -1,
        yoyo: true,
        ease: "power2.inOut",
        morphSVG: "#squiggleAlt",
      });
    }
  }
});

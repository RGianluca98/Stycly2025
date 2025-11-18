// MAIN.JS - Gestione header "blob", menu e modale

document.addEventListener("DOMContentLoaded", () => {
  // HEADER BLOB MENU
  const header = document.querySelector(".stycly-header.overlay-header");
  const burger = document.querySelector(".burger");

  if (burger && header) {
    burger.addEventListener("click", () => {
      header.classList.toggle("clicked");
    });
  }

  // Selezione voci menu nel blob
  const navItems = document.querySelectorAll(".overlay-nav ul li");

  navItems.forEach((li) => {
    li.addEventListener("click", () => {
      // evidenzia quella cliccata (se vuoi lo stile selected/notselected)
      navItems.forEach((item) => {
        item.classList.remove("selected");
        item.classList.add("notselected");
      });
      li.classList.add("selected");
      li.classList.remove("notselected");

      // chiudi il menu dopo il click (utile su mobile)
      if (header && header.classList.contains("clicked")) {
        header.classList.remove("clicked");
      }
    });
  });

  // MODAL CTA HOME (se usi ancora il popup con id wardrobe-modal)
  const modal = document.getElementById("wardrobe-modal");
  const cta = document.getElementById("wardrobe-cta");
  const closeBtn = modal ? modal.querySelector(".stycly-modal-close") : null;

  if (cta && modal && closeBtn) {
    cta.addEventListener("click", () => {
      modal.style.display = "flex";
    });

    closeBtn.addEventListener("click", () => {
      modal.style.display = "none";
    });

    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.style.display = "none";
      }
    });
  }

  // GSAP wave animation (se stai usando GSAP + MorphSVG)
  if (window.gsap && window.MorphSVGPlugin) {
    const firstWave = document.getElementById("squiggle");
    const altWave = document.getElementById("squiggleAlt");

    if (firstWave && altWave) {
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

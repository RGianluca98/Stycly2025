// Navbar dropdown
document.querySelectorAll('.stycly-nav-dropdown-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
        e.preventDefault();
        const parent = btn.closest('.stycly-nav-dropdown-parent');
        parent.classList.toggle('open');
    });
});
document.addEventListener("DOMContentLoaded", () => {
  const header = document.querySelector(".stycly-header");
  const burger = document.querySelector(".stycly-nav-hamburger");

  if (burger && header) {
    burger.addEventListener("click", () => {
      header.classList.toggle("nav-open");
    });
  }

  // chiudi il menu quando clicchi un link
  document.querySelectorAll(".stycly-nav a").forEach(link => {
    link.addEventListener("click", () => {
      header.classList.remove("nav-open");
    });
  });
});


// Hamburger menu (mobile)
const hamburger = document.querySelector('.stycly-nav-hamburger');
const nav = document.querySelector('.stycly-nav');
function toggleNav() {
    if (window.innerWidth <= 600) {
        nav.style.display = nav.style.display === 'flex' ? 'none' : 'flex';
    }
}
if (hamburger && nav) {
    hamburger.addEventListener('click', toggleNav);
    window.addEventListener('resize', () => {
        if (window.innerWidth > 600) nav.style.display = 'flex';
        else nav.style.display = 'none';
    });
}

// Modal popup
const modal = document.getElementById('wardrobe-modal');
const cta = document.getElementById('wardrobe-cta');
const closeBtn = document.querySelector('.stycly-modal-close');
if (cta && modal && closeBtn) {
    cta.addEventListener('click', function() {
        modal.style.display = 'flex';
    });
    closeBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    modal.addEventListener('click', function(e) {
        if (e.target === modal) modal.style.display = 'none';
    });
}

// GSAP wave animation
document.addEventListener("DOMContentLoaded", () => {
    if (window.gsap && window.MorphSVGPlugin) {
        const firstWave = document.getElementById("squiggle");
        if (firstWave) {
            window.gsap.to(firstWave, {
                duration: 2,
                repeat: -1,
                yoyo: true,
                ease: "power2.inOut",
                morphSVG: "#squiggleAlt"
            });
        }
    }
});
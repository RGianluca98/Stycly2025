// static/cart.js

// --- CONFIG ---
const CART_KEY = 'styclyCart';
let cart = [];

// --- STORAGE ---
function loadCart() {
  try {
    const saved = localStorage.getItem(CART_KEY);
    cart = saved ? JSON.parse(saved) : [];
  } catch (e) {
    cart = [];
  }
}

function saveCart() {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
}

function getTotalItems() {
  return cart.reduce((sum, item) => sum + item.qty, 0);
}

// --- RENDER DEL POPUP CARRELLO ---
function renderCart() {
  const listEl = document.querySelector('.cart-items');
  const emptyEl = document.querySelector('.cart-empty');
  const totalEl = document.getElementById('cart-total-items');

  if (!listEl || !emptyEl || !totalEl) return;

  listEl.innerHTML = '';

  if (cart.length === 0) {
    emptyEl.style.display = 'block';
    totalEl.textContent = '0';
    return;
  }

  emptyEl.style.display = 'none';

  cart.forEach((item, index) => {
    const row = document.createElement('div');
    row.className = 'mini-cart-item';

    row.innerHTML = `
      <div class="mini-cart-img">
        <img src="/immagini/${item.img || ''}" alt="${item.name || ''}">

      </div>
      <div class="mini-cart-info">
        <div class="mini-cart-header">
          <h4 class="mini-cart-title">${item.name || ''}</h4>
          <button type="button"
                  class="mini-cart-remove"
                  data-index="${index}"
                  aria-label="Rimuovi">
            <svg class="icon-16">
              <use xlink:href="#close"></use>
            </svg>
          </button>
        </div>
        <div class="mini-cart-qty">
          <button type="button"
                  class="qty-btn qty-minus"
                  data-index="${index}">-</button>
          <span class="qty-value">${item.qty}</span>
          <button type="button"
                  class="qty-btn qty-plus"
                  data-index="${index}">+</button>
        </div>
      </div>
    `;

    listEl.appendChild(row);
  });

  totalEl.textContent = getTotalItems();
}

// --- LOGICA CARRELLO ---
function addToCart(product) {
  if (!product || !product.id) return;

  const existing = cart.find((i) => i.id === product.id);
  if (existing) {
    existing.qty += 1;
  } else {
    cart.push({
      id: product.id,
      name: product.name || '',
      img: product.img || '',
      qty: 1,
    });
  }
  saveCart();
  renderCart();
}

function openCart() {
  const overlay = document.getElementById('cart-overlay');
  if (overlay) overlay.classList.remove('cart-hidden');
}

function closeCart() {
  const overlay = document.getElementById('cart-overlay');
  if (overlay) overlay.classList.add('cart-hidden');
}

function openSearch() {
  const overlay = document.getElementById('search-overlay');
  if (overlay) overlay.classList.remove('cart-hidden');
}

function closeSearch() {
  const overlay = document.getElementById('search-overlay');
  if (overlay) overlay.classList.add('cart-hidden');
}

// --- EVENTI GLOBALI ---
document.addEventListener('DOMContentLoaded', function () {
  loadCart();
  renderCart();

  window.styclyAddToCart = addToCart;
  window.styclyOpenCart = openCart;
  // Click su "aggiungi al carrello" (products.html, ecc.)
  // Basta avere un elemento con classe .add-to-cart e:
  // data-id, data-name, data-img
  document.body.addEventListener('click', function (e) {
    const addBtn = e.target.closest('.add-to-cart');
    if (addBtn) {
      const product = {
        id: addBtn.dataset.id,
        name: addBtn.dataset.name,
        img: addBtn.dataset.img,
      };
      addToCart(product);
      openCart();
    }

    // Gestione +/- quantità
    const minus = e.target.closest('.qty-minus');
    const plus = e.target.closest('.qty-plus');
    const remove = e.target.closest('.mini-cart-remove');

    if (minus) {
      const i = parseInt(minus.dataset.index, 10);
      if (!isNaN(i)) {
        if (cart[i].qty > 1) {
          cart[i].qty -= 1;
        } else {
          cart.splice(i, 1);
        }
        saveCart();
        renderCart();
      }
    }

    if (plus) {
      const i = parseInt(plus.dataset.index, 10);
      if (!isNaN(i)) {
        cart[i].qty += 1;
        saveCart();
        renderCart();
      }
    }

    if (remove) {
      const i = parseInt(remove.dataset.index, 10);
      if (!isNaN(i)) {
        cart.splice(i, 1);
        saveCart();
        renderCart();
      }
    }
  });

  // Apertura / chiusura carrello
  const btnOpenCart = document.getElementById('open-cart');
  const btnCloseCart = document.getElementById('close-cart');
  const cartOverlay = document.getElementById('cart-overlay');
  const btnContinueSelection = document.getElementById('cart-continue-selection');
  const btnProceedOrder = document.getElementById('cart-proceed');

  if (btnOpenCart) btnOpenCart.addEventListener('click', openCart);
  if (btnCloseCart) btnCloseCart.addEventListener('click', closeCart);
  if (btnContinueSelection) {
    btnContinueSelection.addEventListener('click', () => {
      closeCart();
      const target = document.getElementById('products');
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else {
        window.location.href = '/#products';
      }
    });
  }
  if (btnProceedOrder) {
    btnProceedOrder.addEventListener('click', () => {
      if (typeof window.styclyProceedOrder === 'function') {
        window.styclyProceedOrder(cart);
      } else {
        alert('Procedi con l’ordine: collega qui il flusso di checkout.');
      }
    });
  }
  if (cartOverlay) {
    cartOverlay.addEventListener('click', (e) => {
      if (e.target === cartOverlay) closeCart();
    });
  }

  // Apertura / chiusura search
  const btnOpenSearch = document.getElementById('open-search');
  const btnCloseSearch = document.getElementById('close-search');
  const searchOverlay = document.getElementById('search-overlay');

  if (btnOpenSearch) btnOpenSearch.addEventListener('click', openSearch);
  if (btnCloseSearch) btnCloseSearch.addEventListener('click', closeSearch);
  if (searchOverlay) {
    searchOverlay.addEventListener('click', (e) => {
      if (e.target === searchOverlay) closeSearch();
    });
  }
});

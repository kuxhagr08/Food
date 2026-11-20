/**
 * QuickBite Core Client App
 */

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const CSRF_TOKEN = getCookie('csrftoken');

function showToast(message, type = 'info', duration = 3500) {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <div style="flex-grow:1; font-size:0.9rem; font-weight:500;">${message}</div>
    <button type="button" style="background:none;border:none;cursor:pointer;font-size:1.1rem;color:#9ca3af;" onclick="this.parentElement.remove()">×</button>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// Cart Management
async function addToCart(itemId, quantity = 1, clearExisting = false) {
  try {
    const res = await fetch('/orders/api/cart/add/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': CSRF_TOKEN
      },
      body: JSON.stringify({ item_id: itemId, quantity, clear_existing: clearExisting })
    });

    const data = await res.json();

    if (res.status === 409 && data.conflict) {
      if (confirm(data.message)) {
        return addToCart(itemId, quantity, true);
      }
      return;
    }

    if (!res.ok) {
      showToast(data.error || "Failed to add item to cart.", "error");
      return;
    }

    showToast(`Added ${data.item_name} to cart!`, "success");
    updateCartBadges(data.cart_count);

    // Update quantity stepper on page if present
    const stepper = document.getElementById(`stepper-${itemId}`);
    if (stepper) {
      const valElem = stepper.querySelector('.qty-value');
      if (valElem) valElem.textContent = data.quantity;
      stepper.style.display = 'inline-flex';
      const addBtn = document.getElementById(`add-btn-${itemId}`);
      if (addBtn) addBtn.style.display = 'none';
    }
  } catch (err) {
    showToast("Network error. Please try again.", "error");
  }
}

async function updateCartItem(itemId, action) {
  try {
    const res = await fetch('/orders/api/cart/update/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': CSRF_TOKEN
      },
      body: JSON.stringify({ item_id: itemId, action })
    });

    const data = await res.json();
    if (res.ok) {
      window.location.reload();
    } else {
      showToast(data.error || "Error updating cart", "error");
    }
  } catch (err) {
    showToast("Network error", "error");
  }
}

function updateCartBadges(count) {
  document.querySelectorAll('.cart-badge-count').forEach(el => {
    el.textContent = count;
    el.classList.toggle('visible', count > 0);
  });
  document.querySelectorAll('.mobile-cart-badge').forEach(el => {
    el.textContent = count;
    el.classList.toggle('visible', count > 0);
  });
}


/* =============================================
   KOMJAR 2026 — MAIN.JS
   Hamburger Menu + Quota Enforcement Logic
   ============================================= */

document.addEventListener('DOMContentLoaded', () => {

  // ─── 1. HAMBURGER MENU ───────────────────────
  const burger = document.getElementById('hamburger');
  const navLinks = document.getElementById('nav-links');

  if (burger && navLinks) {
    burger.addEventListener('click', () => {
      burger.classList.toggle('open');
      navLinks.classList.toggle('open');
      burger.setAttribute('aria-expanded', burger.classList.contains('open'));
    });

    // Close menu on nav link click (mobile)
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        burger.classList.remove('open');
        navLinks.classList.remove('open');
        burger.setAttribute('aria-expanded', 'false');
      });
    });

    // Close on outside click
    document.addEventListener('click', e => {
      if (!burger.contains(e.target) && !navLinks.contains(e.target)) {
        burger.classList.remove('open');
        navLinks.classList.remove('open');
        burger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // ─── 2. ACTIVE NAV LINK ──────────────────────
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPage) link.classList.add('active');
  });

  // ─── 3. QUOTA MANAGEMENT SYSTEM ──────────────
  /*
   * Simulated quota data. In production, replace `quotaData`
   * with a fetch() call to Google Apps Script or Supabase endpoint
   * that returns { department_name: current_count } JSON.
   *
   * Example Google Apps Script URL:
   * const res = await fetch('https://script.google.com/macros/s/YOUR_ID/exec?action=getQuota');
   * const quotaData = await res.json();
   */
  const QUOTA_MAX = 4;

  const quotaData = {
    "Pendidikan Dasar (SD)"       : 2,
    "Pendidikan Menengah (SMP)"   : 4,
    "Sains & Matematika"          : 1,
    "Bahasa & Literasi"           : 3,
    "Seni & Kreativitas"          : 0,
  };

  const deptSelect = document.getElementById('departemen');
  if (deptSelect) {
    updateQuotaOptions(deptSelect, quotaData);
    renderQuotaSummary(quotaData);

    // Re-render quota indicator on change
    deptSelect.addEventListener('change', () => {
      const selected = deptSelect.value;
      const count    = quotaData[selected] ?? 0;
      updateSelectedQuotaInfo(selected, count);
    });
  }

  /**
   * Disables options that have reached QUOTA_MAX.
   * Labels them with "(KUOTA PENUH!)"
   */
  function updateQuotaOptions(selectEl, data) {
    Array.from(selectEl.options).forEach(opt => {
      if (!opt.value) return; // skip placeholder
      const count = data[opt.value] ?? 0;
      if (count >= QUOTA_MAX) {
        opt.disabled = true;
        if (!opt.textContent.includes('KUOTA PENUH')) {
          opt.textContent = `${opt.value} — (KUOTA PENUH!)`;
        }
      } else {
        opt.disabled = false;
        // Restore clean label (strip "KUOTA PENUH" if previously set)
        opt.textContent = opt.value;
      }
    });
  }

  /**
   * Shows inline quota info below the select.
   */
  function updateSelectedQuotaInfo(dept, count) {
    const infoEl = document.getElementById('quota-selected-info');
    if (!infoEl) return;
    const sisa  = QUOTA_MAX - count;
    const isFull = sisa <= 0;
    infoEl.innerHTML = isFull
      ? `<span class="quota-status quota-full">✗ Departemen ini sudah penuh (${QUOTA_MAX}/${QUOTA_MAX})</span>`
      : `<span class="quota-status quota-ok">✓ Sisa slot: ${sisa} dari ${QUOTA_MAX}</span>`;
  }

  /**
   * Renders quota summary cards (if element #quota-summary exists).
   */
  function renderQuotaSummary(data) {
    const summaryEl = document.getElementById('quota-summary');
    if (!summaryEl) return;

    summaryEl.innerHTML = Object.entries(data).map(([dept, count]) => {
      const pct    = Math.min((count / QUOTA_MAX) * 100, 100);
      const isFull = count >= QUOTA_MAX;
      return `
        <div class="quota-card ${isFull ? 'quota-card--full' : ''}">
          <div class="quota-card-label">${dept}</div>
          <div class="quota-bar-wrap">
            <div class="quota-bar ${isFull ? 'full' : ''}" style="width:${pct}%"></div>
          </div>
          <div class="quota-card-count">
            ${count}/${QUOTA_MAX} ${isFull ? '— <strong>PENUH</strong>' : 'terdaftar'}
          </div>
        </div>`;
    }).join('');
  }

  // ─── 4. FILE SIZE VALIDATION ─────────────────
  const fileInputs = document.querySelectorAll('input[type="file"]');
  fileInputs.forEach(input => {
    input.addEventListener('change', () => {
      const file = input.files[0];
      if (!file) return;
      const maxMB   = 2;
      const maxBytes = maxMB * 1024 * 1024;
      const errId   = input.getAttribute('data-error-id');
      const errEl   = errId ? document.getElementById(errId) : null;

      if (file.size > maxBytes) {
        input.value = '';
        input.classList.add('input-error');
        if (errEl) errEl.textContent = `Ukuran file melebihi batas ${maxMB}MB. Silakan unggah file yang lebih kecil.`;
      } else {
        input.classList.remove('input-error');
        if (errEl) errEl.textContent = '';
      }
    });
  });

  // ─── 5. FORM SUBMISSION REDIRECT ─────────────
  /*
   * Attach to each <form data-komjar="true"> element.
   * In production: replace the fetch target with your
   * Google Apps Script or Supabase endpoint URL.
   */
  document.querySelectorAll('form[data-komjar]').forEach(form => {
    form.addEventListener('submit', async e => {
      e.preventDefault();

      const submitBtn = form.querySelector('[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Mengirim...';
      }

      const data = Object.fromEntries(new FormData(form).entries());

      try {
        /*
         * PRODUCTION: uncomment and set YOUR_APPS_SCRIPT_URL
         *
         * const res = await fetch('YOUR_APPS_SCRIPT_URL', {
         *   method: 'POST',
         *   body: JSON.stringify(data),
         *   headers: { 'Content-Type': 'application/json' },
         * });
         * if (!res.ok) throw new Error('Submit gagal');
         */

        // DEMO: simulate 800ms network delay
        await new Promise(r => setTimeout(r, 800));

        window.location.href = 'success.html';
      } catch (err) {
        console.error('Submission error:', err);
        alert('Terjadi kesalahan saat mengirim data. Silakan coba lagi.');
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Kirim Data';
        }
      }
    });
  });

  // ─── 6. SMOOTH SCROLL (anchor links) ─────────
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

});

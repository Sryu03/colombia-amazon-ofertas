/**
 * Vitrina Colombia — Portal Web de Afiliados Amazon.com (Zero-Token Architecture)
 * Compatible con FastAPI (/api/deals, /api/previews, POST /api/scan)
 * y despliegue 100% estático en Vercel CDN (/data/deals.json, /data/outbox_cards.json).
 */

(() => {
  'use strict';

  const DEFAULT_TRM = 4150;
  const DEFAULT_TAG = 'pillepues-20';

  // Respaldo inicial por si aún no se ha corrido el pipeline local
  const FALLBACK_DEALS = [
    {
      asin: 'B0CHWRXH8B',
      title: 'Apple AirPods Pro (2.ª Generación) con Estuche MagSafe USB-C',
      category: 'Audio',
      price_usd: 169.99,
      original_price_usd: 249.00,
      avg_90d_usd: 199.99,
      lowest_90d_usd: 169.99,
      discount_pct: 32,
      tax_free_colombia: true,
      free_shipping_co: true,
      shipping_cost_usd: 0.0,
      requires_locker: false,
      estimated_tax_usd: 0.0,
      image_url: 'https://m.media-amazon.com/images/I/61SUj2aKoEL._AC_SL1500_.jpg',
      affiliate_url: 'https://www.amazon.com/dp/B0CHWRXH8B?linkCode=ll1&tag=pillepues-20&language=es_US&ref_=as_li_ss_tl',
      web_deal_url: 'https://vitrina-colombia-ofertas.vercel.app/?asin=B0CHWRXH8B',
      is_historic_low: true,
      status: 'ACTIVE'
    },
    {
      asin: 'B0B9C4DKKG',
      title: 'Samsung 990 PRO SSD NVMe M.2 PCIe Gen4 de 2TB (7450 MB/s)',
      category: 'Tecnología',
      price_usd: 149.99,
      original_price_usd: 249.99,
      avg_90d_usd: 189.99,
      lowest_90d_usd: 149.99,
      discount_pct: 40,
      tax_free_colombia: true,
      free_shipping_co: true,
      shipping_cost_usd: 0.0,
      requires_locker: false,
      estimated_tax_usd: 0.0,
      image_url: 'https://m.media-amazon.com/images/I/71K6m2A+WJL._AC_SL1500_.jpg',
      affiliate_url: 'https://www.amazon.com/dp/B0B9C4DKKG?linkCode=ll1&tag=pillepues-20&language=es_US&ref_=as_li_ss_tl',
      web_deal_url: 'https://vitrina-colombia-ofertas.vercel.app/?asin=B0B9C4DKKG',
      is_historic_low: true,
      status: 'ACTIVE'
    },
    {
      asin: 'B0863FR3S9',
      title: 'Sony WH-1000XM4 Audífonos Inalámbricos Noise Cancelling con Batería 30h',
      category: 'Audio',
      price_usd: 198.00,
      original_price_usd: 348.00,
      avg_90d_usd: 248.00,
      lowest_90d_usd: 198.00,
      discount_pct: 43,
      tax_free_colombia: true,
      free_shipping_co: true,
      shipping_cost_usd: 0.0,
      requires_locker: false,
      estimated_tax_usd: 0.0,
      image_url: 'https://m.media-amazon.com/images/I/71o8Q5XJS5L._AC_SL1500_.jpg',
      affiliate_url: 'https://www.amazon.com/dp/B0863FR3S9?linkCode=ll1&tag=pillepues-20&language=es_US&ref_=as_li_ss_tl',
      web_deal_url: 'https://vitrina-colombia-ofertas.vercel.app/?asin=B0863FR3S9',
      is_historic_low: true,
      status: 'ACTIVE'
    },
    {
      asin: 'B07GBZ4Q68',
      title: 'Logitech G502 HERO Mouse Gamer Sensor HERO 25K (25,600 DPI)',
      category: 'Gaming',
      price_usd: 34.99,
      original_price_usd: 79.99,
      avg_90d_usd: 49.99,
      lowest_90d_usd: 34.99,
      discount_pct: 56,
      tax_free_colombia: true,
      free_shipping_co: false,
      shipping_cost_usd: 11.95,
      requires_locker: false,
      estimated_tax_usd: 0.0,
      image_url: 'https://m.media-amazon.com/images/I/61mpMH5TzkL._AC_SL1500_.jpg',
      affiliate_url: 'https://www.amazon.com/dp/B07GBZ4Q68?linkCode=ll1&tag=pillepues-20&language=es_US&ref_=as_li_ss_tl',
      web_deal_url: 'https://vitrina-colombia-ofertas.vercel.app/?asin=B07GBZ4Q68',
      is_historic_low: true,
      status: 'ACTIVE'
    }
  ];

  // Estado reactivo de la aplicación
  const state = {
    deals: [],
    outboxCards: [],
    trmCop: DEFAULT_TRM,
    officialTrmCop: DEFAULT_TRM,
    activeFilterPill: 'all', // 'all' | 'dian' | 'shipping' | 'historic'
    selectedCategory: 'ALL',
    searchQuery: '',
    sortBy: 'discount_desc',
    selectedPreviewAsin: null,
    activeModalAsin: null
  };

  // Referencias al DOM
  const dom = {
    dealsGrid: document.getElementById('deals-grid'),
    resultsCounter: document.getElementById('results-counter'),
    trmInput: document.getElementById('trm-input'),
    btnResetTrm: document.getElementById('btn-reset-trm'),
    btnRunScan: document.getElementById('btn-run-scan'),
    btnScanLabel: document.getElementById('btn-scan-label'),
    lastSyncTimestamp: document.getElementById('last-sync-timestamp'),
    searchInput: document.getElementById('search-input'),
    btnClearSearch: document.getElementById('btn-clear-search'),
    categoryFilter: document.getElementById('category-filter'),
    sortFilter: document.getElementById('sort-filter'),
    filterPills: document.querySelectorAll('.filter-pill'),
    previewDealSelect: document.getElementById('preview-deal-select'),
    tgPreviewImg: document.getElementById('tg-preview-img'),
    tgPreviewCaption: document.getElementById('tg-preview-caption'),
    tgPreviewButtons: document.getElementById('tg-preview-buttons'),
    btnCopyTelegram: document.getElementById('btn-copy-telegram'),
    dealModal: document.getElementById('deal-modal'),
    btnCloseModal: document.getElementById('btn-close-modal'),
    modalDealAsin: document.getElementById('modal-deal-asin'),
    modalDealCategory: document.getElementById('modal-deal-category'),
    modalDealStatus: document.getElementById('modal-deal-status'),
    modalDealImage: document.getElementById('modal-deal-image'),
    modalDealBadges: document.getElementById('modal-deal-badges'),
    modalDealTitle: document.getElementById('modal-deal-title'),
    modalPriceFob: document.getElementById('modal-price-fob'),
    modalPriceList: document.getElementById('modal-price-list'),
    modalLockerCo: document.getElementById('modal-locker-co'),
    modalShippingCo: document.getElementById('modal-shipping-co'),
    modalTaxDian: document.getElementById('modal-tax-dian'),
    modalTrmLabel: document.getElementById('modal-trm-label'),
    modalTotalCop: document.getElementById('modal-total-cop'),
    modalAmazonCta: document.getElementById('modal-amazon-cta'),
    btnModalCopyLink: document.getElementById('btn-modal-copy-link'),
    btnModalShareUrl: document.getElementById('btn-modal-share-url'),
    toast: document.getElementById('toast-notification')
  };

  /* ========================================================================
     Utilidades de Formato (USD / COP / Categorías)
     ======================================================================== */

  function formatUSD(amount) {
    const val = Number(amount) || 0;
    return `$${val.toFixed(2)} USD`;
  }

  function formatCOP(usdAmount, trm = state.trmCop) {
    const copValue = Math.round((Number(usdAmount) || 0) * (Number(trm) || DEFAULT_TRM));
    return `$${copValue.toLocaleString('es-CO')} COP`;
  }

  function normalizeCategory(rawCategory = '', title = '') {
    const text = `${rawCategory} ${title}`.toLowerCase();
    if (text.includes('gaming') || text.includes('gamer') || text.includes('ryzen') || text.includes('geforce') || text.includes('playstation') || text.includes('xbox') || text.includes('nintendo')) {
      return 'Gaming';
    }
    if (text.includes('audio') || text.includes('airpods') || text.includes('audifono') || text.includes('audéfono') || text.includes('sony wh') || text.includes('parlante') || text.includes('headphone') || text.includes('earbuds')) {
      return 'Audio';
    }
    if (text.includes('hogar') || text.includes('cocina') || text.includes('aspiradora') || text.includes('cafetera') || text.includes('ninja') || text.includes('philips') || text.includes('home')) {
      return 'Hogar';
    }
    if (['Tecnología', 'Gaming', 'Audio', 'Hogar'].includes(rawCategory)) {
      return rawCategory;
    }
    return 'Tecnología';
  }

  function buildFallbackSvg(asin, title, category) {
    const safeTitle = String(title || asin).replace(/[<>&"]/g, '').slice(0, 32);
    const safeCat = String(category || 'Amazon').replace(/[<>&"]/g, '').toUpperCase();
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 420" width="600" height="420"><rect width="600" height="420" rx="20" fill="#0F172A"/><text x="300" y="175" font-family="sans-serif" font-size="22" font-weight="700" fill="#FF9900" text-anchor="middle">${safeCat}</text><text x="300" y="220" font-family="sans-serif" font-size="24" font-weight="800" fill="#FFFFFF" text-anchor="middle">${safeTitle}</text><text x="300" y="260" font-family="monospace" font-size="16" fill="#94A3B8" text-anchor="middle">ASIN: ${asin}</text></svg>`;
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
  }

  function normalizeDeal(raw) {
    const asin = String(raw.asin || raw.id || 'B000000000').trim();
    const priceUsd = Number(
      raw.price_usd ?? raw.current_price ?? raw.deal_price_usd ?? raw.price ?? 0
    );
    const avg90dUsd = Number(
      raw.avg_90d_usd ?? raw.avg_90d_price ?? raw.reference_price_usd ?? raw.list_price_usd ?? priceUsd
    );
    const originalPriceUsd = Number(
      raw.reference_price_usd ?? raw.original_price_usd ?? raw.list_price_usd ?? raw.list_price ?? avg90dUsd
    );
    const discountPct = Math.round(
      Number(
        raw.discount_pct ??
        raw.discount_percent ??
        (originalPriceUsd > priceUsd
          ? ((originalPriceUsd - priceUsd) / originalPriceUsd) * 100
          : 0)
      )
    );

    const taxFreeColombia =
      typeof raw.tax_free_colombia === 'boolean'
        ? raw.tax_free_colombia
        : typeof raw.tax_free_co === 'boolean'
        ? raw.tax_free_co
        : priceUsd <= 200.0;

    const shipsToColombia =
      typeof raw.ships_to_colombia === 'boolean' ? raw.ships_to_colombia : true;

    const requiresLocker =
      typeof raw.requires_locker === 'boolean' ? raw.requires_locker : !shipsToColombia;

    const freeShippingCo =
      !requiresLocker &&
      (typeof raw.free_shipping_co === 'boolean'
        ? raw.free_shipping_co
        : priceUsd >= 35.0);

    const shippingUsd = Number(
      raw.shipping_cost_usd ?? raw.shipping_usd ?? (freeShippingCo ? 0 : requiresLocker ? 8.5 : 11.95)
    );
    const estimatedTaxUsd = Number(
      raw.estimated_import_tax_usd ?? raw.estimated_tax_usd ?? (taxFreeColombia ? 0 : +(priceUsd * 0.19).toFixed(2))
    );

    const cheaperThanBefore =
      typeof raw.cheaper_than_before === 'boolean'
        ? raw.cheaper_than_before
        : avg90dUsd > priceUsd;

    const vsAvg90dPct =
      raw.vs_avg_90d_pct !== undefined
        ? Number(raw.vs_avg_90d_pct)
        : avg90dUsd > priceUsd
        ? Math.round(((avg90dUsd - priceUsd) / avg90dUsd) * 100)
        : 0;

    const rawAffUrl = raw.affiliate_url || raw.amazon_url || '';
    const affiliateUrl =
      rawAffUrl && rawAffUrl.includes('linkCode=') && rawAffUrl.includes('tag=')
        ? rawAffUrl
        : `https://www.amazon.com/dp/${asin}?linkCode=ll1&tag=${DEFAULT_TAG}&language=es_US&ref_=as_li_ss_tl`;

    const webDealUrl =
      raw.web_deal_url ||
      raw.web_url ||
      `${window.location.origin}${window.location.pathname}?asin=${encodeURIComponent(asin)}`;

    const category = normalizeCategory(raw.category, raw.title);
    const upgradedImageUrl = (raw.image_url || '').replace(
      /(\/images\/I\/[^/.]+)\._[^/]+_\.(jpg|jpeg|png|webp)$/i,
      '$1._AC_SL1200_.$2'
    );

    return {
      asin,
      title: raw.title || `Producto Amazon.com (${asin})`,
      category,
      price_usd: priceUsd,
      original_price_usd: originalPriceUsd,
      avg_90d_usd: avg90dUsd,
      lowest_90d_usd: Number(raw.lowest_90d_usd ?? raw.lowest_90d_price ?? priceUsd),
      discount_pct: discountPct,
      cheaper_than_before: cheaperThanBefore,
      vs_avg_90d_pct: vsAvg90dPct,
      tax_free_colombia: taxFreeColombia,
      ships_to_colombia: shipsToColombia,
      requires_locker: requiresLocker,
      free_shipping_co: freeShippingCo,
      shipping_usd: shippingUsd,
      estimated_tax_usd: estimatedTaxUsd,
      image_url: upgradedImageUrl || buildFallbackSvg(asin, raw.title, category),
      fallback_image_url: buildFallbackSvg(asin, raw.title, category),
      affiliate_url: affiliateUrl,
      web_deal_url: webDealUrl,
      is_historic_low: Boolean(raw.is_historic_low ?? discountPct >= 35),
      status: raw.status || 'ACTIVE'
    };
  }

  function showToast(message) {
    if (!dom.toast) return;
    dom.toast.textContent = message;
    dom.toast.classList.add('visible');
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => {
      dom.toast.classList.remove('visible');
    }, 3200);
  }

  async function copyToClipboard(text, label = 'Texto copiado al portapapeles') {
    try {
      await navigator.clipboard.writeText(text);
      showToast(`✅ ${label}`);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      showToast(`✅ ${label}`);
    }
  }

  /* ========================================================================
     Carga de Datos (FastAPI /api/* con Fallback Automático a /data/*.json)
     ======================================================================== */

  async function fetchJsonWithFallback(urls) {
    for (const url of urls) {
      try {
        const res = await fetch(url, { cache: 'no-store' });
        if (res.ok) {
          return await res.json();
        }
      } catch {
        // Intenta el siguiente endpoint estático
      }
    }
    return null;
  }

  async function loadCatalogAndPreviews() {
    const dealsPayload = await fetchJsonWithFallback([
      './data/deals.json',
      '/api/deals',
      '/data/deals.json'
    ]);

    let rawDeals = [];
    if (Array.isArray(dealsPayload)) {
      rawDeals = dealsPayload;
    } else if (dealsPayload && Array.isArray(dealsPayload.deals)) {
      rawDeals = dealsPayload.deals;
      if (dealsPayload.trm_cop || (dealsPayload.metadata && dealsPayload.metadata.trm_cop)) {
        const serverTrm = Number(dealsPayload.trm_cop || dealsPayload.metadata.trm_cop);
        if (serverTrm > 2000) {
          state.trmCop = serverTrm;
          state.officialTrmCop = serverTrm;
          if (dom.trmInput) dom.trmInput.value = String(serverTrm);
        }
      }
    }

    if (!rawDeals.length) {
      rawDeals = FALLBACK_DEALS;
    }

    state.deals = rawDeals.map(normalizeDeal);

    const previewsPayload = await fetchJsonWithFallback([
      './data/outbox_cards.json',
      '/api/previews',
      '/data/outbox_cards.json'
    ]);

    if (Array.isArray(previewsPayload)) {
      state.outboxCards = previewsPayload;
    } else if (previewsPayload && Array.isArray(previewsPayload.cards)) {
      state.outboxCards = previewsPayload.cards;
    } else if (previewsPayload && Array.isArray(previewsPayload.items)) {
      state.outboxCards = previewsPayload.items;
    } else {
      state.outboxCards = [];
    }

    const nowStr = new Date().toLocaleTimeString('es-CO', {
      hour: '2-digit',
      minute: '2-digit'
    });
    if (dom.lastSyncTimestamp) {
      dom.lastSyncTimestamp.textContent = `${state.deals.length} ofertas verificadas · Sync ${nowStr}`;
    }

    populatePreviewSelect();
    renderCatalog();
    renderChannelSimulator();
    checkDeepLinkAsin();
  }

  /* ========================================================================
     Filtrado y Renderizado del Catálogo
     ======================================================================== */

  function getFilteredDeals() {
    const q = state.searchQuery.trim().toLowerCase();

    const filtered = state.deals.filter((deal) => {
      // Filtro por píldoras rápidas de Colombia
      if (state.activeFilterPill === 'dian' && deal.tax_free_colombia !== true) {
        return false;
      }
      if (
        state.activeFilterPill === 'shipping' &&
        !(deal.free_shipping_co === true && deal.price_usd >= 35)
      ) {
        return false;
      }
      if (state.activeFilterPill === 'historic' && !(deal.discount_pct >= 35)) {
        return false;
      }

      // Filtro por categoría
      if (state.selectedCategory !== 'ALL' && deal.category !== state.selectedCategory) {
        return false;
      }

      // Filtro por texto / ASIN
      if (q) {
        const haystack = `${deal.title} ${deal.asin} ${deal.category}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }

      return true;
    });

    // Ordenamiento
    filtered.sort((a, b) => {
      if (state.sortBy === 'price_asc') {
        return a.price_usd - b.price_usd;
      }
      if (state.sortBy === 'savings_desc') {
        return (b.original_price_usd - b.price_usd) - (a.original_price_usd - a.price_usd);
      }
      return b.discount_pct - a.discount_pct;
    });

    return filtered;
  }

  function renderCatalog() {
    if (!dom.dealsGrid) return;
    const filtered = getFilteredDeals();

    if (dom.resultsCounter) {
      dom.resultsCounter.textContent = `Mostrando ${filtered.length} de ${state.deals.length} ofertas en Colombia`;
    }

    if (!filtered.length) {
      dom.dealsGrid.innerHTML = `
        <div class="empty-catalog-state">
          <h3>No encontramos ofertas con estos filtros</h3>
          <p>Prueba restableciendo los filtros aduaneros o buscando otro término/ASIN.</p>
          <button type="button" class="btn-scan-zero-token" id="btn-reset-all-filters">
            Restablecer todos los filtros
          </button>
        </div>
      `;
      const resetBtn = document.getElementById('btn-reset-all-filters');
      if (resetBtn) {
        resetBtn.addEventListener('click', resetAllFilters);
      }
      return;
    }

    dom.dealsGrid.innerHTML = filtered
      .map((deal) => {
        const totalUsd = deal.price_usd + deal.shipping_usd + deal.estimated_tax_usd;
        const priceCopFormatted = formatCOP(deal.price_usd, state.trmCop);
        const totalCopFormatted = formatCOP(totalUsd, state.trmCop);
        const savingsUsd = Math.max(0, deal.original_price_usd - deal.price_usd).toFixed(2);

        const dianBadge = deal.tax_free_colombia
          ? `<span class="co-pill co-pill-tax-free" title="Exento de IVA 19% y Arancel en Colombia (<= $200 USD)">🟢 Sin Impuestos DIAN ≤$200</span>`
          : `<span class="co-pill co-pill-taxed" title="Supera $200 USD: incluye estimado de importación">⚠️ +$200 USD (Imp. +$${deal.estimated_tax_usd.toFixed(2)})</span>`;

        const shippingBadge =
          !deal.requires_locker && deal.shipping_usd === 0
            ? `<span class="co-pill co-pill-shipping">🇨🇴 Envío Gratis ($0)</span>`
            : `<span class="co-pill">✈️ Envío +$${deal.shipping_usd.toFixed(2)} USD</span>`;

        const lockerBadge = deal.requires_locker
          ? `<span class="co-pill co-pill-taxed">📦 Necesita casillero: Sí (Miami)</span>`
          : `<span class="co-pill co-pill-tax-free">✅ Casillero: No (Directo)</span>`;

        const cheaperBadge = deal.cheaper_than_before
          ? `<span class="co-pill co-pill-historic">📉 ${deal.vs_avg_90d_pct || deal.discount_pct}% más barato que antes</span>`
          : '';

        return `
          <article class="deal-card" role="listitem" data-asin="${deal.asin}">
            <div class="deal-card-media">
              <div class="deal-badges-top">
                <span class="badge-discount">-${deal.discount_pct}% OFF</span>
                <span class="badge-category">${deal.category}</span>
              </div>
              <img
                src="${deal.image_url}"
                alt="${deal.title.replace(/"/g, '&quot;')}"
                loading="lazy"
                onerror="this.onerror=null;this.src='${deal.fallback_image_url}';"
              />
              <span class="badge-asin-overlay">ASIN: ${deal.asin}</span>
            </div>

            <div class="deal-card-body">
              <div class="colombia-badges-row">
                ${dianBadge}
                ${shippingBadge}
                ${lockerBadge}
                ${cheaperBadge}
              </div>

              <h3 class="deal-title" data-open-modal="${deal.asin}" title="Ver desglose aduanero DIAN completo">
                ${deal.title}
              </h3>

              <div class="deal-pricing-box">
                <div class="price-primary-row">
                  <div>
                    <span class="price-usd">${formatUSD(deal.price_usd)}</span>
                    <span class="price-original-usd">$${deal.original_price_usd.toFixed(2)}</span>
                  </div>
                  <span class="price-cop-badge">~${priceCopFormatted}</span>
                </div>
                <div class="price-meta-row">
                  <span>Ahorras: <strong>$${savingsUsd} USD</strong></span>
                  <span class="mono">Prom. 90d: $${deal.avg_90d_usd.toFixed(2)}</span>
                </div>
                <div class="price-meta-row">
                  <span>Total puesto en CO:</span>
                  <strong class="mono">~${totalCopFormatted}</strong>
                </div>
              </div>

              <div class="deal-card-actions">
                <a
                  href="${deal.affiliate_url}"
                  target="_blank"
                  rel="nofollow sponsored noopener"
                  class="btn-amazon-cta"
                >
                  <span>🛒 Ver Oferta en Amazon.com</span>
                </a>
                <div class="deal-secondary-actions">
                  <button
                    type="button"
                    class="btn-card-secondary"
                    data-open-modal="${deal.asin}"
                  >
                    🔍 Aduana DIAN (?asin)
                  </button>
                  <button
                    type="button"
                    class="btn-card-secondary"
                    data-preview-channel="${deal.asin}"
                  >
                    ✈️ Ver en Telegram
                  </button>
                </div>
              </div>
            </div>
          </article>
        `;
      })
      .join('');
  }

  function resetAllFilters() {
    state.activeFilterPill = 'all';
    state.selectedCategory = 'ALL';
    state.searchQuery = '';
    if (dom.searchInput) dom.searchInput.value = '';
    if (dom.btnClearSearch) dom.btnClearSearch.hidden = true;
    if (dom.categoryFilter) dom.categoryFilter.value = 'ALL';
    dom.filterPills.forEach((pill) => {
      pill.classList.toggle('active', pill.dataset.filter === 'all');
    });
    renderCatalog();
  }

  /* ========================================================================
     Simulador en Vivo: Telegram & Microsoft Teams (Adaptive Cards)
     ======================================================================== */

  function populatePreviewSelect() {
    if (!dom.previewDealSelect) return;
    dom.previewDealSelect.innerHTML = state.deals
      .map(
        (deal) =>
          `<option value="${deal.asin}">[${deal.asin}] -${deal.discount_pct}% · ${deal.title.slice(0, 48)}...</option>`
      )
      .join('');

    if (!state.selectedPreviewAsin && state.deals.length > 0) {
      state.selectedPreviewAsin = state.deals[0].asin;
    }
    if (state.selectedPreviewAsin) {
      dom.previewDealSelect.value = state.selectedPreviewAsin;
    }
  }

  function buildChannelPayloadsForDeal(deal) {
    const matchedCard = state.outboxCards.find(
      (c) => (c.asin || c.deal_asin) === deal.asin
    );

    const totalCop = formatCOP(
      deal.price_usd + deal.shipping_usd + deal.estimated_tax_usd,
      state.trmCop
    );
    const dianLine = deal.tax_free_colombia
      ? '🟢 <b>SIN IMPUESTOS DIAN</b> (≤ $200 USD · 0% IVA/Arancel)'
      : `⚠️ Impuesto DIAN estimado: $${deal.estimated_tax_usd.toFixed(2)} USD`;
    const shipLine =
      deal.free_shipping_co && deal.price_usd >= 35
        ? '🚚 <b>Envío a Colombia:</b> GRATIS ($0.00 USD)'
        : `🚚 <b>Envío a Colombia:</b> +$${deal.shipping_usd.toFixed(2)} USD (~${formatCOP(deal.shipping_usd, state.trmCop)})`;
    const lockerLine = deal.requires_locker
      ? '📬 <b>Casillero:</b> Sí — Requiere casillero en Miami'
      : '📬 <b>Casillero:</b> No — Envío directo a Colombia';
    const avg90 = deal.avg_90d_usd || deal.original_price_usd;
    const cheaperLine = deal.cheaper_than_before
      ? `📉 <b>Más barato que antes:</b> Prom. 90d $${avg90.toFixed(2)} → Hoy <b>-${deal.discount_pct}% OFF</b>`
      : `📊 Precio Lista: $${deal.original_price_usd.toFixed(2)} USD (-${deal.discount_pct}% OFF)`;

    const telegramCaptionHtml =
      (matchedCard &&
        ((matchedCard.telegram_card && matchedCard.telegram_card.caption_html) ||
          (matchedCard.telegram &&
            matchedCard.telegram.payload &&
            matchedCard.telegram.payload.caption) ||
          matchedCard.telegram_caption ||
          matchedCard.telegram_html)) ||
      [
        `🔥 <b>OFERTA VERIFICADA AMAZON (-${deal.discount_pct}% OFF)</b>`,
        ``,
        `📦 <b>${deal.title}</b>`,
        ``,
        `💵 <b>Precio Hoy:</b> $${deal.price_usd.toFixed(2)} USD (~${formatCOP(deal.price_usd, state.trmCop)})`,
        `${cheaperLine}`,
        `🇨🇴 <b>Total estimado CO:</b> ~${totalCop} (TRM $${state.trmCop.toLocaleString('es-CO')})`,
        `${dianLine}`,
        `${shipLine}`,
        `${lockerLine}`,
        ``,
        `🔗 Comprar aquí: ${deal.affiliate_url}`
      ].join('\n');

    return {
      telegramCaptionHtml
    };
  }

  function renderChannelSimulator() {
    const deal =
      state.deals.find((d) => d.asin === state.selectedPreviewAsin) ||
      state.deals[0];
    if (!deal) return;

    const { telegramCaptionHtml } = buildChannelPayloadsForDeal(deal);
    const totalCop = formatCOP(
      deal.price_usd + deal.shipping_usd + deal.estimated_tax_usd,
      state.trmCop
    );
    const fallbackImg = buildFallbackSvg(deal.asin, deal.category);

    // Actualizar Vista Telegram
    if (dom.tgPreviewImg) {
      dom.tgPreviewImg.onerror = () => {
        dom.tgPreviewImg.onerror = null;
        dom.tgPreviewImg.src = fallbackImg;
      };
      dom.tgPreviewImg.src = deal.image_url || fallbackImg;
      dom.tgPreviewImg.alt = deal.title;
    }
    if (dom.tgPreviewCaption) {
      dom.tgPreviewCaption.innerHTML = telegramCaptionHtml;
    }
    if (dom.tgPreviewButtons) {
      dom.tgPreviewButtons.innerHTML = `
        <a
          href="${deal.affiliate_url}"
          target="_blank"
          rel="nofollow sponsored noopener"
          class="tg-inline-btn"
        >
          🛒 Comprar en Amazon ($${deal.price_usd.toFixed(2)} USD)
        </a>
        <a
          href="?asin=${encodeURIComponent(deal.asin)}"
          data-open-modal="${deal.asin}"
          class="tg-inline-btn"
        >
          🇨🇴 Desglose DIAN en Vitrina Web (~${totalCop})
        </a>
      `;
    }

    // Guardar payload actual para copiado en un clic
    state.currentTelegramText = telegramCaptionHtml.replace(/<[^>]+>/g, '');
  }

  /* ========================================================================
     Modal de Análisis Aduanero Profundo (?asin=B0...)
     ======================================================================== */

  function openDealModal(asin, updateHistory = true) {
    const deal = state.deals.find(
      (d) => d.asin.toUpperCase() === String(asin).toUpperCase()
    );
    if (!deal || !dom.dealModal) return;

    state.activeModalAsin = deal.asin;

    const totalUsd = deal.price_usd + deal.shipping_usd + deal.estimated_tax_usd;
    const totalCop = formatCOP(totalUsd, state.trmCop);
    const fallbackImg = buildFallbackSvg(deal.asin, deal.category);
    const avg90 = deal.avg_90d_usd || deal.original_price_usd;

    dom.modalDealAsin.textContent = `ASIN: ${deal.asin}`;
    dom.modalDealCategory.textContent = deal.category;
    dom.modalDealStatus.textContent = deal.cheaper_than_before
      ? `📉 Más barato que antes (-${deal.discount_pct}% OFF)`
      : `Descuento real -${deal.discount_pct}% OFF`;
    dom.modalDealImage.onerror = () => {
      dom.modalDealImage.onerror = null;
      dom.modalDealImage.src = fallbackImg;
    };
    dom.modalDealImage.src = deal.image_url || fallbackImg;
    dom.modalDealImage.alt = deal.title;
    dom.modalDealTitle.textContent = deal.title;

    dom.modalDealBadges.innerHTML = `
      ${
        deal.tax_free_colombia
          ? `<span class="co-pill co-pill-tax-free">🟢 Libre de Impuestos DIAN (≤$200 USD)</span>`
          : `<span class="co-pill co-pill-taxed">⚠️ Sujeto a IVA/Arancel (+$200 USD)</span>`
      }
      ${
        deal.free_shipping_co && deal.price_usd >= 35
          ? `<span class="co-pill co-pill-shipping">🚚 Envío Gratis a Colombia</span>`
          : `<span class="co-pill co-pill-shipping">🚚 Envío +$${deal.shipping_usd.toFixed(2)} USD</span>`
      }
      <span class="co-pill ${deal.requires_locker ? 'co-pill-taxed' : 'co-pill-tax-free'}">
        ${deal.requires_locker ? '📬 Casillero: Sí (Miami)' : '📬 Casillero: No (Directo)'}
      </span>
    `;

    dom.modalPriceFob.textContent = `${formatUSD(deal.price_usd)} (~${formatCOP(deal.price_usd, state.trmCop)})`;
    dom.modalPriceList.textContent = `${formatUSD(avg90)} (-${deal.discount_pct}% OFF${deal.cheaper_than_before ? ' · Más barato que antes' : ''})`;
    dom.modalShippingCo.textContent =
      deal.free_shipping_co && deal.price_usd >= 35
        ? 'GRATIS a Colombia ($0.00 USD)'
        : `+${formatUSD(deal.shipping_usd)} (~${formatCOP(deal.shipping_usd, state.trmCop)})`;
    if (dom.modalLockerCo) {
      dom.modalLockerCo.textContent = deal.requires_locker
        ? 'Sí — Requiere casillero en Miami'
        : 'No — Envío directo a Colombia';
    }
    dom.modalTaxDian.textContent = deal.tax_free_colombia
      ? '$0.00 USD (0% Exento por ley DIAN ≤ $200 USD)'
      : `${formatUSD(deal.estimated_tax_usd)} (IVA 19% + Arancel)`;
    dom.modalTrmLabel.textContent = state.trmCop.toLocaleString('es-CO');
    dom.modalTotalCop.textContent = `${totalCop} (${formatUSD(totalUsd)})`;

    dom.modalAmazonCta.href = deal.affiliate_url;

    dom.dealModal.classList.add('open');
    dom.dealModal.setAttribute('aria-hidden', 'false');

    if (updateHistory) {
      const nextUrl = `${window.location.pathname}?asin=${encodeURIComponent(deal.asin)}`;
      window.history.replaceState({ asin: deal.asin }, '', nextUrl);
    }
  }

  function closeDealModal() {
    if (!dom.dealModal) return;
    dom.dealModal.classList.remove('open');
    dom.dealModal.setAttribute('aria-hidden', 'true');
    state.activeModalAsin = null;

    if (window.location.search.includes('asin=')) {
      window.history.replaceState({}, '', window.location.pathname);
    }
  }

  function checkDeepLinkAsin() {
    const params = new URLSearchParams(window.location.search);
    const asinParam = params.get('asin');
    if (asinParam) {
      openDealModal(asinParam, false);
    }
  }

  /* ========================================================================
     Barrido Bajo Demanda (POST /api/scan o Recarga Estática)
     ======================================================================== */

  async function triggerZeroTokenScan() {
    if (!dom.btnRunScan) return;
    dom.btnRunScan.disabled = true;
    if (dom.btnScanLabel) {
      dom.btnScanLabel.textContent = 'Ejecutando Barrido SQLite...';
    }

    try {
      let scannedViaApi = false;
      try {
        const res = await fetch('/api/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        if (res.ok) {
          scannedViaApi = true;
        }
      } catch {
        // Modo 100% estático en Vercel CDN
      }

      await loadCatalogAndPreviews();
      showToast(
        scannedViaApi
          ? '⚡ Barrido Zero-Token completado (0 tokens LLM consumidos)'
          : '⚡ Catálogo sincronizado desde el snapshot de ofertas en Vercel CDN'
      );
    } finally {
      dom.btnRunScan.disabled = false;
      if (dom.btnScanLabel) {
        dom.btnScanLabel.textContent = 'Ejecutar Barrido Zero-Token';
      }
    }
  }

  /* ========================================================================
     Eventos e Interactividad
     ======================================================================== */

  function bindEvents() {
    // Conversor TRM en tiempo real
    if (dom.trmInput) {
      dom.trmInput.addEventListener('input', (e) => {
        const val = Number(e.target.value);
        if (val >= 1000 && val <= 15000) {
          state.trmCop = val;
          renderCatalog();
          renderChannelSimulator();
          if (state.activeModalAsin) {
            openDealModal(state.activeModalAsin, false);
          }
        }
      });
    }

    if (dom.btnResetTrm) {
      dom.btnResetTrm.addEventListener('click', () => {
        state.trmCop = state.officialTrmCop;
        if (dom.trmInput) dom.trmInput.value = String(state.officialTrmCop);
        renderCatalog();
        renderChannelSimulator();
        if (state.activeModalAsin) {
          openDealModal(state.activeModalAsin, false);
        }
        showToast(`🇨🇴 TRM restaurada a $${state.officialTrmCop.toLocaleString('es-CO')} COP`);
      });
    }

    // Botón Barrido Zero-Token
    if (dom.btnRunScan) {
      dom.btnRunScan.addEventListener('click', triggerZeroTokenScan);
    }

    // Píldoras de filtro rápido
    dom.filterPills.forEach((pill) => {
      pill.addEventListener('click', () => {
        state.activeFilterPill = pill.dataset.filter || 'all';
        dom.filterPills.forEach((p) => p.classList.toggle('active', p === pill));
        renderCatalog();
      });
    });

    // Filtro por categoría
    if (dom.categoryFilter) {
      dom.categoryFilter.addEventListener('change', (e) => {
        state.selectedCategory = e.target.value;
        renderCatalog();
      });
    }

    // Ordenamiento
    if (dom.sortFilter) {
      dom.sortFilter.addEventListener('change', (e) => {
        state.sortBy = e.target.value;
        renderCatalog();
      });
    }

    // Búsqueda instantánea por texto o ASIN
    if (dom.searchInput) {
      dom.searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value;
        if (dom.btnClearSearch) {
          dom.btnClearSearch.hidden = !state.searchQuery.length;
        }
        renderCatalog();
      });
    }

    if (dom.btnClearSearch) {
      dom.btnClearSearch.addEventListener('click', () => {
        state.searchQuery = '';
        if (dom.searchInput) dom.searchInput.value = '';
        dom.btnClearSearch.hidden = true;
        renderCatalog();
      });
    }

    // Delegación de eventos en tarjetas y simulador
    document.addEventListener('click', (e) => {
      const modalTrigger = e.target.closest('[data-open-modal]');
      if (modalTrigger) {
        e.preventDefault();
        openDealModal(modalTrigger.getAttribute('data-open-modal'), true);
        return;
      }

      const previewTrigger = e.target.closest('[data-preview-channel]');
      if (previewTrigger) {
        e.preventDefault();
        const asin = previewTrigger.getAttribute('data-preview-channel');
        state.selectedPreviewAsin = asin;
        if (dom.previewDealSelect) {
          dom.previewDealSelect.value = asin;
        }
        renderChannelSimulator();
        const section = document.getElementById('channels-preview');
        if (section) {
          section.scrollIntoView({ behavior: 'smooth' });
        }
      }
    });

    // Selector del previsualizador de canales
    if (dom.previewDealSelect) {
      dom.previewDealSelect.addEventListener('change', (e) => {
        state.selectedPreviewAsin = e.target.value;
        renderChannelSimulator();
      });
    }

    // Copiar payload de Telegram
    if (dom.btnCopyTelegram) {
      dom.btnCopyTelegram.addEventListener('click', () => {
        copyToClipboard(
          state.currentTelegramText || '',
          'Copy de Telegram copiado con link de afiliado'
        );
      });
    }

    // Acciones del modal
    if (dom.btnCloseModal) {
      dom.btnCloseModal.addEventListener('click', closeDealModal);
    }

    if (dom.dealModal) {
      dom.dealModal.addEventListener('click', (e) => {
        if (e.target === dom.dealModal) closeDealModal();
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && state.activeModalAsin) {
        closeDealModal();
      }
    });

    if (dom.btnModalCopyLink) {
      dom.btnModalCopyLink.addEventListener('click', () => {
        const deal = state.deals.find((d) => d.asin === state.activeModalAsin);
        if (deal) {
          copyToClipboard(deal.affiliate_url, `Link de afiliado (${deal.asin}) copiado`);
        }
      });
    }

    if (dom.btnModalShareUrl) {
      dom.btnModalShareUrl.addEventListener('click', () => {
        if (state.activeModalAsin) {
          const deepUrl = `${window.location.origin}${window.location.pathname}?asin=${encodeURIComponent(state.activeModalAsin)}`;
          copyToClipboard(deepUrl, `URL profunda (?asin=${state.activeModalAsin}) copiada`);
        }
      });
    }
  }

  // Inicialización
  document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    loadCatalogAndPreviews();
  });
})();

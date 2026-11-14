/**
 * Vitrina Colombia — Portal Web de Afiliados Amazon.com (Zero-Token Architecture)
 * Compatible con FastAPI (/api/deals, /api/previews, POST /api/scan)
 * y despliegue 100% estático en Vercel CDN (/data/deals.json, /data/outbox_cards.json).
 */

(() => {
  'use strict';

  const DEFAULT_TRM = 4150;
  const DEFAULT_TAG = 'colombiaofertas-20';

  // Respaldo inicial por si aún no se ha corrido el pipeline local
  const FALLBACK_DEALS = [
    {
      asin: 'B09V3KXJPB',
      title: 'Apple AirPods Pro (2.ª Generación) con Estuche MagSafe USB-C',
      category: 'Audio',
      price_usd: 169.99,
      original_price_usd: 249.00,
      avg_90d_usd: 199.50,
      lowest_90d_usd: 169.99,
      discount_pct: 32,
      tax_free_colombia: true,
      free_shipping_co: true,
      shipping_usd: 0.0,
      estimated_tax_usd: 0.0,
      image_url: 'https://m.media-amazon.com/images/I/61SUj2aKoEL._AC_SL1500_.jpg',
      affiliate_url: 'https://www.amazon.com/dp/B09V3KXJPB?tag=colombiaofertas-20&linkCode=ll1&language=es_US',
      web_deal_url: 'https://colombia-amazon-ofertas.vercel.app/?asin=B09V3KXJPB',
      is_historic_low: true,
      status: 'ACTIVE'
    },
    {
      asin: 'B0BSHF7WHW',
      title: 'Crucial X9 Pro 2TB SSD Portátil USB 3.2 (Hasta 1050 MB/s) Resistente IP55',
      category: 'Tecnología',
      price_usd: 119.99,
      original_price_usd: 189.99,
      avg_90d_usd: 154.00,
      lowest_90d_usd: 119.99,
      discount_pct: 37,
      tax_free_colombia: true,
      free_shipping_co: true,
      shipping_usd: 0.0,
      estimated_tax_usd: 0.0,
      image_url: 'https://m.media-amazon.com/images/I/71K6m2A+WJL._AC_SL1500_.jpg',
      affiliate_url: 'https://www.amazon.com/dp/B0BSHF7WHW?tag=colombiaofertas-20&linkCode=ll1&language=es_US',
      web_deal_url: 'https://colombia-amazon-ofertas.vercel.app/?asin=B0BSHF7WHW',
      is_historic_low: true,
      status: 'ACTIVE'
    },
    {
      asin: 'B0863TXGM3',
      title: 'Sony WH-1000XM4 Audífonos Inalámbricos Noise Cancelling con Batería 30h',
      category: 'Audio',
      price_usd: 188.00,
      original_price_usd: 348.00,
      avg_90d_usd: 248.00,
      lowest_90d_usd: 188.00,
      discount_pct: 46,
      tax_free_colombia: true,
      free_shipping_co: true,
      shipping_usd: 0.0,
      estimated_tax_usd: 0.0,
      image_url: 'https://m.media-amazon.com/images/I/71o8Q5XJS5L._AC_SL1500_.jpg',
      affiliate_url: 'https://www.amazon.com/dp/B0863TXGM3?tag=colombiaofertas-20&linkCode=ll1&language=es_US',
      web_deal_url: 'https://colombia-amazon-ofertas.vercel.app/?asin=B0863TXGM3',
      is_historic_low: true,
      status: 'ACTIVE'
    },
    {
      asin: 'B0C8PSMPTH',
      title: 'AMD Ryzen 7 7800X3D Procesador Gaming 8-Core 16-Thread 3D V-Cache AM5',
      category: 'Gaming',
      price_usd: 198.50,
      original_price_usd: 329.00,
      avg_90d_usd: 289.00,
      lowest_90d_usd: 198.50,
      discount_pct: 40,
      tax_free_colombia: true,
      free_shipping_co: true,
      shipping_usd: 0.0,
      estimated_tax_usd: 0.0,
      image_url: 'https://m.media-amazon.com/images/I/61IIbwz-+ML._AC_SL1500_.jpg',
      affiliate_url: 'https://www.amazon.com/dp/B0C8PSMPTH?tag=colombiaofertas-20&linkCode=ll1&language=es_US',
      web_deal_url: 'https://colombia-amazon-ofertas.vercel.app/?asin=B0C8PSMPTH',
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
    teamsPreviewBadge: document.getElementById('teams-preview-badge'),
    teamsPreviewTitle: document.getElementById('teams-preview-title'),
    teamsPreviewImg: document.getElementById('teams-preview-img'),
    teamsPreviewFacts: document.getElementById('teams-preview-facts'),
    teamsPreviewActions: document.getElementById('teams-preview-actions'),
    btnCopyTeams: document.getElementById('btn-copy-teams'),
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

  function normalizeDeal(raw) {
    const asin = String(raw.asin || raw.id || 'B000000000').trim();
    const priceUsd = Number(
      raw.price_usd ?? raw.current_price ?? raw.deal_price_usd ?? raw.price ?? 0
    );
    const originalPriceUsd = Number(
      raw.original_price_usd ?? raw.list_price_usd ?? raw.list_price ?? raw.avg_90d_usd ?? raw.avg_90d_price ?? (priceUsd * 1.35)
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
        : typeof raw.dian_tax_free === 'boolean'
        ? raw.dian_tax_free
        : priceUsd <= 200.0;

    const freeShippingCo =
      typeof raw.free_shipping_co === 'boolean'
        ? raw.free_shipping_co
        : typeof raw.free_shipping_colombia === 'boolean'
        ? raw.free_shipping_colombia
        : priceUsd >= 35.0;

    const shippingUsd = Number(raw.shipping_usd ?? (freeShippingCo ? 0 : 12.99));
    const estimatedTaxUsd = Number(
      raw.estimated_tax_usd ?? (taxFreeColombia ? 0 : +(priceUsd * 0.29).toFixed(2))
    );

    const affiliateUrl =
      raw.affiliate_url ||
      raw.amazon_url ||
      `https://www.amazon.com/dp/${asin}?tag=${DEFAULT_TAG}&linkCode=ll1&language=es_US`;

    const webDealUrl =
      raw.web_deal_url ||
      `${window.location.origin}${window.location.pathname}?asin=${encodeURIComponent(asin)}`;

    const category = normalizeCategory(raw.category, raw.title);

    return {
      asin,
      title: raw.title || `Producto Amazon.com (${asin})`,
      category,
      price_usd: priceUsd,
      original_price_usd: originalPriceUsd,
      avg_90d_usd: Number(raw.avg_90d_usd ?? raw.avg_90d_price ?? originalPriceUsd),
      lowest_90d_usd: Number(raw.lowest_90d_usd ?? raw.lowest_90d_price ?? priceUsd),
      discount_pct: discountPct,
      tax_free_colombia: taxFreeColombia,
      free_shipping_co: freeShippingCo,
      shipping_usd: shippingUsd,
      estimated_tax_usd: estimatedTaxUsd,
      image_url:
        raw.image_url ||
        'https://m.media-amazon.com/images/I/61SUj2aKoEL._AC_SL1500_.jpg',
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
        const copFormatted = formatCOP(totalUsd, state.trmCop);
        const savingsUsd = Math.max(0, deal.original_price_usd - deal.price_usd).toFixed(2);

        const dianBadge = deal.tax_free_colombia
          ? `<span class="co-pill co-pill-tax-free" title="Exento de IVA 19% y Arancel en Colombia (<= $200 USD)">🟢 Sin Impuestos DIAN ≤$200</span>`
          : `<span class="co-pill co-pill-taxed" title="Supera $200 USD: incluye estimado de importación">⚠️ +$200 USD (Imp. +$${deal.estimated_tax_usd.toFixed(2)})</span>`;

        const shippingBadge =
          deal.free_shipping_co && deal.price_usd >= 35
            ? `<span class="co-pill co-pill-shipping">🇨🇴 Envío Gratis a CO</span>`
            : `<span class="co-pill">📦 Envío $${deal.shipping_usd.toFixed(2)} USD</span>`;

        const historicBadge =
          deal.discount_pct >= 35
            ? `<span class="co-pill co-pill-historic">🔥 Mínimo 90d</span>`
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
              />
              <span class="badge-asin-overlay">ASIN: ${deal.asin}</span>
            </div>

            <div class="deal-card-body">
              <div class="colombia-badges-row">
                ${dianBadge}
                ${shippingBadge}
                ${historicBadge}
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
                  <span class="price-cop-badge">~${copFormatted}</span>
                </div>
                <div class="price-meta-row">
                  <span>Ahorras: <strong>$${savingsUsd} USD</strong></span>
                  <span class="mono">Prom. 90d: $${deal.avg_90d_usd.toFixed(2)}</span>
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
                    📡 Ver en Telegram/Teams
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
        ? '🇨🇴 <b>Envío GRATIS a Colombia</b>'
        : `📦 Envío a Colombia: $${deal.shipping_usd.toFixed(2)} USD`;

    const telegramCaptionHtml =
      (matchedCard && (matchedCard.telegram_caption || matchedCard.telegram_html)) ||
      [
        `🔥 <b>MÍNIMO VERIFICADO (-${deal.discount_pct}% OFF)</b>`,
        ``,
        `📦 <b>${deal.title}</b>`,
        ``,
        `💵 Precio Oferta: <b>$${deal.price_usd.toFixed(2)} USD</b> (Antes: $${deal.original_price_usd.toFixed(2)})`,
        `🇨🇴 Total en Pesos: <b>~${totalCop}</b> (TRM $${state.trmCop.toLocaleString('es-CO')})`,
        `${dianLine}`,
        `${shipLine}`,
        ``,
        `🔗 Link Afiliado: ${deal.affiliate_url}`
      ].join('\n');

    const teamsAdaptiveCard =
      (matchedCard && matchedCard.teams_adaptive_card) || {
        type: 'AdaptiveCard',
        $schema: 'http://adaptivecards.io/schemas/adaptive-card.json',
        version: '1.4',
        body: [
          {
            type: 'TextBlock',
            text: `🔥 OFERTA AMAZON COLOMBIA (-${deal.discount_pct}% OFF)`,
            weight: 'Bolder',
            color: 'Attention'
          },
          {
            type: 'TextBlock',
            text: deal.title,
            weight: 'Bolder',
            size: 'Medium',
            wrap: true
          },
          {
            type: 'FactSet',
            facts: [
              {
                title: 'Precio Oferta:',
                value: `$${deal.price_usd.toFixed(2)} USD (~${totalCop})`
              },
              {
                title: 'Precio Lista / 90d:',
                value: `$${deal.original_price_usd.toFixed(2)} USD (-${deal.discount_pct}%)`
              },
              {
                title: 'Aduana DIAN CO:',
                value: deal.tax_free_colombia
                  ? '✅ Exento 0% IVA/Arancel (≤$200 USD)'
                  : `⚠️ +$${deal.estimated_tax_usd.toFixed(2)} USD Impuestos`
              },
              {
                title: 'Envío a Colombia:',
                value:
                  deal.free_shipping_co && deal.price_usd >= 35
                    ? '🇨🇴 GRATIS (Elegible AmazonGlobal)'
                    : `$${deal.shipping_usd.toFixed(2)} USD`
              },
              {
                title: 'Código ASIN:',
                value: deal.asin
              }
            ]
          }
        ],
        actions: [
          {
            type: 'Action.OpenUrl',
            title: '🛒 Comprar en Amazon.com',
            url: deal.affiliate_url
          },
          {
            type: 'Action.OpenUrl',
            title: '🌐 Análisis Aduanero en Web',
            url: deal.web_deal_url
          }
        ]
      };

    return {
      telegramCaptionHtml,
      teamsAdaptiveCard
    };
  }

  function renderChannelSimulator() {
    const deal =
      state.deals.find((d) => d.asin === state.selectedPreviewAsin) ||
      state.deals[0];
    if (!deal) return;

    const { telegramCaptionHtml, teamsAdaptiveCard } = buildChannelPayloadsForDeal(deal);
    const totalCop = formatCOP(
      deal.price_usd + deal.shipping_usd + deal.estimated_tax_usd,
      state.trmCop
    );

    // Actualizar Vista Telegram
    if (dom.tgPreviewImg) {
      dom.tgPreviewImg.src = deal.image_url;
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

    // Actualizar Vista Microsoft Teams Adaptive Card
    if (dom.teamsPreviewBadge) {
      dom.teamsPreviewBadge.textContent = deal.tax_free_colombia
        ? `🟢 EXENTO DIAN ≤$200 USD · -${deal.discount_pct}% OFF`
        : `🔥 OFERTA VERIFICADA · -${deal.discount_pct}% OFF`;
    }
    if (dom.teamsPreviewTitle) {
      dom.teamsPreviewTitle.textContent = deal.title;
    }
    if (dom.teamsPreviewImg) {
      dom.teamsPreviewImg.src = deal.image_url;
      dom.teamsPreviewImg.alt = deal.title;
    }
    if (dom.teamsPreviewFacts) {
      const facts = [
        ['Precio Amazon:', `$${deal.price_usd.toFixed(2)} USD (Antes $${deal.original_price_usd.toFixed(2)})`],
        ['Total en Pesos:', `~${totalCop} (TRM $${state.trmCop.toLocaleString('es-CO')})`],
        [
          'Aduana DIAN:',
          deal.tax_free_colombia
            ? '🟢 0% IVA y 0% Arancel (≤$200 USD)'
            : `⚠️ Estimado +$${deal.estimated_tax_usd.toFixed(2)} USD`
        ],
        [
          'Envío a Colombia:',
          deal.free_shipping_co && deal.price_usd >= 35
            ? '🇨🇴 Envío Gratis a Colombia'
            : `$${deal.shipping_usd.toFixed(2)} USD`
        ],
        ['ASIN / Estado:', `${deal.asin} · Verificado Zero-Token`]
      ];
      dom.teamsPreviewFacts.innerHTML = facts
        .map(
          ([title, value]) => `
            <div class="teams-fact-title">${title}</div>
            <div class="teams-fact-value">${value}</div>
          `
        )
        .join('');
    }
    if (dom.teamsPreviewActions) {
      dom.teamsPreviewActions.innerHTML = `
        <a
          href="${deal.affiliate_url}"
          target="_blank"
          rel="nofollow sponsored noopener"
          class="teams-action-btn teams-action-btn-primary"
        >
          🛒 Comprar en Amazon
        </a>
        <a
          href="?asin=${encodeURIComponent(deal.asin)}"
          data-open-modal="${deal.asin}"
          class="teams-action-btn teams-action-btn-secondary"
        >
          🌐 Abrir Ficha (?asin=${deal.asin})
        </a>
      `;
    }

    // Guardar payloads actuales para copiado en un clic
    state.currentTelegramText = telegramCaptionHtml.replace(/<[^>]+>/g, '');
    state.currentTeamsJson = JSON.stringify(teamsAdaptiveCard, null, 2);
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

    dom.modalDealAsin.textContent = `ASIN: ${deal.asin}`;
    dom.modalDealCategory.textContent = deal.category;
    dom.modalDealStatus.textContent = `Descuento real -${deal.discount_pct}% OFF`;
    dom.modalDealImage.src = deal.image_url;
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
          ? `<span class="co-pill co-pill-shipping">🇨🇴 Envío Gratis a Colombia</span>`
          : ''
      }
    `;

    dom.modalPriceFob.textContent = `${formatUSD(deal.price_usd)} (~${formatCOP(deal.price_usd, state.trmCop)})`;
    dom.modalPriceList.textContent = `${formatUSD(deal.original_price_usd)} (-${deal.discount_pct}% OFF)`;
    dom.modalShippingCo.textContent =
      deal.free_shipping_co && deal.price_usd >= 35
        ? 'GRATIS a Colombia ($0.00 USD)'
        : `${formatUSD(deal.shipping_usd)}`;
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

    // Copiar payloads de Telegram y Teams
    if (dom.btnCopyTelegram) {
      dom.btnCopyTelegram.addEventListener('click', () => {
        copyToClipboard(
          state.currentTelegramText || '',
          'Copy de Telegram copiado con link de afiliado'
        );
      });
    }

    if (dom.btnCopyTeams) {
      dom.btnCopyTeams.addEventListener('click', () => {
        copyToClipboard(
          state.currentTeamsJson || '{}',
          'JSON Adaptive Card de Microsoft Teams copiado'
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

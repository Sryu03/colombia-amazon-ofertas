# Bitácora de Errores y Soluciones — PillePues (Amazon Colombia Affiliates)

Registro histórico de incidentes reales encontrados durante el desarrollo, despliegue y operación 24/7 del sistema Zero-Token (`Sryu03/colombia-amazon-ofertas`), junto con su causa raíz y solución aplicada.

---

## 1. Flujo manual de despliegue (ZIPs) y carpeta duplicada en Vercel (`63aea32`)
- **Síntoma:** Cada cambio requería descargar un `.zip`, descomprimirlo y subir archivos manualmente por la interfaz web de GitHub. Además, el segundo proyecto en Vercel (`colombia-amazon-ofertas-3123`) fallaba con `deployment failed`.
- **Causa raíz:** El repositorio no estaba operando con flujo Git/PR automatizado y existía una carpeta duplicada (`vitrina-colombia-ofertas/`) que quedó obsoleta tras reorganizar el proyecto en la raíz (`public/`, `api/`, `docs/`).
- **Solución:**
  - Se limpiaron los archivos duplicados y cachés (`__pycache__`) en `63aea32`.
  - Se conectó el flujo automatizado mediante ramas de trabajo + `gh pr create` + `gh pr merge` (necesario porque las políticas de seguridad bloquean `git push` directo a `main` con `HTTP 403`).
  - El proyecto principal en Vercel (`colombia-amazon-ofertas`, Root Directory vacío) quedó desplegando automáticamente desde `main`.

---

## 2. Enlaces de afiliado sin parámetros oficiales de SiteStripe (`20ddb77` · PR #1)
- **Síntoma:** Los enlaces generados hacia Amazon.com solo llevaban `?tag=pillepues-20` y no incluían los parámetros completos que entrega SiteStripe al compartir un producto como asociado.
- **Causa raíz:** `build_affiliate_url` y el frontend construían URLs simplificadas sin `linkCode`, `language` ni `ref_`.
- **Solución:**
  - Se actualizó [`build_affiliate_url`](src/copywriter/affiliate_builder.py) y `build_telegram_card` para emitir y normalizar siempre:
    `https://www.amazon.com/dp/{ASIN}?linkCode=ll1&tag=pillepues-20&language=es_US&ref_=as_li_ss_tl`.
  - Se replicó la misma normalización en [`public/app.js`](public/app.js) y [`docs/app.js`](docs/app.js).

---

## 3. Priorización por comisión y productos sin envío directo a Colombia (`7761404` · PR #1)
- **Síntoma:** El sistema necesitaba enfocarse en la mejor oferta/descuento real extraída de la pestaña de Ofertas de Amazon y rechazar productos que requirieran casillero en Miami.
- **Causa raíz:** El ordenamiento y las fuentes de descubrimiento no priorizaban estrictamente el porcentaje de descuento ni bloqueaban de forma dura `requires_locker=True`.
- **Solución:**
  - Se añadió [`deal_priority_key`](src/evaluator/colombia_rules.py) para ordenar únicamente por bajada de precio nueva, `%` de descuento, envío gratis a Colombia, exención DIAN (`<= $200 USD`) y ahorro en USD.
  - Se exigió `ships_to_colombia=True` y `requires_locker=False` en [`evaluate_colombia_deal`](src/evaluator/colombia_rules.py) y [`api/index.py`](api/index.py).
  - Se agregaron feeds de Ofertas de Amazon (`gp/goldbox`, `p_n_deal_type=23566064011`, `movers-and-shakers`, `bestsellers`) en [`src/monitor/discovery.py`](src/monitor/discovery.py).

---

## 4. Amazon bloquea IPs de GitHub Actions con CAPTCHA y vacía `deals.json` (`37b299c` → `0c8c8c1` · PR #2)
- **Síntoma:** En la ejecución automática `37b299c`, el bot sobrescribió [`public/data/deals.json`](public/data/deals.json) dejándolo con `0` ofertas (`[]`).
- **Causa raíz:**
  1. Las IPs de datacenter de GitHub Actions reciben CAPTCHA al consultar páginas individuales `/dp/{ASIN}`.
  2. La protección anterior en [`api/index.py`](api/index.py) solo preservaba `deals.json` cuando `len(catalog) == 0`, pero si pasaba 1 producto sin descuento válido (`approved_deals == 0`), borraba todo el catálogo público.
- **Solución:**
  - Se corrigió la guarda en `api/index.py` a `if LIVE_SCRAPE and len(approved_deals) == 0 and deals_json_path.exists():` para proteger siempre el catálogo vigente.
  - Se agregó `curl_cffi` con suplantación TLS de Chrome en `discovery.py`, `amazon_scraper.py` y [`.github/workflows/zero-token-monitor.yml`](.github/workflows/zero-token-monitor.yml).
  - Se implementó [`parse_search_deals_html`](src/monitor/discovery.py) para extraer título, precio, precio tachado, imagen y elegibilidad directamente desde el HTML SSR de las páginas de Ofertas sin tener que abrir `/dp/{ASIN}`.

---

## 5. Fallo del parser SSR cuando falta `beautifulsoup4` (`0c8c8c1` · PR #2)
- **Síntoma:** La prueba unitaria de `parse_search_deals_html` devolvía `0 != 1` en entornos sin `bs4` instalado.
- **Causa raíz:** `parse_search_deals_html` dependía exclusivamente de `BeautifulSoup`.
- **Solución:** Se añadió un parser alterno 100% con librería estándar (`re` + `html.unescape`) dentro de [`parse_search_deals_html`](src/monitor/discovery.py) y [`parse_bestsellers_deals_html`](src/monitor/discovery.py).

---

## 6. Telegram no recibía mensajes y no había visibilidad real del estado de entrega (`7a2c6f3` · PR #3)
- **Síntoma:** El workflow terminaba en verde (`success`), pero `@pillepues` no había recibido las ofertas y los logs de GitHub Actions (`403`) no eran accesibles por API del conector. Además, `price_history.py` marcaba productos como publicados aunque Telegram hubiera fallado.
- **Causa raíz:**
  1. La sandbox local bloquea `api.telegram.org` (`HTTP 403`), por lo que el envío real solo puede ocurrir desde GitHub Actions.
  2. Cuando el scraping en vivo encontraba `0` ofertas nuevas, no había opción de respaldo para enviar el catálogo verificado.
  3. `api/index.py` llamaba `price_history.mark_published()` verificando solo si existía token, sin comprobar `status == "sent"`.
- **Solución:**
  - Se agregó el input manual `publish_catalog` en [`.github/workflows/zero-token-monitor.yml`](.github/workflows/zero-token-monitor.yml) y su lógica en [`api/index.py`](api/index.py).
  - Se exigió `b_res.get("telegram", {}).get("status") == "sent"` antes de actualizar [`price_history.json`](public/data/price_history.json).
  - Se añadió `telegram_delivery_status` sanitizado (sin tokens, usando `_sanitize_error_detail` en [`channels.py`](src/broadcaster/channels.py)) dentro de `deals.json` para auditar cada envío desde Git.
  - Se implementó subida respaldo `multipart/form-data` en `channels.py` por si Telegram rechaza descargar una URL externa de imagen.

---

## 7. Imágenes pixeladas (`_AC_UL320_`), productos recortados en Telegram y falta de marca de agua (`2ea252f` · PR #4)
- **Síntoma:** Las fotos enviadas a Telegram se veían en baja resolución y recortadas en la vista previa de Telegram, sin identidad visual ni marca de agua de `PillePues`.
- **Causa raíz:**
  1. Las tarjetas de búsqueda de Amazon entregan miniaturas de `320px` (`._AC_UL320_.jpg`).
  2. Al enviar la imagen cruda sin relleno (`padding`), Telegram recorta los extremos de fotos verticales/altas.
- **Solución:**
  - Se creó [`src/broadcaster/card_image.py`](src/broadcaster/card_image.py) con `Pillow` (0 tokens LLM) para:
    - Convertir URLs de Amazon a alta resolución (`_AC_SL1500_` / `_AC_SL1200_`) mediante `upgrade_amazon_image_url` (cuidando no degradar imágenes que ya son `>= 1500px`, error detectado en pruebas unitarias).
    - Componer una tarjeta HD `1080×1080` usando `ImageOps.contain` con márgenes amplios (el producto **nunca** se recorta), cabecera `PillePues`, badge de descuento, pills de envío a Colombia / `0% IVA DIAN`, precio USD/antes/COP, marca de agua diagonal sutil y sello `PillePues · @pillepues`.
    - Corrección menor durante pruebas: `Image.rotate()` solo acepta `BICUBIC`/`BILINEAR`/`NEAREST` (no `LANCZOS`).
  - Se actualizó [`public/index.css`](public/index.css) y [`public/app.js`](public/app.js) para replicar el encuadre sin recortes, resolución HD y sello `PillePues · @pillepues` en la web.

---

## 8. El cron `*/10 * * * *` de GitHub Actions no disparó en 35+ minutos
- **Síntoma:** Tras 35 minutos desde la última ejecución, no hubo ninguna corrida automática en GitHub Actions (todas las corridas registradas seguían siendo `workflow_dispatch`).
- **Causa raíz:**
  1. El `schedule` gratuito de GitHub Actions es *best-effort* (no un cron en tiempo real): los minutos `:00, :10, :20, :30, :40, :50` sufren la mayor congestión global de GitHub y se retrasan 15–60+ minutos o se omiten.
  2. Además, cada merge que modifica `.github/workflows/zero-token-monitor.yml` en `main` reinicia el registro interno del cron en GitHub.
- **Solución:**
  - Se ajustó el `cron` en [`.github/workflows/zero-token-monitor.yml`](.github/workflows/zero-token-monitor.yml) a minutos desfasados fuera de pico (`7,22,37,52 * * * *`).
  - Para puntualidad exacta cada 10 minutos, se documentó la activación mediante webhook externo gratuito (`cron-job.org`) invocando `workflow_dispatch` vía API de GitHub.

---

## 9. Correos repetidos de fallo en Vercel cada 10 minutos (`colombia-amazon-ofertas-3123`)
- **Síntoma:** Cada vez que el bot ejecutaba `git push` a `main`, Vercel enviaba un correo de error indicando `The specified Root Directory "vitrina-colombia-ofertas" does not exist`.
- **Causa raíz:** Existía un segundo proyecto duplicado en Vercel (`colombia-amazon-ofertas-3123`) conectado al mismo repositorio de GitHub y apuntando al antiguo subdirectorio `vitrina-colombia-ofertas/`, mientras el proyecto principal (`colombia-amazon-ofertas` → `vitrina-colombia-ofertas.vercel.app`) ya operaba desde la raíz del repo.
- **Solución:** Eliminación del proyecto duplicado `colombia-amazon-ofertas-3123` en Vercel para que solo permanezca el proyecto principal activo.

---

## 10. Precios en Telegram no coincidían con Amazon.com por ofertas viejas en cola
- **Síntoma:** Varias ofertas enviadas a `@pillepues` desde la cola (`verified_catalog`) mostraban un precio de oferta anterior que ya había cambiado o expirado en Amazon.com.
- **Causa raíz:**
  1. Cuando el descubrimiento general recibía CAPTCHA, [`api/index.py`](api/index.py) tomaba ofertas guardadas horas atrás en [`public/data/deals.json`](public/data/deals.json) y las enviaba a Telegram **sin re-verificar el precio en vivo** ni validar antigüedad máxima (TTL).
  2. El parser de búsqueda (`parse_search_deals_html`) aceptaba tarjetas con precio exclusivo Prime (`With Prime`) o dispositivos Amazon (`Echo`, `Ring`, `Blink`), y `parse_amazon_html` tenía un fallback global de precio fuera del contenedor de Buy Box.
- **Solución:**
  - Re-verificación en vivo obligatoria (`scraper.fetch_asin_live(asin)`) para cada oferta en cola antes de enviarla a Telegram: si la oferta expiró o perdió el descuento mínimo (`20%`), **se descarta de Telegram y se elimina automáticamente de `deals.json`**; si cambió de precio pero sigue vigente, se actualiza con el precio real en Telegram y en la Web.
  - Bloqueo estricto de antigüedad (`MAX_UNVERIFIED_DEAL_AGE_MINUTES = 90`): si Amazon bloquea la re-verificación y la oferta en cola supera 90 minutos sin verificarse, no se envía a Telegram (`stale_catalog_blocked_recheck`).
  - Priorización de los ASINs activos de `deals.json` dentro de `fetch_catalog` para refrescar la vitrina web en cada ciclo.
  - Filtros en [`src/monitor/discovery.py`](src/monitor/discovery.py) contra precios exclusivos Prime y dispositivos restringidos (`Echo`/`Ring`/`Blink`/`Fire TV`/`Kindle`), y acotamiento estricto al Buy Box en [`src/monitor/amazon_scraper.py`](src/monitor/amazon_scraper.py).

---

## 11. Productos sin envío a Colombia o precio distinto desde listado de búsqueda (`B0DL72PK1P` Apple Magic Mouse)
- **Síntoma:** Se publicó en Telegram y Web `Apple Magic Mouse` (`B0DL72PK1P`) con precio `$59.99 USD` y etiqueta `"Necesita casillero: No (Envío directo a Colombia)"`, cuando al abrirlo desde Colombia Amazon mostraba `"No puede enviarse este producto al punto de entrega seleccionado"` + `"Ver artículos similares"` (sin Buy Box ni envío directo).
- **Causa raíz:**
  1. [`parse_search_deals_html`](src/monitor/discovery.py) marcaba `live_verified=True` y `ships_to_colombia=True` directamente desde tarjetas de búsqueda renderizadas para IP de EE. UU., y `fetch_catalog` omitía consultar `/dp/<ASIN>` cuando veía `live_verified=True`.
  2. El scraper no configuraba sesión de entrega en Colombia (`countryCode=CO`) en Amazon y asumía `ships_to_colombia=True` por defecto si no detectaba la frase de bloqueo.
  3. No existía una puerta final independiente de auditoría antes de exportar a la Web y difundir a Telegram.
- **Solución:**
  - Se creó el subagente auditor **`verificador-colombia-auditor`** y su motor determinista [`DealAuditor`](src/auditor/deal_auditor.py), ejecutado obligatoriamente en [`api/index.py`](api/index.py) antes de exportar a `deals.json` (Web) y antes de enviar a `@pillepues` (Telegram).
  - [`discovery.py`](src/monitor/discovery.py) ahora marca los hallazgos de búsqueda con `live_verified=False` y `detail_verified=False`, obligando a [`AmazonMonitorScraper`](src/monitor/amazon_scraper.py) a verificar cada `/dp/<ASIN>` con sesión `countryCode=CO` (endpoint `glow/address-change` + `sp-cdn="L5Z9:CO"`), Buy Box activo (`#add-to-cart-button` / `#buy-now-button`) y confirmación explícita de envío a Colombia (`delivery_country_confirmed == "CO"`).
  - Si un producto no envía directo (`BLOCKED_CO` o `requires_locker=True`), nunca puede publicarse como envío directo; [`card_image.py`](src/broadcaster/card_image.py), [`colombia_rules.py`](src/evaluator/colombia_rules.py) y [`public/app.js`](public/app.js) muestran explícitamente `"Requiere casillero en Miami"` cuando aplique, y `DealAuditor` rechaza y purga automáticamente ofertas no verificadas en `deals.json`.


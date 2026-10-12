// APP MASTER JS CONTROLLER — Master Suite 5-in-1

let currentTab = 'inicio';
let stockDataGlobal = [];
let productosDataGlobal = [];
let comisionesDataGlobal = [];
let satDataGlobal = [];
let cobranzaDataGlobal = [];
let pnlDataGlobal = null;
let gastosDataGlobal = null;
let currentGastosSubtab = 'tablero';
let currentGastosMovimientoManual = null;
let currentComprobanteFile = null;
let currentBancoFile = null;
let currentPnlSubtab = 'cascada';
let currentPnlCascadaMode = 'split';
let chartTopProductos = null;
let chartProdModalMensual = null;
let chartProdModalDonut = null;
let especialesActivosGlobal = { 'sandra belinda medina': 0.05 };
let clientesUnicosGlobal = [];
let currentTheme = 'dark';

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  const now = new Date();
  const elProdMes = document.getElementById('prod-mes');
  if (elProdMes) elProdMes.value = now.getMonth() + 1;
  const elComMes = document.getElementById('com-mes');
  if (elComMes) elComMes.value = now.getMonth() + 1;
  const elVvMes = document.getElementById('vv-mes');
  if (elVvMes) elVvMes.value = now.getMonth() + 1;

  switchTab('inicio');
  renderChipsEspecialesUI();
  loadVendedores();
  pollStatus();
  setInterval(pollStatus, 15000);

  // Close custom dropdown when clicking outside
  document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('dropdown-clientes-custom');
    const input = document.getElementById('com-cli-esp');
    if (dropdown && input && !dropdown.contains(e.target) && !input.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  });
});

function normalizarTexto(txt) {
  if (!txt) return '';
  return txt.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

function escapeJs(str) {
  if (!str) return '';
  return String(str)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/"/g, '&quot;')
    .replace(/\n/g, ' ')
    .replace(/\r/g, '');
}
window.escapeJs = escapeJs;

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
window.escapeHtml = escapeHtml;

function almacenesCoincidenJS(filtro, almacenReal) {
  if (!filtro || filtro === 'Todos los Almacenes' || filtro === 'TODOS') return true;
  return normalizarTexto(filtro) === normalizarTexto(almacenReal);
}

function toggleMobileSidebar(forceState) {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (!sidebar || !backdrop) return;

  const isCurrentlyOpen = !sidebar.classList.contains('-translate-x-full');
  const shouldOpen = forceState !== undefined ? forceState : !isCurrentlyOpen;

  if (shouldOpen) {
    sidebar.classList.remove('-translate-x-full');
    backdrop.classList.remove('hidden');
  } else {
    sidebar.classList.add('-translate-x-full');
    backdrop.classList.add('hidden');
  }
}

// ── SISTEMA GLOBAL DE CARGA & RETROALIMENTACIÓN EN VIVO ────────────────────
let loadingTimer = null;

function showLoading(title = 'Cargando información...', desc = 'Sincronizando datos con Odoo ERP...') {
  if (loadingTimer) {
    clearTimeout(loadingTimer);
    loadingTimer = null;
  }
  const overlay = document.getElementById('global-loading-dialog');
  const card = document.getElementById('global-loading-card');
  const iconCont = document.getElementById('global-loading-icon-container');
  const icon = document.getElementById('global-loading-icon');
  const titleEl = document.getElementById('global-loading-title');
  const descEl = document.getElementById('global-loading-desc');
  const barWrapper = document.getElementById('global-loading-bar-wrapper');

  if (!overlay || !card) return;

  if (iconCont) iconCont.className = 'w-16 h-16 rounded-2xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 text-2xl transition-all duration-300 shadow-lg shadow-blue-600/20';
  if (icon) icon.className = 'fa-solid fa-spinner fa-spin';
  if (titleEl) titleEl.innerText = title;
  if (descEl) descEl.innerText = desc;
  if (barWrapper) barWrapper.classList.remove('hidden');

  overlay.classList.remove('opacity-0', 'pointer-events-none');
  overlay.classList.add('opacity-100');
  card.classList.remove('scale-95');
  card.classList.add('scale-100');
}

function hideLoading(successTitle = '¡Listo!', successDesc = 'Información actualizada correctamente') {
  const overlay = document.getElementById('global-loading-dialog');
  const card = document.getElementById('global-loading-card');
  const iconCont = document.getElementById('global-loading-icon-container');
  const icon = document.getElementById('global-loading-icon');
  const titleEl = document.getElementById('global-loading-title');
  const descEl = document.getElementById('global-loading-desc');
  const barWrapper = document.getElementById('global-loading-bar-wrapper');

  if (!overlay || !card) return;

  if (iconCont) iconCont.className = 'w-16 h-16 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 text-2xl transition-all duration-300 shadow-lg shadow-emerald-600/30 scale-105';
  if (icon) icon.className = 'fa-solid fa-check';
  if (titleEl) titleEl.innerText = successTitle;
  if (descEl) descEl.innerText = successDesc;
  if (barWrapper) barWrapper.classList.add('hidden');

  if (loadingTimer) clearTimeout(loadingTimer);
  loadingTimer = setTimeout(() => {
    overlay.classList.remove('opacity-100');
    overlay.classList.add('opacity-0', 'pointer-events-none');
    card.classList.remove('scale-100');
    card.classList.add('scale-95');
  }, 450);
}

// ── NAVEGACIÓN ENTRE MÓDULOS ──────────────────────────────────────────────
function switchTab(tab) {
  if (tab === 'sat' || tab === 'gastos') {
    tab = 'inicio';
  }
  currentTab = tab;

  const tabs = ['inicio', 'stock', 'productos', 'comisiones', 'sat', 'cobranza', 'ventas_vendedor', 'pnl', 'gastos'];

  tabs.forEach(t => {
    // Hide content
    const el = document.getElementById(`tab-content-${t}`);
    if (el) el.classList.add('hidden');

    // Reset desktop nav
    const btn = document.getElementById(`nav-${t}`);
    if (btn) {
      btn.className = 'px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-all flex items-center space-x-2';
    }

    // Reset sub nav (tablets / mobile horizontal)
    const subBtn = document.getElementById(`nav-sub-${t}`);
    if (subBtn) {
      subBtn.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold shrink-0 text-slate-400 hover:text-white hover:bg-slate-800 flex items-center space-x-1.5';
    }

    // Reset mobile bottom nav
    const mobBtn = document.getElementById(`mob-nav-${t}`);
    if (mobBtn) {
      mobBtn.className = 'flex flex-col items-center justify-center flex-1 py-1 text-slate-400 hover:text-white transition-colors';
    }
  });

  // Activate content
  const activeContent = document.getElementById(`tab-content-${tab}`);
  if (activeContent) activeContent.classList.remove('hidden');

  // Activate desktop nav
  const activeBtn = document.getElementById(`nav-${tab}`);
  if (activeBtn) {
    activeBtn.className = 'px-3.5 py-2 rounded-xl text-xs font-bold transition-all duration-150 bg-blue-600 text-white shadow-md shadow-blue-600/20 flex items-center space-x-2';
  }

  // Activate sub nav
  const activeSubBtn = document.getElementById(`nav-sub-${tab}`);
  if (activeSubBtn) {
    activeSubBtn.className = 'px-3 py-1.5 rounded-lg text-xs font-bold shrink-0 bg-blue-600 text-white flex items-center space-x-1.5';
  }

  // Activate mobile bottom nav
  const activeMobBtn = document.getElementById(`mob-nav-${tab}`);
  if (activeMobBtn) {
    activeMobBtn.className = 'flex flex-col items-center justify-center flex-1 py-1 text-blue-400 font-bold transition-colors';
  }

  // Trigger data load for the tab
  if (tab === 'inicio') {
    renderInicioDashboard();
  } else if (tab === 'stock') {
    if (stockDataGlobal.length === 0) loadStockData();
    else renderStockTable();
  } else if (tab === 'productos') {
    if (productosDataGlobal.length === 0) loadProductosData();
    else renderProductosTable();
  } else if (tab === 'comisiones') {
    const selCom = document.getElementById('com-vendedor');
    if (!selCom || selCom.options.length <= 1 || !selCom.value) {
      loadVendedores();
    } else if (comisionesDataGlobal.length === 0) {
      loadComisionesData();
    } else {
      renderComisionesTable();
    }
  } else if (tab === 'sat') {
    if (satDataGlobal.length === 0) loadSatData();
    else renderSatTable();
  } else if (tab === 'cobranza') {
    if (cobranzaDataGlobal.length === 0) {
      loadCobranzaData();
    } else {
      renderCobranzaKPIs();
      renderCobranzaClientesCards();
      renderCobranzaTable();
      renderCobradoMesView();
      renderCobranzaRecuperacion();
    }
  } else if (tab === 'ventas_vendedor') {
    if (!ventasVendedorDataGlobal) loadVentasVendedorData();
    else renderVentasVendedor();
  } else if (tab === 'pnl') {
    if (!pnlDataGlobal) loadPnlData();
    else renderPnlView();
  } else if (tab === 'gastos') {
    if (!gastosDataGlobal) loadGastosConciliacion();
    else {
      renderGastosKPIs();
      renderGastosVistas();
    }
  }
}

function onEmpresaChange() {
  mlDataGlobal = null;
  ventasVendedorDataGlobal = null;
  pnlDataGlobal = null;
  gastosDataGlobal = null;
  showLoading('Cambiando de Empresa...', 'Sincronizando registros con Odoo ERP...');
  if (currentTab === 'inicio') {
    renderInicioDashboard();
    hideLoading();
  }
  else if (currentTab === 'stock') loadStockData();
  else if (currentTab === 'productos') {
    loadProductosData();
    if (currentProdView === 'ml' || currentProdView === 'historico') {
      loadTop20HistoricoML();
    }
  }
  else if (currentTab === 'comisiones') loadVendedores();
  else if (currentTab === 'sat') loadSatData();
  else if (currentTab === 'cobranza') loadCobranzaData();
  else if (currentTab === 'ventas_vendedor') loadVentasVendedorData();
  else if (currentTab === 'pnl') loadPnlData();
  else if (currentTab === 'gastos') loadGastosConciliacion();
}

// ── AUXILIARES FORMATO ──────────────────────────────────────────────────────
function fmtMxn(val) {
  try { return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(val || 0); }
  catch { return '$0.00'; }
}

function fmtNum(val) {
  try { return new Intl.NumberFormat('es-MX', { maximumFractionDigits: 1 }).format(val || 0); }
  catch { return '0'; }
}

function formatFechaMX(val) {
  if (!val) return '—';
  try {
    const s = String(val).trim();
    if (s.length >= 10 && s.includes('-')) {
      const parts = s.substring(0, 10).split('-');
      if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return s;
  } catch {
    return String(val);
  }
}
window.formatFechaMX = formatFechaMX;



// ── MÓDULO 0: INICIO / PORTAL Y CENTRO DE CONTROL EJECUTIVO ─────────────────
async function renderInicioDashboard() {
  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  const labelEmpresa = document.getElementById('inicio-empresa-label');
  if (labelEmpresa) {
    labelEmpresa.innerText = empresa.includes('BALDOMERO') ? 'Baldomero Medina Garza' :
                             empresa.includes('MULTITRANS') ? 'Auto Línea Multitrans' : 'Consolidado Multitienda';
  }

  const labelFecha = document.getElementById('inicio-fecha-actual');
  if (labelFecha) {
    const d = new Date();
    const opciones = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const fechaStr = d.toLocaleDateString('es-MX', opciones);
    labelFecha.innerText = fechaStr.charAt(0).toUpperCase() + fechaStr.slice(1);
  }

  const d = new Date();
  const mes = d.getMonth() + 1;
  const anio = d.getFullYear();

  // 1. KPI Ventas Mes Actual
  fetch('/api/ventas_vendedor', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ empresa_nombre: empresa, mes: mes, anio: anio, excluir_interempresa: false })
  })
    .then(res => res.json())
    .then(data => {
      const totGen = data.data?.totales_generales;
      const totalFact = totGen?.total_facturado || totGen?.total_con_iva || data.data?.totales?.total_neto || 0;
      const el = document.getElementById('inicio-kpi-ventas');
      if (el) el.innerText = fmtMxn(totalFact);
    })
    .catch(err => console.error("Error inicio ventas:", err));

  // 2. KPI Cobranza / Cartera Viva
  const interCob = document.getElementById('cob-interempresa')?.checked ?? true;
  fetch('/api/cobranza', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ empresa_nombre: empresa, excluir_interempresa: interCob })
  })
    .then(res => res.json())
    .then(data => {
      const tot = data.data?.totales;
      const saldo = tot?.saldo_total || tot?.total_saldo || 0;
      const el = document.getElementById('inicio-kpi-cobranza');
      if (el) el.innerText = fmtMxn(saldo);
    })
    .catch(err => console.error("Error inicio cobranza:", err));

  // 3. KPI Stock
  fetch('/api/stock', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ empresa_nombre: empresa, almacen_filtro: 'Todos los Almacenes', dias_analisis: 30, excluir_interempresa: true })
  })
    .then(res => res.json())
    .then(data => {
      const inv = data.data?.inventario || data.data || [];
      if (data.data?.almacenes_detectados && data.data.almacenes_detectados.length > 0) {
        const selectAlm = document.getElementById('stock-almacen');
        if (selectAlm && selectAlm.options.length <= 1) {
          data.data.almacenes_detectados.forEach(wh => {
            const opt = document.createElement('option');
            opt.value = wh;
            opt.innerText = wh;
            selectAlm.appendChild(opt);
          });
        }
      }
      if (inv.length > 0) {
        stockDataGlobal = inv;
        const elStock = document.getElementById('inicio-kpi-stock');
        if (elStock) elStock.innerHTML = `${inv.length.toLocaleString('es-MX')} <span class="text-sm font-sans font-normal text-slate-400">SKUs</span>`;
        const agotados = inv.filter(p => (p.disponible || p.stock_actual || 0) <= 0).length;
        const elAlert = document.getElementById('inicio-kpi-stock-alert');
        if (elAlert) {
          if (agotados > 0) {
            elAlert.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-1 text-rose-400"></i> <span class="text-rose-400 font-bold">${agotados} agotados</span> <span class="text-slate-500 ml-1">• ${(inv.length - agotados).toLocaleString('es-MX')} en stock</span>`;
          } else {
            elAlert.innerHTML = `<i class="fa-solid fa-shield-check mr-1 text-emerald-400"></i> <span class="text-emerald-400 font-bold">100% en existencia</span>`;
          }
        }
      }
    })
    .catch(err => console.error("Error inicio stock:", err));

  // 4. KPI P&L Rentabilidad Bruta
  fetch('/api/estado_resultados', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ empresa_nombre: empresa, anio: anio, excluir_interempresa: false })
  })
    .then(res => res.json())
    .then(data => {
      const resEj = data.data?.kpis || data.data?.resumen_ejecutivo;
      const el = document.getElementById('inicio-kpi-pnl') || document.getElementById('inicio-kpi-sat');
      if (el && resEj) {
        el.innerText = `${(resEj.margen_bruto_pct || 0).toFixed(1)}%`;
      }
      const elSub = document.getElementById('inicio-kpi-pnl-sub');
      if (elSub && resEj) {
        elSub.innerHTML = `<i class="fa-solid fa-calculator mr-1"></i> ${fmtMxn(resEj.utilidad_bruta || 0)} utilidad`;
      }
    })
    .catch(err => console.error("Error inicio pnl:", err));
}

// ── MÓDULO 1: STOCK & ALMACENES (DEMANDA Y REABASTECIMIENTO) ─────────────────
let currentStockQuickFilter = 'TODOS';

function onStockAlmacenChange() {
  if (stockDataGlobal && stockDataGlobal.length > 0) {
    recalcularMetricasStockLocal();
  } else {
    loadStockData();
  }
}

async function loadStockData() {
  const empresa = document.getElementById('global-empresa')?.value || 'BALDOMERO MEDINA GARZA';
  const dias = document.getElementById('stock-dias')?.value || '30';
  const inter = document.getElementById('stock-interempresa')?.checked ?? true;

  showLoading('Consultando Stock & Almacenes...', 'Obteniendo existencias y rotación en tiempo real desde Odoo 19...');

  const tbody = document.getElementById('tbody-stock');
  if (tbody && stockDataGlobal.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="12" class="p-8 text-center text-blue-400 font-medium">
          <i class="fa-solid fa-spinner fa-spin text-2xl mb-2 block"></i>
          Sincronizando inventario, demanda mensual y puntos de reorden desde Odoo 19...
        </td>
      </tr>
    `;
  }

  try {
    const res = await fetch('/api/stock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ empresa_nombre: empresa, almacen_filtro: 'Todos los Almacenes', dias_analisis: dias, excluir_interempresa: inter })
    });
    if (!res.ok) {
      throw new Error(`El servidor respondió con código ${res.status}. Reconectando...`);
    }
    const data = await res.json();
    if (data.success && data.data) {
      stockDataGlobal = data.data.inventario || [];

      if (data.data.almacenes_detectados && data.data.almacenes_detectados.length > 0) {
        const selectAlm = document.getElementById('stock-almacen');
        if (selectAlm) {
          const valActual = selectAlm.value;
          selectAlm.innerHTML = '<option value="Todos los Almacenes">Todos los Almacenes (Consolidado)</option>';
          data.data.almacenes_detectados.forEach(wh => {
            const opt = document.createElement('option');
            opt.value = wh;
            opt.innerText = wh;
            if (wh === valActual) opt.selected = true;
            selectAlm.appendChild(opt);
          });
        }
      }

      recalcularMetricasStockLocal();
      hideLoading('¡Inventario Listo!', `${stockDataGlobal.length} productos y puntos de reorden calculados.`);
    } else {
      hideLoading('⚠️ Sin Datos', 'No se encontraron registros de inventario.');
    }
  } catch (err) {
    console.error('Error stock:', err);
    hideLoading('⚠️ Error de Stock', 'No se pudo sincronizar el inventario.');
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="12" class="p-8 text-center text-rose-400 font-medium">
            Error al sincronizar inventario: ${err}
          </td>
        </tr>
      `;
    }
  }
}

function recalcularMetricasStockLocal() {
  const diasSeguridad = parseInt(document.getElementById('stock-dias-seguridad')?.value || '15');
  const diasMeta = parseInt(document.getElementById('stock-dias-meta')?.value || '30');

  // Recalcular métricas dinámicas para cada producto en memoria
  stockDataGlobal.forEach(item => {
    const vDia = parseFloat(item.venta_diaria || 0);
    const disp = parseFloat(item.disponible || 0);
    const vPer = parseFloat(item.ventas_periodo || 0);

    // Venta mensual estimada a 30 días
    item.venta_mensual_est = Math.round(vDia * 30.0 * 10) / 10;

    // Stock mínimo de seguridad y meta deseada
    if (vDia > 0) {
      item.stock_minimo = Math.max(1, Math.ceil(vDia * diasSeguridad));
      item.stock_sugerido_mes = Math.max(1, Math.ceil(vDia * diasMeta));
      item.stock_maximo = Math.max(2, Math.ceil(vDia * (diasMeta * 2)));
    } else {
      item.stock_minimo = 0;
      item.stock_sugerido_mes = 0;
      item.stock_maximo = 50;
    }

    // Faltante a pedir para llegar a la meta mensual
    if (item.stock_sugerido_mes > 0 && disp < item.stock_sugerido_mes) {
      item.sugerido_pedir = Math.ceil(item.stock_sugerido_mes - disp);
    } else {
      item.sugerido_pedir = 0;
    }

    // Inversión estimada
    const pr = parseFloat(item.precio_unitario_est || (item.ventas_periodo > 0 ? (item.valor_estimado / (item.disponible || 1)) : 0) || 0);
    item.inversion_reorden = item.sugerido_pedir * pr;

    // Actualizar estado dinámico
    if (disp <= 0) {
      item.estado = 'AGOTADO';
    } else if (disp < item.stock_minimo || item.dias_cobertura <= diasSeguridad) {
      item.estado = 'REORDENAR';
    } else if (vPer === 0 && disp > 50) {
      item.estado = 'SOBRESTOCK';
    } else if (disp > item.stock_maximo && disp > 50 && vPer > 0) {
      item.estado = 'SOBRESTOCK';
    } else if (vPer === 0) {
      item.estado = 'SIN_MOVIMIENTO';
    } else {
      item.estado = 'OPTIMO';
    }
  });

  renderStockTable();
}

function setQuickFilterStock(estado) {
  currentStockQuickFilter = estado;
  const selEstado = document.getElementById('filter-stock-estado');
  if (selEstado) selEstado.value = estado;

  // Actualizar estilos activos de las píldoras
  ['TODOS', 'SOLO_REORDEN', 'AGOTADO', 'REORDENAR', 'OPTIMO', 'SOBRESTOCK'].forEach(k => {
    const btn = document.getElementById(`pill-stock-${k}`);
    if (btn) {
      if (k === estado) {
        btn.className = 'px-2.5 py-1 rounded-lg bg-blue-600 text-white transition-all text-[11px] font-bold shadow-md shadow-blue-600/30 ring-2 ring-blue-400';
      } else {
        let textClr = 'text-slate-300';
        let borderClass = 'border-slate-800';
        if (k === 'SOLO_REORDEN') { textClr = 'text-rose-300'; borderClass = 'border-rose-500/30'; }
        if (k === 'AGOTADO') { textClr = 'text-red-400'; borderClass = 'border-red-500/30'; }
        if (k === 'REORDENAR') { textClr = 'text-amber-400'; borderClass = 'border-amber-500/30'; }
        if (k === 'OPTIMO') { textClr = 'text-emerald-400'; borderClass = 'border-emerald-500/30'; }
        if (k === 'SOBRESTOCK') { textClr = 'text-purple-400'; borderClass = 'border-purple-500/30'; }
        btn.className = `px-2.5 py-1 rounded-lg bg-slate-800 ${textClr} hover:bg-slate-700 transition-all text-[11px] font-bold border ${borderClass}`;
      }
    }
  });

  renderStockTable();
}

function actualizarPildoraEstadoDesdeSelect(val) {
  setQuickFilterStock(val);
}

function renderStockTable() {
  const tbody = document.getElementById('tbody-stock');
  if (!tbody) return;

  const almacenFilter = document.getElementById('stock-almacen')?.value || 'Todos los Almacenes';
  const searchInput = document.getElementById('search-stock')?.value || '';
  const search = normalizarTexto(searchInput);
  const marcaFilter = document.getElementById('filter-stock-marca')?.value || 'TODAS';
  const estadoFilter = currentStockQuickFilter || 'TODOS';

  tbody.innerHTML = '';

  // 1. Filtrar productos
  const filtered = stockDataGlobal.filter(item => {
    if (!almacenesCoincidenJS(almacenFilter, item.almacen)) return false;
    if (marcaFilter !== 'TODAS' && item.clasificacion !== marcaFilter) return false;
    if (search) {
      const prodNorm = normalizarTexto(item.producto);
      const whNorm = normalizarTexto(item.almacen);
      if (!prodNorm.includes(search) && !whNorm.includes(search)) return false;
    }

    if (estadoFilter === 'SOLO_REORDEN') {
      return (item.sugerido_pedir > 0 || item.estado === 'AGOTADO' || item.estado === 'REORDENAR');
    }
    if (estadoFilter !== 'TODOS' && item.estado !== estadoFilter) return false;
    return true;
  });

  // 2. Conteo de píldoras globales para el almacén seleccionado
  const baseAlmItems = stockDataGlobal.filter(i => almacenesCoincidenJS(almacenFilter, i.almacen) && (marcaFilter === 'TODAS' || i.clasificacion === marcaFilter));
  const cntTodos = baseAlmItems.length;
  const cntPedir = baseAlmItems.filter(i => i.sugerido_pedir > 0 || i.estado === 'AGOTADO' || i.estado === 'REORDENAR').length;
  const cntAgotados = baseAlmItems.filter(i => i.estado === 'AGOTADO').length;
  const cntBajoMin = baseAlmItems.filter(i => i.estado === 'REORDENAR').length;
  const cntOptimo = baseAlmItems.filter(i => i.estado === 'OPTIMO').length;
  const cntSobrestock = baseAlmItems.filter(i => i.estado === 'SOBRESTOCK').length;

  const elCntTodos = document.getElementById('count-pill-todos');
  const elCntPedir = document.getElementById('count-pill-pedir');
  const elCntAgot = document.getElementById('count-pill-agotados');
  const elCntBajo = document.getElementById('count-pill-bajo-min');
  const elCntOpt = document.getElementById('count-pill-optimo');
  const elCntSobre = document.getElementById('count-pill-sobrestock');

  if (elCntTodos) elCntTodos.innerText = cntTodos;
  if (elCntPedir) elCntPedir.innerText = cntPedir;
  if (elCntAgot) elCntAgot.innerText = cntAgotados;
  if (elCntBajo) elCntBajo.innerText = cntBajoMin;
  if (elCntOpt) elCntOpt.innerText = cntOptimo;
  if (elCntSobre) elCntSobre.innerText = cntSobrestock;

  // 3. Métricas de KPIs
  const totDisp = filtered.reduce((sum, i) => sum + (i.a_la_mano ?? i.stock_actual ?? 0), 0);
  const totValor = filtered.reduce((sum, i) => sum + (i.valor_estimado || 0), 0);
  const totVentasMes = filtered.reduce((sum, i) => sum + (i.venta_mensual_est || 0), 0);
  const totPedir = filtered.reduce((sum, i) => sum + (i.sugerido_pedir || 0), 0);
  const totInvReorden = filtered.reduce((sum, i) => sum + (i.inversion_reorden || 0), 0);

  const elDisp = document.getElementById('kpi-stock-disp');
  const elSubDisp = document.getElementById('kpi-stock-sub-disp');
  const elVentasMes = document.getElementById('kpi-stock-ventas-mes') || document.getElementById('kpi-stock-ventas');
  const elPedir = document.getElementById('kpi-stock-pedir') || document.getElementById('kpi-stock-reordenar');
  const elInvReorden = document.getElementById('kpi-stock-inv-reorden');
  const elValor = document.getElementById('kpi-stock-valor');
  const elAlertasCount = document.getElementById('kpi-stock-alertas-count');

  if (elDisp) elDisp.innerText = fmtNum(totDisp);
  if (elSubDisp) elSubDisp.innerText = `En ${filtered.length} productos`;
  if (elVentasMes) elVentasMes.innerText = `${fmtNum(totVentasMes)} uds/mes`;
  if (elPedir) elPedir.innerText = `${fmtNum(totPedir)} uds`;
  if (elInvReorden) elInvReorden.innerText = fmtMxn(totInvReorden);
  if (elValor) elValor.innerText = fmtMxn(totValor);
  if (elAlertasCount) elAlertasCount.innerText = `${cntPedir} códigos en alerta`;

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="12" class="p-8 text-center text-slate-500 font-medium">
          <i class="fa-solid fa-folder-open text-2xl mb-2 block text-slate-600"></i>
          No hay productos que coincidan con la búsqueda, categoría o filtro de estado seleccionado.
        </td>
      </tr>
    `;
    return;
  }

  // Ordenar: primero los que tienen faltante a pedir > 0
  filtered.sort((a, b) => {
    if ((a.sugerido_pedir > 0) !== (b.sugerido_pedir > 0)) {
      return a.sugerido_pedir > 0 ? -1 : 1;
    }
    if (a.sugerido_pedir !== b.sugerido_pedir) {
      return b.sugerido_pedir - a.sugerido_pedir;
    }
    return (b.a_la_mano ?? b.stock_actual ?? 0) - (a.a_la_mano ?? a.stock_actual ?? 0);
  });

  filtered.forEach((item, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/50 transition-colors group cursor-pointer';
    tr.title = 'Haz doble clic para ver existencias de este producto en todos los almacenes';
    tr.ondblclick = () => abrirModalStockDetalleProducto(item.nombre_limpio || item.producto);

    let badgeClass = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    let labelEstado = '🟢 Óptimo';
    if (item.estado === 'REORDENAR') { badgeClass = 'bg-amber-500/10 text-amber-400 border-amber-500/30'; labelEstado = '🟡 Bajo Mínimo'; }
    else if (item.estado === 'AGOTADO') { badgeClass = 'bg-red-500/10 text-red-400 border-red-500/30'; labelEstado = '🔴 AGOTADO'; }
    else if (item.estado === 'SIN_MOVIMIENTO') { badgeClass = 'bg-slate-500/10 text-slate-400 border-slate-500/20'; labelEstado = '⚪ Sin Movimiento'; }
    else if (item.estado === 'SOBRESTOCK') { badgeClass = 'bg-purple-500/10 text-purple-400 border-purple-500/20'; labelEstado = '🟣 Sobrestock'; }

    let catBadgeClass = 'bg-slate-800 text-slate-300';
    if (item.clasificacion === 'MATERIA PRIMA') {
      catBadgeClass = 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
    } else if (item.clasificacion === 'PASTA') {
      catBadgeClass = 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
    } else if (item.clasificacion === 'CHALLENGER') {
      catBadgeClass = 'bg-blue-500/20 text-blue-300 border border-blue-500/30';
    }

    const cobStr = item.dias_cobertura >= 900 ? '∞' : `${item.dias_cobertura.toFixed(0)}d`;

    // Badge Reorden a Pedir
    let reordenCell = '';
    if (item.sugerido_pedir > 0) {
      reordenCell = `<span class="px-2 py-0.5 rounded-lg bg-rose-500/20 text-rose-300 font-extrabold border border-rose-500/40 text-[11px] inline-flex items-center shadow-sm">
        <i class="fa-solid fa-cart-shopping mr-1 text-[10px]"></i> +${fmtNum(item.sugerido_pedir)}
      </span>`;
    } else {
      reordenCell = `<span class="text-emerald-400/80 font-semibold text-[11px] inline-flex items-center">
        <i class="fa-solid fa-check mr-1 text-[10px]"></i> 0 (Cubierto)
      </span>`;
    }

    tr.innerHTML = `
      <td class="p-3 text-center text-slate-500 font-bold">${idx + 1}</td>
      <td class="p-3 font-semibold text-white group-hover:text-blue-300 transition-colors">
        <div class="flex items-center justify-between">
          <span class="truncate max-w-xs" title="${item.producto}">${item.producto}</span>
          <button onclick="event.stopPropagation(); abrirModalStockDetalleProducto('${encodeURIComponent(item.nombre_limpio || item.producto)}')" class="opacity-0 group-hover:opacity-100 text-[10px] px-1.5 py-0.5 rounded bg-blue-600/30 hover:bg-blue-600 text-blue-200 hover:text-white transition-all ml-2 flex-shrink-0" title="Ver existencias en todos los almacenes">
            <i class="fa-solid fa-warehouse"></i>
          </button>
        </div>
      </td>
      <td class="p-3 text-slate-400 truncate max-w-[140px]" title="${item.almacen}">${item.almacen}</td>
      <td class="p-3 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${catBadgeClass}">${item.clasificacion}</span></td>
      <td class="p-3 text-right font-black text-white font-mono bg-blue-500/5 border-x border-slate-800/40">${fmtNum(item.a_la_mano ?? item.stock_actual)}</td>
      <td class="p-3 text-right font-bold text-purple-300 font-mono">${fmtNum(item.venta_mensual_est)}</td>
      <td class="p-3 text-center font-bold text-amber-300 font-mono bg-amber-500/5">${fmtNum(item.stock_minimo)}</td>
      <td class="p-3 text-center font-bold text-blue-300 font-mono bg-blue-500/5">${fmtNum(item.stock_sugerido_mes)}</td>
      <td class="p-3 text-center bg-rose-500/5">${reordenCell}</td>
      <td class="p-3 text-center text-slate-300 font-mono text-[11px]">${cobStr}</td>
      <td class="p-3 text-center"><span class="px-2 py-0.5 rounded-full border text-[10px] font-bold ${badgeClass}">${labelEstado}</span></td>
      <td class="p-3 text-center">
        <button onclick="event.stopPropagation(); abrirModalStockDetalleProducto('${encodeURIComponent(item.nombre_limpio || item.producto)}')" class="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors" title="Ver desglose por cada almacén">
          <i class="fa-solid fa-table-cells"></i>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ── MODAL DESGLOSE MULTI-ALMACÉN DE UN PRODUCTO ─────────────────────────────
function abrirModalStockDetalleProducto(productoCodificado) {
  const productoBuscado = decodeURIComponent(productoCodificado);
  const normBuscado = normalizarTexto(productoBuscado);

  const matched = stockDataGlobal.filter(i => {
    const p1 = normalizarTexto(i.producto);
    const p2 = normalizarTexto(i.nombre_limpio);
    return p1 === normBuscado || p2 === normBuscado || p1.includes(normBuscado) || normBuscado.includes(p1);
  });

  if (matched.length === 0) {
    alert(`No se encontraron registros de almacén para: ${productoBuscado}`);
    return;
  }

  const primer = matched[0];
  const nomEl = document.getElementById('modal-stock-prod-nombre');
  const subEl = document.getElementById('modal-stock-prod-sub');
  if (nomEl) nomEl.innerText = primer.producto;
  if (subEl) subEl.innerText = `Categoría: ${primer.clasificacion} | Monitoreado en ${matched.length} almacenes`;

  // Calcular totales cadena
  const totDisp = matched.reduce((sum, i) => sum + (i.disponible || 0), 0);
  const totVmes = matched.reduce((sum, i) => sum + (i.venta_mensual_est || 0), 0);
  const totSug = matched.reduce((sum, i) => sum + (i.stock_sugerido_mes || 0), 0);
  const totPedir = matched.reduce((sum, i) => sum + (i.sugerido_pedir || 0), 0);

  const elD = document.getElementById('modal-stock-total-disp');
  const elV = document.getElementById('modal-stock-total-vmes');
  const elS = document.getElementById('modal-stock-total-sug');
  const elP = document.getElementById('modal-stock-total-pedir');

  if (elD) elD.innerText = `${fmtNum(totDisp)} uds`;
  if (elV) elV.innerText = `${fmtNum(totVmes)} uds/mes`;
  if (elS) elS.innerText = `${fmtNum(totSug)} uds`;
  if (elP) elP.innerText = `${fmtNum(totPedir)} uds`;

  // Renderizar tabla de almacenes
  const tbody = document.getElementById('modal-tbody-stock-almacenes');
  if (tbody) {
    tbody.innerHTML = '';
    matched.sort((a, b) => (b.sugerido_pedir - a.sugerido_pedir) || (b.disponible - a.disponible));

    matched.forEach(item => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-900 transition-colors';

      let bClass = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      let bTxt = '🟢 Óptimo';
      if (item.estado === 'REORDENAR') { bClass = 'bg-amber-500/20 text-amber-300 border-amber-500/30'; bTxt = '🟡 Bajo Mínimo'; }
      if (item.estado === 'AGOTADO') { bClass = 'bg-red-500/20 text-red-300 border-red-500/30'; bTxt = '🔴 AGOTADO'; }
      if (item.estado === 'SOBRESTOCK') { bClass = 'bg-purple-500/20 text-purple-300 border-purple-500/30'; bTxt = '🟣 Sobrestock'; }
      if (item.estado === 'SIN_MOVIMIENTO') { bClass = 'bg-slate-500/20 text-slate-400 border-slate-500/30'; bTxt = '⚪ Sin Venta'; }

      let pedirBadge = item.sugerido_pedir > 0
        ? `<span class="px-2 py-0.5 rounded-lg bg-rose-500/20 text-rose-300 font-bold border border-rose-500/40 text-[11px]">+${fmtNum(item.sugerido_pedir)} uds</span>`
        : `<span class="text-emerald-400 font-medium text-[11px]">0 (OK)</span>`;

      tr.innerHTML = `
        <td class="p-3 font-semibold text-white">${item.almacen}</td>
        <td class="p-3 text-right text-slate-300">${fmtNum(item.stock_actual)}</td>
        <td class="p-3 text-right text-slate-400">${fmtNum(item.reservado)}</td>
        <td class="p-3 text-right font-black text-blue-400">${fmtNum(item.disponible)}</td>
        <td class="p-3 text-center font-bold text-amber-300">${fmtNum(item.stock_minimo)}</td>
        <td class="p-3 text-center font-bold text-blue-300">${fmtNum(item.stock_sugerido_mes)}</td>
        <td class="p-3 text-center">${pedirBadge}</td>
        <td class="p-3 text-center"><span class="px-2 py-0.5 rounded-full border text-[10px] font-bold ${bClass}">${bTxt}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  document.getElementById('modal-stock-detalle-producto')?.classList.remove('hidden');
}

function cerrarModalStockDetalleProducto() {
  document.getElementById('modal-stock-detalle-producto')?.classList.add('hidden');
}


// ── MÓDULO 2: TOP PRODUCTOS ─────────────────────────────────────────────────
async function loadProductosData() {
  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  const anio = document.getElementById('prod-anio')?.value || '2026';
  const mes = document.getElementById('prod-mes')?.value || 'TODOS';

  let fecha_ini = `${anio}-01-01`;
  let fecha_fin = `${anio}-12-31`;

  if (mes !== "0" && mes !== "TODOS" && mes !== "") {
    const m = String(mes).padStart(2, '0');
    const max_d = new Date(parseInt(anio), parseInt(mes), 0).getDate();
    fecha_ini = `${anio}-${m}-01`;
    fecha_fin = `${anio}-${m}-${max_d}`;
  }

  const tbody = document.getElementById('tbody-productos');
  if (tbody && productosDataGlobal.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="p-8 text-center text-purple-400 font-medium">
          <i class="fa-solid fa-spinner fa-spin text-2xl mb-2 block"></i>
          Calculando ranking de productos más vendidos...
        </td>
      </tr>
    `;
  }

  showLoading('Consultando Top Productos...', 'Analizando ranking de ventas y líneas comerciales...');

  try {
    const res = await fetch('/api/productos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ empresa_nombre: empresa, fecha_inicio: fecha_ini, fecha_fin: fecha_fin, excluir_interempresa: true })
    });
    const data = await res.json();
    if (data.success && data.data) {
      productosDataGlobal = data.data.productos || [];
      const tot = data.data.totales || {};

      document.getElementById('kpi-prod-monto').innerText = fmtMxn(tot.monto);
      document.getElementById('kpi-prod-cant').innerText = fmtNum(tot.cantidad);
      document.getElementById('kpi-prod-top').innerText = productosDataGlobal[0] ? productosDataGlobal[0].nombre_limpio : '-';
      document.getElementById('kpi-prod-variedad').innerText = tot.variedad || 0;

      renderProductosTable();
      renderTopProductosChart();
      hideLoading('¡Top Productos Listo!', `${productosDataGlobal.length} productos calculados.`);
    } else {
      hideLoading('⚠️ Sin Datos', 'No se encontraron registros de ventas.');
    }
  } catch (err) {
    console.error('Error productos:', err);
    hideLoading('⚠️ Error de Productos', 'No se pudieron obtener productos.');
  }
}

let sortProdColumn = 'subtotal';
let sortProdAsc = false;

function sortProductosTable(col) {
  if (sortProdColumn === col) {
    sortProdAsc = !sortProdAsc;
  } else {
    sortProdColumn = col;
    sortProdAsc = (col === 'nombre' || col === 'clasificacion') ? true : false;
  }
  updateSortIconsProductos();
  renderProductosTable();
}

function updateSortIconsProductos() {
  const cols = ['posicion', 'nombre', 'clasificacion', 'cantidad', 'subtotal', 'num_clientes', 'num_facturas', 'pct_monto'];
  cols.forEach(c => {
    const icon = document.getElementById(`sort-icon-prod-${c}`);
    if (!icon) return;
    if (sortProdColumn === c) {
      icon.className = `fa-solid ${sortProdAsc ? 'fa-arrow-up-wide-short text-blue-400' : 'fa-arrow-down-wide-short text-blue-400'} ml-1.5 transition-transform text-[10px]`;
    } else {
      icon.className = 'fa-solid fa-sort ml-1.5 text-slate-600 group-hover:text-slate-400 text-[10px]';
    }
  });
}

function renderProductosTable() {
  const tbody = document.getElementById('tbody-productos');
  const searchInput = document.getElementById('search-productos')?.value || '';
  const search = normalizarTexto(searchInput);
  const marca = document.getElementById('prod-marca')?.value || 'TODAS';

  tbody.innerHTML = '';

  let filtered = productosDataGlobal.filter(p => {
    if (search && !normalizarTexto(p.nombre).includes(search) && !normalizarTexto(p.clasificacion || '').includes(search)) return false;
    if (marca !== 'TODAS' && p.clasificacion !== marca) return false;
    return true;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" class="p-8 text-center text-slate-500">No se encontraron productos con los filtros seleccionados.</td></tr>';
    return;
  }

  // Ordenamiento dinámico
  filtered.sort((a, b) => {
    let valA = a[sortProdColumn];
    let valB = b[sortProdColumn];

    if (sortProdColumn === 'num_clientes') {
      valA = a.num_clientes !== undefined ? a.num_clientes : (a.clientes ? a.clientes.length : 0);
      valB = b.num_clientes !== undefined ? b.num_clientes : (b.clientes ? b.clientes.length : 0);
    }

    if (typeof valA === 'string') {
      const cmp = (valA || '').localeCompare(valB || '', 'es', { sensitivity: 'base' });
      return sortProdAsc ? cmp : -cmp;
    } else {
      valA = (valA !== null && valA !== undefined) ? Number(valA) : 0;
      valB = (valB !== null && valB !== undefined) ? Number(valB) : 0;
      return sortProdAsc ? (valA - valB) : (valB - valA);
    }
  });

  updateSortIconsProductos();

  filtered.forEach(p => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/60 cursor-pointer transition-colors group';
    tr.title = '💡 Haz clic para ver a qué clientes y qué facturas corresponden las ventas de este producto';
    tr.onclick = () => abrirModalVentasProducto(p.nombre);

    let catBadgeClass = 'bg-slate-800 text-slate-300';
    if (p.clasificacion === 'MATERIA PRIMA') {
      catBadgeClass = 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
    } else if (p.clasificacion === 'PASTA') {
      catBadgeClass = 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
    } else if (p.clasificacion === 'CHALLENGER') {
      catBadgeClass = 'bg-blue-500/20 text-blue-300 border border-blue-500/30';
    }

    const hasNc = p.subtotal_nc && p.subtotal_nc > 0;
    const ncBadge = hasNc ? `<span class="text-rose-400 text-[10px] block font-semibold">NC: -${fmtMxn(p.subtotal_nc)}</span>` : '';

    tr.innerHTML = `
      <td class="p-3 text-center font-bold text-slate-500">${p.posicion}</td>
      <td class="p-3 font-semibold text-white group-hover:text-blue-300 transition-colors">
        <div class="flex items-center space-x-2">
          <span>${p.nombre}</span>
          ${p.es_ajuste ? '<span class="px-1.5 py-0.5 rounded text-[9px] bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold">AJUSTE / NC</span>' : ''}
        </div>
      </td>
      <td class="p-3 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${catBadgeClass}">${p.clasificacion}</span></td>
      <td class="p-3 text-right font-medium text-emerald-400">
        ${fmtNum(p.cantidad)} <span class="text-[10px] text-slate-400 font-normal">${p.uom || 'uds'}</span>
      </td>
      <td class="p-3 text-right font-bold text-blue-400">
        ${fmtMxn(p.subtotal)}
        ${ncBadge}
      </td>
      <td class="p-3 text-center">
        <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-300 border border-purple-500/20">
          <i class="fa-solid fa-users text-[9px] mr-1"></i>${p.num_clientes || (p.clientes ? p.clientes.length : 0)}
        </span>
      </td>
      <td class="p-3 text-center font-mono text-slate-300">${p.num_facturas || 0}</td>
      <td class="p-3 text-right font-bold text-purple-400">${(p.pct_monto || 0).toFixed(2)}%</td>
      <td class="p-3 text-center">
        <button onclick="event.stopPropagation(); abrirModalVentasProducto('${encodeURIComponent(p.nombre)}')" class="px-2.5 py-1 rounded-xl bg-blue-600/30 hover:bg-blue-600 text-blue-200 hover:text-white text-[10px] font-bold transition-all shadow-sm flex items-center justify-center mx-auto">
          <i class="fa-solid fa-eye mr-1"></i> Ver Ventas
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderTopProductosChart() {
  const chartCanvas = document.getElementById('chart-top-productos');
  if (!chartCanvas) return;
  const ctx = chartCanvas.getContext('2d');
  const catalogOnly = productosDataGlobal.filter(p => !p.es_ajuste);
  const top10 = catalogOnly.slice(0, 10);

  const labels = top10.map(p => (p.nombre_limpio || p.nombre).slice(0, 24));
  const dataSub = top10.map(p => p.subtotal);

  if (chartTopProductos) chartTopProductos.destroy();

  chartTopProductos = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Ventas ($)',
        data: dataSub,
        backgroundColor: '#2563eb',
        borderRadius: 6
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => ` Subtotal: ${fmtMxn(context.raw)}`
          }
        }
      },
      scales: {
        x: { ticks: { color: '#94a3b8', callback: (v) => fmtMxn(v) }, grid: { color: '#1e293b' } },
        y: { ticks: { color: '#cbd5e1', font: { weight: 'bold' } }, grid: { display: false } }
      }
    }
  });
}

// ── MODAL TRAZABILIDAD Y DETALLE DE VENTAS POR PRODUCTO ──────────────────────
let prodVentasModalActual = null;

function abrirModalVentasProducto(prodNameRaw) {
  const prodName = decodeURIComponent(prodNameRaw || '').trim();
  const pNorm = normalizarTexto(prodName);

  const p = productosDataGlobal.find(item => normalizarTexto(item.nombre) === pNorm || normalizarTexto(item.nombre_limpio || '') === pNorm)
    || productosDataGlobal.find(item => normalizarTexto(item.nombre).includes(pNorm) || pNorm.includes(normalizarTexto(item.nombre)));

  if (!p) {
    showToast('⚠️ No se encontró el detalle de este producto.');
    return;
  }

  prodVentasModalActual = p;

  // Header & info
  document.getElementById('modal-pv-nombre').innerText = p.nombre;
  const catEl = document.getElementById('modal-pv-cat');
  if (catEl) {
    catEl.innerText = p.clasificacion || 'GENERAL';
    catEl.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-extrabold border ' +
      (p.clasificacion === 'PASTA' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' :
      (p.clasificacion === 'MATERIA PRIMA' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : 'bg-blue-500/20 text-blue-300 border-blue-500/30'));
  }

  // KPIs
  document.getElementById('modal-pv-monto-bruto').innerText = fmtMxn(p.subtotal || 0);
  document.getElementById('modal-pv-monto-neto').innerText = fmtMxn(p.subtotal_neto !== undefined ? p.subtotal_neto : p.subtotal);
  document.getElementById('modal-pv-cant-neta').innerText = `${fmtNum(p.cantidad_neta !== undefined ? p.cantidad_neta : p.cantidad)} ${p.uom || 'uds'}`;
  document.getElementById('modal-pv-num-clientes').innerText = p.num_clientes || (p.clientes ? p.clientes.length : 0);
  document.getElementById('modal-pv-num-facturas').innerText = p.num_facturas || 0;
  document.getElementById('modal-pv-num-ncs').innerText = p.num_ncs ? `${p.num_ncs} (-${fmtMxn(p.subtotal_nc)})` : (p.subtotal_nc ? `-${fmtMxn(p.subtotal_nc)}` : '0');

  // Top Clientes
  const contClientes = document.getElementById('modal-pv-lista-clientes');
  const clientes = p.clientes || [];
  document.getElementById('modal-pv-count-clientes-badge').innerText = `${clientes.length} clientes compradores`;
  if (clientes.length === 0) {
    contClientes.innerHTML = '<p class="text-slate-500 text-center py-2">Sin clientes registrados</p>';
  } else {
    contClientes.innerHTML = clientes.map((c, idx) => {
      const pctCli = p.subtotal > 0 ? ((c.subtotal / p.subtotal) * 100).toFixed(1) : 0;
      return `
        <div class="p-2 rounded-xl bg-slate-900/80 border border-slate-800/80 flex items-center justify-between hover:bg-slate-850 transition-colors">
          <div class="flex items-center space-x-2 truncate">
            <span class="w-5 h-5 rounded-lg bg-purple-950 text-purple-400 flex items-center justify-center font-bold text-[10px] shrink-0">${idx + 1}</span>
            <span class="font-bold text-white text-xs truncate" title="${c.cliente}">${c.cliente}</span>
          </div>
          <div class="text-right shrink-0 ml-2">
            <span class="font-black text-emerald-400 text-xs block">${fmtMxn(c.subtotal)}</span>
            <span class="text-[10px] text-slate-400">${fmtNum(c.cantidad)} uds · ${pctCli}%</span>
          </div>
        </div>
      `;
    }).join('');
  }

  // Asesores Comerciales
  const contVendedores = document.getElementById('modal-pv-lista-vendedores');
  const vendedores = p.vendedores || [];
  document.getElementById('modal-pv-count-vendedores-badge').innerText = `${vendedores.length} asesores`;
  if (vendedores.length === 0) {
    contVendedores.innerHTML = '<p class="text-slate-500 text-center py-2">Sin asesores registrados</p>';
  } else {
    contVendedores.innerHTML = vendedores.map((v, idx) => {
      const pctVend = p.subtotal > 0 ? ((v.subtotal / p.subtotal) * 100).toFixed(1) : 0;
      return `
        <div class="p-2 rounded-xl bg-slate-900/80 border border-slate-800/80 flex items-center justify-between hover:bg-slate-850 transition-colors">
          <div class="flex items-center space-x-2 truncate">
            <span class="w-5 h-5 rounded-lg bg-blue-950 text-blue-400 flex items-center justify-center font-bold text-[10px] shrink-0">${idx + 1}</span>
            <span class="font-bold text-white text-xs truncate" title="${v.vendedor}">${v.vendedor}</span>
          </div>
          <div class="text-right shrink-0 ml-2">
            <span class="font-black text-blue-400 text-xs block">${fmtMxn(v.subtotal)}</span>
            <span class="text-[10px] text-slate-400">${fmtNum(v.cantidad)} uds · ${pctVend}%</span>
          </div>
        </div>
      `;
    }).join('');
  }

  // Reset filters
  const searchEl = document.getElementById('search-modal-pv-lineas');
  if (searchEl) searchEl.value = '';
  const tipoEl = document.getElementById('filtro-modal-pv-tipo');
  if (tipoEl) tipoEl.value = 'TODOS';

  filtrarLineasModalVentas();

  // Show modal
  const modal = document.getElementById('modal-detalle-ventas-producto');
  if (modal) modal.classList.remove('hidden');
}

function cerrarModalVentasProducto() {
  const modal = document.getElementById('modal-detalle-ventas-producto');
  if (modal) modal.classList.add('hidden');
}

let sortModalLineasColumn = 'fecha';
let sortModalLineasAsc = false;

function sortModalVentasLineas(col) {
  if (sortModalLineasColumn === col) {
    sortModalLineasAsc = !sortModalLineasAsc;
  } else {
    sortModalLineasColumn = col;
    sortModalLineasAsc = (col === 'cliente' || col === 'factura' || col === 'vendedor' || col === 'empresa') ? true : false;
  }
  updateSortIconsModalVentas();
  filtrarLineasModalVentas();
}

function updateSortIconsModalVentas() {
  const cols = ['factura', 'fecha', 'cliente', 'vendedor', 'empresa', 'cantidad', 'precio_unitario', 'subtotal'];
  cols.forEach(c => {
    const icon = document.getElementById(`sort-icon-mpv-${c}`);
    if (!icon) return;
    if (sortModalLineasColumn === c) {
      icon.className = `fa-solid ${sortModalLineasAsc ? 'fa-arrow-up-wide-short text-emerald-400' : 'fa-arrow-down-wide-short text-emerald-400'} ml-1.5 text-[10px]`;
    } else {
      icon.className = 'fa-solid fa-sort ml-1.5 text-slate-600 group-hover:text-slate-400 text-[10px]';
    }
  });
}

function filtrarLineasModalVentas() {
  if (!prodVentasModalActual) return;
  const searchInput = document.getElementById('search-modal-pv-lineas')?.value || '';
  const search = normalizarTexto(searchInput);
  const tipoFiltro = document.getElementById('filtro-modal-pv-tipo')?.value || 'TODOS';

  let filtered = [...(prodVentasModalActual.lineas || [])];

  if (tipoFiltro === 'FACTURA') {
    filtered = filtered.filter(l => !l.es_nc && l.tipo_doc !== 'Nota de Crédito');
  } else if (tipoFiltro === 'NC') {
    filtered = filtered.filter(l => l.es_nc || l.tipo_doc === 'Nota de Crédito');
  }

  if (search) {
    filtered = filtered.filter(l =>
      normalizarTexto(l.cliente || '').includes(search) ||
      normalizarTexto(l.factura || '').includes(search) ||
      normalizarTexto(l.vendedor || '').includes(search) ||
      normalizarTexto(l.empresa || '').includes(search)
    );
  }

  // Ordenamiento de líneas del modal
  filtered.sort((a, b) => {
    let valA = a[sortModalLineasColumn];
    let valB = b[sortModalLineasColumn];

    if (typeof valA === 'string') {
      const cmp = (valA || '').localeCompare(valB || '', 'es', { sensitivity: 'base' });
      return sortModalLineasAsc ? cmp : -cmp;
    } else {
      valA = (valA !== null && valA !== undefined) ? Number(valA) : 0;
      valB = (valB !== null && valB !== undefined) ? Number(valB) : 0;
      return sortModalLineasAsc ? (valA - valB) : (valB - valA);
    }
  });

  updateSortIconsModalVentas();

  const tbody = document.getElementById('tbody-modal-pv-lineas');
  if (!tbody) return;

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" class="p-6 text-center text-slate-500">No se encontraron líneas de venta con los filtros indicados.</td></tr>';
  } else {
    tbody.innerHTML = filtered.map((l, idx) => {
      const isNc = l.es_nc || l.tipo_doc === 'Nota de Crédito' || (l.subtotal < 0);
      const badgeDoc = isNc
        ? '<span class="px-1.5 py-0.5 rounded text-[9px] font-black bg-rose-500/20 text-rose-300 border border-rose-500/30">NC / DEV</span>'
        : '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">FAC</span>';

      const rowClass = isNc ? 'bg-rose-950/10 hover:bg-rose-950/20' : 'hover:bg-slate-800/40';
      const subClass = isNc ? 'text-rose-400 font-black' : 'text-emerald-400 font-bold';

      return `
        <tr class="${rowClass} transition-colors">
          <td class="p-2.5 text-center text-slate-500 font-bold">${idx + 1}</td>
          <td class="p-2.5 font-mono font-bold text-white flex items-center space-x-1.5">
            ${badgeDoc}
            <span>${l.factura}</span>
          </td>
          <td class="p-2.5 text-center text-slate-400">${l.fecha || '-'}</td>
          <td class="p-2.5 font-bold text-slate-100 max-w-xs truncate" title="${l.cliente}">${l.cliente}</td>
          <td class="p-2.5 text-slate-300 truncate max-w-[150px]" title="${l.vendedor}">
            <i class="fa-solid fa-user-tie text-[10px] text-slate-500 mr-1"></i>${l.vendedor}
          </td>
          <td class="p-2.5 text-center">
            <span class="text-[10px] font-semibold text-slate-400">${l.empresa || 'Baldomero'}</span>
          </td>
          <td class="p-2.5 text-right font-medium text-slate-200">${fmtNum(l.cantidad)} ${l.uom || ''}</td>
          <td class="p-2.5 text-right text-slate-400 font-mono">${fmtMxn(l.precio_unitario)}</td>
          <td class="p-2.5 text-right ${subClass} font-mono">${fmtMxn(l.subtotal)}</td>
        </tr>
      `;
    }).join('');
  }

  // Footer totals
  const totSubFiltered = filtered.reduce((sum, l) => sum + (l.subtotal || 0), 0);
  document.getElementById('modal-pv-footer-count').innerText = `${filtered.length} líneas`;
  document.getElementById('modal-pv-footer-subtotal').innerText = fmtMxn(totSubFiltered);
}

function exportarVentasProductoModalExcel() {
  if (!prodVentasModalActual || !prodVentasModalActual.lineas || prodVentasModalActual.lineas.length === 0) {
    showToast('⚠️ No hay líneas de venta para exportar.');
    return;
  }

  const lineas = prodVentasModalActual.lineas;
  const headers = ['#', 'Folio / Factura', 'Tipo Doc', 'Fecha', 'Cliente / Razon Social', 'Asesor Comercial', 'Empresa', 'Cantidad', 'Unidad', 'Precio Unitario ($)', 'Subtotal ($)'];
  const rows = lineas.map((l, i) => [
    i + 1,
    `"${l.factura || ''}"`,
    `"${l.tipo_doc || 'Factura'}"`,
    `"${l.fecha || ''}"`,
    `"${(l.cliente || '').replace(/"/g, '""')}"`,
    `"${(l.vendedor || '').replace(/"/g, '""')}"`,
    `"${(l.empresa || '').replace(/"/g, '""')}"`,
    l.cantidad || 0,
    `"${l.uom || ''}"`,
    l.precio_unitario || 0,
    l.subtotal || 0
  ]);

  let csvContent = '\uFEFF' + headers.join(',') + '\n' + rows.map(r => r.join(',')).join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const safeName = (prodVentasModalActual.nombre || 'Producto').replace(/[^a-zA-Z0-9]/g, '_');
  a.download = `Ventas_Detalladas_${safeName}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showToast('✅ Detalle de ventas exportado exitosamente a CSV.');
}

// ── VISTAS SUB-TABS TOP PRODUCTOS & MACHINE LEARNING ────────────────────────
let mlDataGlobal = null;
let currentProdView = 'ranking';
let mlLoadingPromise = null;

function switchProdView(view) {
  currentProdView = view;

  ['ranking', 'ml', 'historico'].forEach(v => {
    const el = document.getElementById(`view-prod-${v}`);
    if (el) el.classList.add('hidden');
    const btn = document.getElementById(`btn-subtab-prod-${v}`);
    if (btn) {
      btn.className = 'px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white transition-all';
    }
  });

  const activeView = document.getElementById(`view-prod-${view}`);
  if (activeView) activeView.classList.remove('hidden');

  const activeBtn = document.getElementById(`btn-subtab-prod-${view}`);
  if (activeBtn) {
    if (view === 'ml') {
      activeBtn.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-purple-600 to-blue-600 text-white transition-all shadow-md shadow-purple-600/20';
    } else {
      activeBtn.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 text-white transition-all shadow-md shadow-blue-600/20';
    }
  }

  if (view === 'ml' || view === 'historico') {
    if (!mlDataGlobal) {
      loadTop20HistoricoML();
    } else {
      if (view === 'ml') renderMLPredictionsTable();
      if (view === 'historico') renderHistoricoTop20Table();
    }
  }
}

async function loadTop20HistoricoML() {
  if (mlLoadingPromise) return mlLoadingPromise;

  const tbodyMl = document.getElementById('tbody-prod-ml');
  const tbodyHist = document.getElementById('tbody-prod-historico');
  if (tbodyMl && (!mlDataGlobal || !mlDataGlobal.predicciones_ml || mlDataGlobal.predicciones_ml.length === 0)) {
    tbodyMl.innerHTML = '<tr><td colspan="10" class="p-8 text-center text-purple-400 font-medium"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Generando pronóstico de Machine Learning para todo el catálogo...</td></tr>';
  }
  if (tbodyHist && (!mlDataGlobal || !mlDataGlobal.matriz_historica || mlDataGlobal.matriz_historica.length === 0)) {
    tbodyHist.innerHTML = '<tr><td colspan="15" class="p-8 text-center text-blue-400 font-medium"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Calculando matriz histórica multi-mes para 295 productos...</td></tr>';
  }

  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  const btnMl = document.getElementById('ml-engine-badge');
  if (btnMl) btnMl.innerText = '⚡ Entrenando Modelo XGBoost en tiempo real...';

  showLoading('Entrenando Inteligencia Artificial...', 'Ejecutando modelo predictivo XGBoost para demanda y buffer...');

  mlLoadingPromise = (async () => {
    try {
      const res = await fetch('/api/productos/historico_ml', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ empresa_nombre: empresa, excluir_interempresa: true })
      });
      const data = await res.json();
      if (data.success && data.data) {
        mlDataGlobal = data.data;

        if (btnMl) btnMl.innerText = mlDataGlobal.ml_engine || 'XGBoost Regressor (Gradient Boosting v3.4)';

        // KPIs de ML (Top 20 Productos)
        const preds = mlDataGlobal.predicciones_ml || [];
        const top20Preds = preds.slice(0, 20);
        const totUnidadesPred = top20Preds.reduce((sum, p) => sum + (p.pred_unidades || 0), 0);
        const totIngresoPred = top20Preds.reduce((sum, p) => sum + (p.pred_ingreso || 0), 0);
        const totBuffer = top20Preds.reduce((sum, p) => sum + (p.stock_sugerido || 0), 0);
        const confAvg = top20Preds.length > 0 ? (top20Preds.reduce((sum, p) => sum + (p.confianza_score || 0), 0) / top20Preds.length) : 0;

        const elU = document.getElementById('kpi-ml-unidades');
        const elI = document.getElementById('kpi-ml-ingreso');
        const elB = document.getElementById('kpi-ml-buffer');
        const elC = document.getElementById('kpi-ml-confianza');
        if (elU) elU.innerText = `${fmtNum(totUnidadesPred)} uds`;
        if (elI) elI.innerText = fmtMxn(totIngresoPred);
        if (elB) elB.innerText = `${fmtNum(totBuffer)} uds`;
        if (elC) elC.innerText = `${confAvg.toFixed(1)}%`;

        // Métricas de Ajustes para el Modal
        const metAjustes = mlDataGlobal.metricas_ajuste || {};
        const elDesc = document.getElementById('modal-ajustes-desc');
        const elPct = document.getElementById('modal-ajustes-pct');
        if (elDesc) elDesc.innerText = fmtMxn(metAjustes.total_descuentos_otorgados || 0);
        if (elPct) elPct.innerText = `${(metAjustes.pct_descuento_promedio || 0).toFixed(2)}%`;

        renderMLPredictionsTable();
        renderHistoricoTop20Table();
        hideLoading('¡IA Lista!', 'Pronósticos y sugerencias de compra calculadas.');
      } else {
        hideLoading('⚠️ Sin Datos IA', 'No se pudieron generar predicciones.');
      }
    } catch (err) {
      console.error('Error ML:', err);
      hideLoading('⚠️ Error Modelo IA', 'Error al ejecutar Machine Learning.');
    } finally {
      mlLoadingPromise = null;
    }
  })();

  return mlLoadingPromise;
}

function renderMLPredictionsTable() {
  const tbody = document.getElementById('tbody-prod-ml');
  if (!tbody || !mlDataGlobal) return;

  const mesPron = mlDataGlobal.mes_pronosticado || 'Próximo Mes';
  const elBadge = document.getElementById('ml-engine-badge');
  if (elBadge) {
    elBadge.innerText = `${mlDataGlobal.ml_engine || 'XGBoost'} — Pronóstico para ${mesPron}`;
  }

  tbody.innerHTML = '';
  let preds = mlDataGlobal.predicciones_ml || [];

  // Filtros
  const search = normalizarTexto(document.getElementById('search-prod-ml')?.value || '');
  const catFilter = document.getElementById('filter-ml-cat')?.value || 'TODAS';
  const limitVal = document.getElementById('limit-ml')?.value || 'ALL';

  if (search) {
    preds = preds.filter(p => normalizarTexto(p.producto).includes(search) || normalizarTexto(p.explicacion_ia || '').includes(search));
  }
  if (catFilter !== 'TODAS') {
    preds = preds.filter(p => p.categoria === catFilter);
  }
  if (limitVal !== 'ALL') {
    const lim = parseInt(limitVal, 10);
    preds = preds.slice(0, lim);
  }

  if (preds.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10" class="p-8 text-center text-slate-500 font-medium">
          No se encontraron productos con los filtros seleccionados.
        </td>
      </tr>
    `;
    return;
  }

  preds.forEach(p => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/50 transition-colors group';
    tr.title = `${p.producto}: ${p.explicacion_ia || ''}`;

    let catBadgeClass = 'bg-slate-800 text-slate-300';
    if (p.categoria === 'MATERIA PRIMA') catBadgeClass = 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
    else if (p.categoria === 'PASTA') catBadgeClass = 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
    else if (p.categoria === 'CHALLENGER') catBadgeClass = 'bg-blue-500/20 text-blue-300 border border-blue-500/30';

    let flagBadge = 'bg-slate-500/10 text-slate-300 border-slate-500/20';
    if (p.tendencia_color === 'emerald') flagBadge = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    else if (p.tendencia_color === 'blue') flagBadge = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    else if (p.tendencia_color === 'amber') flagBadge = 'bg-amber-500/10 text-amber-400 border-amber-500/20';

    tr.innerHTML = `
      <td class="p-3 text-center font-bold text-slate-500">${p.ranking}</td>
      <td class="p-3 font-semibold text-white">
        <div>${p.producto}</div>
        <div class="text-[10px] text-slate-400 font-normal italic mt-0.5 group-hover:text-slate-200">${p.explicacion_ia}</div>
      </td>
      <td class="p-3 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${catBadgeClass}">${p.categoria}</span></td>
      <td class="p-3 text-right text-slate-300 font-medium">${fmtNum(p.ult_mes_unidades)}</td>
      <td class="p-3 text-right text-slate-400 font-mono">${fmtNum(p.promedio_mensual)}</td>
      <td class="p-3 text-right font-black text-purple-300 bg-purple-500/10">
        <div>${fmtNum(p.pred_unidades)} uds</div>
        <div class="text-[9px] text-purple-400/80 font-mono">${p.cambio_esperado_pct >= 0 ? '+' : ''}${p.cambio_esperado_pct}% vs mes ant.</div>
      </td>
      <td class="p-3 text-right font-black text-emerald-400">${fmtMxn(p.pred_ingreso)}</td>
      <td class="p-3 text-center font-bold text-blue-400 bg-blue-500/10" title="Buffer con +25% de seguridad sugerido para almacén">${fmtNum(p.stock_sugerido)} uds</td>
      <td class="p-3 text-center"><span class="px-2.5 py-1 rounded-full border text-[10px] font-bold ${flagBadge}">${p.tendencia_flag}</span></td>
      <td class="p-3 text-center font-mono font-bold text-slate-300">${p.confianza_score}%</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderHistoricoTop20Table() {
  const thead = document.getElementById('thead-prod-historico');
  const tbody = document.getElementById('tbody-prod-historico');
  if (!thead || !tbody || !mlDataGlobal) return;

  const periodos = mlDataGlobal.periodos_historico || [];
  let prods = mlDataGlobal.matriz_historica || mlDataGlobal.top20_historico || [];
  const totCatalogo = mlDataGlobal.total_catalogo || prods.length;

  // Filtros
  const search = normalizarTexto(document.getElementById('search-historico')?.value || '');
  const catFilter = document.getElementById('filter-historico-cat')?.value || 'TODAS';
  const limitVal = document.getElementById('limit-historico')?.value || 'ALL';

  if (search) {
    prods = prods.filter(p => normalizarTexto(p.producto).includes(search));
  }
  if (catFilter !== 'TODAS') {
    prods = prods.filter(p => p.categoria === catFilter);
  }
  if (limitVal !== 'ALL') {
    const lim = parseInt(limitVal, 10);
    prods = prods.slice(0, lim);
  }

  const lbl = document.getElementById('lbl-historico-meses');
  if (lbl) lbl.innerText = `Mostrando ${prods.length} de ${totCatalogo} productos (${periodos.length} meses)`;

  // Construir Encabezados
  let theadHTML = `
    <tr>
      <th class="p-3 text-center w-10">Pos</th>
      <th class="p-3">Producto / Código</th>
      <th class="p-3 text-center">Marca</th>
  `;
  periodos.forEach(per => {
    theadHTML += `<th class="p-3 text-right">${per} ($)</th>`;
  });
  theadHTML += `
      <th class="p-3 text-right font-bold text-blue-400">Total Histórico ($)</th>
      <th class="p-3 text-center">Crecimiento MoM</th>
    </tr>
  `;
  thead.innerHTML = theadHTML;

  // Construir Renglones
  tbody.innerHTML = '';
  if (prods.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="${periodos.length + 5}" class="p-8 text-center text-slate-500 font-medium">
          No se encontraron productos con los filtros seleccionados.
        </td>
      </tr>
    `;
    return;
  }

  prods.forEach(p => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/50 transition-colors';

    let catBadgeClass = 'bg-slate-800 text-slate-300';
    if (p.categoria === 'MATERIA PRIMA') catBadgeClass = 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
    else if (p.categoria === 'PASTA') catBadgeClass = 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
    else if (p.categoria === 'CHALLENGER') catBadgeClass = 'bg-blue-500/20 text-blue-300 border border-blue-500/30';

    let momBadge = 'text-slate-400';
    if (p.mom_growth > 0) momBadge = 'text-emerald-400 font-bold';
    else if (p.mom_growth < 0) momBadge = 'text-red-400 font-bold';

    let rowHTML = `
      <td class="p-3 text-center font-bold text-slate-500">${p.ranking}</td>
      <td class="p-3 font-semibold text-white truncate max-w-xs">${p.producto}</td>
      <td class="p-3 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${catBadgeClass}">${p.categoria}</span></td>
    `;

    periodos.forEach(per => {
      const dataMes = p.ventas_por_mes[per] || { subtotal: 0, cantidad: 0 };
      rowHTML += `<td class="p-3 text-right font-mono text-slate-300">${fmtMxn(dataMes.subtotal)}</td>`;
    });

    rowHTML += `
      <td class="p-3 text-right font-black text-blue-400 bg-blue-500/5">${fmtMxn(p.total_subtotal)}</td>
      <td class="p-3 text-center font-mono ${momBadge}">${p.mom_growth > 0 ? '+' : ''}${p.mom_growth}%</td>
    `;

    tr.innerHTML = rowHTML;
    tbody.appendChild(tr);
  });
}

function abrirModalAjustes() {
  const modal = document.getElementById('modal-explicacion-ajustes');
  if (modal) modal.classList.remove('hidden');
  if (!mlDataGlobal) loadTop20HistoricoML();
}

function cerrarModalAjustes() {
  const modal = document.getElementById('modal-explicacion-ajustes');
  if (modal) modal.classList.add('hidden');
}


// ── MÓDULO 3: COMISIONES ────────────────────────────────────────────────────
let isVendedoresLoading = false;
async function loadVendedores() {
  if (isVendedoresLoading) return;
  isVendedoresLoading = true;
  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  try {
    const res = await fetch(`/api/vendedores?empresa=${encodeURIComponent(empresa)}`);
    const data = await res.json();
    const selCom = document.getElementById('com-vendedor');
    const selCob = document.getElementById('cob-vendedor');

    if (selCom) selCom.innerHTML = '';
    if (selCob) selCob.innerHTML = '<option value="TODOS">👥 TODOS LOS VENDEDORES</option>';

    const tagsNoVendedores = [
      'cedis qro', 'cedis', 'sin asignar', 'sin asignacion', 'empleado', 'externo',
      'bmg', 'ventas', 'mirelia cervantes cervantes', 'mirelia', 'rigoberto hernandez zavala',
      'rigoberto', 'administrador', 'admin', 'odoobot', 'alexis ramirez martinez',
      'carolina alvarez suarez', 'david daiko', 'david fernando sanchez hernandez',
      'hugo baldomero medina rivera', 'maria del carmen guerrero rodriguez'
    ];

    if (data.vendedores && data.vendedores.length > 0) {
      data.vendedores.forEach(([val, lbl]) => {
        const lblNorm = normalizarTexto(lbl || '');
        if (tagsNoVendedores.some(t => lblNorm === t || lblNorm.includes('sin asignar') || lblNorm.includes('cedis qro'))) {
          return;
        }
        const lblClean = lbl.trim();
        if (selCom) {
          const optCom = document.createElement('option');
          optCom.value = val;
          optCom.innerText = lblClean;
          if (lblClean.includes('Fabián') || lblClean.includes('Fabian')) optCom.selected = true;
          selCom.appendChild(optCom);
        }
        if (selCob) {
          const optCob = document.createElement('option');
          optCob.value = val;
          optCob.innerText = `👤 ${lblClean}`;
          selCob.appendChild(optCob);
        }
      });
      // Si no seleccionó Fabian por defecto, seleccionar el primer vendedor disponible
      if (selCom && (!selCom.value || selCom.selectedIndex < 0) && selCom.options.length > 0) {
        selCom.options[0].selected = true;
      }
      if (currentTab === 'comisiones') {
        loadComisionesData();
      }
      if (currentTab === 'cobranza') {
        loadCobranzaData();
      }
    }
  } catch (err) {
    console.error('Error vendedores:', err);
  } finally {
    isVendedoresLoading = false;
  }
}

async function loadComisionesData() {
  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  const selVend = document.getElementById('com-vendedor');
  if (!selVend || selVend.options.length <= 1 || !selVend.value) {
    await loadVendedores();
    return;
  }
  const vendVal = selVend.value;
  const vendNom = selVend.selectedOptions[0]?.text || '';
  const mes = document.getElementById('com-mes')?.value || String(new Date().getMonth() + 1);
  const anio = document.getElementById('com-anio')?.value || String(new Date().getFullYear());
  const excl45 = document.getElementById('com-excluir-45')?.checked ?? true;
  const limiteDias = parseInt(document.getElementById('com-limite-dias')?.value || '45');
  const pbnk = document.getElementById('com-pbnk')?.checked ?? true;

  showLoading('Liquidando Comisiones...', `Calculando pagos, pólizas y reglas de ${vendNom || 'vendedor'}...`);

  const tbody = document.getElementById('tbody-comisiones');
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="p-8 text-center text-blue-400 font-medium">
          <i class="fa-solid fa-spinner fa-spin text-2xl mb-2 block"></i>
          Calculando comisiones con reglas oficiales y pólizas Odoo...
        </td>
      </tr>
    `;
  }

  try {
    const res = await fetch('/api/comisiones', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mes: mes, anio: anio, vendedor_valor: vendVal, vendedor_nombre: vendNom,
        empresa_nombre: empresa, incluir_pbnk: pbnk, excluir_retrasos_45: excl45, limite_dias: limiteDias,
        overrides_especiales: especialesActivosGlobal
      })
    });
    const data = await res.json();
    if (data.success && data.data) {
      comisionesDataGlobal = data.data.detalle || [];
      clientesUnicosGlobal = [...new Set(comisionesDataGlobal.map(c => c.cliente))].filter(Boolean).sort();
      renderComisionesTable();
      hideLoading('¡Comisiones Listas!', `${comisionesDataGlobal.length} pagos liquidados con éxito.`);
    } else {
      comisionesDataGlobal = [];
      renderComisionesTable();
      hideLoading('⚠️ Sin Comisiones', data.error || 'No se encontraron pagos registrados en el período.');
    }
  } catch (err) {
    console.error('Error comisiones:', err);
    hideLoading('⚠️ Error Comisiones', 'Error al liquidar comisiones.');
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" class="p-8 text-center text-rose-400 font-medium">
            Error al calcular comisiones: ${err}
          </td>
        </tr>
      `;
    }
  }
}

function filtrarClientesDropdown(query) {
  const dropdown = document.getElementById('dropdown-clientes-custom');
  if (!dropdown) return;

  const q = normalizarTexto(query);
  const filtrados = clientesUnicosGlobal.filter(c => normalizarTexto(c).includes(q));

  if (filtrados.length === 0) {
    dropdown.innerHTML = `
      <div class="p-3 text-center text-xs text-slate-500 font-medium italic">
        No se encontraron clientes para este vendedor
      </div>
    `;
  } else {
    dropdown.innerHTML = filtrados.map(cli => {
      const safeCli = cli.replace(/'/g, "\\'");
      return `
        <div onclick="seleccionarClienteDropdown('${safeCli}')"
             class="p-2.5 hover:bg-amber-500/20 hover:text-amber-300 text-slate-200 text-xs font-semibold cursor-pointer transition-colors flex items-center justify-between group">
          <span class="truncate"><i class="fa-solid fa-user text-slate-500 group-hover:text-amber-400 mr-2 text-[10px]"></i> ${cli}</span>
          <i class="fa-solid fa-arrow-right text-[10px] text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity"></i>
        </div>
      `;
    }).join('');
  }

  dropdown.classList.remove('hidden');
}

function seleccionarClienteDropdown(nombre) {
  const input = document.getElementById('com-cli-esp');
  if (input) input.value = nombre;
  const dropdown = document.getElementById('dropdown-clientes-custom');
  if (dropdown) dropdown.classList.add('hidden');
}

function renderComisionesTable() {
  const tbody = document.getElementById('tbody-comisiones');
  tbody.innerHTML = '';

  const excluir45 = document.getElementById('com-excluir-45')?.checked ?? true;
  const limiteDias = parseInt(document.getElementById('com-limite-dias')?.value || '45');

  if (comisionesDataGlobal.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="p-8 text-center text-slate-500 font-medium">
          <i class="fa-solid fa-folder-open text-2xl mb-2 block text-slate-600"></i>
          No hay pagos registrados para este vendedor en el período seleccionado.
        </td>
      </tr>
    `;
    document.getElementById('kpi-com-cobrado').innerText = '$0.00';
    document.getElementById('kpi-com-challenger').innerText = '$0.00';
    document.getElementById('kpi-com-multi').innerText = '$0.00';
    document.getElementById('kpi-com-total').innerText = '$0.00';
    return;
  }

  let totCobrado = 0;
  let totCobradoBruto = 0;
  let totChallenger = 0;
  let totMulti = 0;
  let totComision = 0;

  comisionesDataGlobal.forEach((c, idx) => {
    const esCancelado = c.cancelado === true;
    const esRetrasado = c.en_tiempo === false;
    const diasRet = c.dias_retraso || 0;
    const excedeLimite = esRetrasado && (diasRet > limiteDias);

    if (c.cuenta_manual === undefined) {
      c.cuenta_manual = !esCancelado;
    }

    const cuentaEfectiva = c.cuenta_manual && !(excluir45 && excedeLimite) && !esCancelado;

    totCobradoBruto += c.cobrado || 0;

    if (cuentaEfectiva) {
      totCobrado += c.cobrado || 0;
      totChallenger += c.base_challenger || 0;
      totMulti += (c.base_multi || 0) + (c.base_pasta || 0);
      totComision += c.comision || 0;
    }

    const tr = document.createElement('tr');
    tr.className = `hover:bg-slate-800/80 cursor-pointer transition-colors group ${!cuentaEfectiva ? 'opacity-40 line-through bg-slate-950/40' : ''}`;
    tr.title = 'Haz clic para inspeccionar este pago producto por producto';
    tr.onclick = () => abrirModalComision(idx);

    let estadoTime = '<span class="text-emerald-400 font-bold">✓ En tiempo</span>';
    if (esCancelado) {
      estadoTime = '<span class="text-slate-400 font-bold">🚫 Cancelado en Odoo</span>';
    } else if (esRetrasado) {
      if (excedeLimite) {
        estadoTime = `<span class="text-red-400 font-bold">🚫 ${diasRet}d (> ${limiteDias}d)</span>`;
      } else {
        estadoTime = `<span class="text-amber-400 font-bold">⚠️ ${diasRet}d tarde</span>`;
      }
    }

    tr.innerHTML = `
      <td class="p-3 text-center font-bold" onclick="toggleCuentaPago(${idx}, event)" title="Haz clic para incluir/excluir este pago">
        <span class="hover:text-blue-400 transition-colors">${cuentaEfectiva ? '☑' : '☐'}</span>
      </td>
      <td class="p-3 text-center text-slate-400">${c.fecha}</td>
      <td class="p-3 font-semibold text-white group-hover:text-blue-400 flex items-center justify-between">
        <span>${c.cliente}</span>
        <i class="fa-solid fa-magnifying-glass-plus text-slate-600 group-hover:text-blue-400 text-xs ml-2"></i>
      </td>
      <td class="p-3 text-slate-400 truncate max-w-xs">${c.factura}</td>
      <td class="p-3 text-right font-medium">${fmtMxn(c.cobrado)}</td>
      <td class="p-3 text-right text-slate-300">${fmtMxn(c.base_challenger)}</td>
      <td class="p-3 text-right font-bold ${cuentaEfectiva ? 'text-emerald-400' : 'text-slate-500'}">${fmtMxn(cuentaEfectiva ? c.comision : 0)}</td>
      <td class="p-3 text-center text-xs">${estadoTime}</td>
    `;
    tbody.appendChild(tr);
  });

  const elCob = document.getElementById('kpi-com-cobrado');
  if (elCob) elCob.innerText = fmtMxn(totCobradoBruto);

  const elCobSub = document.getElementById('kpi-com-cobrado-sub');
  if (elCobSub) {
    if (excluir45 && totCobrado < totCobradoBruto) {
      elCobSub.innerText = `Liquidables: ${fmtMxn(totCobrado)}`;
    } else {
      elCobSub.innerText = `${comisionesDataGlobal.length} pagos Odoo`;
    }
  }

  document.getElementById('kpi-com-challenger').innerText = fmtMxn(totChallenger);
  document.getElementById('kpi-com-multi').innerText = fmtMxn(totMulti);
  document.getElementById('kpi-com-total').innerText = fmtMxn(totComision);
}

function toggleCuentaPago(idx, event) {
  if (event) event.stopPropagation();
  const c = comisionesDataGlobal[idx];
  if (!c) return;
  c.cuenta_manual = !(c.cuenta_manual ?? true);
  renderComisionesTable();
}

function renderChipsEspecialesUI() {
  const container = document.getElementById('chips-especiales-container');
  if (!container) return;
  container.innerHTML = '';

  const keys = Object.keys(especialesActivosGlobal);
  if (keys.length === 0) {
    container.innerHTML = '<span class="text-[11px] text-slate-500 italic">Ninguna tasa especial manual asignada (Sandra Belinda al 5% por defecto).</span>';
    return;
  }

  keys.forEach(cli => {
    const pct = especialesActivosGlobal[cli];
    const chip = document.createElement('div');
    chip.className = 'inline-flex items-center px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-bold';
    chip.innerHTML = `
      <i class="fa-solid fa-tag text-amber-400 mr-1.5 text-[10px]"></i>
      <span>${cli} → ${(pct * 100).toFixed(0)}%</span>
      <button onclick="quitarEspecialUI('${cli}')" class="ml-2 text-amber-400 hover:text-red-400 font-bold transition-colors">✕</button>
    `;
    container.appendChild(chip);
  });
}

function agregarEspecialUI() {
  const cli = document.getElementById('com-cli-esp').value.trim();
  const pctVal = parseFloat(document.getElementById('com-pct-esp').value);

  if (!cli) {
    alert('Escribe o selecciona el nombre de un cliente.');
    return;
  }
  if (isNaN(pctVal) || pctVal <= 0) {
    alert('Escribe un porcentaje válido (ej. 5).');
    return;
  }

  especialesActivosGlobal[cli] = pctVal / 100.0;
  document.getElementById('com-cli-esp').value = '';
  renderChipsEspecialesUI();
  loadComisionesData();
}

function quitarEspecialUI(cli) {
  delete especialesActivosGlobal[cli];
  renderChipsEspecialesUI();
  loadComisionesData();
}

function abrirModalComision(idx) {
  const c = comisionesDataGlobal[idx];
  if (!c) return;

  document.getElementById('lbl-modal-com-cliente').innerText = c.cliente;
  document.getElementById('modal-com-pago').innerText = c.num_pago;
  document.getElementById('modal-com-factura').innerText = c.factura;
  document.getElementById('modal-com-fecha').innerText = c.fecha;
  document.getElementById('modal-com-venc').innerText = c.fecha_venc || '—';
  document.getElementById('modal-com-cobrado').innerText = fmtMxn(c.cobrado);

  const elEstado = document.getElementById('modal-com-estado-tiempo');
  if (c.en_tiempo) {
    elEstado.className = 'mt-0.5 text-xs font-bold text-emerald-400';
    elEstado.innerHTML = '✓ En tiempo';
  } else if (c.en_tiempo === false) {
    elEstado.className = 'mt-0.5 text-xs font-bold text-red-400';
    elEstado.innerHTML = `⚠️ Retrasado ${c.dias_retraso} días`;
  } else {
    elEstado.className = 'mt-0.5 text-xs font-bold text-slate-400';
    elEstado.innerHTML = '—';
  }

  const badgeTasa = document.getElementById('modal-com-badge-tasa');
  if (c.pct_especial) {
    badgeTasa.innerText = `Tasa Especial Cliente: ${(c.pct_especial * 100).toFixed(0)}%`;
  } else {
    badgeTasa.innerText = `Tasa Estándar: ${c.tasa_aplicada || 9}%`;
  }

  document.getElementById('modal-com-total-pago').innerText = fmtMxn(c.comision);

  const tbody = document.getElementById('modal-com-tbody-productos');
  tbody.innerHTML = '';

  const lineas = c.lineas_detalle || [];
  if (lineas.length === 0) {
    const prodTextoList = c.productos_detalle || [];
    if (prodTextoList.length > 0) {
      prodTextoList.forEach((pText, i) => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-900 transition-colors';
        tr.innerHTML = `
          <td class="p-2.5 text-center text-slate-500 font-bold">${i + 1}</td>
          <td class="p-2.5 font-semibold text-white">${pText}</td>
          <td class="p-2.5 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300">Standard</span></td>
          <td class="p-2.5 text-right font-medium">${fmtMxn(c.cobrado / prodTextoList.length)}</td>
          <td class="p-2.5 text-center font-bold text-purple-400">${c.tasa_aplicada || 9}%</td>
          <td class="p-2.5 text-right font-bold text-emerald-400">${fmtMxn(c.comision / prodTextoList.length)}</td>
        `;
        tbody.appendChild(tr);
      });
    } else {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="p-6 text-center text-slate-500 font-medium">
            (Pago global directo en Odoo sin facturas ni renglones desglosados)
          </td>
        </tr>
      `;
    }
  } else {
    lineas.forEach((l, i) => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-900 transition-colors';

      let catBadge = 'bg-blue-500/20 text-blue-300 border-blue-500/30';
      if (l.categoria === 'PASTA' || l.categoria === 'Pasta/Easy Master') catBadge = 'bg-purple-500/20 text-purple-300 border-purple-500/30';
      else if (l.categoria === 'MATERIA PRIMA') catBadge = 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      else if (l.categoria === 'MULTIMARCA') catBadge = 'bg-slate-700 text-slate-300 border-slate-600';

      tr.innerHTML = `
        <td class="p-2.5 text-center text-slate-500 font-bold">${i + 1}</td>
        <td class="p-2.5 font-semibold text-white">${l.producto}</td>
        <td class="p-2.5 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold border ${catBadge}">${l.categoria || 'CHALLENGER'}</span></td>
        <td class="p-2.5 text-right font-medium">${fmtMxn(l.subtotal)}</td>
        <td class="p-2.5 text-center font-bold text-purple-400">${(l.tasa || 9).toFixed(1)}%</td>
        <td class="p-2.5 text-right font-bold text-emerald-400">${fmtMxn(l.monto_comision || 0)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  document.getElementById('modal-comision-detalle').classList.remove('hidden');
}

function cerrarModalComision() {
  document.getElementById('modal-comision-detalle').classList.add('hidden');
}

function openRegistrarPagoModal() {
  const modal = document.getElementById('modal-registrar-pago');
  if (!modal) return;

  const empresa = document.getElementById('global-empresa').value;
  const vendNom = document.getElementById('com-vendedor').selectedOptions[0]?.text || '';
  const mes = document.getElementById('com-mes').selectedOptions[0]?.text || '';
  const anio = document.getElementById('com-anio').value;
  const comTotalText = document.getElementById('kpi-com-total').innerText.replace(/[^0-9.]/g, '');

  document.getElementById('reg-pago-clave').value = `${empresa} | ${vendNom} — ${mes} ${anio}`;
  document.getElementById('reg-pago-com-total').value = comTotalText || '0.00';
  document.getElementById('reg-pago-monto').value = comTotalText || '0.00';
  document.getElementById('reg-pago-fecha').value = new Date().toISOString().split('T')[0];
  document.getElementById('reg-pago-nota').value = '';

  modal.classList.remove('hidden');
}

function closeRegistrarPagoModal() {
  const modal = document.getElementById('modal-registrar-pago');
  if (modal) modal.classList.add('hidden');
}

async function guardarRegistroPago() {
  const clave = document.getElementById('reg-pago-clave').value.trim();
  const com = parseFloat(document.getElementById('reg-pago-com-total').value) || 0;
  const monto = parseFloat(document.getElementById('reg-pago-monto').value) || 0;
  const fecha = document.getElementById('reg-pago-fecha').value.trim();
  const nota = document.getElementById('reg-pago-nota').value.trim();

  if (!clave || !monto || !fecha) {
    alert('Por favor completa la clave, monto y fecha de pago.');
    return;
  }

  try {
    const res = await fetch('/api/comisiones/pagos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clave, comision_total: com, monto, fecha, nota })
    });
    const data = await res.json();
    if (data.success) {
      alert(`✓ Registro de pago de ${fmtMxn(monto)} guardado con éxito.`);
      closeRegistrarPagoModal();
    } else {
      alert(`Error al registrar pago: ${data.error}`);
    }
  } catch (err) {
    alert(`Error de red: ${err.message}`);
  }
}


let currentCfdiModalData = null;

// ── MÓDULO 4: SAT & FACTURAS OFICIALES PURAS (CFDI 4.0 / 3.3) ───────────────
async function loadSatData() {
  showLoading('Consultando Facturas SAT Oficiales...', 'Leyendo CFDI 4.0 / 3.3 oficiales del SAT y aplicando tipos de cambio DOF...');

  const tbody = document.getElementById('tbody-sat');
  if (tbody && satDataGlobal.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="11" class="p-8 text-center text-amber-400 font-medium">
          <i class="fa-solid fa-spinner fa-spin text-2xl mb-2 block"></i>
          Leyendo y validando facturas oficiales del SAT...
        </td>
      </tr>
    `;
  }

  try {
    const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
    const anio = document.getElementById('sat-filter-anio')?.value || 'TODOS';
    const direccion = document.getElementById('sat-filter-direccion')?.value || 'PROVEEDORES';
    
    const res = await fetch('/api/sat/facturas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ empresa_nombre: empresa, anio: anio, direccion: direccion })
    });
    if (!res.ok) {
      throw new Error(`Error en servidor SAT (${res.status})`);
    }
    const data = await res.json();
    if (data.success && data.data) {
      satDataGlobal = data.data.cuentas || [];
      renderSatTable();
      hideLoading('¡Facturas SAT Listas!', `${satDataGlobal.length} comprobantes oficiales procesados.`);
    } else {
      hideLoading('⚠️ Sin Registros', 'No se encontraron facturas del SAT con los filtros actuales.');
    }
  } catch (err) {
    console.error('Error SAT:', err);
    hideLoading('⚠️ Error SAT', 'Error al consultar facturas oficiales.');
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="11" class="p-8 text-center text-rose-400 font-medium">
            Error al consultar facturas SAT: ${err.message || err}
          </td>
        </tr>
      `;
    }
  }
}

function renderSatTable() {
  const tbody = document.getElementById('tbody-sat');
  if (!tbody) return;

  const searchInput = document.getElementById('search-sat')?.value || '';
  const search = normalizarTexto(searchInput);
  const monedaFilter = document.getElementById('sat-filter-moneda')?.value || 'TODAS';
  const tipoFilter = document.getElementById('sat-filter-tipo')?.value || 'TODOS';
  const metodoFilter = document.getElementById('sat-filter-metodo')?.value || 'TODOS';

  tbody.innerHTML = '';

  const filtered = satDataGlobal.filter(item => {
    if (monedaFilter !== 'TODAS' && item.moneda !== monedaFilter) return false;
    if (tipoFilter !== 'TODOS' && item.tipo !== tipoFilter) return false;
    if (metodoFilter !== 'TODOS' && item.metodo_pago !== metodoFilter) return false;
    if (search) {
      const provNorm = normalizarTexto(item.proveedor);
      const rfcEmisorNorm = normalizarTexto(item.rfc_emisor);
      const recepNorm = normalizarTexto(item.receptor);
      const rfcRecepNorm = normalizarTexto(item.rfc_receptor);
      const uuidNorm = normalizarTexto(item.uuid);
      const folioNorm = normalizarTexto(item.folio);
      const concNorm = normalizarTexto((item.conceptos || []).map(c => c.descripcion).join(' '));
      if (!provNorm.includes(search) && !rfcEmisorNorm.includes(search) && !recepNorm.includes(search) && !rfcRecepNorm.includes(search) && !uuidNorm.includes(search) && !folioNorm.includes(search) && !concNorm.includes(search)) return false;
    }
    return true;
  });

  // KPIs
  const totMxn = filtered.reduce((sum, i) => sum + (i.total_mxn || i.total || 0), 0);
  const totUsd = filtered.filter(i => i.is_usd).reduce((sum, i) => sum + (i.total || 0), 0);
  const nPue = filtered.filter(i => i.tipo === 'I' && i.metodo_pago === 'PUE').length;
  const nPpd = filtered.filter(i => i.tipo === 'I' && i.metodo_pago === 'PPD').length;
  const nRep = filtered.filter(i => i.tipo === 'P').length;
  const nNc = filtered.filter(i => i.tipo === 'E').length;
  const uniqueProvs = new Set(filtered.map(i => i.rfc_emisor || i.proveedor)).size;

  const elFacturas = document.getElementById('kpi-sat-facturas');
  const elProvs = document.getElementById('kpi-sat-provs');
  const elDeuda = document.getElementById('kpi-sat-deuda');
  const elSubDeuda = document.getElementById('kpi-sat-sub-deuda');
  const elPagado = document.getElementById('kpi-sat-pagado');
  const elSubPagado = document.getElementById('kpi-sat-sub-pagado');
  const elFaltantes = document.getElementById('kpi-sat-faltantes');
  const elSubMetodos = document.getElementById('kpi-sat-sub-metodos');

  if (elFacturas) elFacturas.innerText = fmtNum(filtered.length);
  if (elProvs) elProvs.innerText = `${uniqueProvs} emisores únicos`;
  if (elDeuda) elDeuda.innerText = fmtMxn(totMxn);
  if (elSubDeuda) elSubDeuda.innerText = `En ${filtered.length} facturas oficiales`;
  if (elPagado) elPagado.innerText = `US$ ${totUsd.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  if (elSubPagado) elSubPagado.innerText = `${filtered.filter(i => i.is_usd).length} facturas en USD`;
  if (elFaltantes) elFaltantes.innerText = `${nPue} PUE | ${nPpd} PPD`;
  if (elSubMetodos) elSubMetodos.innerText = `${nRep} Complementos REP | ${nNc} NC`;

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="11" class="p-8 text-center text-slate-500 font-medium">
          <i class="fa-solid fa-folder-open text-2xl mb-2 block text-slate-600"></i>
          No hay facturas del SAT que coincidan con los filtros seleccionados.
        </td>
      </tr>
    `;
    return;
  }

  filtered.forEach((item, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/40 transition-colors';

    let tipoBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">🟢 Ingreso</span>';
    if (item.tipo === 'P') tipoBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">🟣 REP Pago</span>';
    else if (item.tipo === 'E') tipoBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">🔴 Egreso NC</span>';

    const metodoBadge = item.metodo_pago === 'PUE'
      ? '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">PUE</span>'
      : '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">PPD</span>';

    const curBadge = item.is_usd
      ? '<span class="px-2 py-0.5 rounded text-[10px] font-black bg-purple-600/30 text-purple-300 border border-purple-500/40" title="Tipo de Cambio DOF: ' + item.tipo_cambio + '">🇺🇸 USD</span>'
      : '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700">🇲🇽 MXN</span>';

    const fmtUsd = (val) => `US$ ${Number(val || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

    const cellSubtotal = item.is_usd ? fmtUsd(item.subtotal) : fmtMxn(item.subtotal);
    const cellTotalOrig = item.is_usd ? fmtUsd(item.total) : fmtMxn(item.total);
    const cellTotalMxn = fmtMxn(item.total_mxn);

    tr.innerHTML = `
      <td class="p-3 text-center text-slate-500 font-bold">${idx + 1}</td>
      <td class="p-3 text-center text-slate-300 font-medium whitespace-nowrap">${item.fecha || '—'}</td>
      <td class="p-3">
        <div class="font-mono text-xs font-bold text-amber-300 select-all truncate max-w-[140px]" title="${item.uuid}">${item.uuid ? item.uuid.substring(0, 18) + '...' : '—'}</div>
        <div class="text-[10px] text-slate-400 font-mono truncate">Folio: ${item.folio || '—'}</div>
      </td>
      <td class="p-3 max-w-xs">
        <div class="font-semibold text-white truncate" title="${item.proveedor}">${item.proveedor}</div>
        <div class="text-[10px] font-mono text-slate-400">${item.rfc_emisor}</div>
      </td>
      <td class="p-3 max-w-[160px]">
        <div class="font-medium text-slate-200 truncate" title="${item.receptor}">${item.receptor || '—'}</div>
        <div class="text-[10px] font-mono text-slate-400">${item.rfc_receptor}</div>
      </td>
      <td class="p-3 text-center whitespace-nowrap">
        <div class="flex flex-col items-center gap-1">
          ${tipoBadge}
          ${item.tipo === 'I' ? metodoBadge : ''}
        </div>
      </td>
      <td class="p-3 text-center">${curBadge}</td>
      <td class="p-3 text-right font-mono text-slate-300">${cellSubtotal}</td>
      <td class="p-3 text-right font-mono font-bold text-white">${cellTotalOrig}</td>
      <td class="p-3 text-right font-mono font-black text-emerald-400">${cellTotalMxn}</td>
      <td class="p-3 text-center whitespace-nowrap">
        <div class="flex items-center justify-center space-x-1.5">
          <button onclick="descargarXmlSat('${item.uuid}')" class="px-2.5 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-bold text-[11px] transition-colors shadow-sm flex items-center cursor-pointer" title="Descargar archivo XML oficial del SAT">
            <i class="fa-solid fa-download mr-1"></i> XML
          </button>
          <button onclick="verDetalleCfdiModal('${item.uuid}')" class="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-[11px] transition-colors border border-slate-700 flex items-center cursor-pointer" title="Ver detalle completo del CFDI y Conceptos">
            <i class="fa-solid fa-eye"></i>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ── DESCARGA DE XML Y ZIP SAT ────────────────────────────────────────────────
function descargarXmlSat(uuidStr) {
  if (!uuidStr) return;
  window.open(`/api/sat/descargar_xml?uuid=${encodeURIComponent(uuidStr)}`, '_blank');
}

function descargarXmlSatActual() {
  if (currentCfdiModalData && currentCfdiModalData.uuid) {
    descargarXmlSat(currentCfdiModalData.uuid);
  }
}

async function descargarZipSat() {
  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  const anio = document.getElementById('sat-filter-anio')?.value || 'TODOS';
  const direccion = document.getElementById('sat-filter-direccion')?.value || 'PROVEEDORES';

  showLoading('Comprimiendo Facturas SAT...', 'Empaquetando archivos XML en un ZIP para descarga masiva...');
  try {
    const url = `/api/sat/descargar_zip?empresa_nombre=${encodeURIComponent(empresa)}&anio=${encodeURIComponent(anio)}&direccion=${encodeURIComponent(direccion)}`;
    window.location.href = url;
    setTimeout(() => {
      hideLoading('¡Descarga Iniciada!', 'Tu paquete ZIP con facturas XML se está descargando.');
    }, 1500);
  } catch (err) {
    hideLoading('⚠️ Error de Descarga', 'No se pudo generar el archivo ZIP.');
  }
}

// ── VISOR MODAL DE CFDI DETALLE ─────────────────────────────────────────────
async function verDetalleCfdiModal(uuidStr) {
  if (!uuidStr) return;
  showLoading('Abriendo Factura SAT...', 'Cargando partidas y timbres fiscales del XML oficial...');
  
  try {
    const res = await fetch(`/api/sat/detalle_cfdi?uuid=${encodeURIComponent(uuidStr)}`);
    const data = await res.json();
    if (data.success && data.data) {
      const c = data.data;
      currentCfdiModalData = c;

      document.getElementById('modal-cfdi-title-proveedor').innerText = c.proveedor || 'Proveedor SAT';
      document.getElementById('modal-cfdi-uuid-lbl').innerText = c.uuid || '—';
      document.getElementById('modal-cfdi-emisor-nom').innerText = c.proveedor || '—';
      document.getElementById('modal-cfdi-emisor-rfc').innerText = c.rfc_emisor || '—';
      document.getElementById('modal-cfdi-emisor-reg').innerText = c.regimen_emisor || 'General de Ley';
      
      document.getElementById('modal-cfdi-receptor-nom').innerText = c.receptor || '—';
      document.getElementById('modal-cfdi-receptor-rfc').innerText = c.rfc_receptor || '—';
      document.getElementById('modal-cfdi-receptor-uso').innerText = c.uso_cfdi || 'G03 - Gastos en general';

      document.getElementById('modal-cfdi-fecha').innerText = c.fecha_completa || c.fecha || '—';
      document.getElementById('modal-cfdi-folio').innerText = c.folio || '—';
      document.getElementById('modal-cfdi-forma-pago').innerText = c.forma_pago ? `${c.forma_pago} - Transferencia/Electrónico` : '03 - Transferencia';
      document.getElementById('modal-cfdi-tc').innerText = c.is_usd ? `$${c.tipo_cambio} MXN` : '1.0000 (MXN)';

      // Badges
      const bTipo = document.getElementById('modal-cfdi-badge-tipo');
      if (bTipo) {
        if (c.tipo === 'I') bTipo.innerText = '🟢 INGRESO (FACTURA)';
        else if (c.tipo === 'P') bTipo.innerText = '🟣 PAGO (COMPLEMENTO REP)';
        else if (c.tipo === 'E') bTipo.innerText = '🔴 EGRESO (NOTA DE CRÉDITO)';
      }
      const bMon = document.getElementById('modal-cfdi-badge-moneda');
      if (bMon) bMon.innerText = c.is_usd ? '🇺🇸 USD (Dólares)' : '🇲🇽 MXN (Pesos)';

      const bMet = document.getElementById('modal-cfdi-badge-metodo');
      if (bMet) bMet.innerText = c.metodo_pago === 'PUE' ? 'PUE - Contado' : 'PPD - Crédito / Parcialidades';

      // Conceptos
      const tbodyC = document.getElementById('modal-cfdi-tbody-conceptos');
      const lblCount = document.getElementById('modal-cfdi-conceptos-count');
      if (tbodyC) {
        tbodyC.innerHTML = '';
        const conceptos = c.conceptos || [];
        if (lblCount) lblCount.innerText = `${conceptos.length} partida(s)`;
        if (conceptos.length === 0) {
          tbodyC.innerHTML = '<tr><td colspan="5" class="p-3 text-center text-slate-500">Sin desglose de conceptos detallado en este comprobante.</td></tr>';
        } else {
          conceptos.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td class="p-2.5 font-mono text-[11px] text-amber-300 font-bold">${item.clave_prod_serv || '—'}</td>
              <td class="p-2.5 font-medium text-white">${item.descripcion || '—'}</td>
              <td class="p-2.5 text-right text-slate-300 font-mono">${item.cantidad} ${item.clave_unidad || ''}</td>
              <td class="p-2.5 text-right text-slate-300 font-mono">${c.is_usd ? '$' + Number(item.valor_unitario).toFixed(2) : fmtMxn(item.valor_unitario)}</td>
              <td class="p-2.5 text-right font-mono font-bold text-emerald-400">${c.is_usd ? '$' + Number(item.importe).toFixed(2) : fmtMxn(item.importe)}</td>
            `;
            tbodyC.appendChild(tr);
          });
        }
      }

      // Totales
      const fmtCur = (val) => c.is_usd ? `US$ ${Number(val||0).toLocaleString('en-US', {minimumFractionDigits: 2})}` : fmtMxn(val);
      document.getElementById('modal-cfdi-subtotal').innerText = fmtCur(c.subtotal);
      document.getElementById('modal-cfdi-iva').innerText = fmtCur(c.impuestos_trasladados);
      document.getElementById('modal-cfdi-ret').innerText = fmtCur(c.impuestos_retenidos);
      document.getElementById('modal-cfdi-total-orig').innerText = fmtCur(c.total);

      const boxMxn = document.getElementById('modal-cfdi-box-mxn');
      if (c.is_usd && boxMxn) {
        boxMxn.classList.remove('hidden');
        document.getElementById('modal-cfdi-total-mxn').innerText = fmtMxn(c.total_mxn);
      } else if (boxMxn) {
        boxMxn.classList.add('hidden');
      }

      hideLoading();
      document.getElementById('modal-sat-cfdi-detalle').classList.remove('hidden');
    } else {
      hideLoading('⚠️ Error', 'No se pudo leer el detalle del XML.');
    }
  } catch (err) {
    hideLoading('⚠️ Error', 'Fallo al consultar el CFDI.');
  }
}

function copiarUuidCfdiModal() {
  if (currentCfdiModalData && currentCfdiModalData.uuid) {
    navigator.clipboard.writeText(currentCfdiModalData.uuid).then(() => {
      alert(`UUID copiado al portapapeles:\n${currentCfdiModalData.uuid}`);
    });
  }
}

function imprimirCfdiModal() {
  window.print();
}

function cerrarModalSatCfdi() {
  document.getElementById('modal-sat-cfdi-detalle').classList.add('hidden');
  currentCfdiModalData = null;
}

// ── MODAL Y DESCARGA FIEL SAT ───────────────────────────────────────────────
async function openSatModal() {
  document.getElementById('modal-fiel').classList.remove('hidden');
  try {
    const res = await fetch('/api/sat/config');
    const data = await res.json();
    if (data.config) {
      document.getElementById('fiel-cer-path').value = data.config.cer_path || '';
      document.getElementById('fiel-key-path').value = data.config.key_path || '';
      document.getElementById('fiel-password').value = data.config.password || '';
    }
  } catch (err) {}
}

function closeSatModal() {
  document.getElementById('modal-fiel').classList.add('hidden');
  const lbl = document.getElementById('sat-download-status');
  lbl.classList.add('hidden');
  lbl.innerHTML = '';
}

async function ejecutarDescargaSat() {
  const cer = document.getElementById('fiel-cer-path').value.trim();
  const key = document.getElementById('fiel-key-path').value.trim();
  const pwd = document.getElementById('fiel-password').value.trim();
  const lbl = document.getElementById('sat-download-status');

  if (!cer || !key || !pwd) {
    lbl.classList.remove('hidden');
    lbl.className = 'text-xs text-center font-medium text-red-400';
    lbl.innerText = 'Por favor especifica la ruta de tu .cer, .key y contraseña de la e.firma.';
    return;
  }

  lbl.classList.remove('hidden');
  lbl.className = 'text-xs text-center font-medium text-blue-400 animate-pulse';
  lbl.innerText = '⚡ Conectando con los servidores del SAT y descargando facturas de proveedores...';

  try {
    const targetAnio = parseInt(document.getElementById('fiel-target-anio')?.value || '2026');
    const targetMes = parseInt(document.getElementById('fiel-target-mes')?.value || '8');
    const res = await fetch('/api/sat/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cer_path: cer, key_path: key, password: pwd, anio: targetAnio, mes: targetMes })
    });
    const data = await res.json();

    if (data.success) {
      lbl.className = 'text-xs text-center font-bold text-emerald-400';
      lbl.innerText = `✓ ${data.data.mensaje || 'Descarga completada con éxito.'}`;
      setTimeout(() => {
        closeSatModal();
        loadSatData();
      }, 2000);
    } else {
      lbl.className = 'text-xs text-center font-medium text-red-400';
      lbl.innerText = `⚠️ Error SAT: ${data.error || 'No se pudo conectar al SAT.'}`;
    }
  } catch (err) {
    lbl.className = 'text-xs text-center font-medium text-red-400';
    lbl.innerText = `⚠️ Error de red: ${err.message}`;
  }
}


// ── MÓDULO 5: COBRANZA & GESTIÓN DE COBRO ACTIVO ("COBRAR") ─────────────────
let cobranzaClientesGlobal = [];
let cobranzaTotalesGlobal = {};
let cobranzaCiclosGlobal = { meses: [], resumen_global: {} };
let cobranzaCobradoMesGlobal = { meses: [], resumen_global: {} };
let currentCobAgingFilter = 'ALL';
let currentCobSubtab = 'gestion';
let currentClienteCobroSeleccionado = null;

async function loadCobranzaData() {
  const empresa = document.getElementById('global-empresa')?.value || 'BALDOMERO MEDINA GARZA';
  const vendVal = document.getElementById('cob-vendedor')?.value || 'TODOS';
  const optSel = document.getElementById('cob-vendedor')?.selectedOptions[0];
  const vendNom = optSel && vendVal !== 'TODOS' ? optSel.text.replace(/^[^\w\s\u00C0-\u017F]+/, '').replace(/\s*\([^)]*\)\s*$/, '').trim() : 'TODOS';
  const inter = document.getElementById('cob-interempresa')?.checked ?? true;

  showLoading('Consultando Cartera & Cobranza...', 'Obteniendo saldos por cobrar, pagos y clientes en Odoo ERP...');

  const gridCob = document.getElementById('grid-cobranza-clientes');
  if (gridCob && cobranzaClientesGlobal.length === 0) {
    gridCob.innerHTML = `
      <div class="col-span-full p-12 text-center text-emerald-400 font-medium">
        <i class="fa-solid fa-spinner fa-spin text-3xl mb-3 block"></i>
        Cargando cartera de clientes, teléfonos y cuentas por cobrar desde Odoo...
      </div>
    `;
  }

  try {
    const res = await fetch('/api/cobranza', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ empresa_nombre: empresa, vendedor_valor: vendVal, vendedor_nombre: vendNom, excluir_interempresa: inter })
    });
    const data = await res.json();
    if (data.success && data.data) {
      cobranzaDataGlobal = data.data.cuentas || [];
      cobranzaClientesGlobal = data.data.clientes_cartera || [];
      cobranzaTotalesGlobal = data.data.totales || {};
      cobranzaCiclosGlobal = data.data.ciclos_recuperacion || { meses: [], resumen_global: {} };
      cobranzaCobradoMesGlobal = data.data.cobrado_por_mes || { meses: [], resumen_global: {} };

      // Poblar selector de vendedores principal si está en blanco
      const selVend = document.getElementById('cob-vendedor');
      if (selVend && selVend.options.length <= 1) {
        const vMet = cobranzaTotalesGlobal.vendedores_metricas || [];
        vMet.forEach(v => {
          const opt = document.createElement('option');
          opt.value = v.vendedor_id || v.vendedor;
          opt.innerText = `👤 ${v.vendedor} (${fmtMxn(v.saldo_total)})`;
          selVend.appendChild(opt);
        });
      }

      // Poblar selector de meses en la sub-pestaña de Cobrado por Mes
      const selCobMes = document.getElementById('cob-mes-select-periodo');
      if (selCobMes) {
        const valPrevCob = selCobMes.value;
        selCobMes.innerHTML = '<option value="TODOS">📅 TODOS LOS MESES (Histórico Completo)</option>';
        if (cobranzaCobradoMesGlobal.meses) {
          cobranzaCobradoMesGlobal.meses.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.mes_key;
            const estTxt = fmtMxn(m.cobranza_estimada_vence || 0);
            const cobTxt = fmtMxn(m.cobrado_real_pagos || m.total_cobrado || 0);
            opt.innerText = `📅 ${m.mes_nombre} (Vencen: ${estTxt} | Cobrado: ${cobTxt})`;
            selCobMes.appendChild(opt);
          });
        }
        if (valPrevCob && selCobMes.querySelector(`option[value="${valPrevCob}"]`)) {
          selCobMes.value = valPrevCob;
        } else {
          // Preseleccionar mes actual si existe
          const currKey = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`;
          if (selCobMes.querySelector(`option[value="${currKey}"]`)) {
            selCobMes.value = currKey;
          }
        }
      }

      // Poblar chips de acceso rápido a meses
      const containerChips = document.getElementById('container-chips-meses');
      if (containerChips && cobranzaCobradoMesGlobal.meses) {
        let chipsHtml = '<span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider shrink-0">Acceso Rápido:</span>';
        chipsHtml += `<button onclick="seleccionarMesCobrado('TODOS')" id="chip-mes-TODOS" class="px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all whitespace-nowrap">📅 Todos los Meses</button>`;
        cobranzaCobradoMesGlobal.meses.slice(0, 5).forEach(m => {
          chipsHtml += `
            <button onclick="seleccionarMesCobrado('${m.mes_key}')" id="chip-mes-${m.mes_key}" class="px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-800 hover:bg-emerald-600/80 text-emerald-300 hover:text-white transition-all whitespace-nowrap">
              ${m.mes_nombre}
            </button>
          `;
        });
        containerChips.innerHTML = chipsHtml;
      }

      // Poblar selector de vendedor en sub-pestaña Cobrado por Mes
      const selCobVend = document.getElementById('cob-mes-select-vendedor');
      if (selCobVend && selCobVend.options.length <= 1) {
        const vDetectados = cobranzaTotalesGlobal.vendedores_detectados || [];
        vDetectados.forEach(vName => {
          const opt = document.createElement('option');
          opt.value = vName;
          opt.innerText = `👤 ${vName}`;
          selCobVend.appendChild(opt);
        });
      }

      const badgeCobMes = document.getElementById('badge-cob-mes-count');
      if (badgeCobMes) {
        badgeCobMes.innerText = fmtMxn(cobranzaCobradoMesGlobal.resumen_global?.total_cobrado_real_historico || cobranzaCobradoMesGlobal.resumen_global?.total_cobrado_historico || 0);
      }

      // Poblar selector de meses y vendedores en la sub-pestaña de recuperación
      const selRecupMes = document.getElementById('cob-recup-mes');
      if (selRecupMes) {
        const valPrev = selRecupMes.value;
        selRecupMes.innerHTML = '<option value="TODOS">📅 TODOS LOS MESES (Consolidado)</option>';
        if (cobranzaCiclosGlobal.meses) {
          cobranzaCiclosGlobal.meses.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.mes_key;
            opt.innerText = `📅 ${m.mes_venta} ➔ Recuperar en ${m.mes_siguiente}`;
            selRecupMes.appendChild(opt);
          });
        }
        if (valPrev && selRecupMes.querySelector(`option[value="${valPrev}"]`)) {
          selRecupMes.value = valPrev;
        }
      }

      const selRecupVend = document.getElementById('cob-recup-vendedor');
      if (selRecupVend && selRecupVend.options.length <= 1) {
        const vDetectados = cobranzaTotalesGlobal.vendedores_detectados || [];
        vDetectados.forEach(vName => {
          const opt = document.createElement('option');
          opt.value = vName;
          opt.innerText = `👤 ${vName}`;
          selRecupVend.appendChild(opt);
        });
      }

      const badgeRecup = document.getElementById('badge-cob-recup-count');
      if (badgeRecup) {
        badgeRecup.innerText = `${(cobranzaCiclosGlobal.meses || []).length} Meses`;
      }

      renderCobranzaKPIs();
      renderCobranzaClientesCards();
      renderCobranzaTable();
      renderCobradoMesView();
      renderCobranzaRecuperacion();

      hideLoading('¡Cartera Lista!', `${cobranzaClientesGlobal.length} clientes deudores y ${(cobranzaCobradoMesGlobal.meses || []).length} meses de cobros listos.`);
    } else {
      if (data && data.error) {
        console.warn('Cobranza warning/error:', data.error);
        hideLoading('⚠️ Aviso Cobranza', data.error);
      } else {
        hideLoading('⚠️ Sin Saldos', 'No se encontraron cuentas por cobrar en el periodo.');
      }
    }
  } catch (err) {
    console.error('Error cobranza:', err);
    hideLoading('⚠️ Error Cobranza', err?.message || 'Error al conectar con Odoo.');
  }
}

function renderCobranzaKPIs() {
  const vendFilterVal = document.getElementById('cob-vendedor')?.value || 'TODOS';
  let clientes = cobranzaClientesGlobal;
  let facturas = cobranzaDataGlobal;

  const totTotal = facturas.reduce((s, i) => s + (i.saldo_pendiente || 0), 0);
  
  // Reciente: 0 a 60 días
  const facsReciente = facturas.filter(i => (i.dias_retraso || 0) > 0 && (i.dias_retraso || 0) <= 60);
  const totReciente = facsReciente.reduce((s, i) => s + (i.saldo_pendiente || 0), 0);
  const clisReciente = new Set(facsReciente.map(i => i.cliente_id || i.cliente)).size;

  // Pasada: 60 a 100 días
  const facsPasada = facturas.filter(i => (i.dias_retraso || 0) > 60 && (i.dias_retraso || 0) <= 100);
  const totPasada = facsPasada.reduce((s, i) => s + (i.saldo_pendiente || 0), 0);
  const clisPasada = new Set(facsPasada.map(i => i.cliente_id || i.cliente)).size;

  // Atrasada: Más de 100 días
  const facsAtrasada = facturas.filter(i => (i.dias_retraso || 0) > 100);
  const totAtrasada = facsAtrasada.reduce((s, i) => s + (i.saldo_pendiente || 0), 0);
  const clisAtrasada = new Set(facsAtrasada.map(i => i.cliente_id || i.cliente)).size;

  // Renderizar valores en las tarjetas
  const elTot = document.getElementById('kpi-cob-total');
  const elSubTot = document.getElementById('kpi-cob-sub-total');
  if (elTot) elTot.innerText = fmtMxn(totTotal);
  if (elSubTot) elSubTot.innerText = `${facturas.length} facturas · ${clientes.length} clientes`;

  const elRec = document.getElementById('kpi-cob-reciente');
  const elRecCnt = document.getElementById('kpi-cob-reciente-count');
  if (elRec) elRec.innerText = fmtMxn(totReciente);
  if (elRecCnt) elRecCnt.innerText = `${facsReciente.length} facturas · ${clisReciente} clientes`;

  const elPas = document.getElementById('kpi-cob-pasada');
  const elPasCnt = document.getElementById('kpi-cob-pasada-count');
  if (elPas) elPas.innerText = fmtMxn(totPasada);
  if (elPasCnt) elPasCnt.innerText = `${facsPasada.length} facturas · ${clisPasada} clientes`;

  const elAtr = document.getElementById('kpi-cob-atrasada');
  const elAtrCnt = document.getElementById('kpi-cob-atrasada-count');
  if (elAtr) elAtr.innerText = fmtMxn(totAtrasada);
  if (elAtrCnt) elAtrCnt.innerText = `${facsAtrasada.length} facturas · ${clisAtrasada} clientes`;

  // Resaltar tarjeta activa
  const cards = {
    'ALL': document.getElementById('card-filter-total'),
    'RECIENTE_0_60': document.getElementById('card-filter-reciente'),
    'PASADA_60_100': document.getElementById('card-filter-pasada'),
    'ATRASADA_100_MAS': document.getElementById('card-filter-atrasada')
  };

  Object.keys(cards).forEach(k => {
    if (!cards[k]) return;
    if (k === currentCobAgingFilter) {
      cards[k].classList.add('ring-2', 'ring-emerald-400', 'bg-slate-800/90');
    } else {
      cards[k].classList.remove('ring-2', 'ring-emerald-400', 'bg-slate-800/90');
    }
  });

  const badgeCli = document.getElementById('badge-cob-clientes-count');
  if (badgeCli) badgeCli.innerText = clientes.length;

  const badgeFac = document.getElementById('badge-cob-facturas-count');
  if (badgeFac) badgeFac.innerText = facturas.length;
}

function setCobranzaAgingFilter(filterKey) {
  currentCobAgingFilter = filterKey;

  const lbl = document.getElementById('lbl-cob-active-filter');
  if (lbl) {
    if (filterKey === 'RECIENTE_0_60') {
      lbl.innerHTML = '<span class="text-emerald-400 font-bold">🟢 Filtrando: Cobranza Reciente (0 a 60 días)</span>';
    } else if (filterKey === 'PASADA_60_100') {
      lbl.innerHTML = '<span class="text-amber-400 font-bold">🟡 Filtrando: Cobranza Pasada (60 a 100 días)</span>';
    } else if (filterKey === 'ATRASADA_100_MAS') {
      lbl.innerHTML = '<span class="text-rose-400 font-bold animate-pulse">🚨 Filtrando: Cobranza Atrasada (> 100 días)</span>';
    } else {
      lbl.innerHTML = '<span class="text-indigo-300 font-bold">🟣 Mostrando: Todas las Cuentas Consolidado</span>';
    }
  }

  renderCobranzaKPIs();
  renderCobranzaClientesCards();
  renderCobranzaTable();
}

function switchCobranzaSubtab(subtab) {
  currentCobSubtab = subtab;
  const btnGest = document.getElementById('btn-subtab-cob-gest');
  const btnMes = document.getElementById('btn-subtab-cob-mes');
  const btnRecup = document.getElementById('btn-subtab-cob-recup');
  const btnFacs = document.getElementById('btn-subtab-cob-facs');
  const viewGest = document.getElementById('view-cob-gestion');
  const viewMes = document.getElementById('view-cob-mes');
  const viewRecup = document.getElementById('view-cob-recuperacion');
  const viewFacs = document.getElementById('view-cob-facturas');

  if (viewGest) viewGest.classList.add('hidden');
  if (viewMes) viewMes.classList.add('hidden');
  if (viewRecup) viewRecup.classList.add('hidden');
  if (viewFacs) viewFacs.classList.add('hidden');

  const defaultBtnClass = 'px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white transition-all flex items-center whitespace-nowrap';
  if (btnGest) btnGest.className = defaultBtnClass;
  if (btnMes) btnMes.className = defaultBtnClass;
  if (btnRecup) btnRecup.className = defaultBtnClass;
  if (btnFacs) btnFacs.className = defaultBtnClass;

  if (subtab === 'gestion') {
    if (viewGest) viewGest.classList.remove('hidden');
    if (btnGest) btnGest.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 text-white transition-all shadow-md shadow-emerald-600/20 flex items-center whitespace-nowrap';
  } else if (subtab === 'cobrado_mes') {
    if (viewMes) viewMes.classList.remove('hidden');
    if (btnMes) btnMes.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 text-white transition-all shadow-md shadow-emerald-600/20 flex items-center whitespace-nowrap';
    renderCobradoMesView();
  } else if (subtab === 'recuperacion') {
    if (viewRecup) viewRecup.classList.remove('hidden');
    if (btnRecup) btnRecup.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 text-white transition-all shadow-md shadow-indigo-600/20 flex items-center whitespace-nowrap';
    renderCobranzaRecuperacion();
  } else {
    if (viewFacs) viewFacs.classList.remove('hidden');
    if (btnFacs) btnFacs.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 text-white transition-all shadow-md shadow-emerald-600/20 flex items-center whitespace-nowrap';
  }
}

// ── VISTA 2: COBRANZA ESTIMADA & COBRADO REAL POR MES ─────────────
let sortCobMesCliColumn = 'total_estimado_vence';
let sortCobMesCliAsc = false;
let currentCobMesKpiFilter = 'TODAS'; // 'TODAS', 'COBRADAS', 'PENDIENTES', 'BANCOS'
let expandedCobMesClientesSet = new Set();
let allCobMesClientesExpanded = false;

function setCobMesKpiFilter(filterKey) {
  if (currentCobMesKpiFilter === filterKey && filterKey !== 'TODAS') {
    currentCobMesKpiFilter = 'TODAS'; // Alternar/desactivar filtro
  } else {
    currentCobMesKpiFilter = filterKey;
  }
  updateCobMesKpiCardStyles();
  renderCobradoMesView();

  if (currentCobMesKpiFilter === 'BANCOS') {
    const elBancos = document.getElementById('tbody-cob-mes-pagos-recibidos');
    if (elBancos) {
      elBancos.closest('.bg-slate-900')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  } else {
    const elClis = document.getElementById('tbody-cob-mes-clientes');
    if (elClis) {
      elClis.closest('.bg-slate-900')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
}
window.setCobMesKpiFilter = setCobMesKpiFilter;

function updateCobMesKpiCardStyles() {
  const cards = {
    'TODAS': {
      cardId: 'kpi-card-cob-mes-todas',
      badgeId: 'badge-kpi-active-todas',
      ringClasses: ['ring-2', 'ring-indigo-400', 'bg-indigo-950/40', 'border-indigo-400', 'shadow-indigo-500/20'],
      title: '🎯 Cobranza Esperada (Todas las Facturas que Vencen)',
      desc: 'Mostrando todas las facturas esperadas y clientes del mes.',
      icon: 'fa-bullseye',
      iconColor: 'text-indigo-400'
    },
    'COBRADAS': {
      cardId: 'kpi-card-cob-mes-cobradas',
      badgeId: 'badge-kpi-active-cobradas',
      ringClasses: ['ring-2', 'ring-emerald-400', 'bg-emerald-950/40', 'border-emerald-400', 'shadow-emerald-500/20'],
      title: '🟢 Facturas Cobradas / Recuperación Lograda',
      desc: 'Mostrando facturas con abono o liquidadas y sus respectivos clientes.',
      icon: 'fa-circle-check',
      iconColor: 'text-emerald-400'
    },
    'PENDIENTES': {
      cardId: 'kpi-card-cob-mes-pendientes',
      badgeId: 'badge-kpi-active-pendientes',
      ringClasses: ['ring-2', 'ring-rose-400', 'bg-rose-950/40', 'border-rose-400', 'shadow-rose-500/20'],
      title: '⏳ Facturas con Saldo Aún Pendiente',
      desc: 'Mostrando facturas con saldo deudor pendiente y clientes con adeudo.',
      icon: 'fa-hourglass-half',
      iconColor: 'text-rose-400'
    },
    'BANCOS': {
      cardId: 'kpi-card-cob-mes-bancos',
      badgeId: 'badge-kpi-active-bancos',
      ringClasses: ['ring-2', 'ring-blue-400', 'bg-blue-950/40', 'border-blue-400', 'shadow-blue-500/20'],
      title: '🏦 Ingresos y Pagos Recibidos en Bancos',
      desc: 'Mostrando el detalle de transferencias y depósitos bancarios del mes.',
      icon: 'fa-building-columns',
      iconColor: 'text-blue-400'
    }
  };

  const allRingCls = [
    'ring-2', 'ring-indigo-400', 'ring-emerald-400', 'ring-rose-400', 'ring-blue-400',
    'bg-indigo-950/40', 'bg-emerald-950/40', 'bg-rose-950/40', 'bg-blue-950/40',
    'border-indigo-400', 'border-emerald-400', 'border-rose-400', 'border-blue-400',
    'shadow-indigo-500/20', 'shadow-emerald-500/20', 'shadow-rose-500/20', 'shadow-blue-500/20'
  ];

  Object.values(cards).forEach(info => {
    const elCard = document.getElementById(info.cardId);
    const elBadge = document.getElementById(info.badgeId);
    if (elCard) {
      allRingCls.forEach(c => elCard.classList.remove(c));
    }
    if (elBadge) {
      elBadge.classList.add('hidden');
    }
  });

  const banner = document.getElementById('banner-cob-mes-kpi-filter');
  const txtTitle = document.getElementById('txt-cob-mes-kpi-title');
  const txtDesc = document.getElementById('txt-cob-mes-kpi-desc');
  const badgeIcon = document.getElementById('badge-cob-mes-kpi-icon');

  if (currentCobMesKpiFilter && cards[currentCobMesKpiFilter]) {
    const act = cards[currentCobMesKpiFilter];
    const elCard = document.getElementById(act.cardId);
    const elBadge = document.getElementById(act.badgeId);
    if (elCard) {
      act.ringClasses.forEach(c => elCard.classList.add(c));
    }
    if (elBadge) {
      elBadge.classList.remove('hidden');
    }

    if (currentCobMesKpiFilter !== 'TODAS') {
      if (banner) {
        banner.classList.remove('hidden');
        banner.classList.add('flex');
      }
      if (txtTitle) txtTitle.innerText = act.title;
      if (txtDesc) txtDesc.innerText = `— ${act.desc}`;
      if (badgeIcon) badgeIcon.innerHTML = `<i class="fa-solid ${act.icon} ${act.iconColor}"></i>`;
    } else {
      if (banner) {
        banner.classList.add('hidden');
        banner.classList.remove('flex');
      }
    }
  }
}
window.updateCobMesKpiCardStyles = updateCobMesKpiCardStyles;

function toggleCobMesClienteFacturas(clienteId) {
  const k = String(clienteId);
  if (expandedCobMesClientesSet.has(k)) {
    expandedCobMesClientesSet.delete(k);
  } else {
    expandedCobMesClientesSet.add(k);
  }
  renderCobradoMesView();
}
window.toggleCobMesClienteFacturas = toggleCobMesClienteFacturas;

function toggleAllCobMesClientesFacturas() {
  allCobMesClientesExpanded = !allCobMesClientesExpanded;
  const btnIcon = document.getElementById('icon-toggle-all-cob-facs');
  const btnLbl = document.getElementById('lbl-toggle-all-cob-facs');
  if (allCobMesClientesExpanded) {
    if (btnIcon) btnIcon.className = 'fa-solid fa-chevron-up text-[10px]';
    if (btnLbl) btnLbl.innerText = 'Colapsar Facturas';
  } else {
    expandedCobMesClientesSet.clear();
    if (btnIcon) btnIcon.className = 'fa-solid fa-chevron-down text-[10px]';
    if (btnLbl) btnLbl.innerText = 'Desplegar Facturas';
  }
  renderCobradoMesView();
}
window.toggleAllCobMesClientesFacturas = toggleAllCobMesClientesFacturas;

function sortCobMesClientes(col) {
  if (sortCobMesCliColumn === col) {
    sortCobMesCliAsc = !sortCobMesCliAsc;
  } else {
    sortCobMesCliColumn = col;
    sortCobMesCliAsc = (col === 'cliente_nombre' || col === 'vendedor');
  }
  updateSortIconsCobMesClientes();
  renderCobradoMesView();
}

function updateSortIconsCobMesClientes() {
  const cols = [
    'cliente_nombre',
    'vendedor',
    'total_estimado_vence',
    'total_cobrado_vencidas',
    'saldo_pendiente_vencidas',
    'pct_recup',
    'num_facturas_vence'
  ];

  cols.forEach(c => {
    const icon = document.getElementById(`sort-icon-cmc-${c}`);
    if (!icon) return;
    if (sortCobMesCliColumn === c) {
      if (sortCobMesCliAsc) {
        icon.className = 'fa-solid fa-arrow-up-short-wide ml-1.5 text-purple-400 text-[10px]';
      } else {
        icon.className = 'fa-solid fa-arrow-down-wide-short ml-1.5 text-purple-400 text-[10px]';
      }
    } else {
      icon.className = 'fa-solid fa-sort ml-1.5 text-slate-600 group-hover:text-slate-400 text-[10px]';
    }
  });
}

function seleccionarMesCobrado(mesKey) {
  const selPeriodo = document.getElementById('cob-mes-select-periodo');
  if (selPeriodo) {
    selPeriodo.value = mesKey;
  }
  renderCobradoMesView();
}

function renderCobradoMesView() {
  const meses = cobranzaCobradoMesGlobal.meses || [];
  const selMesKey = document.getElementById('cob-mes-select-periodo')?.value || 'TODOS';
  const selVend = document.getElementById('cob-mes-select-vendedor')?.value || 'TODOS';
  const searchTxt = normalizarTexto(document.getElementById('search-cobrado-mes')?.value || '');
  const searchCliTxt = normalizarTexto(document.getElementById('search-cob-mes-clientes')?.value || '');

  // 1. Resaltar chip activo
  const containerChips = document.getElementById('container-chips-meses');
  if (containerChips) {
    const chipBtns = containerChips.querySelectorAll('button');
    chipBtns.forEach(btn => {
      if (btn.getAttribute('onclick')?.includes(`'${selMesKey}'`)) {
        btn.className = 'px-2.5 py-1 rounded-lg text-xs font-bold bg-emerald-600 text-white transition-all shadow-md shadow-emerald-600/30 whitespace-nowrap';
      } else {
        btn.className = 'px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all whitespace-nowrap';
      }
    });
  }

  // 2. Extraer y filtrar facturas y pagos según el mes y vendedor
  let facturasVencen = [];
  let pagosRecibidos = [];
  let rawClientes = [];

  if (selMesKey === 'TODOS') {
    const clisMap = {};
    meses.forEach(m => {
      (m.facturas_vencen || []).forEach(f => {
        if (selVend === 'TODOS' || normalizarTexto(f.vendedor) === normalizarTexto(selVend)) {
          facturasVencen.push(f);
        }
      });
      (m.pagos_recibidos || []).forEach(p => {
        if (selVend === 'TODOS' || normalizarTexto(p.vendedor) === normalizarTexto(selVend)) {
          pagosRecibidos.push(p);
        }
      });
      (m.clientes || []).forEach(c => {
        const k = c.cliente_id || c.cliente_nombre;
        if (!clisMap[k]) {
          clisMap[k] = {
            cliente_id: c.cliente_id,
            cliente_nombre: c.cliente_nombre,
            rfc: c.rfc,
            vendedor: c.vendedor,
            telefono: c.telefono,
            email: c.email,
            total_estimado_vence: 0,
            total_cobrado_vencidas: 0,
            saldo_pendiente_vencidas: 0,
            num_facturas_vence: 0,
            total_cobrado_real: 0,
            num_pagos_real: 0,
            saldo_actual_cliente: c.saldo_actual_cliente,
            facturas: []
          };
        }
        clisMap[k].total_estimado_vence += (c.total_estimado_vence || 0);
        clisMap[k].total_cobrado_vencidas += (c.total_cobrado_vencidas || 0);
        clisMap[k].saldo_pendiente_vencidas += (c.saldo_pendiente_vencidas || 0);
        clisMap[k].num_facturas_vence += (c.num_facturas_vence || 0);
        clisMap[k].total_cobrado_real += (c.total_cobrado_real || 0);
        clisMap[k].num_pagos_real += (c.num_pagos_real || 0);
        if (c.facturas && c.facturas.length) {
          clisMap[k].facturas.push(...c.facturas);
        }
      });
    });
    rawClientes = Object.values(clisMap);
  } else {
    const mesObj = meses.find(m => m.mes_key === selMesKey);
    if (mesObj) {
      (mesObj.facturas_vencen || []).forEach(f => {
        if (selVend === 'TODOS' || normalizarTexto(f.vendedor) === normalizarTexto(selVend)) {
          facturasVencen.push(f);
        }
      });
      (mesObj.pagos_recibidos || []).forEach(p => {
        if (selVend === 'TODOS' || normalizarTexto(p.vendedor) === normalizarTexto(selVend)) {
          pagosRecibidos.push(p);
        }
      });
      (mesObj.clientes || []).forEach(c => {
        rawClientes.push(Object.assign({}, c));
      });
    }
  }

  // Filtrado de facturas y pagos por buscador global
  if (searchTxt) {
    facturasVencen = facturasVencen.filter(f => {
      const matchFolio = normalizarTexto(f.name || f.folio || '').includes(searchTxt);
      const matchCli = normalizarTexto(f.cliente || f.partner_name || '').includes(searchTxt);
      const matchRfc = normalizarTexto(f.rfc || '').includes(searchTxt);
      const matchVend = normalizarTexto(f.vendedor || '').includes(searchTxt);
      return matchFolio || matchCli || matchRfc || matchVend;
    });

    pagosRecibidos = pagosRecibidos.filter(p => {
      const matchFolio = normalizarTexto(p.folio || p.name || '').includes(searchTxt);
      const matchCli = normalizarTexto(p.cliente || p.cliente_nombre || '').includes(searchTxt);
      const matchRfc = normalizarTexto(p.rfc || '').includes(searchTxt);
      const matchVend = normalizarTexto(p.vendedor || '').includes(searchTxt);
      const matchMemo = normalizarTexto(p.memo || '').includes(searchTxt);
      const matchDiario = normalizarTexto(p.diario || '').includes(searchTxt);
      return matchFolio || matchCli || matchRfc || matchVend || matchMemo || matchDiario;
    });
  }

  // Totales generales para los 4 KPIs (antes de filtrar por tarjeta para reflejar el mes)
  const totEstimadoVence = facturasVencen.reduce((s, f) => s + (f.total_factura || f.amount_total || f.total || 0), 0);
  const totCobradoVencidas = facturasVencen.reduce((s, f) => s + (f.monto_abonado || ((f.total_factura || f.amount_total || 0) - (f.saldo_pendiente || f.amount_residual || 0))), 0);
  const totPendienteVencidas = facturasVencen.reduce((s, f) => s + (f.saldo_pendiente || f.amount_residual || 0), 0);
  const totCobradoReal = pagosRecibidos.reduce((s, p) => s + (p.monto || 0), 0);

  const pctCumplimiento = totEstimadoVence > 0 ? (totCobradoVencidas / totEstimadoVence * 100) : (totCobradoReal > 0 ? 100 : 0);

  // Actualizar DOM de KPIs
  const elEst = document.getElementById('kpi-cob-mes-estimado');
  const elEstSub = document.getElementById('kpi-cob-mes-estimado-sub');
  const elCobVenc = document.getElementById('kpi-cob-mes-cobrado-vencidas');
  const elEfSub = document.getElementById('kpi-cob-mes-efectividad-sub');
  const elPen = document.getElementById('kpi-cob-mes-pendiente');
  const elPenSub = document.getElementById('kpi-cob-mes-pendiente-sub');
  const elCob = document.getElementById('kpi-cob-mes-cobrado');
  const elCobSub = document.getElementById('kpi-cob-mes-cobrado-sub');

  if (elEst) elEst.innerText = fmtMxn(totEstimadoVence);
  if (elEstSub) elEstSub.innerText = `${facturasVencen.length} facturas con vencimiento en el mes`;
  if (elCobVenc) elCobVenc.innerText = fmtMxn(totCobradoVencidas);
  if (elEfSub) elEfSub.innerText = `${pctCumplimiento.toFixed(1)}% de recuperación lograda`;
  if (elPen) elPen.innerText = fmtMxn(totPendienteVencidas);
  if (elPenSub) elPenSub.innerText = `Saldo pendiente de facturas que vencen`;
  if (elCob) elCob.innerText = fmtMxn(totCobradoReal);
  if (elCobSub) elCobSub.innerText = `${pagosRecibidos.length} pagos recibidos en bancos en total`;

  // Sincronizar estilo visual de las tarjetas KPI activas
  updateCobMesKpiCardStyles();

  // Filtrado de Clientes base
  let clientesVence = rawClientes.filter(c => {
    if (selVend !== 'TODOS' && normalizarTexto(c.vendedor) !== normalizarTexto(selVend)) return false;
    if ((c.total_estimado_vence || 0) <= 0.001 && (c.num_facturas_vence || 0) === 0) return false;
    
    const qSearch = searchCliTxt || searchTxt;
    if (qSearch) {
      const matchCli = normalizarTexto(c.cliente_nombre || '').includes(qSearch);
      const matchRfc = normalizarTexto(c.rfc || '').includes(qSearch);
      const matchVend = normalizarTexto(c.vendedor || '').includes(qSearch);
      const matchTel = normalizarTexto(c.telefono || '').includes(qSearch);
      return matchCli || matchRfc || matchVend || matchTel;
    }
    return true;
  });

  // APLICAR FILTRO DE LA TARJETA KPI SELECCIONADA A FACTURAS Y CLIENTES
  let facturasFiltradas = [...facturasVencen];
  let clientesFiltrados = [...clientesVence];

  if (currentCobMesKpiFilter === 'COBRADAS') {
    // Facturas con abonos o pagadas
    facturasFiltradas = facturasVencen.filter(f => {
      const sal = f.saldo_pendiente || f.amount_residual || 0;
      const tot = f.total_factura || f.amount_total || f.total || 0;
      const abo = f.monto_abonado || (tot - sal);
      return abo > 0.01 || sal <= 0.01;
    });
    // Clientes que tuvieron cobranza recuperada
    clientesFiltrados = clientesVence.filter(c => (c.total_cobrado_vencidas || 0) > 0.01);
  } else if (currentCobMesKpiFilter === 'PENDIENTES') {
    // Facturas con saldo pendiente
    facturasFiltradas = facturasVencen.filter(f => {
      const sal = f.saldo_pendiente || f.amount_residual || 0;
      return sal > 0.01;
    });
    // Clientes que deben saldo pendiente
    clientesFiltrados = clientesVence.filter(c => (c.saldo_pendiente_vencidas || 0) > 0.01);
  }

  // Ordenamiento de Clientes
  clientesFiltrados.sort((a, b) => {
    let valA, valB;
    if (sortCobMesCliColumn === 'cliente_nombre') {
      valA = (a.cliente_nombre || '').toLowerCase();
      valB = (b.cliente_nombre || '').toLowerCase();
      return sortCobMesCliAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    } else if (sortCobMesCliColumn === 'vendedor') {
      valA = (a.vendedor || '').toLowerCase();
      valB = (b.vendedor || '').toLowerCase();
      return sortCobMesCliAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    } else if (sortCobMesCliColumn === 'pct_recup') {
      valA = (a.total_estimado_vence || 0) > 0 ? ((a.total_cobrado_vencidas || 0) / a.total_estimado_vence * 100) : 0;
      valB = (b.total_estimado_vence || 0) > 0 ? ((b.total_cobrado_vencidas || 0) / b.total_estimado_vence * 100) : 0;
      return sortCobMesCliAsc ? (valA - valB) : (valB - valA);
    } else if (sortCobMesCliColumn === 'num_facturas_vence') {
      valA = a.num_facturas_vence || 0;
      valB = b.num_facturas_vence || 0;
      return sortCobMesCliAsc ? (valA - valB) : (valB - valA);
    } else if (sortCobMesCliColumn === 'total_cobrado_vencidas') {
      valA = a.total_cobrado_vencidas || 0;
      valB = b.total_cobrado_vencidas || 0;
      return sortCobMesCliAsc ? (valA - valB) : (valB - valA);
    } else if (sortCobMesCliColumn === 'saldo_pendiente_vencidas') {
      valA = a.saldo_pendiente_vencidas || 0;
      valB = b.saldo_pendiente_vencidas || 0;
      return sortCobMesCliAsc ? (valA - valB) : (valB - valA);
    } else {
      valA = a.total_estimado_vence || 0;
      valB = b.total_estimado_vence || 0;
      return sortCobMesCliAsc ? (valA - valB) : (valB - valA);
    }
  });

  // Actualizar labels de cabecera
  const mesObjSelected = meses.find(m => m.mes_key === selMesKey);
  const nombreMesSeleccionado = selMesKey === 'TODOS' ? 'Histórico Completo' : (mesObjSelected ? mesObjSelected.mes_nombre : selMesKey);

  const elLblHist = document.getElementById('lbl-cob-mes-hist-resumen');
  if (elLblHist) elLblHist.innerText = `${meses.length} meses registrados`;

  const elLblClisPer = document.getElementById('lbl-cob-mes-clis-periodo');
  if (elLblClisPer) {
    let extraFilter = '';
    if (currentCobMesKpiFilter === 'COBRADAS') extraFilter = ' — Solo Cobradas';
    else if (currentCobMesKpiFilter === 'PENDIENTES') extraFilter = ' — Solo con Saldo Pendiente';
    elLblClisPer.innerText = `${nombreMesSeleccionado}${extraFilter}`;
  }

  const elLblClisCnt = document.getElementById('lbl-cob-mes-clis-count');
  if (elLblClisCnt) {
    if (currentCobMesKpiFilter !== 'TODAS' && currentCobMesKpiFilter !== 'BANCOS') {
      elLblClisCnt.innerText = `${clientesFiltrados.length} de ${clientesVence.length} clientes`;
    } else {
      elLblClisCnt.innerText = `${clientesFiltrados.length} clientes`;
    }
  }

  const elLblFacsPer = document.getElementById('lbl-cob-mes-facs-periodo');
  if (elLblFacsPer) {
    let extraFilter = '';
    if (currentCobMesKpiFilter === 'COBRADAS') extraFilter = ' — Solo Cobradas';
    else if (currentCobMesKpiFilter === 'PENDIENTES') extraFilter = ' — Solo con Saldo Pendiente';
    elLblFacsPer.innerText = `${nombreMesSeleccionado}${extraFilter}`;
  }

  const elLblFacsCnt = document.getElementById('lbl-cob-mes-facs-count');
  if (elLblFacsCnt) {
    if (currentCobMesKpiFilter !== 'TODAS' && currentCobMesKpiFilter !== 'BANCOS') {
      elLblFacsCnt.innerText = `${facturasFiltradas.length} de ${facturasVencen.length} facturas`;
    } else {
      elLblFacsCnt.innerText = `${facturasFiltradas.length} facturas con vencimiento`;
    }
  }

  const elLblPagosPer = document.getElementById('lbl-cob-mes-pagos-periodo');
  if (elLblPagosPer) elLblPagosPer.innerText = nombreMesSeleccionado;

  const elLblPagosCnt = document.getElementById('lbl-cob-mes-pagos-count');
  if (elLblPagosCnt) elLblPagosCnt.innerText = `${pagosRecibidos.length} pagos bancarios`;

  // ─────────────────────────────────────────────────────────────
  // TABLA 1: MATRIZ MENSUAL (ESTIMADO VS COBRADO VS PENDIENTE)
  // ─────────────────────────────────────────────────────────────
  const tbodyHist = document.getElementById('tbody-cob-mes-historico');
  if (tbodyHist) {
    tbodyHist.innerHTML = '';
    let sumEst = 0;
    let sumFacs = 0;
    let sumCobVencidas = 0;
    let sumPend = 0;
    let sumCobReal = 0;
    let sumPagos = 0;

    meses.forEach(m => {
      const isSelected = (m.mes_key === selMesKey);
      const estM = m.cobranza_estimada_vence || 0;
      const facsM = m.facturas_vencen_count || (m.facturas_vencen ? m.facturas_vencen.length : 0);
      const cobVencM = m.cobrado_de_vencidas || 0;
      const pendM = m.saldo_pendiente_vencidas || m.saldo_pendiente || 0;
      const pctM = m.pct_cumplimiento_vence || (estM > 0 ? (cobVencM / estM * 100) : 0);
      const cobRealM = m.cobrado_real_pagos || m.total_cobrado || 0;
      const pagosM = m.num_pagos_recibidos || m.num_pagos || 0;

      sumEst += estM;
      sumFacs += facsM;
      sumCobVencidas += cobVencM;
      sumPend += pendM;
      sumCobReal += cobRealM;
      sumPagos += pagosM;

      let barColor = 'bg-emerald-500';
      let textColor = 'text-emerald-400';
      if (pctM < 40) { barColor = 'bg-rose-500'; textColor = 'text-rose-400'; }
      else if (pctM < 75) { barColor = 'bg-amber-500'; textColor = 'text-amber-400'; }

      const tr = document.createElement('tr');
      tr.className = `transition-colors hover:bg-slate-800/60 ${isSelected ? 'bg-emerald-950/50 font-bold border-l-4 border-emerald-400' : ''}`;
      tr.innerHTML = `
        <td class="p-3 font-bold text-white flex items-center">
          <i class="fa-solid fa-calendar-check text-emerald-400 mr-2 text-xs"></i>
          ${m.mes_nombre}
          ${isSelected ? '<span class="ml-2 px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[9px] uppercase font-bold">Activo</span>' : ''}
        </td>
        <td class="p-3 text-right font-mono font-bold text-indigo-300 bg-indigo-950/20">${fmtMxn(estM)}</td>
        <td class="p-3 text-center font-mono text-slate-300">${facsM}</td>
        <td class="p-3 text-right font-mono font-bold text-emerald-400 bg-emerald-500/5">${fmtMxn(cobVencM)}</td>
        <td class="p-3 text-right font-mono font-bold text-rose-400">${fmtMxn(pendM)}</td>
        <td class="p-3 text-center">
          <div class="flex items-center justify-center space-x-2">
            <div class="w-14 bg-slate-800 rounded-full h-1.5 overflow-hidden border border-slate-700">
              <div class="${barColor} h-1.5 rounded-full transition-all duration-300" style="width: ${Math.min(100, Math.max(0, pctM))}%"></div>
            </div>
            <span class="text-[11px] font-mono font-bold ${textColor}">${pctM.toFixed(1)}%</span>
          </div>
        </td>
        <td class="p-3 text-right font-mono font-bold text-blue-400 bg-blue-950/20">${fmtMxn(cobRealM)}</td>
        <td class="p-3 text-center font-mono text-slate-300">${pagosM}</td>
        <td class="p-3 text-center">
          <button onclick="seleccionarMesCobrado('${m.mes_key}')" class="px-2.5 py-1 rounded-lg text-[10px] font-bold ${isSelected ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-600/30' : 'bg-slate-800 hover:bg-slate-700 text-slate-300'} transition-all flex items-center mx-auto">
            <i class="fa-solid fa-eye mr-1"></i> ${isSelected ? 'Viendo' : 'Ver Mes'}
          </button>
        </td>
      `;
      tbodyHist.appendChild(tr);
    });

    // Fila de Totales Generales
    const trTot = document.createElement('tr');
    trTot.className = 'bg-slate-900 font-black text-white border-t-2 border-slate-700';
    const pctTot = sumEst > 0 ? (sumCobVencidas / sumEst * 100) : 0;
    trTot.innerHTML = `
      <td class="p-3 text-emerald-300 uppercase tracking-wider font-black">TOTAL HISTÓRICO CONSOLIDADO</td>
      <td class="p-3 text-right font-mono font-black text-indigo-300 bg-indigo-950/30">${fmtMxn(sumEst)}</td>
      <td class="p-3 text-center font-mono text-white font-black">${sumFacs}</td>
      <td class="p-3 text-right font-mono font-black text-emerald-400 bg-emerald-500/10">${fmtMxn(sumCobVencidas)}</td>
      <td class="p-3 text-right font-mono font-black text-rose-400">${fmtMxn(sumPend)}</td>
      <td class="p-3 text-center font-mono font-bold text-purple-300">${pctTot.toFixed(1)}%</td>
      <td class="p-3 text-right font-mono font-black text-blue-400 bg-blue-950/30">${fmtMxn(sumCobReal)}</td>
      <td class="p-3 text-center font-mono text-white font-black">${sumPagos}</td>
      <td class="p-3 text-center">
        <button onclick="seleccionarMesCobrado('TODOS')" class="px-2.5 py-1 rounded-lg text-[10px] font-bold ${selMesKey === 'TODOS' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-300'}">
          ${selMesKey === 'TODOS' ? 'Viendo Todos' : 'Ver Todos'}
        </button>
      </td>
    `;
    tbodyHist.appendChild(trTot);
  }

  // ─────────────────────────────────────────────────────────────
  // TABLA 2: CLIENTES CON VENCIMIENTO EN EL MES (DESGLOSE INLINE DE FACTURAS)
  // ─────────────────────────────────────────────────────────────
  const tbodyClis = document.getElementById('tbody-cob-mes-clientes');
  if (tbodyClis) {
    tbodyClis.innerHTML = '';
    if (clientesFiltrados.length === 0) {
      tbodyClis.innerHTML = `
        <tr>
          <td colspan="11" class="p-8 text-center text-slate-400 italic">
            <i class="fa-solid fa-users-slash text-2xl text-slate-600 mb-2 block"></i>
            No se encontraron clientes que coincidan con los filtros en ${nombreMesSeleccionado}.
          </td>
        </tr>
      `;
    } else {
      let sumEstCli = 0, sumCobCli = 0, sumPendCli = 0, sumFacsCli = 0;
      clientesFiltrados.forEach((c, idx) => {
        const est = c.total_estimado_vence || 0;
        const cob = c.total_cobrado_vencidas || 0;
        const pend = c.saldo_pendiente_vencidas || 0;
        const facs = c.num_facturas_vence || 0;
        const pct = est > 0 ? (cob / est * 100) : 0;
        const cKey = String(c.cliente_id || `cli-${idx}`);
        const isExpanded = allCobMesClientesExpanded || expandedCobMesClientesSet.has(cKey);

        sumEstCli += est;
        sumCobCli += cob;
        sumPendCli += pend;
        sumFacsCli += facs;

        let badgeEstado = '';
        if (pend <= 0.01) {
          badgeEstado = '<span class="px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 font-bold text-[10px]">🟢 100% Pagado</span>';
        } else if (cob > 0.01) {
          badgeEstado = '<span class="px-2 py-0.5 rounded-full bg-amber-950/60 border border-amber-500/30 text-amber-300 font-bold text-[10px]">🟡 Abono Parcial</span>';
        } else {
          badgeEstado = '<span class="px-2 py-0.5 rounded-full bg-rose-950/60 border border-rose-500/30 text-rose-300 font-bold text-[10px]">🚨 Sin Pago</span>';
        }

        let barColor = 'bg-emerald-500';
        let textColor = 'text-emerald-400';
        if (pct < 40) { barColor = 'bg-rose-500'; textColor = 'text-rose-400'; }
        else if (pct < 75) { barColor = 'bg-amber-500'; textColor = 'text-amber-400'; }

        // Fila principal del Cliente
        const tr = document.createElement('tr');
        tr.className = `hover:bg-slate-800/60 transition-colors border-b border-slate-800/60 ${isExpanded ? 'bg-slate-900/90' : ''}`;
        tr.innerHTML = `
          <td class="p-3 text-center font-mono text-slate-500 text-xs">${idx + 1}</td>
          <td class="p-3">
            <div class="flex items-center space-x-1.5">
              <button onclick="toggleCobMesClienteFacturas('${cKey}')" class="p-1 rounded text-purple-400 hover:text-white hover:bg-purple-900/40 transition-all flex-shrink-0" title="${isExpanded ? 'Ocultar facturas del cliente' : 'Desplegar facturas del cliente'}">
                <i class="fa-solid fa-chevron-${isExpanded ? 'down' : 'right'} text-[11px] transition-transform"></i>
              </button>
              <div class="font-bold text-white text-xs hover:text-purple-300 cursor-pointer flex items-center" onclick="abrirModalHistorialCliente('${c.cliente_id || ''}', '${escapeJs(c.cliente_nombre)}')" title="Ver Estado de Cuenta 360°">
                <i class="fa-solid fa-user-tie text-purple-400 mr-1.5 text-xs"></i>
                <span class="truncate max-w-[220px]" title="${escapeHtml(c.cliente_nombre)}">${escapeHtml(c.cliente_nombre || '—')}</span>
              </div>
            </div>
          </td>
          <td class="p-3 text-xs text-slate-300">${escapeHtml(c.vendedor || 'Sin Asignar')}</td>
          <td class="p-3 text-center font-mono text-[11px] text-slate-400">
            <div>${escapeHtml(c.rfc || '—')}</div>
            ${c.telefono ? `<div class="text-[10px] text-slate-500"><i class="fa-solid fa-phone text-[9px] mr-1"></i>${escapeHtml(c.telefono)}</div>` : ''}
          </td>
          <td class="p-3 text-right font-mono font-bold text-indigo-300 bg-indigo-950/20 text-xs">${fmtMxn(est)}</td>
          <td class="p-3 text-right font-mono font-bold text-emerald-400 bg-emerald-500/5 text-xs">${fmtMxn(cob)}</td>
          <td class="p-3 text-right font-mono font-black ${pend > 0.01 ? 'text-rose-400' : 'text-slate-400'} text-xs">${fmtMxn(pend)}</td>
          <td class="p-3 text-center">
            <div class="flex items-center justify-center space-x-2">
              <div class="w-14 bg-slate-800 rounded-full h-1.5 overflow-hidden border border-slate-700">
                <div class="${barColor} h-1.5 rounded-full transition-all duration-300" style="width: ${Math.min(100, Math.max(0, pct))}%"></div>
              </div>
              <span class="text-[11px] font-mono font-bold ${textColor}">${pct.toFixed(1)}%</span>
            </div>
          </td>
          <td class="p-3 text-center">
            <button onclick="toggleCobMesClienteFacturas('${cKey}')" class="px-2.5 py-1 rounded-lg text-xs font-bold ${isExpanded ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30' : 'bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-indigo-500/30'} transition-all inline-flex items-center space-x-1.5" title="Clic para ver/ocultar las facturas de este cliente">
              <i class="fa-solid fa-file-invoice text-[10px]"></i>
              <span>${facs} facs</span>
              <i class="fa-solid fa-chevron-${isExpanded ? 'up' : 'down'} text-[9px]"></i>
            </button>
          </td>
          <td class="p-3 text-center">${badgeEstado}</td>
          <td class="p-3 text-center">
            <button onclick="abrirModalHistorialCliente('${c.cliente_id || ''}', '${escapeJs(c.cliente_nombre)}')" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-purple-600/80 hover:bg-purple-600 text-white shadow-sm shadow-purple-600/30 transition-all flex items-center mx-auto whitespace-nowrap">
              <i class="fa-solid fa-folder-open mr-1"></i> Ver Cuenta
            </button>
          </td>
        `;
        tbodyClis.appendChild(tr);

        // Si está desplegado, insertar subtabla inline con las facturas del cliente
        if (isExpanded) {
          let cFacturas = (c.facturas && c.facturas.length > 0)
            ? c.facturas
            : facturasVencen.filter(f => (f.cliente_id && String(f.cliente_id) === String(c.cliente_id)) || (f.cliente && normalizarTexto(f.cliente) === normalizarTexto(c.cliente_nombre)));

          // Si hay filtro activo por KPI, aplicar también a las facturas inline del cliente
          if (currentCobMesKpiFilter === 'COBRADAS') {
            cFacturas = cFacturas.filter(f => {
              const sal = f.saldo_pendiente || f.amount_residual || 0;
              const tot = f.total_factura || f.amount_total || f.total || 0;
              const abo = f.monto_abonado || (tot - sal);
              return abo > 0.01 || sal <= 0.01;
            });
          } else if (currentCobMesKpiFilter === 'PENDIENTES') {
            cFacturas = cFacturas.filter(f => (f.saldo_pendiente || f.amount_residual || 0) > 0.01);
          }

          const trSub = document.createElement('tr');
          trSub.className = 'bg-slate-950/95 border-b-2 border-indigo-500/40 shadow-inner';
          trSub.innerHTML = `
            <td colspan="11" class="p-3 sm:p-4 pl-6 sm:pl-10">
              <div class="bg-slate-900 border border-indigo-500/30 rounded-2xl p-3 sm:p-4 shadow-xl space-y-3">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
                  <div class="flex items-center space-x-2">
                    <span class="w-6 h-6 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-xs">
                      <i class="fa-solid fa-file-invoice"></i>
                    </span>
                    <span class="text-xs font-bold text-white">
                      Facturas de <span class="text-indigo-300 font-extrabold">${escapeHtml(c.cliente_nombre)}</span>
                    </span>
                    <span class="text-[10px] font-bold text-indigo-300 bg-indigo-950/80 border border-indigo-800 px-2 py-0.5 rounded-full">
                      ${cFacturas.length} factura(s) ${currentCobMesKpiFilter !== 'TODAS' ? `(filtradas por ${currentCobMesKpiFilter})` : 'en este período'}
                    </span>
                  </div>
                  <div class="flex items-center space-x-2">
                    <button onclick="abrirModalHistorialCliente('${c.cliente_id || ''}', '${escapeJs(c.cliente_nombre)}')" class="text-[11px] font-bold text-purple-400 hover:text-purple-300 flex items-center transition-colors">
                      <i class="fa-solid fa-folder-open mr-1"></i> Ver Cuenta 360° Completa
                    </button>
                    <button onclick="toggleCobMesClienteFacturas('${cKey}')" class="text-[11px] text-slate-500 hover:text-slate-300 ml-2">
                      <i class="fa-solid fa-xmark"></i> Cerrar
                    </button>
                  </div>
                </div>

                ${cFacturas.length === 0 ? `
                  <div class="p-4 text-center text-slate-400 italic text-xs">
                    No se encontraron facturas que coincidan con el filtro seleccionado para este cliente.
                  </div>
                ` : `
                  <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/70">
                    <table class="w-full text-left text-xs text-slate-300">
                      <thead class="bg-slate-900/90 text-slate-400 font-bold uppercase text-[9px] tracking-wider border-b border-slate-800">
                        <tr>
                          <th class="p-2.5 text-center w-8">#</th>
                          <th class="p-2.5">Folio Factura</th>
                          <th class="p-2.5 text-center">Emisión</th>
                          <th class="p-2.5 text-center">Vencimiento</th>
                          <th class="p-2.5 text-center">Retraso</th>
                          <th class="p-2.5 text-right text-indigo-300">Total Factura ($)</th>
                          <th class="p-2.5 text-right text-emerald-400">Abonado ($)</th>
                          <th class="p-2.5 text-right text-rose-400">Saldo Pendiente ($)</th>
                          <th class="p-2.5 text-center">Estatus</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-slate-800/50 font-mono text-[11px]">
                        ${cFacturas.map((cf, cidx) => {
                          const cTot = cf.total_factura || cf.amount_total || cf.total || 0;
                          const cSal = cf.saldo_pendiente || cf.amount_residual || 0;
                          const cAbo = cf.monto_abonado || (cTot - cSal);
                          const cDue = cf.fecha_vencimiento || cf.invoice_date_due || '—';
                          const cEmi = cf.fecha_emision || cf.invoice_date || '—';
                          const cRetr = cf.dias_retraso || 0;
                          const cFolio = cf.folio || cf.name || '—';

                          let cBadge = '';
                          if (cSal <= 0.01) {
                            cBadge = '<span class="px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 font-bold text-[9px] font-sans">🟢 Pagada</span>';
                          } else if (cAbo > 0.01) {
                            cBadge = '<span class="px-2 py-0.5 rounded-full bg-amber-950/80 border border-amber-500/40 text-amber-300 font-bold text-[9px] font-sans">🟡 Parcial</span>';
                          } else {
                            cBadge = '<span class="px-2 py-0.5 rounded-full bg-rose-950/80 border border-rose-500/40 text-rose-300 font-bold text-[9px] font-sans">🚨 Pendiente</span>';
                          }

                          return `
                            <tr class="hover:bg-slate-800/50 transition-colors">
                              <td class="p-2.5 text-center text-slate-500">${cidx + 1}</td>
                              <td class="p-2.5 font-bold text-indigo-300">
                                <div class="flex items-center space-x-1.5">
                                  <i class="fa-solid fa-file-invoice text-indigo-400 text-[10px]"></i>
                                  <span>${escapeHtml(cFolio)}</span>
                                </div>
                              </td>
                              <td class="p-2.5 text-center text-slate-400 font-sans">${cEmi}</td>
                              <td class="p-2.5 text-center font-bold ${cRetr > 0 ? 'text-rose-400 bg-rose-950/20' : 'text-indigo-300'} font-sans">${cDue}</td>
                              <td class="p-2.5 text-center font-sans ${cRetr > 0 ? 'text-rose-400 font-bold' : 'text-slate-500'}">
                                ${cRetr > 0 ? `<span class="px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 text-[9px]">${cRetr} d vencida</span>` : 'Al corriente'}
                              </td>
                              <td class="p-2.5 text-right font-bold text-indigo-200 bg-indigo-950/10">${fmtMxn(cTot)}</td>
                              <td class="p-2.5 text-right font-bold text-emerald-400 bg-emerald-500/5">${fmtMxn(cAbo)}</td>
                              <td class="p-2.5 text-right font-black ${cSal > 0.01 ? 'text-rose-400' : 'text-slate-400'}">${fmtMxn(cSal)}</td>
                              <td class="p-2.5 text-center">${cBadge}</td>
                            </tr>
                          `;
                        }).join('')}
                      </tbody>
                    </table>
                  </div>
                `}
              </div>
            </td>
          `;
          tbodyClis.appendChild(trSub);
        }
      });

      // Fila de Totales de Clientes
      const trTotCli = document.createElement('tr');
      trTotCli.className = 'bg-slate-900 font-black text-white border-t-2 border-slate-700';
      const pctTotCli = sumEstCli > 0 ? (sumCobCli / sumEstCli * 100) : 0;
      trTotCli.innerHTML = `
        <td class="p-3 text-center font-mono text-slate-500 text-xs font-black">∑</td>
        <td class="p-3 text-purple-300 uppercase tracking-wider font-black">TOTAL ${clientesFiltrados.length} CLIENTES</td>
        <td class="p-3"></td>
        <td class="p-3"></td>
        <td class="p-3 text-right font-mono font-black text-indigo-300 bg-indigo-950/40 text-xs">${fmtMxn(sumEstCli)}</td>
        <td class="p-3 text-right font-mono font-black text-emerald-400 bg-emerald-500/10 text-xs">${fmtMxn(sumCobCli)}</td>
        <td class="p-3 text-right font-mono font-black text-rose-400 text-xs">${fmtMxn(sumPendCli)}</td>
        <td class="p-3 text-center font-mono font-bold text-purple-300 text-xs">${pctTotCli.toFixed(1)}%</td>
        <td class="p-3 text-center font-mono font-bold text-white text-xs">${sumFacsCli}</td>
        <td colspan="2" class="p-3 text-center text-slate-500 text-[10px]">Consolidado ${currentCobMesKpiFilter !== 'TODAS' ? `(${currentCobMesKpiFilter})` : 'del Mes'}</td>
      `;
      tbodyClis.appendChild(trTotCli);
    }
  }

  // ─────────────────────────────────────────────────────────────
  // TABLA 3: FACTURAS CON VENCIMIENTO EN EL MES
  // ─────────────────────────────────────────────────────────────
  const tbodyFacs = document.getElementById('tbody-cob-mes-facturas-vencen');
  if (tbodyFacs) {
    tbodyFacs.innerHTML = '';
    if (facturasFiltradas.length === 0) {
      tbodyFacs.innerHTML = `
        <tr>
          <td colspan="11" class="p-8 text-center text-slate-400 italic">
            <i class="fa-solid fa-file-invoice text-2xl text-slate-600 mb-2 block"></i>
            No se encontraron facturas que coincidan con los filtros en ${nombreMesSeleccionado}.
          </td>
        </tr>
      `;
    } else {
      facturasFiltradas.forEach((f, idx) => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-800/50 transition-colors border-b border-slate-800/60';

        const totFac = f.total_factura || f.amount_total || f.total || 0;
        const saldo = f.saldo_pendiente || f.amount_residual || 0;
        const abonado = f.monto_abonado || (totFac - saldo);
        const fFolio = f.folio || f.name || '—';
        const fCli = f.cliente || f.partner_name || '—';
        const fEmi = f.fecha_emision || f.invoice_date || '—';
        const fDue = f.fecha_vencimiento || f.invoice_date_due || '—';

        let badgeEstado = '';
        if (saldo <= 0.01) {
          badgeEstado = '<span class="px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 font-bold text-[10px]">🟢 Pagada</span>';
        } else if (abonado > 0) {
          badgeEstado = '<span class="px-2 py-0.5 rounded-full bg-amber-950/60 border border-amber-500/30 text-amber-300 font-bold text-[10px]">🟡 Abono Parcial</span>';
        } else {
          badgeEstado = '<span class="px-2 py-0.5 rounded-full bg-rose-950/60 border border-rose-500/30 text-rose-300 font-bold text-[10px]">🚨 Pendiente</span>';
        }

        tr.innerHTML = `
          <td class="p-3 text-center font-mono text-slate-500 text-xs">${idx + 1}</td>
          <td class="p-3 font-mono font-bold text-indigo-300 text-xs">
            <div class="flex items-center space-x-1.5">
              <i class="fa-solid fa-file-invoice text-[11px] text-indigo-400"></i>
              <span>${escapeHtml(fFolio)}</span>
            </div>
          </td>
          <td class="p-3">
            <div class="font-bold text-white text-xs hover:text-emerald-300 cursor-pointer flex items-center" onclick="abrirModalHistorialCliente('${f.cliente_id || f.partner_id || ''}', '${escapeJs(fCli)}')" title="Ver estado de cuenta 360°">
              <i class="fa-solid fa-building text-slate-500 mr-1.5 text-[10px]"></i>
              <span class="truncate max-w-[220px]" title="${escapeHtml(fCli)}">${escapeHtml(fCli)}</span>
            </div>
          </td>
          <td class="p-3 text-center font-mono text-[11px] text-slate-300">${escapeHtml(f.rfc || '—')}</td>
          <td class="p-3 text-xs text-slate-300">${escapeHtml(f.vendedor || 'Sin Asignar')}</td>
          <td class="p-3 text-center font-mono text-xs text-slate-400">${fEmi}</td>
          <td class="p-3 text-center font-mono text-xs font-bold text-indigo-300 bg-indigo-950/20">${fDue}</td>
          <td class="p-3 text-right font-mono font-bold text-indigo-200 bg-indigo-950/10 text-xs">${fmtMxn(totFac)}</td>
          <td class="p-3 text-right font-mono font-bold text-emerald-400 text-xs">${fmtMxn(abonado)}</td>
          <td class="p-3 text-right font-mono font-black ${saldo > 0 ? 'text-rose-400' : 'text-slate-400'} text-xs">${fmtMxn(saldo)}</td>
          <td class="p-3 text-center">${badgeEstado}</td>
        `;
        tbodyFacs.appendChild(tr);
      });
    }
  }

  // ─────────────────────────────────────────────────────────────
  // TABLA 4: PAGOS Y ABONOS RECIBIDOS EN EL MES
  // ─────────────────────────────────────────────────────────────
  const tbodyPagos = document.getElementById('tbody-cob-mes-pagos-recibidos');
  if (tbodyPagos) {
    tbodyPagos.innerHTML = '';
    if (pagosRecibidos.length === 0) {
      tbodyPagos.innerHTML = `
        <tr>
          <td colspan="9" class="p-8 text-center text-slate-400 italic">
            <i class="fa-solid fa-receipt text-2xl text-slate-600 mb-2 block"></i>
            No se encontraron pagos bancarios registrados en ${nombreMesSeleccionado}.
          </td>
        </tr>
      `;
    } else {
      pagosRecibidos.forEach((p, idx) => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-800/50 transition-colors border-b border-slate-800/60';

        tr.innerHTML = `
          <td class="p-3 text-center font-mono text-slate-500 text-xs">${idx + 1}</td>
          <td class="p-3 text-center font-mono font-bold text-emerald-300 text-xs">${p.fecha || '—'}</td>
          <td class="p-3 font-mono font-bold text-white text-xs">
            <div class="flex items-center space-x-1.5">
              <i class="fa-solid fa-receipt text-emerald-400 text-[10px]"></i>
              <span>${escapeHtml(p.folio || p.name || '—')}</span>
            </div>
          </td>
          <td class="p-3">
            <div class="font-bold text-white text-xs hover:text-emerald-300 cursor-pointer flex items-center" onclick="abrirModalHistorialCliente('${p.cliente_id || ''}', '${escapeJs(p.cliente || p.cliente_nombre || '')}')" title="Ver estado de cuenta 360°">
              <i class="fa-solid fa-building text-slate-500 mr-1.5 text-[10px]"></i>
              <span class="truncate max-w-[220px]" title="${escapeHtml(p.cliente || p.cliente_nombre || '')}">${escapeHtml(p.cliente || p.cliente_nombre || '—')}</span>
            </div>
          </td>
          <td class="p-3 text-xs text-slate-300">${escapeHtml(p.vendedor || 'Sin Asignar')}</td>
          <td class="p-3 text-xs text-blue-300 font-medium">
            <i class="fa-solid fa-building-columns text-[10px] mr-1 text-blue-400"></i> ${escapeHtml(p.diario || 'Banco')}
          </td>
          <td class="p-3 text-xs text-slate-300 italic truncate max-w-[200px]" title="${escapeHtml(p.memo || '')}">${escapeHtml(p.memo || 'Sin concepto')}</td>
          <td class="p-3 text-right font-mono font-black text-emerald-400 bg-emerald-500/5 text-xs">${fmtMxn(p.monto || 0)}</td>
          <td class="p-3 text-center">
            <span class="px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 font-bold text-[10px]">
              ✓ Aplicado
            </span>
          </td>
        `;
        tbodyPagos.appendChild(tr);
      });
    }
  }
}

// Alias y funciones globales
window.renderCobranzaCobradoMes = renderCobradoMesView;
window.renderCobradoMesView = renderCobradoMesView;
window.sortCobMesClientes = sortCobMesClientes;
window.abrirModalHistorialCliente = abrirModalHistorialCliente;
window.abrirHistorialComprasCliente = abrirModalHistorialCliente;
window.abrirHistorialCliente = abrirModalHistorialCliente;
window.cerrarModalHistorialCliente = cerrarModalHistorialCliente;

async function exportarCobradoMesExcel() {
  const selMesKey = document.getElementById('cob-mes-select-periodo')?.value || 'TODOS';
  const selVend = document.getElementById('cob-mes-select-vendedor')?.value || 'TODOS';
  const searchTxt = (document.getElementById('search-cobrado-mes')?.value || '').toLowerCase().trim();

  showLoading('Exportando Excel...', 'Generando reporte detallado de cobrado y recuperación por mes...');
  try {
    const res = await fetch('/api/export_excel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tipo: 'cobrado_mes',
        cobrado_mes_data: cobranzaCobradoMesGlobal,
        periodo_filtro: selMesKey,
        vendedor_filtro: selVend,
        search_filtro: searchTxt
      })
    });

    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Reporte_Cobrado_Mes_${selMesKey}_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      hideLoading('¡Excel Descargado!', 'El reporte mensual de cobros ha sido descargado exitosamente.');
    } else {
      const err = await res.json();
      hideLoading('⚠️ Error', err.error || 'Error al descargar Excel.');
    }
  } catch (e) {
    console.error('Error export excel cobrado mes:', e);
    hideLoading('⚠️ Error', 'Ocurrió un error al generar el archivo Excel.');
  }
}

async function exportarCobradoMesPdf() {
  const selMesKey = document.getElementById('cob-mes-select-periodo')?.value || 'TODOS';
  const selVend = document.getElementById('cob-mes-select-vendedor')?.value || 'TODOS';
  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';

  showLoading('Exportando PDF...', 'Generando estado ejecutivo de cobros mensual en PDF...');
  try {
    const res = await fetch('/api/export_pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tipo: 'cobrado_mes',
        cobrado_mes_data: cobranzaCobradoMesGlobal,
        periodo_filtro: selMesKey,
        vendedor_filtro: selVend,
        empresa_nombre: empresa
      })
    });

    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Reporte_Cobrado_Mes_${selMesKey}_${new Date().toISOString().slice(0,10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      hideLoading('¡PDF Descargado!', 'El reporte PDF mensual de cobros ha sido descargado exitosamente.');
    } else {
      const err = await res.json();
      hideLoading('⚠️ Error', err.error || 'Error al descargar PDF.');
    }
  } catch (e) {
    console.error('Error export pdf cobrado mes:', e);
    hideLoading('⚠️ Error', 'Ocurrió un error al generar el archivo PDF.');
  }
}

// ── VISTA 3: VENDIDO EN UN MES VS RECUPERACIÓN AL SIGUIENTE MES ─────────────
function seleccionarMesRecuperacion(mesKey) {
  const selMes = document.getElementById('cob-recup-mes');
  if (selMes) {
    selMes.value = mesKey;
    renderCobranzaRecuperacion();
  }
}

function renderCobranzaRecuperacion() {
  const selMes = document.getElementById('cob-recup-mes')?.value || 'TODOS';
  const selVend = document.getElementById('cob-recup-vendedor')?.value || 'TODOS';
  const meses = cobranzaCiclosGlobal.meses || [];

  if (meses.length === 0) return;

  let totVendido = 0;
  let totSubtotalVendido = 0;
  let totARecuperar = 0;
  let totRecuperado = 0;
  let totPendiente = 0;
  let facsCount = 0;

  let lblCicloText = 'Ciclo: Todos los Meses Consolidado';
  let lblVendMesText = 'Todos los Meses';

  if (selMes === 'TODOS') {
    meses.forEach(m => {
      if (selVend === 'TODOS') {
        totVendido += m.total_vendido;
        totSubtotalVendido += (m.subtotal_vendido || 0);
        totARecuperar += m.a_recuperar_mes_sig;
        totRecuperado += m.ya_recuperado;
        totPendiente += m.saldo_pendiente;
        facsCount += m.facturas_count;
      } else {
        const vObj = m.vendedores.find(v => v.vendedor === selVend);
        if (vObj) {
          totVendido += vObj.total_vendido;
          totSubtotalVendido += (vObj.subtotal_vendido || 0);
          totARecuperar += vObj.a_recuperar_mes_sig;
          totRecuperado += vObj.ya_recuperado;
          totPendiente += vObj.saldo_pendiente;
          facsCount += vObj.facturas_count;
        }
      }
    });
  } else {
    const m = meses.find(x => x.mes_key === selMes);
    if (m) {
      lblCicloText = `📅 Vendido en: ${m.mes_venta} ➔ Exigible a Recuperar en: ${m.mes_siguiente} (${m.facturas_count} facturas)`;
      lblVendMesText = m.mes_venta;
      if (selVend === 'TODOS') {
        totVendido = m.total_vendido;
        totSubtotalVendido = (m.subtotal_vendido || 0);
        totARecuperar = m.a_recuperar_mes_sig;
        totRecuperado = m.ya_recuperado;
        totPendiente = m.saldo_pendiente;
        facsCount = m.facturas_count;
      } else {
        const vObj = m.vendedores.find(v => v.vendedor === selVend);
        if (vObj) {
          totVendido = vObj.total_vendido;
          totSubtotalVendido = (vObj.subtotal_vendido || 0);
          totARecuperar = vObj.a_recuperar_mes_sig;
          totRecuperado = vObj.ya_recuperado;
          totPendiente = vObj.saldo_pendiente;
          facsCount = vObj.facturas_count;
        }
      }
    }
  }

  const tasaRecup = totVendido > 0 ? (totRecuperado / totVendido * 100) : 0.0;

  // Actualizar KPIs
  const elVendido = document.getElementById('kpi-recup-vendido');
  const elARecup = document.getElementById('kpi-recup-arecuperar');
  const elRecup = document.getElementById('kpi-recup-recuperado');
  const elPend = document.getElementById('kpi-recup-pendiente');
  const elTasa = document.getElementById('kpi-recup-tasa');
  const elLblCiclo = document.getElementById('lbl-recup-ciclo-activo');
  const elLblVendMes = document.getElementById('lbl-recup-vend-mes-nom');

  if (elVendido) {
    elVendido.innerHTML = `
      <div>${fmtMxn(totVendido)}</div>
      <div class="text-[10px] text-slate-400 font-semibold mt-0.5">Subtotal sin IVA: ${fmtMxn(totSubtotalVendido)} (${facsCount} facturas)</div>
    `;
  }
  if (elARecup) elARecup.innerText = fmtMxn(totARecuperar);
  if (elRecup) elRecup.innerText = fmtMxn(totRecuperado);
  if (elPend) elPend.innerText = fmtMxn(totPendiente);
  if (elTasa) elTasa.innerText = `${tasaRecup.toFixed(1)}%`;
  if (elLblCiclo) elLblCiclo.innerText = lblCicloText;
  if (elLblVendMes) elLblVendMes.innerText = lblVendMesText;

  renderCobranzaRecuperacionMesesTable();
  renderCobranzaRecuperacionVendedoresTable();
  renderCobranzaRecuperacionFacturas();
}

function renderCobranzaRecuperacionMesesTable() {
  const tbody = document.getElementById('tbody-cob-recup-meses');
  if (!tbody) return;

  const meses = cobranzaCiclosGlobal.meses || [];
  const selMes = document.getElementById('cob-recup-mes')?.value || 'TODOS';
  tbody.innerHTML = '';

  meses.forEach(m => {
    const tr = document.createElement('tr');
    const isSelected = (m.mes_key === selMes);
    tr.className = `transition-colors hover:bg-slate-800/60 ${isSelected ? 'bg-indigo-950/40 font-bold' : ''}`;

    const tasa = m.tasa_recuperacion || 0;
    let barColor = 'bg-emerald-500';
    let textColor = 'text-emerald-400';
    if (tasa < 50) { barColor = 'bg-rose-500'; textColor = 'text-rose-400'; }
    else if (tasa < 80) { barColor = 'bg-amber-500'; textColor = 'text-amber-400'; }

    tr.innerHTML = `
      <td class="p-3 text-center font-bold text-white">${m.mes_venta}</td>
      <td class="p-3 text-center text-indigo-300 font-extrabold bg-indigo-950/20">
        <i class="fa-solid fa-arrow-right-long mr-1 text-indigo-400 text-xs"></i> ${m.mes_siguiente}
      </td>
      <td class="p-3 text-right font-mono text-slate-200">${fmtMxn(m.total_vendido)}</td>
      <td class="p-3 text-right font-mono font-bold text-indigo-300 bg-indigo-950/20">${fmtMxn(m.a_recuperar_mes_sig)}</td>
      <td class="p-3 text-right font-mono font-bold text-emerald-400">${fmtMxn(m.ya_recuperado)}</td>
      <td class="p-3 text-right font-mono font-bold text-rose-400">${fmtMxn(m.saldo_pendiente)}</td>
      <td class="p-3 text-center">
        <div class="flex items-center justify-center space-x-2">
          <div class="w-16 bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700">
            <div class="${barColor} h-2 rounded-full transition-all duration-300" style="width: ${Math.min(100, tasa)}%"></div>
          </div>
          <span class="text-[11px] font-mono font-bold ${textColor}">${tasa.toFixed(1)}%</span>
        </div>
      </td>
      <td class="p-3 text-center text-slate-400 text-xs font-mono">${m.facturas_count} facs</td>
      <td class="p-3 text-center">
        <button onclick="seleccionarMesRecuperacion('${m.mes_key}')" class="px-2.5 py-1 rounded-lg text-[10px] font-bold ${isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-800 hover:bg-slate-700 text-slate-300'} transition-all">
          <i class="fa-solid fa-eye mr-1"></i> Ver Ciclo
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderCobranzaRecuperacionVendedoresTable() {
  const tbody = document.getElementById('tbody-cob-recup-vendedores');
  if (!tbody) return;

  const meses = cobranzaCiclosGlobal.meses || [];
  const selMes = document.getElementById('cob-recup-mes')?.value || 'TODOS';
  const selVend = document.getElementById('cob-recup-vendedor')?.value || 'TODOS';

  tbody.innerHTML = '';

  let vendedoresMap = {};

  if (selMes === 'TODOS') {
    meses.forEach(m => {
      m.vendedores.forEach(v => {
        if (selVend !== 'TODOS' && v.vendedor !== selVend) return;
        if (!vendedoresMap[v.vendedor]) {
          vendedoresMap[v.vendedor] = {
            vendedor: v.vendedor,
            total_vendido: 0,
            a_recuperar_mes_sig: 0,
            ya_recuperado: 0,
            saldo_pendiente: 0,
            facturas_count: 0
          };
        }
        const vm = vendedoresMap[v.vendedor];
        vm.total_vendido += v.total_vendido;
        vm.a_recuperar_mes_sig += v.a_recuperar_mes_sig;
        vm.ya_recuperado += v.ya_recuperado;
        vm.saldo_pendiente += v.saldo_pendiente;
        vm.facturas_count += v.facturas_count;
      });
    });
  } else {
    const m = meses.find(x => x.mes_key === selMes);
    if (m) {
      m.vendedores.forEach(v => {
        if (selVend !== 'TODOS' && v.vendedor !== selVend) return;
        vendedoresMap[v.vendedor] = { ...v };
      });
    }
  }

  const vList = Object.values(vendedoresMap);
  vList.sort((a, b) => b.total_vendido - a.total_vendido);

  if (vList.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="p-6 text-center text-slate-500">No hay datos de vendedores para este filtro.</td></tr>';
    return;
  }

  vList.forEach(v => {
    const tr = document.createElement('tr');
    tr.className = 'transition-colors hover:bg-slate-800/60';
    const tasa = v.total_vendido > 0 ? (v.ya_recuperado / v.total_vendido * 100) : 0;
    let barColor = 'bg-emerald-500';
    let textColor = 'text-emerald-400';
    if (tasa < 50) { barColor = 'bg-rose-500'; textColor = 'text-rose-400'; }
    else if (tasa < 80) { barColor = 'bg-amber-500'; textColor = 'text-amber-400'; }

    tr.innerHTML = `
      <td class="p-3 font-bold text-white flex items-center">
        <div class="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mr-2 text-[10px] text-emerald-400 font-bold">
          ${v.vendedor.charAt(0)}
        </div>
        ${v.vendedor}
      </td>
      <td class="p-3 text-right font-mono text-slate-200 font-semibold">${fmtMxn(v.total_vendido)}</td>
      <td class="p-3 text-right font-mono font-bold text-indigo-300 bg-indigo-950/20">${fmtMxn(v.a_recuperar_mes_sig)}</td>
      <td class="p-3 text-right font-mono font-bold text-emerald-400">${fmtMxn(v.ya_recuperado)}</td>
      <td class="p-3 text-right font-mono font-bold text-rose-400">${fmtMxn(v.saldo_pendiente)}</td>
      <td class="p-3 text-center">
        <div class="flex items-center justify-center space-x-2">
          <div class="w-16 bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700">
            <div class="${barColor} h-2 rounded-full" style="width: ${Math.min(100, tasa)}%"></div>
          </div>
          <span class="text-[11px] font-mono font-bold ${textColor}">${tasa.toFixed(1)}%</span>
        </div>
      </td>
      <td class="p-3 text-center text-slate-400 text-xs font-mono">${v.facturas_count} facs</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderCobranzaRecuperacionFacturas() {
  const tbody = document.getElementById('tbody-cob-recup-facturas');
  if (!tbody) return;

  const meses = cobranzaCiclosGlobal.meses || [];
  const selMes = document.getElementById('cob-recup-mes')?.value || 'TODOS';
  const selVend = document.getElementById('cob-recup-vendedor')?.value || 'TODOS';
  const search = normalizarTexto(document.getElementById('search-cob-recup-facturas')?.value || '');

  tbody.innerHTML = '';

  let allFacs = [];
  if (selMes === 'TODOS') {
    meses.forEach(m => {
      allFacs.push(...m.facturas);
    });
  } else {
    const m = meses.find(x => x.mes_key === selMes);
    if (m) allFacs.push(...m.facturas);
  }

  const filtered = allFacs.filter(f => {
    if (selVend !== 'TODOS' && f.vendedor !== selVend) return false;
    if (search) {
      const cliNorm = normalizarTexto(f.cliente);
      const folNorm = normalizarTexto(f.folio);
      const vendNorm = normalizarTexto(f.vendedor);
      if (!cliNorm.includes(search) && !folNorm.includes(search) && !vendNorm.includes(search)) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="11" class="p-8 text-center text-slate-500">No se encontraron facturas con los filtros seleccionados.</td></tr>';
    return;
  }

  // Mostrar hasta 250 facturas ordenadas por saldo pendiente desc
  filtered.sort((a, b) => b.saldo_pendiente - a.saldo_pendiente || b.total_factura - a.total_factura);
  const displayFacs = filtered.slice(0, 250);

  displayFacs.forEach((f, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'transition-colors hover:bg-slate-800/60';

    let statusBadge = '<span class="px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">✓ PAGADA</span>';
    if (f.saldo_pendiente > 0.01) {
      if (f.monto_abonado > 0) {
        statusBadge = '<span class="px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 text-[10px] font-bold">🟡 PARCIAL</span>';
      } else {
        statusBadge = '<span class="px-2 py-0.5 rounded-md bg-rose-500/20 text-rose-300 text-[10px] font-bold">🚨 PENDIENTE</span>';
      }
    }

    let phoneBtn = '';
    if (f.telefono) {
      const cleanPhone = f.telefono.replace(/[^0-9]/g, '');
      phoneBtn = `
        <a href="https://wa.me/${cleanPhone}" target="_blank" class="w-6 h-6 rounded-lg bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600 hover:text-white flex items-center justify-center text-[10px]" title="WhatsApp">
          <i class="fa-brands fa-whatsapp"></i>
        </a>
      `;
    }

    let cobrarBtn = '';
    if (f.saldo_pendiente > 0.01) {
      cobrarBtn = `
        <button onclick="abrirModalCobroCliente('${f.cliente_id || f.cliente}')" class="px-2 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-bold shadow transition-all">
          Cobrar
        </button>
      `;
    } else {
      cobrarBtn = `<span class="text-[10px] text-slate-500 italic">Liquidada</span>`;
    }

    tr.innerHTML = `
      <td class="p-3 text-center font-mono text-slate-500 text-xs">${idx + 1}</td>
      <td class="p-3 font-bold text-white truncate max-w-[200px]" title="${f.cliente}">${f.cliente}</td>
      <td class="p-3 text-center text-slate-300 text-xs">${f.vendedor}</td>
      <td class="p-3 text-center font-mono font-bold text-indigo-300">${f.folio}</td>
      <td class="p-3 text-center font-mono text-xs text-slate-400">${formatFechaMX(f.fecha_factura)}</td>
      <td class="p-3 text-center font-mono text-xs font-bold text-indigo-300 bg-indigo-950/20">${formatFechaMX(f.fecha_vencimiento)}</td>
      <td class="p-3 text-right font-mono text-slate-300 font-semibold">${fmtMxn(f.total_factura)}</td>
      <td class="p-3 text-right font-mono font-bold text-emerald-400">${fmtMxn(f.monto_abonado)}</td>
      <td class="p-3 text-right font-mono font-bold text-rose-400">${fmtMxn(f.saldo_pendiente)}</td>
      <td class="p-3 text-center">${statusBadge}</td>
      <td class="p-3 text-center flex items-center justify-center space-x-1.5 pt-3.5">
        ${phoneBtn}
        ${cobrarBtn}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ── VISTA 1: TARJETAS DE GESTIÓN DE COBRANZA ("COBRAR") ─────────────────────
function renderCobranzaClientesCards() {
  const container = document.getElementById('grid-cobranza-clientes');
  if (!container) return;

  const search = normalizarTexto(document.getElementById('search-cobranza-clientes')?.value || '');

  const filtered = cobranzaClientesGlobal.filter(c => {
    // Filtro por antigüedad
    if (currentCobAgingFilter !== 'ALL') {
      if (currentCobAgingFilter === 'RECIENTE_0_60') {
        const hasReciente = c.facturas.some(f => (f.dias_retraso || 0) > 0 && (f.dias_retraso || 0) <= 60);
        if (!hasReciente && c.rango_predominante !== 'RECIENTE_0_60') return false;
      } else if (currentCobAgingFilter === 'PASADA_60_100') {
        const hasPasada = c.facturas.some(f => (f.dias_retraso || 0) > 60 && (f.dias_retraso || 0) <= 100);
        if (!hasPasada && c.rango_predominante !== 'PASADA_60_100') return false;
      } else if (currentCobAgingFilter === 'ATRASADA_100_MAS') {
        const hasAtrasada = c.facturas.some(f => (f.dias_retraso || 0) > 100);
        if (!hasAtrasada && c.rango_predominante !== 'ATRASADA_100_MAS') return false;
      }
    }

    // Búsqueda
    if (search) {
      const nom = normalizarTexto(c.cliente);
      const rfc = normalizarTexto(c.rfc || '');
      const tel = normalizarTexto(c.telefono || '');
      const mail = normalizarTexto(c.email || '');
      const vend = normalizarTexto(c.vendedor || '');
      const facs = normalizarTexto(c.facturas.map(f => f.folio).join(' '));
      if (!nom.includes(search) && !rfc.includes(search) && !tel.includes(search) && !mail.includes(search) && !vend.includes(search) && !facs.includes(search)) {
        return false;
      }
    }
    return true;
  });

  const lblSummary = document.getElementById('lbl-cob-clientes-resumen');
  if (lblSummary) {
    lblSummary.innerText = `Mostrando ${filtered.length} de ${cobranzaClientesGlobal.length} deudores`;
  }

  container.innerHTML = '';

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="col-span-full p-12 text-center bg-slate-900 border border-slate-800 rounded-3xl">
        <i class="fa-solid fa-folder-open text-3xl mb-3 text-slate-600 block"></i>
        <h4 class="text-sm font-bold text-slate-300">No se encontraron clientes deudores</h4>
        <p class="text-xs text-slate-500 mt-1">Intenta con otro filtro de antigüedad o limpia el término de búsqueda.</p>
      </div>
    `;
    return;
  }

  filtered.forEach((c, idx) => {
    const card = document.createElement('div');
    card.className = 'bg-slate-900 border border-slate-800 hover:border-emerald-500/50 rounded-2xl p-5 shadow-xl transition-all duration-150 flex flex-col justify-between group relative overflow-hidden';

    // Badge de retraso y borde de color
    let borderClr = 'bg-emerald-500';
    let badgeHtml = '<span class="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 text-[10px] font-extrabold">🟢 0-60 DÍAS (RECIENTE)</span>';
    let textSaldoClr = 'text-emerald-400';

    if (c.max_dias_retraso > 100) {
      borderClr = 'bg-rose-500';
      badgeHtml = `<span class="px-2 py-0.5 rounded-md bg-rose-500/20 text-rose-400 text-[10px] font-extrabold animate-pulse">🚨 +100 DÍAS (${c.max_dias_retraso}d ATRASADA)</span>`;
      textSaldoClr = 'text-rose-400';
    } else if (c.max_dias_retraso > 60) {
      borderClr = 'bg-amber-500';
      badgeHtml = `<span class="px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-400 text-[10px] font-extrabold">🟡 60-100 DÍAS (${c.max_dias_retraso}d PASADA)</span>`;
      textSaldoClr = 'text-amber-400';
    } else if (c.max_dias_retraso > 0) {
      badgeHtml = `<span class="px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 text-[10px] font-extrabold">🟢 ${c.max_dias_retraso}d (RECIENTE)</span>`;
    }

    const foliosStr = c.facturas.slice(0, 3).map(f => f.folio).join(', ') + (c.facturas.length > 3 ? ` (+${c.facturas.length - 3})` : '');
    const telDisplay = c.telefono || 'Sin teléfono';
    const emailDisplay = c.email || 'Sin correo';

    // Generar link WhatsApp rápido
    let waQuickBtn = '';
    if (c.telefono) {
      const cleanPhone = c.telefono.replace(/[^0-9]/g, '');
      const waText = encodeURIComponent(`Hola ${c.cliente}, le saludamos de Challenger Automotive para compartirle su estado de cuenta.`);
      waQuickBtn = `
        <a href="https://wa.me/${cleanPhone}?text=${waText}" target="_blank" onclick="event.stopPropagation()" class="w-8 h-8 rounded-xl bg-emerald-600/20 hover:bg-emerald-600 text-emerald-400 hover:text-white flex items-center justify-center transition-colors" title="Abrir WhatsApp">
          <i class="fa-brands fa-whatsapp text-sm"></i>
        </a>
      `;
    } else {
      waQuickBtn = `
        <span class="w-8 h-8 rounded-xl bg-slate-800 text-slate-600 flex items-center justify-center cursor-not-allowed" title="Sin WhatsApp registrado">
          <i class="fa-brands fa-whatsapp text-sm"></i>
        </span>
      `;
    }

    let phoneQuickBtn = '';
    if (c.telefono) {
      phoneQuickBtn = `
        <a href="tel:${c.telefono}" onclick="event.stopPropagation()" class="w-8 h-8 rounded-xl bg-blue-600/20 hover:bg-blue-600 text-blue-400 hover:text-white flex items-center justify-center transition-colors" title="Llamar al cliente">
          <i class="fa-solid fa-phone text-xs"></i>
        </a>
      `;
    } else {
      phoneQuickBtn = `
        <span class="w-8 h-8 rounded-xl bg-slate-800 text-slate-600 flex items-center justify-center cursor-not-allowed" title="Sin teléfono">
          <i class="fa-solid fa-phone text-xs"></i>
        </span>
      `;
    }

    let mailQuickBtn = '';
    if (c.email) {
      mailQuickBtn = `
        <a href="mailto:${c.email}?subject=Estado%20de%20Cuenta%20-%20Challenger%20Automotive" onclick="event.stopPropagation()" class="w-8 h-8 rounded-xl bg-purple-600/20 hover:bg-purple-600 text-purple-400 hover:text-white flex items-center justify-center transition-colors" title="Enviar correo">
          <i class="fa-solid fa-envelope text-xs"></i>
        </a>
      `;
    } else {
      mailQuickBtn = `
        <span class="w-8 h-8 rounded-xl bg-slate-800 text-slate-600 flex items-center justify-center cursor-not-allowed" title="Sin correo">
          <i class="fa-solid fa-envelope text-xs"></i>
        </span>
      `;
    }

    card.innerHTML = `
      <div class="w-1.5 ${borderClr} absolute left-0 top-0 bottom-0"></div>

      <!-- HEADER DE LA TARJETA -->
      <div class="space-y-2">
        <div class="flex items-start justify-between gap-2">
          <div class="flex-1 min-w-0">
            <h4 class="text-sm font-bold text-white group-hover:text-emerald-400 transition-colors truncate" title="${c.cliente}">
              ${c.cliente}
            </h4>
            <div class="flex flex-wrap items-center gap-1.5 mt-1">
              <span class="text-[10px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700 font-semibold">${c.rfc || 'SIN RFC'}</span>
              <span class="text-[10px] text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded"><i class="fa-solid fa-user-tie text-[9px] mr-1 text-emerald-400"></i>${c.vendedor}</span>
            </div>
          </div>
          <div class="shrink-0">
            ${badgeHtml}
          </div>
        </div>

        <!-- CONTACTO CON BOTONES DE ACCIÓN RÁPIDA -->
        <div class="bg-slate-950/70 p-3 rounded-xl border border-slate-800/80 space-y-2">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center space-x-1.5 min-w-0 truncate text-xs text-slate-300">
              <i class="fa-solid fa-phone text-blue-400 text-xs shrink-0"></i>
              <span class="truncate">${telDisplay}</span>
            </div>
            <div class="flex items-center space-x-1 shrink-0">
              ${phoneQuickBtn}
              ${waQuickBtn}
              ${mailQuickBtn}
            </div>
          </div>
          <div class="flex items-center space-x-1.5 text-xs text-slate-400 truncate">
            <i class="fa-solid fa-envelope text-purple-400 text-xs shrink-0"></i>
            <span class="truncate">${emailDisplay}</span>
          </div>
          <p class="text-[11px] text-slate-400 pt-1.5 border-t border-slate-800/60 truncate">
            <i class="fa-solid fa-file-invoice text-emerald-400 mr-1"></i> ${c.num_facturas} facturas: <span class="font-mono text-slate-300 font-bold">${foliosStr}</span>
          </p>
        </div>
      </div>

      <!-- SALDO Y ACCIONES PRINCIPALES (GRID 2 BOTONES NUNCA CORTADOS) -->
      <div class="mt-3 pt-3 border-t border-slate-800 space-y-2.5">
        <div class="flex items-center justify-between">
          <div>
            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Saldo Pendiente</span>
            <span class="text-xl font-black ${textSaldoClr}">${fmtMxn(c.saldo_total)}</span>
          </div>
          <div class="text-right">
            <span class="text-[10px] text-slate-400 block">${c.num_facturas} facturas</span>
            <span class="text-xs font-bold text-amber-400 font-mono">${c.max_dias_retraso}d retraso</span>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-2 pt-0.5">
          <button onclick="abrirModalHistorialCliente('${c.cliente_id || ''}', '${escapeJs(c.cliente)}')" class="py-2.5 px-2 rounded-xl bg-cyan-600/20 hover:bg-cyan-600 text-cyan-300 hover:text-white border border-cyan-500/30 text-xs font-bold transition-all shadow-md flex items-center justify-center space-x-1.5" title="Ver historial completo de facturas y compras de este cliente">
            <i class="fa-solid fa-receipt text-cyan-300"></i>
            <span>Ver Compras</span>
          </button>
          <button onclick="abrirModalCobroCliente('${c.cliente_id || c.cliente}')" class="py-2.5 px-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/25 flex items-center justify-center space-x-1.5 transition-all">
            <i class="fa-solid fa-hand-holding-dollar"></i>
            <span>Cobrar</span>
          </button>
        </div>
      </div>
    `;

    container.appendChild(card);
  });
}

// ── VISTA 2: TABLA DE FACTURAS DETALLADAS ───────────────────────────────────
function renderCobranzaTable() {
  const tbody = document.getElementById('tbody-cobranza');
  if (!tbody) return;

  const searchInput = document.getElementById('search-cobranza')?.value || '';
  const search = normalizarTexto(searchInput);

  tbody.innerHTML = '';

  const filtered = cobranzaDataGlobal.filter(item => {
    // Filtro de antigüedad
    if (currentCobAgingFilter !== 'ALL') {
      if (currentCobAgingFilter === 'RECIENTE_0_60' && ((item.dias_retraso || 0) <= 0 || (item.dias_retraso || 0) > 60)) return false;
      if (currentCobAgingFilter === 'PASADA_60_100' && ((item.dias_retraso || 0) <= 60 || (item.dias_retraso || 0) > 100)) return false;
      if (currentCobAgingFilter === 'ATRASADA_100_MAS' && (item.dias_retraso || 0) <= 100) return false;
    }

    if (search) {
      const cliNorm = normalizarTexto(item.cliente);
      const folNorm = normalizarTexto(item.folio);
      const vendNorm = normalizarTexto(item.vendedor);
      const telNorm = normalizarTexto(item.telefono || '');
      if (!cliNorm.includes(search) && !folNorm.includes(search) && !vendNorm.includes(search) && !telNorm.includes(search)) return false;
    }
    return true;
  });

  const lblCount = document.getElementById('lbl-cob-count');
  if (lblCount) {
    lblCount.innerText = `Mostrando ${filtered.length} de ${cobranzaDataGlobal.length} facturas`;
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="12" class="p-8 text-center text-slate-500 font-medium">
          <i class="fa-solid fa-folder-open text-2xl mb-2 block text-slate-600"></i>
          No hay facturas por cobrar que coincidan con la búsqueda o filtros.
        </td>
      </tr>
    `;
    return;
  }

  filtered.forEach((item, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-900 transition-colors group';

    let badgeStatus = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
    let lblStatus = '🟢 0-60d (Reciente)';
    if (item.dias_retraso > 100) {
      badgeStatus = 'bg-rose-500/20 text-rose-400 border-rose-500/30 animate-pulse';
      lblStatus = `🚨 +100d (${item.dias_retraso}d)`;
    } else if (item.dias_retraso > 60) {
      badgeStatus = 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      lblStatus = `🟡 60-100d (${item.dias_retraso}d)`;
    } else if (item.dias_retraso <= 0) {
      badgeStatus = 'bg-slate-800 text-slate-400 border-slate-700';
      lblStatus = '✓ Al día';
    }

    const telContact = item.telefono ? `<i class="fa-solid fa-phone text-blue-400 mr-1"></i>${item.telefono}` : '<span class="text-slate-600">—</span>';

    tr.innerHTML = `
      <td class="p-3 text-center text-slate-500 font-bold">${idx + 1}</td>
      <td class="p-3 font-semibold text-white group-hover:text-emerald-400">
        <span class="truncate block max-w-xs" title="${item.cliente}">${item.cliente}</span>
      </td>
      <td class="p-3 text-center text-xs text-slate-400">${telContact}</td>
      <td class="p-3 text-center text-slate-300 font-medium">${item.vendedor}</td>
      <td class="p-3 text-center font-mono text-blue-400 font-bold">${item.folio}</td>
      <td class="p-3 text-center text-slate-400">${item.fecha_factura}</td>
      <td class="p-3 text-center text-slate-400">${item.fecha_vencimiento}</td>
      <td class="p-3 text-center"><span class="px-2.5 py-1 rounded-full border text-[10px] font-bold ${badgeStatus}">${lblStatus}</span></td>
      <td class="p-3 text-right font-medium text-slate-300">${fmtMxn(item.total_factura)}</td>
      <td class="p-3 text-right text-emerald-400 font-semibold">${fmtMxn(item.monto_abonado)}</td>
      <td class="p-3 text-right font-black text-red-400">${fmtMxn(item.saldo_pendiente)}</td>
      <td class="p-3 text-center">
        <div class="flex items-center justify-center space-x-1">
          <button onclick="abrirModalHistorialCliente('${item.cliente_id || ''}', '${escapeJs(item.cliente)}')" class="px-2 py-1 rounded-lg bg-cyan-600/20 hover:bg-cyan-600 text-cyan-300 hover:text-white text-[11px] font-bold transition-all shadow" title="Ver historial completo de facturas y compras de este cliente">
            <i class="fa-solid fa-receipt"></i>
          </button>
          <button onclick="abrirModalCobroCliente('${item.cliente_id || item.cliente}')" class="px-2.5 py-1 rounded-lg bg-emerald-600/20 hover:bg-emerald-600 text-emerald-400 hover:text-white text-xs font-bold transition-all shadow">
            Cobrar
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ── MODAL 1: DIÁLOGO DE COBRANZA AL CLIENTE ("COBRAR") ──────────────────────
function abrirModalCobroCliente(clientKeyOrId) {
  const client = cobranzaClientesGlobal.find(c => String(c.cliente_id) === String(clientKeyOrId) || String(c.cliente) === String(clientKeyOrId));
  if (!client) return;

  currentClienteCobroSeleccionado = client;

  document.getElementById('mcob-cliente-nom').innerText = client.cliente;
  document.getElementById('mcob-rfc-badge').innerText = `RFC: ${client.rfc || 'No registrado'}`;
  document.getElementById('mcob-vendedor-badge').innerText = `👤 Vendedor: ${client.vendedor}`;
  document.getElementById('mcob-direccion').innerHTML = `<i class="fa-solid fa-location-dot text-emerald-400 mr-1.5"></i> ${client.direccion || client.ciudad || 'Dirección fiscal no especificada en Odoo'}`;

  document.getElementById('mcob-saldo-total').innerText = fmtMxn(client.saldo_total);
  document.getElementById('mcob-max-dias').innerText = `${client.max_dias_retraso} Días`;
  document.getElementById('mcob-facs-summary').innerText = `${client.num_facturas} factura(s) impagadas`;
  document.getElementById('mcob-facs-count-badge').innerText = `${client.num_facturas} facturas pendientes`;

  const badgeRango = document.getElementById('mcob-rango-badge');
  if (client.max_dias_retraso > 100) {
    badgeRango.className = 'inline-block mt-1 px-2.5 py-0.5 rounded-md text-[10px] font-extrabold uppercase bg-rose-500/20 text-rose-400 animate-pulse';
    badgeRango.innerText = '🚨 Cobranza Atrasada (> 100 Días)';
  } else if (client.max_dias_retraso > 60) {
    badgeRango.className = 'inline-block mt-1 px-2.5 py-0.5 rounded-md text-[10px] font-extrabold uppercase bg-amber-500/20 text-amber-400';
    badgeRango.innerText = '🟡 Cobranza Pasada (60 a 100 Días)';
  } else {
    badgeRango.className = 'inline-block mt-1 px-2.5 py-0.5 rounded-md text-[10px] font-extrabold uppercase bg-emerald-500/20 text-emerald-400';
    badgeRango.innerText = '🟢 Cobranza Reciente (0 a 60 Días)';
  }

  // Configurar botones de llamada, whatsapp y correo
  const btnCall = document.getElementById('mcob-btn-call');
  const btnWa = document.getElementById('mcob-btn-wa-direct');
  const btnMail = document.getElementById('mcob-btn-mail-direct');
  const infoLine = document.getElementById('mcob-contacto-info-line');

  if (client.telefono) {
    btnCall.href = `tel:${client.telefono}`;
    btnCall.classList.remove('opacity-50', 'pointer-events-none');
    const cleanPh = client.telefono.replace(/[^0-9]/g, '');
    btnWa.href = `https://wa.me/${cleanPh}`;
    btnWa.classList.remove('opacity-50', 'pointer-events-none');
  } else {
    btnCall.href = '#';
    btnCall.classList.add('opacity-50', 'pointer-events-none');
    btnWa.href = '#';
    btnWa.classList.add('opacity-50', 'pointer-events-none');
  }

  if (client.email) {
    btnMail.href = `mailto:${client.email}?subject=Estado%20de%20Cuenta%20-%20Challenger%20Automotive`;
    btnMail.classList.remove('opacity-50', 'pointer-events-none');
  } else {
    btnMail.href = '#';
    btnMail.classList.add('opacity-50', 'pointer-events-none');
  }

  infoLine.innerText = `Teléfono: ${client.telefono || 'Sin teléfono'} | Email: ${client.email || 'Sin correo'}`;

  // Llenar tabla de facturas
  const tbodyFacs = document.getElementById('mcob-tbody-facturas');
  tbodyFacs.innerHTML = '';

  const foliosList = client.facturas.map(f => f.folio).join(', ');

  client.facturas.forEach((f, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-900 transition-colors';

    let badgeF = 'text-emerald-400';
    if (f.dias_retraso > 100) badgeF = 'text-rose-400 font-black';
    else if (f.dias_retraso > 60) badgeF = 'text-amber-400 font-bold';

    tr.innerHTML = `
      <td class="p-2.5 text-center text-slate-500 font-bold">${idx + 1}</td>
      <td class="p-2.5 text-center font-mono font-bold text-blue-400">${f.folio}</td>
      <td class="p-2.5 text-center text-slate-400">${f.fecha_factura}</td>
      <td class="p-2.5 text-center text-slate-400">${f.fecha_vencimiento}</td>
      <td class="p-2.5 text-center ${badgeF}">${f.dias_retraso}d</td>
      <td class="p-2.5 text-right font-medium text-slate-300">${fmtMxn(f.total_factura)}</td>
      <td class="p-2.5 text-right text-emerald-400 font-medium">${fmtMxn(f.monto_abonado)}</td>
      <td class="p-2.5 text-right font-black text-red-400">${fmtMxn(f.saldo_pendiente)}</td>
      <td class="p-2.5 text-center">
        <button onclick="cerrarModalCobroCliente(); abrirModalCobranzaFacturaId('${f.inv_id}')" class="text-slate-400 hover:text-emerald-400 text-xs" title="Ver desglose de productos">
          <i class="fa-solid fa-magnifying-glass"></i>
        </button>
      </td>
    `;
    tbodyFacs.appendChild(tr);
  });

  // Generar mensaje predeterminado
  const msgDefault = `Estimado(a) ${client.cliente}, le saludamos de Challenger Automotive.

Le recordamos amablemente que al día de hoy presenta un saldo pendiente de ${fmtMxn(client.saldo_total)} MXN correspondiente a su(s) factura(s) (${foliosList}) con una antigüedad de ${client.max_dias_retraso} días.

Agradecemos mucho su valioso apoyo compartiéndonos su comprobante de pago o la fecha estimada de liquidación. ¡Quedamos a su entera disposición!`;

  const txtArea = document.getElementById('mcob-msg-text');
  if (txtArea) txtArea.value = msgDefault;

  const copyFb = document.getElementById('mcob-copy-feedback');
  if (copyFb) copyFb.classList.add('hidden');

  document.getElementById('modal-cobro-cliente').classList.remove('hidden');
}

function cerrarModalCobroCliente() {
  document.getElementById('modal-cobro-cliente').classList.add('hidden');
}

function copiarMensajeCobro() {
  const txtArea = document.getElementById('mcob-msg-text');
  if (!txtArea) return;
  navigator.clipboard.writeText(txtArea.value).then(() => {
    const copyFb = document.getElementById('mcob-copy-feedback');
    if (copyFb) {
      copyFb.classList.remove('hidden');
      setTimeout(() => copyFb.classList.add('hidden'), 3000);
    }
  });
}

function enviarWhatsAppModal() {
  if (!currentClienteCobroSeleccionado) return;
  let phone = currentClienteCobroSeleccionado.telefono;
  if (!phone) {
    phone = prompt('El cliente no tiene teléfono guardado en Odoo. Por favor ingrese el número (ej. 524421234567):');
    if (!phone) return;
  }
  const cleanPhone = phone.replace(/[^0-9]/g, '');
  const msg = document.getElementById('mcob-msg-text')?.value || '';
  const url = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(msg)}`;
  window.open(url, '_blank');
}

async function enviarCorreoIndividualOdoo() {
  if (!currentClienteCobroSeleccionado) return;
  const client = currentClienteCobroSeleccionado;
  let mail = client.email;
  if (!mail || !mail.includes('@')) {
    mail = prompt('El cliente no tiene correo registrado en Odoo. Ingrese el correo destinatario:', '');
    if (!mail || !mail.includes('@')) {
      alert('Por favor ingrese un correo válido para continuar.');
      return;
    }
  }

  const asunto = `Recordatorio de Estado de Cuenta y Facturas Pendientes - Challenger Automotive`;
  const cuerpo = document.getElementById('mcob-msg-text')?.value || '';
  const empresa = document.getElementById('global-empresa')?.value || 'Challenger Automotive';

  const btnSend = document.getElementById('btn-send-mail-single');
  const fbBanner = document.getElementById('mcob-mail-feedback');

  if (btnSend) {
    btnSend.disabled = true;
    btnSend.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Enviando vía Odoo...';
  }

  if (fbBanner) {
    fbBanner.className = 'p-3 rounded-xl text-xs font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30 flex items-center';
    fbBanner.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Despachando correo oficial a ${mail} vía Odoo ERP...`;
    fbBanner.classList.remove('hidden');
  }

  try {
    const res = await fetch('/api/cobranza/enviar_correo_individual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cliente_id: client.cliente_id,
        cliente: client.cliente,
        email: mail,
        asunto: asunto,
        cuerpo: cuerpo,
        empresa_nombre: empresa,
        facturas: client.facturas || []
      })
    });
    const resData = await res.json();

    if (resData.success) {
      if (fbBanner) {
        fbBanner.className = 'p-3 rounded-xl text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center';
        fbBanner.innerHTML = `<i class="fa-solid fa-circle-check mr-2 text-emerald-400"></i> ${resData.mensaje || '¡Correo de cobranza enviado exitosamente vía Odoo ERP!'}`;
      }
    } else {
      if (fbBanner) {
        fbBanner.className = 'p-3 rounded-xl text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center';
        fbBanner.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-2 text-rose-400"></i> Error enviando correo: ${resData.error}`;
      }
    }
  } catch (err) {
    if (fbBanner) {
      fbBanner.className = 'p-3 rounded-xl text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center';
      fbBanner.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-2 text-rose-400"></i> Error de conexión: ${err}`;
    }
  } finally {
    if (btnSend) {
      btnSend.disabled = false;
      btnSend.innerHTML = '<i class="fa-solid fa-paper-plane mr-1.5 text-purple-200"></i> 🚀 Enviar Correo Oficial (Odoo)';
    }
  }
}

function abrirGmailIndividual() {
  if (!currentClienteCobroSeleccionado) return;
  let mail = currentClienteCobroSeleccionado.email || '';
  const subject = `Recordatorio de Estado de Cuenta y Facturas Pendientes - Challenger Automotive`;
  const body = document.getElementById('mcob-msg-text')?.value || '';
  const url = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(mail)}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  window.open(url, '_blank');
}

function enviarCorreoIndividualModal() {
  enviarCorreoIndividualOdoo();
}

function abrirModalCobranzaFacturaId(invId) {
  const idx = cobranzaDataGlobal.findIndex(i => String(i.inv_id) === String(invId));
  if (idx >= 0) abrirModalCobranza(idx);
}

function abrirModalCobranza(idx) {
  const c = cobranzaDataGlobal[idx];
  if (!c) return;

  document.getElementById('lbl-modal-cob-cliente').innerText = c.cliente;
  document.getElementById('modal-cob-folio').innerText = `Factura: ${c.folio} | ID Odoo: ${c.inv_id}`;
  document.getElementById('modal-cob-vendedor').innerText = c.vendedor;
  document.getElementById('modal-cob-fechas').innerText = `${c.fecha_factura} → Vence: ${c.fecha_vencimiento}`;

  const elPill = document.getElementById('modal-cob-estatus-pill');
  const dias = c.dias_retraso || 0;
  if (dias > 100) {
    elPill.className = 'text-xs font-bold text-rose-400 animate-pulse';
    elPill.innerText = `🚨 Atrasada Crítica (${dias} días de retraso)`;
  } else if (dias > 60) {
    elPill.className = 'text-xs font-bold text-amber-400';
    elPill.innerText = `🟡 Pasada (${dias} días de retraso)`;
  } else if (dias > 0) {
    elPill.className = 'text-xs font-bold text-emerald-400';
    elPill.innerText = `🟢 Reciente (${dias} días de retraso)`;
  } else {
    elPill.className = 'text-xs font-bold text-slate-300';
    elPill.innerText = `✓ Al día (Sin vencer)`;
  }

  document.getElementById('modal-cob-saldo-total').innerText = fmtMxn(c.saldo_pendiente);

  const tbody = document.getElementById('modal-cob-tbody-productos');
  tbody.innerHTML = '';

  const lineas = c.lineas_producto || [];
  if (lineas.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="p-6 text-center text-slate-500 font-medium">
          (Factura global o sin renglones de producto desglosados en Odoo)
        </td>
      </tr>
    `;
  } else {
    lineas.forEach((l, i) => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-900 transition-colors';
      tr.innerHTML = `
        <td class="p-2.5 text-center text-slate-500 font-bold">${i + 1}</td>
        <td class="p-2.5 font-semibold text-white">${l.producto}</td>
        <td class="p-2.5 text-right font-medium text-slate-300">${fmtNum(l.cantidad)}</td>
        <td class="p-2.5 text-right text-slate-400">${fmtMxn(l.precio_unit)}</td>
        <td class="p-2.5 text-right font-bold text-emerald-400">${fmtMxn(l.subtotal)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  document.getElementById('modal-cobranza-detalle').classList.remove('hidden');
}

function cerrarModalCobranza() {
  document.getElementById('modal-cobranza-detalle').classList.add('hidden');
}


// ── MODAL 2: CORREOS MASIVOS DE COBRANZA ────────────────────────────────────
function abrirModalCorreosMasivos() {
  const selRango = document.getElementById('mmail-filtro-rango');
  if (selRango) {
    selRango.value = currentCobAgingFilter === 'ALL' ? 'ALL' : currentCobAgingFilter;
  }
  actualizarTablaDestinatariosMasivos();
  document.getElementById('mmail-progress-container').classList.add('hidden');
  document.getElementById('modal-correos-masivos-cobranza').classList.remove('hidden');
}

function cerrarModalCorreosMasivos() {
  document.getElementById('modal-correos-masivos-cobranza').classList.add('hidden');
}

function actualizarTablaDestinatariosMasivos() {
  const tbody = document.getElementById('mmail-tbody-destinatarios');
  if (!tbody) return;

  const rango = document.getElementById('mmail-filtro-rango')?.value || 'ALL';
  tbody.innerHTML = '';

  const destinatariosValidos = cobranzaClientesGlobal.filter(c => {
    if (!c.email || !c.email.includes('@')) return false;
    if (rango !== 'ALL') {
      if (rango === 'ATRASADA_100_MAS' && c.max_dias_retraso <= 100) return false;
      if (rango === 'PASADA_60_100' && (c.max_dias_retraso <= 60 || c.max_dias_retraso > 100)) return false;
      if (rango === 'RECIENTE_0_60' && (c.max_dias_retraso <= 0 || c.max_dias_retraso > 60)) return false;
    }
    return true;
  });

  if (destinatariosValidos.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="p-6 text-center text-slate-500 font-medium">
          No hay clientes con correo electrónico en este rango seleccionado.
        </td>
      </tr>
    `;
    document.getElementById('mmail-count-selected').innerText = `0 destinatarios seleccionados`;
    return;
  }

  destinatariosValidos.forEach((c, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-900 transition-colors';

    let rClr = 'text-emerald-400';
    if (c.max_dias_retraso > 100) rClr = 'text-rose-400 font-bold';
    else if (c.max_dias_retraso > 60) rClr = 'text-amber-400 font-bold';

    tr.innerHTML = `
      <td class="p-2 text-center text-slate-500 font-bold">${idx + 1}</td>
      <td class="p-2 text-center">
        <input type="checkbox" class="mmail-item-chk rounded bg-slate-800 border-slate-700 text-purple-600 focus:ring-0 cursor-pointer" checked onchange="actualizarContadorSeleccionadosMassMail()" data-cliente-id="${c.cliente_id || ''}" data-cliente="${c.cliente}" data-email="${c.email}" data-saldo="${c.saldo_total}" data-dias="${c.max_dias_retraso}" data-folios="${c.facturas.map(f=>f.folio).join(', ')}">
      </td>
      <td class="p-2 font-semibold text-white truncate max-w-xs">${c.cliente}</td>
      <td class="p-2 text-purple-300 font-mono text-[11px] truncate max-w-[180px]">${c.email}</td>
      <td class="p-2 text-center text-slate-400 text-[11px]">${c.vendedor}</td>
      <td class="p-2 text-center ${rClr}">${c.max_dias_retraso}d</td>
      <td class="p-2 text-right font-black text-slate-200">${fmtMxn(c.saldo_total)}</td>
    `;
    tbody.appendChild(tr);
  });

  actualizarContadorSeleccionadosMassMail();
}

function toggleSelectAllMassMail(checked) {
  document.querySelectorAll('.mmail-item-chk').forEach(chk => {
    chk.checked = checked;
  });
  actualizarContadorSeleccionadosMassMail();
}

function actualizarContadorSeleccionadosMassMail() {
  const chks = document.querySelectorAll('.mmail-item-chk');
  const checked = document.querySelectorAll('.mmail-item-chk:checked');
  const lbl = document.getElementById('mmail-count-selected');
  if (lbl) {
    lbl.innerText = `${checked.length} de ${chks.length} destinatarios seleccionados`;
  }
}

function copiarListaBccDestinatarios() {
  const checked = document.querySelectorAll('.mmail-item-chk:checked');
  const emails = Array.from(checked).map(c => c.dataset.email).filter(Boolean);
  if (emails.length === 0) {
    alert('No hay correos seleccionados.');
    return;
  }
  navigator.clipboard.writeText(emails.join(', ')).then(() => {
    alert(`¡Se copiaron ${emails.length} direcciones de correo al portapapeles en formato BCC!`);
  });
}

function abrirGmailMasivoBcc() {
  const checked = document.querySelectorAll('.mmail-item-chk:checked');
  const emails = Array.from(checked).map(c => c.dataset.email).filter(Boolean);
  if (emails.length === 0) {
    alert('No hay correos seleccionados.');
    return;
  }
  const asunto = document.getElementById('mmail-asunto')?.value || 'Recordatorio de Estado de Cuenta y Facturas Pendientes - Challenger Automotive';
  const cuerpo = document.getElementById('mmail-cuerpo')?.value || '';
  const url = `https://mail.google.com/mail/?view=cm&fs=1&bcc=${encodeURIComponent(emails.join(','))}&su=${encodeURIComponent(asunto)}&body=${encodeURIComponent(cuerpo)}`;
  window.open(url, '_blank');
}

async function ejecutarEnvioCorreosMasivos() {
  const checked = document.querySelectorAll('.mmail-item-chk:checked');
  if (checked.length === 0) {
    alert('Por favor selecciona al menos un cliente destinatario con correo.');
    return;
  }

  const destinatarios = Array.from(checked).map(c => {
    const cNom = c.dataset.cliente;
    const clientObj = (cobranzaClientesGlobal || []).find(cl => cl.cliente === cNom) || {};
    return {
      cliente_id: c.dataset.clienteId || null,
      cliente: cNom,
      email: c.dataset.email,
      saldo_total: parseFloat(c.dataset.saldo || 0),
      max_dias_retraso: parseInt(c.dataset.dias || 0),
      facturas_folios: c.dataset.folios,
      facturas: clientObj.facturas || []
    };
  });

  const asunto = document.getElementById('mmail-asunto')?.value || 'Recordatorio de Pago y Estado de Cuenta';
  const plantilla = document.getElementById('mmail-cuerpo')?.value || '';
  const empresa = document.getElementById('global-empresa')?.value || 'Challenger Automotive';

  const progressCont = document.getElementById('mmail-progress-container');
  const progressStatus = document.getElementById('mmail-progress-status');
  const progressPct = document.getElementById('mmail-progress-pct');
  const progressBar = document.getElementById('mmail-progress-bar');
  const logContainer = document.getElementById('mmail-results-log');
  const btnSend = document.getElementById('btn-iniciar-envio-masivo');

  progressCont.classList.remove('hidden');
  btnSend.disabled = true;
  btnSend.classList.add('opacity-50');

  progressStatus.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2 text-purple-400"></i> Despachando campaña de ${destinatarios.length} correos oficiales vía Odoo ERP...`;
  progressBar.style.width = '35%';
  progressPct.innerText = '35%';

  try {
    const res = await fetch('/api/cobranza/enviar_correos_masivos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ destinatarios, asunto, plantilla, empresa_nombre: empresa })
    });
    const resData = await res.json();

    progressBar.style.width = '100%';
    progressPct.innerText = '100%';

    if (resData.success) {
      progressStatus.innerHTML = `<span class="text-emerald-400 font-bold"><i class="fa-solid fa-circle-check mr-1.5"></i> ¡Campaña completada! (${resData.total_enviados} correos registrados y enviados en Odoo ERP)</span>`;
      logContainer.innerHTML = `
        <div class="text-emerald-400 font-bold pb-1">${resData.mensaje}</div>
        ${resData.enviados.map(e => `<div>✓ Correo despachado para: <b>${e.cliente}</b> (${e.email}) · Saldo: $${e.saldo.toLocaleString()} MXN [Msg ID: ${e.message_id || 'Odoo'}]</div>`).join('')}
        ${resData.errores.length > 0 ? `<div class="text-rose-400 font-bold pt-1">Errores: ${resData.errores.map(err=>`${err.cliente}: ${err.error}`).join(', ')}</div>` : ''}
      `;
    } else {
      progressStatus.innerHTML = `<span class="text-rose-400 font-bold"><i class="fa-solid fa-triangle-exclamation mr-1.5"></i> Error: ${resData.error}</span>`;
    }
  } catch (err) {
    progressStatus.innerHTML = `<span class="text-rose-400 font-bold"><i class="fa-solid fa-triangle-exclamation mr-1.5"></i> Error en la conexión: ${err}</span>`;
  } finally {
    btnSend.disabled = false;
    btnSend.classList.remove('opacity-50');
  }
}


// ── MODAL 3: HISTORIAL COMPLETO DE COMPRAS, VENTAS Y FACTURAS DEL CLIENTE ───
let currentHistorialCliente = null;
let currentHistorialFiltro = 'TODAS';
let expandedInvoicesSet = new Set();

function escapeJs(str) {
  if (!str) return '';
  return String(str).replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

function promptBuscarHistorialCliente() {
  const clienteBusqueda = prompt('Ingresa el nombre o RFC del cliente para consultar su historial de compras:');
  if (!clienteBusqueda || !clienteBusqueda.trim()) return;
  abrirModalHistorialCliente(null, clienteBusqueda.trim());
}

async function abrirModalHistorialCliente(clienteId, clienteNombre) {
  const modal = document.getElementById('modal-historial-compras-cliente');
  const loading = document.getElementById('mhist-loading');
  const tableContainer = document.getElementById('mhist-table-container');
  
  if (!modal) return;
  modal.classList.remove('hidden');
  loading.classList.remove('hidden');
  tableContainer.classList.add('hidden');
  
  // Limpiar estados previos
  currentHistorialCliente = null;
  currentHistorialFiltro = 'TODAS';
  expandedInvoicesSet.clear();
  const searchInput = document.getElementById('mhist-search-input');
  if (searchInput) searchInput.value = '';
  
  document.getElementById('mhist-cliente-nom').innerText = clienteNombre || 'Cargando cliente...';
  document.getElementById('mhist-rfc-badge').innerText = 'RFC: ...';
  document.getElementById('mhist-vendedor-badge').innerText = '👤 Vendedor: ...';
  document.getElementById('mhist-direccion').innerHTML = `<i class="fa-solid fa-location-dot text-slate-500 mr-1"></i> Consultando...`;
  document.getElementById('mhist-telefono').innerHTML = `<i class="fa-solid fa-phone text-blue-400 mr-1"></i> ...`;
  document.getElementById('mhist-email').innerHTML = `<i class="fa-solid fa-envelope text-purple-400 mr-1"></i> ...`;
  
  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  
  try {
    const res = await fetch('/api/cobranza/historial_cliente', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cliente_id: clienteId,
        cliente_nombre: clienteNombre,
        empresa_nombre: empresa
      })
    });
    
    const data = await res.json();
    if (!data.success) {
      alert(`No se pudo cargar el historial: ${data.error || 'Error desconocido'}`);
      cerrarModalHistorialCliente();
      return;
    }
    
    currentHistorialCliente = data;
    
    // Asignar Header
    document.getElementById('mhist-cliente-nom').innerText = data.cliente_nombre;
    document.getElementById('mhist-rfc-badge').innerText = `RFC: ${data.rfc || 'SIN RFC'}`;
    document.getElementById('mhist-vendedor-badge').innerText = `👤 Vendedor: ${data.vendedor || 'Sin Asignar'}`;
    document.getElementById('mhist-direccion').innerHTML = `<i class="fa-solid fa-location-dot text-slate-500 mr-1"></i> ${data.direccion || data.ciudad || 'Dirección no registrada'}`;
    document.getElementById('mhist-telefono').innerHTML = `<i class="fa-solid fa-phone text-blue-400 mr-1"></i> ${data.telefono || 'Sin teléfono'}`;
    document.getElementById('mhist-email').innerHTML = `<i class="fa-solid fa-envelope text-purple-400 mr-1"></i> ${data.email || 'Sin correo'}`;
    
    // Asignar KPIs
    const kpis = data.kpis || {};
    document.getElementById('mhist-kpi-total-comprado').innerText = fmtMxn(kpis.total_comprado || 0);
    document.getElementById('mhist-kpi-ticket-promedio').innerText = `Ticket Promedio: ${fmtMxn(kpis.ticket_promedio || 0)}`;
    
    document.getElementById('mhist-kpi-total-pagado').innerText = fmtMxn(kpis.total_pagado || 0);
    document.getElementById('mhist-kpi-pct-liquidado').innerText = `✓ ${kpis.pct_cumplimiento || 0}% liquidado`;
    
    document.getElementById('mhist-kpi-saldo-pendiente').innerText = fmtMxn(kpis.total_saldo_pendiente || 0);
    document.getElementById('mhist-kpi-saldo-alerta').innerText = `${kpis.facturas_pendientes || 0} factura(s) con saldo`;
    
    document.getElementById('mhist-kpi-total-facturas').innerText = `${kpis.total_facturas || 0}`;
    document.getElementById('mhist-kpi-desglose-facs').innerText = `${kpis.facturas_pagadas || 0} pagadas | ${kpis.facturas_pendientes || 0} pendientes | ${kpis.facturas_canceladas || 0} canceladas`;
    
    // Conteo en botones de filtro
    const facs = data.facturas || [];
    document.getElementById('mhist-count-todas').innerText = facs.length;
    document.getElementById('mhist-count-pendientes').innerText = facs.filter(f => f.estatus_pago === 'PENDIENTE' || f.estatus_pago === 'PARCIAL').length;
    document.getElementById('mhist-count-pagadas').innerText = facs.filter(f => f.estatus_pago === 'PAGADA').length;
    document.getElementById('mhist-count-notas').innerText = facs.filter(f => f.move_type === 'out_refund').length;
    
    loading.classList.add('hidden');
    tableContainer.classList.remove('hidden');
    
    renderHistorialFacturasTabla();
  } catch (err) {
    console.error("Error al obtener historial cliente:", err);
    alert(`Error de conexión al obtener historial: ${err}`);
    cerrarModalHistorialCliente();
  }
}

function cerrarModalHistorialCliente() {
  document.getElementById('modal-historial-compras-cliente').classList.add('hidden');
}

function setHistorialFiltroEstado(filtro) {
  currentHistorialFiltro = filtro;
  
  // Actualizar estilos de los botones
  const btnTodas = document.getElementById('mhist-btn-filtro-todas');
  const btnPend = document.getElementById('mhist-btn-filtro-pendientes');
  const btnPag = document.getElementById('mhist-btn-filtro-pagadas');
  const btnNotas = document.getElementById('mhist-btn-filtro-notas');
  
  const inactivoCls = 'px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-xs font-bold transition-all';
  if (btnTodas) btnTodas.className = filtro === 'TODAS' ? 'px-3 py-1.5 rounded-xl bg-slate-800 text-white text-xs font-bold transition-all shadow' : `${inactivoCls} text-slate-300`;
  if (btnPend) btnPend.className = filtro === 'PENDIENTES' ? 'px-3 py-1.5 rounded-xl bg-rose-600/30 text-rose-300 border border-rose-500/40 text-xs font-bold transition-all shadow' : `${inactivoCls} text-rose-400`;
  if (btnPag) btnPag.className = filtro === 'PAGADAS' ? 'px-3 py-1.5 rounded-xl bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 text-xs font-bold transition-all shadow' : `${inactivoCls} text-emerald-400`;
  if (btnNotas) btnNotas.className = filtro === 'NOTAS' ? 'px-3 py-1.5 rounded-xl bg-purple-600/30 text-purple-300 border border-purple-500/40 text-xs font-bold transition-all shadow' : `${inactivoCls} text-purple-400`;
  
  renderHistorialFacturasTabla();
}

function renderHistorialFacturasTabla() {
  if (!currentHistorialCliente) return;
  const tbody = document.getElementById('mhist-tbody-facturas');
  if (!tbody) return;
  
  const search = normalizarTexto(document.getElementById('mhist-search-input')?.value || '');
  const facturas = currentHistorialCliente.facturas || [];
  
  const filtered = facturas.filter(f => {
    // Filtro estado
    if (currentHistorialFiltro === 'PENDIENTES') {
      if (f.estatus_pago !== 'PENDIENTE' && f.estatus_pago !== 'PARCIAL') return false;
    } else if (currentHistorialFiltro === 'PAGADAS') {
      if (f.estatus_pago !== 'PAGADA') return false;
    } else if (currentHistorialFiltro === 'NOTAS') {
      if (f.move_type !== 'out_refund') return false;
    }
    
    // Filtro búsqueda
    if (search) {
      const folNorm = normalizarTexto(f.folio);
      const fechaNorm = normalizarTexto(f.fecha_emision);
      const estNorm = normalizarTexto(f.estatus_pago);
      const prodMatch = (f.productos || []).some(p => normalizarTexto(p.producto).includes(search) || normalizarTexto(p.sku || '').includes(search));
      if (!folNorm.includes(search) && !fechaNorm.includes(search) && !estNorm.includes(search) && !prodMatch) {
        return false;
      }
    }
    return true;
  });
  
  const countEl = document.getElementById('mhist-footer-count');
  if (countEl) countEl.innerText = `${filtered.length} de ${facturas.length} facturas`;
  tbody.innerHTML = '';
  
  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="12" class="p-10 text-center text-slate-500 font-medium">
          <i class="fa-solid fa-folder-open text-2xl mb-2 block text-slate-600"></i>
          No hay facturas que coincidan con el filtro seleccionado.
        </td>
      </tr>
    `;
    return;
  }
  
  filtered.forEach((f, idx) => {
    const isExpanded = expandedInvoicesSet.has(String(f.id));
    const tr = document.createElement('tr');
    tr.className = `hover:bg-slate-900/80 transition-colors border-b border-slate-800/60 ${isExpanded ? 'bg-slate-900/50' : ''}`;
    
    // Badge de estatus
    let badgeStatus = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
    let lblStatus = '🟢 PAGADA';
    if (f.estatus_pago === 'CANCELADA') {
      badgeStatus = 'bg-slate-800 text-slate-500 border-slate-700';
      lblStatus = '⚫ CANCELADA';
    } else if (f.estatus_pago === 'PARCIAL') {
      badgeStatus = 'bg-amber-500/20 text-amber-300 border-amber-500/30 animate-pulse';
      lblStatus = `🟡 PARCIAL (${fmtMxn(f.monto_pagado)})`;
    } else if (f.estatus_pago === 'PENDIENTE') {
      if (f.dias_retraso > 0) {
        badgeStatus = 'bg-rose-500/20 text-rose-400 border-rose-500/30 animate-pulse';
        lblStatus = `🚨 ${f.dias_retraso}d VENCIDA`;
      } else {
        badgeStatus = 'bg-blue-500/20 text-blue-300 border-blue-500/30';
        lblStatus = `🔵 PENDIENTE (Al día)`;
      }
    }
    
    // Badge de tipo
    const isRefund = f.move_type === 'out_refund';
    const tipoBadge = isRefund ?
      '<span class="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[10px] font-bold">Nota Crédito</span>' :
      '<span class="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 text-[10px] font-medium">Factura</span>';
      
    const prodsCount = (f.productos || []).length;
    const pagosCount = (f.pagos || []).length;
    
    tr.innerHTML = `
      <td class="p-2.5 text-center text-slate-500 font-bold">
        <button onclick="toggleDetalleRenglonesFactura('${f.id}')" class="w-6 h-6 rounded-md bg-slate-800 hover:bg-cyan-600 hover:text-white text-slate-400 text-xs flex items-center justify-center transition-colors shadow">
          <i class="fa-solid ${isExpanded ? 'fa-minus text-cyan-300' : 'fa-plus'}"></i>
        </button>
      </td>
      <td class="p-2.5 font-mono font-bold text-cyan-400">
        <span class="hover:underline cursor-pointer" onclick="toggleDetalleRenglonesFactura('${f.id}')">${f.folio}</span>
      </td>
      <td class="p-2.5 text-center">${tipoBadge}</td>
      <td class="p-2.5 text-center text-slate-400 text-[11px]">${f.fecha_emision}</td>
      <td class="p-2.5 text-center text-slate-400 text-[11px]">${f.fecha_vencimiento}</td>
      <td class="p-2.5 text-center text-slate-300 font-medium text-[11px]">
        ${f.dias_retraso > 0 ? `<span class="text-rose-400 font-bold">${f.dias_retraso}d retraso</span>` : `<span class="text-slate-400">${f.dias_credito}d crédito</span>`}
      </td>
      <td class="p-2.5 text-center">
        <span class="px-2 py-0.5 rounded-full border text-[10px] font-bold ${badgeStatus}">${lblStatus}</span>
      </td>
      <td class="p-2.5 text-right font-bold ${isRefund ? 'text-purple-400' : 'text-white'}">${fmtMxn(f.total)}</td>
      <td class="p-2.5 text-right font-medium text-emerald-400">${fmtMxn(f.monto_pagado)}</td>
      <td class="p-2.5 text-right font-black ${f.saldo_pendiente > 0.01 ? 'text-red-400' : 'text-slate-400'}">${fmtMxn(f.saldo_pendiente)}</td>
      <td class="p-2.5 text-center">
        <div class="w-full bg-slate-800 rounded-full h-2 min-w-[55px] overflow-hidden border border-slate-700/60 inline-block align-middle">
          <div class="bg-gradient-to-r from-emerald-500 to-cyan-500 h-full rounded-full" style="width: ${Math.min(100, Math.max(0, f.pct_cubierto))}%;"></div>
        </div>
        <span class="text-[10px] font-mono text-slate-400 block mt-0.5">${f.pct_cubierto}%</span>
      </td>
      <td class="p-2.5 text-center">
        <button onclick="toggleDetalleRenglonesFactura('${f.id}')" class="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[11px] font-bold transition-all shadow" title="Ver ${prodsCount} productos y ${pagosCount} pagos">
          <i class="fa-solid fa-boxes-stacked mr-1 text-cyan-400"></i> ${prodsCount} prods
        </button>
      </td>
    `;
    tbody.appendChild(tr);
    
    // Sub-fila acordeón con el detalle de productos y pagos
    if (isExpanded) {
      const trDetail = document.createElement('tr');
      trDetail.className = 'bg-slate-950/90 border-b border-cyan-500/20 shadow-inner';
      
      const prodsList = f.productos || [];
      const pagosList = f.pagos || [];
      
      let prodsRowsHtml = '';
      if (prodsList.length === 0) {
        prodsRowsHtml = `
          <tr>
            <td colspan="8" class="p-4 text-center text-slate-500">Sin líneas de producto desglosadas en Odoo para esta factura.</td>
          </tr>
        `;
      } else {
        prodsRowsHtml = prodsList.map((p, pIdx) => `
          <tr class="hover:bg-slate-900/60 border-b border-slate-800/40 text-[11px]">
            <td class="p-2 text-center text-slate-500 font-bold">${pIdx + 1}</td>
            <td class="p-2 font-mono text-cyan-300 font-semibold">${p.sku || '—'}</td>
            <td class="p-2 font-medium text-white">${p.producto}</td>
            <td class="p-2 text-right font-bold text-slate-200">${fmtNum(p.cantidad)}</td>
            <td class="p-2 text-center text-slate-400">${p.uom || 'Pz'}</td>
            <td class="p-2 text-right text-slate-300">${fmtMxn(p.precio_unit)}</td>
            <td class="p-2 text-right text-slate-400">${fmtMxn(p.subtotal)}</td>
            <td class="p-2 text-right font-bold text-emerald-400">${fmtMxn(p.total)}</td>
          </tr>
        `).join('');
      }
      
      let pagosHtml = '';
      if (pagosList.length === 0) {
        pagosHtml = `<span class="text-xs text-slate-500 italic">No hay abonos ni pagos registrados en Odoo para este folio aún.</span>`;
      } else {
        pagosHtml = `
          <div class="flex flex-wrap items-center gap-2">
            ${pagosList.map(pg => `
              <div class="px-3 py-1.5 rounded-xl bg-emerald-950/60 border border-emerald-500/30 text-xs flex items-center space-x-2 shadow">
                <i class="fa-solid fa-money-bill-transfer text-emerald-400 text-sm"></i>
                <div>
                  <div class="font-bold text-emerald-300">${fmtMxn(pg.monto)} <span class="text-[10px] text-slate-400 font-normal">(${pg.fecha})</span></div>
                  <div class="text-[10px] text-slate-400 truncate max-w-xs">${pg.metodo} ${pg.referencia ? `· ${pg.referencia}` : ''}</div>
                </div>
              </div>
            `).join('')}
          </div>
        `;
      }
      
      trDetail.innerHTML = `
        <td colspan="12" class="p-4 pl-10">
          <div class="space-y-3 bg-slate-900/90 p-4 rounded-2xl border border-slate-800 shadow-lg">
            
            <!-- SECCIÓN 1: PRODUCTOS VENDIDOS EN LA FACTURA -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center">
                  <i class="fa-solid fa-boxes-packing mr-1.5 text-cyan-400"></i> ¿Qué se vendió en esta factura? (${prodsList.length} productos)
                </span>
                <span class="text-xs text-slate-400 font-mono">Folio: <b>${f.folio}</b></span>
              </div>
              <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950">
                <table class="w-full text-left text-xs text-slate-300">
                  <thead class="bg-slate-900/90 text-slate-400 font-bold uppercase text-[10px] border-b border-slate-800">
                    <tr>
                      <th class="p-2 text-center w-8">#</th>
                      <th class="p-2 w-24">Código/SKU</th>
                      <th class="p-2">Descripción del Producto</th>
                      <th class="p-2 text-right">Cant.</th>
                      <th class="p-2 text-center">Unidad</th>
                      <th class="p-2 text-right">Precio Unit. ($)</th>
                      <th class="p-2 text-right">Subtotal ($)</th>
                      <th class="p-2 text-right">Total c/IVA ($)</th>
                    </tr>
                  </thead>
                  <tbody>${prodsRowsHtml}</tbody>
                </table>
              </div>
            </div>

            <!-- SECCIÓN 2: HISTORIAL DE PAGOS Y ABONOS -->
            <div class="pt-2 border-t border-slate-800/80">
              <div class="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-1.5 flex items-center">
                <i class="fa-solid fa-receipt mr-1.5 text-emerald-400"></i> ¿Cuánto pagó el cliente? (Abonos registrados: ${pagosList.length})
              </div>
              ${pagosHtml}
            </div>

          </div>
        </td>
      `;
      tbody.appendChild(trDetail);
    }
  });
}

function toggleDetalleRenglonesFactura(invId) {
  const strId = String(invId);
  if (expandedInvoicesSet.has(strId)) {
    expandedInvoicesSet.delete(strId);
  } else {
    expandedInvoicesSet.add(strId);
  }
  renderHistorialFacturasTabla();
}

function toggleTodosDetallesFacturas() {
  if (!currentHistorialCliente) return;
  const facturas = currentHistorialCliente.facturas || [];
  const btn = document.getElementById('mhist-btn-toggle-all');
  
  if (expandedInvoicesSet.size === facturas.length) {
    expandedInvoicesSet.clear();
    if (btn) btn.innerHTML = `<i class="fa-solid fa-chevron-down mr-1"></i> Expandir Todo`;
  } else {
    facturas.forEach(f => expandedInvoicesSet.add(String(f.id)));
    if (btn) btn.innerHTML = `<i class="fa-solid fa-chevron-up mr-1"></i> Contraer Todo`;
  }
  renderHistorialFacturasTabla();
}

async function exportarHistorialClienteExcel() {
  if (!currentHistorialCliente) return;
  const clientData = currentHistorialCliente;
  
  try {
    const res = await fetch('/api/export_excel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tipo: 'historial_cliente',
        hist_data: clientData,
        items: clientData.facturas || []
      })
    });
    
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Historial_Compras_${clientData.cliente_nombre.replace(/[^a-zA-Z0-9]/g, '_')}_${new Date().toISOString().slice(0,10)}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (err) {
    console.error("Error al exportar Excel historial:", err);
    alert('Error al exportar Excel del cliente: ' + err);
  }
}

async function exportarHistorialClientePdf() {
  if (!currentHistorialCliente) return;
  const clientData = currentHistorialCliente;
  
  try {
    const res = await fetch('/api/export_pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tipo: 'historial_cliente',
        hist_data: clientData,
        items: clientData.facturas || [],
        empresa_nombre: document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)'
      })
    });
    
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Estado_Cuenta_${clientData.cliente_nombre.replace(/[^a-zA-Z0-9]/g, '_')}_${new Date().toISOString().slice(0,10)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (err) {
    console.error("Error al exportar PDF historial:", err);
    alert('Error al generar PDF del cliente: ' + err);
  }
}

function exportarHistorialClienteCsv() {
  if (!currentHistorialCliente) return;
  const facturas = currentHistorialCliente.facturas || [];
  if (facturas.length === 0) {
    alert('No hay facturas para exportar.');
    return;
  }
  
  let csvContent = 'data:text/csv;charset=utf-8,\uFEFF';
  csvContent += 'Folio,Tipo,Fecha Emision,Fecha Vencimiento,Dias Credito,Dias Retraso,Estatus Pago,Total Factura,Monto Pagado,Saldo Pendiente,Codigo Producto,Descripcion Producto,Cantidad,Unidad,Precio Unitario,Subtotal Producto,Total Producto con IVA\n';
  
  facturas.forEach(f => {
    const prods = f.productos || [];
    if (prods.length === 0) {
      csvContent += `"${f.folio}","${f.tipo}","${f.fecha_emision}","${f.fecha_vencimiento}",${f.dias_credito},${f.dias_retraso},"${f.estatus_pago}",${f.total},${f.monto_pagado},${f.saldo_pendiente},"","","","","","",""\n`;
    } else {
      prods.forEach(p => {
        csvContent += `"${f.folio}","${f.tipo}","${f.fecha_emision}","${f.fecha_vencimiento}",${f.dias_credito},${f.dias_retraso},"${f.estatus_pago}",${f.total},${f.monto_pagado},${f.saldo_pendiente},"${p.sku || ''}","${(p.producto || '').replace(/"/g, '""')}",${p.cantidad},"${p.uom || ''}",${p.precio_unit},${p.subtotal},${p.total}\n`;
      });
    }
  });
  
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement('a');
  link.setAttribute('href', encodedUri);
  link.setAttribute('download', `Historial_Compras_${currentHistorialCliente.cliente_nombre.replace(/[^a-zA-Z0-9]/g, '_')}_${new Date().toISOString().slice(0,10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}


// ── MÓDULO 6: VENTAS POR VENDEDOR & PRODUCTOS VENDIDOS ───────────────────────
let ventasVendedorDataGlobal = null;
let currentVvSubtab = 'resumen';
let openVendedorAccordions = {};

function switchVentasVendedorSubtab(subtab) {
  currentVvSubtab = subtab;
  const btnResumen = document.getElementById('btn-subtab-vv-resumen');
  const btnMatriz = document.getElementById('btn-subtab-vv-matriz');
  const viewResumen = document.getElementById('view-vv-resumen');
  const viewMatriz = document.getElementById('view-vv-matriz');

  if (subtab === 'resumen') {
    if (viewResumen) viewResumen.classList.remove('hidden');
    if (viewMatriz) viewMatriz.classList.add('hidden');
    if (btnResumen) btnResumen.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 text-white transition-all shadow-md shadow-emerald-600/20 flex items-center';
    if (btnMatriz) btnMatriz.className = 'px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white transition-all flex items-center';
    renderVentasVendedor();
  } else {
    if (viewResumen) viewResumen.classList.add('hidden');
    if (viewMatriz) viewMatriz.classList.remove('hidden');
    if (btnResumen) btnResumen.className = 'px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white transition-all flex items-center';
    if (btnMatriz) btnMatriz.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 text-white transition-all shadow-md shadow-blue-600/20 flex items-center';
    renderVentasVendedorMatriz();
  }
}

async function loadVentasVendedorData() {
  const container = document.getElementById('container-vv-vendedores');
  if (container && (!ventasVendedorDataGlobal || !ventasVendedorDataGlobal.resumen_vendedores || ventasVendedorDataGlobal.resumen_vendedores.length === 0)) {
    container.innerHTML = `
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-emerald-400 font-medium shadow-xl">
        <i class="fa-solid fa-spinner fa-spin text-2xl mb-3"></i>
        <p>Consultando ventas y productos por vendedor en Odoo 19...</p>
      </div>
    `;
  }

  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  const vendedor = document.getElementById('vv-vendedor')?.value || 'TODOS';
  const mes = document.getElementById('vv-mes')?.value || '8';
  const anio = document.getElementById('vv-anio')?.value || '2026';
  const excluirInter = document.getElementById('vv-interempresa')?.checked ?? false;

  showLoading('Consultando Ventas por Vendedor...', 'Agrupando facturación y desgloses de productos en Odoo ERP...');

  try {
    const res = await fetch('/api/ventas_vendedor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        empresa_nombre: empresa,
        vendedor: vendedor,
        mes: parseInt(mes),
        anio: parseInt(anio),
        excluir_interempresa: excluirInter
      })
    });
    const data = await res.json();
    if (data.success && data.data) {
      ventasVendedorDataGlobal = data.data;

      // Actualizar dropdown de vendedores si es la primera vez
      const selVend = document.getElementById('vv-vendedor');
      if (selVend && selVend.options.length <= 1 && ventasVendedorDataGlobal.vendedores_disponibles) {
        const currentVal = selVend.value;
        selVend.innerHTML = '<option value="TODOS">👥 TODOS LOS VENDEDORES</option>';
        ventasVendedorDataGlobal.vendedores_disponibles.forEach(v => {
          const opt = document.createElement('option');
          opt.value = v.valor;
          opt.innerText = `👤 ${v.nombre}`;
          selVend.appendChild(opt);
        });
        selVend.value = currentVal;
      }

      // KPIs
      const tot = ventasVendedorDataGlobal.totales_generales || {};
      const elTot = document.getElementById('kpi-vv-total');
      const elUnits = document.getElementById('kpi-vv-unidades');
      const elLider = document.getElementById('kpi-vv-lider');
      const elLiderSub = document.getElementById('kpi-vv-lider-sub');
      const elFacs = document.getElementById('kpi-vv-facturas');
      const elVendsCount = document.getElementById('kpi-vv-vends-count');
      const elPer = document.getElementById('kpi-vv-periodo-lbl');

      if (elTot) {
        const hasNc = (tot.total_nc_con_iva && tot.total_nc_con_iva > 0);
        elTot.innerHTML = `
          <div class="text-xl sm:text-2xl font-black text-emerald-400">${fmtMxn(tot.total_con_iva || tot.total_facturado || 0)}</div>
          <div class="text-[10px] sm:text-xs text-slate-400 font-semibold mt-0.5">Subtotal sin IVA: <span class="text-slate-300 font-bold">${fmtMxn(tot.subtotal_facturado || 0)}</span></div>
          ${hasNc ? `<div class="text-[10px] text-rose-400 font-bold mt-1 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded-md inline-block"><i class="fa-solid fa-arrow-rotate-left mr-1"></i> ${tot.num_nc || 0} NCs: -${fmtMxn(tot.total_nc_con_iva)} (Venta Neta: ${fmtMxn(tot.total_neto_con_iva)})</div>` : ''}
        `;
      }
      if (elUnits) elUnits.innerText = `${fmtNum(tot.total_unidades || 0)} uds`;
      if (elLider) elLider.innerText = tot.vendedor_lider || '—';
      if (elLiderSub) {
        const lidMonto = tot.vendedor_lider_monto || 0;
        const totalBase = (tot.total_con_iva || tot.total_facturado || 1);
        const pctLid = totalBase > 0 ? (lidMonto / totalBase * 100) : 0;
        elLiderSub.innerText = `${fmtMxn(lidMonto)} (${pctLid.toFixed(1)}% de la facturación)`;
      }
      if (elFacs) {
        const ncTxt = tot.num_nc ? ` (+ ${tot.num_nc} NCs)` : '';
        elFacs.innerText = `${tot.num_facturas || 0} facturas${ncTxt}`;
      }
      if (elVendsCount) elVendsCount.innerText = `${tot.num_vendedores || 0} asesores comerciales activos`;
      if (elPer) elPer.innerText = ventasVendedorDataGlobal.periodo_seleccionado || 'Período seleccionado';

      if (currentVvSubtab === 'resumen') renderVentasVendedor();
      else renderVentasVendedorMatriz();

      hideLoading('¡Ventas Listas!', `${ventasVendedorDataGlobal.resumen_vendedores?.length || 0} asesores procesados con éxito.`);
    } else {
      hideLoading('⚠️ Sin Ventas', 'No se encontraron registros de ventas.');
    }
  } catch (err) {
    console.error('Error Ventas por Vendedor:', err);
    hideLoading('⚠️ Error de Ventas', 'Error al consultar ventas por vendedor.');
    const container = document.getElementById('container-vv-vendedores');
    if (container) {
      container.innerHTML = `<div class="p-8 text-center text-rose-400">Error al cargar ventas: ${err}</div>`;
    }
  }
}

function renderVentasVendedor() {
  const container = document.getElementById('container-vv-vendedores');
  if (!container || !ventasVendedorDataGlobal) return;

  const search = (document.getElementById('search-vv')?.value || '').toLowerCase().trim();
  const catFiltro = document.getElementById('vv-cat')?.value || 'TODAS';

  const vends = ventasVendedorDataGlobal.resumen_vendedores || [];
  if (vends.length === 0) {
    container.innerHTML = `
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 font-medium">
        <i class="fa-solid fa-inbox text-3xl text-slate-600 mb-3"></i>
        <p>No se encontraron ventas para los filtros seleccionados.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = '';

  vends.forEach((v, vIdx) => {
    let prods = v.productos_vendidos || [];

    // Filtros por búsqueda y categoría
    if (catFiltro !== 'TODAS') {
      prods = prods.filter(p => p.categoria === catFiltro);
    }
    if (search) {
      const matchVend = v.vendedor.toLowerCase().includes(search);
      prods = prods.filter(p => matchVend || p.producto.toLowerCase().includes(search) || (p.categoria && p.categoria.toLowerCase().includes(search)));
      if (!matchVend && prods.length === 0) return;
    }

    const subTotalFiltrado = prods.reduce((sum, p) => sum + (p.subtotal || 0), 0);
    const cantFiltrada = prods.reduce((sum, p) => sum + (p.cantidad || 0), 0);

    const isOpen = openVendedorAccordions[v.vendedor] ?? (vIdx < 3);
    const isDirect = v.es_venta_directa;

    const badgeLider = (!isDirect && vIdx === 0 && (v.total_con_iva || v.total_subtotal) > 0)
      ? '<span class="ml-2 px-2 py-0.5 rounded-full text-[9px] font-extrabold bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-sm"><i class="fa-solid fa-crown text-amber-400 mr-1"></i> LÍDER DEL MES</span>'
      : (isDirect ? '<span class="ml-2 px-2 py-0.5 rounded-full text-[9px] font-extrabold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">🏢 VENTA DIRECTA / SIN ASIGNAR</span>' : '');

    const avatarNum = isDirect ? '🏢' : `#${v.posicion}`;
    const avatarGradient = isDirect
      ? 'from-indigo-600 to-slate-800 text-white'
      : (vIdx === 0 ? 'from-amber-500 to-yellow-600 text-black' : (vIdx === 1 ? 'from-slate-300 to-slate-500 text-black' : (vIdx === 2 ? 'from-amber-700 to-amber-900 text-white' : 'from-slate-700 to-slate-800 text-slate-300')));

    const hasNcVend = (v.num_nc && v.num_nc > 0);
    const ncInfoHtml = hasNcVend
      ? `<span class="text-rose-400 font-bold ml-1">· ${v.num_nc} NCs (-${fmtMxn(v.total_nc_con_iva)}) ➔ Venta Neta: <span class="text-emerald-300">${fmtMxn(v.total_neto_con_iva)}</span></span>`
      : '';

    const card = document.createElement('div');
    card.className = 'bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl transition-all';
    card.innerHTML = `
      <!-- HEADER ACORDEÓN VENDEDOR -->
      <div onclick="toggleVendedorAcordeon('${v.vendedor}')" class="p-4 bg-slate-900/90 hover:bg-slate-850 border-b border-slate-800 cursor-pointer flex flex-wrap items-center justify-between gap-4 transition-colors">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-xl bg-gradient-to-br ${avatarGradient} flex items-center justify-center font-black text-xs shadow-md">
            ${avatarNum}
          </div>
          <div>
            <h4 class="text-sm font-bold text-white flex items-center">
              ${v.vendedor}
              ${badgeLider}
            </h4>
            <p class="text-[11px] text-slate-400 mt-0.5">
              ${v.num_facturas} facturas emitidas · ${v.num_clientes} clientes atendidos · Ticket Promedio: <span class="text-slate-300 font-semibold">${fmtMxn(v.ticket_promedio)}</span>
              ${ncInfoHtml}
            </p>
          </div>
        </div>

        <div class="flex items-center space-x-6">
          <div class="text-right">
            <span class="text-[10px] uppercase font-bold text-slate-400 block">Total Facturado</span>
            <span class="text-base sm:text-lg font-black text-emerald-400">${fmtMxn(v.total_con_iva || v.total_facturado || v.total_subtotal)}</span>
            <span class="text-[10px] font-semibold text-slate-400 block mt-0.5">Subtotal: ${fmtMxn(v.total_subtotal)}</span>
          </div>

          <div class="text-right hidden sm:block">
            <span class="text-[10px] uppercase font-bold text-slate-500 block">Volumen</span>
            <span class="text-xs font-bold text-blue-400">${fmtNum(v.total_cantidad)} uds</span>
          </div>

          <div class="text-right hidden md:block">
            <span class="text-[10px] uppercase font-bold text-slate-500 block">Participación</span>
            <span class="text-xs font-black text-purple-400">${v.pct_participacion}%</span>
          </div>

          <div class="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400">
            <i class="fa-solid ${isOpen ? 'fa-chevron-up' : 'fa-chevron-down'} text-xs"></i>
          </div>
        </div>
      </div>

      <!-- DETALLE DE PRODUCTOS DEL VENDEDOR -->
      <div id="acc-body-${v.vendedor.replace(/[^a-zA-Z0-9]/g, '_')}" class="${isOpen ? '' : 'hidden'}">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-300">
            <thead class="bg-slate-950 text-slate-400 font-bold uppercase text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th class="p-3 text-center w-10">#</th>
                <th class="p-3">Producto / Código Comercial</th>
                <th class="p-3 text-center">Marca / Categoría</th>
                <th class="p-3 text-right">Cantidad (Uds)</th>
                <th class="p-3 text-right">Precio Promedio ($)</th>
                <th class="p-3 text-right">Total Facturado ($)</th>
                <th class="p-3 text-center">% del Vendedor</th>
                <th class="p-3 text-center">Facturas</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800/60">
              ${prods.length === 0 ? '<tr><td colspan="8" class="p-4 text-center text-slate-500">No hay productos que coincidan con los filtros.</td></tr>' : prods.map((p, pIdx) => {
                let badgeCat = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
                if (p.categoria === 'PASTA') badgeCat = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
                else if (p.categoria === 'MULTIMARCA') badgeCat = 'bg-purple-500/10 text-purple-400 border-purple-500/20';
                else if (p.categoria === 'MATERIA PRIMA') badgeCat = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';

                return `
                  <tr class="hover:bg-slate-800/40 transition-colors">
                    <td class="p-3 text-center text-slate-500 font-bold">${p.posicion || (pIdx + 1)}</td>
                    <td class="p-3 font-semibold text-white">
                      ${p.producto}
                    </td>
                    <td class="p-3 text-center">
                      <span class="px-2 py-0.5 rounded-full text-[9px] font-bold border ${badgeCat}">${p.categoria}</span>
                    </td>
                    <td class="p-3 text-right font-medium text-slate-300">${fmtNum(p.cantidad)}</td>
                    <td class="p-3 text-right text-slate-400">${fmtMxn(p.precio_promedio)}</td>
                    <td class="p-3 text-right font-bold text-emerald-400">${fmtMxn(p.subtotal)}</td>
                    <td class="p-3 text-center">
                      <div class="flex items-center justify-center space-x-1.5">
                        <div class="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                          <div class="bg-emerald-500 h-1.5 rounded-full" style="width: ${Math.min(100, p.pct_del_vendedor)}%"></div>
                        </div>
                        <span class="text-[10px] font-bold text-slate-400">${p.pct_del_vendedor}%</span>
                      </div>
                    </td>
                    <td class="p-3 text-center text-slate-400">${p.num_facturas}</td>
                  </tr>
                `;
              }).join('')}
            </tbody>
            <tfoot class="bg-slate-950 font-bold border-t border-slate-800 text-slate-300">
              <tr>
                <td colspan="3" class="p-3 text-right uppercase text-[10px] text-slate-400">Total Vendedor (${prods.length} productos):</td>
                <td class="p-3 text-right text-blue-400 font-black">${fmtNum(cantFiltrada)} uds</td>
                <td class="p-3 text-right">—</td>
                <td class="p-3 text-right text-emerald-400 font-black text-sm">${fmtMxn(subTotalFiltrado)}</td>
                <td class="p-3 text-center text-emerald-400">100.0%</td>
                <td class="p-3 text-center">—</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    `;

    container.appendChild(card);
  });
}

function toggleVendedorAcordeon(vendedorNombre) {
  openVendedorAccordions[vendedorNombre] = !(openVendedorAccordions[vendedorNombre] ?? false);
  renderVentasVendedor();
}

function expandirTodosVendedores(expand) {
  if (!ventasVendedorDataGlobal) return;
  (ventasVendedorDataGlobal.resumen_vendedores || []).forEach(v => {
    openVendedorAccordions[v.vendedor] = expand;
  });
  renderVentasVendedor();
}

function renderVentasVendedorMatriz() {
  const thead = document.getElementById('thead-vv-matriz');
  const tbody = document.getElementById('tbody-vv-matriz');
  const lblCount = document.getElementById('lbl-vv-matriz-count');
  if (!thead || !tbody || !ventasVendedorDataGlobal) return;

  const matriz = ventasVendedorDataGlobal.matriz_meses_vendedores || [];
  const periodos = ventasVendedorDataGlobal.periodos_historico || [];

  if (lblCount) lblCount.innerText = `${matriz.length} vendedores evaluados`;

  // Encabezados
  let thHtml = '<tr><th class="p-3 text-center w-10">#</th><th class="p-3">Vendedor Oficial</th>';
  periodos.forEach(per => {
    thHtml += `<th class="p-3 text-right">${per}</th>`;
  });
  thHtml += '<th class="p-3 text-right font-black text-emerald-400">Total Histórico ($)</th><th class="p-3 text-center">MoM (%)</th></tr>';
  thead.innerHTML = thHtml;

  tbody.innerHTML = '';
  if (matriz.length === 0) {
    tbody.innerHTML = `<tr><td colspan="${periodos.length + 4}" class="p-8 text-center text-slate-500">No hay datos históricos.</td></tr>`;
    return;
  }

  matriz.forEach(m => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/40 transition-colors';

    let trHtml = `
      <td class="p-3 text-center text-slate-500 font-bold">${m.posicion}</td>
      <td class="p-3 font-semibold text-white">${m.vendedor}</td>
    `;

    periodos.forEach(per => {
      const val = m.ventas_por_mes?.[per] || 0;
      trHtml += `<td class="p-3 text-right font-medium ${val > 0 ? 'text-slate-300' : 'text-slate-600'}">${val > 0 ? fmtMxn(val) : '—'}</td>`;
    });

    const mom = m.mom_growth || 0;
    const momBadge = mom > 0
      ? `<span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">+${mom.toFixed(1)}%</span>`
      : (mom < 0 ? `<span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">${mom.toFixed(1)}%</span>` : `<span class="text-slate-500">0.0%</span>`);

    trHtml += `
      <td class="p-3 text-right font-black text-emerald-400">${fmtMxn(m.total_historico)}</td>
      <td class="p-3 text-center">${momBadge}</td>
    `;

    tr.innerHTML = trHtml;
    tbody.appendChild(tr);
  });
}


// ── CRON SYNC Y STATUS ──────────────────────────────────────────────────────
async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    if (data.last_sync) {
      document.getElementById('lbl-last-sync').innerText = `Última sync: ${data.last_sync}`;
    }
  } catch (err) {}
}

async function triggerManualSync() {
  try {
    await fetch('/api/sync_now', { method: 'POST' });
    document.getElementById('lbl-last-sync').innerText = 'Sincronizando en segundo plano...';
    setTimeout(pollStatus, 3000);
  } catch (err) {}
}


function toggleModal3mAcordeon(vendNombre) {
  openModal3mAccordions[vendNombre] = !(openModal3mAccordions[vendNombre] ?? false);
  renderModal3mProductos();
}

// ── REPORTE 3 MESES (TRIMESTRAL) VENTAS POR VENDEDOR ─────────────────────────
let reporte3MesesDataGlobal = null;
let currentModal3mTab = 'resumen';
let openModal3mAccordions = {};

async function abrirReporte3MesesModal() {
  const modal = document.getElementById('modal-vv-3meses');
  if (modal) modal.classList.remove('hidden');

  const thead = document.getElementById('modal-3m-thead-resumen');
  const tbody = document.getElementById('modal-3m-tbody-resumen');
  const contProds = document.getElementById('modal-3m-container-prods');
  const lblPeriodo = document.getElementById('modal-3m-periodo-lbl');

  if (lblPeriodo) lblPeriodo.innerText = 'Consultando facturación de los últimos 3 meses en Odoo 19...';
  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="11" class="p-8 text-center text-purple-400 font-medium"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Consolidando reporte de 3 meses para todos los vendedores...</td></tr>';
  }
  if (contProds) {
    contProds.innerHTML = '<div class="p-8 text-center text-purple-400"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Cargando productos...</div>';
  }

  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  const mes = document.getElementById('vv-mes')?.value || '8';
  const anio = document.getElementById('vv-anio')?.value || '2026';
  const excluirInter = document.getElementById('vv-interempresa')?.checked ?? false;

  try {
    const res = await fetch('/api/ventas_vendedor_3meses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        empresa_nombre: empresa,
        mes: parseInt(mes),
        anio: parseInt(anio),
        excluir_interempresa: excluirInter
      })
    });
    const data = await res.json();
    if (data.success && data.data) {
      reporte3MesesDataGlobal = data.data;

      if (lblPeriodo) lblPeriodo.innerText = `Período: ${reporte3MesesDataGlobal.periodo_trimestre || 'Últimos 3 Meses'}`;

      // KPIs 3M
      const tot = reporte3MesesDataGlobal.totales_generales_3m || {};
      const elTot = document.getElementById('modal-3m-kpi-total');
      const elUnits = document.getElementById('modal-3m-kpi-unidades');
      const elLider = document.getElementById('modal-3m-kpi-lider');
      const elLiderSub = document.getElementById('modal-3m-kpi-lider-sub');
      const elFacs = document.getElementById('modal-3m-kpi-facs');
      const elVends = document.getElementById('modal-3m-kpi-vends');

      if (elTot) elTot.innerText = fmtMxn(tot.total_facturado || 0);
      if (elUnits) elUnits.innerText = `${fmtNum(tot.total_unidades || 0)} uds`;
      if (elLider) elLider.innerText = tot.vendedor_lider || '—';
      if (elLiderSub) {
        const lidM = tot.vendedor_lider_monto || 0;
        const pctL = tot.total_facturado > 0 ? (lidM / tot.total_facturado * 100) : 0;
        elLiderSub.innerText = `${fmtMxn(lidM)} (${pctL.toFixed(1)}% del total)`;
      }
      if (elFacs) elFacs.innerText = `${tot.num_facturas || 0} facturas`;
      if (elVends) elVends.innerText = `${tot.num_vendedores || 0} ejecutivos con ventas`;

      // Poblar selector de vendedores del modal
      const selModalVend = document.getElementById('filter-3m-vendedor');
      if (selModalVend) {
        selModalVend.innerHTML = '<option value="TODOS">👥 Todos los Vendedores</option>';
        (reporte3MesesDataGlobal.resumen_vendedores_3m || []).forEach(v => {
          const opt = document.createElement('option');
          opt.value = v.vendedor;
          opt.innerText = `👤 ${v.vendedor}`;
          selModalVend.appendChild(opt);
        });
      }

      renderModal3mResumen();
      renderModal3mProductos();
    }
  } catch (err) {
    console.error('Error Reporte 3 Meses:', err);
    if (tbody) tbody.innerHTML = `<tr><td colspan="11" class="p-8 text-center text-rose-400">Error al cargar datos: ${err}</td></tr>`;
  }
}

function cerrarReporte3MesesModal() {
  const modal = document.getElementById('modal-vv-3meses');
  if (modal) modal.classList.add('hidden');
}

function switchModal3mSubtab(tab) {
  currentModal3mTab = tab;
  const btnRes = document.getElementById('btn-modal-3m-tab-resumen');
  const btnProds = document.getElementById('btn-modal-3m-tab-prods');
  const viewRes = document.getElementById('modal-3m-view-resumen');
  const viewProds = document.getElementById('modal-3m-view-prods');

  if (tab === 'resumen') {
    if (viewRes) viewRes.classList.remove('hidden');
    if (viewProds) viewProds.classList.add('hidden');
    if (btnRes) btnRes.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-purple-600 text-white shadow-md shadow-purple-600/20 flex items-center transition-all';
    if (btnProds) btnProds.className = 'px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white flex items-center transition-all';
  } else {
    if (viewRes) viewRes.classList.add('hidden');
    if (viewProds) viewProds.classList.remove('hidden');
    if (btnRes) btnRes.className = 'px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white flex items-center transition-all';
    if (btnProds) btnProds.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-purple-600 text-white shadow-md shadow-purple-600/20 flex items-center transition-all';
    renderModal3mProductos();
  }
}

function renderModal3mResumen() {
  const thead = document.getElementById('modal-3m-thead-resumen');
  const tbody = document.getElementById('modal-3m-tbody-resumen');
  if (!thead || !tbody || !reporte3MesesDataGlobal) return;

  const meses = reporte3MesesDataGlobal.periodos_meses_nombres || ['Mes 1', 'Mes 2', 'Mes 3'];
  const vends = reporte3MesesDataGlobal.resumen_vendedores_3m || [];

  thead.innerHTML = `
    <tr>
      <th class="p-3 text-center w-10">#</th>
      <th class="p-3">Vendedor Oficial</th>
      <th class="p-3 text-right">${meses[0]}</th>
      <th class="p-3 text-right">${meses[1]}</th>
      <th class="p-3 text-right">${meses[2]}</th>
      <th class="p-3 text-right font-black text-purple-400">Total 3 Meses ($)</th>
      <th class="p-3 text-right">Unidades (3M)</th>
      <th class="p-3 text-center">Facturas</th>
      <th class="p-3 text-center">Clientes</th>
      <th class="p-3 text-center">% Part</th>
      <th class="p-3 text-center">Tendencia</th>
    </tr>
  `;

  tbody.innerHTML = '';
  if (vends.length === 0) {
    tbody.innerHTML = '<tr><td colspan="11" class="p-8 text-center text-slate-500">No se encontraron datos para este trimestre.</td></tr>';
    return;
  }

  vends.forEach((v, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-900/60 transition-colors';

    const mom = v.tendencia_mom || 0;
    const momBadge = mom > 0
      ? `<span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">+${mom.toFixed(1)}%</span>`
      : (mom < 0 ? `<span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">${mom.toFixed(1)}%</span>` : `<span class="text-slate-500">0.0%</span>`);

    tr.innerHTML = `
      <td class="p-3 text-center text-slate-500 font-bold">${v.posicion || (idx + 1)}</td>
      <td class="p-3 font-semibold text-white flex items-center">
        ${v.vendedor}
        ${idx === 0 ? '<span class="ml-2 px-2 py-0.5 rounded-full text-[9px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">👑 LÍDER</span>' : ''}
      </td>
      <td class="p-3 text-right font-medium text-slate-300">${fmtMxn(v.sub_mes_1)}</td>
      <td class="p-3 text-right font-medium text-slate-300">${fmtMxn(v.sub_mes_2)}</td>
      <td class="p-3 text-right font-medium text-slate-300">${fmtMxn(v.sub_mes_3)}</td>
      <td class="p-3 text-right font-black text-purple-400">${fmtMxn(v.total_subtotal_3m)}</td>
      <td class="p-3 text-right text-blue-400 font-semibold">${fmtNum(v.total_cantidad_3m)}</td>
      <td class="p-3 text-center text-slate-400">${v.num_facturas_3m}</td>
      <td class="p-3 text-center text-slate-400">${v.num_clientes_3m}</td>
      <td class="p-3 text-center font-bold text-purple-300">${v.pct_participacion_3m}%</td>
      <td class="p-3 text-center">${momBadge}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderModal3mProductos() {
  const container = document.getElementById('modal-3m-container-prods');
  if (!container || !reporte3MesesDataGlobal) return;

  const search = (document.getElementById('search-3m-prods')?.value || '').toLowerCase().trim();
  const filterVend = document.getElementById('filter-3m-vendedor')?.value || 'TODOS';
  const meses = reporte3MesesDataGlobal.periodos_meses_nombres || ['Mes 1', 'Mes 2', 'Mes 3'];
  const vends = reporte3MesesDataGlobal.resumen_vendedores_3m || [];

  container.innerHTML = '';

  vends.forEach((v, vIdx) => {
    if (filterVend !== 'TODOS' && v.vendedor !== filterVend) return;

    let prods = v.productos_vendidos_3m || [];
    if (search) {
      const matchV = v.vendedor.toLowerCase().includes(search);
      prods = prods.filter(p => matchV || p.producto.toLowerCase().includes(search) || (p.categoria && p.categoria.toLowerCase().includes(search)));
      if (!matchV && prods.length === 0) return;
    }

    const isOpen = openModal3mAccordions[v.vendedor] ?? (vIdx < 2);

    const card = document.createElement('div');
    card.className = 'bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-xl';
    card.innerHTML = `
      <div onclick="toggleModal3mAcordeon('${v.vendedor}')" class="p-4 bg-slate-900/80 hover:bg-slate-850 cursor-pointer flex flex-wrap items-center justify-between gap-4 transition-colors">
        <div class="flex items-center space-x-3">
          <div class="w-7 h-7 rounded-xl bg-purple-900/50 text-purple-300 border border-purple-700/50 flex items-center justify-center font-bold text-xs">
            #${v.posicion}
          </div>
          <div>
            <h4 class="text-sm font-bold text-white">${v.vendedor}</h4>
            <p class="text-[11px] text-slate-400">Total 3 Meses: <span class="font-bold text-purple-400">${fmtMxn(v.total_subtotal_3m)}</span> · ${prods.length} productos comercializados</p>
          </div>
        </div>
        <div class="flex items-center space-x-4">
          <span class="text-xs font-bold text-blue-400">${fmtNum(v.total_cantidad_3m)} uds</span>
          <i class="fa-solid ${isOpen ? 'fa-chevron-up' : 'fa-chevron-down'} text-xs text-slate-400"></i>
        </div>
      </div>

      <div id="modal-3m-acc-${v.vendedor.replace(/[^a-zA-Z0-9]/g, '_')}" class="${isOpen ? '' : 'hidden'}">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-300">
            <thead class="bg-slate-900 text-slate-400 font-bold uppercase text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th class="p-3 text-center w-10">#</th>
                <th class="p-3">Producto / Código</th>
                <th class="p-3 text-center">Marca</th>
                <th class="p-3 text-right">Cant ${meses[0]}</th>
                <th class="p-3 text-right">Cant ${meses[1]}</th>
                <th class="p-3 text-right">Cant ${meses[2]}</th>
                <th class="p-3 text-right font-bold text-blue-400">Cant Total (3M)</th>
                <th class="p-3 text-right">Precio Prom ($)</th>
                <th class="p-3 text-right font-bold text-purple-400">Total Facturado ($)</th>
                <th class="p-3 text-center">% del Vendedor</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800/60">
              ${prods.map((p, pIdx) => {
                let badgeCat = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
                if (p.categoria === 'PASTA') badgeCat = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
                else if (p.categoria === 'MULTIMARCA') badgeCat = 'bg-purple-500/10 text-purple-400 border-purple-500/20';
                else if (p.categoria === 'MATERIA PRIMA') badgeCat = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';

                return `
                  <tr class="hover:bg-slate-900/40 transition-colors">
                    <td class="p-3 text-center text-slate-500 font-bold">${p.posicion || (pIdx + 1)}</td>
                    <td class="p-3 font-semibold text-white">${p.producto}</td>
                    <td class="p-3 text-center"><span class="px-2 py-0.5 rounded-full text-[9px] font-bold border ${badgeCat}">${p.categoria}</span></td>
                    <td class="p-3 text-right text-slate-400">${fmtNum(p.cant_mes_1)}</td>
                    <td class="p-3 text-right text-slate-400">${fmtNum(p.cant_mes_2)}</td>
                    <td class="p-3 text-right text-slate-400">${fmtNum(p.cant_mes_3)}</td>
                    <td class="p-3 text-right font-black text-blue-400">${fmtNum(p.total_cantidad_3m)}</td>
                    <td class="p-3 text-right text-slate-400">${fmtMxn(p.precio_promedio_3m)}</td>
                    <td class="p-3 text-right font-black text-purple-400">${fmtMxn(p.total_subtotal_3m)}</td>
                    <td class="p-3 text-center font-bold text-slate-400">${p.pct_del_vendedor_3m}%</td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    container.appendChild(card);
  });
}


// ── EXPORTACIÓN A EXCEL ─────────────────────────────────────────────────────
async function exportExcel(tipo) {
  let items = [];
  if (tipo === 'stock') {
    const almacenFilter = document.getElementById('stock-almacen')?.value || 'Todos los Almacenes';
    const marcaFilter = document.getElementById('filter-stock-marca')?.value || 'TODAS';
    const estadoFilter = currentStockQuickFilter || 'TODOS';
    const search = normalizarTexto(document.getElementById('search-stock')?.value || '');

    if (almacenFilter !== 'Todos los Almacenes' || marcaFilter !== 'TODAS' || estadoFilter !== 'TODOS' || search) {
      items = stockDataGlobal.filter(item => {
        if (!almacenesCoincidenJS(almacenFilter, item.almacen)) return false;
        if (marcaFilter !== 'TODAS' && item.clasificacion !== marcaFilter) return false;
        if (search) {
          const prodNorm = normalizarTexto(item.producto);
          const whNorm = normalizarTexto(item.almacen);
          if (!prodNorm.includes(search) && !whNorm.includes(search)) return false;
        }
        if (estadoFilter === 'SOLO_REORDEN') {
          return (item.sugerido_pedir > 0 || item.estado === 'AGOTADO' || item.estado === 'REORDENAR');
        }
        if (estadoFilter !== 'TODOS' && item.estado !== estadoFilter) return false;
        return true;
      });
    } else {
      items = stockDataGlobal;
    }
  }
  else if (tipo === 'productos') items = productosDataGlobal;
  else if (tipo === 'productos_ml') items = mlDataGlobal ? mlDataGlobal.predicciones_ml : [];
  else if (tipo === 'productos_historico') items = mlDataGlobal ? (mlDataGlobal.matriz_historica || mlDataGlobal.top20_historico) : [];
  else if (tipo === 'comisiones') items = comisionesDataGlobal;
  else if (tipo === 'sat') items = satDataGlobal;
  else if (tipo === 'cobranza') items = cobranzaDataGlobal;
  else if (tipo === 'ventas_vendedor') items = ventasVendedorDataGlobal ? ventasVendedorDataGlobal.resumen_vendedores : [];
  else if (tipo === 'ventas_vendedor_3meses') items = reporte3MesesDataGlobal ? reporte3MesesDataGlobal.resumen_vendedores_3m : [];

  // Si se requiere exportar productos y no se ha cargado ML, cargarlo automáticamente
  if ((tipo === 'productos' || tipo === 'productos_ml' || tipo === 'productos_historico') && !mlDataGlobal) {
    await loadTop20HistoricoML();
    if (tipo === 'productos_ml') items = mlDataGlobal ? mlDataGlobal.predicciones_ml : [];
    if (tipo === 'productos_historico') items = mlDataGlobal ? (mlDataGlobal.matriz_historica || mlDataGlobal.top20_historico) : [];
  }

  const payload = { tipo: tipo, items: items };
  if ((tipo === 'productos' || tipo === 'productos_ml' || tipo === 'productos_historico') && mlDataGlobal) {
    payload.ml_data = mlDataGlobal;
  }
  if (tipo === 'ventas_vendedor' && ventasVendedorDataGlobal) {
    payload.vv_data = ventasVendedorDataGlobal;
  }
  if (tipo === 'ventas_vendedor_3meses' && reporte3MesesDataGlobal) {
    payload.vv_data = reporte3MesesDataGlobal;
  }

  try {
    const res = await fetch('/api/export_excel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Reporte_Ejecutivo_${tipo}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (err) {
    alert('Error al exportar Excel: ' + err);
  }
}


// ── EXPORTACIÓN A PDF ───────────────────────────────────────────────────────
async function exportPdf(tipo) {
  let items = [];
  if (tipo === 'stock') {
    const almacenFilter = document.getElementById('stock-almacen')?.value || 'Todos los Almacenes';
    const marcaFilter = document.getElementById('filter-stock-marca')?.value || 'TODAS';
    const estadoFilter = currentStockQuickFilter || 'TODOS';
    const search = normalizarTexto(document.getElementById('search-stock')?.value || '');

    if (almacenFilter !== 'Todos los Almacenes' || marcaFilter !== 'TODAS' || estadoFilter !== 'TODOS' || search) {
      items = stockDataGlobal.filter(item => {
        if (!almacenesCoincidenJS(almacenFilter, item.almacen)) return false;
        if (marcaFilter !== 'TODAS' && item.clasificacion !== marcaFilter) return false;
        if (search) {
          const prodNorm = normalizarTexto(item.producto);
          const whNorm = normalizarTexto(item.almacen);
          if (!prodNorm.includes(search) && !whNorm.includes(search)) return false;
        }
        if (estadoFilter === 'SOLO_REORDEN') {
          return (item.sugerido_pedir > 0 || item.estado === 'AGOTADO' || item.estado === 'REORDENAR');
        }
        if (estadoFilter !== 'TODOS' && item.estado !== estadoFilter) return false;
        return true;
      });
    } else {
      items = stockDataGlobal;
    }
  }
  else if (tipo === 'productos') items = productosDataGlobal;
  else if (tipo === 'productos_ml') items = mlDataGlobal ? mlDataGlobal.predicciones_ml : [];
  else if (tipo === 'productos_historico') items = mlDataGlobal ? (mlDataGlobal.matriz_historica || mlDataGlobal.top20_historico) : [];
  else if (tipo === 'comisiones') items = comisionesDataGlobal;
  else if (tipo === 'sat') items = satDataGlobal;
  else if (tipo === 'cobranza') items = cobranzaDataGlobal;
  else if (tipo === 'ventas_vendedor') items = ventasVendedorDataGlobal ? ventasVendedorDataGlobal.resumen_vendedores : [];
  else if (tipo === 'ventas_vendedor_3meses') items = reporte3MesesDataGlobal ? reporte3MesesDataGlobal.resumen_vendedores_3m : [];

  if ((tipo === 'productos' || tipo === 'productos_ml' || tipo === 'productos_historico') && !mlDataGlobal) {
    await loadTop20HistoricoML();
    if (tipo === 'productos_ml') items = mlDataGlobal ? mlDataGlobal.predicciones_ml : [];
    if (tipo === 'productos_historico') items = mlDataGlobal ? (mlDataGlobal.matriz_historica || mlDataGlobal.top20_historico) : [];
  }

  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  const payload = { tipo: tipo, items: items, empresa_nombre: empresa };
  if ((tipo === 'productos' || tipo === 'productos_ml' || tipo === 'productos_historico') && mlDataGlobal) {
    payload.ml_data = mlDataGlobal;
  }
  if (tipo === 'ventas_vendedor' && ventasVendedorDataGlobal) {
    payload.ml_data = ventasVendedorDataGlobal;
  }
  if (tipo === 'ventas_vendedor_3meses' && reporte3MesesDataGlobal) {
    payload.ml_data = reporte3MesesDataGlobal;
  }

  try {
    const res = await fetch('/api/export_pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      alert('Error al generar PDF: ' + (errJson.error || res.statusText));
      return;
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Reporte_Ejecutivo_${tipo}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (err) {
    alert('Error al exportar PDF: ' + err);
  }
}

// ── MÓDULO 7: ESTADO DE RESULTADOS (P&L) & RENTABILIDAD FINANCIERA ──────────
function switchPnlSubtab(subtab) {
  currentPnlSubtab = subtab;
  const subtabs = ['cascada', 'categorias', 'productos', 'vendedores'];
  
  subtabs.forEach(s => {
    const v = document.getElementById(`view-pnl-${s}`);
    const b = document.getElementById(`btn-pnl-subtab-${s}`);
    if (v) v.classList.add('hidden');
    if (b) b.className = 'px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white transition-all flex items-center';
  });

  const activeV = document.getElementById(`view-pnl-${subtab}`);
  const activeB = document.getElementById(`btn-pnl-subtab-${subtab}`);
  if (activeV) activeV.classList.remove('hidden');
  if (activeB) {
    if (subtab === 'cascada') activeB.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-purple-600 text-white transition-all shadow-md shadow-purple-600/20 flex items-center';
    else if (subtab === 'categorias') activeB.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 text-white transition-all shadow-md shadow-blue-600/20 flex items-center';
    else if (subtab === 'productos') activeB.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 text-white transition-all shadow-md shadow-emerald-600/20 flex items-center';
    else if (subtab === 'vendedores') activeB.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-amber-600 text-white transition-all shadow-md shadow-amber-600/20 flex items-center';
  }

  renderPnlView();
}

async function loadPnlData() {
  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  const anio = parseInt(document.getElementById('pnl-anio')?.value || '2026', 10);
  const mes = parseInt(document.getElementById('pnl-mes')?.value || '0', 10);

  showLoading('Consultando Estado de Resultados...', 'Cruzando facturación Odoo 19 con lista de costos Challenger...');

  try {
    const res = await fetch('/api/estado_resultados', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ empresa_nombre: empresa, anio: anio, mes: mes })
    });
    const data = await res.json();
    if (data.success && data.data) {
      pnlDataGlobal = data.data;

      // KPIs
      const k = pnlDataGlobal.kpis || {};
      const elVn = document.getElementById('kpi-pnl-ventas-netas');
      const elVnSub = document.getElementById('kpi-pnl-sub-ventas');
      const elCogs = document.getElementById('kpi-pnl-cogs');
      const elCogsSub = document.getElementById('kpi-pnl-sub-cogs');
      const elUb = document.getElementById('kpi-pnl-utilidad-bruta');
      const elUbMg = document.getElementById('kpi-pnl-badge-margen-bruto');
      const elCom = document.getElementById('kpi-pnl-comisiones');
      const elComSub = document.getElementById('kpi-pnl-sub-comisiones');
      const elCont = document.getElementById('kpi-pnl-contribucion');
      const elContMg = document.getElementById('kpi-pnl-badge-margen-contribucion');
      const elPeriodo = document.getElementById('lbl-pnl-periodo');

      if (elVn) elVn.innerText = fmtMxn(k.ventas_netas);
      if (elVnSub) elVnSub.innerText = `Brutas: ${fmtMxn(k.ventas_brutas)} (-${fmtMxn(k.devoluciones_descuentos)})`;
      if (elCogs) elCogs.innerText = fmtMxn(k.costo_ventas);
      if (elCogsSub) {
        const cogsPct = k.ventas_netas > 0 ? (k.costo_ventas / k.ventas_netas * 100) : 0;
        elCogsSub.innerText = `${cogsPct.toFixed(1)}% de las Ventas`;
      }
      if (elUb) elUb.innerText = fmtMxn(k.utilidad_bruta);
      if (elUbMg) elUbMg.innerText = `${k.margen_bruto_pct || 0}%`;
      if (elCom) elCom.innerText = fmtMxn(k.comisiones_vendedores);
      if (elComSub) {
        const comPct = k.ventas_netas > 0 ? (k.comisiones_vendedores / k.ventas_netas * 100) : 0;
        elComSub.innerText = `${comPct.toFixed(1)}% de las Ventas`;
      }
      if (elCont) elCont.innerText = fmtMxn(k.contribucion_neta);
      if (elContMg) elContMg.innerText = `${k.margen_contribucion_pct || 0}% Margen`;
      if (elPeriodo) elPeriodo.innerText = mes === 0 ? `Ejercicio ${anio} Completo` : `Mes ${mes}/${anio}`;

      // Llenar dropdown de categorías de producto si aplica
      const selCat = document.getElementById('filter-pnl-prod-cat');
      if (selCat && pnlDataGlobal.categorias) {
        const currentVal = selCat.value;
        selCat.innerHTML = '<option value="TODAS">🎨 Todas las Categorías</option>';
        pnlDataGlobal.categorias.forEach(c => {
          const opt = document.createElement('option');
          opt.value = c.categoria;
          opt.innerText = `${c.categoria} (${c.margen_pct}%)`;
          selCat.appendChild(opt);
        });
        selCat.value = currentVal;
      }

      renderPnlView();
      hideLoading('¡P&L Calculado!', 'Estado de resultados y rentabilidad generados.');
    } else {
      hideLoading('⚠️ Sin Datos', 'No se pudieron calcular los resultados.');
    }
  } catch (err) {
    console.error('Error P&L:', err);
    hideLoading('⚠️ Error P&L', 'Error al calcular estado de resultados.');
  }
}

function renderPnlView() {
  if (!pnlDataGlobal) return;
  if (currentPnlSubtab === 'cascada') renderPnlCascada();
  else if (currentPnlSubtab === 'categorias') renderPnlCategorias();
  else if (currentPnlSubtab === 'productos') renderPnlProductos();
  else if (currentPnlSubtab === 'vendedores') renderPnlVendedores();
}

function switchPnlCascadaMode(mode) {
  currentPnlCascadaMode = mode;
  const btnSplit = document.getElementById('btn-pnl-mode-split');
  const btnMatrix = document.getElementById('btn-pnl-mode-matrix');
  const viewSplit = document.getElementById('pnl-cascada-split-view');
  const viewMatrix = document.getElementById('pnl-cascada-matrix-view');

  if (mode === 'split') {
    if (viewSplit) viewSplit.classList.remove('hidden');
    if (viewMatrix) viewMatrix.classList.add('hidden');
    if (btnSplit) btnSplit.className = 'px-3.5 py-1.5 rounded-xl text-xs font-bold bg-purple-600 text-white transition-all shadow-md shadow-purple-600/20 flex items-center';
    if (btnMatrix) btnMatrix.className = 'px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white transition-all flex items-center';
  } else {
    if (viewSplit) viewSplit.classList.add('hidden');
    if (viewMatrix) viewMatrix.classList.remove('hidden');
    if (btnSplit) btnSplit.className = 'px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white transition-all flex items-center';
    if (btnMatrix) btnMatrix.className = 'px-3.5 py-1.5 rounded-xl text-xs font-bold bg-purple-600 text-white transition-all shadow-md shadow-purple-600/20 flex items-center';
  }
}

function renderPnlCascada() {
  if (!pnlDataGlobal) return;
  const tbodyCascada = document.getElementById('tbody-pnl-cascada');
  const tbodyMensual = document.getElementById('tbody-pnl-mensual');
  const tbodyMatrixFull = document.getElementById('tbody-pnl-matrix-full');

  // 1. Tabla Cascada Split
  if (tbodyCascada && pnlDataGlobal.cascada_pnl) {
    tbodyCascada.innerHTML = '';
    pnlDataGlobal.cascada_pnl.forEach(item => {
      const tr = document.createElement('tr');
      let fontStyle = 'text-slate-300 font-semibold';
      let valStyle = 'text-white font-bold';

      if (item.tipo === 'total_clave') {
        tr.className = 'bg-blue-600/10 border-y border-blue-500/30';
        fontStyle = 'text-blue-300 font-black text-xs uppercase';
        valStyle = 'text-blue-300 font-black text-sm';
      } else if (item.tipo === 'utilidad_bruta') {
        tr.className = 'bg-emerald-500/10 border-y border-emerald-500/30';
        fontStyle = 'text-emerald-300 font-black text-xs uppercase';
        valStyle = 'text-emerald-300 font-black text-sm';
      } else if (item.tipo === 'total_final') {
        tr.className = 'bg-emerald-600/20 border-y-2 border-emerald-500/50';
        fontStyle = 'text-emerald-400 font-black text-sm uppercase';
        valStyle = 'text-emerald-400 font-black text-base';
      } else if (item.tipo === 'costo' || item.tipo === 'deduccion') {
        valStyle = 'text-red-400 font-semibold';
      } else if (item.tipo === 'gasto') {
        valStyle = 'text-purple-300 font-semibold';
      }

      tr.innerHTML = `
        <td class="p-3 ${fontStyle}">${item.concepto}</td>
        <td class="p-3 text-right ${valStyle}">${fmtMxn(item.monto)}</td>
        <td class="p-3 text-center text-slate-400 font-mono text-[11px] w-20">${item.pct.toFixed(1)}%</td>
      `;
      tbodyCascada.appendChild(tr);
    });
  }

  // 2. Tabla Evolución Mensual Split
  if (tbodyMensual && pnlDataGlobal.matriz_mensual) {
    tbodyMensual.innerHTML = '';
    pnlDataGlobal.matriz_mensual.forEach(m => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-800/40 transition-colors';
      let badgeClass = 'text-emerald-400 font-bold';
      if (m.margen_pct < 30) badgeClass = 'text-amber-400 font-bold';
      if (m.margen_pct <= 0) badgeClass = 'text-slate-500 font-normal';

      tr.innerHTML = `
        <td class="p-3 text-center font-bold text-white bg-slate-950/40">${m.mes_nombre}</td>
        <td class="p-3 text-right text-slate-200 font-medium">${fmtMxn(m.ventas_netas)}</td>
        <td class="p-3 text-right text-amber-300/90 font-medium">${fmtMxn(m.cogs)}</td>
        <td class="p-3 text-right text-emerald-400 font-bold">${fmtMxn(m.utilidad_bruta)}</td>
        <td class="p-3 text-center ${badgeClass}">${m.margen_pct}%</td>
      `;
      tbodyMensual.appendChild(tr);
    });
  }

  // 3. Matriz Comparativa Completa 12 Meses
  if (tbodyMatrixFull && pnlDataGlobal.cascada_matriz_mensual && pnlDataGlobal.meses_nombres) {
    tbodyMatrixFull.innerHTML = '';
    const meses = pnlDataGlobal.meses_nombres;

    pnlDataGlobal.cascada_matriz_mensual.forEach(row => {
      const tr = document.createElement('tr');
      let rowBg = 'hover:bg-slate-800/40';
      let isPct = row.tipo === 'pct';
      let fontClass = 'text-slate-300';
      let totalClass = 'text-white font-black bg-purple-950/30';

      if (row.tipo === 'total_clave') {
        rowBg = 'bg-blue-600/10 border-y border-blue-500/30';
        fontClass = 'text-blue-300 font-black uppercase text-xs';
        totalClass = 'text-blue-300 font-black bg-blue-900/40';
      } else if (row.tipo === 'utilidad_bruta') {
        rowBg = 'bg-emerald-500/10 border-y border-emerald-500/30';
        fontClass = 'text-emerald-300 font-black uppercase text-xs';
        totalClass = 'text-emerald-300 font-black bg-emerald-900/40';
      } else if (row.tipo === 'total_final') {
        rowBg = 'bg-emerald-600/20 border-y-2 border-emerald-500/50';
        fontClass = 'text-emerald-400 font-black uppercase text-xs';
        totalClass = 'text-emerald-300 font-black text-sm bg-emerald-900/60';
      } else if (row.tipo === 'costo' || row.tipo === 'deduccion') {
        fontClass = 'text-amber-400 font-medium';
      }

      let cellsHtml = `<td class="p-3 font-semibold ${fontClass} sticky left-0 bg-slate-900 z-10 truncate">${row.concepto}</td>`;
      
      meses.forEach(mName => {
        const val = row.meses[mName] || 0;
        let cellText = isPct ? `${val.toFixed(1)}%` : fmtMxn(val);
        let cellClass = val === 0 ? 'text-slate-600' : (isPct ? 'text-emerald-400 font-bold' : 'text-slate-200');
        cellsHtml += `<td class="p-3 text-right ${cellClass} font-mono text-xs">${cellText}</td>`;
      });

      let totalText = isPct ? `${row.total.toFixed(1)}%` : fmtMxn(row.total);
      cellsHtml += `<td class="p-3 text-right ${totalClass} font-mono text-xs">${totalText}</td>`;

      tr.className = `${rowBg} transition-colors`;
      tr.innerHTML = cellsHtml;
      tbodyMatrixFull.appendChild(tr);
    });
  }
}

function renderPnlCategorias() {
  if (!pnlDataGlobal || !pnlDataGlobal.categorias) return;
  const tbody = document.getElementById('tbody-pnl-categorias');
  const lbl = document.getElementById('lbl-pnl-cat-count');
  if (!tbody) return;

  const cats = pnlDataGlobal.categorias || [];
  if (lbl) lbl.innerText = `${cats.length} familias de producto analizadas`;
  tbody.innerHTML = '';

  cats.forEach((c, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/40 transition-colors';

    let badgeColor = 'bg-blue-500';
    if (c.margen_pct >= 55) badgeColor = 'bg-emerald-500';
    else if (c.margen_pct >= 40) badgeColor = 'bg-blue-500';
    else if (c.margen_pct >= 25) badgeColor = 'bg-amber-500';
    else badgeColor = 'bg-red-500';

    tr.innerHTML = `
      <td class="p-3 text-center text-slate-500 font-bold">${idx + 1}</td>
      <td class="p-3 font-bold text-white flex items-center">
        <span class="w-2.5 h-2.5 rounded-full ${badgeColor} mr-2"></span>
        ${c.categoria}
      </td>
      <td class="p-3 text-right text-slate-300">${fmtNum(c.unidades)} uds</td>
      <td class="p-3 text-right font-semibold text-slate-200">${fmtMxn(c.ventas)}</td>
      <td class="p-3 text-right text-amber-300/90">${fmtMxn(c.cogs)}</td>
      <td class="p-3 text-right font-black text-emerald-400">${fmtMxn(c.utilidad_bruta)}</td>
      <td class="p-3 text-center">
        <div class="flex items-center justify-center space-x-2">
          <div class="w-16 bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div class="${badgeColor} h-1.5 rounded-full" style="width: ${Math.min(100, Math.max(0, c.margen_pct))}%"></div>
          </div>
          <span class="text-xs font-black text-white">${c.margen_pct}%</span>
        </div>
      </td>
      <td class="p-3 text-center font-semibold text-purple-300">${c.pct_de_venta}%</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderPnlProductos() {
  if (!pnlDataGlobal || !pnlDataGlobal.top_productos) return;
  const tbody = document.getElementById('tbody-pnl-productos');
  const lblCount = document.getElementById('lbl-pnl-prods-count');
  if (!tbody) return;

  const search = normalizarTexto(document.getElementById('search-pnl-prod')?.value || '');
  const catFilter = document.getElementById('filter-pnl-prod-cat')?.value || 'TODAS';

  let prods = pnlDataGlobal.top_productos || [];
  if (search) {
    prods = prods.filter(p => normalizarTexto(p.producto).includes(search) || normalizarTexto(p.nombre_completo).includes(search));
  }
  if (catFilter !== 'TODAS') {
    prods = prods.filter(p => p.categoria === catFilter);
  }

  if (lblCount) lblCount.innerText = `${prods.length} productos en catálogo`;

  tbody.innerHTML = '';
  if (prods.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" class="p-8 text-center text-slate-500 font-medium">No se encontraron productos con los filtros seleccionados.</td></tr>';
    return;
  }

  prods.forEach((p, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/60 cursor-pointer transition-colors group';
    tr.title = '💡 Haz doble clic para ver análisis de costos, margen y gráficas de este producto';
    tr.ondblclick = () => abrirModalDetalleProducto(p.producto);

    let badgeClass = 'text-emerald-400 font-bold';
    if (p.margen_pct >= 55) badgeClass = 'text-emerald-400 font-black';
    else if (p.margen_pct >= 40) badgeClass = 'text-blue-400 font-bold';
    else if (p.margen_pct >= 25) badgeClass = 'text-amber-400 font-bold';
    else badgeClass = 'text-red-400 font-bold';

    tr.innerHTML = `
      <td class="p-3 text-center text-slate-500 font-bold">${idx + 1}</td>
      <td class="p-3 font-semibold text-white group-hover:text-purple-300 transition-colors truncate max-w-xs" title="${p.nombre_completo}">${p.producto}</td>
      <td class="p-3 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700">${p.categoria}</span></td>
      <td class="p-3 text-right font-medium text-slate-300">${fmtNum(p.unidades)}</td>
      <td class="p-3 text-right font-mono text-amber-400 font-semibold">${fmtMxn(p.costo_unitario)}</td>
      <td class="p-3 text-right font-mono text-blue-400">${fmtMxn(p.precio_promedio)}</td>
      <td class="p-3 text-right font-semibold text-slate-200">${fmtMxn(p.ventas)}</td>
      <td class="p-3 text-right font-black text-emerald-400">${fmtMxn(p.utilidad_bruta)}</td>
      <td class="p-3 text-center ${badgeClass}">${p.margen_pct}%</td>
      <td class="p-3 text-center">
        <button onclick="event.stopPropagation(); abrirModalDetalleProducto('${encodeURIComponent(p.producto)}')" class="px-2.5 py-1 rounded-xl bg-purple-600/30 hover:bg-purple-600 text-purple-200 hover:text-white text-[10px] font-bold transition-all flex items-center justify-center mx-auto">
          <i class="fa-solid fa-chart-pie mr-1"></i> Costos
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderPnlVendedores() {
  if (!pnlDataGlobal || !pnlDataGlobal.vendedores) return;
  const tbody = document.getElementById('tbody-pnl-vendedores');
  const lbl = document.getElementById('lbl-pnl-vend-count');
  if (!tbody) return;

  const vends = pnlDataGlobal.vendedores || [];
  if (lbl) lbl.innerText = `${vends.length} asesores comerciales evaluados`;
  tbody.innerHTML = '';

  vends.forEach((v, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/40 transition-colors';

    tr.innerHTML = `
      <td class="p-3 text-center text-slate-500 font-bold">${idx + 1}</td>
      <td class="p-3 font-bold text-white flex items-center">
        <i class="fa-solid fa-user-tie mr-2 text-slate-500"></i>
        ${v.vendedor}
      </td>
      <td class="p-3 text-right font-semibold text-slate-200">${fmtMxn(v.ventas)}</td>
      <td class="p-3 text-right text-amber-300/90">${fmtMxn(v.cogs)}</td>
      <td class="p-3 text-right font-black text-emerald-400">${fmtMxn(v.utilidad_bruta)}</td>
      <td class="p-3 text-center font-bold text-blue-400">${v.margen_pct}%</td>
      <td class="p-3 text-right text-purple-300 font-semibold">${fmtMxn(v.comision_estimada)}</td>
      <td class="p-3 text-right font-black text-emerald-300 bg-emerald-500/10">${fmtMxn(v.contribucion_neta)}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── MODAL DETALLE DE RENTABILIDAD & GRÁFICAS POR PRODUCTO ────────────────────
async function abrirModalDetalleProducto(prodNameRaw) {
  let prodName = decodeURIComponent(prodNameRaw || '').trim();

  // Si no se han cargado datos P&L, consultarlos primero
  if (!pnlDataGlobal) {
    await loadPnlData();
  }
  if (!pnlDataGlobal || !pnlDataGlobal.top_productos) return;

  const prods = pnlDataGlobal.top_productos;
  const pNorm = normalizarTexto(prodName);
  
  // Buscar producto exacto o coincidencia
  let p = prods.find(item => normalizarTexto(item.producto) === pNorm || normalizarTexto(item.nombre_completo) === pNorm);
  if (!p) {
    p = prods.find(item => pNorm.includes(normalizarTexto(item.producto)) || normalizarTexto(item.nombre_completo).includes(pNorm));
  }
  if (!p) {
    p = prods[0];
  }
  if (!p) return;

  // Llenar datos de texto
  document.getElementById('modal-prod-title').innerText = p.producto || p.nombre_completo;
  document.getElementById('modal-prod-cat').innerText = p.categoria || 'Challenger';
  
  // Extraer código
  let codeStr = 'PRODUCTO';
  if (p.nombre_completo && p.nombre_completo.includes('[') && p.nombre_completo.includes(']')) {
    codeStr = p.nombre_completo.split('[')[1].split(']')[0];
  }
  document.getElementById('modal-prod-code').innerText = codeStr;

  // Llenar 4 KPIs
  document.getElementById('modal-prod-kpi-costo').innerText = fmtMxn(p.costo_unitario);
  document.getElementById('modal-prod-kpi-precio').innerText = fmtMxn(p.precio_promedio);
  document.getElementById('modal-prod-kpi-margen-u').innerText = fmtMxn(p.margen_unitario);
  document.getElementById('modal-prod-badge-margen').innerText = `${p.margen_pct || 0}% Margen`;
  document.getElementById('modal-prod-kpi-unidades').innerText = `${fmtNum(p.unidades)} uds`;
  document.getElementById('modal-prod-kpi-total-utilidad').innerText = `Utilidad: ${fmtMxn(p.utilidad_bruta)} (Ventas: ${fmtMxn(p.ventas)})`;

  // Porcentajes para Donut
  const cogsPct = p.precio_promedio > 0 ? (p.costo_unitario / p.precio_promedio * 100) : 0;
  const utilPct = p.precio_promedio > 0 ? Math.max(0, 100 - cogsPct) : 0;
  document.getElementById('modal-prod-donut-cogs-pct').innerText = `${cogsPct.toFixed(1)}%`;
  document.getElementById('modal-prod-donut-utilidad-pct').innerText = `${utilPct.toFixed(1)}%`;

  // 1. Renderizar Gráfica de Barras Mensual (12 Meses)
  const ctxMensual = document.getElementById('chart-prod-modal-mensual')?.getContext('2d');
  if (ctxMensual) {
    if (chartProdModalMensual) chartProdModalMensual.destroy();
    
    const mesesLabels = (p.mensual || []).map(m => m.mes_nombre);
    const ventasSeries = (p.mensual || []).map(m => m.ventas);
    const cogsSeries = (p.mensual || []).map(m => m.cogs);
    const utilSeries = (p.mensual || []).map(m => m.utilidad);

    chartProdModalMensual = new Chart(ctxMensual, {
      type: 'bar',
      data: {
        labels: mesesLabels,
        datasets: [
          { label: 'Ventas ($)', data: ventasSeries, backgroundColor: '#3b82f6', borderRadius: 4 },
          { label: 'Costo COGS ($)', data: cogsSeries, backgroundColor: '#f59e0b', borderRadius: 4 },
          { label: 'Utilidad Bruta ($)', data: utilSeries, backgroundColor: '#10b981', borderRadius: 4 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#94a3b8', font: { size: 11, weight: 'bold' } } }
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 } } },
          y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8', font: { size: 10 }, callback: v => '$' + (v >= 1000 ? (v/1000).toFixed(0) + 'k' : v) } }
        }
      }
    });
  }

  // 2. Renderizar Gráfica Donut de Estructura de Precio
  const ctxDonut = document.getElementById('chart-prod-modal-donut')?.getContext('2d');
  if (ctxDonut) {
    if (chartProdModalDonut) chartProdModalDonut.destroy();

    chartProdModalDonut = new Chart(ctxDonut, {
      type: 'doughnut',
      data: {
        labels: ['Costo de Fábrica', 'Margen de Ganancia'],
        datasets: [{
          data: [p.costo_unitario, Math.max(0, p.margen_unitario)],
          backgroundColor: ['#f59e0b', '#10b981'],
          borderWidth: 0,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 10 } } }
        },
        cutout: '70%'
      }
    });
  }

  // 3. Renderizar Tabla de Vendedores de este Producto
  const tbodyVends = document.getElementById('tbody-modal-prod-vendedores');
  const lblVends = document.getElementById('modal-prod-vends-count');
  if (tbodyVends) {
    tbodyVends.innerHTML = '';
    const vends = p.vendedores || [];
    if (lblVends) lblVends.innerText = `${vends.length} asesores activos`;

    if (vends.length === 0) {
      tbodyVends.innerHTML = '<tr><td colspan="7" class="p-4 text-center text-slate-500">Sin historial por vendedor.</td></tr>';
    } else {
      vends.forEach(v => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-800/40 transition-colors';
        tr.innerHTML = `
          <td class="p-2.5 font-bold text-white">${v.vendedor}</td>
          <td class="p-2.5 text-right text-slate-300 font-medium">${fmtNum(v.unidades)} uds</td>
          <td class="p-2.5 text-right text-blue-400 font-mono">${fmtMxn(v.precio_promedio)}</td>
          <td class="p-2.5 text-right text-slate-200 font-semibold">${fmtMxn(v.ventas)}</td>
          <td class="p-2.5 text-right text-amber-400/90">${fmtMxn(v.cogs)}</td>
          <td class="p-2.5 text-right text-emerald-400 font-black">${fmtMxn(v.utilidad_bruta)}</td>
          <td class="p-2.5 text-center font-bold text-emerald-300">${v.margen_pct}%</td>
        `;
        tbodyVends.appendChild(tr);
      });
    }
  }

  // Abrir Modal
  document.getElementById('modal-producto-rentabilidad-detalle').classList.remove('hidden');
}

function cerrarModalProductoDetalle() {
  const modal = document.getElementById('modal-producto-rentabilidad-detalle');
  if (modal) modal.classList.add('hidden');
}

// ── CONTROLADOR DE TEMAS (MODO BLANCO CLARO / AZUL OSCURO) ──────────────────
function initTheme() {
  const saved = localStorage.getItem('challenger_theme') || 'dark';
  applyTheme(saved);
}

function toggleTheme() {
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  applyTheme(newTheme);
}

function applyTheme(theme) {
  currentTheme = theme;
  localStorage.setItem('challenger_theme', theme);
  const icon = document.getElementById('theme-icon');
  const text = document.getElementById('theme-text');

  if (theme === 'light') {
    document.documentElement.classList.add('theme-light');
    document.body.classList.add('theme-light');
    if (icon) icon.className = 'fa-solid fa-moon text-blue-600 sm:mr-1.5 text-xs sm:text-sm';
    if (text) text.innerText = 'Modo Azul Oscuro';
  } else {
    document.documentElement.classList.remove('theme-light');
    document.body.classList.remove('theme-light');
    if (icon) icon.className = 'fa-solid fa-sun text-amber-400 sm:mr-1.5 text-xs sm:text-sm';
    if (text) text.innerText = 'Modo Blanco';
  }

  // Si hay gráficas activas, actualizarlas
  if (chartTopProductos) chartTopProductos.update();
  if (chartProdModalMensual) chartProdModalMensual.update();
  if (chartProdModalDonut) chartProdModalDonut.update();
}

// =============================================================================
// MÓDULO 8: GASTOS A PROVEEDORES & CONCILIACIÓN BANCARIA AUTOMÁTICA
// =============================================================================

async function loadGastosConciliacion(forceSync = false) {
  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  const badgeEmpresa = document.getElementById('gastos-badge-empresa');
  if (badgeEmpresa) badgeEmpresa.innerText = empresa.toUpperCase();

  showLoading('Conciliando Gastos & Bancos...', 'Consultando comprobantes WhatsApp y estados de cuenta...');

  try {
    const resp = await fetch(`/api/gastos/conciliacion?empresa=${encodeURIComponent(empresa)}`);
    const data = await resp.json();

    if (data.success || data.status === 'success') {
      gastosDataGlobal = data.data || data;
      renderGastosKPIs();
      renderGastosVistas();
      const concCount = gastosDataGlobal.kpis?.total_conciliados || 0;
      hideLoading('¡Conciliación Actualizada!', `${concCount} movimientos conciliados`);
    } else {
      hideLoading('Atención', data.error || data.message || 'No se pudo cargar la conciliación');
    }
  } catch (err) {
    console.error('Error al cargar conciliación de gastos:', err);
    hideLoading('Error', 'No se pudo conectar con el servidor de conciliación');
  }
}

function renderGastosKPIs() {
  if (!gastosDataGlobal || !gastosDataGlobal.kpis) return;
  const k = gastosDataGlobal.kpis;

  const elBanco = document.getElementById('gastos-kpi-banco');
  const elBancoCount = document.getElementById('gastos-kpi-banco-count');
  if (elBanco) elBanco.innerText = fmtMxn(k.total_banco_egresos);
  if (elBancoCount) elBancoCount.innerText = `${k.total_movimientos_banco || 0} cargos registrados`;

  const elComp = document.getElementById('gastos-kpi-comprobantes');
  const elCompCount = document.getElementById('gastos-kpi-comprobantes-count');
  if (elComp) elComp.innerText = fmtMxn(k.total_comprobantes_monto);
  if (elCompCount) elCompCount.innerText = `${k.total_comprobantes || 0} archivos cargados`;

  const elConc = document.getElementById('gastos-kpi-conciliado');
  const elConcCount = document.getElementById('gastos-kpi-conciliado-count');
  const elConcPct = document.getElementById('gastos-kpi-conciliado-pct');
  if (elConc) elConc.innerText = fmtMxn(k.monto_conciliado);
  if (elConcCount) elConcCount.innerText = `${k.total_conciliados || 0} movimientos cruzados`;
  if (elConcPct) elConcPct.innerText = `${k.porcentaje_conciliado || 0}%`;

  const elSin = document.getElementById('gastos-kpi-sin-comprobante');
  const elSinCount = document.getElementById('gastos-kpi-sin-comprobante-count');
  if (elSin) elSin.innerText = fmtMxn(k.monto_sin_comprobante);
  if (elSinCount) elSinCount.innerText = `${k.total_sin_comprobante || 0} cargos sin respaldar`;

  const elPend = document.getElementById('gastos-kpi-pendientes');
  const elPendCount = document.getElementById('gastos-kpi-pendientes-count');
  if (elPend) elPend.innerText = fmtMxn(k.monto_comprobantes_pendientes);
  if (elPendCount) elPendCount.innerText = `${k.total_comprobantes_pendientes || 0} pendientes en banco`;
}

function switchGastosSubtab(subtab) {
  currentGastosSubtab = subtab;
  const subtabs = ['tablero', 'comprobantes', 'movimientos', 'proveedores'];

  subtabs.forEach(s => {
    const view = document.getElementById(`gastos-view-${s}`);
    const btn = document.getElementById(`btn-gastos-subtab-${s}`);
    if (view) view.classList.add('hidden');
    if (btn) {
      btn.className = 'px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 flex items-center transition-all cursor-pointer';
    }
  });

  const activeView = document.getElementById(`gastos-view-${subtab}`);
  const activeBtn = document.getElementById(`btn-gastos-subtab-${subtab}`);
  if (activeView) activeView.classList.remove('hidden');
  if (activeBtn) {
    activeBtn.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-rose-600 text-white shadow-md shadow-rose-600/20 flex items-center transition-all cursor-pointer';
  }

  renderGastosVistas();
}

function renderGastosVistas() {
  if (currentGastosSubtab === 'tablero') renderGastosTablero();
  else if (currentGastosSubtab === 'comprobantes') renderGastosComprobantes();
  else if (currentGastosSubtab === 'movimientos') renderGastosMovimientos();
  else if (currentGastosSubtab === 'proveedores') renderGastosProveedores();
}

// ── VISTA 1: TABLERO COMPARATIVO LADO A LADO ─────────────────────────────
function renderGastosTablero() {
  if (!gastosDataGlobal) return;
  const tbody = document.getElementById('tbody-gastos-tablero');
  const lblCount = document.getElementById('lbl-gastos-tablero-count');
  if (!tbody) return;

  const query = normalizarTexto(document.getElementById('search-gastos-tablero')?.value || '');
  const filtroBanco = document.getElementById('filtro-gastos-banco')?.value || 'TODOS';
  const filtroEstado = document.getElementById('filtro-gastos-estado')?.value || 'TODOS';

  let items = gastosDataGlobal.conciliados || [];

  if (filtroBanco !== 'TODOS') {
    items = items.filter(it => normalizarTexto(it.movimiento_banco?.banco || '') === normalizarTexto(filtroBanco));
  }

  if (filtroEstado !== 'TODOS') {
    items = items.filter(it => it.estado_conciliacion === filtroEstado);
  }

  if (query) {
    items = items.filter(it => {
      const b = it.movimiento_banco || {};
      const c = it.comprobante || {};
      const txt = `${b.concepto || ''} ${b.referencia || ''} ${b.banco || ''} ${c.proveedor || ''} ${c.nota_whatsapp || ''} ${c.clave_rastreo || ''}`;
      return normalizarTexto(txt).includes(query);
    });
  }

  if (lblCount) lblCount.innerText = `${items.length} registros`;
  tbody.innerHTML = '';

  if (items.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10" class="p-8 text-center text-slate-500">
          <i class="fa-solid fa-inbox text-3xl mb-2 block text-slate-600"></i>
          No se encontraron registros que coincidan con los filtros.
        </td>
      </tr>
    `;
    return;
  }

  items.forEach((it, idx) => {
    const b = it.movimiento_banco || {};
    const c = it.comprobante || null;
    const est = it.estado_conciliacion;

    let badgeEstadoHtml = '';
    if (est === 'CONCILIADO') {
      badgeEstadoHtml = `<span class="px-2.5 py-1 rounded-full text-[10px] font-black bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center gap-1"><i class="fa-solid fa-circle-check text-[10px]"></i> Conciliado (${it.match_score}%)</span>`;
    } else if (est === 'PENDIENTE') {
      badgeEstadoHtml = `<span class="px-2.5 py-1 rounded-full text-[10px] font-black bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center justify-center gap-1"><i class="fa-solid fa-triangle-exclamation text-[10px]"></i> ${it.razon_diferencia || 'Diferencia'}</span>`;
    } else {
      badgeEstadoHtml = `<span class="px-2.5 py-1 rounded-full text-[10px] font-black bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center justify-center gap-1"><i class="fa-solid fa-circle-xmark text-[10px]"></i> Sin Comprobante</span>`;
    }

    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/40 transition-colors';

    let compColProveedor = '<span class="text-slate-500 italic">Sin comprobante</span>';
    let compColArchivo = '<span class="text-slate-600">—</span>';
    let compColMonto = '<span class="text-slate-600 font-mono text-right block">—</span>';
    let accionHtml = `<button onclick="abrirModalConciliarManual('${b.id}')" class="px-2.5 py-1 rounded-lg bg-rose-600/20 hover:bg-rose-600 border border-rose-500/30 text-rose-300 hover:text-white text-[11px] font-bold transition-all cursor-pointer" title="Vincular con comprobante"><i class="fa-solid fa-link mr-1"></i> Vincular</button>`;

    if (c) {
      compColProveedor = `
        <div class="space-y-0.5">
          <div class="font-bold text-white flex items-center gap-1.5">
            <i class="fa-solid fa-user-check text-purple-400 text-xs"></i>
            <span>${c.proveedor || 'Proveedor Desconocido'}</span>
          </div>
          ${c.nota_whatsapp ? `<div class="text-[10px] text-emerald-400 font-mono font-bold flex items-center gap-1"><i class="fa-brands fa-whatsapp text-[10px]"></i> "${c.nota_whatsapp}"</div>` : ''}
        </div>
      `;

      compColArchivo = `
        <button onclick="abrirModalVisorComprobante('${c.id}')" class="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1 truncate max-w-[180px] cursor-pointer" title="Ver comprobante original">
          <i class="fa-solid fa-file-pdf text-rose-400"></i>
          <span class="truncate">${c.archivo_nombre || 'comprobante'}</span>
        </button>
      `;

      compColMonto = `
        <div class="text-right">
          <span class="font-black text-purple-300 font-mono text-xs block">${fmtMxn(c.monto_total || c.monto)}</span>
          ${c.comision > 0 ? `<span class="text-[9px] text-amber-400 block font-mono">+${fmtMxn(c.comision)} Flex</span>` : ''}
        </div>
      `;

      accionHtml = `
        <button onclick="abrirModalVisorComprobante('${c.id}')" class="p-1.5 rounded-lg bg-slate-800 hover:bg-purple-600 text-slate-300 hover:text-white transition-colors cursor-pointer" title="Ver Comprobante">
          <i class="fa-solid fa-eye text-xs"></i>
        </button>
      `;
    }

    tr.innerHTML = `
      <td class="p-3 text-center text-slate-500 font-mono text-[11px]">${idx + 1}</td>
      <td class="p-3 text-slate-300 font-mono text-xs whitespace-nowrap">${b.fecha || '-'}</td>
      <td class="p-3">
        <span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-500/15 text-blue-300 border border-blue-500/30 font-mono">
          ${b.banco || 'BANCO'}
        </span>
        <div class="text-[10px] text-slate-500 mt-0.5 truncate">${b.empresa || ''}</div>
      </td>
      <td class="p-3 max-w-[280px]">
        <div class="font-semibold text-slate-100 truncate" title="${b.concepto || ''}">${b.concepto || '-'}</div>
        ${b.referencia ? `<div class="text-[10px] font-mono text-slate-400 truncate" title="${b.referencia}">Ref: ${b.referencia}</div>` : ''}
      </td>
      <td class="p-3 text-right font-black text-rose-400 font-mono text-xs whitespace-nowrap">
        ${fmtMxn(Math.abs(b.cargo || 0))}
      </td>
      <td class="p-3 text-center whitespace-nowrap">
        ${badgeEstadoHtml}
      </td>
      <td class="p-3">
        ${compColProveedor}
      </td>
      <td class="p-3">
        ${compColArchivo}
      </td>
      <td class="p-3">
        ${compColMonto}
      </td>
      <td class="p-3 text-center">
        ${accionHtml}
      </td>
    `;

    tbody.appendChild(tr);
  });
}

// ── VISTA 2: BANDEJA DE COMPROBANTES WHATSAPP ────────────────────────────
function renderGastosComprobantes() {
  if (!gastosDataGlobal) return;
  const tbody = document.getElementById('tbody-gastos-comprobantes');
  const lblCount = document.getElementById('lbl-gastos-comprobantes-count');
  if (!tbody) return;

  const query = normalizarTexto(document.getElementById('search-gastos-comprobantes')?.value || '');
  let items = gastosDataGlobal.comprobantes || [];

  if (query) {
    items = items.filter(c => {
      const txt = `${c.proveedor || ''} ${c.nota_whatsapp || ''} ${c.clave_rastreo || ''} ${c.concepto || ''} ${c.archivo_nombre || ''}`;
      return normalizarTexto(txt).includes(query);
    });
  }

  if (lblCount) lblCount.innerText = `${items.length} comprobantes`;
  tbody.innerHTML = '';

  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="12" class="p-8 text-center text-slate-500">No hay comprobantes registrados. Haz clic en "Subir Comprobante" para agregar el primero.</td></tr>`;
    return;
  }

  items.forEach((c, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/40 transition-colors';

    let badgeEstatus = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300">Pendiente</span>`;
    if (c.conciliado) {
      badgeEstatus = `<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Conciliado</span>`;
    }

    tr.innerHTML = `
      <td class="p-3 text-center text-slate-500 font-mono text-[11px]">${idx + 1}</td>
      <td class="p-3 font-mono text-xs whitespace-nowrap text-slate-300">${c.fecha || '-'}</td>
      <td class="p-3 text-xs text-slate-300 truncate max-w-[140px]">${c.empresa || '-'}</td>
      <td class="p-3">
        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
          <i class="fa-brands fa-whatsapp text-[10px]"></i>
          ${c.nota_whatsapp || '—'}
        </span>
      </td>
      <td class="p-3 font-bold text-white">${c.proveedor || '-'}</td>
      <td class="p-3 font-mono text-xs text-blue-300">${c.banco || '-'}</td>
      <td class="p-3 font-mono text-[11px] text-purple-300 truncate max-w-[160px]" title="${c.clave_rastreo || ''}">
        ${c.clave_rastreo || '—'}
      </td>
      <td class="p-3 text-right font-mono text-slate-200">${fmtMxn(c.monto)}</td>
      <td class="p-3 text-right font-mono text-amber-400">${c.comision > 0 ? fmtMxn(c.comision) : '$0.00'}</td>
      <td class="p-3 text-right font-mono font-black text-emerald-400">${fmtMxn(c.monto_total || (c.monto + (c.comision || 0)))}</td>
      <td class="p-3 text-center">${badgeEstatus}</td>
      <td class="p-3 text-center">
        <button onclick="abrirModalVisorComprobante('${c.id}')" class="px-2.5 py-1 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition-all shadow cursor-pointer" title="Ver Comprobante">
          <i class="fa-solid fa-eye"></i>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ── VISTA 3: MOVIMIENTOS DE ESTADO DE CUENTA ─────────────────────────────
function renderGastosMovimientos() {
  if (!gastosDataGlobal) return;
  const tbody = document.getElementById('tbody-gastos-movimientos');
  const lblCount = document.getElementById('lbl-gastos-movimientos-count');
  if (!tbody) return;

  const query = normalizarTexto(document.getElementById('search-gastos-movimientos')?.value || '');
  let items = gastosDataGlobal.movimientos_banco || [];

  if (query) {
    items = items.filter(m => {
      const txt = `${m.concepto || ''} ${m.referencia || ''} ${m.banco || ''} ${m.empresa || ''}`;
      return normalizarTexto(txt).includes(query);
    });
  }

  if (lblCount) lblCount.innerText = `${items.length} movimientos`;
  tbody.innerHTML = '';

  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="p-8 text-center text-slate-500">No hay movimientos bancarios cargados. Haz clic en "Cargar Movimientos Banco" para subir tu estado de cuenta.</td></tr>`;
    return;
  }

  items.forEach((m, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/40 transition-colors';

    let badgeEstatus = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-300">🔴 Sin Comprobante</span>`;
    let accionHtml = `<button onclick="abrirModalConciliarManual('${m.id}')" class="px-2.5 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-bold transition-all cursor-pointer"><i class="fa-solid fa-link mr-1"></i> Conciliar</button>`;

    if (m.conciliado) {
      badgeEstatus = `<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">🟢 Conciliado</span>`;
      accionHtml = `<span class="text-xs text-emerald-400 font-bold">✓ Vinculado</span>`;
    }

    tr.innerHTML = `
      <td class="p-3 text-center text-slate-500 font-mono text-[11px]">${idx + 1}</td>
      <td class="p-3 font-mono text-xs whitespace-nowrap text-slate-300">${m.fecha || '-'}</td>
      <td class="p-3 text-xs text-slate-300 truncate max-w-[140px]">${m.empresa || '-'}</td>
      <td class="p-3">
        <span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-500/20 text-blue-300 font-mono">
          ${m.banco || '-'}
        </span>
      </td>
      <td class="p-3 font-medium text-white max-w-[260px] truncate" title="${m.concepto || ''}">${m.concepto || '-'}</td>
      <td class="p-3 font-mono text-[11px] text-slate-400 truncate max-w-[160px]" title="${m.referencia || ''}">${m.referencia || '—'}</td>
      <td class="p-3 text-right font-mono font-black text-rose-400">${fmtMxn(Math.abs(m.cargo || 0))}</td>
      <td class="p-3 text-right font-mono text-slate-400">${m.saldo ? fmtMxn(m.saldo) : '—'}</td>
      <td class="p-3 text-center">${badgeEstatus}</td>
      <td class="p-3 text-center">${accionHtml}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── VISTA 4: RESUMEN POR PROVEEDOR ───────────────────────────────────────
function renderGastosProveedores() {
  if (!gastosDataGlobal) return;
  const tbody = document.getElementById('tbody-gastos-proveedores');
  const lblCount = document.getElementById('lbl-gastos-proveedores-count');
  if (!tbody) return;

  const comps = gastosDataGlobal.comprobantes || [];
  const conciliados = gastosDataGlobal.conciliados || [];

  // Agrupar por proveedor
  const provMap = {};
  comps.forEach(c => {
    const prov = (c.proveedor || 'Desconocido').toUpperCase().trim();
    if (!provMap[prov]) {
      provMap[prov] = {
        proveedor: prov,
        empresa: c.empresa,
        comprobantes_count: 0,
        total_comprobado: 0,
        monto_conciliado: 0
      };
    }
    provMap[prov].comprobantes_count += 1;
    provMap[prov].total_comprobado += (c.monto_total || c.monto || 0);
  });

  conciliados.forEach(it => {
    if (it.estado_conciliacion === 'CONCILIADO' && it.comprobante) {
      const prov = (it.comprobante.proveedor || 'Desconocido').toUpperCase().trim();
      if (provMap[prov]) {
        provMap[prov].monto_conciliado += (it.comprobante.monto_total || it.comprobante.monto || 0);
      }
    }
  });

  const list = Object.values(provMap).sort((a, b) => b.total_comprobado - a.total_comprobado);

  if (lblCount) lblCount.innerText = `${list.length} proveedores`;
  tbody.innerHTML = '';

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="p-8 text-center text-slate-500">No hay proveedores registrados.</td></tr>`;
    return;
  }

  list.forEach((p, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/40 transition-colors';

    const saldoPend = Math.max(0, p.total_comprobado - p.monto_conciliado);
    const pct = p.total_comprobado > 0 ? Math.round((p.monto_conciliado / p.total_comprobado) * 100) : 0;

    let badgeGen = `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300">🟡 En Proceso</span>`;
    if (pct >= 99) {
      badgeGen = `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-black bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">🟢 Al Corriente</span>`;
    }

    tr.innerHTML = `
      <td class="p-3 text-center text-slate-500 font-mono text-[11px]">${idx + 1}</td>
      <td class="p-3 font-bold text-white flex items-center gap-2">
        <div class="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-300 flex items-center justify-center text-xs font-black">
          ${p.proveedor.substring(0, 2)}
        </div>
        <span>${p.proveedor}</span>
      </td>
      <td class="p-3 text-xs text-slate-300">${p.empresa || '-'}</td>
      <td class="p-3 text-center font-bold text-purple-300 font-mono">${p.comprobantes_count}</td>
      <td class="p-3 text-right font-mono font-black text-slate-100">${fmtMxn(p.total_comprobado)}</td>
      <td class="p-3 text-right font-mono font-black text-emerald-400">${fmtMxn(p.monto_conciliado)}</td>
      <td class="p-3 text-right font-mono font-bold text-amber-400">${fmtMxn(saldoPend)}</td>
      <td class="p-3 text-center">
        <span class="px-2 py-0.5 rounded-full text-xs font-black ${pct >= 99 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-300'}">${pct}%</span>
      </td>
      <td class="p-3 text-center">${badgeGen}</td>
    `;

    tbody.appendChild(tr);
  });
}

// ── ACCIONES Y MODALES: SUBIR COMPROBANTE ────────────────────────────────
function abrirModalSubirComprobante() {
  const modal = document.getElementById('modal-subir-comprobante-gasto');
  if (!modal) return;
  const emp = document.getElementById('global-empresa')?.value;
  if (emp && emp !== 'TODAS (Consolidado)') {
    const selEmp = document.getElementById('comp-empresa');
    if (selEmp) selEmp.value = emp;
  }
  // Set default today date
  const fechaInput = document.getElementById('comp-fecha');
  if (fechaInput && !fechaInput.value) {
    fechaInput.value = new Date().toISOString().split('T')[0];
  }
  modal.classList.remove('hidden');
}

function cerrarModalSubirComprobante() {
  const modal = document.getElementById('modal-subir-comprobante-gasto');
  if (modal) modal.classList.add('hidden');
  currentComprobanteFile = null;
  const fileInput = document.getElementById('file-comprobante-input');
  if (fileInput) fileInput.value = '';
  const icon = document.getElementById('dropzone-icon');
  const txtMain = document.getElementById('dropzone-text-main');
  if (icon) icon.className = 'fa-solid fa-cloud-arrow-up text-2xl text-slate-400 mb-2 block';
  if (txtMain) txtMain.innerText = 'Haz clic o arrastra aquí tu comprobante de WhatsApp / PDF / SPEI';

  const notaWhatsapp = document.getElementById('comp-nota-whatsapp');
  if (notaWhatsapp) notaWhatsapp.value = '';
  const proveedor = document.getElementById('comp-proveedor');
  if (proveedor) proveedor.value = '';
  const monto = document.getElementById('comp-monto');
  if (monto) monto.value = '';
  const comision = document.getElementById('comp-comision');
  if (comision) comision.value = '';
  const rastreo = document.getElementById('comp-rastreo');
  if (rastreo) rastreo.value = '';
}

function onComprobanteFileSelected(input) {
  if (input.files && input.files[0]) {
    currentComprobanteFile = input.files[0];
    const icon = document.getElementById('dropzone-icon');
    const txtMain = document.getElementById('dropzone-text-main');
    if (icon) icon.className = 'fa-solid fa-file-circle-check text-2xl text-emerald-400 mb-2 block';
    if (txtMain) txtMain.innerText = `Archivo seleccionado: ${currentComprobanteFile.name} (${(currentComprobanteFile.size / 1024).toFixed(1)} KB)`;
  }
}

async function subirComprobanteGasto() {
  const notaWhatsapp = document.getElementById('comp-nota-whatsapp')?.value || '';
  const empresa = document.getElementById('comp-empresa')?.value || 'BALDOMERO MEDINA GARZA';
  const proveedor = document.getElementById('comp-proveedor')?.value || '';
  const banco = document.getElementById('comp-banco')?.value || 'BBVA';
  const monto = parseFloat(document.getElementById('comp-monto')?.value || '0');
  const comision = parseFloat(document.getElementById('comp-comision')?.value || '0');
  const fecha = document.getElementById('comp-fecha')?.value || '';
  const rastreo = document.getElementById('comp-rastreo')?.value || '';

  const formData = new FormData();
  if (currentComprobanteFile) {
    formData.append('file', currentComprobanteFile);
  }
  formData.append('nota_whatsapp', notaWhatsapp);
  formData.append('empresa', empresa);
  formData.append('proveedor', proveedor);
  formData.append('banco', banco);
  formData.append('monto', monto);
  formData.append('comision', comision);
  formData.append('fecha', fecha);
  formData.append('clave_rastreo', rastreo);

  showLoading('Guardando Comprobante...', 'Extrayendo metadatos y conciliando automáticamente...');

  try {
    const resp = await fetch('/api/gastos/comprobante/upload', {
      method: 'POST',
      body: formData
    });
    const data = await resp.json();

    if (data.success || data.status === 'success') {
      cerrarModalSubirComprobante();
      await loadGastosConciliacion();
      hideLoading('¡Comprobante Guardado!', data.message || 'Comprobante procesado y conciliado con éxito');
    } else {
      hideLoading('Error al subir', data.error || data.message || 'No se pudo guardar el comprobante');
    }
  } catch (err) {
    console.error('Error al subir comprobante:', err);
    hideLoading('Error', 'Fallo al comunicarse con el servidor');
  }
}

// ── ACCIONES Y MODALES: ESTADO DE CUENTA BANCARIO ────────────────────────
function abrirModalCargarEstadoCuenta() {
  const modal = document.getElementById('modal-cargar-estado-cuenta');
  if (!modal) return;
  const emp = document.getElementById('global-empresa')?.value;
  if (emp && emp !== 'TODAS (Consolidado)') {
    const selEmp = document.getElementById('banco-upload-empresa');
    if (selEmp) selEmp.value = emp;
  }
  modal.classList.remove('hidden');
}

function cerrarModalCargarEstadoCuenta() {
  const modal = document.getElementById('modal-cargar-estado-cuenta');
  if (modal) modal.classList.add('hidden');
  currentBancoFile = null;
  const fileInput = document.getElementById('file-banco-input');
  if (fileInput) fileInput.value = '';
  const txt = document.getElementById('dropzone-banco-text');
  if (txt) txt.innerText = 'Arrastra aquí el estado de cuenta en Excel / CSV';
  const raw = document.getElementById('banco-raw-text');
  if (raw) raw.value = '';
}

function onBancoFileSelected(input) {
  if (input.files && input.files[0]) {
    currentBancoFile = input.files[0];
    const txt = document.getElementById('dropzone-banco-text');
    if (txt) txt.innerText = `Archivo seleccionado: ${currentBancoFile.name}`;
  }
}

async function subirEstadoCuentaBancario() {
  const empresa = document.getElementById('banco-upload-empresa')?.value || 'BALDOMERO MEDINA GARZA';
  const banco = document.getElementById('banco-upload-banco')?.value || 'BBVA';
  const rawText = document.getElementById('banco-raw-text')?.value || '';

  const formData = new FormData();
  formData.append('empresa', empresa);
  formData.append('banco', banco);

  if (currentBancoFile) {
    formData.append('file', currentBancoFile);
  }
  if (rawText) {
    formData.append('raw_text', rawText);
  }

  showLoading('Procesando Estado de Cuenta...', 'Importando cargos bancarios y ejecutando conciliación...');

  try {
    const resp = await fetch('/api/gastos/banco/upload', {
      method: 'POST',
      body: formData
    });
    const data = await resp.json();

    if (data.success || data.status === 'success') {
      cerrarModalCargarEstadoCuenta();
      await loadGastosConciliacion();
      const cant = data.conteo || data.movimientos_creados || (data.movimientos ? data.movimientos.length : 0);
      hideLoading('¡Estado de Cuenta Cargado!', `${cant} movimientos importados`);
    } else {
      hideLoading('Error al cargar', data.error || data.message || 'No se pudo procesar el estado de cuenta');
    }
  } catch (err) {
    console.error('Error al subir estado de cuenta:', err);
    hideLoading('Error', 'Fallo al comunicarse con el servidor');
  }
}

// ── ACCIONES Y MODALES: VISOR DE COMPROBANTE ─────────────────────────────
function abrirModalVisorComprobante(compId) {
  if (!gastosDataGlobal || !gastosDataGlobal.comprobantes) return;
  const comp = gastosDataGlobal.comprobantes.find(c => c.id === compId);
  if (!comp) return;

  const modal = document.getElementById('modal-visor-comprobante');
  if (!modal) return;

  // Llenar datos
  const elEstado = document.getElementById('visor-badge-estado');
  const elBanco = document.getElementById('visor-badge-banco');
  const elEmp = document.getElementById('visor-badge-empresa');
  const elProvTit = document.getElementById('visor-proveedor-titulo');
  const elNotaWa = document.getElementById('visor-nota-whatsapp');
  const elArchNom = document.getElementById('visor-archivo-nombre');
  const elMontoNeto = document.getElementById('visor-monto-neto');
  const elComision = document.getElementById('visor-comision');
  const elTotal = document.getElementById('visor-total-cargo');
  const elFecha = document.getElementById('visor-fecha');
  const elRastreo = document.getElementById('visor-rastreo');
  const elConcepto = document.getElementById('visor-concepto');
  const elPreviewCont = document.getElementById('visor-preview-container');
  const elBtnDownload = document.getElementById('visor-btn-descargar');
  const elBtnNewTab = document.getElementById('visor-btn-abrir-nueva-pestana');

  if (elEstado) {
    elEstado.className = comp.conciliado 
      ? 'px-2.5 py-0.5 rounded-full text-[10px] font-black bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
      : 'px-2.5 py-0.5 rounded-full text-[10px] font-black bg-amber-500/20 text-amber-300 border border-amber-500/30';
    elEstado.innerText = comp.conciliado ? '🟢 CONCILIADO' : '🟡 PENDIENTE BANCO';
  }
  if (elBanco) elBanco.innerText = comp.banco || 'BANCO';
  if (elEmp) elEmp.innerText = comp.empresa || 'CHALLENGER';
  if (elProvTit) elProvTit.innerText = comp.proveedor || 'PROVEEDOR';
  if (elNotaWa) elNotaWa.innerText = comp.nota_whatsapp || '—';
  if (elArchNom) elArchNom.innerText = comp.archivo_nombre || 'comprobante.pdf';
  if (elMontoNeto) elMontoNeto.innerText = fmtMxn(comp.monto);
  if (elComision) elComision.innerText = fmtMxn(comp.comision || 0);
  if (elTotal) elTotal.innerText = fmtMxn(comp.monto_total || (comp.monto + (comp.comision || 0)));
  if (elFecha) elFecha.innerText = comp.fecha || '-';
  if (elRastreo) elRastreo.innerText = comp.clave_rastreo || 'No especificada';
  if (elConcepto) elConcepto.innerText = comp.concepto || '-';

  // Preview
  const fileUrl = `/api/gastos/comprobante/archivo/${comp.id}`;
  if (elBtnDownload) elBtnDownload.href = fileUrl;
  if (elBtnNewTab) elBtnNewTab.href = fileUrl;

  if (elPreviewCont) {
    const ext = (comp.archivo_nombre || '').toLowerCase();
    if (ext.endsWith('.png') || ext.endsWith('.jpg') || ext.endsWith('.jpeg')) {
      elPreviewCont.innerHTML = `<img src="${fileUrl}" alt="Comprobante" class="max-h-[500px] max-w-full rounded-xl object-contain shadow-lg">`;
    } else {
      elPreviewCont.innerHTML = `<iframe src="${fileUrl}" class="w-full h-[520px] rounded-xl border border-slate-800 bg-white"></iframe>`;
    }
  }

  modal.classList.remove('hidden');
}

function cerrarModalVisorComprobante() {
  const modal = document.getElementById('modal-visor-comprobante');
  if (modal) modal.classList.add('hidden');
  const elPreviewCont = document.getElementById('visor-preview-container');
  if (elPreviewCont) elPreviewCont.innerHTML = '';
}

// ── ACCIONES Y MODALES: CONCILIAR MANUAL ─────────────────────────────────
function abrirModalConciliarManual(movId) {
  if (!gastosDataGlobal || !gastosDataGlobal.movimientos_banco) return;
  const mov = gastosDataGlobal.movimientos_banco.find(m => m.id === movId);
  if (!mov) return;

  currentGastosMovimientoManual = mov;
  const modal = document.getElementById('modal-conciliar-manual');
  if (!modal) return;

  // Llenar datos de banco
  const elBnc = document.getElementById('cman-banco-nombre');
  const elFec = document.getElementById('cman-banco-fecha');
  const elMon = document.getElementById('cman-banco-monto');
  const elRef = document.getElementById('cman-banco-referencia');
  const elCon = document.getElementById('cman-banco-concepto');
  const selectComp = document.getElementById('cman-select-comprobante');

  if (elBnc) elBnc.innerText = mov.banco || '-';
  if (elFec) elFec.innerText = mov.fecha || '-';
  if (elMon) elMon.innerText = fmtMxn(Math.abs(mov.cargo || 0));
  if (elRef) elRef.innerText = mov.referencia || '—';
  if (elCon) elCon.innerText = mov.concepto || '-';

  if (selectComp) {
    selectComp.innerHTML = '<option value="">-- Selecciona un comprobante de WhatsApp --</option>';
    const comps = (gastosDataGlobal.comprobantes || []).filter(c => !c.conciliado || c.id === mov.comprobante_id);
    comps.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      const totalC = fmtMxn(c.monto_total || c.monto);
      opt.innerText = `[${c.fecha}] ${c.proveedor} | Nota WhatsApp: "${c.nota_whatsapp || ''}" | Monto: ${totalC} (Ref: ${c.clave_rastreo || 'S/R'})`;
      selectComp.appendChild(opt);
    });
  }

  modal.classList.remove('hidden');
}

function cerrarModalConciliarManual() {
  const modal = document.getElementById('modal-conciliar-manual');
  if (modal) modal.classList.add('hidden');
  currentGastosMovimientoManual = null;
}

async function guardarConciliacionManual() {
  if (!currentGastosMovimientoManual) return;
  const selectComp = document.getElementById('cman-select-comprobante');
  const compId = selectComp?.value;
  const nota = document.getElementById('cman-nota')?.value || '';

  if (!compId) {
    alert('Por favor selecciona un comprobante para vincular.');
    return;
  }

  showLoading('Vinculando Conciliación...', 'Guardando cruce manual de banco y comprobante...');

  try {
    const resp = await fetch('/api/gastos/conciliar/vincular', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        movimiento_id: currentGastosMovimientoManual.id,
        comprobante_id: compId,
        nota: nota
      })
    });
    const data = await resp.json();

    if (data.success || data.status === 'success') {
      cerrarModalConciliarManual();
      await loadGastosConciliacion();
      hideLoading('¡Conciliado!', 'El movimiento ha quedado respaldado con el comprobante');
    } else {
      hideLoading('Error', data.error || data.message || 'No se pudo completar la conciliación');
    }
  } catch (err) {
    console.error('Error al vincular conciliación:', err);
    hideLoading('Error', 'Fallo al comunicarse con el servidor');
  }
}

// ── RE-EJECUTAR MOTOR & EXPORTAR EXCEL ───────────────────────────────────
async function ejecutarConciliacionEngineUI() {
  showLoading('Conciliando Inteligente...', 'Re-evaluando claves de rastreo, fechas y montos...');
  await loadGastosConciliacion(true);
}

function exportarGastosExcel() {
  const empresa = document.getElementById('global-empresa')?.value || 'TODAS (Consolidado)';
  window.open(`/api/gastos/exportar/excel?empresa=${encodeURIComponent(empresa)}`, '_blank');
}

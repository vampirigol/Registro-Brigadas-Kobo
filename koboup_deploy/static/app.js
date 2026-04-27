(function () {
  /* Prefijo para API bajo /koboup/ (p. ej. /koboup sin barra final hacía fallar api/files → /api/files) */
  var kobuPathPrefix = (function () {
    var p = location.pathname;
    if (p.endsWith('/')) return p;
    var i = p.lastIndexOf('/');
    if (i <= 0) return p + '/';
    var last = p.substring(i + 1);
    if (last.indexOf('.') > 0) {
      return p.substring(0, i + 1);
    }
    return p + '/';
  }());
  function u(rel) {
    if (rel == null) rel = '';
    rel = String(rel).replace(/^\/+/, '');
    if (!kobuPathPrefix.endsWith('/')) {
      return kobuPathPrefix + '/' + rel;
    }
    return kobuPathPrefix + rel;
  }
  if (typeof window !== 'undefined') {
    window.kobuUrl = u;
  }

  /* ═══════════════ ELEMENTOS DOM ═══════════════ */

  // Secciones principales
  var sectionWork = document.getElementById('sectionWork');
  var sectionRefs = document.getElementById('sectionRefs');
  var sectionRanking = document.getElementById('sectionRanking');
  var sectionAudit = document.getElementById('sectionAudit');
  var sectionSearch = document.getElementById('sectionSearch');
  var sectionKpi = document.getElementById('sectionKpi');
  var searchValidatedInput = document.getElementById('searchValidatedInput');
  var searchValidatedStatus = document.getElementById('searchValidatedStatus');
  var searchValidatedScope = document.getElementById('searchValidatedScope');
  var searchValidatedLimit = document.getElementById('searchValidatedLimit');
  var searchValidatedPerFile = document.getElementById('searchValidatedPerFile');
  var btnSearchValidated = document.getElementById('btnSearchValidated');
  var btnSearchValidatedClear = document.getElementById('btnSearchValidatedClear');
  var searchResultsTable = document.getElementById('searchResultsTable');
  var searchResultsBody = document.getElementById('searchResultsBody');
  var searchBusy = false;
  var navBtns = document.querySelectorAll('.main-nav-btn');

  // Archivos de trabajo
  var fileInput = document.getElementById('fileInput');
  var uploadZone = document.getElementById('uploadZone');
  var btnUpload = document.getElementById('btnUpload');
  var inputName = document.getElementById('inputName');
  var inputNotes = document.getElementById('inputNotes');
  var uploadMsg = document.getElementById('uploadMsg');
  var filesList = document.getElementById('filesList');
  var btnRefresh = document.getElementById('btnRefresh');
  var kpiPatients = document.getElementById('kpiPatients');
  var kpiPatientsDetail = document.getElementById('kpiPatientsDetail');


  // Modal validar (multi-paso)
  var modalOverlay = document.getElementById('modalOverlay');
  var modalFilename = document.getElementById('modalFilename');
  var pendingValidateId = null;

  // Paso 1
  var valStep1 = document.getElementById('valStep1');
  var valOptUpload = document.getElementById('valOptUpload');
  var valOptSelect = document.getElementById('valOptSelect');
  var modalCancel = document.getElementById('modalCancel');

  // Paso 2A: subir
  var valStep2Upload = document.getElementById('valStep2Upload');
  var valUploadZone = document.getElementById('valUploadZone');
  var valFileInput = document.getElementById('valFileInput');
  var valUploadName = document.getElementById('valUploadName');
  var valUploadNotes = document.getElementById('valUploadNotes');
  var valUploadMsg = document.getElementById('valUploadMsg');
  var valUploadConfirm = document.getElementById('valUploadConfirm');
  var valUploadCancel = document.getElementById('valUploadCancel');
  var valBackFromUpload = document.getElementById('valBackFromUpload');
  var valUploadReplacingName = document.getElementById('valUploadReplacingName');
  var valSelectedFile = null;

  // Paso 2B: seleccionar existente
  var valStep2Select = document.getElementById('valStep2Select');
  var valSelectFile = document.getElementById('valSelectFile');
  var valSelectName = document.getElementById('valSelectName');
  var valSelectMsg = document.getElementById('valSelectMsg');
  var valSelectConfirm = document.getElementById('valSelectConfirm');
  var valSelectCancel = document.getElementById('valSelectCancel');
  var valBackFromSelect = document.getElementById('valBackFromSelect');
  var valSelectReplacingName = document.getElementById('valSelectReplacingName');

  // Modal descargar
  var dlModalOverlay = document.getElementById('dlModalOverlay');
  var dlModalFilename = document.getElementById('dlModalFilename');
  var dlModalName = document.getElementById('dlModalName');
  var dlModalCancel = document.getElementById('dlModalCancel');
  var dlModalConfirm = document.getElementById('dlModalConfirm');
  var pendingDownload = null;

  // Modal editar archivo
  var editModalOverlay = document.getElementById('editModalOverlay');
  var editModalFilename = document.getElementById('editModalFilename');
  var editModalOriginalName = document.getElementById('editModalOriginalName');
  var editModalUploadedBy = document.getElementById('editModalUploadedBy');
  var editModalNotes = document.getElementById('editModalNotes');
  var editModalMsg = document.getElementById('editModalMsg');
  var editModalCancel = document.getElementById('editModalCancel');
  var editModalConfirm = document.getElementById('editModalConfirm');
  var pendingEditFile = null;

  // Editor de hoja (tabla)
  var sheetOverlay = document.getElementById('sheetEditorOverlay');
  var sheetTitle = document.getElementById('sheetEditorTitle');
  var sheetHint = document.getElementById('sheetEditorHint');
  var sheetStatus = document.getElementById('sheetEditorStatus');
  var sheetTableScroll = document.getElementById('sheetTableScroll');
  var sheetTableWrap = document.getElementById('sheetTableWrap');
  var sheetColumnsCheck = document.getElementById('sheetColumnsCheck');
  var sheetOriginalName = document.getElementById('sheetOriginalName');
  var sheetUploadedBy = document.getElementById('sheetUploadedBy');
  var sheetNotes = document.getElementById('sheetNotes');
  var sheetAddRow = document.getElementById('sheetAddRow');
  var sheetAddCol = document.getElementById('sheetAddCol');
  var sheetColRemove = document.getElementById('sheetColRemove');
  var sheetColRemoveGo = document.getElementById('sheetColRemoveGo');
  var sheetApplySuggestions = document.getElementById('sheetApplySuggestions');
  var sheetToggleColumnMode = document.getElementById('sheetToggleColumnMode');
  var sheetOpenGuide = document.getElementById('sheetOpenGuide');
  var sheetOpenTreatmentSuggest = document.getElementById('sheetOpenTreatmentSuggest');
  var sheetTreatmentPanel = document.getElementById('sheetTreatmentPanel');
  var sheetTreatmentList = document.getElementById('sheetTreatmentList');
  var sheetTreatmentRowInfo = document.getElementById('sheetTreatmentRowInfo');
  var sheetTreatmentCohortInfo = document.getElementById('sheetTreatmentCohortInfo');
  var sheetSubmitKobo = document.getElementById('sheetSubmitKobo');
  var sheetMarkEditedValidated = document.getElementById('sheetMarkEditedValidated');
  var sheetSave = document.getElementById('sheetSave');
  var sheetClose = document.getElementById('sheetClose');
  var sheetOpenMetaOnly = document.getElementById('sheetOpenMetaOnly');
  var sheetState = null; /* { file, columns, rows } */
  var sheetDirty = false;
  var sheetSelection = null; /* {r1,c1,r2,c2} */
  var sheetSelecting = false;
  var sheetLockHeartbeat = null;
  var sheetUnlockSent = false;
  var sheetContextMenuEl = null;
  var sheetContextTarget = null; /* {ci:number|null, ri:number|null} */
  var SHEET_COL_MODE_KEY = 'koboup_sheet_col_mode_v1';
  var sheetShowAllColumns = (localStorage.getItem(SHEET_COL_MODE_KEY) || 'relevant') === 'all';
  var koboSubmitModalOverlay = document.getElementById('koboSubmitModalOverlay');
  var koboSubmitModalFilename = document.getElementById('koboSubmitModalFilename');
  var koboSubmitRows = document.getElementById('koboSubmitRows');
  var koboSubmitSelectAll = document.getElementById('koboSubmitSelectAll');
  var koboSubmitPassword = document.getElementById('koboSubmitPassword');
  var koboSubmitMsg = document.getElementById('koboSubmitMsg');
  var koboSubmitCancel = document.getElementById('koboSubmitCancel');
  var koboSubmitConfirm = document.getElementById('koboSubmitConfirm');
  var koboSubmitBusy = false;
  var SHEET_GUIDE_SEEN_KEY = 'koboup_sheet_guide_v1_seen_v1';
  var sheetGuide = {
    active: false,
    stepIndex: 0,
    steps: [],
    targetEl: null,
    overlay: null,
    card: null,
    titleEl: null,
    textEl: null,
    counterEl: null,
    prevBtn: null,
    nextBtn: null,
    closeBtn: null
  };

  // Referencias PDF
  var refFileInput = document.getElementById('refFileInput');
  var refUploadZone = document.getElementById('refUploadZone');
  var btnRefUpload = document.getElementById('btnRefUpload');
  var refInputName = document.getElementById('refInputName');
  var refInputLocation = document.getElementById('refInputLocation');
  var refInputNotes = document.getElementById('refInputNotes');
  var refUploadMsg = document.getElementById('refUploadMsg');
  var refsList = document.getElementById('refsList');
  var btnRefRefresh = document.getElementById('btnRefRefresh');
  var refLocationTabs = document.getElementById('refLocationTabs');
  var locationSuggestions = document.getElementById('locationSuggestions');

  // Selector de archivo a reemplazar
  var replacesRow = document.getElementById('replacesRow');
  var selectReplaces = document.getElementById('selectReplaces');

  var selectedFiles = [];
  // selectedRefFiles se declara más abajo en la sección de Referencias
  var currentFilter = '';
  var currentRefLocation = '';
  var filesCache = [];
  var refsCache = [];
  var koboLogsTableBody = document.getElementById('koboLogsTableBody');
  var btnKoboLogsRefresh = document.getElementById('btnKoboLogsRefresh');

  var savedName = localStorage.getItem('koboup_name') || '';
  if (savedName && inputName) inputName.value = savedName;
  if (savedName && refInputName) refInputName.value = savedName;

  /* ═══════════════ UTILIDADES ═══════════════ */

  function setMsg(el, text, type) {
    if (!el) return;
    el.textContent = text || '';
    el.className = 'toast-msg ' + (type || '');
  }

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function escAttr(s) {
    s = s == null ? '' : String(s);
    return s
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;');
  }

  function ensureSheetGuideUI() {
    if (sheetGuide.overlay && sheetGuide.card) return;
    var overlay = document.createElement('div');
    overlay.className = 'sheet-tour-overlay';
    overlay.id = 'sheetTourOverlay';

    var card = document.createElement('div');
    card.className = 'sheet-tour-card';
    card.id = 'sheetTourCard';
    card.innerHTML = ''
      + '<div class="sheet-tour-title" id="sheetTourTitle"></div>'
      + '<div class="sheet-tour-text" id="sheetTourText"></div>'
      + '<div class="sheet-tour-foot">'
      + '  <span class="sheet-tour-counter" id="sheetTourCounter"></span>'
      + '  <div class="sheet-tour-actions">'
      + '    <button type="button" class="btn btn-ghost" id="sheetTourPrev">Anterior</button>'
      + '    <button type="button" class="btn btn-outline" id="sheetTourClose">Cerrar guía</button>'
      + '    <button type="button" class="btn btn-primary" id="sheetTourNext">Siguiente</button>'
      + '  </div>'
      + '</div>';
    document.body.appendChild(overlay);
    document.body.appendChild(card);

    sheetGuide.overlay = overlay;
    sheetGuide.card = card;
    sheetGuide.titleEl = card.querySelector('#sheetTourTitle');
    sheetGuide.textEl = card.querySelector('#sheetTourText');
    sheetGuide.counterEl = card.querySelector('#sheetTourCounter');
    sheetGuide.prevBtn = card.querySelector('#sheetTourPrev');
    sheetGuide.nextBtn = card.querySelector('#sheetTourNext');
    sheetGuide.closeBtn = card.querySelector('#sheetTourClose');

    overlay.addEventListener('click', function () { stopSheetGuide(true); });
    if (sheetGuide.prevBtn) {
      sheetGuide.prevBtn.addEventListener('click', function () {
        if (!sheetGuide.active) return;
        if (sheetGuide.stepIndex <= 0) return;
        sheetGuide.stepIndex -= 1;
        renderSheetGuideStep();
      });
    }
    if (sheetGuide.nextBtn) {
      sheetGuide.nextBtn.addEventListener('click', function () {
        if (!sheetGuide.active) return;
        if (sheetGuide.stepIndex >= sheetGuide.steps.length - 1) {
          stopSheetGuide(true);
          return;
        }
        sheetGuide.stepIndex += 1;
        renderSheetGuideStep();
      });
    }
    if (sheetGuide.closeBtn) {
      sheetGuide.closeBtn.addEventListener('click', function () { stopSheetGuide(true); });
    }
  }

  function clearSheetGuideFocus() {
    if (sheetGuide.targetEl && sheetGuide.targetEl.classList) {
      sheetGuide.targetEl.classList.remove('sheet-tour-focus');
    }
    sheetGuide.targetEl = null;
  }

  function buildSheetGuideSteps() {
    var out = [
      {
        title: 'Paso 1: Revisa qué falta',
        text: 'Este panel te dice en lenguaje simple si el archivo está listo o qué debes corregir antes de guardar.',
        target: function () { return sheetColumnsCheck; }
      },
      {
        title: 'Paso 2: Corrige la tabla',
        text: 'Edita aquí celdas, filas y columnas. Puedes pegar datos como en Excel y ajustar encabezados.',
        target: function () { return sheetTableWrap; }
      },
      {
        title: 'Paso 3: Verifica nombre y nota',
        text: 'Antes de guardar, confirma el nombre visible del archivo y agrega nota si hace falta.',
        target: function () { return sheetOriginalName; }
      },
      {
        title: 'Paso 4: Guarda los cambios',
        text: 'Cuando termines, pulsa "Guardar todo". Esto actualiza el archivo en el servidor y en la base de datos.',
        target: function () { return sheetSave; }
      }
    ];
    if (sheetMarkEditedValidated) {
      out.push({
        title: 'Paso 5 (Opcional): Marca validación final',
        text: 'Si ya revisaste todo, usa "Marcar Editado Validado" para dejar claro que el archivo quedó listo.',
        target: function () { return sheetMarkEditedValidated; }
      });
    }
    return out.filter(function (step) {
      try { return !!(step.target && step.target()); } catch (e) { return false; }
    });
  }

  function renderSheetGuideStep() {
    if (!sheetGuide.active) return;
    if (!sheetGuide.steps || !sheetGuide.steps.length) return;
    var idx = Math.max(0, Math.min(sheetGuide.stepIndex, sheetGuide.steps.length - 1));
    sheetGuide.stepIndex = idx;
    var step = sheetGuide.steps[idx];
    var target = null;
    try { target = step.target ? step.target() : null; } catch (e) { target = null; }

    clearSheetGuideFocus();
    if (target && target.classList) {
      sheetGuide.targetEl = target;
      target.classList.add('sheet-tour-focus');
      if (typeof target.scrollIntoView === 'function') {
        target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
      }
    }

    if (sheetGuide.titleEl) sheetGuide.titleEl.textContent = step.title || '';
    if (sheetGuide.textEl) sheetGuide.textEl.textContent = step.text || '';
    if (sheetGuide.counterEl) sheetGuide.counterEl.textContent = 'Paso ' + (idx + 1) + ' de ' + sheetGuide.steps.length;
    if (sheetGuide.prevBtn) sheetGuide.prevBtn.disabled = idx <= 0;
    if (sheetGuide.nextBtn) sheetGuide.nextBtn.textContent = (idx >= sheetGuide.steps.length - 1) ? 'Finalizar' : 'Siguiente';
  }

  function startSheetGuide() {
    if (!sheetOverlay || sheetOverlay.style.display === 'none') return;
    ensureSheetGuideUI();
    sheetGuide.steps = buildSheetGuideSteps();
    if (!sheetGuide.steps.length) return;
    sheetGuide.stepIndex = 0;
    sheetGuide.active = true;
    if (sheetGuide.overlay) sheetGuide.overlay.style.display = 'block';
    if (sheetGuide.card) sheetGuide.card.style.display = 'block';
    renderSheetGuideStep();
  }

  function stopSheetGuide(markSeen) {
    if (!sheetGuide.active && !sheetGuide.overlay) return;
    clearSheetGuideFocus();
    sheetGuide.active = false;
    if (sheetGuide.overlay) sheetGuide.overlay.style.display = 'none';
    if (sheetGuide.card) sheetGuide.card.style.display = 'none';
    if (markSeen) {
      try { localStorage.setItem(SHEET_GUIDE_SEEN_KEY, '1'); } catch (e) {}
    }
  }

  function isStubXlsName(stored) {
    var n = (stored || '').toLowerCase();
    return n.endsWith('.xls') && !n.endsWith('.xlsx');
  }

  function canOpenSheetEditor(f) {
    if (!f || f.status !== 'validado' || f.file_type === 'pdf') return false;
    if (isStubXlsName(f.stored_name)) return false;
    var n = (f.stored_name || '').toLowerCase();
    return n.endsWith('.xlsx') || n.endsWith('.csv');
  }

  function fmtSize(b) {
    if (!b) return '';
    if (b < 1024) return b + ' B';
    if (b < 1048576) return Math.round(b / 1024) + ' KB';
    return (b / 1048576).toFixed(1) + ' MB';
  }

  function fmtDate(iso) {
    if (!iso) return '';
    try {
      var d = new Date(iso + 'Z');
      return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })
        + ' ' + d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
    } catch (e) { return iso.slice(0, 16).replace('T', ' '); }
  }

  function timeSince(iso) {
    if (!iso) return '';
    try {
      var d = new Date(iso + 'Z');
      var diff = Math.floor((Date.now() - d.getTime()) / 1000);
      if (diff < 60) return 'hace un momento';
      if (diff < 3600) return 'hace ' + Math.floor(diff / 60) + ' min';
      if (diff < 86400) return 'hace ' + Math.floor(diff / 3600) + ' h';
      return 'hace ' + Math.floor(diff / 86400) + ' días';
    } catch (e) { return ''; }
  }

  function getSelectedStatus() {
    var checked = document.querySelector('input[name="uploadStatus"]:checked');
    return checked ? checked.value : 'pendiente';
  }

  function statusLabel(s) {
    if (s === 'por_validar') return 'En validación';
    if (s === 'validado') return 'Validado';
    if (s === 'reemplazado') return 'Reemplazado';
    return 'Pendiente';
  }

  function statusBadgeClass(s) {
    if (s === 'por_validar') return 'badge-review';
    if (s === 'validado') return 'badge-valid';
    if (s === 'reemplazado') return 'badge-superseded';
    return 'badge-pending';
  }

  /* ═══════════════ NAVEGACIÓN PRINCIPAL ═══════════════ */

  function hideAllMainSections() {
    if (sectionWork) sectionWork.style.display = 'none';
    if (sectionRefs) sectionRefs.style.display = 'none';
    if (sectionRanking) sectionRanking.style.display = 'none';
    if (sectionAudit) sectionAudit.style.display = 'none';
    if (sectionSearch) sectionSearch.style.display = 'none';
    if (sectionKpi) sectionKpi.style.display = 'none';
  }

  function openFileSheetFromSearch(fileId) {
    var fid = parseInt(String(fileId), 10);
    if (isNaN(fid) || !sectionWork) return;
    navBtns.forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-section') === 'work');
    });
    hideAllMainSections();
    sectionWork.style.display = '';
    loadFiles().then(function () {
      onEditFileClick(String(fid), true);
    });
  }

  async function runValidatedSearch() {
    if (searchBusy) return;
    if (!searchValidatedInput) return;
    var q = (searchValidatedInput.value || '').trim();
    if (q.length < 2) {
      if (searchValidatedStatus) searchValidatedStatus.textContent = 'Escriba al menos 2 caracteres.';
      return;
    }
    var scope = (searchValidatedScope && searchValidatedScope.value) || 'all';
    var limit = (searchValidatedLimit && searchValidatedLimit.value) || '200';
    var per = (searchValidatedPerFile && searchValidatedPerFile.value) || '25';
    var qs = 'q=' + encodeURIComponent(q)
      + '&scope=' + encodeURIComponent(scope)
      + '&limit=' + encodeURIComponent(limit)
      + '&per_file=' + encodeURIComponent(per);
    searchBusy = true;
    if (searchValidatedStatus) searchValidatedStatus.textContent = 'Buscando…';
    if (searchResultsTable) searchResultsTable.style.display = 'none';
    if (searchResultsBody) searchResultsBody.innerHTML = '';
    try {
      var r = await fetch(u('api/search/validated?' + qs));
      var d = await r.json();
      if (!d.ok) throw new Error((d && d.error) || 'Error en búsqueda');
      if (searchValidatedStatus) {
        var sc = d.files_scanned != null ? d.files_scanned : 0;
        var rc = (d.result_count != null) ? d.result_count : (d.results && d.results.length) || 0;
        var tr = d.truncated ? ' (límite de resultados alcanzado)' : '';
        searchValidatedStatus.textContent = rc + ' coincidencia(s) en ' + sc + ' archivo(s) revisado(s)' + tr + '.';
      }
      var rows = d.results || [];
      if (!rows.length) {
        if (searchResultsBody) {
          searchResultsBody.innerHTML = '<tr><td colspan="6">No se encontraron coincidencias. Pruebe otra palabra o cambie el ámbito.</td></tr>';
        }
        if (searchResultsTable) searchResultsTable.style.display = '';
        return;
      }
      var h = '';
      for (var i = 0; i < rows.length; i += 1) {
        var it = rows[i] || {};
        var fn = esc(String(it.file_name || ''));
        var kind = esc(String(it.match_in || (it.row_index == null ? 'metadato' : 'fila') || '—'));
        var fr = (it.excel_row != null && it.excel_row !== '') ? String(it.excel_row) : '—';
        var coln = esc(String(it.column != null && it.column !== '' ? it.column : '—'));
        var val = it.value != null ? String(it.value) : '';
        var shortVal = val.length > 500 ? (val.slice(0, 500) + '…') : val;
        var op = '<button type="button" class="btn btn-outline btn-sm js-search-open" data-fid="' + it.file_id + '">Abrir hoja</button>';
        h += '<tr><td class="file-name-col">' + fn + '</td><td>' + kind + '</td><td>' + esc(fr) + '</td><td>' + coln
          + '</td><td class="search-match-text">' + esc(shortVal) + '</td><td class="file-actions-col">' + op + '</td></tr>';
      }
      if (searchResultsBody) searchResultsBody.innerHTML = h;
      if (searchResultsTable) searchResultsTable.style.display = '';
      if (searchResultsBody) {
        searchResultsBody.querySelectorAll('.js-search-open').forEach(function (b) {
          b.addEventListener('click', function () { openFileSheetFromSearch(b.getAttribute('data-fid')); });
        });
      }
    } catch (e) {
      if (searchValidatedStatus) searchValidatedStatus.textContent = 'Error: ' + (e && e.message);
    } finally {
      searchBusy = false;
    }
  }

  function clearValidatedSearch() {
    if (searchValidatedInput) searchValidatedInput.value = '';
    if (searchValidatedStatus) searchValidatedStatus.textContent = '';
    if (searchResultsTable) searchResultsTable.style.display = 'none';
    if (searchResultsBody) searchResultsBody.innerHTML = '';
  }

  if (btnSearchValidated) {
    btnSearchValidated.addEventListener('click', function () { runValidatedSearch(); });
  }
  if (btnSearchValidatedClear) {
    btnSearchValidatedClear.addEventListener('click', function () { clearValidatedSearch(); });
  }
  if (searchValidatedInput) {
    searchValidatedInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); runValidatedSearch(); }
    });
  }

  navBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      navBtns.forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      var section = btn.getAttribute('data-section');
      hideAllMainSections();
      if (section === 'refs') {
        if (sectionRefs) sectionRefs.style.display = '';
        loadRefs();
      } else if (section === 'ranking') {
        if (sectionRanking) sectionRanking.style.display = '';
        loadRanking();
      } else if (section === 'audit') {
        if (sectionAudit) sectionAudit.style.display = '';
        loadKoboSubmissionLogs();
      } else if (section === 'search') {
        if (sectionSearch) sectionSearch.style.display = '';
        if (searchValidatedInput) searchValidatedInput.focus();
      } else if (section === 'kpi') {
        if (sectionKpi) sectionKpi.style.display = '';
        if (typeof window.kobuLoadKpis === 'function') {
          window.kobuLoadKpis();
        }
      } else {
        if (sectionWork) sectionWork.style.display = '';
        loadFiles();
      }
    });
  });

  /* ═══════════════ ARCHIVOS DE TRABAJO ═══════════════ */

  function checkUploadReady() {
    var hasFiles = selectedFiles.length > 0;
    var hasName = !!(inputName && inputName.value.trim());
    btnUpload.disabled = !(hasFiles && hasName);
  }

  if (inputName) inputName.addEventListener('input', checkUploadReady);

  function updateReplacesVisibility() {
    var status = getSelectedStatus();
    if (status === 'validado' && selectedFiles.length <= 1) {
      replacesRow.style.display = '';
      populateReplacesSelect();
    } else {
      replacesRow.style.display = 'none';
      selectReplaces.value = '';
    }
  }

  function populateReplacesSelect() {
    var replaceable = filesCache.filter(function (f) {
      return f.status === 'pendiente' || f.status === 'por_validar';
    });
    var html = '<option value="">— Ninguno (detección automática por nombre) —</option>';
    replaceable.forEach(function (f) {
      var label = f.original_name || f.stored_name;
      var extra = '';
      if (f.uploaded_by) extra += ' · ' + f.uploaded_by;
      extra += ' · ' + statusLabel(f.status);
      if (f.created_at) extra += ' · ' + fmtDate(f.created_at);
      html += '<option value="' + f.id + '">' + esc(label) + extra + '</option>';
    });
    selectReplaces.innerHTML = html;
  }

  document.querySelectorAll('input[name="uploadStatus"]').forEach(function (radio) {
    radio.addEventListener('change', updateReplacesVisibility);
  });

  uploadZone.addEventListener('click', function (e) {
    if (e.target.closest('.ref-file-remove')) return;
    fileInput.click();
  });
  uploadZone.addEventListener('dragover', function (e) { e.preventDefault(); uploadZone.classList.add('dragover'); });
  uploadZone.addEventListener('dragleave', function () { uploadZone.classList.remove('dragover'); });
  uploadZone.addEventListener('drop', function (e) {
    e.preventDefault(); uploadZone.classList.remove('dragover');
    var files = e.dataTransfer && e.dataTransfer.files;
    if (files && files.length) addWorkFiles(files);
  });
  fileInput.addEventListener('change', function () {
    if (fileInput.files && fileInput.files.length) addWorkFiles(fileInput.files);
  });

  function addWorkFiles(fileList) {
    var valid = [];
    for (var i = 0; i < fileList.length; i++) {
      if (/\.(xlsx|xls|csv|pdf)$/i.test(fileList[i].name)) valid.push(fileList[i]);
    }
    if (valid.length === 0) return;
    var existingNames = selectedFiles.map(function (f) { return f.name; });
    valid.forEach(function (f) {
      if (existingNames.indexOf(f.name) === -1) selectedFiles.push(f);
    });
    updateWorkDropzoneUI();
    checkUploadReady();
    updateReplacesVisibility();
    setMsg(uploadMsg, '');
  }

  function updateWorkDropzoneUI() {
    if (selectedFiles.length === 0) {
      resetUpload();
      return;
    }
    uploadZone.classList.add('has-file');
    if (selectedFiles.length === 1) {
      var f = selectedFiles[0];
      uploadZone.querySelector('.dropzone-content').innerHTML =
        '<div class="dropzone-icon"><svg width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>' +
        '<p class="dropzone-filename">' + esc(f.name) + '</p>' +
        '<span class="dropzone-filesize">' + fmtSize(f.size) + ' — Listo para subir</span>';
    } else {
      var totalSize = selectedFiles.reduce(function (s, f) { return s + f.size; }, 0);
      var listHtml = selectedFiles.map(function (f, i) {
        var isPdf = /\.pdf$/i.test(f.name);
        return '<div class="ref-file-item">' +
          '<span class="work-file-badge ' + (isPdf ? 'work-badge-pdf' : 'work-badge-xls') + '">' + (isPdf ? 'PDF' : 'XLS') + '</span>' +
          '<span class="ref-file-name">' + esc(f.name) + '</span>' +
          '<span class="ref-file-size">' + fmtSize(f.size) + '</span>' +
          '<button type="button" class="ref-file-remove" data-idx="' + i + '" title="Quitar">&times;</button>' +
          '</div>';
      }).join('');
      uploadZone.querySelector('.dropzone-content').innerHTML =
        '<div class="dropzone-icon"><svg width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>' +
        '<p class="dropzone-filename">' + selectedFiles.length + ' archivo' + (selectedFiles.length > 1 ? 's' : '') + ' seleccionado' + (selectedFiles.length > 1 ? 's' : '') + ' (' + fmtSize(totalSize) + ')</p>' +
        '<div class="ref-files-list">' + listHtml + '</div>' +
        '<span class="dropzone-hint" style="margin-top:0.5rem">Arrastra más o haz clic para agregar</span>';
    }
  }

  uploadZone.addEventListener('click', function (e) {
    var removeBtn = e.target.closest('.ref-file-remove');
    if (removeBtn) {
      e.stopPropagation();
      var idx = parseInt(removeBtn.getAttribute('data-idx'), 10);
      selectedFiles.splice(idx, 1);
      updateWorkDropzoneUI();
      checkUploadReady();
      updateReplacesVisibility();
    }
  });

  function resetUpload() {
    selectedFiles = [];
    fileInput.value = '';
    uploadZone.classList.remove('has-file');
    uploadZone.querySelector('.dropzone-content').innerHTML =
      '<div class="dropzone-icon"><svg width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg></div>' +
      '<p class="dropzone-text">Arrastra uno o varios archivos aquí o <strong>haz clic para seleccionar</strong></p>' +
      '<span class="dropzone-hint">Excel (.xlsx, .xls, .csv) o PDF — Máx. 50 MB — Puedes seleccionar varios</span>';
    btnUpload.disabled = true;
    if (inputNotes) inputNotes.value = '';
  }

  /* ─── Progress panel for work files ─── */
  var workProgressWrap = document.getElementById('workProgressWrap');
  var workProgressTitle = document.getElementById('workProgressTitle');
  var workProgressSpeed = document.getElementById('workProgressSpeed');
  var workProgressCount = document.getElementById('workProgressCount');
  var workProgressElapsed = document.getElementById('workProgressElapsed');
  var workProgressBar = document.getElementById('workProgressBar');
  var workProgressPercent = document.getElementById('workProgressPercent');
  var workProgressFiles = document.getElementById('workProgressFiles');

  var WORK_PARALLEL = 3;
  var workUploadState = null;

  function initWorkUploadState(total) {
    workUploadState = {
      total: total, completed: 0, failed: 0,
      startTime: Date.now(), totalBytes: 0, loadedBytes: 0, files: {}
    };
  }

  function updateWorkProgress() {
    if (!workUploadState) return;
    var st = workUploadState;
    var done = st.completed + st.failed;
    var pct = st.totalBytes > 0 ? Math.round((st.loadedBytes / st.totalBytes) * 100) : (st.total > 0 ? Math.round((done / st.total) * 100) : 0);
    workProgressBar.style.width = pct + '%';
    workProgressPercent.textContent = pct + '%';
    workProgressCount.textContent = done + ' de ' + st.total + ' completados';
    var elapsed = Date.now() - st.startTime;
    workProgressElapsed.textContent = fmtElapsed(elapsed);
    if (st.loadedBytes > 0 && elapsed > 500) {
      var speed = st.loadedBytes / (elapsed / 1000);
      workProgressSpeed.textContent = fmtSpeed(speed);
      var remaining = st.totalBytes - st.loadedBytes;
      if (speed > 0 && remaining > 0) workProgressSpeed.textContent += ' — ~' + fmtElapsed((remaining / speed) * 1000) + ' restante';
    }
    btnUpload.textContent = 'Subiendo ' + done + '/' + st.total + '…';
    btnUpload.classList.add('btn-uploading');
    renderWorkFileProgress();
  }

  function renderWorkFileProgress() {
    if (!workUploadState || !workProgressFiles) return;
    var entries = Object.values(workUploadState.files);
    entries.sort(function (a, b) { return a.index - b.index; });
    var visible = entries.filter(function (f) { return f.status === 'uploading' || f.status === 'done' || f.status === 'error'; });
    var lastDone = visible.filter(function (f) { return f.status === 'done'; });
    var active = visible.filter(function (f) { return f.status === 'uploading'; });
    var errored = visible.filter(function (f) { return f.status === 'error'; });
    var show = [].concat(errored, active, lastDone.slice(-2));
    workProgressFiles.innerHTML = show.map(function (f) {
      var icon, barClass, pctText;
      if (f.status === 'done') {
        icon = '<svg class="pf-icon pf-done" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>';
        barClass = 'pf-bar-done'; pctText = fmtSize(f.total);
      } else if (f.status === 'error') {
        icon = '<svg class="pf-icon pf-error" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
        barClass = 'pf-bar-error'; pctText = f.errorMsg || 'Error';
      } else {
        icon = '<div class="pf-spinner"></div>';
        barClass = '';
        var filePct = f.total > 0 ? Math.round((f.loaded / f.total) * 100) : 0;
        pctText = filePct + '% · ' + fmtSize(f.loaded) + ' / ' + fmtSize(f.total);
      }
      var barWidth = f.total > 0 ? Math.round((f.loaded / f.total) * 100) : 0;
      if (f.status === 'done') barWidth = 100;
      return '<div class="pf-row pf-' + f.status + '">' + icon +
        '<div class="pf-info"><div class="pf-name">' + esc(f.name) + '</div><div class="pf-track"><div class="pf-fill ' + barClass + '" style="width:' + barWidth + '%"></div></div></div>' +
        '<div class="pf-pct">' + pctText + '</div></div>';
    }).join('');
  }

  function showWorkProgress() {
    workProgressWrap.style.display = '';
    workProgressWrap.classList.add('uploading');
    workProgressBar.className = 'progress-bar-fill';
    workProgressPercent.className = 'progress-percent';
    workProgressTitle.textContent = 'Subiendo archivos…';
    workProgressSpeed.textContent = '';
    workProgressElapsed.textContent = '';
  }

  function hideWorkProgress() {
    workProgressWrap.style.display = 'none';
    workProgressWrap.classList.remove('uploading');
    workProgressBar.style.width = '0%';
    if (workProgressFiles) workProgressFiles.innerHTML = '';
    workUploadState = null;
    btnUpload.innerHTML =
      '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg> Subir archivo';
    btnUpload.classList.remove('btn-uploading');
  }

  function finishWorkProgress() {
    workProgressBar.style.width = '100%';
    workProgressBar.className = 'progress-bar-fill done';
    workProgressPercent.textContent = '100%';
    workProgressPercent.className = 'progress-percent done';
    workProgressWrap.classList.remove('uploading');
    workProgressTitle.textContent = 'Subida completada';
    btnUpload.textContent = 'Listo';
    btnUpload.classList.remove('btn-uploading');
  }

  function uploadWorkFile(file, index, name, uploadStatus, noteVal, replacesId) {
    return new Promise(function (resolve, reject) {
      var fd = new FormData();
      fd.append('file', file);
      fd.append('uploaded_by', name);
      fd.append('status', uploadStatus);
      if (noteVal) fd.append('notes', noteVal);
      if (uploadStatus === 'validado' && replacesId) fd.append('replaces_id', replacesId);

      workUploadState.files[index] = {
        index: index, name: file.name, status: 'uploading',
        loaded: 0, total: file.size, errorMsg: ''
      };
      workUploadState.totalBytes += file.size;
      updateWorkProgress();

      var xhr = new XMLHttpRequest();
      var prevLoaded = 0;
      xhr.upload.addEventListener('progress', function (e) {
        if (e.lengthComputable) {
          var delta = e.loaded - prevLoaded; prevLoaded = e.loaded;
          workUploadState.loadedBytes += delta;
          workUploadState.files[index].loaded = e.loaded;
          workUploadState.files[index].total = e.total;
          updateWorkProgress();
        }
      });
      xhr.addEventListener('load', function () {
        if (xhr.status === 413) {
          workUploadState.files[index].status = 'error'; workUploadState.files[index].errorMsg = 'Muy grande';
          workUploadState.failed++; updateWorkProgress(); reject(new Error('Archivo demasiado grande')); return;
        }
        if (xhr.status < 200 || xhr.status >= 300) {
          workUploadState.files[index].status = 'error'; workUploadState.files[index].errorMsg = 'Error ' + xhr.status;
          workUploadState.failed++; updateWorkProgress(); reject(new Error('Error del servidor')); return;
        }
        try {
          var data = JSON.parse(xhr.responseText);
          if (!data.ok) { workUploadState.files[index].status = 'error'; workUploadState.files[index].errorMsg = data.error || 'Error'; workUploadState.failed++; updateWorkProgress(); reject(new Error(data.error)); return; }
          workUploadState.files[index].status = 'done'; workUploadState.files[index].loaded = workUploadState.files[index].total;
          workUploadState.completed++; updateWorkProgress(); resolve(data);
        } catch (e) {
          workUploadState.files[index].status = 'error'; workUploadState.files[index].errorMsg = 'Respuesta inválida';
          workUploadState.failed++; updateWorkProgress(); reject(new Error('Respuesta inválida'));
        }
      });
      xhr.addEventListener('error', function () {
        workUploadState.files[index].status = 'error'; workUploadState.files[index].errorMsg = 'Sin conexión';
        workUploadState.failed++; updateWorkProgress(); reject(new Error('Error de conexión'));
      });
      xhr.addEventListener('abort', function () {
        workUploadState.files[index].status = 'error'; workUploadState.files[index].errorMsg = 'Cancelado';
        workUploadState.failed++; updateWorkProgress(); reject(new Error('Cancelado'));
      });
      xhr.open('POST', u('api/files'));
      xhr.send(fd);
    });
  }

  btnUpload.addEventListener('click', async function () {
    if (selectedFiles.length === 0) return;
    var name = (inputName && inputName.value.trim()) || '';
    if (!name) { setMsg(uploadMsg, 'Escribe tu nombre antes de subir.', 'error'); return; }
    localStorage.setItem('koboup_name', name);

    var uploadStatus = getSelectedStatus();
    var noteVal = (inputNotes && inputNotes.value.trim()) || '';
    var replacesId = (selectReplaces && selectReplaces.value) || '';

    if (selectedFiles.length === 1) {
      var fd = new FormData();
      fd.append('file', selectedFiles[0]);
      fd.append('uploaded_by', name);
      fd.append('status', uploadStatus);
      if (noteVal) fd.append('notes', noteVal);
      if (uploadStatus === 'validado' && replacesId) fd.append('replaces_id', replacesId);

      btnUpload.disabled = true;
      setMsg(uploadMsg, 'Subiendo archivo...', 'info');
      try {
        var r = await fetch(u('api/files'), { method: 'POST', body: fd });
        var data = await r.json();
        if (!data.ok) throw new Error(data.error || 'Error al subir');
        var msg = 'Archivo "' + (data.file.original_name || '') + '" subido correctamente como ' + statusLabel(data.file.status) + '.';
        if (data.superseded && data.superseded.length > 0) msg += ' ' + data.superseded.length + ' archivo(s) anterior(es) marcado(s) como reemplazado(s).';
        setMsg(uploadMsg, msg, 'ok');
        resetUpload();
        replacesRow.style.display = 'none';
        var defaultRadio = document.querySelector('input[name="uploadStatus"][value="pendiente"]');
        if (defaultRadio) defaultRadio.checked = true;
        await loadFiles();
      } catch (e) {
        setMsg(uploadMsg, 'Error: ' + e.message, 'error');
        btnUpload.disabled = false;
      }
      return;
    }

    btnUpload.disabled = true;
    var filesToUpload = selectedFiles.slice();
    var total = filesToUpload.length;
    initWorkUploadState(total);
    setMsg(uploadMsg, '', '');
    showWorkProgress();
    updateWorkProgress();
    workProgressWrap.scrollIntoView({ behavior: 'smooth', block: 'center' });

    var elapsedInterval = setInterval(function () {
      if (!workUploadState) { clearInterval(elapsedInterval); return; }
      updateWorkProgress();
    }, 1000);

    var errors = [];
    var running = 0;
    var idx = 0;

    await new Promise(function (resolveAll) {
      function next() {
        while (running < WORK_PARALLEL && idx < total) {
          (function (i, file) {
            running++;
            uploadWorkFile(file, i, name, uploadStatus, noteVal, '')
              .catch(function (e) { errors.push(file.name + ': ' + e.message); })
              .then(function () {
                running--;
                if (idx >= total && running === 0) resolveAll();
                else next();
              });
          })(idx, filesToUpload[idx]);
          idx++;
        }
        if (idx >= total && running === 0) resolveAll();
      }
      next();
    });

    clearInterval(elapsedInterval);
    finishWorkProgress();
    updateWorkProgress();

    var elapsed = workUploadState ? fmtElapsed(Date.now() - workUploadState.startTime) : '';
    var successCount = workUploadState ? workUploadState.completed : 0;
    if (errors.length === 0) {
      setMsg(uploadMsg, successCount + ' archivo' + (successCount > 1 ? 's' : '') + ' subido' + (successCount > 1 ? 's' : '') + ' correctamente' + (elapsed ? ' (' + elapsed + ')' : '') + '.', 'ok');
    } else {
      setMsg(uploadMsg, successCount + ' subido' + (successCount > 1 ? 's' : '') + ', ' + errors.length + ' error' + (errors.length > 1 ? 'es' : '') + (elapsed ? ' (' + elapsed + ')' : '') + '.', 'error');
    }

    setTimeout(hideWorkProgress, 8000);
    resetUpload();
    replacesRow.style.display = 'none';
    var defaultRadio = document.querySelector('input[name="uploadStatus"][value="pendiente"]');
    if (defaultRadio) defaultRadio.checked = true;
    await loadFiles();
  });

  // Botón descarga masiva
  var btnBulkDownload = document.getElementById('btnBulkDownload');
  var bulkDlModalOverlay = document.getElementById('bulkDlModalOverlay');
  var bulkDlPassword = document.getElementById('bulkDlPassword');
  var bulkDlMsg = document.getElementById('bulkDlMsg');
  var bulkDlCancel = document.getElementById('bulkDlCancel');
  var bulkDlConfirm = document.getElementById('bulkDlConfirm');

  function updateBulkDownloadVisibility() {
    if (btnBulkDownload) {
      btnBulkDownload.style.display = currentFilter === 'validado' ? '' : 'none';
    }
  }

  if (btnBulkDownload) {
    btnBulkDownload.addEventListener('click', function () {
      bulkDlPassword.value = '';
      setMsg(bulkDlMsg, '');
      bulkDlConfirm.disabled = false;
      bulkDlModalOverlay.style.display = 'flex';
      bulkDlPassword.focus();
    });
  }

  bulkDlCancel.addEventListener('click', function () { bulkDlModalOverlay.style.display = 'none'; });
  bulkDlModalOverlay.addEventListener('click', function (e) { if (e.target === bulkDlModalOverlay) bulkDlModalOverlay.style.display = 'none'; });

  bulkDlPassword.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') bulkDlConfirm.click();
  });

  bulkDlConfirm.addEventListener('click', async function () {
    var pwd = (bulkDlPassword.value || '').trim();
    if (!pwd) {
      bulkDlPassword.style.borderColor = '#ef4444';
      bulkDlPassword.focus();
      setMsg(bulkDlMsg, 'Ingresa la contraseña.', 'error');
      return;
    }
    bulkDlPassword.style.borderColor = '';
    bulkDlConfirm.disabled = true;
    setMsg(bulkDlMsg, 'Generando ZIP, espera...', 'info');

    try {
      var r = await fetch(u('api/files/download-validated-zip'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pwd }),
      });
      if (r.status === 403) {
        setMsg(bulkDlMsg, 'Contraseña incorrecta. Intenta de nuevo.', 'error');
        bulkDlPassword.style.borderColor = '#ef4444';
        bulkDlPassword.value = '';
        bulkDlPassword.focus();
        bulkDlConfirm.disabled = false;
        return;
      }
      if (r.status === 404) {
        setMsg(bulkDlMsg, 'No hay archivos validados para descargar.', 'error');
        bulkDlConfirm.disabled = false;
        return;
      }
      if (!r.ok) {
        var errData = await r.json().catch(function () { return {}; });
        throw new Error(errData.error || 'Error del servidor');
      }
      var blob = await r.blob();
      var disposition = r.headers.get('Content-Disposition') || '';
      var filenameMatch = disposition.match(/filename="?([^";\n]+)"?/);
      var filename = filenameMatch ? filenameMatch[1] : 'archivos_validados.zip';
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      bulkDlModalOverlay.style.display = 'none';
    } catch (e) {
      setMsg(bulkDlMsg, 'Error: ' + e.message, 'error');
      bulkDlConfirm.disabled = false;
    }
  });

  // Filtros
  document.querySelectorAll('#filterTabs .tab').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('#filterTabs .tab').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      currentFilter = btn.getAttribute('data-filter') || '';
      updateBulkDownloadVisibility();
      renderFiles();
    });
  });
  btnRefresh.addEventListener('click', function () { loadFiles(); });

  async function loadFiles() {
    try {
      var r = await fetch(u('api/files'));
      var data = await r.json();
      if (!data.ok) throw new Error(data.error || 'Error');
      filesCache = data.files || [];
      loadPatientKpi();
      renderFiles();
      if (replacesRow.style.display !== 'none') populateReplacesSelect();
    } catch (e) {
      filesList.innerHTML = '<div class="empty-state"><p>Error al cargar archivos</p><span>' + esc(e.message) + '</span></div>';
    }
  }

  function fmtNum(n) {
    return n.toLocaleString('es-MX');
  }

  function loadPatientKpi() {
    fetch(u('api/stats/records')).then(function (r) { return r.json(); }).then(function (data) {
      if (!data.ok) return;
      var total = data.validated_records || 0;
      var files = data.validated_files || 0;
      if (kpiPatients) {
        kpiPatients.textContent = fmtNum(total);
        kpiPatients.style.transform = 'scale(1.06)';
        setTimeout(function () { kpiPatients.style.transform = 'scale(1)'; }, 200);
      }
      if (kpiPatientsDetail) {
        kpiPatientsDetail.textContent = 'en ' + files + ' archivo' + (files !== 1 ? 's' : '') + ' validado' + (files !== 1 ? 's' : '');
      }
    }).catch(function () {});
  }

  function renderFiles() {
    var filtered = filesCache;
    if (currentFilter) filtered = filesCache.filter(function (f) { return f.status === currentFilter; });

    if (filtered.length === 0) {
      filesList.innerHTML =
        '<div class="empty-state">' +
        '<svg width="56" height="56" fill="none" stroke="currentColor" stroke-width="1.2" viewBox="0 0 24 24" opacity="0.3"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>' +
        '<p>' + (currentFilter ? 'No hay archivos con estado "' + statusLabel(currentFilter) + '".' : 'Aún no hay archivos.') + '</p></div>';
      return;
    }

    filesList.innerHTML = filtered.map(function (f) {
      var isPdf = f.file_type === 'pdf';
      var iconClass = isPdf ? 'pdf' : 'excel';
      var iconText = isPdf ? 'PDF' : 'XLS';
      var isSuperseded = f.status === 'reemplazado';
      var isEditing = !!f.is_editing;
      var isEditedValidated = !!f.edited_validated;
      var isKoboApiSent = !!f.kobo_api_sent;

      var actions = [];
      if (isSuperseded) {
        actions.push('<button class="btn btn-outline btn-sm js-delete" data-id="' + f.id + '" title="Eliminar">' +
          '<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg></button>');
      } else {
        actions.push('<button class="btn btn-outline btn-sm js-download" data-id="' + f.id + '" data-url="' + u(f.download_url || ('api/files/' + f.id + '/download')) + '" data-name="' + esc(f.original_name || f.stored_name) + '">' +
          '<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Descargar</button>');
        if (f.status === 'validado') {
          var canSheet = canOpenSheetEditor(f);
          var edLabel = canSheet ? 'Editar tabla' : 'Editar';
          var edTitle = canSheet ? 'Editar todo el archivo: celdas, filas y columnas' : 'Nota, nombre y responsable del archivo';
          actions.push('<button class="btn btn-outline-purple btn-sm js-edit" data-id="' + f.id + '" data-sheet="' + (canSheet ? '1' : '0') + '" title="' + escAttr(edTitle) + '">' +
            '<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4 12.5-12.5z"/></svg> ' + esc(edLabel) + '</button>');
          if (isEditing) {
            actions.push('<button class="btn btn-outline-blue btn-sm js-force-unlock" data-id="' + f.id + '" data-name="' + esc(f.original_name || f.stored_name) + '" title="Liberar bloqueo de edición">' +
              '<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 1v6"/><path d="M8 5h8"/><rect x="4" y="11" width="16" height="10" rx="2"/></svg> Liberar bloqueo</button>');
          }
        }

        if (f.status === 'pendiente') {
          actions.push('<button class="btn btn-outline-blue btn-sm js-to-review" data-id="' + f.id + '">Marcar en validación</button>');
        }
        if (f.status !== 'validado') {
          actions.push('<button class="btn btn-outline-green btn-sm js-validate" data-id="' + f.id + '" data-name="' + esc(f.original_name) + '">' +
            '<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg> Validar</button>');
        }
        actions.push('<button class="btn btn-outline-red btn-sm js-delete" data-id="' + f.id + '">' +
          '<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg></button>');
      }

      var meta = '<span class="badge ' + statusBadgeClass(f.status) + '">' + statusLabel(f.status) + '</span>';
      if (isKoboApiSent) {
        meta += '<span class="sep">·</span><span class="badge badge-kobo-api-sent" title="' + escAttr(
          f.kobo_api_last_submitted_at ? ('Último envío API: ' + f.kobo_api_last_submitted_at) : 'Con envío a Kobo por API'
        ) + '">Envío a Kobo (API)</span>';
      }
      if (isEditedValidated) {
        meta += '<span class="sep">·</span><span class="badge badge-edited-validated">Editado validado</span>';
      }
      if (isEditing) {
        meta += '<span class="sep">·</span><span class="badge badge-editing">En edición</span>';
      }
      if (f.row_count != null && f.row_count > 0) meta += '<span class="sep">·</span><span class="file-row-count">' + fmtNum(f.row_count) + ' registros</span>';
      if (f.size_bytes) meta += '<span class="sep">·</span>' + fmtSize(f.size_bytes);
      meta += '<span class="sep">·</span>' + timeSince(f.created_at);

      var people = '';
      if (isEditing) {
        people += '<span class="person person-editing"><svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="9"/></svg> En edición por: <strong>' + esc(f.editing_by || 'Usuario') + '</strong></span>';
      }
      if (f.uploaded_by) people += '<span class="person"><svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> Subido por: <strong>' + esc(f.uploaded_by) + '</strong></span>';
      if (f.downloaded_by) people += '<span class="person person-download"><svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Descargado por: <strong>' + esc(f.downloaded_by) + '</strong> (' + timeSince(f.downloaded_at) + ')</span>';
      if (f.validated_by) people += '<span class="person person-valid"><svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg> Validado por: <strong>' + esc(f.validated_by) + '</strong> (' + timeSince(f.validated_at) + ')</span>';

      var supersededNote = '';
      if (isSuperseded) {
        var replacedBy = filesCache.find(function (r) { return r.id === f.superseded_by; });
        supersededNote = '<div class="file-superseded-note">' +
          '<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg> ' +
          'Archivo original reemplazado por versión validada' +
          (replacedBy ? ': <strong>' + esc(replacedBy.original_name) + '</strong>' : '') +
          '</div>';
      }

      return '<div class="file-row' + (isSuperseded ? ' file-row-superseded' : '') + (isEditing ? ' file-row-editing' : '') + (isKoboApiSent ? ' file-row-kobo-api-sent' : '') + (isEditedValidated ? ' file-row-edited-validated' : '') + '" data-id="' + f.id + '">' +
        '<div class="file-icon-wrap ' + iconClass + (isSuperseded ? ' icon-superseded' : '') + '">' + iconText + '</div>' +
        '<div class="file-info">' +
          '<div class="file-name' + (isSuperseded ? ' name-superseded' : '') + '">' + esc(f.original_name || f.stored_name) + '</div>' +
          '<div class="file-meta">' + meta + '</div>' +
          (people ? '<div class="file-people">' + people + '</div>' : '') +
          (f.notes ? '<div class="file-notes">' + esc(f.notes) + '</div>' : '') +
          supersededNote +
        '</div>' +
        '<div class="file-actions">' + actions.join('') + '</div>' +
        '</div>';
    }).join('');
  }

  // Acciones archivos de trabajo
  filesList.addEventListener('click', function (ev) {
    var dlBtn = ev.target.closest('.js-download');
    var eBtn = ev.target.closest('.js-edit');
    var vBtn = ev.target.closest('.js-validate');
    var dBtn = ev.target.closest('.js-delete');
    var rBtn = ev.target.closest('.js-to-review');
    var fuBtn = ev.target.closest('.js-force-unlock');
    if (dlBtn) openDownloadModal(dlBtn.getAttribute('data-id'), dlBtn.getAttribute('data-url'), dlBtn.getAttribute('data-name'));
    else if (eBtn) onEditFileClick(eBtn.getAttribute('data-id'), eBtn.getAttribute('data-sheet') === '1');
    else if (vBtn) openValidateModal(vBtn.getAttribute('data-id'), vBtn.getAttribute('data-name'));
    else if (rBtn) changeStatus(rBtn.getAttribute('data-id'), 'por_validar');
    else if (fuBtn) forceUnlockFile(fuBtn.getAttribute('data-id'), fuBtn.getAttribute('data-name'));
    else if (dBtn) deleteFile(dBtn.getAttribute('data-id'));
  });

  async function forceUnlockFile(id, name) {
    var editorName = getCurrentEditorName();
    if (!editorName) {
      alert('Escribe tu nombre para liberar bloqueos.');
      if (inputName) inputName.focus();
      return;
    }
    if (!confirm('¿Liberar el bloqueo de edición para "' + (name || 'este archivo') + '"?')) return;
    try {
      var r = await fetch(u('api/files/' + id + '/sheet/force-unlock'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ editor_name: editorName })
      });
      var d = await r.json();
      if (!d.ok) throw new Error((d && d.error) || 'No se pudo liberar el bloqueo');
      setMsg(uploadMsg, 'Bloqueo liberado correctamente.', 'ok');
      await loadFiles();
    } catch (e) {
      setMsg(uploadMsg, 'Error al liberar bloqueo: ' + (e && e.message ? e.message : e), 'error');
    }
  }

  /* ─── Modal validar: multi-paso ─── */

  function closeValidateModal() {
    modalOverlay.style.display = 'none';
    pendingValidateId = null;
    valSelectedFile = null;
    valStep1.style.display = '';
    valStep2Upload.style.display = 'none';
    valStep2Select.style.display = 'none';
    resetValUploadZone();
    setMsg(valUploadMsg, '');
    setMsg(valSelectMsg, '');
  }

  function openValidateModal(id, name) {
    pendingValidateId = id;
    modalFilename.textContent = name || '';
    var sn = localStorage.getItem('koboup_name') || '';
    if (inputName && inputName.value.trim()) sn = inputName.value.trim();
    valUploadName.value = sn;
    valSelectName.value = sn;
    valUploadNotes.value = '';
    valSelectedFile = null;
    valUploadConfirm.disabled = true;
    valSelectConfirm.disabled = true;

    valUploadReplacingName.textContent = name || '';
    valSelectReplacingName.textContent = name || '';

    populateValSelectList();

    valStep1.style.display = '';
    valStep2Upload.style.display = 'none';
    valStep2Select.style.display = 'none';
    resetValUploadZone();
    setMsg(valUploadMsg, '');
    setMsg(valSelectMsg, '');

    modalOverlay.style.display = 'flex';
  }

  function populateValSelectList() {
    var validated = filesCache.filter(function (f) { return f.status === 'validado'; });
    var html = '<option value="">— Selecciona un archivo —</option>';
    validated.forEach(function (f) {
      var label = f.original_name || f.stored_name;
      var extra = '';
      if (f.uploaded_by) extra += ' · ' + f.uploaded_by;
      if (f.created_at) extra += ' · ' + fmtDate(f.created_at);
      html += '<option value="' + f.id + '">' + esc(label) + extra + '</option>';
    });
    valSelectFile.innerHTML = html;
  }

  modalCancel.addEventListener('click', closeValidateModal);
  valUploadCancel.addEventListener('click', closeValidateModal);
  valSelectCancel.addEventListener('click', closeValidateModal);
  modalOverlay.addEventListener('click', function (e) { if (e.target === modalOverlay) closeValidateModal(); });

  // Paso 1 → Paso 2A (subir)
  valOptUpload.addEventListener('click', function () {
    valStep1.style.display = 'none';
    valStep2Upload.style.display = '';
    valUploadName.focus();
  });

  // Paso 1 → Paso 2B (seleccionar)
  valOptSelect.addEventListener('click', function () {
    valStep1.style.display = 'none';
    valStep2Select.style.display = '';
    valSelectName.focus();
  });

  // Botones atrás
  valBackFromUpload.addEventListener('click', function () {
    valStep2Upload.style.display = 'none';
    valStep1.style.display = '';
    resetValUploadZone();
  });
  valBackFromSelect.addEventListener('click', function () {
    valStep2Select.style.display = 'none';
    valStep1.style.display = '';
  });

  /* ─── Paso 2A: subir archivo validado ─── */

  function resetValUploadZone() {
    valSelectedFile = null;
    valFileInput.value = '';
    valUploadZone.classList.remove('has-file');
    valUploadZone.querySelector('.dropzone-content').innerHTML =
      '<div class="dropzone-icon"><svg width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg></div>' +
      '<p class="dropzone-text">Arrastra el archivo validado o <strong>haz clic</strong></p>' +
      '<span class="dropzone-hint">Excel (.xlsx, .xls, .csv) o PDF</span>';
    valUploadConfirm.disabled = true;
  }

  function checkValUploadReady() {
    valUploadConfirm.disabled = !(valSelectedFile && (valUploadName.value || '').trim());
  }

  valUploadName.addEventListener('input', checkValUploadReady);

  valUploadZone.addEventListener('click', function () { valFileInput.click(); });
  valUploadZone.addEventListener('dragover', function (e) { e.preventDefault(); valUploadZone.classList.add('dragover'); });
  valUploadZone.addEventListener('dragleave', function () { valUploadZone.classList.remove('dragover'); });
  valUploadZone.addEventListener('drop', function (e) {
    e.preventDefault(); valUploadZone.classList.remove('dragover');
    var f = e.dataTransfer && e.dataTransfer.files[0];
    if (f && /\.(xlsx|xls|csv|pdf)$/i.test(f.name)) selectValFile(f);
  });
  valFileInput.addEventListener('change', function () {
    if (valFileInput.files[0]) selectValFile(valFileInput.files[0]);
  });

  function selectValFile(f) {
    valSelectedFile = f;
    valUploadZone.classList.add('has-file');
    valUploadZone.querySelector('.dropzone-content').innerHTML =
      '<div class="dropzone-icon"><svg width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>' +
      '<p class="dropzone-filename">' + esc(f.name) + '</p>' +
      '<span class="dropzone-filesize">' + fmtSize(f.size) + ' — Listo</span>';
    checkValUploadReady();
  }

  valUploadConfirm.addEventListener('click', async function () {
    if (!pendingValidateId || !valSelectedFile) return;
    var vName = (valUploadName.value || '').trim();
    if (!vName) { valUploadName.style.borderColor = '#ef4444'; valUploadName.focus(); return; }
    valUploadName.style.borderColor = '';
    localStorage.setItem('koboup_name', vName);

    var fd = new FormData();
    fd.append('file', valSelectedFile);
    fd.append('uploaded_by', vName);
    fd.append('status', 'validado');
    fd.append('replaces_id', pendingValidateId);
    var noteVal = (valUploadNotes.value || '').trim();
    if (noteVal) fd.append('notes', noteVal);

    valUploadConfirm.disabled = true;
    setMsg(valUploadMsg, 'Subiendo archivo...', 'info');

    try {
      var r = await fetch(u('api/files'), { method: 'POST', body: fd });
      var data = await r.json();
      if (!data.ok) throw new Error(data.error || 'Error al subir');
      setMsg(uploadMsg, 'Archivo "' + (data.file.original_name || '') + '" subido como validado. El archivo original fue reemplazado.', 'ok');
      closeValidateModal();
      await loadFiles();
    } catch (e) {
      setMsg(valUploadMsg, 'Error: ' + e.message, 'error');
      valUploadConfirm.disabled = false;
    }
  });

  /* ─── Paso 2B: seleccionar archivo existente ─── */

  function checkValSelectReady() {
    valSelectConfirm.disabled = !((valSelectFile.value || '').trim() && (valSelectName.value || '').trim());
  }

  valSelectFile.addEventListener('change', checkValSelectReady);
  valSelectName.addEventListener('input', checkValSelectReady);

  valSelectConfirm.addEventListener('click', async function () {
    if (!pendingValidateId) return;
    var selectedId = (valSelectFile.value || '').trim();
    var vName = (valSelectName.value || '').trim();
    if (!selectedId) { setMsg(valSelectMsg, 'Selecciona un archivo validado.', 'error'); return; }
    if (!vName) { valSelectName.style.borderColor = '#ef4444'; valSelectName.focus(); return; }
    valSelectName.style.borderColor = '';
    localStorage.setItem('koboup_name', vName);

    valSelectConfirm.disabled = true;
    setMsg(valSelectMsg, 'Procesando...', 'info');

    try {
      var r = await fetch(u('api/files/' + pendingValidateId + '/replace-with'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ validated_file_id: parseInt(selectedId, 10), validated_by: vName }),
      });
      var data = await r.json();
      if (!data.ok) throw new Error(data.error || 'Error');
      setMsg(uploadMsg, 'Archivo reemplazado correctamente por la versión validada.', 'ok');
      closeValidateModal();
      await loadFiles();
    } catch (e) {
      setMsg(valSelectMsg, 'Error: ' + e.message, 'error');
      valSelectConfirm.disabled = false;
    }
  });

  async function changeStatus(id, newStatus) {
    try {
      var r = await fetch(u('api/files/' + id + '/status'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      var data = await r.json();
      if (!data.ok) throw new Error(data.error || 'Error');
      await loadFiles();
    } catch (e) {
      alert('Error: ' + e.message);
    }
  }

  async function deleteFile(id) {
    if (!confirm('¿Eliminar este archivo? Esta acción no se puede deshacer.')) return;
    try {
      var r = await fetch(u('api/files/' + id), { method: 'DELETE' });
      var data = await r.json();
      if (!data.ok) throw new Error(data.error || 'Error');
      await loadFiles();
    } catch (e) {
      alert('Error al eliminar: ' + e.message);
    }
  }

  function onEditFileClick(id, asSheet) {
    var fid = parseInt(id, 10);
    var file = filesCache.find(function (f) { return f.id === fid; });
    if (!file) return;
    if (file.status !== 'validado') {
      alert('Solo se permite editar archivos en la pestaña "Validados".');
      return;
    }
    if (asSheet) {
      openSheetEditor(fid);
    } else {
      openEditModal(String(fid));
    }
  }

  function setSheetMsg(t, cl) {
    if (!sheetStatus) return;
    sheetStatus.textContent = t != null ? t : '';
    sheetStatus.className = 'sheet-editor-status' + (cl ? ' ' + cl : '');
  }

  function colNameAtIndexUnique(raw, index) {
    if (!sheetState) return (String(raw || '').trim() || 'Columna');
    var base = (String(raw != null ? raw : '')).trim() || 'Columna';
    var cj;
    for (var n = 0; n < 5000; n += 1) {
      var candidate = n === 0 ? base : (base + ' (' + n + ')');
      var usedElsewhere = false;
      for (cj = 0; cj < sheetState.columns.length; cj += 1) {
        if (cj === index) continue;
        if (sheetState.columns[cj] === candidate) { usedElsewhere = true; break; }
      }
      if (!usedElsewhere) return candidate;
    }
    return base;
  }

  function newEmptyRow() {
    var o = {};
    (sheetState ? sheetState.columns : []).forEach(function (c) { o[c] = ''; });
    return o;
  }

  function uniqueNewColumnName() {
    var n;
    for (n = 0; n < 2000; n += 1) {
      var c = 'Columna nueva' + (n > 0 ? ' ' + (n + 1) : '');
      if (!sheetState || sheetState.columns.indexOf(c) < 0) return c;
    }
    return 'Col_' + String(Date.now());
  }

  function insertColumnLeftAt(ci) {
    if (!sheetState) return false;
    if (isNaN(ci) || ci < 0 || ci > sheetState.columns.length) return false;
    if (sheetState.columns.length >= 200) {
      setSheetMsg('Límite de 200 columnas. Divida el archivo o use otra hoja.', 'error');
      return false;
    }
    var newCol = uniqueNewColumnName();
    sheetState.columns.splice(ci, 0, newCol);
    sheetState.rows.forEach(function (r) { if (r) r[newCol] = ''; });
    if (sheetState.rows.length === 0) sheetState.rows = [newEmptyRow()];
    sheetDirty = true;
    renderSheetTable();
    return true;
  }

  function deleteColumnAt(ci) {
    if (!sheetState) return false;
    if (isNaN(ci) || ci < 0 || ci >= sheetState.columns.length) return false;
    var colName = sheetState.columns[ci];
    if (!confirm('¿Eliminar la columna "' + colName + '"?')) return false;
    if (sheetState.columnDisplay && Object.prototype.hasOwnProperty.call(sheetState.columnDisplay, colName)) {
      delete sheetState.columnDisplay[colName];
    }
    sheetState.columns.splice(ci, 1);
    sheetState.rows.forEach(function (row) { if (row) delete row[colName]; });
    if (sheetState.columns.length === 0) sheetState.rows = [];
    sheetDirty = true;
    renderSheetTable();
    return true;
  }

  function deleteRowAt(ri) {
    if (!sheetState) return false;
    if (isNaN(ri) || ri < 0 || ri >= sheetState.rows.length) return false;
    if (!confirm('¿Eliminar la fila #' + (ri + 1) + '?')) return false;
    sheetState.rows.splice(ri, 1);
    sheetDirty = true;
    renderSheetTable();
    return true;
  }

  function hideSheetContextMenu() {
    if (sheetContextMenuEl) sheetContextMenuEl.style.display = 'none';
    sheetContextTarget = null;
  }

  function ensureSheetContextMenu() {
    if (sheetContextMenuEl) return sheetContextMenuEl;
    var menu = document.createElement('div');
    menu.id = 'sheetContextMenu';
    menu.className = 'sheet-context-menu';
    menu.innerHTML = ''
      + '<button type="button" class="sheet-context-item" data-action="insert_col_left">Insertar columna (izquierda)</button>'
      + '<button type="button" class="sheet-context-item" data-action="delete_col">Eliminar columna</button>'
      + '<button type="button" class="sheet-context-item" data-action="delete_row">Eliminar fila</button>';
    document.body.appendChild(menu);
    menu.addEventListener('click', function (e) {
      var btn = e.target && e.target.closest('.sheet-context-item');
      if (!btn || !sheetContextTarget) return;
      var action = btn.getAttribute('data-action');
      if (action === 'insert_col_left' && sheetContextTarget.ci != null) {
        insertColumnLeftAt(sheetContextTarget.ci);
      } else if (action === 'delete_col' && sheetContextTarget.ci != null) {
        deleteColumnAt(sheetContextTarget.ci);
      } else if (action === 'delete_row' && sheetContextTarget.ri != null) {
        deleteRowAt(sheetContextTarget.ri);
      } else {
        setSheetMsg('Selecciona una celda, columna o fila para aplicar la acción.', 'info');
      }
      hideSheetContextMenu();
    });
    sheetContextMenuEl = menu;
    return menu;
  }

  function showSheetContextMenu(x, y, target) {
    var menu = ensureSheetContextMenu();
    sheetContextTarget = target || { ci: null, ri: null };
    menu.style.display = 'block';
    menu.style.left = Math.max(8, x) + 'px';
    menu.style.top = Math.max(8, y) + 'px';
    var rect = menu.getBoundingClientRect();
    var maxX = window.innerWidth - rect.width - 8;
    var maxY = window.innerHeight - rect.height - 8;
    if (rect.left > maxX) menu.style.left = Math.max(8, maxX) + 'px';
    if (rect.top > maxY) menu.style.top = Math.max(8, maxY) + 'px';
  }

  function onColumnHeaderBlur(input) {
    if (!sheetState || !input) return;
    var index = parseInt(input.getAttribute('data-ci'), 10);
    if (isNaN(index) || index < 0 || index >= sheetState.columns.length) return;
    var oldName = sheetState.columns[index];
    var newName = colNameAtIndexUnique(input.value, index);
    if (oldName === newName) {
      if (input.value !== newName) input.value = newName;
      return;
    }
    sheetState.columns[index] = newName;
    if (sheetState.columnDisplay) {
      if (Object.prototype.hasOwnProperty.call(sheetState.columnDisplay, oldName)) {
        delete sheetState.columnDisplay[oldName];
      }
    }
    sheetState.rows.forEach(function (row) {
      if (!row) return;
      row[newName] = (row[oldName] != null && row[oldName] !== undefined) ? String(row[oldName]) : '';
      if (oldName !== newName) delete row[oldName];
    });
    sheetDirty = true;
    renderSheetTable();
  }

  function getCurrentEditorName() {
    var n = (inputName && inputName.value || '').trim();
    if (!n) n = (localStorage.getItem('koboup_name') || '').trim();
    return n;
  }

  function normalizeSelection(sel) {
    if (!sel) return null;
    return {
      r1: Math.min(sel.r1, sel.r2),
      c1: Math.min(sel.c1, sel.c2),
      r2: Math.max(sel.r1, sel.r2),
      c2: Math.max(sel.c1, sel.c2)
    };
  }

  function hasSelection() {
    var s = normalizeSelection(sheetSelection);
    return !!(s && sheetState && s.r1 >= 0 && s.c1 >= 0 && s.r2 < sheetState.rows.length && s.c2 < sheetState.columns.length);
  }

  function isCellSelected(r, c) {
    var s = normalizeSelection(sheetSelection);
    if (!s) return false;
    return r >= s.r1 && r <= s.r2 && c >= s.c1 && c <= s.c2;
  }

  function paintSelection() {
    if (!sheetTableWrap) return;
    var cells = sheetTableWrap.querySelectorAll('.sheet-cell');
    Array.prototype.forEach.call(cells, function (el) {
      var r = parseInt(el.getAttribute('data-r'), 10);
      var c = parseInt(el.getAttribute('data-ci'), 10);
      el.classList.toggle('sheet-cell-selected', isCellSelected(r, c));
    });
  }

  function setSelection(r1, c1, r2, c2) {
    if (!sheetState) return;
    if (sheetState.rows.length === 0 || sheetState.columns.length === 0) return;
    var maxR = sheetState.rows.length - 1;
    var maxC = sheetState.columns.length - 1;
    sheetSelection = {
      r1: Math.max(0, Math.min(maxR, r1)),
      c1: Math.max(0, Math.min(maxC, c1)),
      r2: Math.max(0, Math.min(maxR, r2)),
      c2: Math.max(0, Math.min(maxC, c2))
    };
    paintSelection();
  }

  function clearSelection() {
    sheetSelection = null;
    paintSelection();
  }

  function getSelectedCellCount() {
    var s = normalizeSelection(sheetSelection);
    if (!s) return 0;
    return (s.r2 - s.r1 + 1) * (s.c2 - s.c1 + 1);
  }

  function selectedCellsMatrix() {
    var s = normalizeSelection(sheetSelection);
    if (!s || !sheetState) return [];
    var out = [];
    for (var r = s.r1; r <= s.r2; r += 1) {
      var line = [];
      for (var c = s.c1; c <= s.c2; c += 1) {
        var cn = sheetState.columns[c];
        line.push((sheetState.rows[r] && sheetState.rows[r][cn] != null) ? String(sheetState.rows[r][cn]) : '');
      }
      out.push(line);
    }
    return out;
  }

  async function copySelectedToClipboard() {
    if (!hasSelection()) return;
    try {
      var lines = selectedCellsMatrix().map(function (line) { return line.join('\t'); });
      await navigator.clipboard.writeText(lines.join('\n'));
      setSheetMsg('Selección copiada.', 'ok');
    } catch (e) {
      setSheetMsg('No se pudo copiar al portapapeles.', 'error');
    }
  }

  function applySingleValueToSelection(value) {
    var s = normalizeSelection(sheetSelection);
    if (!s || !sheetState) return;
    for (var r = s.r1; r <= s.r2; r += 1) {
      for (var c = s.c1; c <= s.c2; c += 1) {
        var col = sheetState.columns[c];
        if (!sheetState.rows[r]) sheetState.rows[r] = {};
        sheetState.rows[r][col] = value;
      }
    }
    sheetDirty = true;
  }

  function parseClipboardTable(text) {
    if (!text) return [];
    var rows = String(text).replace(/\r/g, '').split('\n');
    if (rows.length && rows[rows.length - 1] === '') rows.pop();
    return rows.map(function (r) { return r.split('\t'); });
  }

  function ensureRowCount(minRows) {
    while (sheetState.rows.length < minRows) {
      sheetState.rows.push(newEmptyRow());
    }
  }

  function pasteMatrixAtSelection(matrix) {
    if (!sheetState || !matrix || matrix.length === 0) return;
    var sel = normalizeSelection(sheetSelection);
    var startR = sel ? sel.r1 : 0;
    var startC = sel ? sel.c1 : 0;
    ensureRowCount(startR + matrix.length);
    for (var r = 0; r < matrix.length; r += 1) {
      for (var c = 0; c < matrix[r].length; c += 1) {
        var tc = startC + c;
        var tr = startR + r;
        if (tc >= sheetState.columns.length) continue;
        var colName = sheetState.columns[tc];
        if (!sheetState.rows[tr]) sheetState.rows[tr] = {};
        sheetState.rows[tr][colName] = String(matrix[r][c] == null ? '' : matrix[r][c]);
      }
    }
    sheetDirty = true;
    var endR = startR + matrix.length - 1;
    var maxCols = 0;
    matrix.forEach(function (row) { if (row.length > maxCols) maxCols = row.length; });
    var endC = startC + Math.max(1, maxCols) - 1;
    setSelection(startR, startC, endR, endC);
  }

  function lockColWidth(ci, px) {
    if (!sheetState) return;
    if (!sheetState.colWidths) sheetState.colWidths = {};
    var width = Math.max(70, Math.min(650, Math.round(px)));
    sheetState.colWidths[String(ci)] = width;
    sheetDirty = true;
  }

  function updateColRemoveOptions() {
    if (!sheetColRemove || !sheetState) return;
    var s = '<option value="">— Quitar columna —</option>';
    for (var i = 0; i < sheetState.columns.length; i += 1) {
      var c = sheetState.columns[i];
      var disp = sheetState.columnDisplay && sheetState.columnDisplay[c];
      var optLabel = disp && disp !== c ? (disp + ' — ' + c) : c;
      s += '<option value="' + i + '">' + esc(optLabel) + '</option>';
    }
    sheetColRemove.innerHTML = s;
  }

  function updateEditedValidatedButton() {
    if (!sheetMarkEditedValidated || !sheetState || !sheetState.file) return;
    var marked = !!sheetState.file.edited_validated;
    sheetMarkEditedValidated.textContent = marked ? 'Quitar Editado Validado' : 'Marcar Editado Validado';
    sheetMarkEditedValidated.classList.toggle('is-on', marked);
  }

  function normColName(v) {
    var s = String(v == null ? '' : v).trim().toLowerCase();
    try {
      s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    } catch (e) {}
    return s.replace(/[^a-z0-9]+/g, ' ').trim();
  }

  function looksMissingValue(v) {
    var t = String(v == null ? '' : v).trim();
    if (!t) return true;
    var n = normColName(t);
    return [
      'nd', 'n d', 'n d ', 'n/d', 'n d', 'n.d', 'n.d.',
      'na', 'n a', 's d', 's/d', 'sin dato',
      'no aplica', 'none', 'null'
    ].indexOf(n) >= 0;
  }

  function preNormalizeKoboOptionsCell(s) {
    var t = String(s == null ? '' : s).trim();
    if (!t) return t;
    t = t.replace(/\s*\+\d+$/g, '');
    t = t.trim();
    if (t.length >= 2 && (t[0] === 'S' || t[0] === 's') && t.charCodeAt(1) === 0xfffd) {
      t = t[0] + 'í' + t.slice(2);
    }
    t = t.trim();
    return t;
  }

  function parseLatLonSimple(v) {
    var t = String(v == null ? '' : v).trim();
    if (!t) return ['', ''];
    var parts = t.split(/[,\s;]+/).filter(Boolean);
    if (parts.length < 2) return ['', ''];
    return [parts[0], parts[1]];
  }

  function isDateYmd(v) {
    var t = String(v == null ? '' : v).trim();
    if (!t) return true;
    return /^\d{4}-\d{2}-\d{2}(?:\s+00:00:00)?$/.test(t);
  }

  function tokenizeOptionValue(v) {
    var t = String(v == null ? '' : v).trim();
    if (!t) return [];
    var parts = t.split(/\|\|\||[,;]+/).map(function (x) { return String(x || '').trim(); }).filter(Boolean);
    return parts.length ? parts : [t];
  }

  function normalizeServiceName(v) {
    var n = normColName(v);
    if (n.indexOf('medicina') >= 0 || n.indexOf('consulta') >= 0 || n === 'medico') return 'medicina general';
    if (n.indexOf('dental') >= 0 || n.indexOf('odont') >= 0) return 'dental';
    if (n.indexOf('fisio') >= 0 || n.indexOf('rehabilit') >= 0) return 'fisioterapia';
    if (n.indexOf('oftalmo') >= 0 || n.indexOf('optica') >= 0 || n.indexOf('vision') >= 0 || n.indexOf('lentes') >= 0) return 'oftalmologia';
    if (n.indexOf('laboratorio') >= 0 || n === 'lab' || n.indexOf('examen') >= 0) return 'laboratorios';
    return n;
  }

  /** DIS + detalle: siempre editables en la hoja (la validación Kobo sigue ligada a medicina general). */
  var DISABILITY_SHEET_EDIT_ALIASES = [
    'Indicar si el paciente tiene alguna de las siguientes discapacidades',
    'Discapacidad',
    'DIS',
    'Especificar discapacidad',
    'Especificar_discapacidad'
  ];

  function colIsDisabilityBinarySubcolumn(colTitle) {
    var raw = String(colTitle || '');
    if (raw.indexOf('/') < 0) return false;
    var segs = raw.split('/').map(function (s) { return String(s || '').trim(); }).filter(Boolean);
    if (segs.length < 2) return false;
    var parent = normColName(segs.slice(0, -1).join(' '));
    if (parent.indexOf('discapacidad') < 0) return false;
    var last = normColName(segs[segs.length - 1]);
    return ['motriz', 'visual', 'auditiva', 'intelectual', 'otra'].indexOf(last) >= 0;
  }

  var MED_GENERAL_COLS = DISABILITY_SHEET_EDIT_ALIASES.concat([
    'Diagnóstico Medicina General',
    'Diagnostico Medicina General',
    'Diagnóstico Med',
    'Diagnóstico Med?',
    'Diagnósticos',
    'Diagnosticos',
    'Diagnósticos Medicina General',
    'Diagnosticos Medicina General'
  ]);
  var MED_GENERAL_COLS_FOR_CLEAR = MED_GENERAL_COLS.concat([
    'Especificar diagnóstico (Medicina General)',
    'Especificar diagnóstico',
    'Especificar Diagnóstico Medicina General',
    'Especificar Diagnostico Medicina General',
    'dxesp'
  ]);
  var MG_DIAGNOSIS_ESPECIFICAR_ALIASES = [
    'Especificar diagnóstico (Medicina General)',
    'Especificar diagnóstico',
    'Especificar Diagnóstico Medicina General',
    'Especificar Diagnostico Medicina General',
    'dxesp'
  ];
  var TREATMENT_SUGG_ALIASES = [
    'Tratamiento',
    'Tratamiento indicado',
    'Tx',
    'TX',
    'Medicamentos (Nombres específicos)',
    'Medicamentos (Nombres especificos)',
    'Medicamentos / Procedimiento',
    'Medicamentos'
  ];
  var MG_DIAGNOSIS_COLUMN_ALIASES = [
    'Diagnóstico Medicina General',
    'Diagnostico Medicina General',
    'Diagnóstico Med',
    'Diagnóstico Med?',
    'Diagnósticos',
    'Diagnosticos',
    'Diagnósticos Medicina General',
    'Diagnosticos Medicina General'
  ];
  var DENTAL_COLS = [
    'Diagnóstico Odontología',
    'Diagnostico Odontologia',
    'Diagnóstico Odo',
    'Diagnóstico Odo?',
    '¿Se realiza procedimiento odontológico?',
    'Se realiza procedimiento odontológico?',
    'Qué procedimiento se realiza',
    'Que procedimiento se realiza',
    '¿Qué procedimiento se realiza?',
    '¿Que procedimiento se realiza?',
    'Qué procedimiento',
    'Que procedimiento'
  ];
  /** Columna condicional: ¿se hizo procedimiento? (va inmediatamente antes de «Qué procedimiento…»). */
  var PROC_ODON_TRIGGER_ALIASES = [
    '¿Se realiza procedimiento odontológico?',
    'Se realiza procedimiento odontológico?',
    '¿Se realiza procedimiento odontológico? (ej. Limpieza, Extracción, Resina)'
  ];
  var QUE_PROCEDIMIENTO_DENTAL_ALIASES = [
    'Qué procedimiento se realiza',
    'Que procedimiento se realiza',
    '¿Qué procedimiento se realiza?',
    '¿Que procedimiento se realiza?',
    'Qué procedimiento',
    'Que procedimiento'
  ];
  /** Solo columnas de diagnóstico / módulo fisio (no el plan escrito, que va aparte). */
  var FISIO_COLS = [
    'Fisioterapia',
    'Diagnóstico Fisio',
    'Diagnostico Fisio',
    'Diagnóstico Fisioterapia',
    'Diagnostico Fisioterapia'
  ];
  /** Plan escrito en Kobo (Plan_de_Tratamiento): solo aplica a filas de fisioterapia. */
  var PLAN_TRATAMIENTO_FISIO_ALIASES = [
    'Plan de Tratamiento',
    'Plan de tratamiento',
    'Plan de Tratamiento (Fisioterapia u otros)',
    'Plan de tratamiento (fisioterapia u otros)',
    'Plan_de_Tratamiento'
  ];
  var MOTIVO_REF_ALIASES = [
    'Motivo Ref',
    'Motivo referencia',
    'Motivo_referencia',
    'Motivo Referido',
    'Motivo referido'
  ];
  var ESPECIFICAR_MOTIVO_REF_FISIO_LABEL = 'Especificar (motivo referido)';
  var ESPECIFICAR_MOTIVO_REF_FISIO_ALIASES = [
    ESPECIFICAR_MOTIVO_REF_FISIO_LABEL,
    'Especificar motivo referencia',
    'Especificar m. ref. fisioterapia',
    'Especificar m. ref. fisio',
    'Motivo_especificar'
  ];

  function colIsPlanTratamientoFisioColumn(colTitle) {
    if (!colTitle) return false;
    if (colIsAny(colTitle, PLAN_TRATAMIENTO_FISIO_ALIASES)) return true;
    var n = normColName(colTitle);
    if (n.indexOf('plan de tratamiento') >= 0 && n.indexOf('fisioterapia') >= 0) return true;
    if (n === 'plan de tratamiento') return true;
    return false;
  }
  var OFTALMO_COLS = [
    'Síntomas que presenta a la fecha de consulta',
    'Sintomas que presenta a la fecha de consulta',
    '¿Ha recibido algún diagnóstico previo?',
    'Ha recibido algun diagnostico previo',
    'Diagnóstico Actual',
    'Diagnostico Actual',
    'Requiere anteojos'
  ];
  var LAB_COLS = [
    'Laboratorio Clínico',
    'Laboratorio Clinico',
    'Diagnóstico / Resu',
    'Diagnostico / Resu',
    'Diagnóstico/Resu',
    'Diagnostico/Resu',
    'Diagnóstico Resultados Laboratorio',
    'Diagnostico Resultados Laboratorio'
  ];
  var ESPECIFIQUE_ENTREGA_ALIASES = [
    'Especifique qué se entrega',
    'Especifique que se entrega',
    'Especifique qué se entrega (detalle del insumo)',
    'Especifique que se entrega (detalle del insumo)',
    'Especifique_qué_se_entrega (Detalle del insumo)',
    'Especifique_que_se_entrega (Detalle del insumo)',
    'Especifique_qu_se_entrega'
  ];
  var ESPECIFICAR_ENTREGA_DETALLE_ALIASES = [
    'Especificar lo que se entrega al beneficiario',
    'Especificar lo que se entrega',
    'Especificar_lo_que_se_entrega_'
  ];
  /** Alineado con server.py _ME_ML_COLUMN_ALIASES */
  var ME_ML_ALIASES = [
    '¿Mujer embarazada o en periodo de lactancia?',
    'Mujer embarazada o en periodo de lactancia',
    '¿Embarazada / Lactancia?',
    'Embarazada / Lactancia',
    'ME_ML',
    'Embarazada o lactancia',
    'Embarazo/Lactancia',
    'Embarazo / Lactancia',
    'Embarazada/Lactancia?'
  ];

  function rowValueByAliases(row, columns, aliases) {
    if (!row || !columns || !aliases || !aliases.length) return '';
    var wanted = aliases.map(normColName).filter(Boolean);
    for (var i = 0; i < columns.length; i += 1) {
      var c = String(columns[i] || '');
      if (!c) continue;
      if (wanted.indexOf(normColName(c)) >= 0) {
        return String(row[c] == null ? '' : row[c]);
      }
    }
    return '';
  }

  function colIsAny(colName, aliases) {
    if (!aliases || !aliases.length) return false;
    var n = normColName(colName);
    for (var i = 0; i < aliases.length; i += 1) {
      if (n === normColName(aliases[i])) return true;
    }
    return false;
  }

  /** Incluye encabezados truncados en Excel, p. ej. solo «Qué procedimiento». */
  function colIsQueProcedimientoDentalColumn(colTitle) {
    if (!colTitle) return false;
    if (colIsAny(colTitle, QUE_PROCEDIMIENTO_DENTAL_ALIASES)) return true;
    var n = normColName(colTitle);
    return n === 'que procedimiento';
  }

  function yesLike(v) {
    var n = normColName(v);
    return n === 'si' || n === 'sí' || n === 'yes' || n === '1' || n === 'true';
  }

  function femaleLike(v) {
    var n = normColName(v);
    return n === 'femenino' || n === 'f' || n === 'female' || n === 'mujer' || n === '2';
  }

  function meMlEmbarazo(v) {
    var n = normColName(v);
    return n === 'embarazada' || n === 'embarazo' || n === '1';
  }

  function meMlLactancia(v) {
    var n = normColName(v);
    return n === 'lactancia' || n === '2 1' || n === '2_1';
  }

  function meMlNoAplica(v) {
    var n = normColName(v);
    return n === 'no aplica' || n === 'noaplica' || n === '0' || n === 'na' || n === 'n a' || n === 'n/a' || n === 'n/d' || n === 'nd';
  }

  function meMlCellValueValid(v) {
    return meMlEmbarazo(v) || meMlLactancia(v) || meMlNoAplica(v);
  }

  function discapacidadOtra(v) {
    var tokens = tokenizeOptionValue(v).map(normColName);
    if (!tokens.length) tokens = [normColName(v)];
    return tokens.indexOf('5') >= 0 || tokens.indexOf('otro') >= 0 || tokens.indexOf('otra') >= 0;
  }

  function rowDiagnosisTokensIncludeOtro(diagText) {
    var tks = tokenizeOptionValue(diagText);
    for (var i = 0; i < tks.length; i += 1) {
      var n = normColName(tks[i]);
      if (n === 'otro' || n === 'otra') return true;
    }
    return false;
  }

  function getDiagnosticoMGOptionsFromSchema() {
    if (!sheetState || !sheetState.koboSchema || !sheetState.koboSchema.length) return [];
    var want = normColName('Diagnóstico Medicina General');
    for (var i = 0; i < sheetState.koboSchema.length; i += 1) {
      var it = sheetState.koboSchema[i] || {};
      if (normColName(it.label || '') !== want) continue;
      return (it.options || []).map(function (x) { return String(x || '').trim(); }).filter(Boolean);
    }
    return [];
  }

  function getNormKeyForOption(opt) {
    return normColName(String(opt || '').trim());
  }

  function buildDiagnosticoMGMappings(options) {
    var optionByNorm = {};
    var noOtro = [];
    (options || []).forEach(function (o) {
      if (!o) return;
      var k = getNormKeyForOption(o);
      if (!k || k === 'otro' || k === 'otra') return;
      optionByNorm[k] = o;
      noOtro.push(k);
    });
    var aliasMap = {
      cefaleas: 'Cefalea',
      cefalea: 'Cefalea',
      migrana: 'Cefalea',
      migraña: 'Cefalea',
      amigdalitis: 'Amigdalitis',
      otitis: 'Otitis media',
      diarrea: 'Diarrea aguda'
    };
    return { optionByNorm: optionByNorm, noOtroKeys: noOtro, aliasMap: aliasMap };
  }

  function applyDiagnosticoMGNormalizationForRow(row, columns, editedCol, rawText) {
    if (!row || !columns) return false;
    var diagCol = _pickColumnByAliases(columns, MG_DIAGNOSIS_COLUMN_ALIASES);
    if (!diagCol) return false;
    if (editedCol != null && String(editedCol) !== String(diagCol)) return false;
    var options = getDiagnosticoMGOptionsFromSchema();
    if (!options.length) return false;
    var m = buildDiagnosticoMGMappings(options);
    var espCol = _pickColumnByAliases(columns, MG_DIAGNOSIS_ESPECIFICAR_ALIASES);
    if (!espCol) return false;
    var trim = function (x) { return String(x == null ? '' : x).trim(); };
    var raw0 = rawText != null ? trim(rawText) : trim(row[diagCol]);
    if (!raw0) {
      return false;
    }
    // Mismo criterio que carga: "Otro: descripción"
    var otroLine = raw0.match(/^\s*otro\s*[:\-]\s*(.+)$/i);
    if (otroLine && otroLine[1]) {
      row[diagCol] = 'Otro';
      row[espCol] = String(otroLine[1]).trim();
      return true;
    }

    var tks = tokenizeOptionValue(raw0);
    var out = [];
    var espec = [];
    var added = {};
    for (var ti = 0; ti < tks.length; ti += 1) {
      var part = String(tks[ti] || '').trim();
      if (!part) continue;
      var n = getNormKeyForOption(part);
      if (!n) continue;
      if (n === 'otro' || n === 'otra') {
        if (!added['__otro__']) {
          added['__otro__'] = true;
          out.push('Otro');
        }
        continue;
      }
      if (m.optionByNorm[n]) {
        var v = m.optionByNorm[n];
        var u = getNormKeyForOption(v);
        if (added[u]) continue;
        added[u] = true;
        out.push(v);
        continue;
      }
      if (m.aliasMap[n] && m.optionByNorm[getNormKeyForOption(m.aliasMap[n])]) {
        var w = m.optionByNorm[getNormKeyForOption(m.aliasMap[n])];
        var u2 = getNormKeyForOption(w);
        if (added[u2]) continue;
        added[u2] = true;
        out.push(w);
        continue;
      }
      if (!added['__otro__']) {
        added['__otro__'] = true;
        out.push('Otro');
      }
      if (espec.indexOf(part) < 0) espec.push(part);
    }
    var nextDiag = out.length ? out.join('|||') : '';
    var hasOtro = out.indexOf('Otro') >= 0;
    var nextEsp;
    if (!hasOtro) {
      nextEsp = '';
    } else if (espec.length) {
      nextEsp = espec.join('|||');
    } else {
      nextEsp = trim(row[espCol]);
    }
    if (trim(row[diagCol]) === nextDiag && trim(row[espCol]) === nextEsp) {
      return false;
    }
    row[diagCol] = nextDiag;
    row[espCol] = nextEsp;
    return true;
  }

  function applyRowDefaultsByKoboRules(row, columns) {
    if (!row || !columns || !columns.length) return false;
    var changed = false;
    var specialtyAliases = {
      'medicina general': MED_GENERAL_COLS_FOR_CLEAR,
      'dental': DENTAL_COLS,
      'fisioterapia': FISIO_COLS,
      'oftalmologia': OFTALMO_COLS,
      'laboratorios': LAB_COLS
    };

    var sexVal = rowValueByAliases(row, columns, ['Sexo', 'SEX']);
    var meMlCol = _pickColumnByAliases(columns, ME_ML_ALIASES);
    if (meMlCol) {
      var meMlRaw = row[meMlCol];
      var meTrim = String(meMlRaw == null ? '' : meMlRaw).trim();
      if (!femaleLike(sexVal)) {
        if (meTrim !== '') {
          row[meMlCol] = '';
          changed = true;
        }
      } else if (!meMlCellValueValid(meMlRaw)) {
        row[meMlCol] = 'No Aplica';
        if (meTrim !== 'No Aplica') changed = true;
      }
    }

    var service = normalizeServiceName(rowValueByAliases(row, columns, [
      'Servicio que se brinda', 'Servicio', 'Especialidad', 'Servicio_que_se_brinda'
    ]));
    if (specialtyAliases[service]) {
      Object.keys(specialtyAliases).forEach(function (svcKey) {
        if (svcKey === service) return;
        var aliases = specialtyAliases[svcKey] || [];
        (columns || []).forEach(function (colName) {
          if (!colIsAny(colName, aliases)) return;
          if (looksMissingValue(row[colName])) return;
          row[colName] = '';
          changed = true;
        });
      });
    }
    if (service !== 'fisioterapia') {
      (columns || []).forEach(function (cn) {
        if (!colIsPlanTratamientoFisioColumn(cn)) return;
        if (looksMissingValue(row[cn])) return;
        row[cn] = '';
        changed = true;
      });
    }
    var disVal = rowValueByAliases(row, columns, [
      'Indicar si el paciente tiene alguna de las siguientes discapacidades',
      'Discapacidad',
      'DIS'
    ]);
    var disSpecCol = _pickColumnByAliases(columns, ['Especificar discapacidad', 'Especificar_discapacidad']);
    var shouldKeepDisSpec = service === 'medicina general' && discapacidadOtra(disVal);
    if (disSpecCol && !shouldKeepDisSpec && !looksMissingValue(row[disSpecCol])) {
      row[disSpecCol] = '';
      changed = true;
    }

    var mgDcol = _pickColumnByAliases(columns, MG_DIAGNOSIS_COLUMN_ALIASES);
    var mgEcol = _pickColumnByAliases(columns, MG_DIAGNOSIS_ESPECIFICAR_ALIASES);
    if (mgDcol && mgEcol && service === 'medicina general') {
      var mgDtxt = String(row[mgDcol] == null ? '' : row[mgDcol]).trim();
      if (!rowDiagnosisTokensIncludeOtro(mgDtxt) && !looksMissingValue(row[mgEcol])) {
        row[mgEcol] = '';
        changed = true;
      }
    }

    var espEntregaCol = _pickColumnByAliases(columns, ESPECIFIQUE_ENTREGA_ALIASES);
    var espEntregaDetalleCol = _pickColumnByAliases(columns, ESPECIFICAR_ENTREGA_DETALLE_ALIASES);
    if (espEntregaCol && espEntregaDetalleCol) {
      if (!rowEspecifiqueEntregaIsOtro(row, columns) && !looksMissingValue(row[espEntregaDetalleCol])) {
        row[espEntregaDetalleCol] = '';
        changed = true;
      }
    }

    var motEspCol = _pickColumnByAliases(columns, ESPECIFICAR_MOTIVO_REF_FISIO_ALIASES);
    if (motEspCol && !shouldEnableEspecificarMotivoRefFisioCell(row, columns) && !looksMissingValue(row[motEspCol])) {
      row[motEspCol] = '';
      changed = true;
    }

    return changed;
  }

  function shouldEnableCellByKoboRules(row, columns, colName) {
    var service = normalizeServiceName(rowValueByAliases(row, columns, [
      'Servicio que se brinda', 'Servicio', 'Especialidad', 'Servicio_que_se_brinda'
    ]));
    var sexVal = rowValueByAliases(row, columns, ['Sexo', 'SEX']);
    var refVal = rowValueByAliases(row, columns, ['Se hizo referencia', '¿Se hizo referencia?', 'Referencia', 'REF']);
    var meMlVal = rowValueByAliases(row, columns, ME_ML_ALIASES);
    var ageVal = rowValueByAliases(row, columns, ['Edad', 'AGE']);
    var ageNum = Number(String(ageVal || '').replace(',', '.'));
    var hasRef = yesLike(refVal);
    var isFemale = femaleLike(sexVal);
    var isPregnant = meMlEmbarazo(meMlVal);
    var isLactating = meMlLactancia(meMlVal);

    var referenciaCols = [
      '¿A dónde?', 'A dónde', 'A donde',
      'Especificar referencia',
      'Motivo Ref', 'Motivo Referido', 'Motivo referencia'
    ];

    // Condicionales por especialidad
    if (colIsAny(colName, DISABILITY_SHEET_EDIT_ALIASES) || colIsDisabilityBinarySubcolumn(colName)) {
      return true;
    }
    if (colIsAny(colName, MG_DIAGNOSIS_ESPECIFICAR_ALIASES) && !colIsAny(colName, ['Especificar discapacidad', 'Especificar_discapacidad', 'Especificar referencia'])) {
      if (service !== 'medicina general') return false;
      var dColEn = _pickColumnByAliases(columns, MG_DIAGNOSIS_COLUMN_ALIASES);
      if (!dColEn) return true;
      var dTxtEn = String((row && row[dColEn] != null) ? row[dColEn] : '').trim();
      return rowDiagnosisTokensIncludeOtro(dTxtEn);
    }
    if (isEspecificarEntregaBeneficiarioColumn(colName)) {
      return rowEspecifiqueEntregaIsOtro(row, columns);
    }
    if (colIsAny(colName, MED_GENERAL_COLS) && !colIsAny(colName, DISABILITY_SHEET_EDIT_ALIASES) && !colIsDisabilityBinarySubcolumn(colName)) {
      return service === 'medicina general';
    }
    if (colIsAny(colName, DENTAL_COLS)) return service === 'dental';
    if (colIsPlanTratamientoFisioColumn(colName)) return service === 'fisioterapia';
    if (colIsAny(colName, FISIO_COLS)) return service === 'fisioterapia';
    if (colIsAny(colName, OFTALMO_COLS)) return service === 'oftalmologia';
    if (colIsAny(colName, LAB_COLS)) return service === 'laboratorios';

    if (isEspecificarMotivoRefFisioColumn(colName)) {
      return shouldEnableEspecificarMotivoRefFisioCell(row, columns);
    }

    // Referencias: "Motivo Ref", "A dónde", etc. si hay referencia; también aplica a fisioterapia
    if (colIsAny(colName, ['Se hizo referencia', '¿Se hizo referencia?', 'Referencia', 'REF'])) {
      return true;
    }
    if (colIsAny(colName, referenciaCols)) {
      return hasRef;
    }

    // Embarazo / lactancia y suplementos
    if (colIsAny(colName, ME_ML_ALIASES)) {
      return isFemale;
    }
    if (colIsAny(colName, ['Suplemento hierro', 'FE'])) {
      return isPregnant || isLactating;
    }
    if (colIsAny(colName, ['Suplemento ácido fólico', 'Suplemento acido folico', 'FA'])) {
      return isPregnant;
    }

    // Acompañante en menores
    if (colIsAny(colName, ['Acompañante', 'Acompanante', 'CGR'])) {
      if (isNaN(ageNum)) return true;
      return ageNum < 18;
    }

    return true;
  }

  function isRuleTriggerColumn(colName) {
    if (colIsAny(colName, ME_ML_ALIASES)) return true;
    if (colIsAny(colName, DISABILITY_SHEET_EDIT_ALIASES) || colIsDisabilityBinarySubcolumn(colName)) return true;
    if (colIsAny(colName, [
      'Toma de consentimiento antes de iniciar la consulta',
      'Toma consentimiento inicial',
      'CONS1',
      '¿Se tomó consentimiento informado de forma verbal?',
      'Se tomó consentimiento informado de forma verbal',
      'CONS',
      'Consentimiento informado verbal'
    ])) return true;
    return colIsAny(colName, [
      'Servicio que se brinda', 'Servicio', 'Especialidad', 'Servicio_que_se_brinda',
      'Sexo', 'SEX',
      'Se hizo referencia', '¿Se hizo referencia?', 'Referencia', 'REF',
      'Motivo Ref', 'Motivo referencia', 'Motivo_referencia', 'Motivo Referido', 'Motivo referido',
      'Especificar (motivo referido)', 'Especificar motivo referencia', 'Motivo_especificar',
      'Edad', 'AGE',
      'Diagnóstico Medicina General', 'Diagnostico Medicina General',
      'Diagnósticos', 'Diagnosticos', 'Diagnósticos Medicina General', 'Diagnosticos Medicina General',
      'Especificar diagnóstico (Medicina General)', 'Especificar diagnóstico',
      'Especificar Diagnóstico Medicina General', 'Especificar Diagnostico Medicina General', 'dxesp',
      'Especifique qué se entrega', 'Especifique que se entrega',
      'Especifique qué se entrega (detalle del insumo)', 'Especifique que se entrega (detalle del insumo)', 'Especifique_qu_se_entrega',
      'Especificar lo que se entrega al beneficiario', 'Especificar lo que se entrega', 'Especificar_lo_que_se_entrega_'
    ]);
  }

  function _ensureColumnsPresentInSheetState(labels) {
    if (!sheetState || !sheetState.columns || !sheetState.rows || !labels || !labels.length) return false;
    var existing = {};
    (sheetState.columns || []).forEach(function (c) { existing[normColName(c)] = true; });

    function schemaAliasesForLabel(label) {
      var out = [String(label || '')];
      if (!sheetState || !sheetState.koboSchema || !sheetState.koboSchema.length) return out;
      var target = normColName(label);
      for (var i = 0; i < sheetState.koboSchema.length; i += 1) {
        var it = sheetState.koboSchema[i] || {};
        var labelKey = normColName(it.label || '');
        if (labelKey !== target) continue;
        var aliases = (it.aliases || []).slice();
        aliases.push(it.label || '');
        aliases.forEach(function (a) {
          var t = String(a || '').trim();
          if (!t) return;
          if (out.map(normColName).indexOf(normColName(t)) < 0) out.push(t);
        });
        break;
      }
      return out;
    }

    function alreadyPresentByAlias(label) {
      var aliases = schemaAliasesForLabel(label);
      for (var i = 0; i < aliases.length; i += 1) {
        if (existing[normColName(aliases[i])]) return true;
      }
      return false;
    }

    var added = [];
    labels.forEach(function (label) {
      var key = normColName(label);
      if (!key || existing[key]) return;
      if (alreadyPresentByAlias(label)) return;
      existing[key] = true;
      sheetState.columns.push(label);
      added.push(label);
    });
    if (!added.length) return false;
    sheetState.rows.forEach(function (row) {
      if (!row) return;
      added.forEach(function (c) {
        if (row[c] == null) row[c] = '';
      });
    });
    return true;
  }

  function ensureColumnsForServicesInSheet() {
    if (!sheetState || !sheetState.columns || !sheetState.rows) return false;
    var serviceCol = _pickColumnByAliases(sheetState.columns, ['Servicio que se brinda', 'Servicio', 'Especialidad', 'Servicio_que_se_brinda']);
    if (!serviceCol) return false;
    var needed = [];
    sheetState.rows.forEach(function (row) {
      var service = normalizeServiceName(row && row[serviceCol]);
      if (service === 'medicina general') {
        needed.push('Padecimiento médico actual');
        needed.push('Indicar si el paciente tiene alguna de las siguientes discapacidades');
        needed.push('Diagnóstico Medicina General');
        needed.push('Especificar diagnóstico (Medicina General)');
      } else if (service === 'dental') {
        needed.push('Diagnóstico Odontología');
        needed.push('¿Se realiza procedimiento odontológico?');
        needed.push('Qué procedimiento se realiza');
      } else if (service === 'fisioterapia') {
        needed.push('Fisioterapia');
        needed.push('Plan de Tratamiento');
      } else if (service === 'oftalmologia') {
        needed.push('Síntomas que presenta a la fecha de consulta');
        needed.push('¿Ha recibido algún diagnóstico previo?');
        needed.push('Diagnóstico Actual');
        needed.push('Requiere anteojos');
      } else if (service === 'laboratorios') {
        needed.push('Laboratorio Clínico');
        needed.push('Diagnóstico / Resu');
        needed.push('Diagnóstico Resultados Laboratorio');
      }
    });
    return _ensureColumnsPresentInSheetState(needed);
  }

  function hasDataInColumn(colName, rows) {
    if (!rows || !rows.length) return false;
    for (var i = 0; i < rows.length; i += 1) {
      var v = rows[i] && rows[i][colName];
      if (!looksMissingValue(v)) return true;
    }
    return false;
  }

  function _specialtyKeyForColumn(colName) {
    if (colIsAny(colName, [
      'Especificar diagnóstico (Medicina General)', 'Especificar diagnóstico',
      'Especificar Diagnóstico Medicina General', 'Especificar Diagnostico Medicina General', 'dxesp'
    ]) && !colIsAny(colName, [
      'Especificar (nacionalidad)', 'Especificar discapacidad', 'Especificar_discapacidad', 'Especificar referencia',
      'Especificar lo que se entrega al beneficiario', 'Especificar lo que se entrega', 'Especificar_lo_que_se_entrega_',
      'NATOT', 'Nacionalidad (especificar)'
    ])) {
      return 'medicina general';
    }
    if (colIsAny(colName, MED_GENERAL_COLS)) return 'medicina general';
    if (colIsAny(colName, DENTAL_COLS)) return 'dental';
    if (colIsPlanTratamientoFisioColumn(colName)) return 'fisioterapia';
    if (isEspecificarMotivoRefFisioColumn(colName)) return 'fisioterapia';
    if (colIsAny(colName, FISIO_COLS)) return 'fisioterapia';
    if (colIsAny(colName, OFTALMO_COLS)) return 'oftalmologia';
    if (colIsAny(colName, LAB_COLS)) return 'laboratorios';
    return '';
  }

  function servicesPresentInSheet(rows, columns) {
    var out = {};
    if (!rows || !columns) return out;
    var serviceCol = _pickColumnByAliases(columns, ['Servicio que se brinda', 'Servicio', 'Especialidad', 'Servicio_que_se_brinda']);
    if (!serviceCol) return out;
    rows.forEach(function (row) {
      var key = normalizeServiceName(row && row[serviceCol]);
      if (key) out[key] = true;
    });
    return out;
  }

  function normalizeStateName(v) {
    var n = normColName(v);
    if (!n) return '';
    if (n.indexOf('baja california sur') >= 0 || n === 'bcs') return 'baja california sur';
    if (n.indexOf('baja california') >= 0 && n.indexOf('sur') < 0) return 'baja california';
    if (n.indexOf('nuevo leon') >= 0) return 'nuevo leon';
    if (n.indexOf('sonora') >= 0) return 'sonora';
    if (n.indexOf('chihuahua') >= 0) return 'chihuahua';
    if (n.indexOf('otro') >= 0) return 'otro';
    return '';
  }

  function statesPresentInSheet(rows, columns) {
    var out = {};
    if (!rows || !columns) return out;
    var stateCol = _pickColumnByAliases(columns, [
      'Estado',
      'Estado brigada',
      'Estado_brigada',
      'Estado de brigada'
    ]);
    if (!stateCol) return out;
    (rows || []).forEach(function (row) {
      var key = normalizeStateName(row && row[stateCol]);
      if (key) out[key] = true;
    });
    return out;
  }

  function lugarAtencionColumnStateKey(colName) {
    var raw = String(colName || '').trim();
    if (!raw) return '';
    var n = normColName(raw);
    if (n.indexOf('lugar de atencion') !== 0) return '';
    var suffix = n.replace(/^lugar de atencion\s*:?\s*/, '').trim();
    return normalizeStateName(suffix);
  }

  function isAlwaysVisibleLugarAtencionColumn(colName) {
    return lugarAtencionColumnStateKey(colName) === 'otro';
  }

  function isLugarAtencionColumn(colName) {
    var n = normColName(colName);
    if (!n) return false;
    return n === 'lugar de atencion' || n.indexOf('lugar de atencion ') === 0;
  }

  function isTreatmentSourceColumn(colName) {
    var n = normColName(colName);
    if (!n) return false;
    if ([
      'medicamento',
      'medicamentos',
      'medicamentos no especificos',
      'insumos entregados',
      'insumos entregados categoria general',
      'insumos entregados categoria'
    ].indexOf(n) >= 0) return true;
    if (n.indexOf('insumos entregados') >= 0) return true;
    if (n.indexOf('medicamentos no') >= 0) return true;
    if (n.indexOf('medicamento no') >= 0) return true;
    return false;
  }

  function isEspecificarEntregaBeneficiarioColumn(colName) {
    return colIsAny(colName, ESPECIFICAR_ENTREGA_DETALLE_ALIASES);
  }

  function rowEspecifiqueEntregaIsOtro(row, columns) {
    if (!row) return false;
    var esp = _pickColumnByAliases(columns, ESPECIFIQUE_ENTREGA_ALIASES);
    if (!esp) return false;
    var raw = preNormalizeKoboOptionsCell(String(row[esp] == null ? '' : row[esp]).trim());
    return normColName(raw) === 'otro';
  }

  function anyRowEspecifiqueEntregaIsOtro(rows, columns) {
    if (!rows || !rows.length) return false;
    for (var i = 0; i < rows.length; i += 1) {
      if (rowEspecifiqueEntregaIsOtro(rows[i], columns)) return true;
    }
    return false;
  }

  function shouldShowEspecificarEntregaBeneficiarioColumn(colName, columns, rows) {
    if (!isEspecificarEntregaBeneficiarioColumn(colName)) return true;
    if (anyRowEspecifiqueEntregaIsOtro(rows, columns)) return true;
    return hasDataInColumn(colName, rows);
  }

  function isEspecificarMotivoRefFisioColumn(colName) {
    return colIsAny(colName, ESPECIFICAR_MOTIVO_REF_FISIO_ALIASES);
  }

  function rowMotivoRefIsOtro(row, columns) {
    if (!row) return false;
    var mcol = _pickColumnByAliases(columns, MOTIVO_REF_ALIASES);
    if (!mcol) return false;
    var raw = String((row[mcol] == null ? '' : row[mcol]) || '').trim();
    if (!raw) return false;
    return rowDiagnosisTokensIncludeOtro(raw) || normColName(raw) === 'otro';
  }

  function shouldEnableEspecificarMotivoRefFisioCell(row, columns) {
    var service = normalizeServiceName(rowValueByAliases(row, columns, [
      'Servicio que se brinda', 'Servicio', 'Especialidad', 'Servicio_que_se_brinda'
    ]));
    if (service !== 'fisioterapia') return false;
    var refVal = rowValueByAliases(row, columns, [
      'Se hizo referencia', '¿Se hizo referencia?', 'Referencia', 'REF'
    ]);
    if (!yesLike(refVal)) return false;
    return rowMotivoRefIsOtro(row, columns);
  }

  function anyRowEspecificarMotivoRefFisioNeeded(rows, columns) {
    if (!rows || !rows.length) return false;
    for (var i = 0; i < rows.length; i += 1) {
      if (shouldEnableEspecificarMotivoRefFisioCell(rows[i], columns)) return true;
    }
    return false;
  }

  function shouldShowEspecificarMotivoRefFisioColumn(colName, columns, rows) {
    if (!isEspecificarMotivoRefFisioColumn(colName)) return true;
    if (anyRowEspecificarMotivoRefFisioNeeded(rows, columns)) return true;
    return hasDataInColumn(colName, rows);
  }

  function ensureEspecificarMotivoRefFisioColumn() {
    if (!sheetState || !sheetState.columns || !sheetState.rows) return false;
    if (!anyRowEspecificarMotivoRefFisioNeeded(sheetState.rows, sheetState.columns)) return false;
    var cols = sheetState.columns;
    var afterKey = _pickColumnByAliases(cols, MOTIVO_REF_ALIASES);
    if (!afterKey) return false;
    var espKey = _pickColumnByAliases(cols, ESPECIFICAR_MOTIVO_REF_FISIO_ALIASES);
    if (espKey) {
      var aIdx = (function () {
        for (var i = 0; i < cols.length; i += 1) {
          if (normColName(cols[i]) === normColName(afterKey)) return i;
        }
        return -1;
      }());
      var eIdx = (function () {
        for (var j = 0; j < cols.length; j += 1) {
          if (normColName(cols[j]) === normColName(espKey)) return j;
        }
        return -1;
      }());
      if (aIdx < 0 || eIdx < 0) return false;
      if (eIdx === aIdx + 1) return false;
      var colName = cols.splice(eIdx, 1)[0];
      if (eIdx < aIdx) aIdx -= 1;
      cols.splice(aIdx + 1, 0, colName);
      if (sheetState.colWidths) sheetState.colWidths = {};
      return true;
    }
    var tIdx = (function () {
      for (var k = 0; k < cols.length; k += 1) {
        if (normColName(cols[k]) === normColName(afterKey)) return k;
      }
      return -1;
    }());
    if (tIdx < 0) return false;
    cols.splice(tIdx + 1, 0, ESPECIFICAR_MOTIVO_REF_FISIO_LABEL);
    (sheetState.rows || []).forEach(function (row) {
      if (!row) return;
      if (row[ESPECIFICAR_MOTIVO_REF_FISIO_LABEL] == null) row[ESPECIFICAR_MOTIVO_REF_FISIO_LABEL] = '';
    });
    if (sheetState.colWidths) sheetState.colWidths = {};
    return true;
  }

  var ESPECIFICAR_ENTREGA_BENEFICIARIO_LABEL = 'Especificar lo que se entrega al beneficiario';

  /**
   * Asegura la columna de detalle; va justo a la derecha de «Especifique qué/… (detalle del insumo)».
   * Si existía al final, la mueve acorde. Devuelve true si hubo cambio.
   */
  function ensureEspecificarEntregaBeneficiarioColumn() {
    if (!sheetState || !sheetState.columns || !sheetState.rows) return false;
    var cols = sheetState.columns;
    if (!anyRowEspecifiqueEntregaIsOtro(sheetState.rows, cols)) return false;

    var entregaKey = _pickColumnByAliases(cols, ESPECIFIQUE_ENTREGA_ALIASES);
    if (!entregaKey) return false;
    var eIdx = (function findIdx() {
      for (var ii = 0; ii < cols.length; ii += 1) {
        if (normColName(cols[ii]) === normColName(entregaKey)) return ii;
      }
      return -1;
    }());
    if (eIdx < 0) return false;

    var wantAfter = eIdx + 1;
    var detKey = _pickColumnByAliases(cols, ESPECIFICAR_ENTREGA_DETALLE_ALIASES);
    if (detKey) {
      var dIdx = (function findD() {
        for (var j = 0; j < cols.length; j += 1) {
          if (normColName(cols[j]) === normColName(detKey)) return j;
        }
        return -1;
      }());
      if (dIdx < 0) return false;
      if (dIdx === wantAfter) return false;
      var colName = cols.splice(dIdx, 1)[0];
      if (dIdx < eIdx) eIdx -= 1;
      eIdx = (function findE() {
        for (var k = 0; k < cols.length; k += 1) {
          if (normColName(cols[k]) === normColName(entregaKey)) return k;
        }
        return 0;
      }());
      cols.splice(eIdx + 1, 0, colName);
      if (sheetState.colWidths) sheetState.colWidths = {};
      return true;
    }
    cols.splice(eIdx + 1, 0, ESPECIFICAR_ENTREGA_BENEFICIARIO_LABEL);
    (sheetState.rows || []).forEach(function (row) {
      if (!row) return;
      if (row[ESPECIFICAR_ENTREGA_BENEFICIARIO_LABEL] == null) row[ESPECIFICAR_ENTREGA_BENEFICIARIO_LABEL] = '';
    });
    if (sheetState.colWidths) sheetState.colWidths = {};
    return true;
  }

  /**
   * Coloca «Qué procedimiento se realiza» justo a la derecha de «¿Se realiza procedimiento odontológico?».
   */
  function _pickQueProcedimientoDentalColumn(cols) {
    var k = _pickColumnByAliases(cols, QUE_PROCEDIMIENTO_DENTAL_ALIASES);
    if (k) return k;
    for (var i = 0; i < (cols || []).length; i += 1) {
      var c = String(cols[i] || '');
      if (colIsQueProcedimientoDentalColumn(c)) return c;
    }
    return '';
  }

  function ensureProcedimientoDentalAfterTriggerColumn() {
    if (!sheetState || !sheetState.columns) return false;
    var cols = sheetState.columns;
    var trigKey = _pickColumnByAliases(cols, PROC_ODON_TRIGGER_ALIASES);
    var procKey = _pickQueProcedimientoDentalColumn(cols);
    if (!trigKey || !procKey) return false;
    if (normColName(trigKey) === normColName(procKey)) return false;

    var tIdx = (function findT() {
      for (var i = 0; i < cols.length; i += 1) {
        if (normColName(cols[i]) === normColName(trigKey)) return i;
      }
      return -1;
    }());
    var pIdx = (function findP() {
      for (var j = 0; j < cols.length; j += 1) {
        if (normColName(cols[j]) === normColName(procKey)) return j;
      }
      return -1;
    }());
    if (tIdx < 0 || pIdx < 0) return false;
    var wantAfter = tIdx + 1;
    if (pIdx === wantAfter) return false;

    var colName = cols.splice(pIdx, 1)[0];
    if (pIdx < tIdx) tIdx -= 1;
    tIdx = (function findT2() {
      for (var k = 0; k < cols.length; k += 1) {
        if (normColName(cols[k]) === normColName(trigKey)) return k;
      }
      return 0;
    }());
    cols.splice(tIdx + 1, 0, colName);
    if (sheetState.colWidths) sheetState.colWidths = {};
    return true;
  }

  function visibleColumnIndexes(columns, rows) {
    if (sheetShowAllColumns) {
      var all = [];
      for (var k = 0; k < columns.length; k += 1) all.push(k);
      return all;
    }
    var presentServices = servicesPresentInSheet(rows, columns);
    var presentStates = statesPresentInSheet(rows, columns);
    var idx = [];
    for (var ci = 0; ci < columns.length; ci += 1) {
      var c = columns[ci];
      if (isTreatmentSourceColumn(c)) {
        continue;
      }
      if (isEspecificarEntregaBeneficiarioColumn(c) && !shouldShowEspecificarEntregaBeneficiarioColumn(c, columns, rows)) {
        continue;
      }
      if (isEspecificarMotivoRefFisioColumn(c) && !shouldShowEspecificarMotivoRefFisioColumn(c, columns, rows)) {
        continue;
      }
      if (isAlwaysVisibleLugarAtencionColumn(c)) {
        idx.push(ci);
        continue;
      }
      var colStateKey = lugarAtencionColumnStateKey(c);
      if (colStateKey) {
        if (presentStates[colStateKey] || hasDataInColumn(c, rows)) idx.push(ci);
        continue;
      }
      if (isLugarAtencionColumn(c) && !hasDataInColumn(c, rows)) {
        continue;
      }
      var svcKey = _specialtyKeyForColumn(c);
      if (!svcKey) {
        idx.push(ci);
        continue;
      }
      if (presentServices[svcKey] || hasDataInColumn(c, rows)) {
        idx.push(ci);
      }
    }
    return idx;
  }

  function updateSheetColumnModeButton() {
    if (!sheetToggleColumnMode) return;
    if (sheetShowAllColumns) {
      sheetToggleColumnMode.textContent = 'Mostrar solo relevantes';
      sheetToggleColumnMode.title = 'Oculta columnas de especialidades no presentes';
      sheetToggleColumnMode.classList.add('is-on');
    } else {
      sheetToggleColumnMode.textContent = 'Mostrar todas las columnas';
      sheetToggleColumnMode.title = 'Muestra todas las columnas, incluso de especialidades no presentes';
      sheetToggleColumnMode.classList.remove('is-on');
    }
  }

  function buildSimpleCheck(columns, rows, schema, aliasToLabel) {
    var requiredLabels = (schema || []).filter(function (x) { return !!x.required; }).map(function (x) { return x.label; });
    var matched = {};
    (columns || []).forEach(function (c) {
      var col = String(c || '').trim();
      if (!col) return;
      var label = aliasToLabel[normColName(col)];
      if (!label) return;
      if (!matched[label]) matched[label] = [];
      matched[label].push(col);
    });

    var missingRequiredColumns = requiredLabels.filter(function (lbl) { return !(matched[lbl] && matched[lbl].length); });
    var rowsMissing = [];
    (rows || []).forEach(function (row, idx) {
      var missing = [];
      requiredLabels.forEach(function (lbl) {
        var cols = matched[lbl] || [];
        var ok = cols.some(function (c) { return !looksMissingValue(row && row[c]); });
        if (!ok) missing.push(lbl);
      });
      if (missing.length) {
        rowsMissing.push({ row_index: idx, excel_row: idx + 2, missing_labels: missing });
      }
    });

    var findCol = function (aliases) {
      var wanted = aliases.map(normColName).filter(Boolean);
      for (var i = 0; i < (columns || []).length; i += 1) {
        var c = String(columns[i] || '');
        if (wanted.indexOf(normColName(c)) >= 0) return c;
      }
      return '';
    };

    var dateRows = [];
    var dateCol = findCol(['Fecha de atención', 'Fecha_de_atenci_n', 'Fecha', 'Fecha Atención', 'Fecha atencion']);
    if (dateCol) {
      (rows || []).forEach(function (row, idx) {
        var v = String((row && row[dateCol]) || '').trim();
        if (v && !isDateYmd(v)) dateRows.push(idx + 2);
      });
    }

    var coordinatesRows = [];
    var coordsCol = findCol(['Coordenadas', 'Ubicación geográfica de la atención', 'Ubicaci_n_geogr_fica_de_la_atenci_n']);
    if (coordsCol) {
      (rows || []).forEach(function (row, idx) {
        var v = String((row && row[coordsCol]) || '').trim();
        if (!v) return;
        var ll = parseLatLonSimple(v);
        if (!ll[0] || !ll[1]) coordinatesRows.push(idx + 2);
      });
    }

    var referenceDestinationRows = [];
    var refCol = findCol(['Se hizo referencia', '¿Se hizo referencia?', 'Referencia']);
    var whereCol = findCol(['A dónde', 'A donde', '¿A dónde?', 'Referencia_donde']);
    if (refCol && whereCol) {
      (rows || []).forEach(function (row, idx) {
        var refVal = normColName(preNormalizeKoboOptionsCell((row && row[refCol]) || ''));
        if (refVal === 'si' || refVal === 'sí') {
          if (looksMissingValue(row && row[whereCol])) referenceDestinationRows.push(idx + 2);
        }
      });
    }

    var fisioMotivoRefDetailRows = [];
    var motivoRefColB = findCol(MOTIVO_REF_ALIASES);
    var motEspColB = findCol(ESPECIFICAR_MOTIVO_REF_FISIO_ALIASES);
    var serviceColB = findCol(['Servicio que se brinda', 'Servicio', 'Especialidad', 'Servicio_que_se_brinda']);
    if (refCol && motivoRefColB && serviceColB && motEspColB) {
      (rows || []).forEach(function (row, idx) {
        var rawSvc = String((row && row[serviceColB]) || '').trim();
        if (!rawSvc || normalizeServiceName(rawSvc) !== 'fisioterapia') return;
        var refVal3 = normColName(preNormalizeKoboOptionsCell((row && row[refCol]) || ''));
        if (refVal3 !== 'si' && refVal3 !== 'sí') return;
        var mRaw = String((row && row[motivoRefColB]) || '').trim();
        if (!mRaw) return;
        var isOtro = rowDiagnosisTokensIncludeOtro(mRaw) || normColName(mRaw) === 'otro';
        if (!isOtro) return;
        if (looksMissingValue(row && row[motEspColB])) fisioMotivoRefDetailRows.push(idx + 2);
      });
    }

    var invalidOptionRows = [];
    var refColForOptions = findCol(['Se hizo referencia', '¿Se hizo referencia?', 'Referencia']);
    var preferredColumnsForLabel = function (label, colsForLabel) {
      var target = normColName(label);
      var exact = (colsForLabel || []).filter(function (c) { return normColName(c) === target; });
      if (exact.length) return exact.slice(0, 1);
      return colsForLabel || [];
    };
    (schema || []).forEach(function (item) {
      var options = (item && item.options) || [];
      if (!options.length) return;
      var label = String(item.label || '').trim();
      if (!label) return;
      var colsForLabel = matched[label] || [];
      if (!colsForLabel.length) return;
      colsForLabel = preferredColumnsForLabel(label, colsForLabel);
      var validSet = {};
      options.forEach(function (op) {
        var key = normColName(op);
        if (key) validSet[key] = true;
      });
      colsForLabel.forEach(function (col) {
        var badRows = [];
        (rows || []).forEach(function (row, idx) {
          // Regla condicional: "A dónde" solo se valida cuando "Se hizo referencia?" = Sí.
          if (normColName(col) === normColName('A dónde') && refColForOptions) {
            var refVal2 = normColName(preNormalizeKoboOptionsCell((row && row[refColForOptions]) || ''));
            if (!(refVal2 === 'si' || refVal2 === 'sí')) return;
          }
          var raw = preNormalizeKoboOptionsCell(String((row && row[col]) || '').trim());
          if (looksMissingValue(raw)) return;
          var tokens = tokenizeOptionValue(raw);
          if (!tokens.length) return;
          var bad = tokens.some(function (tk) { return !validSet[normColName(tk)]; });
          if (bad) badRows.push(idx + 2);
        });
        if (badRows.length) {
          invalidOptionRows.push({
            label: label,
            column: col,
            rows: badRows.slice(0, 20),
            count: badRows.length
          });
        }
      });
    });

    var serviceLabelByKey = {
      'medicina general': 'Medicina General',
      'dental': 'Dental',
      'fisioterapia': 'Fisioterapia',
      'oftalmologia': 'Oftalmología',
      'laboratorios': 'Laboratorios'
    };
    var serviceConditional = {
      'medicina general': ['Diagnóstico Medicina General'],
      'dental': ['Diagnóstico Odontología'],
      'fisioterapia': ['Fisioterapia', 'Plan de Tratamiento'],
      'oftalmologia': [
        'Síntomas que presenta a la fecha de consulta',
        '¿Ha recibido algún diagnóstico previo?',
        'Diagnóstico Actual'
      ],
      'laboratorios': ['Laboratorio Clínico', 'Diagnóstico / Resu']
    };
    var serviceMissing = [];
    var serviceCol = findCol(['Servicio que se brinda', 'Servicio', 'Especialidad', 'Servicio_que_se_brinda']);
    if (serviceCol) {
      var present = {};
      (rows || []).forEach(function (row) {
        var val = String((row && row[serviceCol]) || '').trim();
        if (!val) return;
        var key = normalizeServiceName(val);
        if (serviceConditional[key]) present[key] = true;
      });
      Object.keys(present).forEach(function (svcKey) {
        var expected = serviceConditional[svcKey] || [];
        var missing = expected.filter(function (lbl) {
          if (normColName(lbl) === normColName('Diagnóstico Medicina General')) {
            return !(columns || []).some(function (c) {
              return colIsAny(c, [
                'Diagnóstico Medicina General', 'Diagnostico Medicina General', 'Diagnóstico Med', 'Diagnóstico Med?',
                'Diagnósticos', 'Diagnosticos', 'Diagnósticos Medicina General', 'Diagnosticos Medicina General'
              ]);
            });
          }
          if (matched[lbl] && matched[lbl].length) return false;
          var nk = normColName(lbl);
          return !(columns || []).some(function (c) { return normColName(c) === nk; });
        });
        if (missing.length) {
          serviceMissing.push({
            service: serviceLabelByKey[svcKey] || svcKey,
            missing_columns: missing
          });
        }
      });
    }

    var ready = (
      missingRequiredColumns.length === 0
      && rowsMissing.length === 0
      && dateRows.length === 0
      && coordinatesRows.length === 0
      && invalidOptionRows.length === 0
      && referenceDestinationRows.length === 0
      && fisioMotivoRefDetailRows.length === 0
      && serviceMissing.length === 0
    );

    return {
      ready_to_submit: ready,
      missing_required_columns: missingRequiredColumns,
      rows_with_missing_required: {
        count: rowsMissing.length,
        sample: rowsMissing.slice(0, 20)
      },
      invalid_formats: {
        date_rows: dateRows.slice(0, 30),
        coordinates_rows: coordinatesRows.slice(0, 30),
        option_rows: invalidOptionRows.slice(0, 20),
        reference_destination_rows: referenceDestinationRows.slice(0, 30),
        fisio_motivo_ref_detail_rows: fisioMotivoRefDetailRows.slice(0, 30)
      },
      service_conditional_missing: serviceMissing,
      human_message: ready ? 'Listo para enviar a Kobo.' : 'Faltan datos por corregir antes de enviar a Kobo.'
    };
  }

  function computeColumnsCheckFromSchema(columns, schema, rows, previousCheck) {
    var aliasToLabel = {};
    (schema || []).forEach(function (item) {
      var label = String(item.label || '').trim();
      if (!label) return;
      var aliases = (item.aliases || []).slice();
      aliases.push(label);
      aliases.forEach(function (a) {
        var k = normColName(a);
        if (k && !aliasToLabel[k]) aliasToLabel[k] = label;
      });
    });
    var headerNormToLabel = {
      'toma de consentimiento antes de iniciar la consulta': 'Toma de consentimiento antes de iniciar la consulta',
      'pertenece a alguna minora etnica': 'Minoría',
      'originario': 'Estado',
      'motivo referido': 'Motivo Ref',
      'laboratorio clinico': 'Laboratorio Clínico',
      'coordenadas': 'Coordenadas'
    };
    var requiredLabels = (schema || []).filter(function (x) { return !!x.required; }).map(function (x) { return x.label; });
    var matched = {};
    var unknown = [];
    var suggestions = {};
    var aliasKeys = Object.keys(aliasToLabel);

    (columns || []).forEach(function (c) {
      var col = String(c || '').trim();
      if (!col) return;
      var key = normColName(col);
      var direct = headerNormToLabel[key];
      var label = direct || aliasToLabel[key];
      if (label) {
        if (!matched[label]) matched[label] = [];
        matched[label].push(col);
      } else {
        unknown.push(col);
        var best = null;
        var bestScore = 0;
        aliasKeys.forEach(function (k) {
          var score = 0;
          if (k === key) score = 1;
          else if (k.indexOf(key) >= 0 || key.indexOf(k) >= 0) score = 0.86;
          else {
            var parts = key.split(' ');
            var hits = 0;
            parts.forEach(function (p) { if (p && k.indexOf(p) >= 0) hits += 1; });
            score = parts.length ? hits / parts.length : 0;
          }
          if (score > bestScore) { bestScore = score; best = k; }
        });
        if (best && bestScore >= 0.86) {
          var suggL = aliasToLabel[best];
          var nsL = normColName(suggL);
          if (key.indexOf('inici') >= 0 && nsL.indexOf('verbal') >= 0) { /* no cruzar CONS1 vs CONS */ }
          else if (key.indexOf('verbal') >= 0 && nsL.indexOf('inici') >= 0) { }
          else {
            suggestions[col] = suggL;
          }
        }
      }
    });

    var missing = requiredLabels.filter(function (l) { return !matched[l]; });
    var dups = [];
    Object.keys(matched).forEach(function (lbl) {
      if (matched[lbl].length > 1) dups.push({ label: lbl, columns: matched[lbl] });
    });
    return {
      ok_required: missing.length === 0,
      required_total: requiredLabels.length,
      required_present: requiredLabels.length - missing.length,
      missing_required_columns: missing,
      unknown_columns: unknown,
      duplicates: dups,
      rename_suggestions: suggestions,
      simple_check: buildSimpleCheck(columns || [], rows || [], schema || [], aliasToLabel),
      kobo_schema_source: previousCheck && previousCheck.kobo_schema_source ? previousCheck.kobo_schema_source : ''
    };
  }

  function renderSheetColumnsCheck() {
    if (!sheetColumnsCheck) return;
    if (!sheetState || !sheetState.columnsCheck) {
      sheetColumnsCheck.style.display = 'none';
      sheetColumnsCheck.innerHTML = '';
      if (sheetApplySuggestions) sheetApplySuggestions.style.display = 'none';
      return;
    }
    var cc = sheetState.columnsCheck;
    var missing = cc.missing_required_columns || [];
    var unknown = cc.unknown_columns || [];
    var dups = cc.duplicates || [];
    var sugg = cc.rename_suggestions || {};
    var suggCount = Object.keys(sugg).length;
    var sc = cc.simple_check || {};
    var rowsMiss = (sc.rows_with_missing_required && sc.rows_with_missing_required.count) || 0;
    var rowsSample = (sc.rows_with_missing_required && sc.rows_with_missing_required.sample) || [];
    var invalid = sc.invalid_formats || {};
    var statusCls = sc.ready_to_submit ? 'ok' : 'warn';
    var h = '<div class="sheet-check-assistant">';
    h += '<div class="sheet-check-header-row">';
    h += '<div class="sheet-check-title-main">Antes de enviar a Kobo</div>';
    h += '<div class="sheet-check-card ' + statusCls + '">';
    h += '<div class="sheet-check-title">' + (sc.ready_to_submit ? 'Listo para enviar' : 'Faltan datos') + '</div>';
    h += '</div></div>';
    h += '<div class="sheet-check-human">' + esc(sc.human_message || '') + '</div>';

    if (missing.length) {
      h += '<div class="sheet-check-list"><strong>Corrige estas columnas obligatorias:</strong> ' + missing.map(esc).join(', ') + '</div>';
    }
    if (rowsMiss) {
      h += '<div class="sheet-check-list"><strong>Filas con datos incompletos:</strong> ' + rowsMiss + '</div>';
      if (rowsSample.length) {
        h += '<div class="sheet-check-list">Primeras filas: ' + rowsSample.slice(0, 8).map(function (r) {
          return '#'+ esc(String(r.excel_row || ''));
        }).join(', ') + '</div>';
      }
    }
    if (invalid.date_rows && invalid.date_rows.length) {
      h += '<div class="sheet-check-list"><strong>Formato de fecha por revisar:</strong> filas ' + invalid.date_rows.slice(0, 8).map(String).join(', ') + '</div>';
    }
    if (invalid.coordinates_rows && invalid.coordinates_rows.length) {
      h += '<div class="sheet-check-list"><strong>Coordenadas por revisar:</strong> filas ' + invalid.coordinates_rows.slice(0, 8).map(String).join(', ') + '</div>';
    }
    if (invalid.option_rows && invalid.option_rows.length) {
      h += '<div class="sheet-check-list"><strong>Valores fuera de catálogo:</strong> '
        + invalid.option_rows.slice(0, 4).map(function (it) {
          var rs = (it.rows || []).slice(0, 4).map(String).join(', ');
          return esc(String(it.label || it.column || 'Campo')) + ' (filas ' + esc(rs || '...') + ')';
        }).join(' · ')
        + '</div>';
    }
    if (invalid.reference_destination_rows && invalid.reference_destination_rows.length) {
      h += '<div class="sheet-check-list"><strong>Falta "¿A dónde?" cuando "¿Se hizo referencia?" = Sí:</strong> filas '
        + invalid.reference_destination_rows.slice(0, 10).map(String).join(', ')
        + '</div>';
    }
    if (invalid.fisio_motivo_ref_detail_rows && invalid.fisio_motivo_ref_detail_rows.length) {
      h += '<div class="sheet-check-list"><strong>Falta "Especificar (motivo referido)" en fisioterapia (referencia = Sí y «Motivo Ref» = Otro):</strong> filas '
        + invalid.fisio_motivo_ref_detail_rows.slice(0, 10).map(String).join(', ')
        + '</div>';
    }
    if (sc.service_conditional_missing && sc.service_conditional_missing.length) {
      h += '<div class="sheet-check-list"><strong>Campos por servicio:</strong> '
        + sc.service_conditional_missing.map(function (it) {
          return esc(String(it.service || 'Servicio')) + ' → ' + (it.missing_columns || []).map(esc).join(', ');
        }).join(' · ')
        + '</div>';
    }

    h += '<details class="sheet-check-advanced">';
    h += '<summary>Opciones avanzadas (soporte)</summary>';
    if (unknown.length) {
      h += '<div class="sheet-check-list"><strong>Columnas no reconocidas:</strong> ' + unknown.map(esc).join(', ') + '</div>';
    }
    if (dups.length) {
      h += '<div class="sheet-check-list"><strong>Columnas duplicadas:</strong> ' + dups.map(function (d) { return esc(d.label) + ' (' + d.columns.length + ')'; }).join(', ') + '</div>';
    }
    if (suggCount) {
      h += '<div class="sheet-check-list"><strong>Sugerencias de nombre:</strong> ' + Object.keys(sugg).slice(0, 8).map(function (k) { return '"' + esc(k) + '" → "' + esc(sugg[k]) + '"'; }).join(' · ') + '</div>';
    }
    h += '</details></div>';

    sheetColumnsCheck.innerHTML = h;
    sheetColumnsCheck.style.display = '';
    if (sheetApplySuggestions) {
      sheetApplySuggestions.style.display = suggCount ? '' : 'none';
      sheetApplySuggestions.disabled = !suggCount;
    }
  }

  function schemaInfoForColumnName(colName) {
    if (!sheetState) return null;
    if (colIsAny(colName, ME_ML_ALIASES)) {
      return {
        required: false,
        hint: 'Solo si el sexo registrado es femenino. Use: Embarazada, Lactancia o No Aplica. En sexo masculino la celda debe quedar vacía.',
        options: ['Embarazada', 'Lactancia', 'No Aplica']
      };
    }
    if (!sheetState.koboSchema) return null;
    var key = normColName(colName);
    if (!key) return null;

    // Soporta columnas derivadas como "Lugar de atención: Chihuahua"
    var baseKey = key;
    var raw = String(colName || '');
    if (raw.indexOf(':') >= 0) {
      baseKey = normColName(raw.split(':', 1)[0]);
    }

    for (var i = 0; i < sheetState.koboSchema.length; i += 1) {
      var it = sheetState.koboSchema[i];
      var aliases = (it.aliases || []).slice();
      aliases.push(it.label);
      for (var j = 0; j < aliases.length; j += 1) {
        var a = normColName(aliases[j]);
        if (a === key || (baseKey && a === baseKey)) {
          // Tooltip específico para columnas derivadas:
          // "Lugar de Atención: <Estado>"
          if (String(colName || '').indexOf(':') >= 0 && a === normColName('Lugar de atención')) {
            var suffixRaw = String(colName || '').split(':').slice(1).join(':').trim();
            var suffix = normColName(suffixRaw);
            var byState = {
              'sonora': ['Ciudad Obregón', 'Otro'],
              'nuevo leon': ['Montemorelos'],
              'baja california': [
                'Valle de la Trinidad',
                'San Matías',
                'Santa Catalina',
                'Comunidad Kiliwa',
                'Tijuana',
                'Otro'
              ],
              'baja california sur': [
                'Santa Rosalía',
                'Mulege',
                'Loreto',
                'Ciudad Constitución',
                'Vizcaíno',
                'Bahía Tortuga',
                'Bahía Asunción',
                'Punta Abreojos',
                'La Bucana',
                'Otro'
              ],
              'chihuahua': ['Ciudad Juárez', 'Otro'],
              'otro': ['Otro']
            };
            if (byState[suffix]) {
              var copy = Object.assign({}, it);
              copy.options = byState[suffix].slice();
              copy.hint = 'Opciones para "' + suffixRaw + '".';
              return copy;
            }
          }
          return it;
        }
      }
    }
    if (colIsQueProcedimientoDentalColumn(colName)) {
      return {
        required: false,
        hint: 'Opciones del formulario Kobo (puede haber varias). Si usa Otro, detalle según las notas del formulario.',
        options: ['Resina', 'Limpieza dental', 'Endodoncia', 'Extracción', 'Cirugía', 'Otro']
      };
    }
    if (colIsAny(colName, PROC_ODON_TRIGGER_ALIASES)) {
      return {
        required: false,
        hint: 'Solo odontología. Si elige Si, registre el o los procedimientos en la columna siguiente.',
        options: ['Si', 'No']
      };
    }
    return null;
  }

  function buildColumnTooltip(it) {
    if (!it) return '';
    var lines = [];
    if (it.required) lines.push('Obligatoria');
    if (it.hint) lines.push(String(it.hint));
    if (it.options && it.options.length) {
      lines.push('Opciones Kobo:');
      for (var i = 0; i < it.options.length; i += 1) {
        lines.push('- ' + String(it.options[i]));
      }
    }
    return lines.join('\n');
  }

  function clientTreatmentTextLooksIncomplete(s) {
    s = String(s == null ? '' : s).trim();
    if (!s) return true;
    if (/(\d{1,4}[\s.,]*\s*mg|\bml\b|tabs?\.?|compr(imi|imido)?|c[áa]ps?|dosis|x\s*20d)/i.test(s)) {
      return false;
    }
    return true;
  }

  function renderSheetTable() {
    if (!sheetState || !sheetTableWrap) return;
    ensureColumnsForServicesInSheet();
    ensureEspecificarEntregaBeneficiarioColumn();
    ensureEspecificarMotivoRefFisioColumn();
    ensureProcedimientoDentalAfterTriggerColumn();
    if (sheetState.koboSchema) {
      sheetState.columnsCheck = computeColumnsCheckFromSchema(
        sheetState.columns || [],
        sheetState.koboSchema,
        sheetState.rows || [],
        sheetState.columnsCheck || null
      );
      renderSheetColumnsCheck();
    } else {
      renderSheetColumnsCheck();
    }
    var cols = sheetState.columns;
    var rows = sheetState.rows;
    var visibleIdx = visibleColumnIndexes(cols, rows);
    var refColName = _pickColumnByAliases(cols, ['Se hizo referencia', '¿Se hizo referencia?', 'Referencia']);
    var whereColName = _pickColumnByAliases(cols, ['A dónde', 'A donde', '¿A dónde?', 'Referencia_donde']);
    if (sheetTitle) {
      var fn = sheetState.file && (sheetState.file.original_name || sheetState.file.stored_name) || 'Archivo';
      sheetTitle.textContent = 'Hoja: ' + fn;
    }
    if (cols.length === 0) {
      sheetTableWrap.innerHTML = '<p class="sheet-empty-hint">Añada al menos una columna con <strong>+ Columna</strong> (o cargue de nuevo si el error persistió).</p>';
      updateColRemoveOptions();
      return;
    }
    var h = '<table class="sheet-table" role="grid" aria-label="Hoja de datos del archivo"><thead><tr><th class="sheet-corner" scope="col">#</th>';
    for (var vi = 0; vi < visibleIdx.length; vi += 1) {
      var cj = visibleIdx[vi];
      var w = sheetState.colWidths && sheetState.colWidths[String(cj)] ? sheetState.colWidths[String(cj)] : 135;
      var c0 = cols[cj];
      var mapDisp = sheetState.columnDisplay && sheetState.columnDisplay[c0];
      var schemaInfo = schemaInfoForColumnName(c0);
      var tipText = buildColumnTooltip(schemaInfo);
      var reqMark = schemaInfo && schemaInfo.required ? '<span class="sheet-col-required">*</span>' : '';
      var tipIcon = tipText ? ('<span class="sheet-col-tip" data-tip="' + escAttr(tipText) + '" aria-label="Ayuda de columna">i</span>') : '';
      h += '<th class="sheet-col-h" scope="col" data-ci="' + cj + '" style="width:' + w + 'px;min-width:' + w + 'px;max-width:' + w + 'px;">'
        + reqMark
        + tipIcon;
      if (mapDisp) {
        h += '<div class="sheet-header-mapped" data-ci="' + cj + '">'
          + '<span class="sheet-header-mapped-primary" title="Nombre alineado con Kobo (solo visual)">' + esc(mapDisp) + '</span>'
          + '<span class="sheet-header-mapped-file" title="Nombre de columna en el archivo; no se cambia al guardar.">'
          + esc(c0) + '</span>'
          + '</div>';
      } else {
        h += '<input class="sheet-header-input" type="text" data-ci="' + cj + '" value="' + escAttr(c0) + '" spellcheck="false" />';
      }
      h += '<span class="sheet-col-resizer" data-ci="' + cj + '" title="Arrastre para cambiar el ancho"></span>'
        + '</th>';
    }
    h += '<th class="sheet-dummy" aria-hidden="true"></th></tr></thead><tbody>';
    if (rows.length === 0) {
      h += '<tr><td style="z-index:0" colspan="' + (cols.length + 2) + '"><p class="sheet-empty-hint" style="margin:0.5rem 0.5rem 0.5rem 1.2rem">No hay filas. Pulse <strong>+ Fila</strong> para añadir registros.</p></td></tr>';
    }
    var tColWarn = _pickColumnByAliases(cols, TREATMENT_SUGG_ALIASES);
    for (var ri = 0; ri < rows.length; ri += 1) {
      applyRowDefaultsByKoboRules(rows[ri] || {}, cols);
      var tVal = tColWarn && rows[ri] && rows[ri][tColWarn] != null ? String(rows[ri][tColWarn]) : '';
      var tInc = tColWarn ? clientTreatmentTextLooksIncomplete(tVal) : false;
      var trCls = tInc ? ' class="sheet-row-tto-warn"' : '';
      h += '<tr data-r="' + ri + '"' + trCls + '><th class="sheet-row-h" scope="row" role="rowheader" data-r="' + ri + '">#' + (ri + 1) + '<br/><button type="button" class="sheet-btn-del-row" data-r="' + ri + '" title="Quitar fila" aria-label="Quitar fila ' + (ri + 1) + '">×</button></th>';
      for (vi = 0; vi < visibleIdx.length; vi += 1) {
        cj = visibleIdx[vi];
        var cname = cols[cj];
        var cw = sheetState.colWidths && sheetState.colWidths[String(cj)] ? sheetState.colWidths[String(cj)] : 135;
        var cell = (rows[ri] && (rows[ri][cname] != null) ? String(rows[ri][cname]) : '');
        var disabledByRule = !shouldEnableCellByKoboRules(rows[ri] || {}, cols, cname);
        if (disabledByRule && cell) {
          rows[ri][cname] = '';
          cell = '';
        }
        var disAttr = disabledByRule ? ' disabled aria-disabled="true"' : '';
        var disCls = disabledByRule ? ' sheet-cell-disabled' : '';
        h += '<td style="width:' + cw + 'px;min-width:' + cw + 'px;max-width:' + cw + 'px;"><input class="sheet-cell' + disCls + '" type="text" data-r="' + ri + '" data-ci="' + cj + '" value="' + escAttr(cell) + '" spellcheck="false"' + disAttr + ' /></td>';
      }
      h += '<td class="sheet-dummy" aria-hidden="true"></td></tr>';
    }
    h += '</tbody></table>';
    sheetTableWrap.innerHTML = h;
    updateColRemoveOptions();
    paintSelection();
  }

  function rerenderSheetPreservingViewportAndFocus() {
    if (!sheetTableScroll) {
      renderSheetTable();
      return;
    }
    var prevLeft = sheetTableScroll.scrollLeft || 0;
    var prevTop = sheetTableScroll.scrollTop || 0;
    var active = document.activeElement;
    var focusMeta = null;
    if (active && active.classList && active.classList.contains('sheet-cell')) {
      var fr = active.getAttribute('data-r');
      var fc = active.getAttribute('data-ci');
      if (fr != null && fc != null) {
        focusMeta = {
          r: fr,
          c: fc,
          start: typeof active.selectionStart === 'number' ? active.selectionStart : null,
          end: typeof active.selectionEnd === 'number' ? active.selectionEnd : null
        };
      }
    }
    renderSheetTable();
    function reapplyScroll() {
      if (!sheetTableScroll) return;
      sheetTableScroll.scrollLeft = prevLeft;
      sheetTableScroll.scrollTop = prevTop;
    }
    reapplyScroll();
    if (focusMeta) {
      var nextCell = sheetTableScroll.querySelector('.sheet-cell[data-r="' + focusMeta.r + '"][data-ci="' + focusMeta.c + '"]');
      if (nextCell) {
        nextCell.focus();
        if (focusMeta.start != null && focusMeta.end != null && typeof nextCell.setSelectionRange === 'function') {
          try { nextCell.setSelectionRange(focusMeta.start, focusMeta.end); } catch (e) {}
        }
        try { nextCell.scrollIntoView({ block: 'nearest', inline: 'nearest' }); } catch (e2) {}
      }
    }
    if (window.requestAnimationFrame) {
      requestAnimationFrame(function () {
        reapplyScroll();
        if (focusMeta) {
          var n2 = sheetTableScroll.querySelector('.sheet-cell[data-r="' + focusMeta.r + '"][data-ci="' + focusMeta.c + '"]');
          if (n2) n2.focus();
        }
      });
    } else {
      setTimeout(reapplyScroll, 0);
    }
  }

  function applyConditionalStateToRenderedRow(tr) {
    if (!tr || !sheetState || !sheetState.columns || !sheetState.rows) return;
    var ri = parseInt(tr.getAttribute('data-r'), 10);
    if (isNaN(ri) || !sheetState.rows[ri]) return;
    var row = sheetState.rows[ri];
    var cols = sheetState.columns;
    applyRowDefaultsByKoboRules(row, cols);
    tr.querySelectorAll('input.sheet-cell[data-ci]').forEach(function (inp) {
      var ci = parseInt(inp.getAttribute('data-ci'), 10);
      if (isNaN(ci) || !cols[ci]) return;
      var cname = cols[ci];
      var disabledByRule = !shouldEnableCellByKoboRules(row, cols, cname);
      inp.disabled = !!disabledByRule;
      inp.setAttribute('aria-disabled', disabledByRule ? 'true' : 'false');
      inp.classList.toggle('sheet-cell-disabled', !!disabledByRule);
      if (disabledByRule && inp.value) {
        inp.value = '';
        row[cname] = '';
      } else if (!disabledByRule && row[cname] != null && inp.value !== String(row[cname])) {
        inp.value = String(row[cname]);
      }
    });
  }

  function stopSheetLockHeartbeat() {
    if (sheetLockHeartbeat) {
      clearInterval(sheetLockHeartbeat);
      sheetLockHeartbeat = null;
    }
  }

  function startSheetLockHeartbeat() {
    stopSheetLockHeartbeat();
    if (!sheetState || !sheetState.file || !sheetState.editorName) return;
    sheetUnlockSent = false;
    sheetLockHeartbeat = setInterval(function () {
      if (!sheetState || !sheetState.file || !sheetState.editorName) return;
      fetch(u('api/files/' + sheetState.file.id + '/sheet/heartbeat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ editor_name: sheetState.editorName })
      }).then(function (r) {
        return r.json().then(function (d) {
          if (!d.ok) throw new Error(d.error || 'Bloqueo perdido');
          return d;
        });
      }).catch(function () {
        // Mantener silencioso; el siguiente guardado/open detectará bloqueo.
      });
    }, 30 * 1000);
  }

  function releaseSheetLock(forceBeacon) {
    if (!sheetState || !sheetState.file || !sheetState.editorName) return;
    if (sheetUnlockSent) return;
    var payload = JSON.stringify({ editor_name: sheetState.editorName });
    var url = u('api/files/' + sheetState.file.id + '/sheet/unlock');
    if ((forceBeacon || document.visibilityState === 'hidden') && navigator.sendBeacon) {
      try {
        var blob = new Blob([payload], { type: 'application/json' });
        var sent = navigator.sendBeacon(url, blob);
        if (sent) {
          sheetUnlockSent = true;
          return;
        }
      } catch (e) {}
    }
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payload,
      keepalive: true
    }).then(function () {
      sheetUnlockSent = true;
    }).catch(function () {});
  }

  function closeSheetEditor(allowWithoutConfirm) {
    if (sheetOverlay && !allowWithoutConfirm && sheetDirty && !confirm('Hay cambios sin guardar. ¿Cerrar de todos modos?')) return;
    stopSheetGuide(false);
    hideSheetContextMenu();
    closeKoboSubmitModal();
    releaseSheetLock();
    stopSheetLockHeartbeat();
    if (sheetOverlay) sheetOverlay.style.display = 'none';
    try { document.body.style.overflow = ''; } catch (e) {}
    sheetUnlockSent = false;
    sheetState = null;
    sheetDirty = false;
    sheetSelection = null;
    sheetSelecting = false;
    if (sheetTableWrap) sheetTableWrap.innerHTML = '';
    renderSheetColumnsCheck();
    if (sheetSave) sheetSave.disabled = false;
    setSheetMsg('', '');
  }

  function openSheetEditor(id) {
    if (!sheetOverlay) return;
    if (isNaN(id) || id == null) return;
    var file = filesCache.find(function (f) { return f.id === id; });
    if (!file) return;
    if (!canOpenSheetEditor(file)) {
      if (isStubXlsName(file.stored_name)) {
        alert('Los archivos .xls (Excel antiguo) no se pueden reescribir con seguridad. Conviértalos a .xlsx, vuelva a subir el archivo, o abra y guárdelos en Excel con formato .xlsx.');
        return;
      }
      if (file.file_type === 'pdf') {
        openEditModal(String(id));
        return;
      }
    }
    sheetState = null;
    sheetUnlockSent = false;
    sheetDirty = false;
    clearSelection();
    if (sheetTableWrap) sheetTableWrap.innerHTML = '<p class="sheet-skel">Cargando hoja del servidor…</p>';
    if (sheetHint) sheetHint.textContent = 'Corrige datos, revisa el panel y pulsa "Guardar todo" para dejar el archivo actualizado.';
    setSheetMsg('Cargando…', 'info');
    var editorName = getCurrentEditorName();
    if (!editorName) {
      var asked = prompt('Para editar, escribe tu nombre (responsable):', (localStorage.getItem('koboup_name') || ''));
      editorName = (asked || '').trim();
      if (!editorName) {
        alert('Debes escribir tu nombre para abrir el editor.');
        if (inputName) inputName.focus();
        return;
      }
      if (inputName) inputName.value = editorName;
      localStorage.setItem('koboup_name', editorName);
    }
    localStorage.setItem('koboup_name', editorName);
    if (sheetOriginalName) sheetOriginalName.value = file.original_name || file.stored_name || '';
    if (sheetUploadedBy) {
      sheetUploadedBy.value = editorName;
      sheetUploadedBy.readOnly = true;
    }
    if (sheetNotes) sheetNotes.value = file.notes || '';
    updateSheetColumnModeButton();
    sheetOverlay.style.display = 'flex';
    try { document.body.style.overflow = 'hidden'; } catch (e) {}

    fetch(u('api/files/' + id + '/sheet?editor_name=' + encodeURIComponent(editorName)), { method: 'GET' })
      .then(function (r) { return r.json().then(function (d) { d._st = r.status; return d; }); })
      .then(function (d) {
        if (!d.ok) {
          if (d._st === 423) {
            throw new Error((d && d.error) || ('El archivo está siendo editado por ' + (d.locked_by || 'otro usuario')));
          }
          if (d._st === 413) throw new Error((d && d.error) || 'Archivo demasiado grande');
          if (d._st === 400) {
            if (d.error && d.error.toLowerCase().indexOf('pdf') >= 0) {
              if (sheetOverlay) sheetOverlay.style.display = 'none';
              try { document.body.style.overflow = ''; } catch (e) {}
              if (typeof openEditModal === 'function') openEditModal(String(id));
              return;
            }
            throw new Error((d && d.error) || 'No se pudo leer el archivo');
          }
          if (d._st && d._st >= 400) throw new Error((d && d.error) || 'Error al leer hoja');
        }
        if (!d.columns) d.columns = [];
        if (!d.rows) d.rows = [];
        var rows = (d.rows).map(function (r) { return Object.assign({}, r || {}); });
        sheetState = {
          file: file,
          columns: (d.columns || []).slice(),
          rows: rows,
          colWidths: {},
          editorName: editorName,
          koboSchema: d.columns_check && d.columns_check.kobo_schema ? d.columns_check.kobo_schema : null,
          columnsCheck: d.columns_check || null,
          columnDisplay: d.column_display && typeof d.column_display === 'object' ? d.column_display : {}
        };
        if (d.file) sheetState.file = d.file;
        startSheetLockHeartbeat();
        updateEditedValidatedButton();
        setSheetMsg('Listo. "Guardar todo" escribe en disco.', 'ok');
        renderSheetTable();
        try {
          if (!localStorage.getItem(SHEET_GUIDE_SEEN_KEY)) {
            setTimeout(function () { startSheetGuide(); }, 350);
          }
        } catch (e) {}
      })
      .catch(function (e) {
        if (e && e.message && e.message.toLowerCase().indexOf('siendo editado') >= 0) {
          alert(e.message);
        }
        if (e && e.message) setSheetMsg('Error: ' + e.message, 'error');
        if (sheetTableWrap) {
          sheetTableWrap.innerHTML = '<p class="sheet-skel">No se pudo cargar la hoja. Revise conexión o cierre (Esc o Cerrar).</p>';
        }
      });
  }

  async function saveSheetAll() {
    if (!sheetState) return;
    var on = (sheetOriginalName && sheetOriginalName.value || '').trim();
    if (!on) { setSheetMsg('Indique el nombre visible del archivo (obligatorio).', 'error'); if (sheetOriginalName) sheetOriginalName.focus(); return; }
    if (sheetSave) sheetSave.disabled = true;
    var editorName = getCurrentEditorName();
    if (!editorName) {
      setSheetMsg('Escribe tu nombre para guardar.', 'error');
      if (inputName) inputName.focus();
      return;
    }
    localStorage.setItem('koboup_name', editorName);
    setSheetMsg('Guardando tabla y metadatos…', 'info');
    var id = sheetState.file && sheetState.file.id;
    try {
      if (!sheetState.columns || sheetState.columns.length === 0) {
        throw new Error('Añada al menos una columna antes de guardar.');
      }
      var r1 = await fetch(u('api/files/' + id + '/sheet'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          columns: sheetState.columns,
          rows: sheetState.rows,
          original_name: on,
          notes: (sheetNotes && sheetNotes.value || '').trim(),
          editor_name: editorName
        })
      });
      var d1 = await r1.json();
      if (r1.status === 423) throw new Error((d1 && d1.error) || 'Archivo bloqueado por otro usuario');
      if (!d1.ok) throw new Error((d1 && d1.error) || 'No se pudo guardar la tabla');
      if (d1.file) sheetState.file = d1.file;
      if (d1.column_display && typeof d1.column_display === 'object') {
        sheetState.columnDisplay = d1.column_display;
      }
      if (sheetUploadedBy) sheetUploadedBy.value = editorName;
      setSheetMsg('Guardado en el servidor.', 'ok');
      if (typeof uploadMsg !== 'undefined' && uploadMsg) setMsg(uploadMsg, 'Archivo y hoja actualizados.', 'ok');
      sheetDirty = false;
      await loadFiles();
    } catch (e) {
      setSheetMsg('Error: ' + (e && e.message), 'error');
    } finally {
      if (sheetSave) sheetSave.disabled = false;
    }
  }

  function _pickColumnByAliases(cols, aliases) {
    if (!cols || !cols.length) return '';
    var al = aliases || [];
    for (var i = 0; i < cols.length; i += 1) {
      var c = String(cols[i] || '');
      if (!c) continue;
      var n = normColName(c);
      for (var j = 0; j < al.length; j += 1) {
        if (!al[j]) continue;
        if (n === normColName(String(al[j]))) return c;
      }
    }
    return '';
  }

  function pickTreatmentColumnForSheet(cols) {
    return _pickColumnByAliases(cols, TREATMENT_SUGG_ALIASES);
  }

  function buildTreatmentSuggestPayload(ri) {
    if (!sheetState || !sheetState.rows || !sheetState.rows[ri]) return null;
    var row = sheetState.rows[ri];
    var colList = sheetState.columns;
    return {
      edad: rowValueByAliases(row, colList, ['Edad', 'AGE']),
      servicio: rowValueByAliases(row, colList, [
        'Servicio que se brinda', 'Servicio', 'Especialidad', 'Servicio_que_se_brinda'
      ]),
      sexo: rowValueByAliases(row, colList, ['Sexo', 'SEX']),
      dx_espir: (
        rowValueByAliases(row, colList, MG_DIAGNOSIS_ESPECIFICAR_ALIASES) ||
        rowValueByAliases(row, colList, MG_DIAGNOSIS_COLUMN_ALIASES) ||
        ''
      ),
      tratamiento_actual: rowValueByAliases(row, colList, TREATMENT_SUGG_ALIASES) || ''
    };
  }

  function applyTreatmentSuggestion(ri, texto) {
    if (!sheetState || !sheetState.rows[ri]) return;
    var col = pickTreatmentColumnForSheet(sheetState.columns);
    if (!col) {
      if (sheetStatus) setMsg(sheetStatus, 'No se encontró columna Tratamiento. Use un encabezado alineado con Kobo (Tratamiento, medicamentos, etc.)', 'error');
      return;
    }
    sheetState.rows[ri][col] = texto;
    sheetDirty = true;
    if (sheetTreatmentPanel) sheetTreatmentPanel.style.display = 'none';
    if (sheetTreatmentList) sheetTreatmentList.innerHTML = '';
    renderSheetTable();
  }

  function loadTreatmentSuggestionsForRow(ri) {
    if (!sheetState) return;
    if (isNaN(ri) || ri < 0 || ri >= sheetState.rows.length) return;
    if (sheetTreatmentRowInfo) {
      sheetTreatmentRowInfo.textContent = 'Fila #' + (ri + 1) + (sheetTreatmentPanel ? '' : '');
    }
    if (sheetTreatmentPanel) sheetTreatmentPanel.style.display = 'block';
    if (sheetTreatmentList) sheetTreatmentList.innerHTML = '<p class="sheet-skel">Cargando sugerencias…</p>';
    var pl = buildTreatmentSuggestPayload(ri);
    if (!pl) return;
    fetch(u('api/treatment-suggestions'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        edad: pl.edad,
        servicio: pl.servicio,
        sexo: pl.sexo,
        dx_espir: pl.dx_espir,
        tratamiento_actual: pl.tratamiento_actual
      })
    })
      .then(function (r) {
        if (!r.ok) {
          return r.text().then(function (tx) { throw new Error('HTTP ' + r.status + (tx ? (': ' + tx.substring(0, 120)) : '')); });
        }
        return r.json();
      })
      .then(function (data) {
        if (sheetTreatmentRowInfo) {
          var inct = data.incompleto ? ' · tratamiento vacío o sin dosis' : '';
          sheetTreatmentRowInfo.textContent = 'Fila #' + (ri + 1) + inct;
        }
        if (sheetTreatmentCohortInfo) {
          var cg = (data.cohorte_generado != null && data.cohorte_generado) ? data.cohorte_generado : '—';
          var nfi = (data.cohorte_fila_index != null) ? data.cohorte_fila_index : 0;
          var nfa = (data.cohorte_archivo_index != null) ? data.cohorte_archivo_index : 0;
          sheetTreatmentCohortInfo.textContent = 'Cohorte indexado: ' + nfa + ' archivos / ' + nfi + ' filas con dosis · generado: ' + cg;
        }
        if (!sheetTreatmentList) return;
        if (!data || data.ok === false) {
          sheetTreatmentList.innerHTML = '<p class="sheet-treatment-err">' + esc(String((data && data.error) || 'Error al obtener sugerencias')) + '</p>';
          return;
        }
        var sugg = (data && data.suggestions) ? data.suggestions : [];
        if (!sugg.length) {
          sheetTreatmentList.innerHTML = '<p class="sheet-treatment-empty">No hay sugerencias. Reconstruya el índice: POST api/treatment-cohort/rebuild o deposite cohort_treatment_index.json. Revise pauta en dosis_referencia.json.</p>';
          return;
        }
        var h = '<ul class="sheet-treatment-ul">';
        for (var i = 0; i < sugg.length; i += 1) {
          var s = sugg[i];
          var src = s.fuente === 'pauta' ? 'Pauta editorial' : 'Cohorte (frec. en validados, no clínica)';
          var n = s.n && s.n > 0 ? 'n=' + s.n : '';
          h += '<li class="sheet-treatment-li">'
            + '<div class="sheet-treatment-txt">' + esc(String(s.texto || '')) + '</div>'
            + '<div class="sheet-treatment-meta">' + esc(src) + (n ? ' ' + n : '') + '</div>';
          h += '<button type="button" class="btn btn-sm sheet-treatment-apply" data-ri="' + ri
            + '" data-txt="' + escAttr(String(s.texto || '')) + '">Aplicar a Tratamiento</button></li>';
        }
        h += '</ul>';
        sheetTreatmentList.innerHTML = h;
        var btns2 = sheetTreatmentList.querySelectorAll('.sheet-treatment-apply');
        for (var jj = 0; jj < btns2.length; jj += 1) {
          btns2[jj].addEventListener('click', function (ev) {
            var b = ev.currentTarget;
            var r = parseInt(b.getAttribute('data-ri'), 10);
            var tx = b.getAttribute('data-txt') || '';
            applyTreatmentSuggestion(r, tx);
          });
        }
      })
      .catch(function (e) {
        if (sheetTreatmentList) {
          sheetTreatmentList.innerHTML = '<p class="sheet-treatment-err">' + esc((e && e.message) || String(e)) + '</p>';
        }
      });
  }

  function closeKoboSubmitModal() {
    if (!koboSubmitModalOverlay) return;
    if (koboSubmitBusy) return;
    koboSubmitModalOverlay.style.display = 'none';
    if (koboSubmitRows) koboSubmitRows.innerHTML = '';
    if (koboSubmitPassword) koboSubmitPassword.value = '';
    setMsg(koboSubmitMsg, '', '');
  }

  function openKoboSubmitModal() {
    if (!sheetState || !sheetState.rows || !sheetState.columns || !koboSubmitModalOverlay || !koboSubmitRows) return;
    var cols = sheetState.columns || [];
    var nameCol = _pickColumnByAliases(cols, ['Nombre del Paciente', 'Nombre', 'NAME']);
    var serviceCol = _pickColumnByAliases(cols, ['Servicio que se brinda', 'Servicio', 'Especialidad', 'Servicio_que_se_brinda']);
    var html = '';
    for (var i = 0; i < sheetState.rows.length; i += 1) {
      var row = sheetState.rows[i] || {};
      var n = nameCol ? (row[nameCol] || '') : '';
      var s = serviceCol ? (row[serviceCol] || '') : '';
      html += '<tr>'
        + '<td><input type="checkbox" class="kobo-row-check" data-row="' + i + '" /></td>'
        + '<td>#' + (i + 2) + '</td>'
        + '<td>' + esc(String(n || '—')) + '</td>'
        + '<td>' + esc(String(s || '—')) + '</td>'
        + '</tr>';
    }
    koboSubmitRows.innerHTML = html || '<tr><td colspan="4">No hay filas para enviar.</td></tr>';
    if (koboSubmitSelectAll) koboSubmitSelectAll.checked = false;
    if (koboSubmitModalFilename) {
      var fn = (sheetState.file && (sheetState.file.original_name || sheetState.file.stored_name)) || 'archivo';
      koboSubmitModalFilename.textContent = fn;
    }
    setMsg(koboSubmitMsg, '', '');
    if (koboSubmitPassword) koboSubmitPassword.value = '';
    koboSubmitModalOverlay.style.display = 'flex';
  }

  function getKoboSelectedIndices() {
    var out = [];
    if (!koboSubmitRows) return out;
    var checks = koboSubmitRows.querySelectorAll('input.kobo-row-check[data-row]');
    checks.forEach(function (ch) {
      if (!ch.checked) return;
      var idx = parseInt(ch.getAttribute('data-row'), 10);
      if (!isNaN(idx)) out.push(idx);
    });
    return out;
  }

  async function submitRowsToKoboFromModal() {
    if (!sheetState || !sheetState.file) return;
    if (koboSubmitBusy) return;
    var editorName = getCurrentEditorName();
    if (!editorName) {
      setMsg(koboSubmitMsg, 'Escribe tu nombre para continuar.', 'error');
      return;
    }
    var pwd = (koboSubmitPassword && koboSubmitPassword.value || '').trim();
    if (!pwd) {
      setMsg(koboSubmitMsg, 'Escribe la contraseña de autorización.', 'error');
      if (koboSubmitPassword) koboSubmitPassword.focus();
      return;
    }
    var selected = getKoboSelectedIndices();
    var submitAll = !!(koboSubmitSelectAll && koboSubmitSelectAll.checked);
    if (!submitAll && selected.length === 0) {
      setMsg(koboSubmitMsg, 'Selecciona al menos una fila para enviar.', 'error');
      return;
    }
    var sc = (sheetState.columnsCheck && sheetState.columnsCheck.simple_check) || null;
    if (sc && !sc.ready_to_submit) {
      var confirmMsg = 'Aún faltan correcciones en el archivo (columnas, filas incompletas o formatos).\n\n'
        + 'Si envías ahora, algunas filas pueden fallar en Kobo.\n\n'
        + '¿Deseas continuar de todas formas?';
      if (!window.confirm(confirmMsg)) {
        setMsg(koboSubmitMsg, 'Corrige los datos marcados en "Antes de enviar a Kobo" y vuelve a intentar.', 'info');
        return;
      }
    }

    koboSubmitBusy = true;
    if (koboSubmitConfirm) koboSubmitConfirm.disabled = true;
    setMsg(koboSubmitMsg, 'Enviando datos a Kobo…', 'info');
    try {
      var r = await fetch(u('api/files/' + sheetState.file.id + '/sheet/kobo-submit'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          editor_name: editorName,
          password: pwd,
          submit_all: submitAll,
          row_indices: selected,
          columns: sheetState.columns,
          rows: sheetState.rows
        })
      });
      var d = await r.json();
      if (!d.ok && !d.partial) {
        var detailErr = (d && d.error) || '';
        if (!detailErr && d && d.message) detailErr = d.message;
        if (!detailErr && d && d.errors && d.errors.length) {
          detailErr = d.errors[0].error || '';
        }
        throw new Error(detailErr || 'No se pudo enviar a Kobo');
      }
      var msg = (d && d.message) ? d.message : ('Enviadas: ' + (d.sent || 0) + ' · Con error: ' + (d.failed || 0));
      setMsg(koboSubmitMsg, msg, (d.failed ? 'info' : 'ok'));
      setSheetMsg(msg, (d.failed ? 'info' : 'ok'));
      if (!d.failed) {
        setTimeout(closeKoboSubmitModal, 500);
      }
    } catch (e) {
      setMsg(koboSubmitMsg, 'Error: ' + (e && e.message), 'error');
    } finally {
      koboSubmitBusy = false;
      if (koboSubmitConfirm) koboSubmitConfirm.disabled = false;
    }
  }

  if (sheetTableScroll) {
    if (!sheetTableScroll._sheetInit) {
      sheetTableScroll._sheetInit = true;
      var resizeState = null;

      sheetTableScroll.addEventListener('mousedown', function (e) {
        var resizer = e.target && e.target.closest('.sheet-col-resizer');
        if (resizer && sheetState) {
          e.preventDefault();
          var ci = parseInt(resizer.getAttribute('data-ci'), 10);
          if (isNaN(ci)) return;
          var th = resizer.closest('th');
          resizeState = {
            ci: ci,
            startX: e.clientX,
            startW: th ? th.getBoundingClientRect().width : 135
          };
          return;
        }

        var cell = e.target && e.target.closest('.sheet-cell');
        if (cell && sheetState) {
          var r = parseInt(cell.getAttribute('data-r'), 10);
          var c = parseInt(cell.getAttribute('data-ci'), 10);
          if (isNaN(r) || isNaN(c)) return;
          if (e.shiftKey && sheetSelection) {
            var s = normalizeSelection(sheetSelection);
            setSelection(s.r1, s.c1, r, c);
          } else {
            setSelection(r, c, r, c);
          }
          sheetSelecting = true;
          return;
        }
      });

      sheetTableScroll.addEventListener('mousemove', function (e) {
        if (!resizeState || !sheetState) return;
        var next = resizeState.startW + (e.clientX - resizeState.startX);
        lockColWidth(resizeState.ci, next);
        renderSheetTable();
      });

      document.addEventListener('mouseup', function () {
        if (resizeState) resizeState = null;
        if (sheetSelecting) sheetSelecting = false;
      });

      sheetTableScroll.addEventListener('input', function (e) {
        if (!e.target) return;
        var el = e.target;
        if (!el.classList || !el.classList.contains('sheet-cell') || !sheetState) return;
        var ri = parseInt(el.getAttribute('data-r'), 10);
        var ci = parseInt(el.getAttribute('data-ci'), 10);
        if (isNaN(ri) || isNaN(ci) || !sheetState.columns[ci]) return;
        if (!sheetState.rows[ri]) sheetState.rows[ri] = {};
        var cname = sheetState.columns[ci];
        sheetState.rows[ri][cname] = el.value;
        var changedByDefaults = applyRowDefaultsByKoboRules(sheetState.rows[ri], sheetState.columns);
        var changedByDiag = applyDiagnosticoMGNormalizationForRow(
          sheetState.rows[ri],
          sheetState.columns,
          cname,
          el.value
        );
        // Evitar re-render por tecla: actualiza estado de la fila en vivo y
        // solo re-renderiza cuando una regla realmente lo exige.
        if (changedByDiag || changedByDefaults) {
          rerenderSheetPreservingViewportAndFocus();
        } else if (colIsAny(cname, ESPECIFIQUE_ENTREGA_ALIASES)) {
          // Re-render completo solo si se inserta una columna nueva. Si no, basta ajustar la
          // fila: re-render a cada tecla reemplazaba el <input> y hacía saltar el scroll.
          if (ensureEspecificarEntregaBeneficiarioColumn()) {
            rerenderSheetPreservingViewportAndFocus();
          } else {
            var trEnt = el.closest('tr[data-r]');
            if (trEnt) applyConditionalStateToRenderedRow(trEnt);
          }
        } else if (colIsAny(cname, MOTIVO_REF_ALIASES) || colIsAny(cname, [
          'Se hizo referencia', '¿Se hizo referencia?', 'Referencia', 'REF'
        ])) {
          if (ensureEspecificarMotivoRefFisioColumn()) {
            rerenderSheetPreservingViewportAndFocus();
          } else {
            var trM = el.closest('tr[data-r]');
            if (trM) applyConditionalStateToRenderedRow(trM);
          }
        } else if (isRuleTriggerColumn(cname)) {
          var tr = el.closest('tr[data-r]');
          if (tr) applyConditionalStateToRenderedRow(tr);
        }
        sheetDirty = true;
      });

      sheetTableScroll.addEventListener('change', function (e) {
        if (!e.target) return;
        var el = e.target;
        if (!el.classList || !el.classList.contains('sheet-cell') || !sheetState) return;
        var ci = parseInt(el.getAttribute('data-ci'), 10);
        if (isNaN(ci) || !sheetState.columns[ci]) return;
        var cname = sheetState.columns[ci];
        // Recalcular habilitación/deshabilitación al confirmar cambio en columnas gatillo.
        if (isRuleTriggerColumn(cname)) {
          rerenderSheetPreservingViewportAndFocus();
        } else if (colIsAny(cname, MG_DIAGNOSIS_COLUMN_ALIASES) || colIsAny(cname, MG_DIAGNOSIS_ESPECIFICAR_ALIASES)) {
          rerenderSheetPreservingViewportAndFocus();
        }
      });

      sheetTableScroll.addEventListener('focusin', function (e) {
        var el = e.target;
        if (!el || !el.classList || !el.classList.contains('sheet-cell')) return;
        var r = parseInt(el.getAttribute('data-r'), 10);
        var c = parseInt(el.getAttribute('data-ci'), 10);
        if (isNaN(r) || isNaN(c)) return;
        if (sheetState) sheetState._lastRowFocus = r;
        if (!e.shiftKey) setSelection(r, c, r, c);
      });

      sheetTableScroll.addEventListener('mouseover', function (e) {
        if (!sheetSelecting || !sheetSelection || !sheetState) return;
        var el = e.target && e.target.closest('.sheet-cell');
        if (!el) return;
        var r = parseInt(el.getAttribute('data-r'), 10);
        var c = parseInt(el.getAttribute('data-ci'), 10);
        var s = normalizeSelection(sheetSelection);
        if (isNaN(r) || isNaN(c) || !s) return;
        setSelection(s.r1, s.c1, r, c);
      });

      sheetTableScroll.addEventListener('keydown', function (e) {
        if (!sheetState || !sheetOverlay || sheetOverlay.style.display === 'none') return;
        var isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
        var copyCombo = (isMac ? e.metaKey : e.ctrlKey) && (e.key === 'c' || e.key === 'C');
        if (copyCombo && hasSelection()) {
          e.preventDefault();
          copySelectedToClipboard();
          return;
        }
        if ((isMac ? e.metaKey : e.ctrlKey) && e.key === 'Enter' && hasSelection()) {
          var t = e.target;
          if (t && t.classList && t.classList.contains('sheet-cell')) {
            e.preventDefault();
            applySingleValueToSelection(t.value || '');
            renderSheetTable();
          }
        }
      });

      sheetTableScroll.addEventListener('paste', function (e) {
        if (!sheetState || !sheetOverlay || sheetOverlay.style.display === 'none') return;
        var text = (e.clipboardData && e.clipboardData.getData('text/plain')) || '';
        if (!text) return;
        var matrix = parseClipboardTable(text);
        if (!matrix.length) return;
        e.preventDefault();
        if (matrix.length === 1 && matrix[0].length === 1 && getSelectedCellCount() > 1) {
          applySingleValueToSelection(matrix[0][0] || '');
          renderSheetTable();
          return;
        }
        if (!hasSelection()) {
          var active = document.activeElement;
          if (active && active.classList && active.classList.contains('sheet-cell')) {
            var rr = parseInt(active.getAttribute('data-r'), 10);
            var cc = parseInt(active.getAttribute('data-ci'), 10);
            if (!isNaN(rr) && !isNaN(cc)) setSelection(rr, cc, rr, cc);
          } else if (sheetState.rows.length > 0 && sheetState.columns.length > 0) {
            setSelection(0, 0, 0, 0);
          }
        }
        pasteMatrixAtSelection(matrix);
        renderSheetTable();
      });

      sheetTableScroll.addEventListener('click', function (e) {
        var t = e.target && (e.target.closest('button.sheet-btn-del-row') || (e.target.classList && e.target.classList.contains('sheet-btn-del-row') ? e.target : null));
        if (t && sheetState) {
          e.preventDefault();
          var ri2 = parseInt(t.getAttribute('data-r'), 10);
          if (isNaN(ri2)) return;
          deleteRowAt(ri2);
          return;
        }

        var th = e.target && e.target.closest('th.sheet-col-h');
        if (th && sheetState) {
          var cSel = parseInt(th.getAttribute('data-ci'), 10);
          if (!isNaN(cSel) && sheetState.rows.length > 0) {
            setSelection(0, cSel, sheetState.rows.length - 1, cSel);
          }
          return;
        }

        var rowH = e.target && e.target.closest('th.sheet-row-h');
        if (rowH && sheetState) {
          var rSel = parseInt(rowH.getAttribute('data-r'), 10);
          if (!isNaN(rSel) && sheetState.columns.length > 0) {
            setSelection(rSel, 0, rSel, sheetState.columns.length - 1);
          }
        }
      });
      sheetTableScroll.addEventListener('contextmenu', function (e) {
        if (!sheetState || !sheetOverlay || sheetOverlay.style.display === 'none') return;
        var cell = e.target && e.target.closest('.sheet-cell');
        var colH = e.target && e.target.closest('th.sheet-col-h');
        var rowH = e.target && e.target.closest('th.sheet-row-h');
        if (!cell && !colH && !rowH) return;
        e.preventDefault();
        var ci = null;
        var ri = null;
        if (cell) {
          ri = parseInt(cell.getAttribute('data-r'), 10);
          ci = parseInt(cell.getAttribute('data-ci'), 10);
          if (!isNaN(ri) && !isNaN(ci)) setSelection(ri, ci, ri, ci);
        } else if (colH) {
          ci = parseInt(colH.getAttribute('data-ci'), 10);
          if (!isNaN(ci) && sheetState.rows.length > 0) setSelection(0, ci, sheetState.rows.length - 1, ci);
        } else if (rowH) {
          ri = parseInt(rowH.getAttribute('data-r'), 10);
          if (!isNaN(ri) && sheetState.columns.length > 0) setSelection(ri, 0, ri, sheetState.columns.length - 1);
        }
        if (isNaN(ci)) ci = null;
        if (isNaN(ri)) ri = null;
        showSheetContextMenu(e.clientX, e.clientY, { ci: ci, ri: ri });
      });
      sheetTableScroll.addEventListener('blur', function (e) {
        if (!e.target) return;
        if (!e.target.classList || !e.target.classList.contains('sheet-header-input')) return;
        onColumnHeaderBlur(e.target);
      }, true);
    }
  }
  if (sheetOriginalName) {
    sheetOriginalName.addEventListener('input', function () { if (sheetState) sheetDirty = true; });
  }
  if (sheetNotes) {
    sheetNotes.addEventListener('input', function () { if (sheetState) sheetDirty = true; });
  }
  if (sheetAddRow) {
    sheetAddRow.addEventListener('click', function () {
      if (!sheetState) return;
      if (sheetState.columns.length === 0) {
        setSheetMsg('Añada primero una columna (botón + Columna).', 'error');
        return;
      }
      sheetState.rows.push(newEmptyRow());
      sheetDirty = true;
      renderSheetTable();
    });
  }
  if (sheetAddCol) {
    sheetAddCol.addEventListener('click', function () {
      if (!sheetState) return;
      var add = uniqueNewColumnName();
      var oldCols = sheetState.columns.slice();
      if (oldCols.length >= 200) {
        setSheetMsg('Límite de 200 columnas. Divida el archivo o use otra hoja.', 'error');
        return;
      }
      sheetState.columns.push(add);
      sheetState.rows.forEach(function (r) { if (r) r[add] = ''; });
      if (oldCols.length === 0) {
        if (sheetState.rows.length === 0) {
          var nr = newEmptyRow();
          sheetState.rows = [nr];
        }
      }
      sheetDirty = true;
      renderSheetTable();
    });
  }
  if (sheetColRemoveGo) {
    sheetColRemoveGo.addEventListener('click', function () {
      if (!sheetState || !sheetColRemove) return;
      var idx = parseInt(sheetColRemove.value, 10);
      if (isNaN(idx) || idx < 0 || idx >= sheetState.columns.length) { setSheetMsg('Seleccione qué columna quitar (lista desplegable).', 'error'); return; }
      deleteColumnAt(idx);
    });
  }
  if (sheetSave) {
    sheetSave.addEventListener('click', function () { saveSheetAll(); });
  }
  if (sheetOpenGuide) {
    sheetOpenGuide.addEventListener('click', function () {
      if (!sheetState) return;
      startSheetGuide();
    });
  }
  if (sheetOpenTreatmentSuggest) {
    sheetOpenTreatmentSuggest.addEventListener('click', function () {
      if (!sheetState || !sheetState.rows || !sheetState.rows.length) {
        if (sheetStatus) setMsg(sheetStatus, 'No hay hoja cargada.', 'error');
        return;
      }
      var r = 0;
      var active = document.activeElement;
      if (active && active.classList && active.classList.contains('sheet-cell')) {
        r = parseInt(active.getAttribute('data-r'), 10);
      } else if (sheetState._lastRowFocus != null && !isNaN(sheetState._lastRowFocus)) {
        r = sheetState._lastRowFocus;
      }
      if (isNaN(r) || r < 0) r = 0;
      loadTreatmentSuggestionsForRow(r);
    });
  }
  if (sheetSubmitKobo) {
    sheetSubmitKobo.addEventListener('click', function () {
      if (!sheetState) return;
      openKoboSubmitModal();
    });
  }
  if (sheetApplySuggestions) {
    sheetApplySuggestions.addEventListener('click', function () {
      if (!sheetState || !sheetState.columnsCheck) return;
      var sugg = sheetState.columnsCheck.rename_suggestions || {};
      var keys = Object.keys(sugg);
      if (!keys.length) return;
      var renamed = 0;
      for (var i = 0; i < sheetState.columns.length; i += 1) {
        var current = sheetState.columns[i];
        var target = sugg[current];
        if (!target) continue;
        var unique = colNameAtIndexUnique(target, i);
        if (!unique || unique === current) continue;
        var oldName = sheetState.columns[i];
        sheetState.columns[i] = unique;
        sheetState.rows.forEach(function (row) {
          if (!row) return;
          row[unique] = (row[oldName] != null && row[oldName] !== undefined) ? String(row[oldName]) : '';
          if (oldName !== unique) delete row[oldName];
        });
        renamed += 1;
      }
      if (renamed > 0) {
        sheetDirty = true;
        setSheetMsg('Se aplicaron ' + renamed + ' sugerencias de nombres Kobo.', 'ok');
        renderSheetTable();
      } else {
        setSheetMsg('No hubo sugerencias aplicables.', 'info');
      }
    });
  }
  if (sheetToggleColumnMode) {
    sheetToggleColumnMode.addEventListener('click', function () {
      sheetShowAllColumns = !sheetShowAllColumns;
      try {
        localStorage.setItem(SHEET_COL_MODE_KEY, sheetShowAllColumns ? 'all' : 'relevant');
      } catch (e) {}
      updateSheetColumnModeButton();
      if (sheetState) {
        rerenderSheetPreservingViewportAndFocus();
      }
    });
    updateSheetColumnModeButton();
  }
  if (sheetMarkEditedValidated) {
    sheetMarkEditedValidated.addEventListener('click', async function () {
      if (!sheetState || !sheetState.file) return;
      var editorName = getCurrentEditorName();
      if (!editorName) {
        alert('Escribe tu nombre para marcar Editado Validado.');
        if (inputName) inputName.focus();
        return;
      }
      var nextState = !sheetState.file.edited_validated;
      sheetMarkEditedValidated.disabled = true;
      try {
        var r = await fetch(u('api/files/' + sheetState.file.id + '/edited-validated'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ edited_validated: nextState, editor_name: editorName })
        });
        var d = await r.json();
        if (!d.ok) throw new Error(d.error || 'No se pudo actualizar el estado.');
        if (d.file) sheetState.file = d.file;
        updateEditedValidatedButton();
        setSheetMsg(nextState ? 'Archivo marcado como Editado Validado.' : 'Marca Editado Validado removida.', 'ok');
        await loadFiles();
      } catch (e) {
        setSheetMsg('Error: ' + (e && e.message), 'error');
      } finally {
        sheetMarkEditedValidated.disabled = false;
      }
    });
  }
  if (sheetClose) {
    sheetClose.addEventListener('click', function () { closeSheetEditor(); });
  }
  if (sheetOpenMetaOnly) {
    sheetOpenMetaOnly.addEventListener('click', function () {
      if (!sheetState) return;
      var fid = sheetState.file && sheetState.file.id;
      if (sheetDirty) {
        if (!confirm('Los datos de la hoja no se han guardado. ¿Cerrar el editor y abrir solo nota, nombre e información?')) return;
      }
      closeSheetEditor(true);
      setTimeout(function () { openEditModal(String(fid)); }, 100);
    });
  }
  if (sheetOverlay) {
    sheetOverlay.addEventListener('click', function (e) {
      if (e.target === sheetOverlay) closeSheetEditor();
      else hideSheetContextMenu();
    });
  }
  if (koboSubmitSelectAll) {
    koboSubmitSelectAll.addEventListener('change', function () {
      if (!koboSubmitRows) return;
      var checks = koboSubmitRows.querySelectorAll('input.kobo-row-check');
      checks.forEach(function (ch) { ch.checked = !!koboSubmitSelectAll.checked; });
    });
  }
  if (koboSubmitCancel) {
    koboSubmitCancel.addEventListener('click', closeKoboSubmitModal);
  }
  if (koboSubmitConfirm) {
    koboSubmitConfirm.addEventListener('click', function () { submitRowsToKoboFromModal(); });
  }
  if (koboSubmitModalOverlay) {
    koboSubmitModalOverlay.addEventListener('click', function (e) {
      if (e.target === koboSubmitModalOverlay) closeKoboSubmitModal();
    });
  }
  document.addEventListener('click', function (e) {
    if (!sheetContextMenuEl || sheetContextMenuEl.style.display === 'none') return;
    if (e.target && e.target.closest && e.target.closest('#sheetContextMenu')) return;
    hideSheetContextMenu();
  });
  window.addEventListener('resize', hideSheetContextMenu);
  window.addEventListener('scroll', hideSheetContextMenu, true);
  document.addEventListener('keydown', function (e) {
    if (sheetGuide && sheetGuide.active && e.key === 'Escape') {
      e.preventDefault();
      stopSheetGuide(true);
      return;
    }
    if (koboSubmitModalOverlay && koboSubmitModalOverlay.style.display !== 'none' && e.key === 'Escape') {
      e.preventDefault();
      closeKoboSubmitModal();
      return;
    }
    if (!sheetOverlay || sheetOverlay.style.display === 'none' || e.key !== 'Escape') return;
    e.preventDefault();
    hideSheetContextMenu();
    closeSheetEditor();
  }, true);
  window.addEventListener('beforeunload', function () {
    releaseSheetLock(true);
  });
  window.addEventListener('pagehide', function () {
    releaseSheetLock(true);
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') releaseSheetLock(true);
  });

  function closeEditModal() {
    pendingEditFile = null;
    if (editModalOverlay) editModalOverlay.style.display = 'none';
    if (editModalFilename) editModalFilename.textContent = '';
    if (editModalOriginalName) editModalOriginalName.value = '';
    if (editModalUploadedBy) editModalUploadedBy.value = '';
    if (editModalNotes) editModalNotes.value = '';
    if (editModalConfirm) editModalConfirm.disabled = false;
    setMsg(editModalMsg, '');
  }

  function openEditModal(id) {
    var fid = parseInt(id, 10);
    if (isNaN(fid)) return;
    var file = filesCache.find(function (f) { return f.id === fid; });
    if (!file) return;
    pendingEditFile = file;
    if (editModalFilename) {
      editModalFilename.textContent = (file.original_name || file.stored_name || '');
    }
    if (editModalOriginalName) editModalOriginalName.value = file.original_name || file.stored_name || '';
    if (editModalUploadedBy) editModalUploadedBy.value = file.uploaded_by || '';
    if (editModalNotes) editModalNotes.value = file.notes || '';
    setMsg(editModalMsg, '');
    if (editModalOverlay) editModalOverlay.style.display = 'flex';
    if (editModalOriginalName) editModalOriginalName.focus();
  }

  if (editModalCancel) editModalCancel.addEventListener('click', closeEditModal);
  if (editModalOverlay) {
    editModalOverlay.addEventListener('click', function (e) {
      if (e.target === editModalOverlay) closeEditModal();
    });
  }
  if (editModalConfirm) {
    editModalConfirm.addEventListener('click', async function () {
      if (!pendingEditFile) return;
      var originalName = (editModalOriginalName && editModalOriginalName.value || '').trim();
      var uploadedBy = (editModalUploadedBy && editModalUploadedBy.value || '').trim();
      var notes = (editModalNotes && editModalNotes.value || '').trim();
      if (!originalName) {
        setMsg(editModalMsg, 'El nombre del archivo es obligatorio.', 'error');
        if (editModalOriginalName) editModalOriginalName.focus();
        return;
      }
      editModalConfirm.disabled = true;
      setMsg(editModalMsg, 'Guardando cambios...', 'info');
      try {
        var r = await fetch(u('api/files/' + pendingEditFile.id), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            original_name: originalName,
            uploaded_by: uploadedBy,
            notes: notes
          }),
        });
        var data = await r.json();
        if (!data.ok) throw new Error(data.error || 'No se pudo editar');
        setMsg(uploadMsg, 'Archivo actualizado correctamente.', 'ok');
        closeEditModal();
        await loadFiles();
      } catch (e) {
        setMsg(editModalMsg, 'Error: ' + e.message, 'error');
      } finally {
        if (editModalConfirm) editModalConfirm.disabled = false;
      }
    });
  }

  // Modal descargar
  function openDownloadModal(id, url, name) {
    pendingDownload = { id: id, url: url };
    dlModalFilename.textContent = name || '';
    dlModalName.value = (inputName && inputName.value.trim()) || localStorage.getItem('koboup_name') || '';
    dlModalOverlay.style.display = 'flex';
    dlModalName.focus();
  }

  dlModalCancel.addEventListener('click', function () { dlModalOverlay.style.display = 'none'; pendingDownload = null; });
  dlModalOverlay.addEventListener('click', function (e) { if (e.target === dlModalOverlay) { dlModalOverlay.style.display = 'none'; pendingDownload = null; } });

  dlModalConfirm.addEventListener('click', async function () {
    if (!pendingDownload) return;
    var dlName = (dlModalName.value || '').trim();
    if (!dlName) { dlModalName.style.borderColor = '#ef4444'; dlModalName.focus(); return; }
    dlModalName.style.borderColor = '';
    localStorage.setItem('koboup_name', dlName);
    dlModalConfirm.disabled = true;

    try {
      await fetch(u('api/files/' + pendingDownload.id + '/register-download'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ downloaded_by: dlName }),
      });

      var a = document.createElement('a');
      a.href = pendingDownload.url;
      a.download = '';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      dlModalOverlay.style.display = 'none';
      pendingDownload = null;
      await loadFiles();
    } catch (e) {
      alert('Error: ' + e.message);
    } finally {
      dlModalConfirm.disabled = false;
    }
  });

  /* ═══════════════ PDFs DE REFERENCIA ═══════════════ */

  var selectedRefFiles = [];

  function checkRefUploadReady() {
    var hasFiles = selectedRefFiles.length > 0;
    var hasName = !!(refInputName && refInputName.value.trim());
    var hasLoc = !!(refInputLocation && refInputLocation.value.trim());
    btnRefUpload.disabled = !(hasFiles && hasName && hasLoc);
  }

  if (refInputName) refInputName.addEventListener('input', checkRefUploadReady);
  if (refInputLocation) refInputLocation.addEventListener('input', checkRefUploadReady);

  refUploadZone.addEventListener('click', function () { refFileInput.click(); });
  refUploadZone.addEventListener('dragover', function (e) { e.preventDefault(); refUploadZone.classList.add('dragover'); });
  refUploadZone.addEventListener('dragleave', function () { refUploadZone.classList.remove('dragover'); });
  refUploadZone.addEventListener('drop', function (e) {
    e.preventDefault(); refUploadZone.classList.remove('dragover');
    var files = e.dataTransfer && e.dataTransfer.files;
    if (files && files.length) addRefFiles(files);
  });
  refFileInput.addEventListener('change', function () {
    if (refFileInput.files && refFileInput.files.length) addRefFiles(refFileInput.files);
  });

  function addRefFiles(fileList) {
    var pdfs = [];
    for (var i = 0; i < fileList.length; i++) {
      if (/\.pdf$/i.test(fileList[i].name)) pdfs.push(fileList[i]);
    }
    if (pdfs.length === 0) return;
    selectedRefFiles = selectedRefFiles.concat(pdfs);
    updateRefDropzoneUI();
    checkRefUploadReady();
    setMsg(refUploadMsg, '');
  }

  function updateRefDropzoneUI() {
    if (selectedRefFiles.length === 0) {
      resetRefUpload();
      return;
    }
    refUploadZone.classList.add('has-file');
    var totalSize = selectedRefFiles.reduce(function (s, f) { return s + f.size; }, 0);
    var listHtml = selectedRefFiles.map(function (f, i) {
      return '<div class="ref-file-item">' +
        '<span class="ref-file-name">' + esc(f.name) + '</span>' +
        '<span class="ref-file-size">' + fmtSize(f.size) + '</span>' +
        '<button type="button" class="ref-file-remove" data-idx="' + i + '" title="Quitar">&times;</button>' +
        '</div>';
    }).join('');
    refUploadZone.querySelector('.dropzone-content').innerHTML =
      '<div class="dropzone-icon"><svg width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>' +
      '<p class="dropzone-filename">' + selectedRefFiles.length + ' PDF' + (selectedRefFiles.length > 1 ? 's' : '') + ' seleccionado' + (selectedRefFiles.length > 1 ? 's' : '') + ' (' + fmtSize(totalSize) + ')</p>' +
      '<div class="ref-files-list">' + listHtml + '</div>' +
      '<span class="dropzone-hint" style="margin-top:0.5rem">Arrastra más o haz clic para agregar</span>';
  }

  refUploadZone.addEventListener('click', function (e) {
    var removeBtn = e.target.closest('.ref-file-remove');
    if (removeBtn) {
      e.stopPropagation();
      var idx = parseInt(removeBtn.getAttribute('data-idx'), 10);
      selectedRefFiles.splice(idx, 1);
      updateRefDropzoneUI();
      checkRefUploadReady();
    }
  });

  function resetRefUpload() {
    selectedRefFiles = [];
    refFileInput.value = '';
    refUploadZone.classList.remove('has-file');
    refUploadZone.querySelector('.dropzone-content').innerHTML =
      '<div class="dropzone-icon"><svg width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>' +
      '<p class="dropzone-text">Arrastra uno o varios PDFs aquí o <strong>haz clic para seleccionar</strong></p>' +
      '<span class="dropzone-hint">Solo archivos PDF — Máx. 200 MB cada uno — Puedes seleccionar varios</span>';
    btnRefUpload.disabled = true;
    if (refInputNotes) refInputNotes.value = '';
  }

  // Duplicates modal
  var dupModalOverlay = document.getElementById('dupModalOverlay');
  var dupFilesList = document.getElementById('dupFilesList');
  var dupCancel = document.getElementById('dupCancel');
  var dupSkip = document.getElementById('dupSkip');
  var dupReplace = document.getElementById('dupReplace');
  var pendingUploadAction = null; // { filesToUpload, duplicates, name, loc, noteVal }

  dupCancel.addEventListener('click', function () { dupModalOverlay.style.display = 'none'; pendingUploadAction = null; });
  dupModalOverlay.addEventListener('click', function (e) { if (e.target === dupModalOverlay) { dupModalOverlay.style.display = 'none'; pendingUploadAction = null; } });

  dupSkip.addEventListener('click', function () {
    if (!pendingUploadAction) return;
    dupModalOverlay.style.display = 'none';
    var dupNames = pendingUploadAction.duplicates.map(function (d) { return d.fileName; });
    var filtered = pendingUploadAction.filesToUpload.filter(function (f) {
      return dupNames.indexOf(f.name) === -1;
    });
    if (filtered.length === 0) {
      setMsg(refUploadMsg, 'Todos los archivos ya existen. No se subió nada.', 'info');
      pendingUploadAction = null;
      return;
    }
    doRefUpload(filtered, pendingUploadAction.name, pendingUploadAction.loc, pendingUploadAction.noteVal, []);
    pendingUploadAction = null;
  });

  dupReplace.addEventListener('click', function () {
    if (!pendingUploadAction) return;
    dupModalOverlay.style.display = 'none';
    var idsToDelete = pendingUploadAction.duplicates.map(function (d) { return d.existingId; });
    doRefUpload(pendingUploadAction.filesToUpload, pendingUploadAction.name, pendingUploadAction.loc, pendingUploadAction.noteVal, idsToDelete);
    pendingUploadAction = null;
  });

  function findDuplicates(files, location) {
    var existingInLoc = refsCache.filter(function (r) { return r.location === location; });
    var dups = [];
    files.forEach(function (f) {
      var match = existingInLoc.find(function (r) { return r.original_name === f.name; });
      if (match) dups.push({ fileName: f.name, existingId: match.id });
    });
    return dups;
  }

  btnRefUpload.addEventListener('click', async function () {
    if (selectedRefFiles.length === 0) return;
    var name = (refInputName && refInputName.value.trim()) || '';
    var loc = (refInputLocation && refInputLocation.value.trim()) || '';
    if (!name) { setMsg(refUploadMsg, 'Escribe tu nombre.', 'error'); return; }
    if (!loc) { setMsg(refUploadMsg, 'Escribe la ubicación.', 'error'); return; }
    localStorage.setItem('koboup_name', name);
    var noteVal = (refInputNotes && refInputNotes.value.trim()) || '';

    // Asegurar que tenemos datos frescos del servidor
    try {
      var rr = await fetch(u('api/refs'));
      var dd = await rr.json();
      if (dd.ok) refsCache = dd.refs || [];
    } catch (e) { /* usar cache existente */ }

    var duplicates = findDuplicates(selectedRefFiles, loc);

    if (duplicates.length > 0) {
      dupFilesList.innerHTML = duplicates.map(function (d) {
        return '<div class="dup-file-item">' +
          '<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>' +
          '<span class="dup-file-name">' + esc(d.fileName) + '</span></div>';
      }).join('');
      pendingUploadAction = {
        filesToUpload: selectedRefFiles.slice(),
        duplicates: duplicates,
        name: name,
        loc: loc,
        noteVal: noteVal
      };
      dupModalOverlay.style.display = 'flex';
      return;
    }

    doRefUpload(selectedRefFiles.slice(), name, loc, noteVal, []);
  });

  var refProgressWrap = document.getElementById('refProgressWrap');
  var refProgressTitle = document.getElementById('refProgressTitle');
  var refProgressSpeed = document.getElementById('refProgressSpeed');
  var refProgressCount = document.getElementById('refProgressCount');
  var refProgressElapsed = document.getElementById('refProgressElapsed');
  var refProgressBar = document.getElementById('refProgressBar');
  var refProgressPercent = document.getElementById('refProgressPercent');
  var refProgressFiles = document.getElementById('refProgressFiles');

  var PARALLEL_UPLOADS = 3;
  var uploadState = null;

  function fmtElapsed(ms) {
    var s = Math.floor(ms / 1000);
    if (s < 60) return s + 's';
    var m = Math.floor(s / 60);
    s = s % 60;
    return m + 'm ' + (s < 10 ? '0' : '') + s + 's';
  }

  function fmtSpeed(bytesPerSec) {
    if (bytesPerSec < 1024) return Math.round(bytesPerSec) + ' B/s';
    if (bytesPerSec < 1048576) return Math.round(bytesPerSec / 1024) + ' KB/s';
    return (bytesPerSec / 1048576).toFixed(1) + ' MB/s';
  }

  function initUploadState(total) {
    uploadState = {
      total: total,
      completed: 0,
      failed: 0,
      startTime: Date.now(),
      totalBytes: 0,
      loadedBytes: 0,
      files: {}
    };
  }

  function updateOverallProgress() {
    if (!uploadState) return;
    var st = uploadState;
    var done = st.completed + st.failed;
    var pct = st.total > 0 ? Math.round((done / st.total) * 100) : 0;

    if (st.totalBytes > 0) {
      pct = Math.round((st.loadedBytes / st.totalBytes) * 100);
    }

    refProgressBar.style.width = pct + '%';
    refProgressPercent.textContent = pct + '%';
    refProgressCount.textContent = done + ' de ' + st.total + ' completados';

    var elapsed = Date.now() - st.startTime;
    refProgressElapsed.textContent = fmtElapsed(elapsed);

    if (st.loadedBytes > 0 && elapsed > 500) {
      var speed = st.loadedBytes / (elapsed / 1000);
      refProgressSpeed.textContent = fmtSpeed(speed);
      var remaining = st.totalBytes - st.loadedBytes;
      if (speed > 0 && remaining > 0) {
        var eta = remaining / speed;
        refProgressSpeed.textContent += ' — ~' + fmtElapsed(eta * 1000) + ' restante';
      }
    }

    btnRefUpload.textContent = 'Subiendo ' + done + '/' + st.total + '…';
    btnRefUpload.classList.add('btn-uploading');

    renderFileProgress();
  }

  function renderFileProgress() {
    if (!uploadState || !refProgressFiles) return;
    var entries = Object.values(uploadState.files);
    entries.sort(function (a, b) { return a.index - b.index; });

    var visible = entries.filter(function (f) {
      return f.status === 'uploading' || f.status === 'done' || f.status === 'error';
    });
    var lastDone = visible.filter(function (f) { return f.status === 'done'; });
    var active = visible.filter(function (f) { return f.status === 'uploading'; });
    var errored = visible.filter(function (f) { return f.status === 'error'; });

    var show = [].concat(errored, active, lastDone.slice(-2));

    refProgressFiles.innerHTML = show.map(function (f) {
      var icon, barClass, pctText;
      if (f.status === 'done') {
        icon = '<svg class="pf-icon pf-done" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>';
        barClass = 'pf-bar-done';
        pctText = fmtSize(f.total);
      } else if (f.status === 'error') {
        icon = '<svg class="pf-icon pf-error" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
        barClass = 'pf-bar-error';
        pctText = f.errorMsg || 'Error';
      } else {
        icon = '<div class="pf-spinner"></div>';
        barClass = '';
        var filePct = f.total > 0 ? Math.round((f.loaded / f.total) * 100) : 0;
        pctText = filePct + '% · ' + fmtSize(f.loaded) + ' / ' + fmtSize(f.total);
      }
      var barWidth = f.total > 0 ? Math.round((f.loaded / f.total) * 100) : 0;
      if (f.status === 'done') barWidth = 100;

      return '<div class="pf-row pf-' + f.status + '">' +
        icon +
        '<div class="pf-info">' +
          '<div class="pf-name">' + esc(f.name) + '</div>' +
          '<div class="pf-track"><div class="pf-fill ' + barClass + '" style="width:' + barWidth + '%"></div></div>' +
        '</div>' +
        '<div class="pf-pct">' + pctText + '</div>' +
      '</div>';
    }).join('');
  }

  function showProgressPanel() {
    refProgressWrap.style.display = '';
    refProgressWrap.classList.add('uploading');
    refProgressBar.className = 'progress-bar-fill';
    refProgressPercent.className = 'progress-percent';
    refProgressTitle.textContent = 'Subiendo archivos…';
    refProgressSpeed.textContent = '';
    refProgressElapsed.textContent = '';
  }

  function hideProgress() {
    refProgressWrap.style.display = 'none';
    refProgressWrap.classList.remove('uploading');
    refProgressBar.style.width = '0%';
    if (refProgressFiles) refProgressFiles.innerHTML = '';
    uploadState = null;
    btnRefUpload.innerHTML =
      '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg> Subir PDF';
    btnRefUpload.classList.remove('btn-uploading');
  }

  function finishProgress() {
    refProgressBar.style.width = '100%';
    refProgressBar.className = 'progress-bar-fill done';
    refProgressPercent.textContent = '100%';
    refProgressPercent.className = 'progress-percent done';
    refProgressWrap.classList.remove('uploading');
    refProgressTitle.textContent = 'Subida completada';
    btnRefUpload.textContent = 'Listo';
    btnRefUpload.classList.remove('btn-uploading');
  }

  function uploadSingleFile(file, index, name, loc, noteVal) {
    return new Promise(function (resolve, reject) {
      var fd = new FormData();
      fd.append('file', file);
      fd.append('uploaded_by', name);
      fd.append('location', loc);
      if (noteVal) fd.append('notes', noteVal);

      uploadState.files[index] = {
        index: index, name: file.name, status: 'uploading',
        loaded: 0, total: file.size, errorMsg: ''
      };
      uploadState.totalBytes += file.size;
      updateOverallProgress();

      var xhr = new XMLHttpRequest();
      var prevLoaded = 0;

      xhr.upload.addEventListener('progress', function (e) {
        if (e.lengthComputable) {
          var delta = e.loaded - prevLoaded;
          prevLoaded = e.loaded;
          uploadState.loadedBytes += delta;
          uploadState.files[index].loaded = e.loaded;
          uploadState.files[index].total = e.total;
          updateOverallProgress();
        }
      });

      xhr.addEventListener('load', function () {
        if (xhr.status === 413) {
          uploadState.files[index].status = 'error';
          uploadState.files[index].errorMsg = 'Muy grande';
          uploadState.failed++;
          updateOverallProgress();
          reject(new Error('Archivo demasiado grande'));
          return;
        }
        if (xhr.status < 200 || xhr.status >= 300) {
          uploadState.files[index].status = 'error';
          uploadState.files[index].errorMsg = 'Error ' + xhr.status;
          uploadState.failed++;
          updateOverallProgress();
          reject(new Error('Error del servidor (' + xhr.status + ')'));
          return;
        }
        try {
          var data = JSON.parse(xhr.responseText);
          if (!data.ok) {
            uploadState.files[index].status = 'error';
            uploadState.files[index].errorMsg = data.error || 'Error';
            uploadState.failed++;
            updateOverallProgress();
            reject(new Error(data.error || 'Error'));
            return;
          }
          uploadState.files[index].status = 'done';
          uploadState.files[index].loaded = uploadState.files[index].total;
          uploadState.completed++;
          updateOverallProgress();
          resolve(data);
        } catch (e) {
          uploadState.files[index].status = 'error';
          uploadState.files[index].errorMsg = 'Respuesta inválida';
          uploadState.failed++;
          updateOverallProgress();
          reject(new Error('Respuesta inválida del servidor'));
        }
      });

      xhr.addEventListener('error', function () {
        uploadState.files[index].status = 'error';
        uploadState.files[index].errorMsg = 'Sin conexión';
        uploadState.failed++;
        updateOverallProgress();
        reject(new Error('Error de conexión'));
      });

      xhr.addEventListener('abort', function () {
        uploadState.files[index].status = 'error';
        uploadState.files[index].errorMsg = 'Cancelado';
        uploadState.failed++;
        updateOverallProgress();
        reject(new Error('Subida cancelada'));
      });

      xhr.open('POST', u('api/refs'));
      xhr.send(fd);
    });
  }

  async function doRefUpload(files, name, loc, noteVal, idsToDelete) {
    btnRefUpload.disabled = true;

    for (var d = 0; d < idsToDelete.length; d++) {
      try {
        await fetch(u('api/refs/' + idsToDelete[d]), { method: 'DELETE' });
      } catch (e) { /* continuar */ }
    }

    var total = files.length;
    initUploadState(total);

    setMsg(refUploadMsg, '', '');
    showProgressPanel();
    updateOverallProgress();
    refProgressWrap.scrollIntoView({ behavior: 'smooth', block: 'center' });

    var elapsedInterval = setInterval(function () {
      if (!uploadState) { clearInterval(elapsedInterval); return; }
      updateOverallProgress();
    }, 1000);

    var queue = files.slice();
    var errors = [];
    var running = 0;
    var idx = 0;

    await new Promise(function (resolveAll) {
      function next() {
        while (running < PARALLEL_UPLOADS && idx < total) {
          (function (i, file) {
            running++;
            uploadSingleFile(file, i, name, loc, noteVal)
              .catch(function (e) { errors.push(file.name + ': ' + e.message); })
              .then(function () {
                running--;
                if (idx >= total && running === 0) {
                  resolveAll();
                } else {
                  next();
                }
              });
          })(idx, queue[idx]);
          idx++;
        }
        if (idx >= total && running === 0) resolveAll();
      }
      next();
    });

    clearInterval(elapsedInterval);
    finishProgress();
    updateOverallProgress();

    var elapsed = uploadState ? fmtElapsed(Date.now() - uploadState.startTime) : '';
    var successCount = uploadState ? uploadState.completed : 0;
    if (errors.length === 0) {
      setMsg(refUploadMsg, successCount + ' PDF' + (successCount > 1 ? 's' : '') + ' subido' + (successCount > 1 ? 's' : '') + ' correctamente en "' + loc + '"' + (elapsed ? ' (' + elapsed + ')' : '') + '.' + (idsToDelete.length > 0 ? ' (' + idsToDelete.length + ' reemplazado' + (idsToDelete.length > 1 ? 's' : '') + ')' : ''), 'ok');
    } else {
      setMsg(refUploadMsg, successCount + ' subido' + (successCount > 1 ? 's' : '') + ', ' + errors.length + ' error' + (errors.length > 1 ? 'es' : '') + (elapsed ? ' (' + elapsed + ')' : '') + '.', 'error');
    }

    setTimeout(hideProgress, 8000);
    resetRefUpload();
    await loadRefs();
  }

  btnRefRefresh.addEventListener('click', function () { loadRefs(); });

  async function loadRefs() {
    try {
      var r = await fetch(u('api/refs'));
      var data = await r.json();
      if (!data.ok) throw new Error(data.error || 'Error');
      refsCache = data.refs || [];
      await updateLocationTabs();
      renderRefs();
    } catch (e) {
      refsList.innerHTML = '<div class="empty-state"><p>Error al cargar PDFs</p><span>' + esc(e.message) + '</span></div>';
    }
  }

  async function updateLocationTabs() {
    try {
      var r = await fetch(u('api/refs/locations'));
      var data = await r.json();
      var locations = (data.ok && data.locations) || [];

      // Actualizar datalist de sugerencias
      locationSuggestions.innerHTML = locations.map(function (loc) {
        return '<option value="' + esc(loc) + '">';
      }).join('');

      // Actualizar pestañas
      var html = '<button class="tab' + (!currentRefLocation ? ' active' : '') + '" data-location="">Todos (' + refsCache.length + ')</button>';
      locations.forEach(function (loc) {
        var count = refsCache.filter(function (r) { return r.location === loc; }).length;
        html += '<button class="tab' + (currentRefLocation === loc ? ' active' : '') + '" data-location="' + esc(loc) + '">' + esc(loc) + ' (' + count + ')</button>';
      });
      refLocationTabs.innerHTML = html;

      // Re-bind click events
      refLocationTabs.querySelectorAll('.tab').forEach(function (btn) {
        btn.addEventListener('click', function () {
          refLocationTabs.querySelectorAll('.tab').forEach(function (b) { b.classList.remove('active'); });
          btn.classList.add('active');
          currentRefLocation = btn.getAttribute('data-location') || '';
          renderRefs();
        });
      });
    } catch (e) { /* ignore */ }
  }

  function renderRefs() {
    var filtered = refsCache;
    if (currentRefLocation) filtered = refsCache.filter(function (r) { return r.location === currentRefLocation; });

    if (filtered.length === 0) {
      refsList.innerHTML =
        '<div class="empty-state">' +
        '<svg width="56" height="56" fill="none" stroke="currentColor" stroke-width="1.2" viewBox="0 0 24 24" opacity="0.3"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>' +
        '<p>' + (currentRefLocation ? 'No hay PDFs para "' + esc(currentRefLocation) + '".' : 'Aún no hay PDFs de referencia.') + '</p></div>';
      return;
    }

    refsList.innerHTML = filtered.map(function (r) {
      var actions = '';
      actions += '<a class="btn btn-outline btn-sm" href="' + u(r.download_url || ('api/refs/' + r.id + '/download')) + '" download>' +
        '<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Descargar</a>';
      actions += '<button class="btn btn-outline-red btn-sm js-ref-delete" data-id="' + r.id + '">' +
        '<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg></button>';

      var meta = '<span class="badge badge-location">' + esc(r.location) + '</span>';
      if (r.size_bytes) meta += '<span class="sep">·</span>' + fmtSize(r.size_bytes);
      meta += '<span class="sep">·</span>' + timeSince(r.created_at);

      var people = '';
      if (r.uploaded_by) people += '<span class="person"><svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> Subido por: <strong>' + esc(r.uploaded_by) + '</strong></span>';

      return '<div class="file-row" data-id="' + r.id + '">' +
        '<div class="file-icon-wrap pdf">PDF</div>' +
        '<div class="file-info">' +
          '<div class="file-name">' + esc(r.original_name || r.stored_name) + '</div>' +
          '<div class="file-meta">' + meta + '</div>' +
          (people ? '<div class="file-people">' + people + '</div>' : '') +
          (r.notes ? '<div class="file-notes">' + esc(r.notes) + '</div>' : '') +
        '</div>' +
        '<div class="file-actions">' + actions + '</div>' +
        '</div>';
    }).join('');
  }

  refsList.addEventListener('click', async function (ev) {
    var dBtn = ev.target.closest('.js-ref-delete');
    if (!dBtn) return;
    var id = dBtn.getAttribute('data-id');
    if (!confirm('¿Eliminar este PDF de referencia?')) return;
    try {
      var r = await fetch(u('api/refs/' + id), { method: 'DELETE' });
      var data = await r.json();
      if (!data.ok) throw new Error(data.error || 'Error');
      await loadRefs();
    } catch (e) {
      alert('Error al eliminar: ' + e.message);
    }
  });

  /* ═══════════════ RANKING ═══════════════ */

  var rankingList = document.getElementById('rankingList');
  var uploadersRankingList = document.getElementById('uploadersRankingList');
  var btnRankRefresh = document.getElementById('btnRankRefresh');

  if (btnRankRefresh) {
    btnRankRefresh.addEventListener('click', function () { loadRanking(); });
  }

  var RANK_MEDALS = [
    { emoji: '\uD83C\uDFC6', label: 'Campeon', badge: 'gold', bar: 'gold' },
    { emoji: '\uD83E\uDD48', label: '2do lugar', badge: 'silver', bar: 'silver' },
    { emoji: '\uD83E\uDD49', label: '3er lugar', badge: 'bronze', bar: 'bronze' }
  ];

  function getInitials(name) {
    if (!name) return '?';
    var parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.substring(0, 2).toUpperCase();
  }

  function renderRankingList(container, data, countLabel) {
    if (!data || data.length === 0) {
      container.innerHTML =
        '<div class="empty-state">' +
        '<svg width="56" height="56" fill="none" stroke="currentColor" stroke-width="1.2" viewBox="0 0 24 24" opacity="0.3"><path d="M6 9H4.5a2.5 2.5 0 010-5H6"/><path d="M18 9h1.5a2.5 2.5 0 000-5H18"/><path d="M4 22h16"/><path d="M18 2H6v7a6 6 0 1012 0V2Z"/></svg>' +
        '<p>Aun no hay datos.</p></div>';
      return;
    }

    var maxCount = data[0].count || 1;
    var isLastSingle = data.length > 1;
    var lastIdx = data.length - 1;

    container.innerHTML = data.map(function (item, i) {
      var pos = i + 1;
      var medal = RANK_MEDALS[i] || null;
      var isLast = isLastSingle && i === lastIdx && !medal;

      var rowClass = 'rank-row';
      var avatarClass = 'rank-avatar rank-avatar-default';
      var countClass = 'rank-count-number rank-count-number-default';
      var barClass = 'rank-bar-fill rank-bar-default';
      var nameClass = 'rank-name';
      var positionHtml;

      if (medal) {
        rowClass += ' rank-row-' + medal.badge;
        avatarClass = 'rank-avatar rank-avatar-' + pos;
        countClass = 'rank-count-number rank-count-number-' + medal.badge;
        barClass = 'rank-bar-fill rank-bar-' + medal.badge;
        positionHtml = '<div class="rank-position">' + medal.emoji + '</div>';
        if (i === 0) nameClass += ' rank-name-gold';
      } else if (isLast) {
        rowClass += ' rank-row-last';
        avatarClass = 'rank-avatar rank-avatar-last';
        countClass = 'rank-count-number rank-count-number-last';
        barClass = 'rank-bar-fill rank-bar-last';
        positionHtml = '<div class="rank-position">\uD83D\uDCAA</div>';
      } else {
        positionHtml = '<div class="rank-position"><div class="rank-position-number">' + pos + '</div></div>';
      }

      var badgeHtml = '';
      if (medal) {
        badgeHtml = '<span class="rank-badge rank-badge-' + medal.badge + '">' + medal.emoji + ' ' + medal.label + '</span>';
      } else if (isLast) {
        badgeHtml = '<span class="rank-badge rank-badge-last">\uD83D\uDCAA \u00A1T\u00FA puedes!</span>';
      }

      var barWidth = Math.round((item.count / maxCount) * 100);

      var detailText = '';
      var lastDate = item.last_validated_at || item.last_upload_at || '';
      if (lastDate) detailText = 'Ultima actividad: ' + timeSince(lastDate);

      return '<div class="' + rowClass + '">' +
        positionHtml +
        '<div class="' + avatarClass + '">' + getInitials(item.name) + '</div>' +
        '<div class="rank-info">' +
          '<div class="' + nameClass + '">' + esc(item.name) + '</div>' +
          (detailText ? '<div class="rank-detail">' + detailText + '</div>' : '') +
        '</div>' +
        '<div class="rank-bar-wrap"><div class="' + barClass + '" style="width:' + barWidth + '%"></div></div>' +
        '<div class="rank-count">' +
          '<div class="' + countClass + '">' + item.count + '</div>' +
          '<div class="rank-count-label">' + countLabel + '</div>' +
        '</div>' +
        badgeHtml +
      '</div>';
    }).join('');
  }

  async function loadRanking() {
    try {
      var r = await fetch(u('api/stats/ranking'));
      var data = await r.json();
      if (!data.ok) throw new Error(data.error || 'Error');
      renderRankingList(rankingList, data.validators || [], 'validados');
      renderRankingList(uploadersRankingList, data.uploaders || [], 'subidos');
    } catch (e) {
      if (rankingList) {
        rankingList.innerHTML = '<div class="empty-state"><p>Error al cargar ranking</p><span>' + esc(e.message) + '</span></div>';
      }
    }
  }

  /* ═══════════════ BITÁCORA KOBO ═══════════════ */

  function renderKoboSubmissionLogs(logs) {
    if (!koboLogsTableBody) return;
    if (!logs || !logs.length) {
      koboLogsTableBody.innerHTML = '<tr><td colspan="7">Sin registros todavía.</td></tr>';
      return;
    }
    koboLogsTableBody.innerHTML = logs.map(function (row) {
      var failed = Number(row.failed_count || 0);
      var sent = Number(row.sent_count || 0);
      var status = failed > 0 ? 'Con errores' : (sent > 0 ? 'Completado' : 'Sin envío');
      return '<tr>'
        + '<td>' + esc(fmtDate(row.submitted_at) || '—') + '</td>'
        + '<td>' + esc(row.submitted_by || '—') + '</td>'
        + '<td>' + esc(row.file_name || ('#' + (row.file_id || '—'))) + '</td>'
        + '<td>' + esc(String(row.selected_total == null ? '0' : row.selected_total)) + '</td>'
        + '<td>' + esc(String(sent)) + '</td>'
        + '<td>' + esc(String(failed)) + '</td>'
        + '<td>' + esc(status) + '</td>'
        + '</tr>';
    }).join('');
  }

  async function loadKoboSubmissionLogs() {
    if (koboLogsTableBody) {
      koboLogsTableBody.innerHTML = '<tr><td colspan="7">Cargando bitácora…</td></tr>';
    }
    try {
      var r = await fetch(u('api/kobo-submissions/logs?limit=120'));
      var d = await r.json();
      if (!d.ok) throw new Error(d.error || 'No se pudo cargar la bitácora');
      renderKoboSubmissionLogs(d.logs || []);
    } catch (e) {
      if (koboLogsTableBody) {
        koboLogsTableBody.innerHTML = '<tr><td colspan="7">Error al cargar bitácora: ' + esc(e.message || '') + '</td></tr>';
      }
    }
  }

  if (btnKoboLogsRefresh) {
    btnKoboLogsRefresh.addEventListener('click', function () {
      loadKoboSubmissionLogs();
    });
  }

  /* ═══════════════ INICIO ═══════════════ */
  loadFiles();
})();

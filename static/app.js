(function () {
  const formUrlEl = document.getElementById('formUrl');
  const mappingStatusEl = document.getElementById('mappingStatus');
  const uploadZone = document.getElementById('uploadZone');
  const fileInput = document.getElementById('fileInput');
  const uploadLabel = document.getElementById('uploadLabel');
  const uploadedFileEl = document.getElementById('uploadedFile');
  const verifySectionEl = document.getElementById('verifySection');
  const dataTableEl = document.getElementById('dataTable');
  const btnConfirm = document.getElementById('btnConfirm');
  const btnSelectAll = document.getElementById('btnSelectAll');
  const btnSelectNone = document.getElementById('btnSelectNone');
  const btnStart = document.getElementById('btnStart');
  const btnStop = document.getElementById('btnStop');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  const statOk = document.getElementById('statOk');
  const statFail = document.getElementById('statFail');
  const statTime = document.getElementById('statTime');
  const logEl = document.getElementById('log');
  const confirmRowSection = document.getElementById('confirmRowSection');
  const btnValidateSend = document.getElementById('btnValidateSend');
  const btnSkipRow = document.getElementById('btnSkipRow');
  const progressActionsEl = document.getElementById('progressActions');
  const validationSummaryEl = document.getElementById('validationSummary');
  const validationDetailEl = document.getElementById('validationDetail');
  const pdfDataTableEl = document.getElementById('pdfDataTable');
  const btnDownloadExtracted = document.getElementById('btnDownloadExtracted');

  // Discover & Mapping editor
  const btnDiscover = document.getElementById('btnDiscover');
  const btnMappingEditor = document.getElementById('btnMappingEditor');
  const mappingEditorSection = document.getElementById('mappingEditorSection');
  const mappingTextarea = document.getElementById('mappingTextarea');
  const btnSaveMapping = document.getElementById('btnSaveMapping');
  const btnCancelMapping = document.getElementById('btnCancelMapping');
  const btnCopyDiscovered = document.getElementById('btnCopyDiscovered');
  const mappingEditorMsg = document.getElementById('mappingEditorMsg');

  // Checkpoint / resume
  const resumeFormEl = document.getElementById('resumeForm');
  const inputStartRow = document.getElementById('inputStartRow');
  const checkpointHintEl = document.getElementById('checkpointHint');
  // Coordenadas por lugar
  const inputLugar = document.getElementById('inputLugar');
  const inputLatitud = document.getElementById('inputLatitud');
  const inputLongitud = document.getElementById('inputLongitud');
  const coordsHint = document.getElementById('coordsHint');

  // Historial
  const historialToggle = document.getElementById('historialToggle');
  const historialContent = document.getElementById('historialContent');
  const historialList = document.getElementById('historialList');
  const historialArchivos = document.getElementById('historialArchivos');
  
  const kpiSummaryEl = document.getElementById('kpiSummary');
  const kpiPatientsEl = document.getElementById('kpiPatients');
  const kpiConsultasEl = document.getElementById('kpiConsultas');
  const kpiSpecialtiesEl = document.getElementById('kpiSpecialties');
  const kpiSuppliesEl = document.getElementById('kpiSupplies');

  const summaryArchivosEl = document.getElementById('summaryArchivos');
  const summaryRegistrosEl = document.getElementById('summaryRegistros');

  // KoboUp queue
  const btnLoadKoboup = document.getElementById('btnLoadKoboup');
  const koboupStatus = document.getElementById('koboupStatus');
  const koboupListEl = document.getElementById('koboupList');
  const koboupListBody = document.getElementById('koboupListBody');
  const koboupEmpty = document.getElementById('koboupEmpty');
  const crossValidationPanel = document.getElementById('crossValidationPanel');

  // Filebox (gestión simple de archivos)
  const fileBoxInput = document.getElementById('fileBoxInput');
  const fileBoxDropzone = document.getElementById('fileBoxDropzone');
  const fileBoxPending = document.getElementById('fileBoxPending');
  const fileBoxPendingCount = document.getElementById('fileBoxPendingCount');
  const fileBoxPendingList = document.getElementById('fileBoxPendingList');
  const btnFileBoxClear = document.getElementById('btnFileBoxClear');
  const chkFileBoxValidated = document.getElementById('chkFileBoxValidated');
  const fileBoxNote = document.getElementById('fileBoxNote');
  const btnFileBoxUpload = document.getElementById('btnFileBoxUpload');
  const fileBoxList = document.getElementById('fileBoxList');
  const fileBoxMessage = document.getElementById('fileBoxMessage');
  const fileBoxProgress = document.getElementById('fileBoxProgress');
  const fileBoxProgressBar = document.getElementById('fileBoxProgressBar');
  const fileBoxProgressText = document.getElementById('fileBoxProgressText');

  let uploadedFilename = null;
  let uploadedFileType = null;
  let uploadedOriginalName = null;
  let koboupFiles = [];
  let activeKoboupFileId = null;
  let extractedRecords = [];
  let pdfExtractedRecords = [];
  // true cuando el servidor indica que no pudo determinar coords automáticamente
  let coordsRequired = false;
  let lastValidation = null;
  let lastAlreadySubmitted = [];

  if (btnDownloadExtracted) {
    btnDownloadExtracted.style.display = 'none';
  }
  let dataConfirmed = false;
  let currentFormUrl = '';
  let discoveredYaml = '';
  let activeEventSource = null;
  // Índices seleccionados que deben restaurarse tras un re-render de la tabla
  // (se setea antes de loadExcelForVerification() para no perder la selección del usuario)
  let _pendingRestoreIndices = null;
  let fileBoxCache = [];

  // ── Utilidades ──────────────────────────────────────────────────────────────

  function addLog(text, type) {
    const entry = document.createElement('div');
    entry.className = 'log-entry ' + (type || '');
    entry.textContent = text;
    logEl.appendChild(entry);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function setProgress(pct, text) {
    progressBar.style.width = (pct || 0) + '%';
    progressText.textContent = text || '—';
  }

  function updateStats(stats) {
    if (!stats) return;
    statOk.textContent = stats.exitosos ?? 0;
    statFail.textContent = stats.fallidos ?? 0;
    if (stats.tiempo_segundos != null) {
      statTime.textContent = stats.tiempo_segundos + ' s';
    }
  }

  function setCoordsHint(text, type) {
    if (!coordsHint) return;
    if (!text) {
      coordsHint.style.display = 'none';
      coordsHint.textContent = '';
      coordsHint.className = 'hint small';
      return;
    }
    coordsHint.textContent = text;
    coordsHint.className = 'hint small ' + (type || '');
    coordsHint.style.display = 'block';
  }

  function setFileBoxMessage(text, type) {
    if (!fileBoxMessage) return;
    fileBoxMessage.textContent = text || '';
    fileBoxMessage.className = 'hint ' + (type || '');
  }

  async function prefillCoordsFromStore(lugar, opts) {
    if (!lugar || (!inputLatitud && !inputLongitud)) return;
    const latFilled = inputLatitud && inputLatitud.value;
    const lonFilled = inputLongitud && inputLongitud.value;
    if (latFilled && lonFilled) return;
    try {
      const url = '/api/lugar-coords?lugar=' + encodeURIComponent(lugar);
      const r = await fetch(url);
      const data = await r.json();
      if (data && data.ok && data.found && data.coords) {
        const lat = data.coords.lat || '';
        const lon = data.coords.lon || '';
        if (inputLatitud && !inputLatitud.value && lat) inputLatitud.value = lat;
        if (inputLongitud && !inputLongitud.value && lon) inputLongitud.value = lon;
        if (!opts || !opts.silent) {
          addLog('Coordenadas guardadas aplicadas para "' + (data.coords.lugar || lugar) + '".', 'info');
        }
        setCoordsHint('Coordenadas guardadas para "' + (data.coords.lugar || lugar) + '" listas.', 'info');
      } else if (!opts || !opts.silent) {
        setCoordsHint('Sin coordenadas guardadas para este lugar.', 'warn');
      }
    } catch (e) {
      if (!opts || !opts.silent) {
        setCoordsHint('No se pudieron cargar coordenadas guardadas.', 'error');
      }
    }
  }

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function setRunning(running) {
    btnStart.style.display = running ? 'none' : '';
    btnStop.style.display = running ? '' : 'none';
    btnStart.disabled = running;
    if (!running) {
      updateStartButton();
    }
    if (!running && progressActionsEl) {
      // Mostrar botón de descarga si hubo errores
      var failCount = parseInt(statFail.textContent, 10) || 0;
      if (failCount > 0) {
        progressActionsEl.style.display = 'block';
      }
    }
  }

  // ── Configuración ───────────────────────────────────────────────────────────

  async function loadConfig() {
    try {
      const r = await fetch('/api/config');
      const data = await r.json();
      const formUrl = data.form_url || '';
      currentFormUrl = formUrl;
      formUrlEl.href = formUrl || '#';
      formUrlEl.textContent = formUrl ? (formUrl.length > 50 ? formUrl.slice(0, 47) + '...' : formUrl) : '—';
      if (data.has_mapping) {
        mappingStatusEl.textContent = 'Mapeo configurado (' + Object.keys(data.mapping || {}).length + ' campos).';
        mappingStatusEl.className = 'mapping-status ok';
      } else {
        mappingStatusEl.textContent = 'Falta configurar mapping.yaml (ejecuta discover_form.py y copia a mapping.yaml).';
        mappingStatusEl.className = 'mapping-status warn';
      }
      var apiWrap = document.getElementById('apiToggleWrap');
      if (apiWrap) apiWrap.style.display = (data.use_kobo_api ? 'block' : 'none');
      if (data.use_kobo_api && document.getElementById('chkUsarApi')) document.getElementById('chkUsarApi').checked = true;
      uploadedFilename = null;
      uploadedFileType = null;
      uploadedOriginalName = null;
      uploadedFileEl.textContent = '';
      verifySectionEl.style.display = 'none';
      dataTableEl.innerHTML = '';
      extractedRecords = [];
      pdfExtractedRecords = [];
      dataConfirmed = false;
      if (validationSummaryEl) validationSummaryEl.style.display = 'none';
      if (btnDownloadExtracted) btnDownloadExtracted.style.display = 'none';
      updateStartButton();
    } catch (e) {
      mappingStatusEl.textContent = 'Error al cargar configuración.';
      mappingStatusEl.className = 'mapping-status warn';
    }
    logEl.innerHTML = '';
    setProgress(0, '—');
    statOk.textContent = '0';
    statFail.textContent = '0';
    statTime.textContent = '—';
    if (progressActionsEl) progressActionsEl.style.display = 'none';
    var btnDlFailed = document.getElementById('btnDownloadFailed');
    if (btnDlFailed) btnDlFailed.style.display = 'none';
    confirmRowSection.style.display = 'none';

    var inpEstado = document.getElementById('inputEstadoBrigada');
    if (inpEstado) inpEstado.value = '';
    if (inputLugar) inputLugar.value = '';
    if (inputLatitud) inputLatitud.value = '';
    if (inputLongitud) inputLongitud.value = '';
    setCoordsHint('');
    coordsRequired = false;

    loadFileBox();
    loadSummaryStats();
    loadCheckpoint();
  }

  function updateStartButton() {
    const hasMapping = mappingStatusEl.classList.contains('ok');
    const hasFile = !!uploadedFilename;
    const estado = (document.getElementById('inputEstadoBrigada') || {}).value || '';
    const lugar  = (inputLugar ? inputLugar.value : '').trim();
    const lat = (inputLatitud && inputLatitud.value || '').trim();
    const lon = (inputLongitud && inputLongitud.value || '').trim();
    const allLocationFilled = !!(estado.trim() && lugar && lat && lon);
    btnStart.disabled = !hasFile || !hasMapping || !allLocationFilled;

    var reasons = [];
    if (!hasFile) reasons.push('No se ha cargado un archivo Excel');
    if (!hasMapping) reasons.push('El mapeo de columnas no está configurado');
    if (!estado.trim()) reasons.push('Falta: Estado de la brigada');
    if (!lugar) reasons.push('Falta: Lugar (colegio/comunidad)');
    if (!lat) reasons.push('Falta: Latitud');
    if (!lon) reasons.push('Falta: Longitud');

    var wrapper = document.getElementById('btnStartWrapper');
    if (reasons.length > 0) {
      var tooltipText = 'No se puede iniciar:\n• ' + reasons.join('\n• ');
      if (wrapper) wrapper.setAttribute('data-tooltip', tooltipText);
      var locationMissing = reasons.filter(function(r) { return r.startsWith('Falta:'); });
      if (locationMissing.length > 0) {
        setCoordsHint('Completa: ' + locationMissing.map(function(r) { return r.replace('Falta: ', ''); }).join(', ') + ' antes de iniciar la carga.', 'error');
      }
    } else {
      if (wrapper) wrapper.setAttribute('data-tooltip', 'Todo listo. Haz clic para iniciar el llenado automático.');
      setCoordsHint('Datos de ubicación completos. Puedes iniciar la carga.', 'info');
    }
  }

  // ── Checkpoint ──────────────────────────────────────────────────────────────

  async function loadCheckpoint() {
    try {
      const r = await fetch('/api/checkpoint');
      const data = await r.json();
      if (data.ok && data.checkpoint) {
        const cp = data.checkpoint;
        resumeFormEl.style.display = 'block';
        inputStartRow.value = cp.last_row + 1;
        checkpointHintEl.textContent = 'Último guardado: fila ' + (cp.last_row + 1) + ' — ' + (cp.ts || '').slice(0, 16).replace('T', ' ');
      } else {
        resumeFormEl.style.display = 'none';
        inputStartRow.value = '';
        checkpointHintEl.textContent = '';
      }
    } catch (e) {
      // silencioso
    }
  }

  // Prefill coordenadas guardadas cuando el usuario escribe el lugar
  let lugarLookupTimeout = null;
  if (inputLugar) {
    inputLugar.addEventListener('input', function () {
      setCoordsHint('');
      if (lugarLookupTimeout) clearTimeout(lugarLookupTimeout);
      lugarLookupTimeout = setTimeout(function () {
        const val = (inputLugar.value || '').trim();
        if (!val) return;
        if ((inputLatitud && inputLatitud.value) || (inputLongitud && inputLongitud.value)) return;
        prefillCoordsFromStore(val, { silent: true });
      }, 450);
    });
    inputLugar.addEventListener('blur', function () {
      const val = (inputLugar.value || '').trim();
      if (!val) return;
      if ((inputLatitud && inputLatitud.value) && (inputLongitud && inputLongitud.value)) return;
      prefillCoordsFromStore(val, { silent: false });
    });
  }

  // Re-validar el botón de inicio cuando el usuario llena manualmente las coordenadas
  function onCoordsInput() {
    updateStartButton();
    const lat = (inputLatitud && inputLatitud.value || '').trim();
    const lon = (inputLongitud && inputLongitud.value || '').trim();
    if (lat && lon && coordsRequired) {
      setCoordsHint('Coordenadas ingresadas. Puedes iniciar la carga.', 'info');
    }
  }
  if (inputLatitud) inputLatitud.addEventListener('input', onCoordsInput);
  if (inputLongitud) inputLongitud.addEventListener('input', onCoordsInput);
  var _inputEstBrig = document.getElementById('inputEstadoBrigada');
  if (_inputEstBrig) _inputEstBrig.addEventListener('input', function() { updateStartButton(); });
  if (inputLugar) inputLugar.addEventListener('input', function() { updateStartButton(); });

  var btnStartWrapper = document.getElementById('btnStartWrapper');
  if (btnStartWrapper) {
    btnStartWrapper.addEventListener('click', function(e) {
      if (!btnStart.disabled) return;
      var tooltip = btnStartWrapper.getAttribute('data-tooltip') || '';
      if (tooltip) {
        alert(tooltip.replace(/\n/g, '\n'));
        var firstMissing = document.getElementById('inputEstadoBrigada');
        if (firstMissing && !firstMissing.value.trim()) { firstMissing.scrollIntoView({ behavior: 'smooth', block: 'center' }); firstMissing.focus(); return; }
        firstMissing = document.getElementById('inputLugar');
        if (firstMissing && !firstMissing.value.trim()) { firstMissing.scrollIntoView({ behavior: 'smooth', block: 'center' }); firstMissing.focus(); return; }
        firstMissing = document.getElementById('inputLatitud');
        if (firstMissing && !firstMissing.value) { firstMissing.scrollIntoView({ behavior: 'smooth', block: 'center' }); firstMissing.focus(); return; }
        firstMissing = document.getElementById('inputLongitud');
        if (firstMissing && !firstMissing.value) { firstMissing.scrollIntoView({ behavior: 'smooth', block: 'center' }); firstMissing.focus(); return; }
      }
    });
  }

  // ── Tabla de verificación ───────────────────────────────────────────────────

  var COLUMN_LABELS = {
    NAME: 'Nombre del Paciente', AGE: 'Edad', SEX: 'Sexo', DOB: 'Fecha nacimiento',
    HEI: 'Talla (cm)', WEI: 'Peso (kg)', HPI: 'Padecimiento',
    Diagn_stico: 'Diagnóstico', Fecha_de_atenci_n: 'Fecha atención',
    Estado: 'Estado', Estado_brigada: 'Estado brigada', Lugar: 'Lugar',
    Servicio_que_se_brinda: 'Servicio que se brinda',
    Diagnostico_Motivo: 'Padecimiento / Motivo',
    Resultados_Lab_Insumos: 'Insumos Entregados',
    entrega_tx: '¿Entrega Tratamiento?', Referencia: '¿Ref?',
    Referencia_donde: '¿A dónde?', Motivo_referencia: 'Motivo Ref.',
    CGR: 'Acompañante', estatus_migra: 'Estatus', followup: 'Primera vez / Seguimiento',
    Modalidad_de_la_atenci_n: 'Modalidad', CONS1: 'Consent.', _Pertenece_a_alguna_minor_a_t: 'Minoría',
    NAT: 'Nacionalidad', lat: 'Latitud', long: 'Longitud', alt: 'Altitud (m)', acc: 'Precisión (m)',
    ME_ML: '¿Embarazada / Lactancia?',
    Unidades_entregadas: 'Unidades entregadas',
    Especifique_qu_se_entrega: 'Especifica qué se entrega'
  };

  var COLUMN_SELECT_OPTIONS = {
    Servicio_que_se_brinda: [
      'Medicina General', 'Dental', 'Fisioterapia', 'Oftalmología', 'Laboratorios'
    ],
    SEX: ['Femenino', 'Masculino'],
    followup: ['Primera vez', 'Seguimiento', 'Atención Única', 'Entrega de Insumos'],
    entrega_tx: ['Sí', 'No'],
    ME_ML: ['Embarazada', 'Lactancia', 'No Aplica']
  };

  function normText(s) {
    return (s || '').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  function loadExcelForVerification() {
    fetch('/api/load-excel', { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) {
          addLog('Error: ' + data.error, 'error');
          return;
        }
        extractedRecords = data.records || [];
        var alreadySubmitted = data.already_submitted || [];
        renderTable(extractedRecords, alreadySubmitted);
        verifySectionEl.style.display = 'block';
        showCrossValidation(data.cross_validation);
        showValidationSummary(data.validation, alreadySubmitted);
        var msg = 'Excel cargado: ' + data.count + ' registros.';
        if (alreadySubmitted.length > 0) {
          msg += ' ' + alreadySubmitted.length + ' fila(s) ya cargada(s) anteriormente.';
        }
        var v = data.validation || {};
        if (v.valid != null) msg += ' ' + v.valid + ' completos.';
        addLog(msg + ' Listo para iniciar.', 'info');
        // Limpiar campos de ubicación para aplicar los del nuevo archivo
        var inpEstado = document.getElementById('inputEstadoBrigada');
        var inpLugar = document.getElementById('inputLugar');
        var inpLat = document.getElementById('inputLatitud');
        var inpLon = document.getElementById('inputLongitud');
        if (inpEstado) inpEstado.value = '';
        if (inpLugar) inpLugar.value = '';
        if (inpLat) inpLat.value = '';
        if (inpLon) inpLon.value = '';

        if (data.defaults) {
          if (data.defaults.Estado_brigada && inpEstado) inpEstado.value = data.defaults.Estado_brigada;
          if (data.defaults.Lugar && inpLugar) inpLugar.value = data.defaults.Lugar;
          if (data.defaults.Latitud && inpLat) inpLat.value = data.defaults.Latitud;
          if (data.defaults.Longitud && inpLon) inpLon.value = data.defaults.Longitud;
        }
        // Actualizar estado de coordenadas requeridas
        coordsRequired = !!data.coords_required;
        updateStartButton();

        if (data.coords_from_store) {
          var lugarLabel = data.coords_from_store;
          setCoordsHint('Coordenadas aplicadas para "' + lugarLabel + '".', 'info');
          addLog('Coordenadas aplicadas para ' + lugarLabel, 'info');
        } else if ((inpLat && inpLat.value) || (inpLon && inpLon.value)) {
          setCoordsHint('Coordenadas listas para usar.', 'info');
        } else if (!data.defaults || (!data.defaults.Lugar && !data.defaults.Estado_brigada)) {
          setCoordsHint('No se detectó lugar de atención conocido. Ingresa Estado, Lugar y Coordenadas manualmente si es necesario.', 'info');
        } else if (coordsRequired) {
          setCoordsHint('Coordenadas obligatorias: el lugar no fue reconocido. Ingresa Latitud y Longitud para continuar.', 'error');
        } else {
          setCoordsHint('');
        }
      })
      .catch(function (e) {
        addLog('Error al cargar Excel: ' + e.message, 'error');
      });
  }

  function showValidationSummary(v, alreadySubmitted) {
    if (!validationSummaryEl) return;
    lastValidation = v || null;
    lastAlreadySubmitted = alreadySubmitted || [];
    if (validationDetailEl) validationDetailEl.style.display = 'none';

    var parts = [];
    if (alreadySubmitted && alreadySubmitted.length > 0) {
      parts.push('<span class="val-submitted" data-vd-type="submitted">' + alreadySubmitted.length + ' fila(s) ya cargada(s) en Kobo (desmarcadas)</span>');
    }
    if (v && v.errors && v.errors.length > 0) {
      parts.push('<span class="val-error" data-vd-type="errors">\u26a0 ' + v.errors.length + ' fila(s) con errores obligatorios</span>');
    }
    if (v && v.duplicates && v.duplicates.length > 0) {
      parts.push('<span class="val-warn" data-vd-type="dupes">\u26a0 ' + v.duplicates.length + ' posible(s) fila(s) duplicada(s)</span>');
    }
    if (v && v.with_warnings > 0) {
      parts.push('<span class="val-info" data-vd-type="warnings">' + v.with_warnings + ' fila(s) con advertencias</span>');
    }
    if (parts.length === 0) {
      validationSummaryEl.style.display = 'none';
      return;
    }
    validationSummaryEl.innerHTML = parts.join(' \u00b7 ');
    validationSummaryEl.style.display = 'block';
  }

  function showValidationDetail(type) {
    if (!validationDetailEl) return;
    var v = lastValidation || {};
    var html = '';
    var headerClass = '';
    var title = '';
    var rows = [];

    if (type === 'errors' && v.errors && v.errors.length > 0) {
      headerClass = 'vd-errors';
      title = '\u26a0 Filas con errores obligatorios (' + v.errors.length + ')';
      v.errors.forEach(function (e) {
        rows.push('<div class="vd-row"><span class="vd-fila">Fila ' + e.fila + '</span><span class="vd-msg">' + escapeHtml(e.mensaje) + '</span></div>');
      });
      if (v.errors.length >= 30) {
        rows.push('<div class="vd-truncated">Mostrando las primeras 30 filas\u2026</div>');
      }
    } else if (type === 'warnings' && v.warnings && v.warnings.length > 0) {
      headerClass = 'vd-warnings';
      title = 'Filas con advertencias (' + v.with_warnings + ')';
      v.warnings.forEach(function (w) {
        rows.push('<div class="vd-row"><span class="vd-fila">Fila ' + w.fila + '</span><span class="vd-msg">' + escapeHtml(w.mensaje) + '</span></div>');
      });
      if (v.with_warnings > v.warnings.length) {
        rows.push('<div class="vd-truncated">Mostrando ' + v.warnings.length + ' de ' + v.with_warnings + ' filas\u2026</div>');
      }
    } else if (type === 'dupes' && v.duplicates && v.duplicates.length > 0) {
      headerClass = 'vd-dupes';
      title = '\u26a0 Posibles duplicados (' + v.duplicates.length + ')';
      v.duplicates.forEach(function (d) {
        var filasStr = d.filas.join(', ');
        var nombre = d.nombre || '(vac\u00edo)';
        var fecha = d.fecha || '(sin fecha)';
        rows.push('<div class="vd-row"><span class="vd-fila">Filas ' + filasStr + '</span><span class="vd-msg">' + escapeHtml(nombre) + ' \u2014 ' + escapeHtml(fecha) + '</span></div>');
      });
    } else if (type === 'submitted' && lastAlreadySubmitted.length > 0) {
      headerClass = 'vd-submitted';
      title = 'Filas ya cargadas en Kobo (' + lastAlreadySubmitted.length + ')';
      lastAlreadySubmitted.forEach(function (idx) {
        rows.push('<div class="vd-row"><span class="vd-fila">Fila ' + (idx + 1) + '</span><span class="vd-msg">Ya enviada anteriormente</span></div>');
      });
    } else {
      validationDetailEl.style.display = 'none';
      return;
    }

    html += '<div class="validation-detail">';
    html += '<div class="validation-detail-header ' + headerClass + '">';
    html += '<span>' + title + '</span>';
    html += '<button class="validation-detail-close" title="Cerrar">&times;</button>';
    html += '</div>';
    html += '<div class="validation-detail-body">' + rows.join('') + '</div>';
    html += '</div>';

    validationDetailEl.innerHTML = html;
    validationDetailEl.style.display = 'block';
    validationDetailEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  if (validationSummaryEl) {
    validationSummaryEl.addEventListener('click', function (ev) {
      var span = ev.target.closest('[data-vd-type]');
      if (!span) return;
      var type = span.getAttribute('data-vd-type');
      if (validationDetailEl && validationDetailEl.style.display !== 'none' &&
          validationDetailEl.querySelector('.validation-detail-header.' + 'vd-' + type)) {
        validationDetailEl.style.display = 'none';
        return;
      }
      showValidationDetail(type);
    });
  }

  if (validationDetailEl) {
    validationDetailEl.addEventListener('click', function (ev) {
      if (ev.target.closest('.validation-detail-close')) {
        validationDetailEl.style.display = 'none';
      }
    });
  }

  function renderTable(records, alreadySubmitted) {
    if (!records || records.length === 0) {
      dataTableEl.innerHTML = '<tr><td>Sin registros</td></tr>';
      return;
    }
    var submittedSet = {};
    (alreadySubmitted || []).forEach(function (i) { submittedSet[i] = true; });

    const cols = Object.keys(records[0]);
    let html = '<thead><tr>';
    html += '<th class="col-select"><input type="checkbox" id="selectAllRows" title="Seleccionar todas" checked></th>';
    html += '<th class="col-status" title="Estado de carga">Estado</th>';
    cols.forEach(function (c) {
      var label = COLUMN_LABELS[c] || c;
      html += '<th title="' + escapeHtml(c) + '">' + escapeHtml(label) + '</th>';
    });
    html += '</tr></thead><tbody>';
    records.forEach(function (rec, idx) {
      var isSubmitted = !!submittedSet[idx];
      html += '<tr data-row="' + idx + '"' + (isSubmitted ? ' class="row-already-submitted"' : '') + '>';
      html += '<td class="col-select"><input type="checkbox" class="row-select" data-row-index="' + idx + '"' + (isSubmitted ? '' : ' checked') + '></td>';
      html += '<td class="col-status">' + (isSubmitted ? '<span class="badge-submitted" title="Esta fila ya fue cargada exitosamente a Kobo">Cargada</span>' : '<span class="badge-pending">Pendiente</span>') + '</td>';
      cols.forEach(function (col) {
        const val = rec[col] != null ? String(rec[col]) : '';
        if (COLUMN_SELECT_OPTIONS[col]) {
          const opts = COLUMN_SELECT_OPTIONS[col];
          const valNorm = normText(val);
          let matchFound = false;
          let selectHtml = '<select data-col="' + escapeHtml(col) + '">';
          selectHtml += '<option value="">-- seleccionar --</option>';
          opts.forEach(function (opt) {
            const isSelected = valNorm && normText(opt) === valNorm;
            if (isSelected) matchFound = true;
            selectHtml += '<option value="' + escapeHtml(opt) + '"' + (isSelected ? ' selected' : '') + '>' + escapeHtml(opt) + '</option>';
          });
          if (val && !matchFound) {
            selectHtml += '<option value="' + escapeHtml(val) + '" selected>' + escapeHtml(val) + ' ⚠</option>';
          }
          selectHtml += '</select>';
          html += '<td>' + selectHtml + '</td>';
        } else {
          html += '<td><input type="text" value="' + escapeHtml(val) + '" data-col="' + escapeHtml(col) + '"></td>';
        }
      });
      html += '</tr>';
    });
    html += '</tbody>';
    dataTableEl.innerHTML = html;

    var selectAll = document.getElementById('selectAllRows');
    if (selectAll) {
      var hasSubmitted = (alreadySubmitted || []).length > 0;
      if (hasSubmitted) selectAll.checked = false;
      selectAll.addEventListener('change', function () {
        var checked = selectAll.checked;
        dataTableEl.querySelectorAll('.row-select').forEach(function (cb) { cb.checked = checked; });
      });
    }

    // Restaurar selección previa del usuario si la hubo (ej. después de "Guardar")
    if (_pendingRestoreIndices !== null) {
      var idxSet = new Set(_pendingRestoreIndices);
      dataTableEl.querySelectorAll('.row-select').forEach(function (cb) {
        var idx = parseInt(cb.getAttribute('data-row-index'), 10);
        cb.checked = idxSet.has(idx);
      });
      if (selectAll) {
        var allChecked = dataTableEl.querySelectorAll('.row-select').length > 0 &&
                         dataTableEl.querySelectorAll('.row-select:not(:checked)').length === 0;
        selectAll.checked = allChecked;
      }
      _pendingRestoreIndices = null;
    }
  }

  function getSelectedRowIndices() {
    var checked = dataTableEl.querySelectorAll('.row-select:checked');
    var indices = [];
    checked.forEach(function (cb) {
      var idx = parseInt(cb.getAttribute('data-row-index'), 10);
      if (!isNaN(idx)) indices.push(idx);
    });
    return indices.sort(function (a, b) { return a - b; });
  }

  function getRecordsFromTable() {
    const rows = dataTableEl.querySelectorAll('tbody tr');
    const records = [];
    rows.forEach(function (tr) {
      const rec = {};
      tr.querySelectorAll('input[data-col]').forEach(function (inp) {
        var col = inp.getAttribute('data-col');
        if (col) rec[col] = inp.value;
      });
      tr.querySelectorAll('select[data-col]').forEach(function (sel) {
        var col = sel.getAttribute('data-col');
        if (col) rec[col] = sel.value;
      });
      records.push(rec);
    });
    return records;
  }

  function renderPdfTable(records) {
    if (!pdfDataTableEl) return;
    if (!records || records.length === 0) {
      pdfDataTableEl.innerHTML = '<tr><td>Sin datos extraídos del PDF</td></tr>';
      return;
    }
    const cols = Object.keys(records[0]);
    let html = '<thead><tr>';
    cols.forEach(function (c) {
      var label = COLUMN_LABELS[c] || c;
      html += '<th title="' + escapeHtml(c) + '">' + escapeHtml(label) + '</th>';
    });
    html += '</tr></thead><tbody>';
    records.forEach(function (rec) {
      html += '<tr>';
      cols.forEach(function (col) {
        const val = rec[col] != null ? String(rec[col]) : '';
        html += '<td>' + escapeHtml(val) + '</td>';
      });
      html += '</tr>';
    });
    html += '</tbody>';
    pdfDataTableEl.innerHTML = html;
  }

  // ── Upload ──────────────────────────────────────────────────────────────────

  uploadZone.addEventListener('click', function () { fileInput.click(); });
  uploadZone.addEventListener('dragover', function (e) {
    e.preventDefault();
    uploadZone.classList.add('dragover');
  });
  uploadZone.addEventListener('dragleave', function () { uploadZone.classList.remove('dragover'); });
  uploadZone.addEventListener('drop', function (e) {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    const file = e.dataTransfer && e.dataTransfer.files[0];
    if (file && /\.(xlsx|xls|csv|pdf)$/i.test(file.name)) doUpload(file);
  });
  fileInput.addEventListener('change', function () {
    const file = fileInput.files[0];
    if (file) doUpload(file);
  });

  async function doUpload(file) {
    if (!/\.(xlsx|xls|csv|pdf)$/i.test(file.name)) {
      addLog('Solo se permiten archivos Excel (.xlsx, .xls), CSV (.csv) o PDF (.pdf)', 'error');
      return;
    }
    setCoordsHint('');
    coordsRequired = false;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await fetch('/api/upload', { method: 'POST', body: fd });
      const data = await r.json();
      if (data.error) { addLog('Error: ' + data.error, 'error'); return; }
      uploadedFilename = data.filename;
      uploadedFileType = data.type || 'excel';
      uploadedOriginalName = data.original_filename || data.filename;
      uploadedFileEl.textContent = 'Archivo cargado: ' + uploadedOriginalName;
      addLog('Archivo subido: ' + uploadedOriginalName, 'info');
      verifySectionEl.style.display = 'none';
      extractedRecords = [];
      pdfExtractedRecords = [];
      if (uploadedFileType === 'pdf') {
        await extractPdfAndPreview();
      } else {
        loadExcelForVerification();
      }
      updateStartButton();
    } catch (e) {
      addLog('Error al subir: ' + e.message, 'error');
    }
  }

  async function extractPdfAndPreview() {
    try {
      addLog('Extrayendo datos del PDF…', 'info');
      const r = await fetch('/api/extract-pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ backend: 'tesseract' })
      });
      const data = await r.json();
      if (data.error) { addLog('Error: ' + data.error, 'error'); return; }
      pdfExtractedRecords = data.records || [];
      renderPdfTable(pdfExtractedRecords);
      uploadedFilename = data.excel_filename || uploadedFilename;
      uploadedFileType = 'excel';
      addLog('PDF extraído: ' + (data.count || pdfExtractedRecords.length) + ' registros. Excel generado: ' + (data.excel_filename || ''), 'info');
      // Recargar tabla editable desde el Excel generado
      loadExcelForVerification();
      if (btnDownloadExtracted) btnDownloadExtracted.style.display = 'inline-flex';
      updateStartButton();
    } catch (e) {
      addLog('Error al extraer PDF: ' + e.message, 'error');
    }
  }

  // ── Verificación ─────────────────────────────────────────────────────────────

  btnConfirm.addEventListener('click', function () {
    const records = getRecordsFromTable();
    if (records.length === 0) { addLog('No hay registros para confirmar', 'error'); return; }
    btnConfirm.disabled = true;
    fetch('/api/use-extracted', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ records: records }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        btnConfirm.disabled = false;
        if (data.error) { addLog('Error: ' + data.error, 'error'); return; }
        uploadedFilename = data.filename;
        uploadedFileType = 'excel';
        dataConfirmed = true;
        uploadedFileEl.textContent = (uploadedOriginalName || data.filename) + ' — ' + data.rows + ' registros. Listo para Iniciar.';
        addLog('Datos confirmados. Listo para iniciar carga.', 'info');
        // Preservar selección actual para restaurarla después del re-render
        var currentSelection = getSelectedRowIndices();
        _pendingRestoreIndices = currentSelection.length > 0 ? currentSelection : null;
        loadExcelForVerification();
        updateStartButton();
      })
      .catch(function (e) {
        btnConfirm.disabled = false;
        addLog('Error: ' + e.message, 'error');
      });
  });

  if (btnSelectAll) {
    btnSelectAll.addEventListener('click', function () {
      var cb = document.getElementById('selectAllRows');
      if (cb) cb.checked = true;
      dataTableEl.querySelectorAll('.row-select').forEach(function (c) { c.checked = true; });
    });
  }
  if (btnSelectNone) {
    btnSelectNone.addEventListener('click', function () {
      var cb = document.getElementById('selectAllRows');
      if (cb) cb.checked = false;
      dataTableEl.querySelectorAll('.row-select').forEach(function (c) { c.checked = false; });
    });
  }

  // ── Iniciar / Detener ────────────────────────────────────────────────────────

  btnStart.addEventListener('click', function () {
    if (btnStart.disabled) return;

    var _estado = (document.getElementById('inputEstadoBrigada') || {}).value || '';
    var _lugar  = (document.getElementById('inputLugar') || {}).value || '';
    var _lat    = (document.getElementById('inputLatitud') || {}).value || '';
    var _lon    = (document.getElementById('inputLongitud') || {}).value || '';
    var camposFaltantes = [];
    if (!_estado.trim()) camposFaltantes.push('Estado de la brigada');
    if (!_lugar.trim())  camposFaltantes.push('Lugar (colegio/comunidad)');
    if (!_lat.trim())    camposFaltantes.push('Latitud');
    if (!_lon.trim())    camposFaltantes.push('Longitud');
    if (camposFaltantes.length > 0) {
      var msg = 'Faltan datos en "03 INICIAR CARGA":\n• ' + camposFaltantes.join('\n• ') +
                '\n\nLlena estos campos antes de iniciar la carga.';
      alert(msg);
      addLog('No se puede iniciar: faltan campos obligatorios (' + camposFaltantes.join(', ') + ').', 'error');
      var primerCampo = !_estado.trim() ? document.getElementById('inputEstadoBrigada') :
                        !_lugar.trim()  ? document.getElementById('inputLugar') :
                        !_lat.trim()    ? document.getElementById('inputLatitud') :
                                          document.getElementById('inputLongitud');
      if (primerCampo) { primerCampo.scrollIntoView({ behavior: 'smooth', block: 'center' }); primerCampo.focus(); }
      return;
    }

    var selectedIndices = getSelectedRowIndices();
    var hasTableRows = dataTableEl && dataTableEl.querySelectorAll('tbody tr').length > 0;
    if (hasTableRows && selectedIndices.length === 0) {
      addLog('Selecciona al menos una fila para cargar.', 'error');
      alert('Selecciona al menos una fila en la tabla para cargar.');
      return;
    }
    if (selectedIndices.length === 0) selectedIndices = null;

    setRunning(true);
    logEl.innerHTML = '';
    if (progressActionsEl) progressActionsEl.style.display = 'none';
    setProgress(0, 'Iniciando…');
    statOk.textContent = '0';
    statFail.textContent = '0';
    statTime.textContent = '—';
    addLog('Iniciando carga de ' + (selectedIndices ? selectedIndices.length : 'todas') + ' fila(s)…', 'info');
    var alertShown = false;

    if (activeEventSource) { activeEventSource.close(); activeEventSource = null; }

    function handleSSEMessage(ev) {
      try {
        var data = JSON.parse(ev.data);
        if (data.event === 'ping') return;
        if (data.message) {
          addLog(data.message, data.success === false ? 'error' : data.event === 'error' ? 'error' : 'info');
        }
        if (data.stats) updateStats(data.stats);
        if (data.row != null && data.total != null) {
          if (data.event === 'row_start') {
            var pctStart = Math.round(((data.row - 1) / data.total) * 100);
            setProgress(pctStart, 'Llenando fila ' + data.row + ' / ' + data.total + '…');
          } else {
            var pct = Math.round((data.row / data.total) * 100);
            setProgress(pct, 'Fila ' + data.row + ' / ' + data.total);
          }
        }
        if (data.event === 'waiting_for_confirm') {
          addLog('Fila ' + (data.row || '') + ' cargada. Revisa el formulario y valida.', 'info');
          confirmRowSection.style.display = 'block';
          confirmRowSection.scrollIntoView({ behavior: 'smooth' });
        }
        if (data.event === 'row_done') {
          confirmRowSection.style.display = 'none';
          if (data.success === false && data.message) {
            var rowLabel = (data.excel_row != null ? data.excel_row : data.row) || '';
            addLog('Fila ' + rowLabel + ' falló: ' + data.message, 'error');
            if (!alertShown) {
              alertShown = true;
              alert('Error en fila ' + (data.excel_row != null ? data.excel_row : data.row) + ':\n\n' + data.message);
            }
          }
        }
        if (data.event === 'error') {
          confirmRowSection.style.display = 'none';
          if (data.message && !alertShown) {
            alertShown = true;
            alert('Error:\n\n' + data.message);
          }
        }
        if (data.event === 'done' || data.event === 'error') {
          confirmRowSection.style.display = 'none';
          if (activeEventSource) { activeEventSource.close(); activeEventSource = null; }
          setRunning(false);
          if (data.stats && data.stats.tiempo_segundos != null) setProgress(100, 'Finalizado');
          if (data.has_failed_excel || (data.stats && (data.stats.fallidos || 0) > 0)) {
            var btnDl = document.getElementById('btnDownloadFailed');
            if (!btnDl && progressActionsEl) {
              btnDl = document.createElement('a');
              btnDl.id = 'btnDownloadFailed';
              btnDl.href = '/api/logs/download-failed-excel';
              btnDl.download = 'filas_fallidas.xlsx';
              btnDl.className = 'btn btn-warn';
              btnDl.textContent = '⬇ Descargar filas fallidas (.xlsx)';
              btnDl.style.marginTop = '8px';
              btnDl.style.display = 'inline-block';
              progressActionsEl.appendChild(btnDl);
            } else if (btnDl) {
              btnDl.style.display = 'inline-block';
            }
          }
          loadCheckpoint();
          loadHistorial();
          loadExcelForVerification();
          if (data.event === 'done' && activeKoboupFileId) {
            activeKoboupFileId = null;
            loadKoboupQueue();
          }
        }
      } catch (err) {
        addLog('Error al interpretar evento: ' + err.message, 'error');
      }
    }

    function handleSSEError() {
      if (activeEventSource) { activeEventSource.close(); activeEventSource = null; }
      fetch('/api/status').then(function (r) { return r.json(); }).then(function (st) {
        if (st.status === 'running') {
          addLog('Conexión perdida, reconectando…', 'info');
          setTimeout(connectSSE, 2000);
        } else {
          setRunning(false);
          setProgress(100, 'Finalizado');
          loadCheckpoint();
          loadHistorial();
          loadExcelForVerification();
        }
      }).catch(function () {
        setTimeout(function () {
          fetch('/api/status').then(function (r) { return r.json(); }).then(function (st) {
            if (st.status === 'running') { setTimeout(connectSSE, 2000); }
            else { setRunning(false); }
          }).catch(function () { setRunning(false); });
        }, 3000);
      });
    }

    function connectSSE() {
      if (activeEventSource) { activeEventSource.close(); }
      var src = new EventSource('/api/progress');
      activeEventSource = src;
      src.onmessage = handleSSEMessage;
      src.onerror = handleSSEError;
    }

    connectSSE();

    const estadoBrigada = (document.getElementById('inputEstadoBrigada') || {}).value.trim();
    const lugar = (document.getElementById('inputLugar') || {}).value.trim();
    const latitud = (document.getElementById('inputLatitud') || {}).value.trim();
    const longitud = (document.getElementById('inputLongitud') || {}).value.trim();
    const modoAutomatico = (document.getElementById('chkModoAutomatico') || {}).checked !== false;
    const useApi = (document.getElementById('chkUsarApi') || {}).checked === true;
    const startRowVal = inputStartRow ? inputStartRow.value.trim() : '';
    const defaults = {};
    if (estadoBrigada) defaults.Estado_brigada = estadoBrigada;
    if (lugar) defaults.Lugar = lugar;
    if (latitud) defaults.Latitud = latitud;
    if (longitud) defaults.Longitud = longitud;

    fetch('/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        defaults: defaults,
        wait_for_confirm: !modoAutomatico,
        auto_open_window: true,
        open_form_in_page: true,
        row_indices: selectedIndices,
        use_api: useApi,
        start_row: startRowVal ? parseInt(startRowVal, 10) : null,
      })
    })
      .then(function (r) {
        return r.json().then(function (data) {
          if (!r.ok) {
            addLog(data.error || 'Error al iniciar', 'error');
            if (r.status === 409) addLog('Recarga la página (F5) si quedó bloqueado.', 'info');
            setRunning(false);
            es.close();
            activeEventSource = null;
          }
        });
      })
      .catch(function (e) {
        addLog('Error: ' + e.message, 'error');
        setRunning(false);
        es.close();
        activeEventSource = null;
      });
  });

  btnStop.addEventListener('click', function () {
    btnStop.disabled = true;
    btnStop.textContent = 'Deteniendo…';
    fetch('/api/stop', { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        addLog(data.message || 'Señal de parada enviada.', 'info');
        btnStop.disabled = false;
        btnStop.textContent = 'Detener';
      })
      .catch(function (e) {
        addLog('Error al detener: ' + e.message, 'error');
        btnStop.disabled = false;
        btnStop.textContent = 'Detener';
      });
  });

  // ── Filebox (subir/listar/validar/descargar) ──────────────────────────────────

  var pendingFiles = [];

  function addPendingFiles(fileList) {
    var validExts = /\.(xlsx|xls|csv|pdf)$/i;
    for (var i = 0; i < fileList.length; i++) {
      var f = fileList[i];
      if (!validExts.test(f.name)) continue;
      var already = pendingFiles.some(function (p) { return p.name === f.name && p.size === f.size; });
      if (!already) pendingFiles.push(f);
    }
    renderPendingFiles();
  }

  function renderPendingFiles() {
    if (!fileBoxPending || !fileBoxPendingList || !fileBoxPendingCount) return;
    if (pendingFiles.length === 0) {
      fileBoxPending.style.display = 'none';
      return;
    }
    fileBoxPending.style.display = 'block';
    var excelCount = 0, pdfCount = 0;
    pendingFiles.forEach(function (f) {
      if (/\.pdf$/i.test(f.name)) pdfCount++;
      else excelCount++;
    });
    var parts = [];
    if (excelCount > 0) parts.push(excelCount + ' Excel/CSV');
    if (pdfCount > 0) parts.push(pdfCount + ' PDF');
    fileBoxPendingCount.textContent = pendingFiles.length + ' archivo(s) listos para subir (' + parts.join(', ') + ')';
    var html = '';
    pendingFiles.forEach(function (f, idx) {
      var sizeKb = Math.round(f.size / 1024);
      var icon = /\.pdf$/i.test(f.name) ? 'PDF' : 'XLS';
      html += '<li class="filebox-pending-item">';
      html += '<span class="filebox-pending-icon badge-' + icon.toLowerCase() + '">' + icon + '</span>';
      html += '<span class="filebox-pending-name">' + escapeHtml(f.name) + '</span>';
      html += '<span class="filebox-pending-size">' + sizeKb + ' KB</span>';
      html += '<button class="filebox-pending-remove" data-idx="' + idx + '" title="Quitar">&times;</button>';
      html += '</li>';
    });
    fileBoxPendingList.innerHTML = html;
  }

  if (fileBoxDropzone) {
    fileBoxDropzone.addEventListener('click', function () { fileBoxInput && fileBoxInput.click(); });
    fileBoxDropzone.addEventListener('dragover', function (e) {
      e.preventDefault();
      fileBoxDropzone.classList.add('dragover');
    });
    fileBoxDropzone.addEventListener('dragleave', function () { fileBoxDropzone.classList.remove('dragover'); });
    fileBoxDropzone.addEventListener('drop', function (e) {
      e.preventDefault();
      fileBoxDropzone.classList.remove('dragover');
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        addPendingFiles(e.dataTransfer.files);
      }
    });
  }
  if (fileBoxInput) {
    fileBoxInput.addEventListener('change', function () {
      if (fileBoxInput.files && fileBoxInput.files.length > 0) {
        addPendingFiles(fileBoxInput.files);
        fileBoxInput.value = '';
      }
    });
  }
  if (fileBoxPendingList) {
    fileBoxPendingList.addEventListener('click', function (ev) {
      var btn = ev.target.closest('.filebox-pending-remove');
      if (!btn) return;
      var idx = parseInt(btn.getAttribute('data-idx'), 10);
      if (!isNaN(idx) && idx >= 0 && idx < pendingFiles.length) {
        pendingFiles.splice(idx, 1);
        renderPendingFiles();
      }
    });
  }
  if (btnFileBoxClear) {
    btnFileBoxClear.addEventListener('click', function () {
      pendingFiles = [];
      renderPendingFiles();
      setFileBoxMessage('', '');
    });
  }

  async function loadFileBox() {
    try {
      const r = await fetch('/api/files');
      const data = await r.json();
      if (!data.ok) throw new Error(data.error || 'No se pudo listar archivos');
      fileBoxCache = data.files || [];
      renderFileBox();
    } catch (e) {
      setFileBoxMessage('Error al cargar archivos: ' + e.message, 'error');
    }
  }

  function renderFileBox() {
    if (!fileBoxList) return;
    if (!fileBoxCache || fileBoxCache.length === 0) {
      fileBoxList.innerHTML = '<p class="hint">Sin archivos cargados.</p>';
      return;
    }
    const rows = fileBoxCache.map(function (f) {
      const badge = f.status === 'validado'
        ? '<span class="badge-valid">Validado</span>'
        : '<span class="badge-pending">Pendiente</span>';
      const actions = [
        '<a class="filebox-link" href="' + (f.download_url || '#') + '" download>Descargar</a>',
      ];
      if (f.status !== 'validado') {
        actions.push('<button class="btn-file-validate" data-id="' + f.id + '">Marcar validado</button>');
      }
      actions.push('<button class="btn-file-delete" data-id="' + f.id + '">Eliminar</button>');
      const sizeText = f.size_bytes ? Math.round(f.size_bytes / 1024) + ' KB' : '';
      var typeIcon = (f.file_type === 'pdf') ? 'PDF' : 'XLS';
      return [
        '<div class="filebox-item" data-id="' + f.id + '">',
        '<div class="filebox-main">',
        '<div class="filebox-name"><span class="filebox-type-icon badge-' + typeIcon.toLowerCase() + '">' + typeIcon + '</span> ' + escapeHtml(f.original_name || f.stored_name) + '</div>',
        '<div class="filebox-meta">' + badge + ' · ' + escapeHtml(f.file_type || '') + (sizeText ? ' · ' + sizeText : '') + '</div>',
        f.notes ? '<div class="filebox-notes">Nota: ' + escapeHtml(f.notes) + '</div>' : '',
        '</div>',
        '<div class="filebox-actions">' + actions.join(' ') + '</div>',
        '</div>'
      ].join('');
    });
    fileBoxList.innerHTML = rows.join('');
  }

  function setFileBoxProgress(pct, text) {
    if (!fileBoxProgress || !fileBoxProgressBar || !fileBoxProgressText) return;
    fileBoxProgress.style.display = (pct >= 0) ? 'block' : 'none';
    fileBoxProgressBar.style.width = Math.min(100, Math.max(0, pct)) + '%';
    fileBoxProgressText.textContent = text || '';
  }

  async function uploadFileBox() {
    if (pendingFiles.length === 0) {
      setFileBoxMessage('Selecciona al menos un archivo Excel/PDF.', 'error');
      return;
    }
    var totalFiles = pendingFiles.length;
    var isBulk = totalFiles > 1;

    btnFileBoxUpload && (btnFileBoxUpload.disabled = true);
    setFileBoxMessage('', '');

    if (isBulk) {
      setFileBoxProgress(0, 'Subiendo 0 / ' + totalFiles + '…');
      var uploaded = 0;
      var failed = 0;
      var errorMessages = [];

      for (var i = 0; i < totalFiles; i++) {
        var file = pendingFiles[i];
        var fd = new FormData();
        fd.append('file', file);
        if (chkFileBoxValidated && chkFileBoxValidated.checked) {
          fd.append('mark_validated', 'true');
        }
        var noteVal = (fileBoxNote && fileBoxNote.value.trim()) || '';
        if (noteVal) fd.append('notes', noteVal);

        try {
          var r = await fetch('/api/files', { method: 'POST', body: fd });
          var data = await r.json();
          if (!data.ok && data.error) throw new Error(data.error);
          uploaded++;
        } catch (e) {
          failed++;
          errorMessages.push(file.name + ': ' + e.message);
        }
        var pct = Math.round(((i + 1) / totalFiles) * 100);
        setFileBoxProgress(pct, 'Subiendo ' + (i + 1) + ' / ' + totalFiles + '…');
      }

      setFileBoxProgress(-1, '');
      var resultMsg = uploaded + ' archivo(s) subido(s) exitosamente.';
      if (failed > 0) {
        resultMsg += ' ' + failed + ' fallido(s): ' + errorMessages.join('; ');
        setFileBoxMessage(resultMsg, 'warn');
      } else {
        setFileBoxMessage(resultMsg, 'ok');
      }
    } else {
      setFileBoxMessage('Subiendo…', 'info');
      var fd = new FormData();
      fd.append('file', pendingFiles[0]);
      if (chkFileBoxValidated && chkFileBoxValidated.checked) {
        fd.append('mark_validated', 'true');
      }
      var noteVal = (fileBoxNote && fileBoxNote.value.trim()) || '';
      if (noteVal) fd.append('notes', noteVal);

      try {
        var r = await fetch('/api/files', { method: 'POST', body: fd });
        var data = await r.json();
        if (!data.ok) throw new Error(data.error || 'Error al subir');
        setFileBoxMessage('Archivo subido exitosamente.', 'ok');
      } catch (e) {
        setFileBoxMessage('Error: ' + e.message, 'error');
        btnFileBoxUpload && (btnFileBoxUpload.disabled = false);
        return;
      }
    }

    pendingFiles = [];
    renderPendingFiles();
    if (fileBoxNote) fileBoxNote.value = '';
    if (chkFileBoxValidated) chkFileBoxValidated.checked = false;
    btnFileBoxUpload && (btnFileBoxUpload.disabled = false);
    await loadFileBox();
  }

  async function validateFileBox(id) {
    if (!id) return;
    setFileBoxMessage('Marcando como validado…', 'info');
    try {
      const r = await fetch('/api/files/' + id + '/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await r.json();
      if (!data.ok) throw new Error(data.error || 'Error al validar');
      setFileBoxMessage('Archivo marcado como validado.', 'ok');
      await loadFileBox();
    } catch (e) {
      setFileBoxMessage('Error: ' + e.message, 'error');
    }
  }

  async function deleteFileBox(id) {
    if (!id) return;
    if (!confirm('¿Eliminar este archivo? Esta acción no se puede deshacer.')) return;
    setFileBoxMessage('Eliminando…', 'info');
    try {
      const r = await fetch('/api/files/' + id, { method: 'DELETE' });
      const data = await r.json();
      if (!data.ok) throw new Error(data.error || 'Error al eliminar');
      setFileBoxMessage('Archivo eliminado.', 'ok');
      await loadFileBox();
    } catch (e) {
      setFileBoxMessage('Error: ' + e.message, 'error');
    }
  }

  if (btnFileBoxUpload) {
    btnFileBoxUpload.addEventListener('click', uploadFileBox);
  }
  if (fileBoxList) {
    fileBoxList.addEventListener('click', function (ev) {
      const btnValidate = ev.target.closest('.btn-file-validate');
      const btnDelete = ev.target.closest('.btn-file-delete');
      if (btnValidate) {
        const id = btnValidate.getAttribute('data-id');
        validateFileBox(id);
      } else if (btnDelete) {
        const id = btnDelete.getAttribute('data-id');
        deleteFileBox(id);
      }
    });
  }

  // ── Confirm row ──────────────────────────────────────────────────────────────

  function sendConfirmAction(action) {
    if (btnValidateSend.disabled) return;
    btnValidateSend.disabled = true;
    btnSkipRow.disabled = true;
    fetch('/api/confirm-row', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: action }),
    })
      .then(function () {
        addLog(action === 'confirm' ? 'Enviando formulario…' : 'Fila omitida.', 'info');
      })
      .finally(function () {
        btnValidateSend.disabled = false;
        btnSkipRow.disabled = false;
      });
  }
  btnValidateSend.addEventListener('click', function () { sendConfirmAction('confirm'); });
  btnSkipRow.addEventListener('click', function () { sendConfirmAction('skip'); });

  // ── Discover form ────────────────────────────────────────────────────────────

  btnDiscover.addEventListener('click', function () {
    if (!confirm('Se ejecutará discover_form.py para actualizar el mapeo desde el formulario.\n\nEsto puede tardar hasta 2 minutos. ¿Continuar?')) return;
    btnDiscover.disabled = true;
    btnDiscover.textContent = 'Ejecutando…';
    addLog('Ejecutando discover_form.py…', 'info');
    fetch('/api/discover', { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        btnDiscover.disabled = false;
        btnDiscover.textContent = 'Actualizar mapeo desde formulario';
        if (!data.ok && !data.mapping_discovered) {
          addLog('Error en discover: ' + (data.error || data.stderr || 'desconocido'), 'error');
          return;
        }
        discoveredYaml = data.mapping_discovered || '';
        addLog('Discover completado. El archivo mapping_discovered.yaml se generó.', 'info');
        if (discoveredYaml) {
          btnCopyDiscovered.style.display = '';
          addLog('Puedes copiar el mapping descubierto al editor con el botón "Copiar desde mapping_discovered".', 'info');
          // Abrir editor automáticamente con el discovered
          if (!mappingEditorSection || mappingEditorSection.style.display === 'none') {
            openMappingEditor(discoveredYaml);
          }
        }
      })
      .catch(function (e) {
        btnDiscover.disabled = false;
        btnDiscover.textContent = 'Actualizar mapeo desde formulario';
        addLog('Error: ' + e.message, 'error');
      });
  });

  // ── Mapping editor ───────────────────────────────────────────────────────────

  function openMappingEditor(initialContent) {
    mappingEditorSection.style.display = 'block';
    mappingEditorSection.scrollIntoView({ behavior: 'smooth' });
    if (initialContent != null) {
      mappingTextarea.value = initialContent;
    }
    mappingEditorMsg.textContent = '';
  }

  btnMappingEditor.addEventListener('click', function () {
    if (mappingEditorSection.style.display !== 'none') {
      mappingEditorSection.style.display = 'none';
      return;
    }
    fetch('/api/mapping')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        openMappingEditor(data.raw || '');
      })
      .catch(function (e) {
        addLog('Error al cargar mapping: ' + e.message, 'error');
      });
  });

  btnCopyDiscovered.addEventListener('click', function () {
    if (discoveredYaml) {
      mappingTextarea.value = discoveredYaml;
      mappingEditorMsg.textContent = 'Contenido de mapping_discovered copiado. Revisa y guarda.';
      mappingEditorMsg.className = 'mapping-editor-msg info';
    }
  });

  btnSaveMapping.addEventListener('click', function () {
    var raw = mappingTextarea.value.trim();
    if (!raw) { mappingEditorMsg.textContent = 'El mapping no puede estar vacío.'; mappingEditorMsg.className = 'mapping-editor-msg error'; return; }
    btnSaveMapping.disabled = true;
    fetch('/api/mapping', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw: raw }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        btnSaveMapping.disabled = false;
        if (data.error) {
          mappingEditorMsg.textContent = 'Error: ' + data.error;
          mappingEditorMsg.className = 'mapping-editor-msg error';
          return;
        }
        mappingEditorMsg.textContent = 'Mapping guardado (' + data.fields + ' campos). Recargando configuración…';
        mappingEditorMsg.className = 'mapping-editor-msg ok';
        setTimeout(function () {
          loadConfig();
          mappingEditorSection.style.display = 'none';
        }, 1200);
      })
      .catch(function (e) {
        btnSaveMapping.disabled = false;
        mappingEditorMsg.textContent = 'Error: ' + e.message;
        mappingEditorMsg.className = 'mapping-editor-msg error';
      });
  });

  btnCancelMapping.addEventListener('click', function () {
    mappingEditorSection.style.display = 'none';
  });

  // ── Historial ────────────────────────────────────────────────────────────────

  historialToggle.addEventListener('click', function () {
    var open = historialContent.style.display !== 'none';
    historialContent.style.display = open ? 'none' : 'block';
    if (!open) loadHistorial();
  });

  function updateSummaryStats(archivos, registros) {
    if (summaryArchivosEl) summaryArchivosEl.textContent = archivos;
    if (summaryRegistrosEl) summaryRegistrosEl.textContent = registros;
  }

  function loadSummaryStats() {
    fetch('/api/historial')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var entries = data.entries || [];
        var archivosSet = new Set();
        var totalRegistros = 0;
        entries.forEach(function (e) {
          var exitosos = Number(e.exitosos) || 0;
          var nombre = (e.archivo_original || e.archivo || '').trim();
          if (exitosos > 0 && nombre) archivosSet.add(nombre);
          totalRegistros += exitosos;
        });
        updateSummaryStats(archivosSet.size, totalRegistros);
      })
      .catch(function () { });
  }

  function updateSummaryFromEntries(entries) {
    var archivosSet = new Set();
    var totalRegistros = 0;
    (entries || []).forEach(function (e) {
      var exitosos = Number(e.exitosos) || 0;
      var nombre = (e.archivo_original || e.archivo || '').trim();
      if (exitosos > 0 && nombre) archivosSet.add(nombre);
      totalRegistros += exitosos;
    });
    updateSummaryStats(archivosSet.size, totalRegistros);
  }

  function renderKpiMetricCards(container, title, items, emptyText) {
    if (!container) return;
    if (!items || items.length === 0) {
      container.innerHTML = '<div class="kpi-card"><div class="kpi-label">' + escapeHtml(title) + '</div><div class="kpi-sub">' + escapeHtml(emptyText || 'Sin datos') + '</div></div>';
      return;
    }
    var html = items.map(function (item) {
      return '<div class="kpi-card">'
        + '<div class="kpi-label">' + escapeHtml(item.label || '') + '</div>'
        + '<div class="kpi-value">' + (item.count != null ? item.count : 0) + '</div>'
        + '<div class="kpi-sub">' + escapeHtml(title) + '</div>'
        + '</div>';
    }).join('');
    container.innerHTML = html;
  }

  function loadKpis() {
    if (!kpiSummaryEl || !kpiPatientsEl || !kpiConsultasEl) return;
    fetch('/api/kpis')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok || !data.kpis) return;
        var k = data.kpis;
        kpiPatientsEl.textContent = k.patients_registered || 0;
        kpiConsultasEl.textContent = k.total_consultations || 0;
        renderKpiMetricCards(kpiSpecialtiesEl, 'Consultas', k.specialties || [], 'Sin consultas registradas');
        renderKpiMetricCards(kpiSuppliesEl, 'Insumos entregados', k.supplies || [], 'Sin insumos registrados');
      })
      .catch(function () {
        if (kpiPatientsEl) kpiPatientsEl.textContent = '0';
        if (kpiConsultasEl) kpiConsultasEl.textContent = '0';
        if (kpiSpecialtiesEl) kpiSpecialtiesEl.innerHTML = '';
        if (kpiSuppliesEl) kpiSuppliesEl.innerHTML = '';
      });
  }

  function loadHistorial() {
    fetch('/api/historial')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var entries = data.entries || [];
        var archivosExitosos = data.archivos_exitosos || [];
        loadKpis();
        updateSummaryFromEntries(entries);
        renderHistorialArchivos(archivosExitosos);
        renderHistorial(entries);
      })
      .catch(function () { /* silencioso */ });
  }

  function renderHistorialArchivos(archivosExitosos) {
    if (!historialArchivos) return;
    if (!archivosExitosos || archivosExitosos.length === 0) {
      historialArchivos.innerHTML = '<p class="hint">No hay archivos con cargas exitosas.</p>';
      return;
    }
    var html = '<div class="hist-archivos-titulo">Archivos cargados con \u00e9xito a KoboToolbox</div>';
    html += '<div class="hist-archivos-grid">';
    archivosExitosos.forEach(function (a) {
      var nombre = a.nombre_original || '';
      var interno = a.archivo_interno || '';
      var esExcel = /\.(xlsx|xls|csv)$/i.test(interno || nombre);
      var fecha = (a.ultima_fecha || '').slice(0, 10);
      var pct = a.total > 0 ? Math.round((a.exitosos / a.total) * 100) : 0;
      var statusClass = pct === 100 ? 'hist-file-complete' : 'hist-file-partial';

      html += '<div class="hist-file-card ' + statusClass + '" data-preview-file="' + escapeHtml(interno) + '" data-preview-name="' + escapeHtml(nombre) + '" style="cursor:pointer">';
      html += '<div class="hist-file-header">';
      html += '<span class="hist-file-icon">' + (esExcel ? '\uD83D\uDCC4' : '\uD83D\uDCC4') + '</span>';
      html += '<span class="hist-file-name" title="' + escapeHtml(nombre) + '">' + escapeHtml(nombre) + '</span>';
      html += '</div>';
      html += '<div class="hist-file-stats">';
      html += '<div class="hist-file-bar-wrap"><div class="hist-file-bar" style="width:' + pct + '%"></div></div>';
      html += '<span class="hist-file-stat-line">' + a.exitosos + ' exitosos / ' + a.total + ' total (' + pct + '%)</span>';
      if (a.fallidos > 0) {
        html += '<span class="hist-file-fallidos">' + a.fallidos + ' fallidos</span>';
      }
      html += '<span class="hist-file-meta">' + a.cargas + ' carga(s) \u00b7 \u00daltima: ' + escapeHtml(fecha) + '</span>';
      html += '</div>';
      html += '<div class="hist-file-actions">';
      if (a.download_url) {
        html += '<a class="btn-hist-download" href="' + escapeHtml(a.download_url) + '" download title="Descargar archivo">\u2B07 Descargar</a>';
      }
      if (esExcel && interno) {
        html += '<button class="btn-hist-reload btn-hist-reload-small" data-filename="' + escapeHtml(interno) + '" data-original="' + escapeHtml(nombre) + '" title="Recargar en la tabla">\u21A9 Recargar</button>';
      }
      html += '</div>';
      html += '</div>';
    });
    html += '</div>';
    historialArchivos.innerHTML = html;
  }

  function renderHistorial(entries) {
    if (!historialList) return;
    if (entries.length === 0) {
      historialList.innerHTML = '<p class="hint">No hay cargas registradas en este período.</p>';
      return;
    }
    var html = '<table class="historial-table"><thead><tr><th>Fecha</th><th>Archivo original</th><th>Total</th><th title="Exitosos">✓</th><th title="Fallidos">✗</th><th>Tiempo</th></tr></thead><tbody>';
    entries.forEach(function (e) {
      var fecha = (e.fecha || '').slice(0, 16).replace('T', ' ');
      var rowClass = e.fallidos > 0 ? 'hist-row-warn' : 'hist-row-ok';
      var archivo = e.archivo || '';
      var archivoOriginal = e.archivo_original || archivo;
      var esExcel = /\.(xlsx|xls|csv)$/i.test(archivo);
      html += '<tr class="' + rowClass + '">';
      html += '<td>' + escapeHtml(fecha) + '</td>';
      if (esExcel) {
        html += '<td title="' + escapeHtml(archivoOriginal) + ' — clic para cargar en la tabla">';
        html += '<button class="btn-hist-reload" data-filename="' + escapeHtml(archivo) + '" data-original="' + escapeHtml(archivoOriginal) + '" title="Cargar en la tabla">';
        html += escapeHtml(archivoOriginal) + ' ↩';
        html += '</button></td>';
      } else {
        html += '<td title="' + escapeHtml(archivoOriginal) + '">' + escapeHtml(archivoOriginal || '—') + '</td>';
      }
      html += '<td>' + (e.total || 0) + '</td>';
      html += '<td class="hist-ok">' + (e.exitosos || 0) + '</td>';
      html += '<td class="hist-fail">' + (e.fallidos || 0) + '</td>';
      html += '<td>' + (e.tiempo_segundos || 0) + 's</td>';
      html += '</tr>';
    });
    html += '</tbody></table>';
    historialList.innerHTML = html;
  }

  // Clic en nombre de archivo del historial → recarga en la tabla
  function setupHistorialReload(container) {
    if (!container) return;
    container.addEventListener('click', function (ev) {
      var btn = ev.target.closest('.btn-hist-reload');
      if (!btn) return;
      var filename = btn.getAttribute('data-filename');
      var originalName = btn.getAttribute('data-original') || filename;
      if (!filename) return;
      var origText = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Cargando…';
      fetch('/api/reload-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: filename, original_filename: originalName }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          btn.disabled = false;
          btn.textContent = origText;
          if (data.error) {
            addLog('Error al recargar archivo: ' + data.error, 'error');
            return;
          }
          uploadedFilename = data.filename;
          uploadedFileType = data.type || 'excel';
          uploadedOriginalName = data.original_filename || data.filename;
          uploadedFileEl.textContent = 'Archivo cargado: ' + uploadedOriginalName;
          addLog('Archivo recargado desde historial: ' + uploadedOriginalName, 'info');
          verifySectionEl.style.display = 'none';
          extractedRecords = [];
          loadExcelForVerification();
          updateStartButton();
        })
        .catch(function (err) {
          btn.disabled = false;
          btn.textContent = origText;
          addLog('Error al recargar archivo: ' + err.message, 'error');
        });
    });
  }

  setupHistorialReload(historialList);
  setupHistorialReload(historialArchivos);

  // ── Modal vista previa de archivo ──────────────────────────────────────────

  var previewModal = document.getElementById('filePreviewModal');
  var previewTitle = document.getElementById('filePreviewTitle');
  var previewTable = document.getElementById('filePreviewTable');
  var previewLoading = document.getElementById('filePreviewLoading');
  var previewError = document.getElementById('filePreviewError');
  var previewInfo = document.getElementById('filePreviewInfo');
  var btnClosePreview = document.getElementById('btnClosePreview');

  function openFilePreview(filename, displayName) {
    if (!previewModal) return;
    previewTitle.textContent = displayName || filename;
    previewTable.innerHTML = '';
    previewError.style.display = 'none';
    previewInfo.textContent = '';
    previewLoading.style.display = 'flex';
    previewModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    fetch('/api/uploads/' + encodeURIComponent(filename) + '/preview')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        previewLoading.style.display = 'none';
        if (data.error) {
          previewError.textContent = data.error;
          previewError.style.display = 'block';
          return;
        }
        var headers = data.headers || [];
        var rows = data.rows || [];
        var info = rows.length + ' fila(s)';
        if (data.truncated) info += ' (mostrando primeras ' + rows.length + ' de ' + data.total_rows + ')';
        previewInfo.textContent = info;

        var html = '<thead><tr>';
        html += '<th class="row-num">#</th>';
        headers.forEach(function (h) {
          html += '<th>' + escapeHtml(h) + '</th>';
        });
        html += '</tr></thead><tbody>';
        rows.forEach(function (row, idx) {
          html += '<tr>';
          html += '<td class="row-num">' + (idx + 1) + '</td>';
          row.forEach(function (cell) {
            html += '<td>' + escapeHtml(String(cell)) + '</td>';
          });
          html += '</tr>';
        });
        html += '</tbody>';
        previewTable.innerHTML = html;
      })
      .catch(function (err) {
        previewLoading.style.display = 'none';
        previewError.textContent = 'Error al cargar: ' + err.message;
        previewError.style.display = 'block';
      });
  }

  function closeFilePreview() {
    if (!previewModal) return;
    previewModal.style.display = 'none';
    document.body.style.overflow = '';
    previewTable.innerHTML = '';
  }

  if (btnClosePreview) btnClosePreview.addEventListener('click', closeFilePreview);
  if (previewModal) {
    previewModal.addEventListener('click', function (ev) {
      if (ev.target === previewModal) closeFilePreview();
    });
  }
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape' && previewModal && previewModal.style.display !== 'none') closeFilePreview();
  });

  if (historialArchivos) {
    historialArchivos.addEventListener('click', function (ev) {
      var card = ev.target.closest('.hist-file-card');
      if (!card) return;
      if (ev.target.closest('.btn-hist-download') || ev.target.closest('.btn-hist-reload')) return;
      var filename = card.getAttribute('data-preview-file');
      var displayName = card.getAttribute('data-preview-name') || filename;
      if (filename) openFilePreview(filename, displayName);
    });
  }

  // ── Tooltips ────────────────────────────────────────────────────────────────

  (function initTooltips() {
    var bubble = document.createElement('div');
    bubble.className = 'tooltip-bubble';
    document.body.appendChild(bubble);
    var showTimer = null;
    var hideTimer = null;
    var activeTarget = null;

    function positionBubble(target) {
      var rect = target.getBoundingClientRect();
      var bw = bubble.offsetWidth;
      var bh = bubble.offsetHeight;
      var spaceBelow = window.innerHeight - rect.bottom;
      var above = spaceBelow < bh + 12;

      bubble.classList.toggle('tooltip-above', above);

      var top = above ? rect.top - bh - 8 : rect.bottom + 8;
      var left = rect.left + (rect.width / 2) - (bw / 2);
      left = Math.max(8, Math.min(left, window.innerWidth - bw - 8));
      top = Math.max(4, top);

      bubble.style.top = top + 'px';
      bubble.style.left = left + 'px';

      var arrowLeft = rect.left + (rect.width / 2) - left;
      arrowLeft = Math.max(12, Math.min(arrowLeft, bw - 12));
      bubble.style.setProperty('--arrow-left', arrowLeft + 'px');
      var arrow = bubble.querySelector('::before') || bubble;
      bubble.style.cssText += '';
    }

    function showTooltip(target) {
      var text = target.getAttribute('data-tooltip');
      if (!text) return;
      if (text.indexOf('\n') !== -1) {
        bubble.innerHTML = '';
        text.split('\n').forEach(function(line, i) {
          if (i > 0) bubble.appendChild(document.createElement('br'));
          bubble.appendChild(document.createTextNode(line));
        });
      } else {
        bubble.textContent = text;
      }
      bubble.classList.remove('visible', 'tooltip-above', 'tooltip-warning');
      if (target.disabled) bubble.classList.add('tooltip-warning');
      bubble.style.top = '-9999px';
      bubble.style.left = '-9999px';
      bubble.style.display = 'block';
      activeTarget = target;

      requestAnimationFrame(function () {
        positionBubble(target);
        requestAnimationFrame(function () {
          bubble.classList.add('visible');
        });
      });
    }

    function hideTooltip() {
      bubble.classList.remove('visible');
      activeTarget = null;
      setTimeout(function () {
        if (!activeTarget) bubble.style.display = 'none';
      }, 200);
    }

    document.addEventListener('mouseover', function (e) {
      var target = e.target.closest('[data-tooltip]');
      if (!target) return;
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      if (activeTarget === target) return;
      if (showTimer) clearTimeout(showTimer);
      showTimer = setTimeout(function () { showTooltip(target); }, 400);
    });

    document.addEventListener('mouseout', function (e) {
      var target = e.target.closest('[data-tooltip]');
      if (!target) return;
      if (showTimer) { clearTimeout(showTimer); showTimer = null; }
      hideTimer = setTimeout(hideTooltip, 150);
    });

    document.addEventListener('scroll', function () {
      if (activeTarget) positionBubble(activeTarget);
    }, true);

    window.addEventListener('resize', function () {
      if (activeTarget) hideTooltip();
    });
  })();

  // ── Help Guide System ──────────────────────────────────────────────────────

  (function initHelpGuide() {
    var overlay    = document.getElementById('guideOverlay');
    var overlayBg  = document.getElementById('guideOverlayBg');
    var popup      = document.getElementById('guidePopup');
    var arrow      = document.getElementById('guideArrow');
    var stepBadge  = document.getElementById('guideStepBadge');
    var stepTitle  = document.getElementById('guideStepTitle');
    var guideIcon  = document.getElementById('guideIcon');
    var guideStatus = document.getElementById('guideStatus');
    var guideDesc  = document.getElementById('guideDesc');
    var guideDots  = document.getElementById('guideDots');
    var btnPrev    = document.getElementById('guidePrev');
    var btnNext    = document.getElementById('guideNext');
    var btnClose   = document.getElementById('guideClose');
    var btnHelp    = document.getElementById('helpBtn');
    var pointer    = document.getElementById('guidePointer');

    if (!overlay || !popup || !btnHelp) return;

    var currentStep = 0;
    var guideActive = false;
    var highlightedEl = null;

    var STEPS = [
      {
        num: 1,
        title: 'Subir archivo',
        icon: '\uD83D\uDCC2',
        selector: '#uploadZone',
        scrollTo: '.upload.card',
        desc: 'Arrastra o haz clic aquí para subir tu archivo Excel, CSV o PDF con los datos de la brigada. Este es el primer paso obligatorio.',
        isDone: function() { return !!uploadedFilename; },
        pendingText: 'Pendiente: sube un archivo',
        doneText: 'Archivo cargado'
      },
      {
        num: 2,
        title: 'Verificar datos',
        icon: '\uD83D\uDD0D',
        selector: '#verifySection',
        scrollTo: '#verifySection',
        desc: 'Revisa la tabla con los datos extraídos. Puedes editar celdas, cambiar valores y seleccionar qué filas enviar. Luego haz clic en "Guardar cambios y continuar".',
        isDone: function() { return dataConfirmed; },
        pendingText: 'Opcional: revisa los datos',
        doneText: 'Datos verificados',
        showAlways: false
      },
      {
        num: 3,
        title: 'Configurar carga',
        icon: '\u2699\uFE0F',
        selector: '.start.card .defaults-form',
        scrollTo: '.start.card',
        desc: 'Completa el Estado de la brigada, Lugar y coordenadas GPS si es necesario. Elige si quieres modo automático o manual, y si usas API.',
        isDone: function() {
          var est = (document.getElementById('inputEstadoBrigada') || {}).value;
          var lug = (document.getElementById('inputLugar') || {}).value;
          return !!(est && est.trim()) || !!(lug && lug.trim());
        },
        pendingText: 'Completa los datos de la brigada',
        doneText: 'Datos configurados'
      },
      {
        num: 4,
        title: 'Iniciar carga',
        icon: '\uD83D\uDE80',
        selector: '#btnStart',
        scrollTo: '.start-actions',
        desc: 'Cuando todo esté listo, haz clic en "Iniciar carga" para comenzar el envío automático a KoboToolbox. Asegúrate de que el mapeo esté configurado.',
        isDone: function() {
          var ok = parseInt(statOk.textContent, 10) || 0;
          return ok > 0;
        },
        pendingText: 'Listo para iniciar',
        doneText: 'Carga realizada'
      },
      {
        num: 5,
        title: 'Seguir progreso',
        icon: '\uD83D\uDCCA',
        selector: '.progress.card',
        scrollTo: '.progress.card',
        desc: 'Observa el progreso en tiempo real: barra de avance, filas exitosas, fallidas y el log detallado. Al terminar podrás descargar el reporte de errores.',
        isDone: function() { return false; },
        pendingText: 'Se actualiza durante la carga',
        doneText: 'Progreso visible'
      }
    ];

    function getStepStates() {
      return STEPS.map(function(s) { return s.isDone(); });
    }

    function getFirstIncompleteStep() {
      var states = getStepStates();
      for (var i = 0; i < states.length; i++) {
        if (!states[i]) return i;
      }
      return 0;
    }

    function renderDots() {
      var states = getStepStates();
      var html = '';
      for (var i = 0; i < STEPS.length; i++) {
        var cls = 'guide-popup-dot';
        if (i === currentStep) cls += ' active';
        else if (states[i]) cls += ' done';
        html += '<div class="' + cls + '" data-step="' + i + '"></div>';
      }
      guideDots.innerHTML = html;
    }

    function clearHighlight() {
      if (highlightedEl) {
        highlightedEl.classList.remove('guide-highlight', 'guide-spotlight');
        highlightedEl = null;
      }
      pointer.style.display = 'none';
    }

    function highlightElement(el) {
      clearHighlight();
      if (!el) return;
      el.classList.add('guide-highlight', 'guide-spotlight');
      highlightedEl = el;
    }

    function positionPopup(targetEl) {
      if (!targetEl) {
        popup.style.top = '50%';
        popup.style.left = '50%';
        popup.style.transform = 'translate(-50%, -50%)';
        arrow.style.display = 'none';
        return;
      }

      var rect = targetEl.getBoundingClientRect();
      var pw = 340;
      var ph = popup.offsetHeight || 260;
      var margin = 16;

      var spaceBelow = window.innerHeight - rect.bottom;
      var spaceAbove = rect.top;
      var spaceRight = window.innerWidth - rect.right;

      var top, left;
      arrow.className = 'guide-popup-arrow';
      arrow.style.display = 'block';

      if (spaceBelow > ph + margin) {
        top = rect.bottom + margin;
        left = rect.left + (rect.width / 2) - (pw / 2);
        arrow.classList.add('arrow-top');
        arrow.style.top = '-7px';
        arrow.style.left = (pw / 2 - 7) + 'px';
        arrow.style.bottom = '';
      } else if (spaceAbove > ph + margin) {
        top = rect.top - ph - margin;
        left = rect.left + (rect.width / 2) - (pw / 2);
        arrow.classList.add('arrow-bottom');
        arrow.style.bottom = '-7px';
        arrow.style.top = '';
        arrow.style.left = (pw / 2 - 7) + 'px';
      } else {
        top = rect.top;
        left = rect.right + margin;
        if (left + pw > window.innerWidth - 16) {
          left = rect.left - pw - margin;
        }
        arrow.style.display = 'none';
      }

      left = Math.max(12, Math.min(left, window.innerWidth - pw - 12));
      top = Math.max(12, Math.min(top, window.innerHeight - ph - 12));

      popup.style.top = top + 'px';
      popup.style.left = left + 'px';
      popup.style.transform = 'none';

      showPointer(targetEl);
    }

    function showPointer(el) {
      if (!el) { pointer.style.display = 'none'; return; }
      var rect = el.getBoundingClientRect();
      pointer.textContent = '\uD83D\uDC47';
      pointer.className = 'guide-pointer point-down';
      pointer.style.display = 'block';
      pointer.style.top = (rect.top - 36) + 'px';
      pointer.style.left = (rect.left + rect.width / 2 - 16) + 'px';
    }

    function showStep(idx) {
      if (idx < 0) idx = 0;
      if (idx >= STEPS.length) idx = STEPS.length - 1;
      currentStep = idx;
      var step = STEPS[idx];
      var done = step.isDone();

      stepBadge.textContent = step.num;
      stepTitle.textContent = step.title;
      guideIcon.textContent = step.icon;
      guideDesc.textContent = step.desc;

      if (done) {
        guideStatus.textContent = '\u2713 ' + step.doneText;
        guideStatus.className = 'guide-popup-status done';
      } else {
        guideStatus.textContent = '\u25CB ' + step.pendingText;
        guideStatus.className = 'guide-popup-status pending';
      }

      btnPrev.style.display = idx === 0 ? 'none' : '';
      btnNext.textContent = idx === STEPS.length - 1 ? 'Cerrar' : 'Siguiente \u2192';

      renderDots();

      var targetEl = document.querySelector(step.selector);
      var scrollTarget = document.querySelector(step.scrollTo || step.selector);

      if (scrollTarget) {
        scrollTarget.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }

      setTimeout(function() {
        targetEl = document.querySelector(step.selector);
        highlightElement(targetEl);
        positionPopup(targetEl);

        popup.classList.remove('visible');
        requestAnimationFrame(function() {
          requestAnimationFrame(function() {
            popup.classList.add('visible');
          });
        });
      }, 350);
    }

    function openGuide(startStep) {
      if (guideActive) return;
      guideActive = true;
      overlay.classList.add('active');
      btnHelp.style.display = 'none';

      var idx = (startStep != null) ? startStep : getFirstIncompleteStep();
      showStep(idx);
    }

    function closeGuide() {
      guideActive = false;
      overlay.classList.remove('active');
      popup.classList.remove('visible');
      clearHighlight();
      pointer.style.display = 'none';
      btnHelp.style.display = 'flex';
    }

    btnHelp.addEventListener('click', function() { openGuide(); });
    btnClose.addEventListener('click', closeGuide);
    overlayBg.addEventListener('click', closeGuide);

    btnNext.addEventListener('click', function() {
      if (currentStep >= STEPS.length - 1) {
        closeGuide();
      } else {
        clearHighlight();
        popup.classList.remove('visible');
        showStep(currentStep + 1);
      }
    });

    btnPrev.addEventListener('click', function() {
      if (currentStep > 0) {
        clearHighlight();
        popup.classList.remove('visible');
        showStep(currentStep - 1);
      }
    });

    guideDots.addEventListener('click', function(ev) {
      var dot = ev.target.closest('.guide-popup-dot');
      if (!dot) return;
      var idx = parseInt(dot.getAttribute('data-step'), 10);
      if (!isNaN(idx)) {
        clearHighlight();
        popup.classList.remove('visible');
        showStep(idx);
      }
    });

    document.addEventListener('keydown', function(ev) {
      if (!guideActive) return;
      if (ev.key === 'Escape') closeGuide();
      if (ev.key === 'ArrowRight' || ev.key === 'ArrowDown') {
        ev.preventDefault();
        if (currentStep < STEPS.length - 1) {
          clearHighlight();
          popup.classList.remove('visible');
          showStep(currentStep + 1);
        }
      }
      if (ev.key === 'ArrowLeft' || ev.key === 'ArrowUp') {
        ev.preventDefault();
        if (currentStep > 0) {
          clearHighlight();
          popup.classList.remove('visible');
          showStep(currentStep - 1);
        }
      }
    });

    // Auto-detección: si el usuario intenta iniciar sin archivo, mostrar guía en paso 1
    var origBtnStartClick = btnStart.onclick;
    btnStart.addEventListener('click', function(ev) {
      if (!uploadedFilename && !guideActive) {
        ev.stopImmediatePropagation();
        ev.preventDefault();
        openGuide(0);
        return false;
      }
    }, true);

    // Pulso sutil en el botón de ayuda al inicio si no hay archivo cargado
    setTimeout(function() {
      if (!uploadedFilename) {
        btnHelp.classList.add('help-btn--attention');
        setTimeout(function() {
          btnHelp.classList.remove('help-btn--attention');
        }, 8000);
      }
    }, 3000);

    window._helpGuide = { open: openGuide, close: closeGuide };
  })();

  // ── KoboUp Queue ───────────────────────────────────────────────────────────

  function loadKoboupQueue() {
    if (!btnLoadKoboup) return;
    btnLoadKoboup.disabled = true;
    btnLoadKoboup.textContent = 'Cargando…';
    if (koboupStatus) koboupStatus.textContent = '';
    fetch('/api/koboup/files')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        btnLoadKoboup.disabled = false;
        btnLoadKoboup.textContent = 'Actualizar lista';
        if (data.error) {
          if (koboupStatus) koboupStatus.textContent = 'Error: ' + data.error;
          addLog('Error KoboUp: ' + data.error, 'error');
          return;
        }
        koboupFiles = data.files || [];
        if (koboupStatus) {
          koboupStatus.textContent = data.pending + ' pendiente(s) / ' + data.total + ' total';
        }
        renderKoboupList();
      })
      .catch(function (e) {
        btnLoadKoboup.disabled = false;
        btnLoadKoboup.textContent = 'Cargar lista de KoboUp';
        if (koboupStatus) koboupStatus.textContent = 'Sin conexión a KoboUp';
        addLog('Error al conectar con KoboUp: ' + e.message, 'error');
      });
  }

  function renderKoboupList() {
    if (!koboupListBody) return;
    if (koboupFiles.length === 0) {
      if (koboupListEl) koboupListEl.style.display = 'none';
      if (koboupEmpty) { koboupEmpty.style.display = 'block'; koboupEmpty.textContent = 'No hay archivos validados en KoboUp.'; }
      return;
    }
    if (koboupEmpty) koboupEmpty.style.display = 'none';
    if (koboupListEl) koboupListEl.style.display = 'block';

    var html = '';
    for (var i = 0; i < koboupFiles.length; i++) {
      var f = koboupFiles[i];
      var isActive = activeKoboupFileId && String(f.id) === String(activeKoboupFileId);
      var isDone = f.local_status === 'completed';
      var isPartial = f.local_status === 'partial';
      var rowClass = 'kq-row';
      if (isActive) rowClass += ' kq-active';
      if (isDone) rowClass += ' kq-done';

      var statusLabel = isDone ? '<span class="kq-badge kq-badge-done">Completado</span>'
        : isPartial ? '<span class="kq-badge kq-badge-active">Parcial</span>'
        : isActive ? '<span class="kq-badge kq-badge-active">En proceso</span>'
        : '<span class="kq-badge kq-badge-pending">Pendiente</span>';

      var actionBtn = isDone
        ? '<button class="btn btn-small btn-secondary kq-btn" disabled>Completado</button>'
        : isActive
        ? '<button class="btn btn-small btn-secondary kq-btn" disabled>En proceso</button>'
        : '<button class="btn btn-small btn-primary kq-btn" data-kq-idx="' + i + '">' + (isPartial ? 'Continuar' : 'Cargar') + '</button>';

      var sentCount = f.sent_count || 0;
      var totalRows = f.row_count || 0;
      var sentComplete = totalRows > 0 && sentCount >= totalRows;
      var sentPartial = sentCount > 0 && !sentComplete;
      var sentClass = sentComplete ? 'kq-sent-complete' : sentPartial ? 'kq-sent-partial' : 'kq-sent-zero';
      var sentLabel = '<span class="kq-sent ' + sentClass + '">' + sentCount + '/' + totalRows + '</span>';
      var statusSource = f.status_source || '';
      var statusDetail = statusSource
        ? '<div class="kq-status-detail" title="' + statusSource.replace(/"/g, '&quot;') + '">' + statusSource + '</div>'
        : '';

      html += '<div class="' + rowClass + '">'
        + '<span class="kq-col-num">' + (i + 1) + '</span>'
        + '<span class="kq-col-name" title="' + (f.original_name || '').replace(/"/g, '&quot;') + '">' + (f.original_name || 'Sin nombre') + '</span>'
        + '<span class="kq-col-sent">' + sentLabel + '</span>'
        + '<span class="kq-col-status">' + statusLabel + statusDetail + '</span>'
        + '<span class="kq-col-action">' + actionBtn + '</span>'
        + '</div>';
    }
    koboupListBody.innerHTML = html;
  }

  if (koboupListBody) {
    koboupListBody.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-kq-idx]');
      if (!btn) return;
      var idx = parseInt(btn.getAttribute('data-kq-idx'), 10);
      if (isNaN(idx) || !koboupFiles[idx]) return;
      selectKoboupFile(koboupFiles[idx], btn);
    });
  }

  function selectKoboupFile(fileInfo, btn) {
    if (btn) { btn.disabled = true; btn.textContent = 'Descargando…'; }
    activeKoboupFileId = String(fileInfo.id);
    addLog('Descargando de KoboUp: ' + fileInfo.original_name + '…', 'info');

    fetch('/api/koboup/load-file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        download_url: fileInfo.download_url,
        original_name: fileInfo.original_name,
        file_id: String(fileInfo.id),
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) {
          addLog('Error al descargar: ' + data.error, 'error');
          if (btn) { btn.disabled = false; btn.textContent = 'Cargar'; }
          return;
        }
        uploadedFilename = data.filename;
        uploadedFileType = data.type || 'excel';
        uploadedOriginalName = data.original_filename || data.filename;
        uploadedFileEl.textContent = 'Archivo cargado: ' + uploadedOriginalName;
        addLog('Archivo descargado y cargado: ' + uploadedOriginalName, 'info');
        renderKoboupList();
        loadExcelForVerification();
        updateStartButton();
      })
      .catch(function (e) {
        addLog('Error: ' + e.message, 'error');
        if (btn) { btn.disabled = false; btn.textContent = 'Cargar'; }
      });
  }

  if (btnLoadKoboup) {
    btnLoadKoboup.addEventListener('click', loadKoboupQueue);
  }

  // ── Cross Validation Panel ────────────────────────────────────────────────

  function showCrossValidation(cv) {
    if (!crossValidationPanel) return;
    if (!cv || !cv.summary) {
      crossValidationPanel.style.display = 'none';
      return;
    }
    var s = cv.summary;
    if (s.already_loaded === 0 && s.possible_dupes === 0) {
      crossValidationPanel.style.display = 'none';
      return;
    }

    var html = '<div class="cv-summary">';
    if (uploadedOriginalName) {
      html += '<div class="cv-filename">' + uploadedOriginalName + '</div>';
    }
    html += '<div class="cv-stats">';
    if (s.already_loaded > 0) {
      html += '<span class="cv-stat cv-stat-done">' + s.already_loaded + ' paciente(s) ya cargados a Kobo</span>';
    }
    if (s.possible_dupes > 0) {
      html += '<span class="cv-stat cv-stat-warn">' + s.possible_dupes + ' posible(s) duplicado(s) — revisar</span>';
    }
    html += '<span class="cv-stat cv-stat-new">' + s.new + ' paciente(s) nuevos listos para cargar</span>';
    html += '</div>';

    if (cv.possible_duplicates && cv.possible_duplicates.length > 0) {
      html += '<details class="cv-details"><summary>Ver detalle de posibles duplicados</summary><div class="cv-dupes-list">';
      for (var i = 0; i < cv.possible_duplicates.length; i++) {
        var d = cv.possible_duplicates[i];
        html += '<div class="cv-dupe-item"><strong>Fila ' + (d.index + 1) + ':</strong> ' + d.name;
        if (d.matched_with && d.matched_with.length > 0) {
          html += ' — coincide con: ';
          for (var j = 0; j < d.matched_with.length; j++) {
            var m = d.matched_with[j];
            html += '<em>' + m.name + '</em> (' + (m.service || '') + ', ' + (m.date || '') + ', ' + (m.file || '') + ')';
            if (j < d.matched_with.length - 1) html += '; ';
          }
        }
        html += '</div>';
      }
      html += '</div></details>';
    }

    if (s.new > 0 && (s.already_loaded > 0 || s.possible_dupes > 0)) {
      html += '<div class="cv-action"><button type="button" class="btn btn-small btn-primary" id="btnSelectNewOnly">Seleccionar solo ' + s.new + ' nuevos</button></div>';
    }
    html += '</div>';
    crossValidationPanel.innerHTML = html;
    crossValidationPanel.style.display = 'block';

    var btnNewOnly = document.getElementById('btnSelectNewOnly');
    if (btnNewOnly && cv.new_records) {
      btnNewOnly.addEventListener('click', function () {
        selectOnlyIndices(cv.new_records);
        addLog('Seleccionadas solo las ' + cv.new_records.length + ' filas nuevas.', 'info');
      });
    }
  }

  function selectOnlyIndices(indices) {
    var checkboxes = dataTableEl.querySelectorAll('input[type="checkbox"][data-row-idx]');
    var indexSet = {};
    for (var i = 0; i < indices.length; i++) indexSet[indices[i]] = true;
    for (var j = 0; j < checkboxes.length; j++) {
      var idx = parseInt(checkboxes[j].getAttribute('data-row-idx'), 10);
      checkboxes[j].checked = !!indexSet[idx];
    }
  }

  // ── Init ─────────────────────────────────────────────────────────────────────

  loadConfig();
})();

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
  const btnRefreshHistorial = document.getElementById('btnRefreshHistorial');

  let uploadedFilename = null;
  let uploadedFileType = null;
  let extractedRecords = [];
  let pdfExtractedRecords = [];
  // true cuando el servidor indica que no pudo determinar coords automáticamente
  let coordsRequired = false;

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
      btnStart.disabled = !(uploadedFilename && mappingStatusEl.classList.contains('ok'));
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
      if (data.uploaded_file) {
        uploadedFilename = data.uploaded_file;
        uploadedFileType = 'excel';
        dataConfirmed = false;
        uploadedFileEl.textContent = 'Archivo cargado: ' + data.uploaded_file;
        verifySectionEl.style.display = 'none';
        loadExcelForVerification();
        if (btnDownloadExtracted) btnDownloadExtracted.style.display = 'inline-flex';
      } else {
        uploadedFilename = null;
        uploadedFileType = null;
        uploadedFileEl.textContent = '';
        verifySectionEl.style.display = 'none';
        if (btnDownloadExtracted) btnDownloadExtracted.style.display = 'none';
      }
      updateStartButton();
    } catch (e) {
      mappingStatusEl.textContent = 'Error al cargar configuración.';
      mappingStatusEl.className = 'mapping-status warn';
    }
    // Cargar checkpoint para mostrar opción de reanudación
    loadCheckpoint();
  }

  function updateStartButton() {
    const hasMapping = mappingStatusEl.classList.contains('ok');
    const hasFile = !!uploadedFilename;
    const lat = (inputLatitud && inputLatitud.value || '').trim();
    const lon = (inputLongitud && inputLongitud.value || '').trim();
    const hasCoords = !!(lat && lon);
    const coordsMissing = coordsRequired && !hasCoords;
    btnStart.disabled = !hasFile || !hasMapping || coordsMissing;
    if (coordsMissing) {
      setCoordsHint('Coordenadas obligatorias: ingresa Latitud y Longitud antes de iniciar.', 'error');
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
        showValidationSummary(data.validation, alreadySubmitted);
        var msg = 'Excel cargado: ' + data.count + ' registros.';
        if (alreadySubmitted.length > 0) {
          msg += ' ' + alreadySubmitted.length + ' fila(s) ya cargada(s) anteriormente.';
        }
        var v = data.validation || {};
        if (v.valid != null) msg += ' ' + v.valid + ' completos.';
        addLog(msg + ' Listo para iniciar.', 'info');
        if (data.defaults) {
          if (data.defaults.Estado_brigada) {
            var inpEstado = document.getElementById('inputEstadoBrigada');
            if (inpEstado && !inpEstado.value) inpEstado.value = data.defaults.Estado_brigada;
          }
          if (data.defaults.Lugar) {
            var inpLugar = document.getElementById('inputLugar');
            if (inpLugar && !inpLugar.value) inpLugar.value = data.defaults.Lugar;
          }
          if (data.defaults.Latitud) {
            var inpLat = document.getElementById('inputLatitud');
            if (inpLat && !inpLat.value) inpLat.value = data.defaults.Latitud;
          }
          if (data.defaults.Longitud) {
            var inpLon = document.getElementById('inputLongitud');
            if (inpLon && !inpLon.value) inpLon.value = data.defaults.Longitud;
          }
        }
        // Actualizar estado de coordenadas requeridas
        coordsRequired = !!data.coords_required;
        updateStartButton();

        if (data.coords_from_store) {
          var lugarLabel = data.coords_from_store;
          setCoordsHint('Coordenadas aplicadas para "' + lugarLabel + '".', 'info');
          addLog('Coordenadas aplicadas para ' + lugarLabel, 'info');
        } else if ((inputLatitud && inputLatitud.value) || (inputLongitud && inputLongitud.value)) {
          setCoordsHint('Coordenadas listas para usar.', 'info');
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
    var parts = [];
    if (alreadySubmitted && alreadySubmitted.length > 0) {
      parts.push('<span class="val-submitted">' + alreadySubmitted.length + ' fila(s) ya cargada(s) en Kobo (desmarcadas)</span>');
    }
    if (v && v.errors && v.errors.length > 0) {
      parts.push('<span class="val-error">⚠ ' + v.errors.length + ' fila(s) con errores obligatorios</span>');
    }
    if (v && v.duplicates && v.duplicates.length > 0) {
      parts.push('<span class="val-warn">⚠ ' + v.duplicates.length + ' posible(s) fila(s) duplicada(s)</span>');
    }
    if (v && v.with_warnings > 0) {
      parts.push('<span class="val-info">' + v.with_warnings + ' fila(s) con advertencias</span>');
    }
    if (parts.length === 0) {
      validationSummaryEl.style.display = 'none';
      return;
    }
    validationSummaryEl.innerHTML = parts.join(' · ');
    validationSummaryEl.style.display = 'block';
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
      uploadedFileEl.textContent = 'Archivo cargado: ' + data.filename;
      addLog('Archivo subido: ' + data.filename, 'info');
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
        uploadedFileEl.textContent = 'Datos confirmados: ' + data.rows + ' registros. Listo para Iniciar.';
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
    const es = new EventSource('/api/progress');
    activeEventSource = es;

    es.onmessage = function (ev) {
      try {
        const data = JSON.parse(ev.data);
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
          es.close();
          activeEventSource = null;
          setRunning(false);
          if (data.stats && data.stats.tiempo_segundos != null) setProgress(100, 'Finalizado');
          // Mostrar botón de descarga de filas fallidas si corresponde
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
        }
      } catch (err) {
        addLog('Error al interpretar evento: ' + err.message, 'error');
      }
    };
    es.onerror = function () {
      es.close();
      activeEventSource = null;
      setRunning(false);
    };

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

  if (btnRefreshHistorial) {
    btnRefreshHistorial.addEventListener('click', function () { loadHistorial(); });
  }

  function loadHistorial() {
    fetch('/api/historial')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderHistorial(data.entries || []);
      })
      .catch(function () { /* silencioso */ });
  }

  function renderHistorial(entries) {
    if (!historialList) return;
    if (entries.length === 0) {
      historialList.innerHTML = '<p class="hint">Aún no hay cargas registradas.</p>';
      return;
    }
    var html = '<table class="historial-table"><thead><tr><th>Fecha</th><th>Archivo</th><th>Total</th><th title="Exitosos">✓</th><th title="Fallidos">✗</th><th>Tiempo</th></tr></thead><tbody>';
    entries.forEach(function (e) {
      var fecha = (e.fecha || '').slice(0, 16).replace('T', ' ');
      var rowClass = e.fallidos > 0 ? 'hist-row-warn' : 'hist-row-ok';
      var archivo = e.archivo || '';
      var esExcel = /\.(xlsx|xls|csv)$/i.test(archivo);
      html += '<tr class="' + rowClass + '">';
      html += '<td>' + escapeHtml(fecha) + '</td>';
      if (esExcel) {
        html += '<td title="' + escapeHtml(archivo) + ' — clic para cargar en la tabla">';
        html += '<button class="btn-hist-reload" data-filename="' + escapeHtml(archivo) + '" title="Cargar en la tabla">';
        html += escapeHtml(archivo.slice(0, 20)) + (archivo.length > 20 ? '…' : '') + ' ↩';
        html += '</button></td>';
      } else {
        html += '<td title="' + escapeHtml(archivo) + '">' + escapeHtml(archivo.slice(0, 20) || '—') + '</td>';
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
  if (historialList) {
    historialList.addEventListener('click', function (ev) {
      var btn = ev.target.closest('.btn-hist-reload');
      if (!btn) return;
      var filename = btn.getAttribute('data-filename');
      if (!filename) return;
      btn.disabled = true;
      btn.textContent = 'Cargando…';
      fetch('/api/reload-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: filename }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          btn.disabled = false;
          btn.textContent = filename.slice(0, 20) + (filename.length > 20 ? '…' : '') + ' ↩';
          if (data.error) {
            addLog('Error al recargar archivo: ' + data.error, 'error');
            return;
          }
          uploadedFilename = data.filename;
          uploadedFileType = data.type || 'excel';
          uploadedFileEl.textContent = 'Archivo cargado: ' + data.filename;
          addLog('Archivo recargado desde historial: ' + data.filename, 'info');
          verifySectionEl.style.display = 'none';
          extractedRecords = [];
          loadExcelForVerification();
          updateStartButton();
        })
        .catch(function (err) {
          btn.disabled = false;
          btn.textContent = filename.slice(0, 20) + (filename.length > 20 ? '…' : '') + ' ↩';
          addLog('Error al recargar archivo: ' + err.message, 'error');
        });
    });
  }

  // ── Init ─────────────────────────────────────────────────────────────────────

  loadConfig();
})();

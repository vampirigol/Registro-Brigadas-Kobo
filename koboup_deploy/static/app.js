(function () {
  /* ═══════════════ ELEMENTOS DOM ═══════════════ */

  // Secciones principales
  var sectionWork = document.getElementById('sectionWork');
  var sectionRefs = document.getElementById('sectionRefs');
  var sectionRanking = document.getElementById('sectionRanking');
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

  navBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      navBtns.forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      var section = btn.getAttribute('data-section');
      sectionWork.style.display = 'none';
      sectionRefs.style.display = 'none';
      sectionRanking.style.display = 'none';
      if (section === 'refs') {
        sectionRefs.style.display = '';
        loadRefs();
      } else if (section === 'ranking') {
        sectionRanking.style.display = '';
        loadRanking();
      } else {
        sectionWork.style.display = '';
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
      xhr.open('POST', 'api/files');
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
        var r = await fetch('api/files', { method: 'POST', body: fd });
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
      var r = await fetch('api/files/download-validated-zip', {
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
      var r = await fetch('api/files');
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
    fetch('api/stats/records').then(function (r) { return r.json(); }).then(function (data) {
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

      var actions = [];
      if (isSuperseded) {
        actions.push('<button class="btn btn-outline btn-sm js-delete" data-id="' + f.id + '" title="Eliminar">' +
          '<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg></button>');
      } else {
        actions.push('<button class="btn btn-outline btn-sm js-download" data-id="' + f.id + '" data-url="' + (f.download_url || '') + '" data-name="' + esc(f.original_name || f.stored_name) + '">' +
          '<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Descargar</button>');

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
      if (f.row_count != null && f.row_count > 0) meta += '<span class="sep">·</span><span class="file-row-count">' + fmtNum(f.row_count) + ' registros</span>';
      if (f.size_bytes) meta += '<span class="sep">·</span>' + fmtSize(f.size_bytes);
      meta += '<span class="sep">·</span>' + timeSince(f.created_at);

      var people = '';
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

      return '<div class="file-row' + (isSuperseded ? ' file-row-superseded' : '') + '" data-id="' + f.id + '">' +
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
    var vBtn = ev.target.closest('.js-validate');
    var dBtn = ev.target.closest('.js-delete');
    var rBtn = ev.target.closest('.js-to-review');
    if (dlBtn) openDownloadModal(dlBtn.getAttribute('data-id'), dlBtn.getAttribute('data-url'), dlBtn.getAttribute('data-name'));
    else if (vBtn) openValidateModal(vBtn.getAttribute('data-id'), vBtn.getAttribute('data-name'));
    else if (rBtn) changeStatus(rBtn.getAttribute('data-id'), 'por_validar');
    else if (dBtn) deleteFile(dBtn.getAttribute('data-id'));
  });

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
      var r = await fetch('api/files', { method: 'POST', body: fd });
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
      var r = await fetch('api/files/' + pendingValidateId + '/replace-with', {
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
      var r = await fetch('api/files/' + id + '/status', {
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
      var r = await fetch('api/files/' + id, { method: 'DELETE' });
      var data = await r.json();
      if (!data.ok) throw new Error(data.error || 'Error');
      await loadFiles();
    } catch (e) {
      alert('Error al eliminar: ' + e.message);
    }
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
      await fetch('api/files/' + pendingDownload.id + '/register-download', {
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
      var rr = await fetch('api/refs');
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

      xhr.open('POST', 'api/refs');
      xhr.send(fd);
    });
  }

  async function doRefUpload(files, name, loc, noteVal, idsToDelete) {
    btnRefUpload.disabled = true;

    for (var d = 0; d < idsToDelete.length; d++) {
      try {
        await fetch('api/refs/' + idsToDelete[d], { method: 'DELETE' });
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
      var r = await fetch('api/refs');
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
      var r = await fetch('api/refs/locations');
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
      actions += '<a class="btn btn-outline btn-sm" href="' + (r.download_url || '') + '" download>' +
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
      var r = await fetch('api/refs/' + id, { method: 'DELETE' });
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
        positionHtml = '<div class="rank-position">\uD83D\uDCA9</div>';
      } else {
        positionHtml = '<div class="rank-position"><div class="rank-position-number">' + pos + '</div></div>';
      }

      var badgeHtml = '';
      if (medal) {
        badgeHtml = '<span class="rank-badge rank-badge-' + medal.badge + '">' + medal.emoji + ' ' + medal.label + '</span>';
      } else if (isLast) {
        badgeHtml = '<span class="rank-badge rank-badge-last">\uD83D\uDCA9 Ultimo lugar</span>';
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
      var r = await fetch('api/stats/ranking');
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

  /* ═══════════════ INICIO ═══════════════ */
  loadFiles();
})();

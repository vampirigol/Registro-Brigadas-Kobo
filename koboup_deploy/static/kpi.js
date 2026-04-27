(function () {
  var u = typeof window.kobuUrl === 'function' ? window.kobuUrl : function (p) { return p; };

  var kpiPatients = document.getElementById('kpiPatients');
  var kpiPatientsDetail = document.getElementById('kpiPatientsDetail');
  var kpiPatientsCount = document.getElementById('kpiPatientsCount');
  var kpiConsultations = document.getElementById('kpiConsultations');
  var kpiSuppliesTotal = document.getElementById('kpiSuppliesTotal');
  var kpiGrandTotal = document.getElementById('kpiGrandTotal');
  var kpiSpecialties = document.getElementById('kpiSpecialties');
  var kpiSupplies = document.getElementById('kpiSupplies');
  var kpiDentalProcedures = document.getElementById('kpiDentalProcedures');
  var kpiSuppliesByFile = document.getElementById('kpiSuppliesByFile');
  var isUpdatingExclusion = false;

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function fmtNum(n) {
    return Number(n || 0).toLocaleString('es-MX');
  }

  function renderKpiCards(container, items, emptyText) {
    if (!container) return;
    if (!items || items.length === 0) {
      container.innerHTML = '<div class="kpi-mini-card"><div class="kpi-mini-sub">' + esc(emptyText || 'Sin datos') + '</div></div>';
      return;
    }
    container.innerHTML = items.map(function (item) {
      return '<div class="kpi-mini-card">'
        + '<div class="kpi-mini-label">' + esc(item.label || '') + '</div>'
        + '<div class="kpi-mini-value">' + fmtNum(item.count || 0) + '</div>'
        + '<div class="kpi-mini-sub">Registros únicos</div>'
        + '</div>';
    }).join('');
  }

  function toggleFileExclusion(fileName, excluded) {
    if (isUpdatingExclusion) return;
    isUpdatingExclusion = true;
    fetch(u('api/stats/kpis/exclusions'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_name: fileName, excluded: excluded })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) throw new Error(data.error || 'No se pudo actualizar');
        loadPublicKpis();
      })
      .catch(function () {
        isUpdatingExclusion = false;
      });
  }

  function renderSuppliesTable(rows) {
    if (!kpiSuppliesByFile) return;
    if (!rows || rows.length === 0) {
      kpiSuppliesByFile.innerHTML = '<tr><td colspan="6" class="kpi-table-empty">Sin datos por archivo</td></tr>';
      return;
    }
    kpiSuppliesByFile.innerHTML = rows.map(function (row) {
      var actionLabel = row.excluded ? 'Restaurar' : 'Excluir';
      var actionClass = row.excluded ? 'btn-restore' : 'btn-exclude';
      return '<tr>'
        + '<td class="' + (row.excluded ? 'kpi-file-excluded' : '') + '">' + esc(row.file_name || '') + '</td>'
        + '<td>' + fmtNum(row.kit_dental || 0) + '</td>'
        + '<td>' + fmtNum(row.medicamento || 0) + '</td>'
        + '<td>' + fmtNum(row.lentes || 0) + '</td>'
        + '<td><strong>' + fmtNum(row.total_supplies || 0) + '</strong></td>'
        + '<td><button type="button" class="kpi-table-btn ' + actionClass + '" data-file-name="' + esc(row.file_name || '') + '" data-excluded="' + (row.excluded ? '1' : '0') + '">' + actionLabel + '</button></td>'
        + '</tr>';
    }).join('');

    Array.prototype.forEach.call(
      kpiSuppliesByFile.querySelectorAll('.kpi-table-btn'),
      function (button) {
        button.addEventListener('click', function () {
          toggleFileExclusion(
            button.getAttribute('data-file-name') || '',
            button.getAttribute('data-excluded') !== '1'
          );
        });
      }
    );
  }

  function loadPublicKpis() {
    fetch(u('api/stats/kpis'))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        isUpdatingExclusion = false;
        if (!data.ok || !data.kpis) return;
        var stats = data.kpis;
        if (kpiPatients) {
          kpiPatients.textContent = fmtNum(stats.files_downloaded || stats.validated_files || 0);
          kpiPatients.style.transform = 'scale(1.06)';
          setTimeout(function () { kpiPatients.style.transform = 'scale(1)'; }, 200);
        }
        if (kpiPatientsDetail) {
          var files = stats.files_downloaded || stats.validated_files || 0;
          var totalFiles = stats.total_files_analyzed || files;
          var excludedCount = (stats.excluded_files || []).length;
          var source = (stats.source || '').indexOf('priority_validated_folder') === 0
            ? 'carpeta local analizada'
            : 'historial real cargado';
          kpiPatientsDetail.textContent = source + ': ' + files + ' archivo' + (files !== 1 ? 's' : '')
            + ' activos de ' + totalFiles + (excludedCount ? ' (' + excludedCount + ' excluido' + (excludedCount !== 1 ? 's' : '') + ')' : '');
        }
        if (kpiPatientsCount) {
          kpiPatientsCount.textContent = fmtNum(stats.patients_registered || 0);
        }
        if (kpiConsultations) {
          kpiConsultations.textContent = fmtNum(stats.total_consultations || 0);
        }
        if (kpiSuppliesTotal) {
          kpiSuppliesTotal.textContent = fmtNum(stats.total_supplies_delivered || 0);
        }
        if (kpiGrandTotal) {
          kpiGrandTotal.textContent = fmtNum(stats.grand_total || 0);
        }
        renderKpiCards(kpiSpecialties, stats.specialties || [], 'Sin consultas registradas');
        renderKpiCards(kpiSupplies, stats.supplies || [], 'Sin insumos registrados');
        renderKpiCards(kpiDentalProcedures, stats.dental_procedures || [], 'Sin procedimientos dentales registrados');
        renderSuppliesTable(stats.supplies_by_file || []);
      })
      .catch(function () {
        isUpdatingExclusion = false;
      });
  }

  loadPublicKpis();
  if (typeof window !== 'undefined') {
    window.kobuLoadKpis = loadPublicKpis;
  }
})();

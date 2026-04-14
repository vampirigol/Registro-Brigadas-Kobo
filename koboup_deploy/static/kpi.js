(function () {
  var kpiPatients = document.getElementById('kpiPatients');
  var kpiPatientsDetail = document.getElementById('kpiPatientsDetail');
  var kpiConsultations = document.getElementById('kpiConsultations');
  var kpiSpecialties = document.getElementById('kpiSpecialties');
  var kpiSupplies = document.getElementById('kpiSupplies');

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

  function loadPublicKpis() {
    fetch('api/stats/kpis')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok || !data.kpis) return;
        var stats = data.kpis;
        if (kpiPatients) {
          kpiPatients.textContent = fmtNum(stats.patients_registered || 0);
          kpiPatients.style.transform = 'scale(1.06)';
          setTimeout(function () { kpiPatients.style.transform = 'scale(1)'; }, 200);
        }
        if (kpiPatientsDetail) {
          var files = stats.validated_files || 0;
          kpiPatientsDetail.textContent = 'sin duplicados en ' + files + ' archivo' + (files !== 1 ? 's' : '') + ' validado' + (files !== 1 ? 's' : '');
        }
        if (kpiConsultations) {
          kpiConsultations.textContent = fmtNum(stats.total_consultations || 0);
        }
        renderKpiCards(kpiSpecialties, stats.specialties || [], 'Sin consultas registradas');
        renderKpiCards(kpiSupplies, stats.supplies || [], 'Sin insumos registrados');
      })
      .catch(function () {});
  }

  loadPublicKpis();
})();

// Global variables
let allData = null;
let lineChartInstance = null;
let barChartInstance = null;

// Load and initialize
fetch('dashboard_data.json')
  .then(response => {
    if (!response.ok) {
      throw new Error('Erro ao carregar JSON');
    }
    return response.json();
  })
  .then(data => {
    allData = data;

    if (!data.evolucao || data.evolucao.length === 0) {
      console.warn('Evolução vazia');
      return;
    }

    // Initialize everything
    updateKPIs(data.kpis);
    populateMonthFilter(data.evolucao);
    createBarChart(data.kpis);
    createLineChart(data.evolucao);
    setupEventListeners();
  })
  .catch(err => {
    console.error('Erro no dashboard:', err);
  });

// Update KPIs
function updateKPIs(kpis) {
  // Saldo
  const saldoMin = allData.evolucao[allData.evolucao.length - 1].saldo;
  const sinal = saldoMin < 0 ? '-' : '';
  const abs = Math.abs(saldoMin);
  const h = String(Math.floor(abs / 60)).padStart(2, '0');
  const m = String(abs % 60).padStart(2, '0');

  const saldoEl = document.getElementById('saldo');
  saldoEl.textContent = `${sinal}${h}:${m}`;
  saldoEl.className = 'kpi-value';
  saldoEl.classList.add(saldoMin < 0 ? 'negative' : saldoMin > 0 ? 'positive' : '');

  // Other KPIs
  document.getElementById('dias').textContent = allData.detalhes ? allData.detalhes.length : kpis.dias_trabalhados;
  document.getElementById('credito').textContent = kpis.dias_credito || '00:00';
  document.getElementById('debito').textContent = kpis.dias_debito || '00:00';
}

// Populate month filter
function populateMonthFilter(evolucao) {
  const monthFilter = document.getElementById('monthFilter');
  const months = new Set();

  evolucao.forEach(e => {
    const month = e.data.split('/')[1]; // Get month from "DD/MM" format
    months.add(month);
  });

  // Sort months
  const sortedMonths = Array.from(months).sort((a, b) => parseInt(a) - parseInt(b));

  // Add options
  sortedMonths.forEach(month => {
    const option = document.createElement('option');
    option.value = month;
    option.textContent = getMonthName(month);
    monthFilter.appendChild(option);
  });
}

// Get month name
function getMonthName(month) {
  const names = {
    '01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril',
    '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto',
    '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
  };
  return names[month] || month;
}

// Create bar chart
function createBarChart(kpis) {
  const ctx = document.getElementById('barChart');

  // Convert HH:MM to minutes
  const creditoMin = hhmm_para_min(kpis.dias_credito);
  const debitoMin = hhmm_para_min(kpis.dias_debito);

  barChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Horas'],
      datasets: [
        {
          label: 'Crédito',
          data: [creditoMin],
          backgroundColor: '#10b981',
          borderRadius: 8,
          barThickness: 80
        },
        {
          label: 'Débito',
          data: [debitoMin],
          backgroundColor: '#ef4444',
          borderRadius: 8,
          barThickness: 80
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            padding: 20,
            font: {
              size: 13,
              weight: '600'
            },
            usePointStyle: true,
            pointStyle: 'circle'
          }
        },
        tooltip: {
          backgroundColor: '#0f172a',
          padding: 12,
          cornerRadius: 8,
          titleColor: '#f1f5f9',
          bodyColor: '#f1f5f9',
          borderColor: '#334155',
          borderWidth: 1,
          displayColors: true,
          titleFont: {
            size: 13,
            weight: '600'
          },
          bodyFont: {
            size: 14,
            weight: '700'
          },
          callbacks: {
            label: function (context) {
              const min = context.parsed.y;
              const h = Math.floor(min / 60);
              const m = min % 60;
              return `${context.dataset.label}: ${h}h ${m}min`;
            }
          }
        }
      },
      scales: {
        x: {
          display: false
        },
        y: {
          beginAtZero: true,
          grid: {
            color: '#e2e8f0',
            drawBorder: false
          },
          ticks: {
            color: '#64748b',
            font: {
              size: 11,
              weight: '500'
            },
            callback: function (value) {
              const h = Math.floor(value / 60);
              return `${h}h`;
            }
          }
        }
      }
    }
  });
}

// Create line chart
function createLineChart(evolucao) {
  const ctx = document.getElementById('lineChart');

  lineChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: evolucao.map(e => e.data),
      datasets: [{
        label: 'Saldo',
        data: evolucao.map(e => e.saldo),
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.05)',
        borderWidth: 2.5,
        tension: 0.3,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHoverBackgroundColor: '#2563eb',
        pointHoverBorderColor: '#ffffff',
        pointHoverBorderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: 'index'
      },
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          backgroundColor: '#0f172a',
          padding: 12,
          cornerRadius: 8,
          titleColor: '#f1f5f9',
          bodyColor: '#f1f5f9',
          borderColor: '#334155',
          borderWidth: 1,
          displayColors: false,
          titleFont: {
            size: 13,
            weight: '600'
          },
          bodyFont: {
            size: 14,
            weight: '700'
          },
          callbacks: {
            title: function (context) {
              return context[0].label;
            },
            label: function (context) {
              const min = context.parsed.y;
              const sinal = min < 0 ? '-' : '+';
              const abs = Math.abs(min);
              const h = Math.floor(abs / 60);
              const m = abs % 60;
              return `${sinal}${h}h ${m}min`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            display: false,
            drawBorder: false
          },
          ticks: {
            color: '#64748b',
            font: {
              size: 11,
              weight: '500'
            },
            maxRotation: 45,
            minRotation: 45
          }
        },
        y: {
          grid: {
            color: '#e2e8f0',
            drawBorder: false
          },
          ticks: {
            color: '#64748b',
            font: {
              size: 11,
              weight: '500'
            },
            callback: function (value) {
              const h = Math.floor(Math.abs(value) / 60);
              return value < 0 ? `-${h}h` : `+${h}h`;
            }
          }
        }
      }
    }
  });
}

// Setup event listeners
function setupEventListeners() {
  // Month filter
  document.getElementById('monthFilter').addEventListener('change', function (e) {
    const selectedMonth = e.target.value;
    filterByMonth(selectedMonth);
  });

  // PDF export
  document.getElementById('exportPdf').addEventListener('click', exportToPDF);
}

// Filter by month
function filterByMonth(month) {
  if (!allData) return;

  let filteredData;

  if (month === 'all') {
    filteredData = allData.evolucao;
  } else {
    filteredData = allData.evolucao.filter(e => {
      const dataMonth = e.data.split('/')[1];
      return dataMonth === month;
    });
  }

  // Update line chart
  if (lineChartInstance) {
    lineChartInstance.data.labels = filteredData.map(e => e.data);
    lineChartInstance.data.datasets[0].data = filteredData.map(e => e.saldo);
    lineChartInstance.update();
  }
}

// Export to PDF
function exportToPDF() {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();

  // Header
  doc.setFontSize(18);
  doc.setFont('helvetica', 'bold');
  doc.text('Espelho de Ponto - Banco de Horas', 105, 20, { align: 'center' });

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.text(`Gerado em: ${new Date().toLocaleDateString('pt-BR')}`, 105, 28, { align: 'center' });

  // Summary section
  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.text('Resumo', 14, 40);

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.text(`Saldo Acumulado: ${allData.kpis.saldo_atual}`, 14, 48);
  doc.text(`Dias Trabalhados: ${allData.kpis.dias_trabalhados}`, 14, 54);
  doc.text(`Horas Crédito: ${allData.kpis.dias_credito}`, 14, 60);
  doc.text(`Horas Débito: ${allData.kpis.dias_debito}`, 14, 66);

  // Detailed table
  if (allData.detalhes && allData.detalhes.length > 0) {
    const tableData = allData.detalhes.map(d => {
      return [
        d.data,
        d.entrada || '-',
        d.saida_almoco || '-',
        d.volta_almoco || '-',
        d.saida || '-',
        d.banco_dia
      ];
    });

    doc.autoTable({
      startY: 75,
      head: [['Data', 'Entrada', 'Saída Almoço', 'Volta Almoço', 'Saída', 'Banco do Dia']],
      body: tableData,
      theme: 'grid',
      headStyles: {
        fillColor: [37, 99, 235],
        textColor: 255,
        fontStyle: 'bold',
        halign: 'center',
        fontSize: 9
      },
      bodyStyles: {
        halign: 'center',
        fontSize: 8
      },
      columnStyles: {
        0: { cellWidth: 25 },  // Data
        1: { cellWidth: 25 },  // Entrada
        2: { cellWidth: 30 },  // Saída Almoço
        3: { cellWidth: 30 },  // Volta Almoço
        4: { cellWidth: 25 },  // Saída
        5: { cellWidth: 30, fontStyle: 'bold' }   // Banco do Dia
      },
      alternateRowStyles: {
        fillColor: [248, 250, 252]
      },
      margin: { top: 75 },
      didParseCell: function (data) {
        // Colorir banco do dia
        if (data.column.index === 5 && data.section === 'body') {
          const valor = data.cell.text[0];
          if (valor && valor.startsWith('-')) {
            data.cell.styles.textColor = [239, 68, 68]; // vermelho
          } else if (valor && valor.startsWith('+')) {
            data.cell.styles.textColor = [16, 185, 129]; // verde
          }
        }
      }
    });
  }

  // Footer
  const pageCount = doc.internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.text(
      `Página ${i} de ${pageCount}`,
      doc.internal.pageSize.getWidth() / 2,
      doc.internal.pageSize.getHeight() - 10,
      { align: 'center' }
    );
  }

  // Save
  doc.save('espelho-ponto.pdf');
}

// Helper function
function hhmm_para_min(hhmm) {
  const sinal = hhmm.startsWith('-') ? -1 : 1;
  const [h, m] = hhmm.replace('-', '').split(':');
  return sinal * (parseInt(h) * 60 + parseInt(m));
}

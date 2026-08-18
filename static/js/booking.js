/**
 * Padel Arena — Booking page交互
 * Calendario, selección de pista/hora, resumen dinámico, pasos
 */
(function () {
  'use strict';

  /* ======================================================================
     Datos
     ====================================================================== */
  // Horarios mock por ahora (se reemplazará con datos reales del backend)
  var MOCK_SLOTS = {
    available:   ['9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00'],
    unavailable: ['8:00']
  };

  // Meses en español
  var MONTHS = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];

  var WEEKDAYS = ['LU', 'MA', 'MI', 'JU', 'VI', 'SA', 'DO'];

  /* ======================================================================
     Estado
     ====================================================================== */
  var state = {
    currentMonth: new Date().getMonth(),
    currentYear:  new Date().getFullYear(),
    selectedDate: null,   // { day, month, year, weekday }
    selectedCourt: null,  // { id, name, type, price, description }
    selectedTime: null,   // '13:00'
    courtFilter: 'all'
  };

  /* ======================================================================
     Courts data (desde Django JSON)
     ====================================================================== */
  var courts = [];
  try {
    courts = JSON.parse(document.getElementById('courts-data').textContent);
  } catch (e) {
    courts = [];
  }

  /* ======================================================================
     DOM refs
     ====================================================================== */
  var $monthLabel     = document.getElementById('calendar-month-label');
  var $grid           = document.getElementById('calendar-grid');
  var $prevMonth      = document.getElementById('prev-month');
  var $nextMonth      = document.getElementById('next-month');
  var $courtSelect    = document.getElementById('court-select');
  var $courtInfoCard  = document.getElementById('court-info-card');
  var $courtInfoName  = document.getElementById('court-info-name');
  var $courtInfoBadge = document.getElementById('court-info-badge');
  var $courtInfoDesc  = document.getElementById('court-info-desc');
  var $courtInfoPrice = document.getElementById('court-info-price');
  var $summaryCourt   = document.getElementById('summary-court-text');
  var $summaryDT      = document.getElementById('summary-datetime-text');
  var $summaryTotal   = document.getElementById('summary-total');
  var $summaryAmt     = document.getElementById('summary-total-amount');
  var $timePicker     = document.getElementById('time-picker');
  var $timeOverlay    = document.getElementById('time-picker-overlay');
  var $timeGrid       = document.getElementById('time-grid');
  var $timeSubmit     = document.getElementById('time-picker-submit');
  var $timeClose      = document.getElementById('time-picker-close');
  var $steps          = document.querySelectorAll('.step');
  var $filterInputs   = document.querySelectorAll('input[name="court-filter"]');
  var $confirmBtn     = document.getElementById('summary-confirm-btn');

  /* ======================================================================
     Calendario
     ====================================================================== */

  /** Días del mes (1-indexed) + padding para alinear con lunes */
  function getMonthDays(year, month) {
    var firstDay = new Date(year, month, 1);
    var lastDay  = new Date(year, month + 1, 0);
    var daysInMonth = lastDay.getDate();

    // weekday() devuelve 0=Dom, convertimos a 0=Lun
    var startWeekday = (firstDay.getDay() + 6) % 7;

    var days = [];
    // Padding del mes anterior
    for (var i = 0; i < startWeekday; i++) {
      days.push({ day: null, empty: true });
    }
    // Días del mes
    for (var d = 1; d <= daysInMonth; d++) {
      var date = new Date(year, month, d);
      var wd = (date.getDay() + 6) % 7; // 0=Lun
      var today = new Date();
      var isPast = date < new Date(today.getFullYear(), today.getMonth(), today.getDate());
      var isWeekend = wd >= 5; // Sáb/Dom no disponibles (mock)
      days.push({
        day: d,
        empty: false,
        weekday: wd,
        unavailable: isPast || isWeekend,
        available: !isPast && !isWeekend
      });
    }
    return days;
  }

  function renderCalendar() {
    $monthLabel.textContent = MONTHS[state.currentMonth] + ' ' + state.currentYear;

    var days = getMonthDays(state.currentYear, state.currentMonth);
    var html = '';

    // Header de días de semana
    WEEKDAYS.forEach(function (wd) {
      html += '<div class="calendar-weekday">' + wd + '</div>';
    });

    // Celdas de días
    days.forEach(function (d) {
      if (d.empty) {
        html += '<div class="calendar-day calendar-day--empty"></div>';
        return;
      }

      var classes = ['calendar-day'];
      var ariaLabel = d.day + ' de ' + MONTHS[state.currentMonth];
      var ariaDisabled = '';
      var tabIndex = '0';

      if (d.unavailable) {
        classes.push('calendar-day--unavailable');
        ariaLabel += ' — no disponible';
        ariaDisabled = ' aria-disabled="true"';
        tabIndex = '-1';
      } else {
        classes.push('calendar-day--available');
        ariaLabel += ' — disponible';
      }

      // Seleccionado
      if (state.selectedDate &&
          state.selectedDate.day === d.day &&
          state.selectedDate.month === state.currentMonth &&
          state.selectedDate.year === state.currentYear) {
        classes.push('calendar-day--selected');
        ariaLabel += ' — seleccionado';
      }

      html += '<div class="' + classes.join(' ') + '" '
            + 'data-day="' + d.day + '" '
            + 'role="gridcell" '
            + 'aria-label="' + ariaLabel + '" '
            + ariaDisabled + ' '
            + 'tabindex="' + tabIndex + '">'
            + d.day + '</div>';
    });

    $grid.innerHTML = html;
  }

  function onCalendarClick(e) {
    var cell = e.target.closest('.calendar-day--available');
    if (!cell) return;

    var day = parseInt(cell.getAttribute('data-day'), 10);
    var date = new Date(state.currentYear, state.currentMonth, day);
    var wd = (date.getDay() + 6) % 7;

    state.selectedDate = {
      day: day,
      month: state.currentMonth,
      year: state.currentYear,
      weekday: wd
    };

    renderCalendar();
    updateSteps();
    updateSummary();
    tryShowTimePicker();
  }

  $prevMonth.addEventListener('click', function () {
    state.currentMonth--;
    if (state.currentMonth < 0) {
      state.currentMonth = 11;
      state.currentYear--;
    }
    renderCalendar();
  });

  $nextMonth.addEventListener('click', function () {
    state.currentMonth++;
    if (state.currentMonth > 11) {
      state.currentMonth = 0;
      state.currentYear++;
    }
    renderCalendar();
  });

  $grid.addEventListener('click', onCalendarClick);

  /* ======================================================================
     Courts — Select dropdown + info card
     ====================================================================== */
  function renderCourts() {
    var filtered = courts.filter(function (c) {
      if (state.courtFilter === 'all') return true;
      return c.type === state.courtFilter;
    });

    // Rebuild select options (keep the placeholder first option)
    var html = '<option value="">— Seleccioná una pista —</option>';
    filtered.forEach(function (court) {
      var selected = state.selectedCourt && state.selectedCourt.id === court.id ? ' selected' : '';
      var badgeLabel = court.type === 'indoor' ? 'Cubierta' : 'Exterior';
      html += '<option value="' + court.id + '"' + selected + '>'
            + court.name + ' — ' + badgeLabel + ' — ' + formatPrice(court.price) + '/h'
            + '</option>';
    });
    $courtSelect.innerHTML = html;

    // If current selection is no longer in the filtered list, clear it
    if (state.selectedCourt) {
      var stillVisible = filtered.some(function (c) { return c.id === state.selectedCourt.id; });
      if (!stillVisible) {
        state.selectedCourt = null;
      }
    }

    showCourtInfo(state.selectedCourt);
  }

  function showCourtInfo(court) {
    if (!court) {
      $courtInfoCard.style.display = 'none';
      return;
    }
    $courtInfoName.textContent = court.name;
    $courtInfoBadge.textContent = court.type === 'indoor' ? 'Cubierta' : 'Exterior';
    $courtInfoBadge.className = 'court-badge ' + (court.type === 'indoor' ? 'court-badge--indoor' : 'court-badge--outdoor');
    $courtInfoDesc.textContent = court.description;
    $courtInfoPrice.textContent = formatPrice(court.price) + ' / hora';
    $courtInfoCard.style.display = 'flex';
  }

  $courtSelect.addEventListener('change', function () {
    var courtId = this.value ? parseInt(this.value, 10) : null;
    state.selectedCourt = courtId
      ? courts.find(function (c) { return c.id === courtId; }) || null
      : null;

    showCourtInfo(state.selectedCourt);
    updateSteps();
    updateSummary();
    tryShowTimePicker();
  });

  // Filtro
  $filterInputs.forEach(function (input) {
    input.addEventListener('change', function () {
      state.courtFilter = this.value;
      renderCourts();
      updateSteps();
      updateSummary();
    });
  });

  /* ======================================================================
     Time picker
     ====================================================================== */
  function tryShowTimePicker() {
    if (state.selectedDate && state.selectedCourt) {
      showTimePicker();
    }
  }

  function showTimePicker() {
    state.selectedTime = null;
    renderTimeSlots();
    $timeSubmit.disabled = true;
    $timePicker.classList.add('time-picker--visible');
    $timeOverlay.classList.add('time-picker-overlay--visible');
  }

  function hideTimePicker() {
    $timePicker.classList.remove('time-picker--visible');
    $timeOverlay.classList.remove('time-picker-overlay--visible');
  }

  function renderTimeSlots() {
    var html = [];
    var allSlots = MOCK_SLOTS.available.concat(MOCK_SLOTS.unavailable);

    // Ordenar cronológicamente
    allSlots.sort(function (a, b) {
      return parseInt(a) - parseInt(b);
    });

    allSlots.forEach(function (time) {
      var isUnavailable = MOCK_SLOTS.unavailable.indexOf(time) !== -1;
      var isSelected = state.selectedTime === time;
      var classes = ['time-slot'];

      if (isUnavailable) classes.push('time-slot--unavailable');
      if (isSelected) classes.push('time-slot--selected');

      var ariaDisabled = isUnavailable ? ' aria-disabled="true"' : '';
      var tabindex = isUnavailable ? ' tabindex="-1"' : ' tabindex="0"';

      html.push(
        '<div class="' + classes.join(' ') + '" '
        + 'data-time="' + time + '" '
        + 'role="radio" aria-checked="' + (isSelected ? 'true' : 'false') + '"'
        + ariaDisabled + tabindex + '>'
        + time
        + '</div>'
      );
    });

    $timeGrid.innerHTML = html.join('');
  }

  $timeGrid.addEventListener('click', function (e) {
    var slot = e.target.closest('.time-slot:not(.time-slot--unavailable)');
    if (!slot) return;

    state.selectedTime = slot.getAttribute('data-time');
    renderTimeSlots();
    $timeSubmit.disabled = false;
    updateSteps();
    updateSummary();
  });

  $timeClose.addEventListener('click', hideTimePicker);
  $timeOverlay.addEventListener('click', hideTimePicker);

  $timeSubmit.addEventListener('click', function () {
    hideTimePicker();
    updateSteps();
    updateSummary();
    // En paso 4, mostrar botón confirmar
    showConfirmButton();
  });

  /* ======================================================================
     Summary
     ====================================================================== */
  function updateSummary() {
    // Pista
    if (state.selectedCourt) {
      $summaryCourt.classList.remove('summary-detail--placeholder');
      $summaryCourt.innerHTML = '<strong>' + state.selectedCourt.name + '</strong>';
    } else {
      $summaryCourt.classList.add('summary-detail--placeholder');
      $summaryCourt.textContent = 'Elegí una pista';
    }

    // Fecha + hora
    if (state.selectedDate) {
      var dateStr = pad(state.selectedDate.day) + '/' + pad(state.selectedDate.month + 1) + '/' + state.selectedDate.year;
      if (state.selectedTime) {
        dateStr += ' — ' + state.selectedTime;
      }
      $summaryDT.classList.remove('summary-detail--placeholder');
      $summaryDT.innerHTML = '<strong>' + dateStr + '</strong>';
    } else {
      $summaryDT.classList.add('summary-detail--placeholder');
      $summaryDT.textContent = 'Elegí fecha y hora';
    }

    // Total
    if (state.selectedCourt && state.selectedTime) {
      $summaryTotal.style.display = 'flex';
      $summaryAmt.textContent = formatPrice(state.selectedCourt.price);
    } else {
      $summaryTotal.style.display = 'none';
    }

    // Botón confirmar: solo en paso 4
    var allSelected = state.selectedDate && state.selectedCourt && state.selectedTime;
    if (!allSelected) {
      $confirmBtn.style.display = 'none';
    }
  }

  function showConfirmButton() {
    $confirmBtn.style.display = 'block';
    // Scroll al resumen para que lo vea
    $confirmBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  /* ======================================================================
     Steps indicator
     ====================================================================== */
  function updateSteps() {
    var currentStep = 1;
    if (state.selectedDate) currentStep = 2;
    if (state.selectedDate && state.selectedCourt) currentStep = 3;
    if (state.selectedDate && state.selectedCourt && state.selectedTime) currentStep = 4;

    $steps.forEach(function (el) {
      var stepNum = parseInt(el.getAttribute('data-step'), 10);
      el.classList.remove('step--active', 'step--done');
      if (stepNum === currentStep) {
        el.classList.add('step--active');
      } else if (stepNum < currentStep) {
        el.classList.add('step--done');
      }
    });
  }

  /* ======================================================================
     Utils
     ====================================================================== */
  function pad(n) {
    return n < 10 ? '0' + n : '' + n;
  }

  function formatPrice(price) {
    // Viene como número o string del JSON
    var num = parseFloat(price);
    if (isNaN(num)) return price;
    return num.toFixed(2).replace('.', ',') + ' \u20AC';
  }

  /* ======================================================================
     Init
     ====================================================================== */
  renderCalendar();
  renderCourts();
  updateSteps();
  updateSummary();

})();

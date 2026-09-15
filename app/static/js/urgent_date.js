(function () {
  function daysInMonth(year, month) {
    return new Date(year, month, 0).getDate();
  }

  function pad(value, length) {
    return String(value).padStart(length, "0");
  }

  function setupBlock(block) {
    const toggle = block.querySelector("[data-urgent-toggle]");
    const dateFields = block.querySelector("[data-urgent-date-fields]");
    const yearInput = block.querySelector("[data-urgent-year]");
    const monthInput = block.querySelector("[data-urgent-month]");
    const dayInput = block.querySelector("[data-urgent-day]");
    const calendarInput = block.querySelector("[data-urgent-calendar]");
    const hiddenInput = block.querySelector("[data-urgent-hidden]");
    const errorEl = block.querySelector("[data-urgent-error]");

    if (!toggle || !dateFields) return;

    toggle.addEventListener("change", () => {
      dateFields.hidden = !toggle.checked;
      if (!toggle.checked) {
        hiddenInput.value = "";
        errorEl.textContent = "";
      }
    });

    function currentValues() {
      return {
        year: parseInt(yearInput.value, 10),
        month: parseInt(monthInput.value, 10),
        day: parseInt(dayInput.value, 10),
      };
    }

    function recompute() {
      const { year, month, day } = currentValues();
      errorEl.textContent = "";
      hiddenInput.value = "";

      if (!yearInput.value || !monthInput.value || !dayInput.value) {
        return;
      }
      if (String(yearInput.value).length < 4) {
        return;
      }
      if (isNaN(year) || isNaN(month) || isNaN(day)) {
        return;
      }
      if (month < 1 || month > 12) {
        errorEl.textContent = "월은 1~12 사이여야 합니다.";
        return;
      }
      const maxDay = daysInMonth(year, month);
      if (day < 1 || day > maxDay) {
        errorEl.textContent = `${year}년 ${month}월은 ${maxDay}일까지 있습니다.`;
        return;
      }
      const check = new Date(year, month - 1, day);
      if (check.getFullYear() !== year || check.getMonth() !== month - 1 || check.getDate() !== day) {
        errorEl.textContent = "유효하지 않은 날짜입니다.";
        return;
      }
      hiddenInput.value = `${pad(year, 4)}-${pad(month, 2)}-${pad(day, 2)}`;
    }

    yearInput.addEventListener("input", () => {
      let digits = yearInput.value.replace(/\D/g, "");
      if (digits.length && digits[0] === "0") {
        digits = digits.slice(1);
      }
      digits = digits.slice(0, 4);
      yearInput.value = digits;
      if (digits.length === 4) {
        monthInput.focus();
        monthInput.select();
      }
      recompute();
    });

    monthInput.addEventListener("input", () => {
      const digits = monthInput.value.replace(/\D/g, "").slice(0, 2);
      monthInput.value = digits;
      if (digits.length === 2) {
        dayInput.focus();
        dayInput.select();
      }
      recompute();
    });
    monthInput.addEventListener("blur", () => {
      if (monthInput.value) {
        const n = Math.min(12, Math.max(1, parseInt(monthInput.value, 10) || 1));
        monthInput.value = pad(n, 2);
      }
      recompute();
    });
    monthInput.addEventListener("keydown", (event) => {
      if (event.key === "Backspace" && !monthInput.value) {
        yearInput.focus();
      }
    });

    dayInput.addEventListener("input", () => {
      const digits = dayInput.value.replace(/\D/g, "").slice(0, 2);
      dayInput.value = digits;
      recompute();
    });
    dayInput.addEventListener("blur", () => {
      if (dayInput.value) {
        const { year, month } = currentValues();
        const max = year && month ? daysInMonth(year, month) : 31;
        const n = Math.min(max, Math.max(1, parseInt(dayInput.value, 10) || 1));
        dayInput.value = pad(n, 2);
      }
      recompute();
    });
    dayInput.addEventListener("keydown", (event) => {
      if (event.key === "Backspace" && !dayInput.value) {
        monthInput.focus();
      }
    });

    if (calendarInput) {
      calendarInput.addEventListener("change", () => {
        if (!calendarInput.value) return;
        const [y, m, d] = calendarInput.value.split("-");
        yearInput.value = y;
        monthInput.value = m;
        dayInput.value = d;
        recompute();
      });
    }
  }

  document.querySelectorAll("[data-urgent-block]").forEach(setupBlock);
})();

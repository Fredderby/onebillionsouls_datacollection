/* Sunday attendance form: cascading selects, live totals, validation, submit. */

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("attendanceForm");
  const formBody = document.getElementById("formBody");
  const successPanel = document.getElementById("successPanel");
  const submitProgress = document.getElementById("submitProgress");
  const submitBtn = document.getElementById("submitBtn");
  const clearBtn = document.getElementById("clearBtn");
  const anotherBtn = document.getElementById("anotherBtn");
  const banner = document.getElementById("formError");
  const zoneSelect = document.getElementById("zone");
  const regionSelect = document.getElementById("region");
  const divisionSelect = document.getElementById("division");

  let hierarchy = {};

  const SELECT_FIELDS = ["zone", "region", "division"];
  const INTEGER_FIELDS = [
    "total_locations", "total_pastors",
    "workers_brothers", "workers_sisters",
    "adults_male", "adults_female",
    "youths_male", "youths_female",
    "ypf_male", "ypf_female",
    "children_boys", "children_girls",
    "online_male", "online_female",
  ];
  const OPTIONAL_FIELDS = [
    "ypf_male", "ypf_female",
    "online_male", "online_female",
  ];
  const REQUIRED_INTEGER_FIELDS = INTEGER_FIELDS.filter(
    (name) => !OPTIONAL_FIELDS.includes(name)
  );
  const CATEGORY_ROWS = [
    { prefix: "adults", male: "adults_male", female: "adults_female" },
    { prefix: "youths", male: "youths_male", female: "youths_female" },
    { prefix: "ypf", male: "ypf_male", female: "ypf_female" },
    { prefix: "children", male: "children_boys", female: "children_girls" },
  ];

  /* ---------- dropdowns ---------- */
  function fillSelect(select, values, placeholder) {
    select.replaceChildren(new Option(placeholder, ""));
    values.forEach((value) => select.add(new Option(value, value)));
    select.disabled = values.length === 0;
  }

  function clearFieldError(name) {
    const wrapper = document.querySelector(`[data-field="${name}"]`);
    if (!wrapper) return;
    wrapper.classList.remove("invalid");
    const text = wrapper.querySelector(".error-text");
    if (text) text.textContent = "";
  }

  function showFieldError(name, message) {
    const wrapper = document.querySelector(`[data-field="${name}"]`);
    if (!wrapper) return;
    wrapper.classList.add("invalid");
    const text = wrapper.querySelector(".error-text");
    if (text) text.textContent = message;
  }

  function clearAllErrors() {
    document.querySelectorAll(".field.invalid").forEach((el) => {
      el.classList.remove("invalid");
      const text = el.querySelector(".error-text");
      if (text) text.textContent = "";
    });
    hideBanner();
  }

  function showBanner(message) {
    banner.textContent = message;
    banner.hidden = false;
  }

  function hideBanner() {
    banner.hidden = true;
    banner.textContent = "";
  }

  function loadHierarchy() {
    fetch("/api/hierarchy")
      .then((response) => {
        if (!response.ok) throw new Error("hierarchy request failed");
        return response.json();
      })
      .then((data) => {
        hierarchy = data || {};
        fillSelect(zoneSelect, Object.keys(hierarchy), "Select your zone");
      })
      .catch(() => {
        fillSelect(zoneSelect, [], "Location list unavailable");
        showBanner("Could not load the location list. Please refresh the page.");
      });
  }

  zoneSelect.addEventListener("change", () => {
    const zone = hierarchy[zoneSelect.value];
    fillSelect(regionSelect, zone ? Object.keys(zone) : [], "Select your region");
    fillSelect(divisionSelect, [], "Select your division");
    clearFieldError("zone");
    clearFieldError("region");
    clearFieldError("division");
    hideBanner();
    updateProgress();
  });

  regionSelect.addEventListener("change", () => {
    const zone = hierarchy[zoneSelect.value];
    const divisions = zone && zone[regionSelect.value] ? zone[regionSelect.value] : [];
    fillSelect(divisionSelect, divisions, "Select your division");
    clearFieldError("division");
    hideBanner();
    updateProgress();
  });

  /* ---------- live totals ---------- */
  function numberValue(id) {
    const raw = document.getElementById(id).value.trim();
    return /^[0-9]+$/.test(raw) ? Number(raw) : 0;
  }

  function updateProgress() {
    const names = [...SELECT_FIELDS, ...REQUIRED_INTEGER_FIELDS];
    const filled = names.filter((name) => document.getElementById(name).value.trim() !== "").length;
    const count = names.length;
    document.getElementById("progressCount").textContent = `${filled} / ${count}`;
    document.getElementById("progressBar").style.setProperty("--progress", String(filled / count));
  }

  function updateTotals() {
    let inPerson = 0;
    CATEGORY_ROWS.forEach((row) => {
      const rowTotal = numberValue(row.male) + numberValue(row.female);
      inPerson += rowTotal;
      const target = document.querySelector(`[data-subtotal="${row.prefix}"]`);
      if (target) target.textContent = String(rowTotal);
    });
    const online = numberValue("online_male") + numberValue("online_female");
    const grand = inPerson + online;

    document.getElementById("totalInPerson").textContent = String(inPerson);
    document.getElementById("totalOnline").textContent = String(online);
    document.getElementById("grandTotal").textContent = String(grand);
    document.getElementById("railInPerson").textContent = String(inPerson);
    document.getElementById("railOnline").textContent = String(online);
    document.getElementById("railGrand").textContent = String(grand);
  }

  function refreshLiveUi() {
    updateTotals();
    updateProgress();
  }

  form.addEventListener("input", (event) => {
    if (event.target.type === "number") {
      clearFieldError(event.target.name);
      refreshLiveUi();
    }
  });

  /* ---------- validation ---------- */
  function validate() {
    clearAllErrors();
    const errors = {};
    const data = {};

    SELECT_FIELDS.forEach((name) => {
      const value = document.getElementById(name).value.trim();
      if (!value) {
        errors[name] = "Please select this field.";
      } else {
        data[name] = value;
      }
    });

    if (data.zone && hierarchy[data.zone] && data.region &&
        !Object.prototype.hasOwnProperty.call(hierarchy[data.zone], data.region)) {
      errors.region = "Select a valid region for this zone.";
    }
    if (data.zone && data.region && data.division && hierarchy[data.zone] &&
        Array.isArray(hierarchy[data.zone][data.region]) &&
        !hierarchy[data.zone][data.region].includes(data.division)) {
      errors.division = "Select a valid division for this region.";
    }

    INTEGER_FIELDS.forEach((name) => {
      const raw = document.getElementById(name).value.trim();
      if (raw === "" && OPTIONAL_FIELDS.includes(name)) {
        data[name] = 0;
      } else if (raw === "") {
        errors[name] = "This field is required.";
      } else if (!/^[0-9]+$/.test(raw)) {
        errors[name] = "Enter a whole number of 0 or more.";
      } else {
        data[name] = Number(raw);
      }
    });

    Object.entries(errors).forEach(([name, message]) => showFieldError(name, message));

    const firstKey = Object.keys(errors)[0];
    if (firstKey) {
      showBanner("Please complete the required fields before submitting your report.");
      const firstField = document.getElementById(firstKey);
      if (firstField && !firstField.disabled) firstField.focus();
      return null;
    }
    return data;
  }

  /* ---------- submit ---------- */
  function setLoading(loading) {
    submitBtn.classList.toggle("loading", loading);
    submitBtn.disabled = loading;
    clearBtn.disabled = loading;
    submitProgress.hidden = !loading;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = validate();
    if (!data) return;

    setLoading(true);
    try {
      const response = await fetch("/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await response.json();

      if (!response.ok || !result.ok) {
        if (result.errors) {
          Object.entries(result.errors).forEach(([name, message]) => showFieldError(name, message));
        }
        showBanner(result.message || "Please correct the highlighted fields and try again.");
        return;
      }

      document.getElementById("refId").textContent =
        `#${String(result.id).padStart(5, "0")}`;
      formBody.hidden = true;
      successPanel.hidden = false;
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      showBanner("Could not reach the server. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  });

  /* ---------- reset ---------- */
  function resetForm() {
    form.reset();
    clearAllErrors();
    fillSelect(zoneSelect, Object.keys(hierarchy), "Select your zone");
    fillSelect(regionSelect, [], "Select your region");
    fillSelect(divisionSelect, [], "Select your division");
    refreshLiveUi();
  }

  clearBtn.addEventListener("click", () => {
    resetForm();
    if (!zoneSelect.disabled) zoneSelect.focus();
  });

  anotherBtn.addEventListener("click", () => {
    successPanel.hidden = true;
    formBody.hidden = false;
    resetForm();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  loadHierarchy();
  refreshLiveUi();
});

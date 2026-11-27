/* Admin delete confirmation. The dialog is styled by admin.css; no native confirm(). */

(() => {
  const dialog = document.getElementById("deleteDialog");
  if (!dialog) return;

  const form = document.getElementById("deleteForm");
  const target = document.getElementById("deleteTarget");
  const cancel = document.getElementById("cancelDeleteBtn");
  const confirm = document.getElementById("confirmDeleteBtn");

  document.querySelectorAll(".delete-trigger").forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const label = trigger.dataset.deleteLabel || "this division";
      form.action = trigger.dataset.deleteAction;
      target.textContent = label;

      if (typeof dialog.showModal === "function") {
        dialog.showModal();
        confirm.focus();
      } else if (window.confirm(`Permanently delete the report for ${label}?`)) {
        form.submit();
      }
    });
  });

  cancel.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
})();

/* Report details dialog: reveals every stored field without widening the table. */

(() => {
  const dialog = document.getElementById("reportDialog");
  if (!dialog) return;

  const summary = document.getElementById("reportDialogSummary");
  const close = document.getElementById("closeReportBtn");
  const fields = [...dialog.querySelectorAll("[data-report-field]")];

  const setField = (name, value) => {
    const element = fields.find((el) => el.dataset.reportField === name);
    if (element) element.textContent = value === null || value === undefined ? "" : String(value);
  };

  document.querySelectorAll(".admin-report-trigger").forEach((trigger) => {
    trigger.addEventListener("click", () => {
      let report;
      try {
        report = JSON.parse(trigger.dataset.report || "{}");
      } catch (error) {
        return;
      }

      summary.textContent = `${report.division || ""} · ${report.zone || ""} / ${report.region || ""}`;
      Object.entries(report).forEach(([name, value]) => setField(name, value));

      const inPerson =
        Number(report.adults_male || 0) +
        Number(report.adults_female || 0) +
        Number(report.youths_male || 0) +
        Number(report.youths_female || 0) +
        Number(report.ypf_male || 0) +
        Number(report.ypf_female || 0) +
        Number(report.children_boys || 0) +
        Number(report.children_girls || 0);
      const online = Number(report.online_male || 0) + Number(report.online_female || 0);
      setField("in_person", inPerson);
      setField("online_total", online);
      setField("grand_total", inPerson + online);

      if (typeof dialog.showModal === "function") {
        dialog.showModal();
        dialog.scrollTop = 0;
        close.focus({ preventScroll: true });
      } else {
        dialog.setAttribute("open", "");
        dialog.scrollTop = 0;
      }
    });
  });

  close.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
})();

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

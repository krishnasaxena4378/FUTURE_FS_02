// Ask for confirmation before any form that has a data-confirm message is submitted.
document.querySelectorAll("form[data-confirm]").forEach(function (form) {
  form.addEventListener("submit", function (event) {
    if (!window.confirm(form.dataset.confirm)) {
      event.preventDefault(); // user clicked Cancel, so do not delete
    }
  });
});

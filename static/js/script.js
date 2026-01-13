document.addEventListener("DOMContentLoaded", function () {
    const flash = document.getElementById("flashMessage");
    if (flash) {
        setTimeout(() => {
            flash.style.transition = "opacity 0.5s ease";
            flash.style.opacity = "0";

            setTimeout(() => {
                flash.style.display = "none";
            }, 500);
        }, 3000);
    }
    $('#deleteModal').on('show.bs.modal', function (event) {
        const button = $(event.relatedTarget);
        const todoId = button.data('id');

        $('#confirmDeleteBtn').attr('href', `/delete/${todoId}`);
    });
});
const popoverTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="popover"]')
  );
  popoverTriggerList.map(function (popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl, {
      trigger: 'hover'
    });
  });




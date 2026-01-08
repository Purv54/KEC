// Select all products
document.addEventListener("DOMContentLoaded", function () {
    const selectAll = document.getElementById("select-all");
    const checkboxes = document.querySelectorAll(".product-checkbox");

    if (selectAll) {
        selectAll.addEventListener("change", function () {
            checkboxes.forEach(cb => cb.checked = selectAll.checked);
        });
    }
});


document.addEventListener("click", function (e) {
    if (e.target.classList.contains("ajax-page")) {
        e.preventDefault();

        fetch(e.target.href, {
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        })
        .then(res => res.text())
        .then(html => {
            document.querySelector(".card-body").innerHTML = html;
        });
    }
});


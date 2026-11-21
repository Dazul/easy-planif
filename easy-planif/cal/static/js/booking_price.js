// Autocompute a booking's total price:
//   adults * price_adult + children * price_child
//   (+ meal prices when the meal is included)
// Inputs opt in via data-price-part, the total via data-price-total.
// The total field is read-only; this script fills it as the user
// types, and the server re-checks the value anyway. Loaded with
// defer (it needs the form to exist).
(function () {
    var total = document.querySelector('[data-price-total]');
    if (!total) return;

    var inputs = document.querySelectorAll('[data-price-part]');
    if (!inputs.length) return;

    function num(el) {
        var v = parseFloat(el.value);
        return isNaN(v) ? 0 : v;
    }

    function recompute() {
        var values = {};
        inputs.forEach(function (el) {
            values[el.getAttribute('data-price-part')] = num(el);
        });
        values['meal_included'] = document.querySelector(
            '[data-price-part="meal_included"]'
        ).checked;

        var total_price =
            (values['adult'] || 0) * (values['price_adult'] || 0) +
            (values['child'] || 0) * (values['price_child'] || 0);
        if (values['meal_included']) {
            total_price +=
                (values['adult'] || 0) * (values['meal_price_adult'] || 0) +
                (values['child'] || 0) * (values['meal_price_child'] || 0);
        }
        total.value = Math.round(total_price * 100) / 100;
    }

    inputs.forEach(function (el) {
        el.addEventListener('input', recompute);
        el.addEventListener('change', recompute);
    });
    recompute();
})();

// Main portal client-side utilities
document.addEventListener("DOMContentLoaded", () => {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 6000);
    });

    // Quick fill credentials for demo evaluator ease
    const demoButtons = document.querySelectorAll(".btn-fill-demo");
    demoButtons.forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            const email = btn.getAttribute("data-email");
            const pass = btn.getAttribute("data-password");
            const emailInput = document.getElementById("email");
            const passInput = document.getElementById("password");
            if (emailInput && passInput) {
                emailInput.value = email;
                passInput.value = pass;
            }
        });
    });
});

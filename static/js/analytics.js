// Chart.js rendering for Analytics Dashboards
document.addEventListener("DOMContentLoaded", () => {
    // 1. Admin Analytics
    const categoryCtx = document.getElementById("categoryChart");
    const statusCtx = document.getElementById("statusChart");
    const venueCtx = document.getElementById("venueChart");

    if (categoryCtx || statusCtx || venueCtx) {
        fetch("/api/reports/charts-data")
            .then(res => res.json())
            .then(data => {
                // Category Distribution Chart
                if (categoryCtx && data.categories) {
                    new Chart(categoryCtx, {
                        type: "pie",
                        data: {
                            labels: data.categories.labels,
                            datasets: [{
                                data: data.categories.data,
                                backgroundColor: ["#2563eb", "#7e3af2", "#0e9f6e", "#f59e0b", "#ef4444", "#3b82f6"]
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                legend: { position: "bottom" },
                                title: { display: true, text: "Events by Category" }
                            }
                        }
                    });
                }

                // Registration Status Doughnut Chart
                if (statusCtx && data.registration_status) {
                    new Chart(statusCtx, {
                        type: "doughnut",
                        data: {
                            labels: data.registration_status.labels,
                            datasets: [{
                                data: data.registration_status.data,
                                backgroundColor: ["#0e9f6e", "#3b82f6", "#f59e0b", "#ef4444"]
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                legend: { position: "bottom" },
                                title: { display: true, text: "Overall Registration Funnel" }
                            }
                        }
                    });
                }

                // Venue Utilization Bar Chart
                if (venueCtx && data.venues) {
                    new Chart(venueCtx, {
                        type: "bar",
                        data: {
                            labels: data.venues.labels,
                            datasets: [{
                                label: "Hosted Events Count",
                                data: data.venues.data,
                                backgroundColor: "#1e40af"
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: { beginAtZero: true, ticks: { precision: 0 } }
                            },
                            plugins: {
                                legend: { display: false },
                                title: { display: true, text: "Venue Utilization (Events Hosted)" }
                            }
                        }
                    });
                }
            })
            .catch(err => console.error("Error loading charts data:", err));
    }
});

// QR Check-in Terminal Handler
document.addEventListener("DOMContentLoaded", () => {
    const checkinForm = document.getElementById("asyncCheckinForm");
    const ticketInput = document.getElementById("ticket_code_input");
    const statusBox = document.getElementById("checkinResultAlert");
    const resultDetails = document.getElementById("checkinDetails");
    const checkinTableBody = document.getElementById("liveCheckinTableBody");

    if (checkinForm) {
        checkinForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const ticketCode = ticketInput.value.trim();
            if (!ticketCode) return;

            statusBox.className = "alert alert-info d-block";
            statusBox.innerText = "Verifying ticket with database...";
            resultDetails.innerHTML = "";

            try {
                const response = await fetch("/api/checkin", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ ticket_code: ticketCode })
                });
                const res = await response.json();

                if (res.success) {
                    statusBox.className = "alert alert-success d-block";
                    statusBox.innerHTML = `<strong>Verified!</strong> ${res.message}`;

                    if (res.data) {
                        resultDetails.innerHTML = `
                            <div class="card p-3 mt-2 bg-light border-success">
                                <h6 class="text-success mb-1"><i class="fas fa-check-circle"></i> Check-in Confirmed</h6>
                                <p class="mb-0"><strong>Student:</strong> ${res.data.student_name}</p>
                                <p class="mb-0"><strong>Ticket:</strong> <code>${res.data.ticket_code}</code></p>
                                <p class="mb-0 text-muted"><small>Time: ${res.data.check_in_time}</small></p>
                            </div>
                        `;

                        // Prepend row to table if present
                        if (checkinTableBody) {
                            const newRow = document.createElement("tr");
                            newRow.className = "table-success";
                            newRow.innerHTML = `
                                <td><code>${res.data.ticket_code}</code></td>
                                <td>${res.data.student_name}</td>
                                <td><span class="badge bg-success">Checked-In</span></td>
                                <td>${res.data.check_in_time}</td>
                            `;
                            checkinTableBody.insertBefore(newRow, checkinTableBody.firstChild);
                        }
                    }
                    ticketInput.value = "";
                    ticketInput.focus();
                } else {
                    statusBox.className = "alert alert-danger d-block";
                    statusBox.innerHTML = `<strong>Failed:</strong> ${res.message}`;
                }
            } catch (err) {
                statusBox.className = "alert alert-danger d-block";
                statusBox.innerText = `Network or Server Error: ${err.message}`;
            }
        });
    }
});

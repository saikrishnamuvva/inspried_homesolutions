const API = "http://127.0.0.1:5000";

document.addEventListener("DOMContentLoaded", function () {

    const bookingForm = document.getElementById("bookingForm");
    const successMessage = document.getElementById("successMessage");

    if (!bookingForm) return;

    // Hide success message initially
    if (successMessage) {
        successMessage.style.display = "none";
    }

    // Prevent selecting past dates
    const today = new Date().toISOString().split("T")[0];
    const dateInput = document.getElementById("date");

    if (dateInput) {
        dateInput.min = today;
    }

    bookingForm.addEventListener("submit", async function (e) {

        e.preventDefault();

        // Get form values
        const name = document.getElementById("name").value.trim();
        const email = document.getElementById("email").value.trim();
        const phone = document.getElementById("phone").value.trim();
        const person = document.getElementById("person").value;
        const service = document.getElementById("service").value;
        const date = document.getElementById("date").value;
        const time = document.getElementById("time").value;
        const address = document.getElementById("address").value.trim();
        const description = document.getElementById("description").value.trim();

        // Validation
        if (
            !name ||
            !email ||
            !phone ||
            !person ||
            !service ||
            !date ||
            !time ||
            !address
        ) {
            alert("Please fill in all required fields.");
            return;
        }

        // Data sent to Flask
        const bookingData = {
            name: name,
            email: email,
            phone: phone,
            person: person,
            service: service,
            booking_date: date + " " + time,
            address: address,
            message: description
        };

        try {

            const response = await fetch(API + "/api/booking", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(bookingData)
            });

            const data = await response.json();

            if (data.success) {

                // Clear form
                bookingForm.reset();

                // Show success message
                if (successMessage) {
                    successMessage.style.display = "block";

                    successMessage.scrollIntoView({
                        behavior: "smooth",
                        block: "center"
                    });
                }

                console.log(
                    "Booking successful. ID:",
                    data.booking_id
                );

            } else {

                alert(
                    data.message ||
                    "Booking failed. Please try again."
                );
            }

        } catch (error) {

            console.error("Booking Error:", error);

            alert(
                "Unable to connect to Flask backend. " +
                "Please make sure the server is running."
            );
        }
    });
});
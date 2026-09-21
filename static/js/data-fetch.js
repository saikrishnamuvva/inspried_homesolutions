const API = "http://127.0.0.1:5000";

// ==========================================
// HELPER: Get Token
// ==========================================
function getToken() {
    return localStorage.getItem("token");
}

// ==========================================
// HELPER: Auth Header
// ==========================================
function getAuthHeaders() {
    const token = getToken();
    const headers = {
        "Content-Type": "application/json"
    };

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    return headers;
}

// ==========================================
// GENERIC FETCH FUNCTION
// ==========================================
async function fetchData(endpoint, options = {}) {
    try {
        const response = await fetch(API + endpoint, {
            ...options,
            headers: {
                ...getAuthHeaders(),
                ...(options.headers || {})
            }
        });

        // Handle unauthorized
        if (response.status === 401) {
            localStorage.removeItem("token");
            localStorage.removeItem("user");
            alert("Session expired. Please login again.");
            window.location.href = "login.html";
            return null;
        }

        const data = await response.json();
        return data;

    } catch (error) {
        console.error("Fetch error:", error);
        return null;
    }
}

// ==========================================
// APPLIANCES
// ==========================================
async function getAppliances() {
    return await fetchData("/api/appliances");
}

async function searchAppliances(keyword) {
    return await fetchData(`/api/appliances/search?keyword=${encodeURIComponent(keyword)}`);
}

async function compareAppliances(ids) {
    // ids should be a string like "1,2,3"
    return await fetchData(`/api/appliances/comparison?ids=${ids}`);
}

// ==========================================
// BOOKINGS
// ==========================================
async function getBookings() {
    return await fetchData("/api/booking");
}

async function createBooking(bookingData) {
    return await fetchData("/api/booking", {
        method: "POST",
        body: JSON.stringify(bookingData)
    });
}

// ==========================================
// REVIEWS
// ==========================================
async function getReviews() {
    return await fetchData("/api/reviews");
}

async function addReview(reviewData) {
    return await fetchData("/api/review", {
        method: "POST",
        body: JSON.stringify(reviewData)
    });
}

// ==========================================
// CONTACT
// ==========================================
async function sendContact(contactData) {
    return await fetchData("/api/contact", {
        method: "POST",
        body: JSON.stringify(contactData)
    });
}

async function getContacts() {
    return await fetchData("/api/contacts");
}

// ==========================================
// ANALYTICS (Protected)
// ==========================================
async function getAnalytics() {
    return await fetchData("/api/analytics");
}

// ==========================================
// USERS (Protected)
// ==========================================
async function getUsers() {
    return await fetchData("/api/users");
}

async function getCurrentUser() {
    return await fetchData("/api/me");
}
const API = "http://127.0.0.1:5000";

// Get token from localStorage
function getToken() {
    return localStorage.getItem("token");
}

// Get logged-in user
function getUser() {
    const user = localStorage.getItem("user");
    return user ? JSON.parse(user) : null;
}

// Check if user is logged in
function isLoggedIn() {
    return !!getToken();
}

// Logout function
function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "login.html";
}

// Protected API call helper
async function authFetch(url, options = {}) {
    const token = getToken();

    if (!token) {
        alert("Please login first");
        window.location.href = "login.html";
        return;
    }

    const headers = {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
        ...(options.headers || {})
    };

    const response = await fetch(API + url, {
        ...options,
        headers: headers
    });

    // Token expired or invalid
    if (response.status === 401) {
        alert("Session expired. Please login again.");
        logout();
        return;
    }

    return response;
}
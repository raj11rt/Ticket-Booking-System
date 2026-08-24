// API Client Wrapper

const getApiBaseUrl = () => {
    // If running in browser from http://localhost:8000 or similar
    if (window.location.origin && window.location.origin.startsWith("http")) {
        return window.location.origin;
    }
    // Fallback for local files or development
    return "http://localhost:8000";
};

const API_BASE = getApiBaseUrl();

const api = {
    getToken: () => localStorage.getItem("token"),
    setToken: (token) => localStorage.setItem("token", token),
    clearToken: () => {
        localStorage.removeItem("token");
        localStorage.removeItem("role");
        localStorage.removeItem("name");
    },
    
    getUserRole: () => localStorage.getItem("role"),
    getUserName: () => localStorage.getItem("name"),
    
    setUserDetails: (token, role, name) => {
        localStorage.setItem("token", token);
        localStorage.setItem("role", role);
        localStorage.setItem("name", name);
    },

    request: async (endpoint, options = {}) => {
        const url = `${API_BASE}${endpoint}`;
        
        // Prepare headers
        const headers = {
            "Content-Type": "application/json",
            ...(options.headers || {})
        };
        
        const token = api.getToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }
        
        const config = {
            ...options,
            headers
        };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                // If unauthorized, clear tokens and redirect to login
                if (response.status === 401 && !endpoint.includes("/auth/")) {
                    api.clearToken();
                    window.location.href = "/frontend/pages/login.html";
                }
                throw new Error(data.detail || "Something went wrong");
            }
            
            return data;
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            throw error;
        }
    },

    get: (endpoint, headers = {}) => api.request(endpoint, { method: "GET", headers }),
    post: (endpoint, body, headers = {}) => api.request(endpoint, { method: "POST", body: JSON.stringify(body), headers }),
    delete: (endpoint, headers = {}) => api.request(endpoint, { method: "DELETE", headers })
};

// Toast notification helper
const toast = {
    show: (message, type = "info", duration = 4000) => {
        let container = document.querySelector(".toast-container");
        if (!container) {
            container = document.createElement("div");
            container.className = "toast-container";
            document.body.appendChild(container);
        }
        
        const element = document.createElement("div");
        element.className = `toast ${type}`;
        element.innerHTML = `
            <span>${message}</span>
            <button style="background:none;border:none;color:white;cursor:pointer;font-weight:bold;margin-left:15px;" onclick="this.parentElement.remove()">✕</button>
        `;
        
        container.appendChild(element);
        
        setTimeout(() => {
            element.remove();
        }, duration);
    },
    success: (msg) => toast.show(msg, "success"),
    error: (msg) => toast.show(msg, "error"),
    info: (msg) => toast.show(msg, "info")
};

// Common header injection helper
const injectNavbar = () => {
    const header = document.querySelector("header");
    if (!header) return;
    
    const role = api.getUserRole();
    const name = api.getUserName();
    const isLoggedIn = !!role;
    
    let links = `<a href="/frontend/index.html">Browse Events</a>`;
    if (isLoggedIn) {
        if (role === "admin") {
            links += `<a href="/frontend/pages/admin.html">Manage Venues</a>`;
        } else if (role === "organiser") {
            links += `<a href="/frontend/pages/organiser.html">Organiser Panel</a>`;
        } else {
            links += `<a href="/frontend/pages/bookings.html">My Bookings</a>`;
        }
    }
    
    const authSection = isLoggedIn 
        ? `<div style="display:flex;align-items:center;gap:15px;">
             <span style="font-size:14px;color:var(--text-muted);">Hi, <strong>${name}</strong> (${role})</span>
             <button class="btn btn-secondary" onclick="logoutUser()">Logout</button>
           </div>`
        : `<a href="/frontend/pages/login.html" class="btn btn-secondary">Login</a>
           <a href="/frontend/pages/register.html" class="btn btn-primary">Sign Up</a>`;
           
    header.innerHTML = `
        <div class="nav-container">
            <a href="/frontend/index.html" class="logo">🎟️ Ticket<span>Flow</span></a>
            <nav class="nav-links">
                ${links}
            </nav>
            <div class="nav-auth">
                ${authSection}
            </div>
        </div>
    `;
};

window.logoutUser = () => {
    api.clearToken();
    toast.info("Logged out successfully");
    setTimeout(() => {
        window.location.href = "/frontend/index.html";
    }, 1000);
};

// Auto-run on page load
document.addEventListener("DOMContentLoaded", () => {
    injectNavbar();
});

// SEND OTP
function sendOTP() {
    const email = document.getElementById('email').value;

    fetch('/api/forgot-password/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ email })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message || data.error);
        if (data.message) {
            window.location.href = "/verify-otp/?email=" + email;
        }
    });
}

// VERIFY OTP
function verifyOTP() {
    const email = document.getElementById('email').value;
    const otp = document.getElementById('otp').value;

    fetch('/api/verify-otp/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ email, otp })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message || data.error);
        if (data.token) {
            window.location.href = "/reset-password/?token=" + data.token;
        }
    });
}

// RESET PASSWORD
function resetPassword() {
    const token = document.getElementById('token').value;
    const password = document.getElementById('password').value;

    fetch('/api/reset-password/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ token, password })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message || data.error);
        if (data.message) {
            window.location.href = "/login/";
        }
    });
}

// CSRF helper (important)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

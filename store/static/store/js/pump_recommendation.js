document.getElementById('recommendationForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const depth = document.getElementById('depth_ft').value;
    const usage = document.getElementById('usage_type').value;
    const phase = document.getElementById('phase').value;
    const budget = document.getElementById('budget').value;

    fetch('/api/recommend-pump/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            depth_ft: depth,
            usage_type: usage,
            phase: phase,
            budget: budget
        })
    })
    .then(response => response.json())
    .then(data => {
        const resultsSection = document.getElementById('resultsSection');
        const resultsDiv = document.getElementById('recommendationResults');

        resultsDiv.innerHTML = '';
        resultsSection.classList.remove('d-none');

        if (data.recommendations.length === 0) {
            resultsDiv.innerHTML = `<p class="text-muted">No suitable pumps found.</p>`;
            return;
        }

        data.recommendations.forEach(pump => {
            resultsDiv.innerHTML += `
                <div class="col-md-4 mb-4">
                    <div class="card h-100 shadow-sm">
                        <div class="card-body">
                            <h5 class="card-title">${pump.name}</h5>
                            <p class="mb-1"><strong>Model:</strong> ${pump.model_number || '-'}</p>
                            <p class="mb-1"><strong>Power:</strong> ${pump.motor_power_hp} HP</p>
                            <p class="mb-1"><strong>Max Depth:</strong> ${pump.max_depth_ft} ft</p>
                            <p class="mb-1"><strong>Flow:</strong> ${pump.max_flow_lpm} LPM</p>
                            <p class="mb-2"><strong>Price:</strong> ₹${pump.price}</p>

                            ${pump.reason ? `<small class="text-success">${pump.reason}</small>` : ''}

                            <div class="mt-3">
                                <a href="/product/${pump.id}/" class="btn btn-outline-primary btn-sm">
                                    View Product
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
    })
    .catch(error => {
        console.error(error);
        alert('Something went wrong!');
    });
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function displayTestResults(results) {
    const resultsContainer = document.getElementById('test-results');
    resultsContainer.innerHTML = '';

    results.forEach(result => {
        const testCard = document.createElement('div');
        testCard.className = `test-card ${result.status.toLowerCase()}`;
        
        testCard.innerHTML = `
            <h3>${result.test_name}</h3>
            <div class="status-codes">
                <span>Expected: ${result.expected_status}</span>
                <span>Actual: ${result.actual_status}</span>
            </div>
            <div class="request-details">
                <h4>Request</h4>
                <pre>${JSON.stringify(result.request, null, 2)}</pre>
            </div>
            <div class="response-details">
                <h4>Response</h4>
                <pre>${JSON.stringify(result.response, null, 2)}</pre>
            </div>
            <div class="test-status ${result.status.toLowerCase()}">
                ${result.status}
            </div>
        `;
        
        resultsContainer.appendChild(testCard);
    });
}

async function runTests() {
    const curlCommand = document.getElementById('curl-input').value;
    
    try {
        const response = await fetch('/run_tests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ curl_command: curlCommand })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayTestResults(data.results);
        } else {
            alert('Error running tests: ' + data.error);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}
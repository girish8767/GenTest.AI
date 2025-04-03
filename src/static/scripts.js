// Function to toggle test details visibility
function toggleTestDetails(index) {
    const testDetails = document.getElementById(`test-details-${index}`);
    if (testDetails) {
        testDetails.style.display =
            testDetails.style.display === 'block' ? 'none' : 'block';
    }

    const testBody = document.getElementById(`test-body-${index}`);
    if (testBody) {
        const testHeader = testBody.previousElementSibling;

        // Toggle active class for both header and body
        testBody.classList.toggle('active');
        testHeader.classList.toggle('active');
    }
}

// Function to parse curl command and extract URL, headers, and body
function parseCurlCommand(curlCommand) {
    if (!curlCommand) return { url: '', headers: {}, body: '' };

    const result = {
        url: '',
        headers: {},
        body: ''
    };

    // Extract URL
    const urlMatch = curlCommand.match(/curl\s+(?:--location\s+)?['"]?([^'"]+?)['"]?(?:\s|$)/);
    if (urlMatch) {
        result.url = urlMatch[1];
    }

    // Extract headers
    const headerMatches = curlCommand.matchAll(/--header\s+['"]([^:]+):\s*([^'"]+)['"]/g);
    for (const match of headerMatches) {
        result.headers[match[1]] = match[2];
    }

    // Extract body
    const bodyMatch = curlCommand.match(/--data(?:-raw)?\s+['"]([^'"]+)['"]/);
    if (bodyMatch) {
        result.body = bodyMatch[1];
    }

    return result;
}

// Function to format headers for display
function formatHeaders(headers) {
    return Object.entries(headers)
        .map(([key, value]) => `${key}: ${value}`)
        .join('\n');
}

// Function to execute a test case
async function executeTest(index) {
    console.log(`Executing test case ${index + 1}`);
    const responseElement = document.getElementById(`response-${index}`);
    responseElement.textContent = 'Executing test...';

    try {
        // Get the curl command from the stored test cases
        const curlCommand = window.testCases[index].curl_command;
        if (!curlCommand || curlCommand === 'Not available') {
            responseElement.textContent = 'Error: No curl command available';
            return;
        }

        const response = await fetch('/execute-curl', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ curl_command: curlCommand })
        });

        const data = await response.json();
        console.log(`Received test result for case ${index + 1}:`, data);

        if (data.status === 'success') {
            // Format the response
            let formattedResponse = '';

            // Add status code
            formattedResponse += `Status Code: ${data.status_code || 'Unknown'}\n\n`;

            // Add headers if available
            if (data.headers) {
                formattedResponse += 'Headers:\n';
                for (const [key, value] of Object.entries(data.headers)) {
                    formattedResponse += `${key}: ${value}\n`;
                }
                formattedResponse += '\n';
            }

            // Add response body
            formattedResponse += 'Body:\n';
            formattedResponse += typeof data.response === 'object' ?
                JSON.stringify(data.response, null, 2) : data.response;

            responseElement.textContent = formattedResponse;

            // Highlight if status code matches expected
            const expectedStatusCode = window.testCases[index].expected_status_code;
            if (expectedStatusCode && data.status_code) {
                if (parseInt(expectedStatusCode) === parseInt(data.status_code)) {
                    responseElement.classList.add('status-match');
                    responseElement.classList.remove('status-mismatch');
                } else {
                    responseElement.classList.add('status-mismatch');
                    responseElement.classList.remove('status-match');
                }
            }
        } else {
            responseElement.textContent = `Error: ${data.error}`;
        }
    } catch (error) {
        console.error(`Error executing test case ${index + 1}:`, error);
        responseElement.textContent = `Error: ${error.message}`;
    }
}

// Function to generate test cases
async function generateTests() {
    const curlInput = document.getElementById('curlInput');
    const loadingSection = document.getElementById('loadingSection');
    const resultsSection = document.getElementById('resultsSection');
    const analyzeBtn = document.querySelector('.analyze-btn');

    // Disable the button
    analyzeBtn.disabled = true;

    try {
        // Show loading indicator
        loadingSection.style.display = 'block';
        resultsSection.innerHTML = '';

        console.log("Sending request to generate tests");
        const response = await fetch('/generate-tests', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ curl_command: curlInput.value })
        });

        const data = await response.json();
        console.log("Received response:", data);

        // Hide loading indicator
        loadingSection.style.display = 'none';

        // Re-enable the button
        analyzeBtn.disabled = false;

        if (data.status === 'success') {
            // Display test cases
            if (data.test_cases && data.test_cases.length > 0) {
                console.log(`Displaying ${data.test_cases.length} test cases`);

                // Store test cases globally for access by executeTest
                window.testCases = data.test_cases;

                // Create a heading for the test cases section
                const testCasesHeading = document.createElement('h3');
                testCasesHeading.textContent = 'Generated Test Cases';
                testCasesHeading.className = 'test-cases-heading';
                resultsSection.appendChild(testCasesHeading);

                // Create each test case as a separate dropdown
                data.test_cases.forEach((test, index) => {
                    console.log(`Processing test case ${index + 1}:`, test);

                    // Create a container for this test case
                    const testCaseContainer = document.createElement('div');
                    testCaseContainer.className = 'test-case-container';
                    resultsSection.appendChild(testCaseContainer);

                    // Create the test card with dropdown functionality
                    const testCard = document.createElement('div');
                    testCard.className = `test-card ${test.test_type || ''}`;
                    testCaseContainer.appendChild(testCard);

                    // Create the header (clickable part)
                    const testHeader = document.createElement('div');
                    testHeader.className = 'test-header';
                    testHeader.onclick = function () { toggleTestDetails(index); };
                    testHeader.innerHTML = `
                        <h3>${test.description || 'Test Case ' + (index + 1)}</h3>
                        <span class="test-type-badge ${test.test_type || ''}">${test.test_type || 'Unknown'}</span>
                    `;
                    testCard.appendChild(testHeader);

                    // Create the details section (hidden by default)
                    const testDetails = document.createElement('div');
                    testDetails.className = 'test-details';
                    testDetails.id = `test-details-${index}`;
                    testDetails.style.display = 'none';
                    testCard.appendChild(testDetails);

                    // Format the curl command for display
                    let formattedCurl = test.curl_command || 'Not available';
                    // Ensure the curl command is properly escaped for HTML display
                    formattedCurl = formattedCurl.replace(/</g, '&lt;').replace(/>/g, '&gt;');

                    // Add content to the details section
                    testDetails.innerHTML = `
                        <div class="test-details-content">
                        
                            <div class="test-curl">
                                <h4>Request:</h4>
                                <pre class="curl-command">${formattedCurl}</pre>
                            </div>
                            
                            <div class="test-execution">
                                <button class="execute-btn" onclick="executeTest(${index})">Run Test</button>
                            </div>
                            
                            <div class="test-response">
                                <h4>Response:</h4>
                                <pre id="response-${index}" class="response-content">Click "Run Test" to execute this test case</pre>
                            </div>
                        </div>
                    `;
                });
            } else {
                console.log("No test cases found");
                resultsSection.innerHTML = `
                    <div class="no-test-cases">
                        <h3>No Test Cases Generated</h3>
                        <p>The AI was unable to generate test cases for this curl command. Please try again with a different command or check the format of your request.</p>
                    </div>
                `;
            }
        } else {
            console.error("Error in response:", data.error);
            resultsSection.innerHTML = `
                <div class="error-card">
                    <h3>Error</h3>
                    <p>${data.error || 'No test results available'}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error:', error);
        loadingSection.style.display = 'none';

        // Re-enable the button on error
        analyzeBtn.disabled = false;

        resultsSection.innerHTML = `
            <div class="error-card">
                <h3>Error Occurred</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Add this after your document is loaded or at the end of your script
document.addEventListener('DOMContentLoaded', function () {
    // Set up copy button functionality
    const copyButton = document.getElementById('copyButton');
    if (copyButton) {
        copyButton.addEventListener('click', function () {
            const curlInput = document.getElementById('curlInput');

            // Select the text
            curlInput.select();
            curlInput.setSelectionRange(0, 99999); // For mobile devices

            // Copy the text
            navigator.clipboard.writeText(curlInput.value)
                .then(() => {
                    // Visual feedback that copy was successful
                    copyButton.innerHTML = '<span style="color: black;">Copied!</span>';

                    // Reset after 2 seconds
                    setTimeout(() => {
                        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                    }, 2000);
                })
                .catch(err => {
                    console.error('Failed to copy: ', err);
                    // Visual feedback that copy failed
                    copyButton.innerHTML = '<i class="fas fa-times"></i>';
                    copyButton.style.background = '#dc3545';
                    copyButton.style.color = 'white';

                    // Reset after 2 seconds
                    setTimeout(() => {
                        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                        copyButton.style.background = '';
                        copyButton.style.color = '';
                    }, 2000);
                });
        });
    }
});


function runTest(index) {
    const testCase = testCases[index];
    const curlCommand = testCase.curl_command;
    
    // Show loading state
    document.getElementById(`test-result-${index}`).innerHTML = 'Running test...';
    
    fetch('/execute-curl', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ curl_command: curlCommand }),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'error') {
            document.getElementById(`test-result-${index}`).innerHTML = `Error: ${data.error}`;
        } else {
            let responseDisplay = '';
            if (typeof data.response === 'object') {
                responseDisplay = `<pre>${JSON.stringify(data.response, null, 2)}</pre>`;
            } else {
                responseDisplay = `<pre>${data.response}</pre>`;
            }
            
            let requestBodyDisplay = '';
            if (data.request_body) {
                if (typeof data.request_body === 'object') {
                    requestBodyDisplay = `<div class="request-body">
                        <h4>Request Body:</h4>
                        <pre>${JSON.stringify(data.request_body, null, 2)}</pre>
                    </div>`;
                } else {
                    requestBodyDisplay = `<div class="request-body">
                        <h4>Request Body:</h4>
                        <pre>${data.request_body}</pre>
                    </div>`;
                }
            }
            
            document.getElementById(`test-result-${index}`).innerHTML = `
                <div>Status Code: ${data.status_code}</div>
                ${requestBodyDisplay}
                <div>
                    <h4>Response:</h4>
                    ${responseDisplay}
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById(`test-result-${index}`).innerHTML = `Error: ${error.message}`;
    });
}
# GenTest.AI - API Test Case Generator

GenTest.AI is an intelligent tool that automatically generates comprehensive test cases for API endpoints based on curl commands. It leverages AI to create both positive and negative test scenarios, helping developers ensure their APIs are robust and properly validated.

## Features

- **Automated Test Case Generation**: Convert curl commands into comprehensive test suites
- **Positive & Negative Testing**: Generate both valid and invalid test scenarios
- **Header Testing**: Test missing and invalid headers
- **Parameter Testing**: Test missing and invalid request parameters
- **Query Parameter Testing**: Test missing and invalid query parameters
- **Interactive UI**: User-friendly interface for inputting curl commands and viewing test cases
- **Test Execution**: Run tests directly from the UI and see results

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Frontend**: HTML, CSS, JavaScript
- **AI Model**: Ollama with Mistral or other available LLM models
- **Parsing**: Regular expressions and JSON processing
- **Testing**: Automated curl command execution and response analysis

## Architecture

The application follows a simple client-server architecture:

1. **Frontend**: Provides an interface for users to input curl commands and view test cases
2. **Backend API**: Processes curl commands, generates test cases, and executes tests
3. **AI Integration**: Communicates with Ollama API to generate intelligent test scenarios
4. **Test Execution Engine**: Runs the generated curl commands and captures responses

## Getting Started

### Prerequisites

- Python 3.8+
- Flask
- Ollama (for AI model)
- curl (command-line tool for making HTTP requests)

### Installation

1. Clone the repository:
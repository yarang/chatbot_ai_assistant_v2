/**
 * Tests for StreamingErrorHandler - Error handling with Toast notifications.
 *
 * Test Coverage:
 * - Error detection and classification
 * - Toast notification integration
 * - Error recovery suggestions
 * - User-friendly error messages
 * - Error logging
 * - Multiple error types handling
 */

// Simple test runner for browser environment
class TestRunner {
  constructor() {
    this.tests = [];
    this.passed = 0;
    this.failed = 0;
  }

  test(name, fn) {
    this.tests.push({ name, fn });
  }

  async run() {
    console.log("Running StreamingErrorHandler tests...");
    for (const test of this.tests) {
      try {
        await test.fn();
        this.passed++;
        console.log(`✓ ${test.name}`);
      } catch (error) {
        this.failed++;
        console.error(`✗ ${test.name}`);
        console.error(`  ${error.message}`);
      }
    }
    console.log(`\nResults: ${this.passed} passed, ${this.failed} failed`);
    return this.failed === 0;
  }
}

// Mock Toast for testing
if (typeof window !== "undefined" && !window.Toast) {
  window.Toast = {
    error: (message, options) => {
      window.Toast._lastCall = { type: "error", message, options };
      return { element: document.createElement("div") };
    },
    warning: (message, options) => {
      window.Toast._lastCall = { type: "warning", message, options };
      return { element: document.createElement("div") };
    },
    info: (message, options) => {
      window.Toast._lastCall = { type: "info", message, options };
      return { element: document.createElement("div") };
    },
    success: (message, options) => {
      window.Toast._lastCall = { type: "success", message, options };
      return { element: document.createElement("div") };
    },
    _lastCall: null
  };
}

// Test suite
const runner = new TestRunner();

runner.test("StreamingErrorHandler creates instance", () => {
  const handler = new StreamingErrorHandler();

  if (!handler.handleError) {
    throw new Error("Expected handleError method to exist");
  }
});

runner.test("StreamingErrorHandler handles connection errors", () => {
  const handler = new StreamingErrorHandler();

  handler.handleError(new Error("Connection failed"));

  if (!window.Toast._lastCall) {
    throw new Error("Expected Toast to be called");
  }

  if (window.Toast._lastCall.type !== "error") {
    throw new Error("Expected error toast type");
  }
});

runner.test("StreamingErrorHandler handles timeout errors", () => {
  const handler = new StreamingErrorHandler();

  handler.handleError(new Error("Request timeout"));

  if (!window.Toast._lastCall.message.includes("timeout")) {
    throw new Error("Expected message to mention timeout");
  }
});

runner.test("StreamingErrorHandler handles network errors", () => {
  const handler = new StreamingErrorHandler();

  const error = new Error("Failed to fetch");
  error.name = "TypeError";

  handler.handleError(error);

  if (!window.Toast._lastCall.message.includes("network")) {
    throw new Error("Expected message to mention network");
  }
});

runner.test("StreamingErrorHandler provides recovery suggestions", () => {
  const handler = new StreamingErrorHandler();

  handler.handleError(new Error("Connection lost"));

  const message = window.Toast._lastCall.message.toLowerCase();

  // Check for recovery suggestions
  const hasSuggestion = message.includes("retry") ||
                       message.includes("check") ||
                       message.includes("reconnect");

  if (!hasSuggestion) {
    throw new Error("Expected error message to include recovery suggestion");
  }
});

runner.test("StreamingErrorHandler handles streaming errors", () => {
  const handler = new StreamingErrorHandler();

  handler.handleError(new Error("Stream interrupted"));

  if (window.Toast._lastCall.type !== "error") {
    throw new Error("Expected error toast for streaming error");
  }
});

runner.test("StreamingErrorHandler error logging", () => {
  const handler = new StreamingErrorHandler();
  let logged = false;

  const originalError = console.error;
  console.error = (...args) => {
    logged = true;
    originalError(...args);
  };

  handler.handleError(new Error("Test error"));

  console.error = originalError;

  if (!logged) {
    throw new Error("Expected error to be logged to console");
  }
});

runner.test("StreamingErrorHandler with custom error messages", () => {
  const handler = new StreamingErrorHandler({
    messages: {
      "Connection failed": "연결이 실패했습니다"
    }
  });

  handler.handleError(new Error("Connection failed"));

  if (!window.Toast._lastCall.message.includes("연결")) {
    throw new Error("Expected custom error message");
  }
});

runner.test("StreamingErrorHandler error classification", () => {
  const handler = new StreamingErrorHandler();

  const type = handler.classifyError(new Error("Connection timeout"));

  if (type !== "timeout") {
    throw new Error(`Expected 'timeout', got '${type}'`);
  }
});

runner.test("StreamingErrorHandler handles multiple errors in sequence", () => {
  const handler = new StreamingErrorHandler();

  handler.handleError(new Error("Error 1"));
  const call1 = window.Toast._lastCall.message;

  handler.handleError(new Error("Error 2"));
  const call2 = window.Toast._lastCall.message;

  if (call1 === call2) {
    throw new Error("Expected different messages for different errors");
  }
});

runner.test("StreamingErrorHandler respects silent option", () => {
  const handler = new StreamingErrorHandler();

  window.Toast._lastCall = null;

  handler.handleError(new Error("Test"), { silent: true });

  if (window.Toast._lastCall !== null) {
    throw new Error("Expected no toast notification in silent mode");
  }
});

runner.test("StreamingErrorHandler retry callback", () => {
  const handler = new StreamingErrorHandler();
  let retryCalled = false;

  handler.handleError(new Error("Connection lost"), {
    onRetry: () => {
      retryCalled = true;
    }
  });

  // Check if retry action was included
  const options = window.Toast._lastCall.options;

  if (options && options.actions && options.actions.length > 0) {
    // Execute retry action
    const retryAction = options.actions.find(a => a.label && (
      a.label.includes("Retry") || a.label.includes("재시도")
    ));

    if (retryAction) {
      retryAction.handler();
    }
  }

  if (!retryCalled && options?.actions) {
    throw new Error("Expected retry callback to be available");
  }
});

runner.test("StreamingErrorHandler handles 500 server errors", () => {
  const handler = new StreamingErrorHandler();

  const error = new Error("HTTP 500: Internal Server Error");
  handler.handleError(error);

  if (window.Toast._lastCall.type !== "error") {
    throw new Error("Expected error toast for server error");
  }
});

runner.test("StreamingErrorHandler handles 401 auth errors", () => {
  const handler = new StreamingErrorHandler();

  const error = new Error("HTTP 401: Unauthorized");
  handler.handleError(error);

  const message = window.Toast._lastCall.message.toLowerCase();

  if (!message.includes("auth") && !message.includes("인증")) {
    throw new Error("Expected message to mention authentication");
  }
});

runner.test("StreamingErrorHandler default options", () => {
  const handler = new StreamingErrorHandler();

  const defaults = handler.getDefaultOptions();

  if (defaults.duration === undefined) {
    throw new Error("Expected default duration to be defined");
  }

  if (defaults.persistent === undefined) {
    throw new Error("Expected default persistent to be defined");
  }
});

runner.test("StreamingErrorHandler preserves error stack", () => {
  const handler = new StreamingErrorHandler();
  let loggedStack = false;

  const originalError = console.error;
  console.error = (...args) => {
    if (args.some(arg => typeof arg === "string" && arg.includes("stack"))) {
      loggedStack = true;
    }
    originalError(...args);
  };

  const error = new Error("Test");
  error.stack = "Error: Test\n    at test.js:10";

  handler.handleError(error);

  console.error = originalError;

  if (!loggedStack) {
    throw new Error("Expected error stack to be logged");
  }
});

runner.test("StreamingErrorHandler error count tracking", () => {
  const handler = new StreamingErrorHandler();

  if (handler.getErrorCount() !== 0) {
    throw new Error("Expected initial error count to be 0");
  }

  handler.handleError(new Error("Error 1"));

  if (handler.getErrorCount() !== 1) {
    throw new Error("Expected error count to be 1");
  }

  handler.resetErrorCount();

  if (handler.getErrorCount() !== 0) {
    throw new Error("Expected error count to be 0 after reset");
  }
});

// Export test runner for browser console
if (typeof window !== "undefined") {
  window.testStreamingErrorHandler = () => runner.run();
}

// Node.js export
if (typeof module !== "undefined" && module.exports) {
  module.exports = { TestRunner, runner };
}

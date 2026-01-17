/**
 * Tests for ChatStreamingClient - Frontend SSE client for real-time chat streaming.
 *
 * Test Coverage:
 * - Client initialization and configuration
 * - SSE connection management
 * - Event handling (text_chunk, typing_indicator, completion, error)
 * - Auto-reconnection logic
 * - Message buffering and display
 * - Error handling and recovery
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
    console.log("Running ChatStreamingClient tests...");
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

// Mock EventSource for testing
class MockEventSource {
  constructor(url) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    this.listeners = {};
    this.openDelay = 50;
  }

  addEventListener(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  removeEventListener(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback({ data }));
    }
  }

  open() {
    this.readyState = 1; // OPEN
    setTimeout(() => this.emit("open", null), this.openDelay);
  }

  close() {
    this.readyState = 2; // CLOSED
    this.emit("close", null);
  }

  error(message) {
    this.readyState = 2; // CLOSED
    this.emit("error", new Error(message));
  }
}

// Test suite
const runner = new TestRunner();

runner.test("Client initialization with default config", () => {
  const client = new ChatStreamingClient("/api/streaming/chat");

  if (client.endpoint !== "/api/streaming/chat") {
    throw new Error("Expected endpoint to be /api/streaming/chat");
  }
  if (client.reconnectAttempts !== 0) {
    throw new Error("Expected reconnectAttempts to be 0");
  }
  if (client.maxReconnectAttempts !== 3) {
    throw new Error("Expected maxReconnectAttempts to be 3");
  }
});

runner.test("Client initialization with custom config", () => {
  const client = new ChatStreamingClient("/api/streaming/chat", {
    maxReconnectAttempts: 5,
    reconnectDelayMs: 2000,
  });

  if (client.maxReconnectAttempts !== 5) {
    throw new Error("Expected maxReconnectAttempts to be 5");
  }
  if (client.reconnectDelayMs !== 2000) {
    throw new Error("Expected reconnectDelayMs to be 2000");
  }
});

runner.test("Send message with valid data", () => {
  const client = new ChatStreamingClient("/api/streaming/chat");
  const fetchMock = {
    then: (resolve) => ({
      catch: () => {}
    })
  };

  global.fetch = () => fetchMock;

  try {
    client.sendMessage("Hello, world!", "conv-123");
    // Should not throw
  } catch (error) {
    throw new Error(`Should not throw: ${error.message}`);
  }
});

runner.test("Send message with empty string throws error", () => {
  const client = new ChatStreamingClient("/api/streaming/chat");

  try {
    client.sendMessage("");
    throw new Error("Should have thrown error for empty message");
  } catch (error) {
    if (!error.message.includes("empty")) {
      throw new Error("Expected error about empty message");
    }
  }
});

runner.test("Start streaming initializes EventSource", () => {
  const client = new ChatStreamingClient("/api/streaming/chat");
  let eventSourceCreated = false;

  global.EventSource = class extends MockEventSource {
    constructor(url) {
      super(url);
      eventSourceCreated = true;
    }
  };

  client.startStreaming("Test message");

  if (!eventSourceCreated) {
    throw new Error("EventSource should be created");
  }
});

runner.test("OnMessage callback is called for text chunks", async () => {
  const client = new ChatStreamingClient("/api/streaming/chat");
  let receivedMessage = null;

  client.onMessage((message) => {
    receivedMessage = message;
  });

  const mockSource = new MockEventSource();
  client.eventSource = mockSource;

  // Simulate receiving a text chunk event
  mockSource.emit("message", JSON.stringify({
    event_type: "text_chunk",
    data: { content: "Hello", index: 0 }
  }));

  // Wait for async processing
  await new Promise(resolve => setTimeout(resolve, 100));

  if (receivedMessage !== "Hello") {
    throw new Error(`Expected "Hello", got "${receivedMessage}"`);
  }
});

runner.test("OnTyping callback is called for typing indicators", async () => {
  const client = new ChatStreamingClient("/api/streaming/chat");
  let typingState = null;

  client.onTyping((isTyping) => {
    typingState = isTyping;
  });

  const mockSource = new MockEventSource();
  client.eventSource = mockSource;

  // Simulate typing indicator event
  mockSource.emit("message", JSON.stringify({
    event_type: "typing_indicator",
    data: { is_typing: true }
  }));

  await new Promise(resolve => setTimeout(resolve, 100));

  if (typingState !== true) {
    throw new Error(`Expected true, got ${typingState}`);
  }
});

runner.test("OnComplete callback is called on completion", async () => {
  const client = new ChatStreamingClient("/api/streaming/chat");
  let completed = false;

  client.onComplete((metadata) => {
    completed = true;
  });

  const mockSource = new MockEventSource();
  client.eventSource = mockSource;

  // Simulate completion event
  mockSource.emit("message", JSON.stringify({
    event_type: "completion",
    data: { finish_reason: "stop" }
  }));

  await new Promise(resolve => setTimeout(resolve, 100));

  if (!completed) {
    throw new Error("Expected completion callback to be called");
  }
});

runner.test("OnError callback is called for errors", async () => {
  const client = new ChatStreamingClient("/api/streaming/chat");
  let errorReceived = null;

  client.onError((error) => {
    errorReceived = error;
  });

  const mockSource = new MockEventSource();
  client.eventSource = mockSource;

  // Simulate error event
  mockSource.emit("message", JSON.stringify({
    event_type: "error",
    data: { message: "Connection failed", code: "connection_error" }
  }));

  await new Promise(resolve => setTimeout(resolve, 100));

  if (!errorReceived) {
    throw new Error("Expected error callback to be called");
  }
});

runner.test("Disconnect closes EventSource", () => {
  const client = new ChatStreamingClient("/api/streaming/chat");
  const mockSource = new MockEventSource();
  client.eventSource = mockSource;

  client.disconnect();

  if (mockSource.readyState !== 2) {
    throw new Error("EventSource should be closed");
  }
});

runner.test("Auto-reconnection on connection failure", async () => {
  let reconnectAttempts = 0;

  global.EventSource = class extends MockEventSource {
    constructor(url) {
      super(url);
      reconnectAttempts++;
      // Simulate immediate failure
      setTimeout(() => this.error("Connection failed"), 10);
    }
  };

  const client = new ChatStreamingClient("/api/streaming/chat", {
    reconnectDelayMs: 50,
  });

  client.startStreaming("Test message");

  // Wait for reconnection attempts
  await new Promise(resolve => setTimeout(resolve, 200));

  if (reconnectAttempts <= 1) {
    throw new Error(`Expected reconnection attempts > 1, got ${reconnectAttempts}`);
  }
});

// Export test runner for browser console
if (typeof window !== 'undefined') {
  window.testChatStreamingClient = () => runner.run();
}

// Node.js export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { TestRunner, MockEventSource, runner };
}

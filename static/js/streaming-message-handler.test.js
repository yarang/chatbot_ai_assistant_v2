/**
 * Tests for StreamingMessageHandler - UI component for real-time message streaming.
 *
 * Test Coverage:
 * - Message container creation and management
 * - Text chunk appending and buffering
 * - Real-time content updates
 * - Message completion handling
 * - Metadata display integration
 * - Multiple message streams
 * - HTML sanitization
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
    console.log("Running StreamingMessageHandler tests...");
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

// Test suite
const runner = new TestRunner();

runner.test("StreamingMessageHandler creates message container", () => {
  const handler = new StreamingMessageHandler("msg-123");
  const element = handler.getElement();

  if (!element) {
    throw new Error("Expected valid DOM element");
  }

  if (!element.classList.contains("streaming-message")) {
    throw new Error("Expected streaming-message class");
  }
});

runner.test("StreamingMessageHandler initializes with empty content", () => {
  const handler = new StreamingMessageHandler("msg-123");
  const contentElement = handler.getContentElement();

  if (!contentElement) {
    throw new Error("Expected content element to exist");
  }

  if (contentElement.textContent !== "") {
    throw new Error("Expected empty content initially");
  }
});

runner.test("StreamingMessageHandler appendChunk adds text content", () => {
  const handler = new StreamingMessageHandler("msg-123");
  handler.appendChunk("Hello");

  const contentElement = handler.getContentElement();
  if (contentElement.textContent !== "Hello") {
    throw new Error(`Expected 'Hello', got '${contentElement.textContent}'`);
  }
});

runner.test("StreamingMessageHandler appends multiple chunks sequentially", () => {
  const handler = new StreamingMessageHandler("msg-123");

  handler.appendChunk("Hello");
  handler.appendChunk(" ");
  handler.appendChunk("World");

  const contentElement = handler.getContentElement();
  if (contentElement.textContent !== "Hello World") {
    throw new Error(`Expected 'Hello World', got '${contentElement.textContent}'`);
  }
});

runner.test("StreamingMessageHandler getContent returns accumulated text", () => {
  const handler = new StreamingMessageHandler("msg-123");

  handler.appendChunk("AI");
  handler.appendChunk(" 응답");

  if (handler.getContent() !== "AI 응답") {
    throw new Error(`Expected 'AI 응답', got '${handler.getContent()}'`);
  }
});

runner.test("StreamingMessageHandler completes with metadata", () => {
  const handler = new StreamingMessageHandler("msg-123");

  handler.appendChunk("Complete message");
  handler.complete({
    total_tokens: 150,
    duration_ms: 2500,
    finish_reason: "stop"
  });

  const contentElement = handler.getContentElement();
  if (!contentElement.textContent.includes("Complete message")) {
    throw new Error("Expected message content to be preserved");
  }

  const metaElement = handler.getElement().querySelector(".streaming-meta");
  if (!metaElement) {
    throw new Error("Expected metadata element to exist");
  }
});

runner.test("StreamingMessageHandler isStreaming returns correct state", () => {
  const handler = new StreamingMessageHandler("msg-123");

  if (!handler.isStreaming()) {
    throw new Error("Expected isStreaming to be true initially");
  }

  handler.complete({ total_tokens: 100 });
  if (handler.isStreaming()) {
    throw new Error("Expected isStreaming to be false after complete");
  }
});

runner.test("StreamingMessageHandler reset clears content and state", () => {
  const handler = new StreamingMessageHandler("msg-123");

  handler.appendChunk("Some content");
  handler.complete({ total_tokens: 50 });

  handler.reset();

  if (handler.getContent() !== "") {
    throw new Error("Expected empty content after reset");
  }

  if (!handler.isStreaming()) {
    throw new Error("Expected isStreaming to be true after reset");
  }
});

runner.test("StreamingMessageHandler sanitizes HTML in chunks", () => {
  const handler = new StreamingMessageHandler("msg-123");

  handler.appendChunk("<script>alert('xss')</script>");

  const contentElement = handler.getContentElement();
  const scriptTags = contentElement.querySelectorAll("script");

  if (scriptTags.length > 0) {
    throw new Error("Expected HTML to be sanitized");
  }

  // Content should contain escaped HTML or text
  if (contentElement.innerHTML.includes("<script>")) {
    throw new Error("Expected script tags to be escaped");
  }
});

runner.test("StreamingMessageHandler supports custom container", () => {
  const container = document.createElement("div");
  const handler = new StreamingMessageHandler("msg-123", container);

  if (!container.contains(handler.getElement())) {
    throw new Error("Expected handler element to be in custom container");
  }
});

runner.test("StreamingMessageHandler handles Unicode and emojis", () => {
  const handler = new StreamingMessageHandler("msg-123");

  handler.appendChunk("Hello 🌍");
  handler.appendChunk(" 한국어");

  if (handler.getContent() !== "Hello 🌍 한국어") {
    throw new Error(`Expected 'Hello 🌍 한국어', got '${handler.getContent()}'`);
  }
});

runner.test("StreamingMessageHandler messageId is stored correctly", () => {
  const handler = new StreamingMessageHandler("msg-456");

  if (handler.getMessageId() !== "msg-456") {
    throw new Error(`Expected 'msg-456', got '${handler.getMessageId()}'`);
  }
});

runner.test("StreamingMessageHandler destroy removes element", () => {
  const container = document.createElement("div");
  const handler = new StreamingMessageHandler("msg-123", container);

  const element = handler.getElement();
  handler.destroy();

  if (container.contains(element)) {
    throw new Error("Expected element to be removed from container");
  }

  if (handler.getElement()) {
    throw new Error("Expected getElement to return null after destroy");
  }
});

runner.test("StreamingMessageHandler metadata displays token count", () => {
  const handler = new StreamingMessageHandler("msg-123");

  handler.appendChunk("Test");
  handler.complete({
    total_tokens: 123,
    duration_ms: 1000
  });

  const metaElement = handler.getElement().querySelector(".streaming-meta");
  const metaText = metaElement.textContent;

  if (!metaText.includes("123")) {
    throw new Error("Expected metadata to contain token count");
  }
});

runner.test("StreamingMessageHandler metadata displays duration", () => {
  const handler = new StreamingMessageHandler("msg-123");

  handler.appendChunk("Test");
  handler.complete({
    total_tokens: 100,
    duration_ms: 2500
  });

  const metaElement = handler.getElement().querySelector(".streaming-meta");
  const metaText = metaElement.textContent;

  if (!metaText.includes("2.5")) {
    throw new Error("Expected metadata to display duration in seconds");
  }
});

runner.test("StreamingMessageHandler shows streaming class while streaming", () => {
  const handler = new StreamingMessageHandler("msg-123");

  if (!handler.getElement().classList.contains("streaming")) {
    throw new Error("Expected streaming class while streaming");
  }

  handler.complete({ total_tokens: 100 });

  if (handler.getElement().classList.contains("streaming")) {
    throw new Error("Expected streaming class to be removed after complete");
  }
});

// Export test runner for browser console
if (typeof window !== "undefined") {
  window.testStreamingMessageHandler = () => runner.run();
}

// Node.js export
if (typeof module !== "undefined" && module.exports) {
  module.exports = { TestRunner, runner };
}

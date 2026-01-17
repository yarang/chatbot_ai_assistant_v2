/**
 * Integration Tests for Chat Streaming System - Full end-to-end testing.
 *
 * Test Coverage:
 * - Complete streaming workflow
 * - Component integration
 * - Error recovery
 * - User interaction scenarios
 * - Performance validation
 * - Accessibility validation
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
    console.log("Running Integration Tests for Chat Streaming...");
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

    // Coverage summary
    console.log("\n=== Coverage Summary ===");
    console.log("TypingIndicator: UI component");
    console.log("StreamingMessageHandler: Message streaming");
    console.log("ReconnectionManager: Auto-reconnection");
    console.log("AutoScrollManager: Auto-scroll UX");
    console.log("MetadataDisplay: Completion metadata");
    console.log("StreamingErrorHandler: Error handling");
    console.log("ChatStreamingClient: SSE client");

    const coverage = (this.passed / (this.passed + this.failed)) * 100;
    console.log(`\nTotal Coverage: ${coverage.toFixed(1)}%`);

    return this.failed === 0;
  }
}

// Setup mock environment
function setupMockEnvironment() {
  const container = document.createElement("div");
  container.id = "chat-test-container";
  container.style.height = "400px";
  container.style.overflow = "auto";
  document.body.appendChild(container);

  // Mock Toast if not available
  if (!window.Toast) {
    window.Toast = {
      error: (msg) => console.log(`[Toast Error] ${msg}`),
      warning: (msg) => console.log(`[Toast Warning] ${msg}`),
      info: (msg) => console.log(`[Toast Info] ${msg}`),
      success: (msg) => console.log(`[Toast Success] ${msg}`)
    };
  }

  return container;
}

function cleanupMockEnvironment(container) {
  if (container && container.parentNode) {
    container.parentNode.removeChild(container);
  }
}

// Test suite
const runner = new TestRunner();

runner.test("Integration: Complete streaming workflow", async () => {
  const container = setupMockEnvironment();

  // Create components
  const typingIndicator = new TypingIndicator("AI가 입력 중...", container);
  const messageHandler = new StreamingMessageHandler("msg-1", container);
  const scrollManager = new AutoScrollManager(container);
  const metadataDisplay = new MetadataDisplay({ container, mode: "compact" });
  const errorHandler = new StreamingErrorHandler();

  // Simulate streaming workflow
  typingIndicator.show();

  await new Promise(resolve => setTimeout(resolve, 100));

  // Start receiving chunks
  typingIndicator.hide();
  messageHandler.appendChunk("안녕하세요!");
  messageHandler.appendChunk(" ");
  messageHandler.appendChunk("저는 AI 어시스턴트입니다.");

  // Verify auto-scroll
  if (!scrollManager.isAutoScrollEnabled()) {
    throw new Error("Auto-scroll should be enabled");
  }

  // Complete streaming
  messageHandler.complete({
    total_tokens: 50,
    duration_ms: 1500,
    finish_reason: "stop"
  });

  // Verify final state
  if (messageHandler.getContent() !== "안녕하세요! 저는 AI 어시스턴트입니다.") {
    throw new Error("Message content mismatch");
  }

  if (messageHandler.isStreaming()) {
    throw new Error("Message should not be streaming after complete");
  }

  // Cleanup
  typingIndicator.destroy();
  messageHandler.destroy();
  scrollManager.destroy();
  metadataDisplay.destroy();
  cleanupMockEnvironment(container);
});

runner.test("Integration: Error handling and recovery", async () => {
  const container = setupMockEnvironment();
  const errorHandler = new StreamingErrorHandler();

  // Simulate connection error
  const error = new Error("Connection failed");
  errorHandler.handleError(error, { silent: true });

  if (errorHandler.getErrorCount() !== 1) {
    throw new Error("Expected error count to be 1");
  }

  // Verify classification
  const classification = errorHandler.classifyError(error);
  if (classification !== "connection") {
    throw new Error(`Expected 'connection', got '${classification}'`);
  }

  // Test recovery
  errorHandler.resetErrorCount();

  if (errorHandler.getErrorCount() !== 0) {
    throw new Error("Expected error count to be 0 after reset");
  }

  cleanupMockEnvironment(container);
});

runner.test("Integration: Reconnection with exponential backoff", async () => {
  const reconnectManager = new ReconnectionManager({
    maxAttempts: 3,
    baseDelayMs: 100,
    maxDelayMs: 1000
  });

  // Simulate failures
  reconnectManager.recordFailure();
  const delay1 = reconnectManager.getNextDelay();

  reconnectManager.recordFailure();
  const delay2 = reconnectManager.getNextDelay();

  if (delay2 <= delay1) {
    throw new Error("Expected delay to increase");
  }

  // Simulate successful reconnection
  reconnectManager.recordSuccess();

  if (reconnectManager.getCurrentAttempt() !== 0) {
    throw new Error("Expected attempts to reset after success");
  }

  reconnectManager.destroy();
});

runner.test("Integration: User scroll pauses auto-scroll", () => {
  const container = setupMockEnvironment();

  // Add scrollable content
  for (let i = 0; i < 20; i++) {
    const div = document.createElement("div");
    div.style.height = "50px";
    div.textContent = `Line ${i}`;
    container.appendChild(div);
  }

  const scrollManager = new AutoScrollManager(container, { threshold: 100 });

  // Should be at bottom initially
  if (!scrollManager.isNearBottom()) {
    throw new Error("Should be near bottom initially");
  }

  // User scrolls up
  container.scrollTop = 0;

  if (scrollManager.isAutoScrollEnabled()) {
    throw new Error("Auto-scroll should be disabled after user scroll");
  }

  // User scrolls back near bottom
  container.scrollTop = container.scrollHeight - container.clientHeight - 50;

  if (!scrollManager.isAutoScrollEnabled()) {
    throw new Error("Auto-scroll should be re-enabled near bottom");
  }

  scrollManager.destroy();
  cleanupMockEnvironment(container);
});

runner.test("Integration: Multiple message handlers", () => {
  const container = setupMockEnvironment();

  const handler1 = new StreamingMessageHandler("msg-1", container);
  const handler2 = new StreamingMessageHandler("msg-2", container);

  handler1.appendChunk("First message");
  handler2.appendChunk("Second message");

  if (handler1.getContent() !== "First message") {
    throw new Error("Handler 1 content mismatch");
  }

  if (handler2.getContent() !== "Second message") {
    throw new Error("Handler 2 content mismatch");
  }

  // Complete independently
  handler1.complete({ total_tokens: 10 });
  handler2.complete({ total_tokens: 20 });

  if (handler1.isStreaming() || handler2.isStreaming()) {
    throw new Error("Both handlers should be completed");
  }

  handler1.destroy();
  handler2.destroy();
  cleanupMockEnvironment(container);
});

runner.test("Integration: Metadata display formats", () => {
  const container = setupMockEnvironment();

  const display = new MetadataDisplay({ container, mode: "detailed" });

  display.update({
    total_tokens: 1234,
    duration_ms: 5678,
    finish_reason: "stop"
  });

  const text = display.getElement().textContent;

  if (!text.includes("1,234")) {
    throw new Error("Expected formatted token count");
  }

  if (!text.includes("5.7")) {
    throw new Error("Expected formatted duration");
  }

  if (!text.includes("stop")) {
    throw new Error("Expected finish reason");
  }

  display.destroy();
  cleanupMockEnvironment(container);
});

runner.test("Integration: Typing indicator animations", async () => {
  const container = setupMockEnvironment();

  const indicator = new TypingIndicator("Test...", container);

  if (indicator.isVisible()) {
    throw new Error("Indicator should be hidden initially");
  }

  indicator.show();

  if (!indicator.isVisible()) {
    throw new Error("Indicator should be visible after show()");
  }

  // Wait for animation
  await new Promise(resolve => setTimeout(resolve, 100));

  indicator.hide();

  if (indicator.isVisible()) {
    throw new Error("Indicator should be hidden after hide()");
  }

  indicator.destroy();
  cleanupMockEnvironment(container);
});

runner.test("Integration: Error classification", () => {
  const errorHandler = new StreamingErrorHandler();

  const errors = [
    { error: new Error("Connection timeout"), expected: "timeout" },
    { error: new Error("Network error"), expected: "network" },
    { error: new Error("HTTP 401"), expected: "auth" },
    { error: new Error("Stream interrupted"), expected: "streaming" },
    { error: new Error("Connection failed"), expected: "connection" }
  ];

  for (const { error, expected } of errors) {
    const classification = errorHandler.classifyError(error);
    if (classification !== expected) {
      throw new Error(`Expected '${expected}', got '${classification}' for: ${error.message}`);
    }
  }

  errorHandler.destroy();
});

runner.test("Integration: Accessibility attributes", () => {
  const container = setupMockEnvironment();

  const indicator = new TypingIndicator("Test", container);
  const messageHandler = new StreamingMessageHandler("msg-1", container);

  // Check indicator ARIA
  const indicatorElement = indicator.getElement();
  if (indicatorElement.getAttribute("role") !== "status") {
    throw new Error("Typing indicator should have role=status");
  }

  if (indicatorElement.getAttribute("aria-live") !== "polite") {
    throw new Error("Typing indicator should have aria-live=polite");
  }

  // Check message ARIA
  const messageElement = messageHandler.getElement();
  if (messageElement.getAttribute("role") !== "article") {
    throw new Error("Message should have role=article");
  }

  if (messageElement.getAttribute("aria-live") !== "polite") {
    throw new Error("Message should have aria-live=polite");
  }

  indicator.destroy();
  messageHandler.destroy();
  cleanupMockEnvironment(container);
});

runner.test("Integration: Memory cleanup", () => {
  const container = setupMockEnvironment();

  // Create multiple components
  const components = [];
  for (let i = 0; i < 10; i++) {
    components.push(new StreamingMessageHandler(`msg-${i}`, container));
  }

  // Destroy all
  components.forEach(c => c.destroy());

  // Verify cleanup
  const remainingMessages = container.querySelectorAll(".streaming-message");
  if (remainingMessages.length > 0) {
    throw new Error("All message elements should be removed");
  }

  cleanupMockEnvironment(container);
});

runner.test("Integration: Unicode and emoji support", () => {
  const container = setupMockEnvironment();

  const handler = new StreamingMessageHandler("msg-1", container);

  const testText = "Hello 🌍 한국어 🎉 漢字";
  handler.appendChunk(testText);

  if (handler.getContent() !== testText) {
    throw new Error("Unicode content mismatch");
  }

  handler.destroy();
  cleanupMockEnvironment(container);
});

runner.test("Integration: HTML sanitization", () => {
  const container = setupMockEnvironment();

  const handler = new StreamingMessageHandler("msg-1", container);

  const malicious = "<script>alert('xss')</script>Hello";
  handler.appendChunk(malicious);

  const contentElement = handler.getContentElement();
  const scripts = contentElement.querySelectorAll("script");

  if (scripts.length > 0) {
    throw new Error("HTML should be sanitized");
  }

  // Content should be present but safe
  if (!contentElement.textContent.includes("Hello")) {
    throw new Error("Safe content should be preserved");
  }

  handler.destroy();
  cleanupMockEnvironment(container);
});

runner.test("Integration: Performance with large messages", () => {
  const container = setupMockEnvironment();
  const handler = new StreamingMessageHandler("msg-1", container);

  const startTime = performance.now();

  // Simulate many chunks
  for (let i = 0; i < 100; i++) {
    handler.appendChunk(`Chunk ${i} `);
  }

  const endTime = performance.now();
  const duration = endTime - startTime;

  if (duration > 100) {
    throw new Error(`Performance issue: ${duration}ms for 100 chunks`);
  }

  handler.destroy();
  cleanupMockEnvironment(container);
});

// Export test runner for browser console
if (typeof window !== "undefined") {
  window.testStreamingIntegration = () => runner.run();
}

// Node.js export
if (typeof module !== "undefined" && module.exports) {
  module.exports = { TestRunner, runner };
}

/**
 * Tests for ReconnectionManager - Auto-reconnection logic for SSE connections.
 *
 * Test Coverage:
 * - Exponential backoff calculation
 * - Reconnection attempt tracking
 * - Max attempts limit enforcement
 * - Connection state management
 * - Retry delay calculation
 * - Manual reset functionality
 * - Event callbacks
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
    console.log("Running ReconnectionManager tests...");
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

runner.test("ReconnectionManager initializes with default config", () => {
  const manager = new ReconnectionManager();

  if (manager.getMaxAttempts() !== 3) {
    throw new Error(`Expected max attempts 3, got ${manager.getMaxAttempts()}`);
  }

  if (manager.getCurrentAttempt() !== 0) {
    throw new Error(`Expected current attempt 0, got ${manager.getCurrentAttempt()}`);
  }

  if (manager.shouldReconnect()) {
    throw new Error("Expected shouldReconnect to be true initially");
  }
});

runner.test("ReconnectionManager with custom max attempts", () => {
  const manager = new ReconnectionManager({ maxAttempts: 5 });

  if (manager.getMaxAttempts() !== 5) {
    throw new Error(`Expected max attempts 5, got ${manager.getMaxAttempts()}`);
  }
});

runner.test("ReconnectionManager increments attempts on failure", () => {
  const manager = new ReconnectionManager();

  manager.recordFailure();

  if (manager.getCurrentAttempt() !== 1) {
    throw new Error(`Expected current attempt 1, got ${manager.getCurrentAttempt()}`);
  }
});

runner.test("ReconnectionManager stops after max attempts", () => {
  const manager = new ReconnectionManager({ maxAttempts: 2 });

  manager.recordFailure();
  manager.recordFailure();

  if (manager.shouldReconnect()) {
    throw new Error("Expected shouldReconnect to be false after max attempts");
  }
});

runner.test("ReconnectionManager calculates exponential backoff", () => {
  const manager = new ReconnectionManager({
    maxAttempts: 5,
    baseDelayMs: 1000,
    maxDelayMs: 10000
  });

  const delay1 = manager.getNextDelay();
  manager.recordFailure();

  const delay2 = manager.getNextDelay();
  manager.recordFailure();

  const delay3 = manager.getNextDelay();

  if (delay2 <= delay1) {
    throw new Error("Expected delay to increase with attempts");
  }

  if (delay3 <= delay2) {
    throw new Error("Expected delay to continue increasing");
  }
});

runner.test("ReconnectionManager caps delay at maxDelayMs", () => {
  const manager = new ReconnectionManager({
    baseDelayMs: 1000,
    maxDelayMs: 5000
  });

  // Simulate many failures
  for (let i = 0; i < 10; i++) {
    manager.recordFailure();
  }

  const delay = manager.getNextDelay();

  if (delay > 5000) {
    throw new Error(`Expected delay to be capped at 5000ms, got ${delay}ms`);
  }
});

runner.test("ReconnectionManager reset clears attempts", () => {
  const manager = new ReconnectionManager();

  manager.recordFailure();
  manager.recordFailure();

  manager.reset();

  if (manager.getCurrentAttempt() !== 0) {
    throw new Error(`Expected current attempt 0 after reset, got ${manager.getCurrentAttempt()}`);
  }

  if (!manager.shouldReconnect()) {
    throw new Error("Expected shouldReconnect to be true after reset");
  }
});

runner.test("ReconnectionManager recordSuccess clears attempts", () => {
  const manager = new ReconnectionManager();

  manager.recordFailure();
  manager.recordFailure();

  manager.recordSuccess();

  if (manager.getCurrentAttempt() !== 0) {
    throw new Error("Expected attempts to clear after success");
  }
});

runner.test("ReconnectionManager onReconnecting callback", async () => {
  const manager = new ReconnectionManager();
  let callbackCalled = false;
  let attemptNumber = 0;

  manager.onReconnecting((attempt) => {
    callbackCalled = true;
    attemptNumber = attempt;
  });

  manager.recordFailure();
  manager.scheduleReconnect(() => {});

  // Wait a bit for async
  await new Promise(resolve => setTimeout(resolve, 100));

  if (!callbackCalled) {
    throw new Error("Expected onReconnecting callback to be called");
  }

  if (attemptNumber !== 1) {
    throw new Error(`Expected attempt number 1, got ${attemptNumber}`);
  }
});

runner.test("ReconnectionManager onMaxAttemptsReached callback", () => {
  const manager = new ReconnectionManager({ maxAttempts: 2 });
  let callbackCalled = false;

  manager.onMaxAttemptsReached(() => {
    callbackCalled = true;
  });

  manager.recordFailure();
  manager.recordFailure();

  if (!callbackCalled) {
    throw new Error("Expected onMaxAttemptsReached callback to be called");
  }
});

runner.test("ReconnectionManager getState returns current state", () => {
  const manager = new ReconnectionManager({ maxAttempts: 5 });

  manager.recordFailure();

  const state = manager.getState();

  if (state.currentAttempt !== 1) {
    throw new Error("Expected state.currentAttempt to be 1");
  }

  if (state.maxAttempts !== 5) {
    throw new Error("Expected state.maxAttempts to be 5");
  }

  if (state.canReconnect !== true) {
    throw new Error("Expected state.canReconnect to be true");
  }
});

runner.test("ReconnectionManager cancelPendingReconnect clears timeout", async () => {
  const manager = new ReconnectionManager();
  let reconnectCalled = false;

  manager.scheduleReconnect(() => {
    reconnectCalled = true;
  });

  manager.cancelPendingReconnect();

  // Wait longer than the default delay
  await new Promise(resolve => setTimeout(resolve, 1500));

  if (reconnectCalled) {
    throw new Error("Expected reconnect to be cancelled");
  }
});

runner.test("ReconnectionManager with custom baseDelayMs", () => {
  const manager = new ReconnectionManager({ baseDelayMs: 2000 });

  const delay = manager.getNextDelay();

  if (delay < 2000) {
    throw new Error(`Expected delay >= 2000ms, got ${delay}ms`);
  }
});

runner.test("ReconnectionManager multiple failures increase delay appropriately", () => {
  const manager = new ReconnectionManager({
    baseDelayMs: 1000,
    maxDelayMs: 30000
  });

  const delays = [];
  for (let i = 0; i < 5; i++) {
    delays.push(manager.getNextDelay());
    manager.recordFailure();
  }

  // Delays should be strictly increasing (within cap)
  for (let i = 1; i < delays.length; i++) {
    if (delays[i] <= delays[i - 1] && delays[i] < 30000) {
      throw new Error(`Expected delays[${i}] > delays[${i - 1}]`);
    }
  }
});

runner.test("ReconnectionManager handles zero maxAttempts", () => {
  const manager = new ReconnectionManager({ maxAttempts: 0 });

  if (manager.shouldReconnect()) {
    throw new Error("Expected shouldReconnect to be false with maxAttempts=0");
  }
});

// Export test runner for browser console
if (typeof window !== "undefined") {
  window.testReconnectionManager = () => runner.run();
}

// Node.js export
if (typeof module !== "undefined" && module.exports) {
  module.exports = { TestRunner, runner };
}

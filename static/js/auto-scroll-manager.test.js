/**
 * Tests for AutoScrollManager - Smart auto-scroll for chat containers.
 *
 * Test Coverage:
 * - Auto-scroll to bottom on new content
 * - User scroll detection and pause
 * - Proximity detection for scroll resumption
 * - Smooth scroll behavior
 * - Scroll state management
 * - Multiple container support
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
    console.log("Running AutoScrollManager tests...");
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

runner.test("AutoScrollManager scrolls to bottom initially", () => {
  const container = document.createElement("div");
  container.style.height = "200px";
  container.style.overflow = "auto";
  document.body.appendChild(container);

  // Add content that overflows
  for (let i = 0; i < 10; i++) {
    const div = document.createElement("div");
    div.style.height = "50px";
    div.textContent = `Line ${i}`;
    container.appendChild(div);
  }

  const manager = new AutoScrollManager(container);

  if (container.scrollTop !== container.scrollHeight - container.clientHeight) {
    throw new Error("Expected container to be scrolled to bottom");
  }

  document.body.removeChild(container);
});

runner.test("AutoScrollManager detects user scroll up", () => {
  const container = document.createElement("div");
  container.style.height = "200px";
  container.style.overflow = "auto";
  document.body.appendChild(container);

  // Add content
  for (let i = 0; i < 10; i++) {
    const div = document.createElement("div");
    div.style.height = "50px";
    div.textContent = `Line ${i}`;
    container.appendChild(div);
  }

  const manager = new AutoScrollManager(container);

  // Simulate user scroll up
  container.scrollTop = 0;

  if (manager.isAutoScrollEnabled()) {
    throw new Error("Expected auto-scroll to be disabled after user scroll");
  }

  document.body.removeChild(container);
});

runner.test("AutoScrollManager resumes when near bottom", () => {
  const container = document.createElement("div");
  container.style.height = "200px";
  container.style.overflow = "auto";
  document.body.appendChild(container);

  // Add content
  for (let i = 0; i < 10; i++) {
    const div = document.createElement("div");
    div.style.height = "50px";
    div.textContent = `Line ${i}`;
    container.appendChild(div);
  }

  const manager = new AutoScrollManager(container);

  // Scroll to near bottom (within threshold)
  container.scrollTop = container.scrollHeight - container.clientHeight - 50;

  if (!manager.isAutoScrollEnabled()) {
    throw new Error("Expected auto-scroll to be enabled when near bottom");
  }

  document.body.removeChild(container);
});

runner.test("AutoScrollManager scrollToBottom works correctly", () => {
  const container = document.createElement("div");
  container.style.height = "200px";
  container.style.overflow = "auto";
  document.body.appendChild(container);

  // Add content
  for (let i = 0; i < 10; i++) {
    const div = document.createElement("div");
    div.style.height = "50px";
    div.textContent = `Line ${i}`;
    container.appendChild(div);
  }

  const manager = new AutoScrollManager(container);

  container.scrollTop = 0;
  manager.scrollToBottom();

  const isAtBottom = container.scrollTop >= container.scrollHeight - container.clientHeight - 1;

  if (!isAtBottom) {
    throw new Error("Expected container to be at bottom after scrollToBottom");
  }

  document.body.removeChild(container);
});

runner.test("AutoScrollManager disable/enable functionality", () => {
  const container = document.createElement("div");
  container.style.height = "200px";
  container.style.overflow = "auto";
  document.body.appendChild(container);

  const manager = new AutoScrollManager(container);

  manager.disable();

  if (manager.isAutoScrollEnabled()) {
    throw new Error("Expected auto-scroll to be disabled");
  }

  manager.enable();

  if (!manager.isAutoScrollEnabled()) {
    throw new Error("Expected auto-scroll to be enabled");
  }

  document.body.removeChild(container);
});

runner.test("AutoScrollManager custom threshold", () => {
  const container = document.createElement("div");
  container.style.height = "200px";
  container.style.overflow = "auto";
  document.body.appendChild(container);

  // Add content
  for (let i = 0; i < 10; i++) {
    const div = document.createElement("div");
    div.style.height = "50px";
    div.textContent = `Line ${i}`;
    container.appendChild(div);
  }

  const manager = new AutoScrollManager(container, { threshold: 200 });

  // Scroll within custom threshold
  container.scrollTop = container.scrollHeight - container.clientHeight - 150;

  if (!manager.isAutoScrollEnabled()) {
    throw new Error("Expected auto-scroll to be enabled within custom threshold");
  }

  document.body.removeChild(container);
});

runner.test("AutoScrollManager onAutoScrollChange callback", () => {
  const container = document.createElement("div");
  container.style.height = "200px";
  container.style.overflow = "auto";
  document.body.appendChild(container);

  let callbackFired = false;
  let newState = null;

  const manager = new AutoScrollManager(container, {
    onAutoScrollChange: (enabled) => {
      callbackFired = true;
      newState = enabled;
    }
  });

  container.scrollTop = 0;

  if (!callbackFired) {
    throw new Error("Expected callback to be fired on scroll change");
  }

  if (newState !== false) {
    throw new Error("Expected new state to be false");
  }

  document.body.removeChild(container);
});

runner.test("AutoScrollManager cleanup removes event listeners", () => {
  const container = document.createElement("div");
  container.style.height = "200px";
  container.style.overflow = "auto";
  document.body.appendChild(container);

  const manager = new AutoScrollManager(container);

  manager.destroy();

  // Try to trigger scroll event - should not cause errors
  container.scrollTop = 0;

  // If we got here without errors, cleanup was successful
  document.body.removeChild(container);
});

runner.test("AutoScrollManager handles empty container", () => {
  const container = document.createElement("div");
  container.style.height = "200px";
  container.style.overflow = "auto";
  document.body.appendChild(container);

  const manager = new AutoScrollManager(container);

  if (container.scrollTop !== 0) {
    throw new Error("Expected scrollTop to be 0 for empty container");
  }

  document.body.removeChild(container);
});

runner.test("AutoScrollManager isNearBottom returns correct state", () => {
  const container = document.createElement("div");
  container.style.height = "200px";
  container.style.overflow = "auto";
  document.body.appendChild(container);

  // Add content
  for (let i = 0; i < 10; i++) {
    const div = document.createElement("div");
    div.style.height = "50px";
    div.textContent = `Line ${i}`;
    container.appendChild(div);
  }

  const manager = new AutoScrollManager(container);

  // At bottom
  if (!manager.isNearBottom()) {
    throw new Error("Expected to be near bottom when at bottom");
  }

  // Scroll up beyond threshold
  container.scrollTop = container.scrollHeight - container.clientHeight - 200;

  if (manager.isNearBottom()) {
    throw new Error("Expected to not be near bottom when scrolled up");
  }

  document.body.removeChild(container);
});

runner.test("AutoScrollManager smooth scroll option", async () => {
  const container = document.createElement("div");
  container.style.height = "200px";
  container.style.overflow = "auto";
  container.style.scrollBehavior = "auto"; // Disable native smooth scroll
  document.body.appendChild(container);

  // Add content
  for (let i = 0; i < 10; i++) {
    const div = document.createElement("div");
    div.style.height = "50px";
    div.textContent = `Line ${i}`;
    container.appendChild(div);
  }

  const manager = new AutoScrollManager(container, { smooth: true });

  container.scrollTop = 0;
  manager.scrollToBottom();

  // Wait for smooth scroll animation
  await new Promise(resolve => setTimeout(resolve, 300));

  const isAtBottom = container.scrollTop >= container.scrollHeight - container.clientHeight - 1;

  if (!isAtBottom) {
    throw new Error("Expected container to be at bottom after smooth scroll");
  }

  document.body.removeChild(container);
});

runner.test("AutoScrollManager getState returns current state", () => {
  const container = document.createElement("div");
  container.style.height = "200px";
  container.style.overflow = "auto";
  document.body.appendChild(container);

  const manager = new AutoScrollManager(container, { threshold: 150 });

  const state = manager.getState();

  if (state.enabled !== true) {
    throw new Error("Expected state.enabled to be true");
  }

  if (state.threshold !== 150) {
    throw new Error("Expected state.threshold to be 150");
  }

  if (typeof state.isNearBottom !== "boolean") {
    throw new Error("Expected state.isNearBottom to be boolean");
  }

  document.body.removeChild(container);
});

// Export test runner for browser console
if (typeof window !== "undefined") {
  window.testAutoScrollManager = () => runner.run();
}

// Node.js export
if (typeof module !== "undefined" && module.exports) {
  module.exports = { TestRunner, runner };
}

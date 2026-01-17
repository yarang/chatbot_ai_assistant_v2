/**
 * Tests for TypingIndicator - UI component for displaying typing animation.
 *
 * Test Coverage:
 * - Component initialization and DOM creation
 * - Show/hide functionality with animations
 * - Text content customization
 * - Accessibility attributes (ARIA)
 * - CSS animation integration
 * - Multiple instances management
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
    console.log("Running TypingIndicator tests...");
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

runner.test("TypingIndicator creates DOM element with correct structure", () => {
  const indicator = new TypingIndicator();
  const element = indicator.getElement();

  if (!element || element.nodeType !== 1) {
    throw new Error("Expected valid DOM element");
  }

  if (!element.classList.contains("typing-indicator")) {
    throw new Error("Expected element to have typing-indicator class");
  }

  // Check for dots
  const dots = element.querySelectorAll(".typing-dot");
  if (dots.length !== 3) {
    throw new Error(`Expected 3 typing dots, got ${dots.length}`);
  }
});

runner.test("TypingIndicator initializes hidden by default", () => {
  const indicator = new TypingIndicator();
  const element = indicator.getElement();

  if (element.style.display !== "none") {
    throw new Error("Expected indicator to be hidden by default");
  }

  if (indicator.isVisible()) {
    throw new Error("Expected isVisible() to return false");
  }
});

runner.test("TypingIndicator show() displays the indicator", () => {
  const indicator = new TypingIndicator();
  indicator.show();

  const element = indicator.getElement();
  if (element.style.display === "none") {
    throw new Error("Expected indicator to be visible after show()");
  }

  if (!indicator.isVisible()) {
    throw new Error("Expected isVisible() to return true after show()");
  }
});

runner.test("TypingIndicator hide() hides the indicator", () => {
  const indicator = new TypingIndicator();
  indicator.show();
  indicator.hide();

  const element = indicator.getElement();
  if (element.style.display !== "none") {
    throw new Error("Expected indicator to be hidden after hide()");
  }

  if (indicator.isVisible()) {
    throw new Error("Expected isVisible() to return false after hide()");
  }
});

runner.test("TypingIndicator with custom text", () => {
  const indicator = new TypingIndicator("AI is thinking...");
  const element = indicator.getElement();
  const textElement = element.querySelector(".typing-text");

  if (!textElement) {
    throw new Error("Expected typing text element to exist");
  }

  if (textElement.textContent !== "AI is thinking...") {
    throw new Error(`Expected 'AI is thinking...', got '${textElement.textContent}'`);
  }
});

runner.test("TypingIndicator setText() updates text content", () => {
  const indicator = new TypingIndicator();
  indicator.setText("Processing...");

  const element = indicator.getElement();
  const textElement = element.querySelector(".typing-text");

  if (textElement.textContent !== "Processing...") {
    throw new Error(`Expected 'Processing...', got '${textElement.textContent}'`);
  }
});

runner.test("TypingIndicator has proper ARIA attributes", () => {
  const indicator = new TypingIndicator();
  const element = indicator.getElement();

  if (element.getAttribute("role") !== "status") {
    throw new Error("Expected role='status' for accessibility");
  }

  if (element.getAttribute("aria-live") !== "polite") {
    throw new Error("Expected aria-live='polite'");
  }

  if (!element.getAttribute("aria-label")) {
    throw new Error("Expected aria-label attribute");
  }
});

runner.test("TypingIndicator supports custom container", () => {
  const container = document.createElement("div");
  const indicator = new TypingIndicator(null, container);
  indicator.show();

  if (container.children.length === 0) {
    throw new Error("Expected indicator to be appended to custom container");
  }

  if (!container.contains(indicator.getElement())) {
    throw new Error("Expected container to contain indicator element");
  }
});

runner.test("TypingIndicator destroy() removes element from DOM", () => {
  const container = document.createElement("div");
  const indicator = new TypingIndicator(null, container);
  indicator.show();

  const element = indicator.getElement();
  indicator.destroy();

  if (container.contains(element)) {
    throw new Error("Expected element to be removed from container");
  }

  if (indicator.getElement()) {
    throw new Error("Expected getElement() to return null after destroy");
  }
});

runner.test("TypingIndicator animation classes are applied", () => {
  const indicator = new TypingIndicator();
  const element = indicator.getElement();
  const dots = element.querySelectorAll(".typing-dot");

  dots.forEach((dot, index) => {
    if (!dot.classList.contains("typing-dot")) {
      throw new Error(`Expected dot ${index} to have typing-dot class`);
    }
  });
});

runner.test("TypingIndicator handles multiple instances independently", () => {
  const indicator1 = new TypingIndicator("Indicator 1");
  const indicator2 = new TypingIndicator("Indicator 2");

  indicator1.show();

  if (!indicator1.isVisible()) {
    throw new Error("Expected indicator1 to be visible");
  }

  if (indicator2.isVisible()) {
    throw new Error("Expected indicator2 to be hidden");
  }

  indicator2.show();

  if (!indicator2.isVisible()) {
    throw new Error("Expected indicator2 to be visible");
  }

  indicator1.hide();

  if (indicator1.isVisible()) {
    throw new Error("Expected indicator1 to be hidden");
  }

  if (!indicator2.isVisible()) {
    throw new Error("Expected indicator2 to still be visible");
  }
});

runner.test("TypingIndicator with null container uses document.body", () => {
  const indicator = new TypingIndicator();
  indicator.show();

  if (!document.body.contains(indicator.getElement())) {
    throw new Error("Expected indicator to be appended to document.body");
  }

  indicator.destroy();
});

runner.test("TypingIndicator default text is 'AI가 입력 중...'", () => {
  const indicator = new TypingIndicator();
  const element = indicator.getElement();
  const textElement = element.querySelector(".typing-text");

  if (textElement.textContent !== "AI가 입력 중...") {
    throw new Error(`Expected default Korean text, got '${textElement.textContent}'`);
  }
});

// Export test runner for browser console
if (typeof window !== "undefined") {
  window.testTypingIndicator = () => runner.run();
}

// Node.js export
if (typeof module !== "undefined" && module.exports) {
  module.exports = { TestRunner, runner };
}

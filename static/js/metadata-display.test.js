/**
 * Tests for MetadataDisplay - Component for displaying streaming completion metadata.
 *
 * Test Coverage:
 * - Metadata display creation and rendering
 * - Token count formatting
 * - Duration formatting (ms to seconds)
 * - Finish reason display
 * - Timestamp display
 * - Compact and detailed views
 * - Custom label support
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
    console.log("Running MetadataDisplay tests...");
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

runner.test("MetadataDisplay creates element with correct class", () => {
  const display = new MetadataDisplay();
  const element = display.getElement();

  if (!element.classList.contains("streaming-metadata")) {
    throw new Error("Expected element to have streaming-metadata class");
  }
});

runner.test("MetadataDisplay with token count", () => {
  const display = new MetadataDisplay();
  display.update({ total_tokens: 150 });

  const element = display.getElement();
  if (!element.textContent.includes("150")) {
    throw new Error("Expected element to contain token count");
  }

  if (!element.textContent.includes("tokens")) {
    throw new Error("Expected element to contain 'tokens' label");
  }
});

runner.test("MetadataDisplay with duration", () => {
  const display = new MetadataDisplay();
  display.update({ duration_ms: 2500 });

  const element = display.getElement();

  if (!element.textContent.includes("2.5")) {
    throw new Error("Expected element to display 2.5 seconds");
  }

  if (!element.textContent.includes("s")) {
    throw new Error("Expected element to contain 's' for seconds");
  }
});

runner.test("MetadataDisplay with finish reason", () => {
  const display = new MetadataDisplay();
  display.update({ finish_reason: "stop" });

  const element = display.getElement();

  if (!element.textContent.includes("stop")) {
    throw new Error("Expected element to contain finish reason");
  }
});

runner.test("MetadataDisplay with all metadata", () => {
  const display = new MetadataDisplay();
  display.update({
    total_tokens: 150,
    duration_ms: 2500,
    finish_reason: "stop"
  });

  const element = display.getElement();

  if (!element.textContent.includes("150")) {
    throw new Error("Expected token count");
  }

  if (!element.textContent.includes("2.5")) {
    throw new Error("Expected duration");
  }

  if (!element.textContent.includes("stop")) {
    throw new Error("Expected finish reason");
  }
});

runner.test("MetadataDisplay compact mode", () => {
  const display = new MetadataDisplay({ mode: "compact" });
  display.update({
    total_tokens: 100,
    duration_ms: 1000
  });

  const element = display.getElement();

  if (!element.classList.contains("compact")) {
    throw new Error("Expected element to have compact class");
  }
});

runner.test("MetadataDisplay detailed mode", () => {
  const display = new MetadataDisplay({ mode: "detailed" });
  display.update({
    total_tokens: 100,
    duration_ms: 1000
  });

  const element = display.getElement();

  if (!element.classList.contains("detailed")) {
    throw new Error("Expected element to have detailed class");
  }
});

runner.test("MetadataDisplay custom labels", () => {
  const display = new MetadataDisplay({
    labels: {
      tokens: "토큰",
      duration: "소요 시간",
      separator: "·"
    }
  });

  display.update({
    total_tokens: 100,
    duration_ms: 1000
  });

  const element = display.getElement();

  if (!element.textContent.includes("토큰")) {
    throw new Error("Expected custom token label");
  }
});

runner.test("MetadataDisplay with timestamp", () => {
  const display = new MetadataDisplay({ showTimestamp: true });
  display.update({
    total_tokens: 100,
    duration_ms: 1000
  });

  const element = display.getElement();
  const timeElement = element.querySelector(".metadata-time");

  if (!timeElement) {
    throw new Error("Expected timestamp element to exist");
  }
});

runner.test("MetadataDisplay clear removes content", () => {
  const display = new MetadataDisplay();
  display.update({ total_tokens: 100 });

  display.clear();

  const element = display.getElement();
  if (element.textContent.trim() !== "") {
    throw new Error("Expected element to be empty after clear");
  }
});

runner.test("MetadataDisplay updates incrementally", () => {
  const display = new MetadataDisplay();

  display.update({ total_tokens: 100 });
  const content1 = display.getElement().textContent;

  display.update({ duration_ms: 1000 });
  const content2 = display.getElement().textContent;

  if (content2 === content1) {
    throw new Error("Expected content to change after update");
  }

  if (!content2.includes("100")) {
    throw new Error("Expected previous token count to remain");
  }
});

runner.test("MetadataDisplay handles zero values", () => {
  const display = new MetadataDisplay();
  display.update({
    total_tokens: 0,
    duration_ms: 0
  });

  const element = display.getElement();
  if (element.textContent.trim() === "") {
    throw new Error("Expected element to display zero values");
  }
});

runner.test("MetadataDisplay handles missing values", () => {
  const display = new MetadataDisplay();
  display.update({});

  const element = display.getElement();
  // Should not throw, should handle gracefully
});

runner.test("MetadataDisplay destroy removes element", () => {
  const container = document.createElement("div");
  const display = new MetadataDisplay({ container });

  const element = display.getElement();
  display.destroy();

  if (container.contains(element)) {
    throw new Error("Expected element to be removed from container");
  }
});

runner.test("MetadataDisplay formats large numbers", () => {
  const display = new MetadataDisplay();
  display.update({ total_tokens: 1500 });

  const element = display.getElement();

  if (!element.textContent.includes("1,500") && !element.textContent.includes("1500")) {
    throw new Error("Expected large number to be formatted");
  }
});

runner.test("MetadataDisplay formats milliseconds correctly", () => {
  const display = new MetadataDisplay();

  display.update({ duration_ms: 500 });
  let text = display.getElement().textContent;
  if (!text.includes("0.5")) {
    throw new Error("Expected 500ms to format as 0.5s");
  }

  display.clear();
  display.update({ duration_ms: 1500 });
  text = display.getElement().textContent;
  if (!text.includes("1.5")) {
    throw new Error("Expected 1500ms to format as 1.5s");
  }
});

runner.test("MetadataDisplay custom container", () => {
  const container = document.createElement("div");
  const display = new MetadataDisplay({ container });

  if (!container.contains(display.getElement())) {
    throw new Error("Expected element to be in custom container");
  }
});

// Export test runner for browser console
if (typeof window !== "undefined") {
  window.testMetadataDisplay = () => runner.run();
}

// Node.js export
if (typeof module !== "undefined" && module.exports) {
  module.exports = { TestRunner, runner };
}

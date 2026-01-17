/**
 * TypingIndicator - UI component for displaying typing animation.
 *
 * Design TAG: SPEC-STREAM-001-T004
 * Function TAG: SPEC-STREAM-001-F004
 *
 * Features:
 * - Animated three-dot typing indicator
 * - Customizable text labels
 * - Accessibility support (ARIA attributes)
 * - Show/hide with smooth animations
 * - Multiple independent instances
 *
 * Example:
 * ```javascript
 * const indicator = new TypingIndicator("AI is thinking...");
 * indicator.show();
 * // Later...
 * indicator.hide();
 * // Or destroy completely
 * indicator.destroy();
 * ```
 */

export class TypingIndicator {
  /**
   * Create a new TypingIndicator instance.
   *
   * @param {string} [text="AI가 입력 중..."] - Text to display next to dots
   * @param {HTMLElement} [container=null] - Container element (defaults to document.body)
   */
  constructor(text = "AI가 입력 중...", container = null) {
    this.text = text;
    this.container = container;
    this.element = null;
    this._visible = false;

    this._createElement();
  }

  /**
   * Create the DOM element for the typing indicator.
   *
   * @private
   */
  _createElement() {
    this.element = document.createElement("div");
    this.element.className = "typing-indicator";
    this.element.style.display = "none";

    // ARIA attributes for accessibility
    this.element.setAttribute("role", "status");
    this.element.setAttribute("aria-live", "polite");
    this.element.setAttribute("aria-label", "AI가 입력 중입니다");

    // Create three animated dots
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement("span");
      dot.className = "typing-dot";
      dot.setAttribute("aria-hidden", "true");
      this.element.appendChild(dot);
    }

    // Create text label
    const textElement = document.createElement("span");
    textElement.className = "typing-text";
    textElement.textContent = this.text;
    this.element.appendChild(textElement);

    // Append to container
    const targetContainer = this.container || document.body;
    targetContainer.appendChild(this.element);
  }

  /**
   * Display the typing indicator with animation.
   *
   * @returns {TypingIndicator} This instance for chaining
   */
  show() {
    if (this.element && !this._visible) {
      this.element.style.display = "flex";
      this._visible = true;

      // Trigger animation
      requestAnimationFrame(() => {
        this.element.classList.add("typing-indicator-visible");
      });
    }
    return this;
  }

  /**
   * Hide the typing indicator with animation.
   *
   * @returns {TypingIndicator} This instance for chaining
   */
  hide() {
    if (this.element && this._visible) {
      this.element.classList.remove("typing-indicator-visible");

      // Wait for animation to complete before hiding
      setTimeout(() => {
        if (this.element) {
          this.element.style.display = "none";
        }
        this._visible = false;
      }, 300);
    }
    return this;
  }

  /**
   * Check if the indicator is currently visible.
   *
   * @returns {boolean} True if visible, false otherwise
   */
  isVisible() {
    return this._visible;
  }

  /**
   * Update the text label.
   *
   * @param {string} text - New text to display
   * @returns {TypingIndicator} This instance for chaining
   */
  setText(text) {
    this.text = text;
    const textElement = this.element?.querySelector(".typing-text");
    if (textElement) {
      textElement.textContent = text;
    }
    return this;
  }

  /**
   * Get the DOM element for this indicator.
   *
   * @returns {HTMLElement|null} The indicator element or null if destroyed
   */
  getElement() {
    return this.element;
  }

  /**
   * Remove the indicator from DOM and cleanup.
   */
  destroy() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = null;
    this._visible = false;
  }
}

// Export for UMD pattern
if (typeof window !== "undefined") {
  window.TypingIndicator = TypingIndicator;
}

// Default export for ES modules
export default TypingIndicator;

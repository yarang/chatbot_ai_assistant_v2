/**
 * AutoScrollManager - Smart auto-scroll for chat containers with user detection.
 *
 * Design TAG: SPEC-STREAM-001-T007
 * Function TAG: SPEC-STREAM-001-F007
 *
 * Features:
 * - Automatic scroll to bottom on new content
 * - User scroll detection and pause
 * - Proximity detection for scroll resumption
 * - Smooth scroll behavior option
 * - Configurable threshold
 * - Event callbacks for state changes
 *
 * Example:
 * ```javascript
 * const manager = new AutoScrollManager(chatContainer, {
 *   threshold: 100,  // pixels from bottom to consider "near bottom"
 *   smooth: true,
 *   onAutoScrollChange: (enabled) => console.log(`Auto-scroll: ${enabled}`)
 * });
 *
 * // When new message arrives
 * if (manager.isAutoScrollEnabled()) {
 *   manager.scrollToBottom();
 * }
 *
 * // Cleanup
 * manager.destroy();
 * ```
 */

export class AutoScrollManager {
  /**
   * Create a new AutoScrollManager instance.
   *
   * @param {HTMLElement} container - The scrollable container element
   * @param {Object} [options={}] - Configuration options
   * @param {number} [options.threshold=100] - Distance from bottom to consider "near bottom" (pixels)
   * @param {boolean} [options.smooth=false] - Enable smooth scrolling
   * @param {function(boolean): void} [options.onAutoScrollChange] - Callback when auto-scroll state changes
   */
  constructor(container, options = {}) {
    if (!container || !(container instanceof HTMLElement)) {
      throw new Error("Container must be a valid HTMLElement");
    }

    this.container = container;
    this.threshold = options.threshold ?? 100;
    this.smooth = options.smooth ?? false;
    this.onAutoScrollChange = options.onAutoScrollChange ?? null;

    this._enabled = true;
    this._boundHandleScroll = null;

    this._init();
  }

  /**
   * Initialize the scroll manager.
   *
   * @private
   */
  _init() {
    // Scroll to bottom initially
    this.scrollToBottom();

    // Set up scroll listener
    this._boundHandleScroll = this._handleScroll.bind(this);
    this.container.addEventListener("scroll", this._boundHandleScroll, { passive: true });
  }

  /**
   * Handle scroll events to detect user interaction.
   *
   * @private
   */
  _handleScroll() {
    const wasEnabled = this._enabled;
    const isNearBottom = this.isNearBottom();

    // Update state based on user scroll position
    if (!isNearBottom && this._enabled) {
      // User scrolled up - disable auto-scroll
      this._enabled = false;
    } else if (isNearBottom && !this._enabled) {
      // User scrolled back near bottom - re-enable auto-scroll
      this._enabled = true;
    }

    // Notify callback if state changed
    if (wasEnabled !== this._enabled && this.onAutoScrollChange) {
      try {
        this.onAutoScrollChange(this._enabled);
      } catch (error) {
        console.error("Error in onAutoScrollChange callback:", error);
      }
    }
  }

  /**
   * Check if currently near the bottom of the container.
   *
   * @returns {boolean} True if near bottom (within threshold)
   */
  isNearBottom() {
    const scrollTop = this.container.scrollTop;
    const scrollHeight = this.container.scrollHeight;
    const clientHeight = this.container.clientHeight;

    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

    return distanceFromBottom <= this.threshold;
  }

  /**
   * Check if auto-scroll is currently enabled.
   *
   * @returns {boolean} True if auto-scroll is enabled
   */
  isAutoScrollEnabled() {
    return this._enabled;
  }

  /**
   * Scroll to the bottom of the container.
   *
   * @param {boolean} [force=false] - Force scroll even if auto-scroll is disabled
   */
  scrollToBottom(force = false) {
    if (!this._enabled && !force) {
      return;
    }

    const scrollTarget = this.container.scrollHeight;

    if (this.smooth && this.container.style.scrollBehavior !== "smooth") {
      // Use smooth scroll if container supports it
      this.container.scrollTo({
        top: scrollTarget,
        behavior: "smooth"
      });
    } else {
      // Instant scroll
      this.container.scrollTop = scrollTarget;
    }
  }

  /**
   * Manually enable auto-scroll.
   */
  enable() {
    if (!this._enabled) {
      this._enabled = true;
      if (this.onAutoScrollChange) {
        try {
          this.onAutoScrollChange(true);
        } catch (error) {
          console.error("Error in onAutoScrollChange callback:", error);
        }
      }
    }
  }

  /**
   * Manually disable auto-scroll.
   */
  disable() {
    if (this._enabled) {
      this._enabled = false;
      if (this.onAutoScrollChange) {
        try {
          this.onAutoScrollChange(false);
        } catch (error) {
          console.error("Error in onAutoScrollChange callback:", error);
        }
      }
    }
  }

  /**
   * Get the current state of the scroll manager.
   *
   * @returns {Object} State information
   */
  getState() {
    return {
      enabled: this._enabled,
      threshold: this.threshold,
      smooth: this.smooth,
      isNearBottom: this.isNearBottom(),
      scrollTop: this.container.scrollTop,
      scrollHeight: this.container.scrollHeight,
      clientHeight: this.container.clientHeight
    };
  }

  /**
   * Remove event listeners and cleanup.
   */
  destroy() {
    if (this._boundHandleScroll) {
      this.container.removeEventListener("scroll", this._boundHandleScroll);
      this._boundHandleScroll = null;
    }
    this._enabled = false;
  }
}

// Export for UMD pattern
if (typeof window !== "undefined") {
  window.AutoScrollManager = AutoScrollManager;
}

// Default export for ES modules
export default AutoScrollManager;

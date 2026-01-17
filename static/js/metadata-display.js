/**
 * MetadataDisplay - Component for displaying streaming completion metadata.
 *
 * Design TAG: SPEC-STREAM-001-T008
 * Function TAG: SPEC-STREAM-001-F008
 *
 * Features:
 * - Token count display with formatting
 * - Duration display (milliseconds to seconds)
 * - Finish reason display
 * - Timestamp display
 * - Compact and detailed view modes
 * - Custom label support
 * - Incremental updates
 *
 * Example:
 * ```javascript
 * const display = new MetadataDisplay({
 *   mode: "compact",
 *   showTimestamp: true,
 *   labels: {
 *     tokens: "토큰",
 *     separator: "·"
 *   }
 * });
 *
 * display.update({
 *   total_tokens: 150,
 *   duration_ms: 2500,
 *   finish_reason: "stop"
 * });
 * ```
 */

export class MetadataDisplay {
  /**
   * Create a new MetadataDisplay instance.
   *
   * @param {Object} [options={}] - Configuration options
   * @param {HTMLElement} [options.container=null] - Container element
   * @param {string} [options.mode="compact"] - Display mode: "compact" or "detailed"
   * @param {boolean} [options.showTimestamp=false] - Show completion timestamp
   * @param {Object} [options.labels={}] - Custom labels
   * @param {string} [options.labels.tokens="tokens"] - Token count label
   * @param {string} [options.labels.duration="s"] - Duration label
   * @param {string} [options.labels.separator="·"] - Separator between items
   */
  constructor(options = {}) {
    this.container = options.container ?? null;
    this.mode = options.mode ?? "compact";
    this.showTimestamp = options.showTimestamp ?? false;

    this.labels = {
      tokens: options.labels?.tokens ?? "tokens",
      duration: options.labels?.duration ?? "s",
      separator: options.labels?.separator ?? "·",
      ...options.labels
    };

    this.element = null;
    this._metadata = {};

    this._createElement();
  }

  /**
   * Create the DOM element for metadata display.
   *
   * @private
   */
  _createElement() {
    this.element = document.createElement("div");
    this.element.className = `streaming-metadata streaming-metadata-${this.mode}`;
    this.element.setAttribute("role", "status");
    this.element.setAttribute("aria-live", "polite");

    const targetContainer = this.container || document.body;
    targetContainer.appendChild(this.element);
  }

  /**
   * Update the metadata display.
   *
   * @param {Object} metadata - Metadata to display
   * @param {number} [metadata.total_tokens] - Total token count
   * @param {number} [metadata.duration_ms] - Duration in milliseconds
   * @param {string} [metadata.finish_reason] - Reason for completion
   */
  update(metadata = {}) {
    this._metadata = { ...this._metadata, ...metadata };
    this._render();
  }

  /**
   * Render the metadata display.
   *
   * @private
   */
  _render() {
    const parts = [];

    // Token count
    if (this._metadata.total_tokens !== undefined) {
      const formattedTokens = this._formatNumber(this._metadata.total_tokens);
      parts.push(`${formattedTokens} ${this.labels.tokens}`);
    }

    // Duration
    if (this._metadata.duration_ms !== undefined) {
      const seconds = (this._metadata.duration_ms / 1000).toFixed(1);
      parts.push(`${seconds}${this.labels.duration}`);
    }

    // Finish reason
    if (this._metadata.finish_reason) {
      parts.push(`(${this._metadata.finish_reason})`);
    }

    // Join with separator
    this.element.textContent = parts.join(` ${this.labels.separator} `);

    // Add timestamp if enabled
    if (this.showTimestamp && parts.length > 0) {
      const timeElement = document.createElement("span");
      timeElement.className = "metadata-time";
      timeElement.textContent = this._formatTime(new Date());
      this.element.appendChild(document.createTextNode(" "));
      this.element.appendChild(timeElement);
    }
  }

  /**
   * Format a number with thousand separators.
   *
   * @private
   * @param {number} num - Number to format
   * @returns {string} Formatted number
   */
  _formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  /**
   * Format a time as HH:MM:SS.
   *
   * @private
   * @param {Date} date - Date to format
   * @returns {string} Formatted time
   */
  _formatTime(date) {
    return date.toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    });
  }

  /**
   * Clear the metadata display.
   */
  clear() {
    this._metadata = {};
    this.element.textContent = "";
  }

  /**
   * Get the DOM element for this display.
   *
   * @returns {HTMLElement|null} The element or null if destroyed
   */
  getElement() {
    return this.element;
  }

  /**
   * Get the current metadata.
   *
   * @returns {Object} Current metadata object
   */
  getMetadata() {
    return { ...this._metadata };
  }

  /**
   * Remove the element from DOM and cleanup.
   */
  destroy() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = null;
    this._metadata = {};
  }
}

// Export for UMD pattern
if (typeof window !== "undefined") {
  window.MetadataDisplay = MetadataDisplay;
}

// Default export for ES modules
export default MetadataDisplay;

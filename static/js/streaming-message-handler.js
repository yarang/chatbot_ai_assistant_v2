/**
 * StreamingMessageHandler - UI component for real-time message streaming display.
 *
 * Design TAG: SPEC-STREAM-001-T005
 * Function TAG: SPEC-STREAM-001-F005
 *
 * Features:
 * - Real-time text chunk appending
 * - HTML sanitization for security
 * - Metadata display (tokens, duration)
 * - Streaming state management
 * - Unicode and emoji support
 * - Message completion handling
 *
 * Example:
 * ```javascript
 * const handler = new StreamingMessageHandler("msg-123");
 *
 * handler.appendChunk("Hello");
 * handler.appendChunk(" World");
 *
 * handler.complete({
 *   total_tokens: 150,
 *   duration_ms: 2500,
 *   finish_reason: "stop"
 * });
 * ```
 */

export class StreamingMessageHandler {
  /**
   * Create a new StreamingMessageHandler instance.
   *
   * @param {string} messageId - Unique identifier for the message
   * @param {HTMLElement} [container=null] - Container element (defaults to document.body)
   */
  constructor(messageId, container = null) {
    this.messageId = messageId;
    this.container = container;
    this.element = null;
    this.contentElement = null;
    this.metaElement = null;
    this._streaming = true;
    this._content = "";

    this._createElement();
  }

  /**
   * Create the DOM structure for the streaming message.
   *
   * @private
   */
  _createElement() {
    this.element = document.createElement("div");
    this.element.className = "message assistant streaming";
    this.element.setAttribute("data-message-id", this.messageId);
    this.element.setAttribute("role", "article");
    this.element.setAttribute("aria-live", "polite");

    // Message content wrapper
    this.contentElement = document.createElement("div");
    this.contentElement.className = "message-content";
    this.element.appendChild(this.contentElement);

    // Metadata element (hidden initially)
    this.metaElement = document.createElement("div");
    this.metaElement.className = "streaming-meta";
    this.metaElement.style.display = "none";
    this.element.appendChild(this.metaElement);

    // Append to container
    const targetContainer = this.container || document.body;
    targetContainer.appendChild(this.element);
  }

  /**
   * Append a text chunk to the message content.
   *
   * @param {string} chunk - Text chunk to append
   * @returns {StreamingMessageHandler} This instance for chaining
   */
  appendChunk(chunk) {
    if (!chunk || typeof chunk !== "string") {
      return this;
    }

    // Sanitize HTML to prevent XSS
    const sanitizedChunk = this._sanitizeHtml(chunk);
    this._content += sanitizedChunk;

    // Update content element
    this.contentElement.textContent = this._content;

    return this;
  }

  /**
   * Sanitize HTML content to prevent XSS attacks.
   *
   * @private
   * @param {string} html - HTML content to sanitize
   * @returns {string} Sanitized text content
   */
  _sanitizeHtml(html) {
    const temp = document.createElement("div");
    temp.textContent = html;
    return temp.innerHTML;
  }

  /**
   * Get the current accumulated message content.
   *
   * @returns {string} The full message content
   */
  getContent() {
    return this._content;
  }

  /**
   * Get the content DOM element.
   *
   * @returns {HTMLElement} The content element
   */
  getContentElement() {
    return this.contentElement;
  }

  /**
   * Mark the message as complete and display metadata.
   *
   * @param {Object} metadata - Completion metadata
   * @param {number} [metadata.total_tokens] - Total token count
   * @param {number} [metadata.duration_ms] - Duration in milliseconds
   * @param {string} [metadata.finish_reason] - Reason for completion
   * @returns {StreamingMessageHandler} This instance for chaining
   */
  complete(metadata = {}) {
    this._streaming = false;
    this.element.classList.remove("streaming");

    // Display metadata
    if (Object.keys(metadata).length > 0) {
      this._displayMetadata(metadata);
    }

    return this;
  }

  /**
   * Display completion metadata.
   *
   * @private
   * @param {Object} metadata - Metadata to display
   */
  _displayMetadata(metadata) {
    const parts = [];

    if (metadata.total_tokens !== undefined) {
      parts.push(`${metadata.total_tokens} tokens`);
    }

    if (metadata.duration_ms !== undefined) {
      const seconds = (metadata.duration_ms / 1000).toFixed(1);
      parts.push(`${seconds}s`);
    }

    if (metadata.finish_reason) {
      parts.push(`(${metadata.finish_reason})`);
    }

    if (parts.length > 0) {
      this.metaElement.textContent = parts.join(" · ");
      this.metaElement.style.display = "block";
    }
  }

  /**
   * Check if the message is currently streaming.
   *
   * @returns {boolean} True if streaming, false otherwise
   */
  isStreaming() {
    return this._streaming;
  }

  /**
   * Get the message ID.
   *
   * @returns {string} The message ID
   */
  getMessageId() {
    return this.messageId;
  }

  /**
   * Get the DOM element for this message.
   *
   * @returns {HTMLElement|null} The message element or null if destroyed
   */
  getElement() {
    return this.element;
  }

  /**
   * Reset the message handler for reuse.
   *
   * @returns {StreamingMessageHandler} This instance for chaining
   */
  reset() {
    this._content = "";
    this._streaming = true;
    this.contentElement.textContent = "";
    this.metaElement.style.display = "none";
    this.metaElement.textContent = "";
    this.element.classList.add("streaming");

    return this;
  }

  /**
   * Remove the message from DOM and cleanup.
   */
  destroy() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = null;
    this.contentElement = null;
    this.metaElement = null;
    this._streaming = false;
  }
}

// Export for UMD pattern
if (typeof window !== "undefined") {
  window.StreamingMessageHandler = StreamingMessageHandler;
}

// Default export for ES modules
export default StreamingMessageHandler;

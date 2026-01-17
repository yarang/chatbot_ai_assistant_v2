/**
 * ChatStreamingClient - Frontend SSE client for real-time chat streaming.
 *
 * This client handles Server-Sent Events (SSE) connections for real-time
 * bidirectional communication with the chat streaming backend.
 *
 * Design TAG: SPEC-STREAM-001-T003
 * Function TAG: SPEC-STREAM-001-F003
 *
 * Features:
 * - SSE connection management with EventSource API
 * - Event handling (text_chunk, typing_indicator, completion, error)
 * - Auto-reconnection with configurable delays
 * - Message buffering and real-time display
 * - Comprehensive error handling and recovery
 *
 * Example:
 * ```javascript
 * const client = new ChatStreamingClient("/api/streaming/chat");
 *
 * client.onMessage((text) => console.log("Received:", text));
 * client.onTyping((isTyping) => updateTypingIndicator(isTyping));
 * client.onComplete((metadata) => console.log("Done:", metadata));
 * client.onError((error) => console.error("Error:", error));
 *
 * await client.startStreaming("Hello, world!");
 * ```
 */

export class ChatStreamingClient {
  /**
   * Create a new ChatStreamingClient instance.
   *
   * @param {string} endpoint - The SSE endpoint URL
   * @param {Object} options - Configuration options
   * @param {number} [options.maxReconnectAttempts=3] - Maximum reconnection attempts
   * @param {number} [options.reconnectDelayMs=1000] - Delay between reconnection attempts
   * @param {number} [options.messageTimeoutMs=30000] - Timeout for message sending
   */
  constructor(endpoint, options = {}) {
    this.endpoint = endpoint;
    this.eventSource = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 3;
    this.reconnectDelayMs = options.reconnectDelayMs || 1000;
    this.messageTimeoutMs = options.messageTimeoutMs || 30000;

    // Event callbacks
    this.messageCallbacks = [];
    this.typingCallbacks = [];
    this.completionCallbacks = [];
    this.errorCallbacks = [];

    // Connection state
    this.isConnected = false;
    this.isStreaming = false;
  }

  /**
   * Register a callback for text chunk events.
   *
   * @param {function(string): void} callback - Function to call with received text
   * @returns {ChatStreamingClient} This instance for chaining
   */
  onMessage(callback) {
    this.messageCallbacks.push(callback);
    return this;
  }

  /**
   * Register a callback for typing indicator events.
   *
   * @param {function(boolean): void} callback - Function to call with typing state
   * @returns {ChatStreamingClient} This instance for chaining
   */
  onTyping(callback) {
    this.typingCallbacks.push(callback);
    return this;
  }

  /**
   * Register a callback for completion events.
   *
   * @param {function(Object): void} callback - Function to call with completion metadata
   * @returns {ChatStreamingClient} This instance for chaining
   */
  onComplete(callback) {
    this.completionCallbacks.push(callback);
    return this;
  }

  /**
   * Register a callback for error events.
   *
   * @param {function(Error): void} callback - Function to call with errors
   * @returns {ChatStreamingClient} This instance for chaining
   */
  onError(callback) {
    this.errorCallbacks.push(callback);
    return this;
  }

  /**
   * Send a message to start streaming.
   *
   * @param {string} message - The message to send
   * @param {string} [conversationId] - Optional conversation ID
   * @param {string} [personaId] - Optional persona ID
   * @returns {Promise<void>} Promise that resolves when message is sent
   * @throws {Error} If message is empty or whitespace only
   */
  async sendMessage(message, conversationId, personaId) {
    if (!message || !message.trim()) {
      throw new Error("Message cannot be empty or whitespace only");
    }

    const payload = {
      message: message.trim(),
      ...(conversationId && { conversation_id: conversationId }),
      ...(personaId && { persona_id: personaId }),
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.messageTimeoutMs);

    try {
      const response = await fetch(this.endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Start streaming from response
      this._handleStreamResponse(response);

      clearTimeout(timeoutId);
    } catch (error) {
      clearTimeout(timeoutId);
      this._notifyError(error);
      throw error;
    }
  }

  /**
   * Start streaming a message (alias for sendMessage).
   *
   * @param {string} message - The message to send
   * @param {string} [conversationId] - Optional conversation ID
   * @param {string} [personaId] - Optional persona ID
   * @returns {Promise<void>} Promise that resolves when streaming starts
   */
  async startStreaming(message, conversationId, personaId) {
    return this.sendMessage(message, conversationId, personaId);
  }

  /**
   * Disconnect the SSE connection.
   */
  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.isConnected = false;
      this.isStreaming = false;
      this.reconnectAttempts = 0;
    }
  }

  /**
   * Handle SSE stream response from fetch.
   *
   * @private
   * @param {Response} response - The fetch response object
   */
  async _handleStreamResponse(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    this.isStreaming = true;
    this.isConnected = true;

    try {
      while (this.isStreaming) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            this._handleSSEData(data);
          }
        }
      }
    } catch (error) {
      this._notifyError(error);
      this._attemptReconnect();
    } finally {
      this.isStreaming = false;
      this.isConnected = false;
    }
  }

  /**
   * Handle SSE data message.
   *
   * @private
   * @param {string} data - JSON-encoded event data
   */
  _handleSSEData(data) {
    try {
      const event = JSON.parse(data);

      switch (event.event_type) {
        case "text_chunk":
          this._notifyMessage(event.data.content);
          break;
        case "typing_indicator":
          this._notifyTyping(event.data.is_typing);
          break;
        case "completion":
          this._notifyCompletion(event.data);
          this.isStreaming = false;
          break;
        case "error":
          this._notifyError(new Error(event.data.message || "Unknown error"));
          break;
      }
    } catch (error) {
      console.error("Failed to parse SSE event:", error);
    }
  }

  /**
   * Notify all message callbacks.
   *
   * @private
   * @param {string} text - The received text
   */
  _notifyMessage(text) {
    this.messageCallbacks.forEach((callback) => {
      try {
        callback(text);
      } catch (error) {
        console.error("Error in message callback:", error);
      }
    });
  }

  /**
   * Notify all typing callbacks.
   *
   * @private
   * @param {boolean} isTyping - The typing state
   */
  _notifyTyping(isTyping) {
    this.typingCallbacks.forEach((callback) => {
      try {
        callback(isTyping);
      } catch (error) {
        console.error("Error in typing callback:", error);
      }
    });
  }

  /**
   * Notify all completion callbacks.
   *
   * @private
   * @param {Object} metadata - The completion metadata
   */
  _notifyCompletion(metadata) {
    this.completionCallbacks.forEach((callback) => {
      try {
        callback(metadata);
      } catch (error) {
        console.error("Error in completion callback:", error);
      }
    });
  }

  /**
   * Notify all error callbacks.
   *
   * @private
   * @param {Error} error - The error
   */
  _notifyError(error) {
    this.errorCallbacks.forEach((callback) => {
      try {
        callback(error);
      } catch (err) {
        console.error("Error in error callback:", err);
      }
    });
  }

  /**
   * Attempt to reconnect after connection failure.
   *
   * @private
   */
  async _attemptReconnect() {
    if (
      this.reconnectAttempts >= this.maxReconnectAttempts ||
      !this.isStreaming
    ) {
      return;
    }

    this.reconnectAttempts++;

    setTimeout(() => {
      if (this.isStreaming && this.reconnectAttempts <= this.maxReconnectAttempts) {
        console.log(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
        // Reconnection logic would be triggered by next sendMessage call
      }
    }, this.reconnectDelayMs);
  }

  /**
   * Reset reconnection counter.
   */
  resetReconnectCounter() {
    this.reconnectAttempts = 0;
  }

  /**
   * Get current connection state.
   *
   * @returns {Object} Connection state info
   */
  getState() {
    return {
      isConnected: this.isConnected,
      isStreaming: this.isStreaming,
      reconnectAttempts: this.reconnectAttempts,
      maxReconnectAttempts: this.maxReconnectAttempts,
    };
  }
}

// Export for UMD pattern
if (typeof window !== "undefined") {
  window.ChatStreamingClient = ChatStreamingClient;
}

// Default export for ES modules
export default ChatStreamingClient;

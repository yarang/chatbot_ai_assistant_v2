/**
 * StreamingErrorHandler - Error handling with Toast notifications for streaming.
 *
 * Design TAG: SPEC-STREAM-001-T009
 * Function TAG: SPEC-STREAM-001-F009
 *
 * Features:
 * - Automatic error classification
 * - User-friendly error messages
 * - Toast notification integration
 * - Error logging with stack traces
 * - Recovery suggestions with retry actions
 * - Error count tracking
 *
 * Example:
 * ```javascript
 * const handler = new StreamingErrorHandler({
 *   messages: {
 *     "Connection failed": "연결이 실패했습니다"
 *   }
 * });
 *
 * try {
 *   await streamingClient.connect();
 * } catch (error) {
 *   handler.handleError(error, {
 *     onRetry: () => streamingClient.reconnect()
 *   });
 * }
 * ```
 */

export class StreamingErrorHandler {
  /**
   * Create a new StreamingErrorHandler instance.
   *
   * @param {Object} [options={}] - Configuration options
   * @param {Object} [options.messages={}] - Custom error messages
   * @param {boolean} [options.logErrors=true] - Log errors to console
   * @param {boolean} [options.showStack=false] - Include stack traces in logs
   */
  constructor(options = {}) {
    this.messages = options.messages ?? {};
    this.logErrors = options.logErrors ?? true;
    this.showStack = options.showStack ?? false;

    this._errorCount = 0;

    // Default error message templates (Korean)
    this.defaultMessages = {
      "Connection failed": "연결에 실패했습니다. 네트워크 연결을 확인해주세요.",
      "Connection timeout": "연결 시간이 초과되었습니다. 다시 시도해주세요.",
      "Connection lost": "연결이 끊어졌습니다. 자동 재연결을 시도합니다.",
      "Stream interrupted": "스트림이 중단되었습니다. 다시 시도해주세요.",
      "Network error": "네트워크 오류가 발생했습니다. 인터넷 연결을 확인해주세요.",
      "Server error": "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
      "Unauthorized": "인증이 필요합니다. 다시 로그인해주세요.",
      "Forbidden": "접근 권한이 없습니다.",
      "Not Found": "요청한 리소스를 찾을 수 없습니다.",
      "Too Many Requests": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."
    };
  }

  /**
   * Handle an error with appropriate user feedback.
   *
   * @param {Error} error - The error to handle
   * @param {Object} [options={}] - Handling options
   * @param {boolean} [options.silent=false] - Suppress user notification
   * @param {function} [options.onRetry] - Callback for retry action
   * @returns {StreamingErrorHandler} This instance for chaining
   */
  handleError(error, options = {}) {
    this._errorCount++;

    const silent = options.silent ?? false;
    const classification = this.classifyError(error);
    const message = this._getUserMessage(error, classification);

    // Log error
    if (this.logErrors) {
      this._logError(error, classification);
    }

    // Show user notification
    if (!silent && typeof window !== "undefined" && window.Toast) {
      this._showNotification(message, classification, options);
    }

    return this;
  }

  /**
   * Classify an error into a category.
   *
   * @param {Error} error - The error to classify
   * @returns {string} Error classification
   */
  classifyError(error) {
    const message = error.message?.toLowerCase() || "";

    if (message.includes("timeout")) {
      return "timeout";
    }

    if (message.includes("network") || message.includes("fetch")) {
      return "network";
    }

    if (message.includes("unauthorized") || error.message?.includes("401")) {
      return "auth";
    }

    if (message.includes("forbidden") || error.message?.includes("403")) {
      return "forbidden";
    }

    if (message.includes("not found") || error.message?.includes("404")) {
      return "not_found";
    }

    if (message.includes("too many") || error.message?.includes("429")) {
      return "rate_limit";
    }

    if (message.includes("500") || message.includes("internal server")) {
      return "server";
    }

    if (message.includes("connection") || message.includes("connect")) {
      return "connection";
    }

    if (message.includes("stream")) {
      return "streaming";
    }

    return "unknown";
  }

  /**
   * Get a user-friendly error message.
   *
   * @private
   * @param {Error} error - The error
   * @param {string} classification - Error classification
   * @returns {string} User-friendly message
   */
  _getUserMessage(error, classification) {
    // Check custom messages first
    for (const [key, value] of Object.entries(this.messages)) {
      if (error.message?.includes(key)) {
        return value;
      }
    }

    // Check default messages
    for (const [key, value] of Object.entries(this.defaultMessages)) {
      if (error.message?.toLowerCase().includes(key.toLowerCase())) {
        return value;
      }
    }

    // Classification-based defaults
    const classificationMessages = {
      timeout: "요청 시간이 초과되었습니다. 다시 시도해주세요.",
      network: "네트워크 연결을 확인해주세요.",
      auth: "인증이 만료되었습니다. 다시 로그인해주세요.",
      forbidden: "이 작업을 수행할 권한이 없습니다.",
      not_found: "요청한 리소스를 찾을 수 없습니다.",
      rate_limit: "너무 많은 요청을 보냈습니다. 잠시 후 다시 시도해주세요.",
      server: "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
      connection: "연결 오류가 발생했습니다. 다시 시도해주세요.",
      streaming: "스트리밍 오류가 발생했습니다. 다시 시도해주세요."
    };

    return classificationMessages[classification] || error.message || "알 수 없는 오류가 발생했습니다.";
  }

  /**
   * Log error to console.
   *
   * @private
   * @param {Error} error - The error to log
   * @param {string} classification - Error classification
   */
  _logError(error, classification) {
    const logMessage = `[StreamingError] ${classification}: ${error.message}`;

    if (this.showStack && error.stack) {
      console.error(logMessage, error.stack);
    } else {
      console.error(logMessage);
    }
  }

  /**
   * Show toast notification for error.
   *
   * @private
   * @param {string} message - User-friendly message
   * @param {string} classification - Error classification
   * @param {Object} options - Handling options
   */
  _showNotification(message, classification, options) {
    const toastOptions = {
      persistent: classification === "auth" || classification === "forbidden",
      duration: classification === "rate_limit" ? 10000 : 5000
    };

    // Add retry action for connection/timeout errors
    if (
      (classification === "connection" ||
       classification === "timeout" ||
       classification === "network") &&
      options.onRetry
    ) {
      toastOptions.actions = [
        {
          label: "다시 시도",
          type: "primary",
          handler: options.onRetry
        },
        {
          label: "닫기",
          type: "secondary"
        }
      ];
    }

    // Show appropriate toast type
    switch (classification) {
      case "auth":
      case "forbidden":
        window.Toast.error(message, toastOptions);
        break;

      case "rate_limit":
        window.Toast.warning(message, toastOptions);
        break;

      default:
        window.Toast.error(message, toastOptions);
    }
  }

  /**
   * Get the total error count.
   *
   * @returns {number} Total errors handled
   */
  getErrorCount() {
    return this._errorCount;
  }

  /**
   * Reset the error counter.
   *
   * @returns {StreamingErrorHandler} This instance for chaining
   */
  resetErrorCount() {
    this._errorCount = 0;
    return this;
  }

  /**
   * Get default options for error handling.
   *
   * @returns {Object} Default options
   */
  getDefaultOptions() {
    return {
      silent: false,
      logErrors: this.logErrors,
      showStack: this.showStack
    };
  }

  /**
   * Cleanup and destroy the handler.
   */
  destroy() {
    this._errorCount = 0;
  }
}

// Export for UMD pattern
if (typeof window !== "undefined") {
  window.StreamingErrorHandler = StreamingErrorHandler;
}

// Default export for ES modules
export default StreamingErrorHandler;

/**
 * ReconnectionManager - Auto-reconnection logic for SSE connections with exponential backoff.
 *
 * Design TAG: SPEC-STREAM-001-T006
 * Function TAG: SPEC-STREAM-001-F006
 *
 * Features:
 * - Exponential backoff with jitter
 * - Configurable max attempts
 * - Connection state tracking
 * - Event callbacks for reconnection events
 * - Pending reconnection cancellation
 * - Manual reset functionality
 *
 * Example:
 * ```javascript
 * const manager = new ReconnectionManager({
 *   maxAttempts: 5,
 *   baseDelayMs: 1000,
 *   maxDelayMs: 30000
 * });
 *
 * manager.onReconnecting((attempt) => {
 *   console.log(`Reconnection attempt ${attempt}`);
 * });
 *
 * manager.onMaxAttemptsReached(() => {
 *   console.error('Max reconnection attempts reached');
 * });
 *
 * if (manager.shouldReconnect()) {
 *   manager.recordFailure();
 *   manager.scheduleReconnect(() => connect());
 * }
 *
 * // On successful connection
 * manager.recordSuccess();
 * ```
 */

export class ReconnectionManager {
  /**
   * Create a new ReconnectionManager instance.
   *
   * @param {Object} options - Configuration options
   * @param {number} [options.maxAttempts=3] - Maximum reconnection attempts
   * @param {number} [options.baseDelayMs=1000] - Base delay in milliseconds
   * @param {number} [options.maxDelayMs=30000] - Maximum delay in milliseconds
   */
  constructor(options = {}) {
    this.maxAttempts = options.maxAttempts ?? 3;
    this.baseDelayMs = options.baseDelayMs ?? 1000;
    this.maxDelayMs = options.maxDelayMs ?? 30000;

    this._currentAttempt = 0;
    this._pendingTimeoutId = null;

    // Event callbacks
    this._reconnectingCallbacks = [];
    this._maxAttemptsReachedCallbacks = [];
  }

  /**
   * Record a connection failure and increment attempt counter.
   *
   * @returns {ReconnectionManager} This instance for chaining
   */
  recordFailure() {
    this._currentAttempt++;
    return this;
  }

  /**
   * Record a successful connection and reset attempt counter.
   *
   * @returns {ReconnectionManager} This instance for chaining
   */
  recordSuccess() {
    this._currentAttempt = 0;
    this._pendingTimeoutId = null;
    return this;
  }

  /**
   * Check if reconnection should be attempted.
   *
   * @returns {boolean} True if reconnection should be attempted
   */
  shouldReconnect() {
    return this._currentAttempt < this.maxAttempts;
  }

  /**
   * Get the current attempt count.
   *
   * @returns {number} Current attempt number
   */
  getCurrentAttempt() {
    return this._currentAttempt;
  }

  /**
   * Get the maximum allowed attempts.
   *
   * @returns {number} Maximum attempts
   */
  getMaxAttempts() {
    return this.maxAttempts;
  }

  /**
   * Calculate the next delay using exponential backoff with jitter.
   *
   * @returns {number} Delay in milliseconds
   */
  getNextDelay() {
    if (this._currentAttempt === 0) {
      return this.baseDelayMs;
    }

    // Exponential backoff: baseDelay * 2^(attempt-1)
    const exponentialDelay = this.baseDelayMs * Math.pow(2, this._currentAttempt - 1);

    // Add jitter: ±25% random variation
    const jitter = 0.5 + Math.random(); // 0.5 to 1.5
    const delayWithJitter = exponentialDelay * jitter;

    // Cap at maxDelayMs
    return Math.min(delayWithJitter, this.maxDelayMs);
  }

  /**
   * Schedule a reconnection attempt.
   *
   * @param {Function} reconnectFn - Function to call for reconnection
   * @returns {ReconnectionManager} This instance for chaining
   */
  scheduleReconnect(reconnectFn) {
    if (!this.shouldReconnect()) {
      this._notifyMaxAttemptsReached();
      return this;
    }

    // Cancel any pending reconnection
    this.cancelPendingReconnect();

    const delay = this.getNextDelay();

    this._pendingTimeoutId = setTimeout(() => {
      this._notifyReconnecting(this._currentAttempt + 1);
      reconnectFn();
    }, delay);

    return this;
  }

  /**
   * Cancel any pending reconnection attempt.
   *
   * @returns {ReconnectionManager} This instance for chaining
   */
  cancelPendingReconnect() {
    if (this._pendingTimeoutId !== null) {
      clearTimeout(this._pendingTimeoutId);
      this._pendingTimeoutId = null;
    }
    return this;
  }

  /**
   * Reset the reconnection state.
   *
   * @returns {ReconnectionManager} This instance for chaining
   */
  reset() {
    this._currentAttempt = 0;
    this.cancelPendingReconnect();
    return this;
  }

  /**
   * Register a callback for reconnection events.
   *
   * @param {function(number): void} callback - Function called with attempt number
   * @returns {ReconnectionManager} This instance for chaining
   */
  onReconnecting(callback) {
    this._reconnectingCallbacks.push(callback);
    return this;
  }

  /**
   * Register a callback for max attempts reached event.
   *
   * @param {function(): void} callback - Function called when max attempts reached
   * @returns {ReconnectionManager} This instance for chaining
   */
  onMaxAttemptsReached(callback) {
    this._maxAttemptsReachedCallbacks.push(callback);
    return this;
  }

  /**
   * Notify all reconnection callbacks.
   *
   * @private
   * @param {number} attempt - The attempt number
   */
  _notifyReconnecting(attempt) {
    this._reconnectingCallbacks.forEach((callback) => {
      try {
        callback(attempt);
      } catch (error) {
        console.error("Error in reconnection callback:", error);
      }
    });
  }

  /**
   * Notify all max attempts reached callbacks.
   *
   * @private
   */
  _notifyMaxAttemptsReached() {
    this._maxAttemptsReachedCallbacks.forEach((callback) => {
      try {
        callback();
      } catch (error) {
        console.error("Error in max attempts reached callback:", error);
      }
    });
  }

  /**
   * Get the current state of the reconnection manager.
   *
   * @returns {Object} State information
   */
  getState() {
    return {
      currentAttempt: this._currentAttempt,
      maxAttempts: this.maxAttempts,
      canReconnect: this.shouldReconnect(),
      nextDelay: this.getNextDelay(),
      hasPendingReconnect: this._pendingTimeoutId !== null,
    };
  }

  /**
   * Cleanup and destroy the manager.
   */
  destroy() {
    this.cancelPendingReconnect();
    this._reconnectingCallbacks = [];
    this._maxAttemptsReachedCallbacks = [];
  }
}

// Export for UMD pattern
if (typeof window !== "undefined") {
  window.ReconnectionManager = ReconnectionManager;
}

// Default export for ES modules
export default ReconnectionManager;

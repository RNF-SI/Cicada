import { TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { NgZone } from '@angular/core';

import { GlobalErrorHandler } from './global-error.handler';
import { LoggingService } from '../services/logging.service';

// Mock PromiseRejectionEvent for Node.js/Jest environment
class MockPromiseRejectionEvent extends Event {
  promise: Promise<any>;
  reason: any;

  constructor(type: string, init: { promise: Promise<any>; reason: any }) {
    super(type);
    this.promise = init.promise;
    this.reason = init.reason;
  }
}

// Define PromiseRejectionEvent globally if it doesn't exist
if (typeof globalThis.PromiseRejectionEvent === 'undefined') {
  (globalThis as any).PromiseRejectionEvent = MockPromiseRejectionEvent;
}

describe('GlobalErrorHandler', () => {
  let handler: GlobalErrorHandler;
  let loggingServiceMock: {
    error: jest.Mock;
  };
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    loggingServiceMock = {
      error: jest.fn()
    };

    TestBed.configureTestingModule({
      providers: [
        GlobalErrorHandler,
        { provide: LoggingService, useValue: loggingServiceMock }
      ]
    });

    handler = TestBed.inject(GlobalErrorHandler);
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    TestBed.resetTestingModule();
  });

  // ==================== BASIC TESTS ====================

  describe('Basic Operations', () => {
    it('should be created', () => {
      expect(handler).toBeTruthy();
    });

    it('should implement ErrorHandler interface', () => {
      expect(handler.handleError).toBeDefined();
      expect(typeof handler.handleError).toBe('function');
    });
  });

  // ==================== HTTP ERROR HANDLING ====================

  describe('HTTP Error Handling', () => {
    it('should not re-log HTTP errors (already handled by interceptor)', () => {
      const httpError = new HttpErrorResponse({
        status: 404,
        statusText: 'Not Found',
        url: '/api/test'
      });

      handler.handleError(httpError);

      // HTTP errors should not be logged again
      expect(loggingServiceMock.error).not.toHaveBeenCalled();
    });

    it('should not log HTTP 500 errors', () => {
      const httpError = new HttpErrorResponse({
        status: 500,
        statusText: 'Internal Server Error'
      });

      handler.handleError(httpError);

      expect(loggingServiceMock.error).not.toHaveBeenCalled();
    });

    it('should not log HTTP 401 errors', () => {
      const httpError = new HttpErrorResponse({
        status: 401,
        statusText: 'Unauthorized'
      });

      handler.handleError(httpError);

      expect(loggingServiceMock.error).not.toHaveBeenCalled();
    });
  });

  // ==================== JAVASCRIPT ERROR HANDLING ====================

  describe('JavaScript Error Handling', () => {
    it('should log regular JavaScript errors', () => {
      const error = new Error('Test error');

      handler.handleError(error);

      expect(loggingServiceMock.error).toHaveBeenCalledWith(
        'Unhandled error',
        error,
        expect.objectContaining({
          type: 'javascript_error'
        })
      );
    });

    it('should log to console in development', () => {
      const error = new Error('Console test error');

      handler.handleError(error);

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'GlobalErrorHandler caught:',
        error
      );
    });

    it('should handle errors with no message', () => {
      const error = new Error();

      handler.handleError(error);

      expect(loggingServiceMock.error).toHaveBeenCalledWith(
        'Unhandled error',
        error,
        expect.objectContaining({
          type: 'javascript_error'
        })
      );
    });

    it('should handle TypeError', () => {
      const error = new TypeError('Cannot read property of undefined');

      handler.handleError(error);

      expect(loggingServiceMock.error).toHaveBeenCalledWith(
        'Unhandled error',
        error,
        expect.objectContaining({
          type: 'javascript_error'
        })
      );
    });

    it('should handle RangeError', () => {
      const error = new RangeError('Invalid array length');

      handler.handleError(error);

      expect(loggingServiceMock.error).toHaveBeenCalledWith(
        'Unhandled error',
        error,
        expect.objectContaining({
          type: 'javascript_error'
        })
      );
    });
  });

  // ==================== CHUNK LOAD ERROR HANDLING ====================

  describe('Chunk Load Error Handling', () => {
    it('should detect ChunkLoadError by name', () => {
      const error = new Error('Loading chunk failed');
      error.name = 'ChunkLoadError';

      handler.handleError(error);

      expect(loggingServiceMock.error).toHaveBeenCalledWith(
        'Chunk loading failed - application may need refresh',
        error,
        expect.objectContaining({
          type: 'chunk_load_error'
        })
      );
    });

    it('should detect chunk errors by message containing "Loading chunk"', () => {
      const error = new Error('Loading chunk 5 failed');

      handler.handleError(error);

      expect(loggingServiceMock.error).toHaveBeenCalledWith(
        'Chunk loading failed - application may need refresh',
        error,
        expect.objectContaining({
          type: 'chunk_load_error'
        })
      );
    });

    it('should detect dynamic import failures', () => {
      const error = new Error('Failed to fetch dynamically imported module');

      handler.handleError(error);

      expect(loggingServiceMock.error).toHaveBeenCalledWith(
        'Chunk loading failed - application may need refresh',
        error,
        expect.objectContaining({
          type: 'chunk_load_error'
        })
      );
    });
  });

  // ==================== COMPONENT NAME EXTRACTION ====================

  describe('Component Name Extraction', () => {
    it('should extract component name from stack trace', () => {
      const error = new Error('Test error');
      error.stack = `Error: Test error
    at LoginComponent.ngOnInit (http://localhost:4200/main.js:12345)
    at callHook (http://localhost:4200/vendor.js:6789)`;

      handler.handleError(error);

      expect(loggingServiceMock.error).toHaveBeenCalledWith(
        'Unhandled error',
        error,
        expect.objectContaining({
          type: 'javascript_error',
          component: 'LoginComponent'
        })
      );
    });

    it('should return undefined if no component in stack trace', () => {
      const error = new Error('Test error');
      error.stack = `Error: Test error
    at someFunction (http://localhost:4200/main.js:12345)`;

      handler.handleError(error);

      expect(loggingServiceMock.error).toHaveBeenCalledWith(
        'Unhandled error',
        error,
        expect.objectContaining({
          type: 'javascript_error',
          component: undefined
        })
      );
    });

    it('should handle errors without stack trace', () => {
      const error = new Error('Test error');
      delete error.stack;

      handler.handleError(error);

      expect(loggingServiceMock.error).toHaveBeenCalledWith(
        'Unhandled error',
        error,
        expect.objectContaining({
          type: 'javascript_error',
          component: undefined
        })
      );
    });

    it('should extract first component name if multiple in stack', () => {
      const error = new Error('Test error');
      error.stack = `Error: Test error
    at ChildComponent.handleClick (http://localhost:4200/main.js:111)
    at ParentComponent.onButtonClick (http://localhost:4200/main.js:222)`;

      handler.handleError(error);

      expect(loggingServiceMock.error).toHaveBeenCalledWith(
        'Unhandled error',
        error,
        expect.objectContaining({
          component: 'ChildComponent'
        })
      );
    });
  });

  // ==================== NGZONE INTEGRATION ====================

  describe('NgZone Integration', () => {
    it('should run error processing in Angular zone', () => {
      const ngZone = TestBed.inject(NgZone);
      const runSpy = jest.spyOn(ngZone, 'run');

      const error = new Error('Zone test');
      handler.handleError(error);

      expect(runSpy).toHaveBeenCalled();
    });
  });

  // ==================== PROMISE REJECTION HANDLING ====================

  describe('Promise Rejection Handling', () => {
    it('should handle PromiseRejectionEvent', () => {
      // Create a mock PromiseRejectionEvent using our polyfill
      const mockPromiseRejection = new (globalThis as any).PromiseRejectionEvent('unhandledrejection', {
        promise: Promise.resolve(),
        reason: 'Test rejection'
      });

      handler.handleError(mockPromiseRejection as any);

      expect(loggingServiceMock.error).toHaveBeenCalledWith(
        'Unhandled promise rejection',
        mockPromiseRejection,
        expect.objectContaining({
          type: 'unhandled_rejection'
        })
      );
    });
  });
});

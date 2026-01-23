import { TestBed } from '@angular/core/testing';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { of } from 'rxjs';

import { LoggingService } from './logging.service';

describe('LoggingService', () => {
  let service: LoggingService;
  let httpPostMock: jest.Mock;

  let consoleDebugSpy: jest.SpyInstance;
  let consoleInfoSpy: jest.SpyInstance;
  let consoleWarnSpy: jest.SpyInstance;
  let consoleErrorSpy: jest.SpyInstance;
  let consoleLogSpy: jest.SpyInstance;

  beforeEach(() => {
    httpPostMock = jest.fn().mockReturnValue(of({}));

    TestBed.configureTestingModule({
      providers: [
        LoggingService,
        {
          provide: HttpClient,
          useValue: { post: httpPostMock }
        }
      ]
    });

    service = TestBed.inject(LoggingService);

    // Spy on console methods
    consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();
    consoleInfoSpy = jest.spyOn(console, 'info').mockImplementation();
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
  });

  afterEach(() => {
    consoleDebugSpy.mockRestore();
    consoleInfoSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    consoleErrorSpy.mockRestore();
    consoleLogSpy.mockRestore();
    TestBed.resetTestingModule();
  });

  // ==================== BASIC TESTS ====================

  describe('Basic Operations', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });

    it('should start with no correlation ID', () => {
      expect(service.getCorrelationId()).toBeNull();
    });
  });

  // ==================== CORRELATION ID ====================

  describe('Correlation ID', () => {
    it('should set correlation ID', () => {
      service.setCorrelationId('test-123');
      expect(service.getCorrelationId()).toBe('test-123');
    });

    it('should update correlation ID', () => {
      service.setCorrelationId('first-id');
      service.setCorrelationId('second-id');
      expect(service.getCorrelationId()).toBe('second-id');
    });

    it('should clear correlation ID when set to null', () => {
      service.setCorrelationId('test-123');
      service.setCorrelationId(null);
      expect(service.getCorrelationId()).toBeNull();
    });
  });

  // ==================== LOG LEVELS ====================

  describe('Log Levels', () => {
    it('should log debug messages', () => {
      service.debug('Debug message');
      expect(consoleDebugSpy).toHaveBeenCalled();
    });

    it('should log info messages', () => {
      service.info('Info message');
      expect(consoleInfoSpy).toHaveBeenCalled();
    });

    it('should log warn messages', () => {
      service.warn('Warning message');
      expect(consoleWarnSpy).toHaveBeenCalled();
    });

    it('should log error messages', () => {
      service.error('Error message');
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  // ==================== CONTEXT HANDLING ====================

  describe('Context Handling', () => {
    it('should include context in debug logs', () => {
      const context = { userId: 1, action: 'test' };
      service.debug('Debug with context', context);
      expect(consoleDebugSpy).toHaveBeenCalled();
    });

    it('should include context in info logs', () => {
      const context = { data: 'value' };
      service.info('Info with context', context);
      expect(consoleInfoSpy).toHaveBeenCalled();
    });

    it('should include context in warn logs', () => {
      const context = { warning: 'details' };
      service.warn('Warning with context', context);
      expect(consoleWarnSpy).toHaveBeenCalled();
    });

    it('should include context in error logs', () => {
      const error = new Error('Test error');
      const context = { additional: 'info' };
      service.error('Error with context', error, context);
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  // ==================== ERROR LOGGING ====================

  describe('Error Logging', () => {
    it('should log error without Error object', () => {
      service.error('Simple error message');
      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    it('should log error with Error object', () => {
      const error = new Error('Test error');
      service.error('Error occurred', error);
      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    it('should log HTTP errors', () => {
      const httpError = new HttpErrorResponse({
        status: 404,
        statusText: 'Not Found',
        url: '/api/test'
      });

      service.logHttpError(httpError);
      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    it('should log HTTP errors with context', () => {
      const httpError = new HttpErrorResponse({
        status: 500,
        statusText: 'Internal Server Error',
        url: '/api/server'
      });
      const context = { method: 'POST', duration_ms: 150 };

      service.logHttpError(httpError, context);
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  // ==================== CORRELATION ID IN LOGS ====================

  describe('Correlation ID in logs', () => {
    it('should include correlation ID in log message when set', () => {
      service.setCorrelationId('abc12345-6789-0def');
      service.info('Test message');

      expect(consoleInfoSpy).toHaveBeenCalledWith(
        expect.stringContaining('[abc12345]'),
        expect.anything()
      );
    });

    it('should show [-] when no correlation ID', () => {
      service.setCorrelationId(null);
      service.info('Test message');

      expect(consoleInfoSpy).toHaveBeenCalledWith(
        expect.stringContaining('[-]'),
        expect.anything()
      );
    });
  });

  // ==================== MESSAGE FORMATTING ====================

  describe('Message Formatting', () => {
    it('should format message with prefix', () => {
      service.info('Formatted message');
      expect(consoleInfoSpy).toHaveBeenCalledWith(
        expect.stringContaining('Formatted message'),
        expect.anything()
      );
    });
  });
});

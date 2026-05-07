/**
 * Direct API helper for test setup/teardown operations.
 * Uses fetch to call Django REST API directly.
 *
 * The base URL defaults to localhost (host-side execution) but can be
 * overridden via E2E_API_BASE for container-side runs (e.g.
 * `http://web:8000/api`).
 */

const API_BASE = process.env['E2E_API_BASE'] || 'http://localhost:8000/api';

interface LoginResponse {
  access: string;
  refresh: string;
}

export class ApiHelper {
  private token: string | null = null;

  async login(email: string, password: string): Promise<string> {
    const response = await fetch(`${API_BASE}/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: email, password }),
    });

    if (!response.ok) {
      throw new Error(`Login failed for ${email}: ${response.status}`);
    }

    const data: LoginResponse = await response.json();
    this.token = data.access;
    return data.access;
  }

  async get<T = unknown>(path: string): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: this.authHeaders(),
    });
    if (!response.ok) {
      throw new Error(`GET ${path} failed: ${response.status}`);
    }
    return response.json();
  }

  async post<T = unknown>(path: string, body: Record<string, unknown>): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { ...this.authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(`POST ${path} failed: ${response.status}`);
    }
    return response.json();
  }

  async patch<T = unknown>(path: string, body: Record<string, unknown>): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'PATCH',
      headers: { ...this.authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(`PATCH ${path} failed: ${response.status}`);
    }
    return response.json();
  }

  async delete(path: string): Promise<void> {
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'DELETE',
      headers: this.authHeaders(),
    });
    if (!response.ok && response.status !== 404) {
      throw new Error(`DELETE ${path} failed: ${response.status}`);
    }
  }

  private authHeaders(): Record<string, string> {
    if (!this.token) {
      return {};
    }
    return { Authorization: `Bearer ${this.token}` };
  }
}

/**
 * Unified API Client for SIH26237
 * Air-gapped backend communication with session token injection and truthful error mapping.
 */

const TOKEN_STORAGE_KEY = 'sih_auth_token';

export function getStoredToken() {
  return sessionStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token) {
  if (token) {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export function clearStoredToken() {
  sessionStorage.removeItem(TOKEN_STORAGE_KEY);
}

export class ApiError extends Error {
  constructor(status, message, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

const API_BASE = (import.meta.env && import.meta.env.VITE_API_URL) ? import.meta.env.VITE_API_URL.replace(/\/+$/, '') : '';

async function request(endpoint, options = {}) {
  const token = getStoredToken();
  const headers = { ...(options.headers || {}) };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Handle FormData vs JSON
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null;
  }

  // Check content type
  const contentType = response.headers.get('content-type') || '';
  let data = null;

  if (contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else if (contentType.includes('application/pdf') || contentType.includes('application/octet-stream')) {
    if (!response.ok) {
      try {
        const text = await response.text();
        throw new ApiError(response.status, text || `Request failed with status ${response.status}`);
      } catch (e) {
        throw new ApiError(response.status, e.message);
      }
    }
    return response.blob();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}`;
    if (data && typeof data === 'object') {
      if (typeof data.detail === 'string') {
        errorMessage = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMessage = data.detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
      } else if (data.message) {
        errorMessage = data.message;
      }
    } else if (typeof data === 'string' && data.length > 0) {
      errorMessage = data;
    }
    throw new ApiError(response.status, errorMessage, data);
  }

  return data;
}

// Auth API
export const authApi = {
  login: (principalId, passphrase) =>
    request('/api/auth/login', {
      method: 'POST',
      body: { principal_id: principalId, passphrase },
    }),
  logout: () =>
    request('/api/auth/logout', {
      method: 'POST',
    }),
  me: () => request('/api/auth/me', { method: 'GET' }),
};

// Documents API
export const documentsApi = {
  list: () => request('/api/documents', { method: 'GET' }),
  register: (formData) =>
    request('/api/documents/register', {
      method: 'POST',
      body: formData,
    }),
  encrypt: (documentId, recipientIds) =>
    request('/api/documents/encrypt', {
      method: 'POST',
      body: {
        document_id: documentId,
        authorized_recipient_ids: recipientIds,
      },
    }),
};

// Decryption API
export const decryptionApi = {
  decrypt: (documentId, passphrase) =>
    request('/api/decrypt', {
      method: 'POST',
      body: {
        document_id: documentId,
        passphrase: passphrase,
      },
    }),
  downloadDelivery: async (sessionId) => {
    const blob = await request(`/api/sessions/${sessionId}/download`, {
      method: 'GET',
    });
    return blob;
  },
};

// Recipients / Personnel API
export const recipientsApi = {
  list: () => request('/api/recipients', { method: 'GET' }),
  create: (recipientId, name, role) =>
    request('/api/recipients/create', {
      method: 'POST',
      body: { recipient_id: recipientId, name, role },
    }),
  getKeysMe: () => request('/api/keys/me', { method: 'GET' }),
};

// Trust Desk API
export const trustApi = {
  getManifest: () => request('/api/trust/manifest', { method: 'GET' }),
  getAnchor: () => request('/api/trust/anchor', { method: 'GET' }),
  getPending: () => request('/api/trust/pending', { method: 'GET' }),
  attestKey: (principalId, keyId, confirmedSha256) =>
    request('/api/trust/attest', {
      method: 'POST',
      body: {
        principal_id: principalId,
        key_id: keyId,
        confirmed_mldsa_pk_sha256: confirmedSha256,
      },
    }),
  revoke: (principalId, reason) =>
    request('/api/trust/revoke', {
      method: 'POST',
      body: { principal_id: principalId, reason },
    }),
  compromiseKey: (keyId, reason) =>
    request('/api/trust/compromise-key', {
      method: 'POST',
      body: { key_id: keyId, reason },
    }),
};

// Forensics & Investigation API
export const investigationApi = {
  investigate: (formData) =>
    request('/api/investigate', {
      method: 'POST',
      body: formData,
    }),
  listReports: () => request('/api/reports', { method: 'GET' }),
  getReport: (reportId) => request(`/api/reports/${reportId}`, { method: 'GET' }),
  compareInvariance: (sessionA, sessionB) =>
    request('/api/forensics/invariance', {
      method: 'POST',
      body: { session_a: sessionA, session_b: sessionB },
    }),
};

// Ledger & Audit API
export const ledgerApi = {
  getBlocks: () => request('/api/ledger', { method: 'GET' }),
  verify: () => request('/api/ledger/verify', { method: 'GET' }),
  getWitnessStatus: () => request('/api/ledger/witness', { method: 'GET' }),
  tamperTest: (blockIndex, field, newValue) =>
    request('/api/ledger/tamper-test', {
      method: 'POST',
      body: {
        block_index: blockIndex,
        field: field,
        new_value: newValue,
      },
    }),
  reset: () => request('/api/ledger/reset', { method: 'POST' }),
  getAuditTrail: (limit = 100) => request(`/api/audit?limit=${limit}`, { method: 'GET' }),
};

// System Health API
export const systemApi = {
  getHealth: () => request('/api/health', { method: 'GET' }),
  getRoot: () => request('/', { method: 'GET' }),
};

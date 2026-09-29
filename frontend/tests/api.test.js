import { afterEach, beforeEach, test } from 'node:test';
import assert from 'node:assert/strict';
import { authApi, documentsApi, decryptionApi, systemApi, setStoredToken, clearStoredToken } from '../src/services/api.js';

const originalFetch = globalThis.fetch;
beforeEach(() => {
  const storage = new Map();
  globalThis.sessionStorage = {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: (key) => storage.delete(key),
  };
});
afterEach(() => { globalThis.fetch = originalFetch; });

test('static-host HTML is rejected even when the server returns 200', async () => {
  globalThis.fetch = async () => new Response('<!doctype html><div id="root"></div>', {
    headers: { 'Content-Type': 'text/html' },
  });
  await assert.rejects(authApi.login('R001', 'test-only'), /backend is unavailable/);
  await assert.rejects(authApi.me(), /backend is unavailable/);
  await assert.rejects(systemApi.getHealth(), /backend is unavailable/);
});

test('login preserves the backend contract and bearer requests use its token', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/auth/login');
    assert.deepEqual(JSON.parse(options.body), { principal_id: 'R001', passphrase: 'test-only' });
    return Response.json({ token: 'test-token', principal_id: 'R001', role: 'RECIPIENT', name: 'Test' });
  };
  const result = await authApi.login('R001', 'test-only');
  setStoredToken(result.token);
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/auth/me');
    assert.equal(options.headers.Authorization, 'Bearer test-token');
    return Response.json({ principal_id: 'R001', role: 'RECIPIENT' });
  };
  assert.equal((await authApi.me()).principal_id, 'R001');
  clearStoredToken();
});

test('malformed or incomplete login responses never establish an identity', async () => {
  for (const data of [null, {}, { token: 't' }, { principal_id: 'R001', role: 'RECIPIENT' }]) {
    globalThis.fetch = async () => Response.json(data);
    await assert.rejects(authApi.login('R001', 'test-only'), /Authentication was not completed/);
  }
  globalThis.fetch = async () => new Response('{bad json', { headers: { 'Content-Type': 'application/json' } });
  await assert.rejects(authApi.login('R001', 'test-only'), /invalid response/);
});

test('network failures and timeout failures have a readable connection error', async () => {
  globalThis.fetch = async () => { throw new TypeError('fetch failed'); };
  await assert.rejects(systemApi.getHealth(), (error) => error.status === 0 && /backend is unavailable/.test(error.message));
});

test('multipart uploads retain browser-generated boundaries', async () => {
  const upload = new FormData();
  upload.append('file', new Blob(['test pdf'], { type: 'application/pdf' }), 'test.pdf');
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/documents/register');
    assert.equal(options.body, upload);
    assert.equal(options.headers['Content-Type'], undefined);
    return Response.json({ document_id: 'DOC-TEST' });
  };
  assert.equal((await documentsApi.register(upload)).document_id, 'DOC-TEST');
});

test('step-up passphrase is sent and PDF downloads remain blobs', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/decrypt');
    assert.deepEqual(JSON.parse(options.body), { document_id: 'DOC-TEST', passphrase: 'step-up-test' });
    return Response.json({ session_id: 'SESSION-TEST' });
  };
  await decryptionApi.decrypt('DOC-TEST', 'step-up-test');
  globalThis.fetch = async () => new Response('%PDF-1.7', { headers: { 'Content-Type': 'application/pdf' } });
  assert.equal(await (await decryptionApi.downloadDelivery('SESSION-TEST')).text(), '%PDF-1.7');
});

test('backend authorization and validation errors remain failures', async () => {
  for (const [status, detail, expected] of [[403, 'Not authorized', 'Not authorized'], [422, [{ msg: 'Field required' }], 'Field required']]) {
    globalThis.fetch = async () => Response.json({ detail }, { status });
    await assert.rejects(documentsApi.list(), (error) => error.status === status && error.message === expected);
  }
});

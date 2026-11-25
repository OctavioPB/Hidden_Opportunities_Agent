/**
 * Fake backend for UI tests: replaces `fetch` and answers from fixtures.json
 * (trimmed responses captured from the FastAPI app on synthetic demo data).
 */
import { vi } from 'vitest'
import fixtures from './fixtures.json'

export interface Call { method: string; path: string; query: string; body: unknown }

type Reply = { status: number; body: unknown }

const data = fixtures as unknown as Record<string, unknown>

const PATTERNS: [RegExp, string][] = [
  [/^\/clients\/[^/]+\/detail$/, '/clients/:id/detail'],
  [/^\/text-signals\/client\/[^/]+$/, '/text-signals/client/:id'],
  [/^\/negotiations\/[^/]+\/thread$/, '/negotiations/:id/thread'],
]

const isReply = (v: unknown): v is Reply =>
  typeof v === 'object' && v !== null && 'body' in v && 'status' in v && typeof v.status === 'number'

/**
 * `overrides` is keyed by "METHOD /path" (or just "/path" for GET). A value is
 * the JSON body, or { status, body } to simulate an error.
 * Returns the list of requests the UI made.
 */
export function mockApi(overrides: Record<string, unknown> = {}): Call[] {
  const calls: Call[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: string, init?: RequestInit) => {
    const url = new URL(input, 'http://test')
    const path = url.pathname.replace(/^\/api/, '')
    const method = init?.method ?? 'GET'
    calls.push({ method, path, query: url.search, body: init?.body ? JSON.parse(String(init.body)) : null })

    const key = PATTERNS.find(([re]) => re.test(path))?.[1] ?? path
    let found = overrides[`${method} ${path}`] ?? overrides[`${method} ${key}`]
    if (found === undefined && method === 'GET') found = overrides[path] ?? data[path] ?? data[key]
    if (found === undefined && method !== 'GET') found = {}

    const reply: Reply = found === undefined
      ? { status: 404, body: { detail: 'Not mocked' } }
      : isReply(found) ? found : { status: 200, body: found }
    return { ok: reply.status < 400, status: reply.status, json: async () => structuredClone(reply.body) } as Response
  }))
  return calls
}

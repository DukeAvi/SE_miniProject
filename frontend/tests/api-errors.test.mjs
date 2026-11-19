import assert from "node:assert/strict";
import test from "node:test";
import { ApiError, friendlyError, loginError, refreshCsrfToken } from "../lib/api.ts";

test("invalid credentials show the server message on sign-in", () => {
  const error = new ApiError(401, { error: { message: "Email or password is incorrect." } });
  assert.equal(loginError(error), "Email or password is incorrect.");
  assert.equal(friendlyError(error), "Your session has ended. Sign in again to continue.");
});

test("sign-in still displays other validation and network errors", () => {
  const invalid = new ApiError(400, { error: { details: { email: ["Enter a valid email."] } } });
  assert.equal(loginError(invalid), "Enter a valid email.");
  assert.equal(loginError(new Error("Network unavailable")), "Network unavailable");
});

test("unavailable API and invalid responses show actionable session errors", async (t) => {
  const fetchMock = t.mock.method(globalThis, "fetch", async () => new Response("Internal Server Error", { status: 500 }));
  await assert.rejects(refreshCsrfToken(), /Check that the API is running/);
  fetchMock.mock.mockImplementation(async () => new Response("not JSON", { status: 200 }));
  await assert.rejects(refreshCsrfToken(), /Check that the API is running/);
  fetchMock.mock.mockImplementation(async () => { throw new Error("network error"); });
  await assert.rejects(refreshCsrfToken(), /Could not reach the server/);
});

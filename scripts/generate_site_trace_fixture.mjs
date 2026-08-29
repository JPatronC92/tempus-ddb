import { createHash, generateKeyPairSync, sign } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const outputPath = resolve(process.argv[2] ?? "site/data/demo-trace.json");

function canonicalize(value) {
  if (value === null || typeof value === "boolean" || typeof value === "number") return JSON.stringify(value);
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(",")}]`;
  if (typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalize(value[key])}`).join(",")}}`;
  throw new TypeError(`Unsupported value in canonical JSON: ${typeof value}`);
}

function digest(value) {
  return createHash("sha256").update(value).digest("hex");
}

function publicKeyHex(key) {
  const encoded = key.export({ format: "der", type: "spki" });
  const prefix = "302a300506032b6570032100";
  if (!encoded.subarray(0, 12).equals(Buffer.from(prefix, "hex"))) throw new Error("Unexpected Ed25519 public-key encoding");
  return encoded.subarray(-32).toString("hex");
}

function signCanonical(privateKey, value) {
  return sign(null, Buffer.from(canonicalize(value)), privateKey).toString("hex");
}

function signDigest(privateKey, hex) {
  return sign(null, Buffer.from(hex, "hex"), privateKey).toString("hex");
}

const gate = generateKeyPairSync("ed25519");
const agent = generateKeyPairSync("ed25519");
const executor = generateKeyPairSync("ed25519");
const gateId = publicKeyHex(gate.publicKey);
const agentId = publicKeyHex(agent.publicKey);
const executorId = publicKeyHex(executor.publicKey);
const actionId = digest("tempus-site-demo-action-v1");

const intent = {
  schema_version: "tempus.action-intent.v1",
  tenant_id: "example-org",
  agent_id: agentId,
  idempotency_key: "site-demo-action-001",
  action_type: "github.create_issue",
  resource: "example-org/agent-sandbox",
  requested_at: 1787040000000000,
  input: { title: "Document the executor boundary", labels: ["security", "demo"] },
  money: null,
};
const intentHash = digest(canonicalize(intent));
const agentSignature = signCanonical(agent.privateKey, intent);

const authorizationBody = {
  schema_version: "tempus.authorization-receipt.v1",
  action_id: actionId,
  tenant_id: intent.tenant_id,
  agent_id: agentId,
  executor_id: executorId,
  gate_id: gateId,
  decision: "ALLOWED",
  policy_version: "tempus.policy-bundle.v1",
  policy_digest: digest("tempus-site-demo-policy-v1"),
  intent_hash: intentHash,
  reason_codes: ["IDENTITY_VERIFIED", "POLICY_ALLOWED"],
  issued_at: 1787040000000000,
  expires_at: 1787040060000000,
};
const authorizationId = digest(canonicalize(authorizationBody));
const authorization = {
  ...authorizationBody,
  authorization_id: authorizationId,
  gate_signature: signDigest(gate.privateKey, authorizationId),
};

const outcomeBody = {
  schema_version: "tempus.action-outcome.v1",
  authorization_id: authorizationId,
  action_id: actionId,
  executor_id: executorId,
  status: "SUCCEEDED",
  external_reference: "demo-issue-042",
  output: { issue_number: 42, repository: "example-org/agent-sandbox" },
};
const outcome = { ...outcomeBody, executor_signature: signCanonical(executor.privateKey, outcomeBody) };
const receiptBody = {
  schema_version: "tempus.execution-receipt.v1",
  authorization_id: authorizationId,
  action_id: actionId,
  intent_hash: intentHash,
  outcome_hash: digest(canonicalize(outcomeBody)),
  gate_id: gateId,
  executor_id: executorId,
  status: "SUCCEEDED",
  completed_at: 1787040012000000,
};
const receiptId = digest(canonicalize(receiptBody));
const receipt = { ...receiptBody, receipt_id: receiptId, gate_signature: signDigest(gate.privateKey, receiptId) };

const trace = {
  schema_version: "tempus.site-demo-trace.v1",
  fixture_kind: "synthetic-browser-demo",
  action_id: actionId,
  intent,
  agent_signature: agentSignature,
  authorization,
  execution: { outcome, receipt },
};

await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(trace, null, 2)}\n`, "utf8");

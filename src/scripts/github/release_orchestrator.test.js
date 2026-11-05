"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const orchestrator = require("./release_orchestrator");

const repositoryFullName = "dsocial118/SISOC";

function pull(overrides = {}) {
  return {
    base: { ref: "main" },
    head: { ref: "homologacion", repo: { full_name: repositoryFullName } },
    body: [
      "<!-- release-automation: scheduled -->",
      "<!-- release-date: 2026-07-29 -->",
      "<!-- release-head: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->",
      "<!-- release-preparation: none -->",
    ].join("\n"),
    ...overrides,
  };
}

test("reconoce un PR final programado y deriva su tag estable", () => {
  const finalPull = pull({
    head: {
      ref: "homologacion",
      sha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      repo: { full_name: repositoryFullName },
    },
  });

  assert.equal(
    orchestrator.isScheduledFinalPullRequest(finalPull, repositoryFullName),
    true,
  );
  assert.equal(orchestrator.parseReleaseDate(finalPull.body), "2026-07-29");
  assert.equal(
    orchestrator.parseReleaseHead(finalPull.body),
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  );
  assert.equal(orchestrator.isReleaseSnapshotCurrent(finalPull), true);
  assert.equal(orchestrator.stableTagName("2026-07-29"), "2026.07.29-stable");
});

test("rechaza PRs finales que no tienen fecha de release valida", () => {
  const invalid = pull({ body: "<!-- release-automation: scheduled -->\n<!-- release-date: 2026-02-31 -->\n<!-- release-head: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->" });

  assert.equal(orchestrator.parseReleaseDate(invalid.body), null);
  assert.equal(
    orchestrator.isScheduledFinalPullRequest(invalid, repositoryFullName),
    false,
  );
});

test("rechaza un PR final sin el SHA exacto del snapshot", () => {
  const missingHead = pull({
    body: "<!-- release-automation: scheduled -->\n<!-- release-date: 2026-07-29 -->",
  });

  assert.equal(
    orchestrator.isScheduledFinalPullRequest(missingHead, repositoryFullName),
    false,
  );
});

test("acepta los estados controlados de preparación", () => {
  assert.equal(orchestrator.parseReleasePreparation("<!-- release-preparation: pending -->"), "pending");
  assert.equal(orchestrator.parseReleasePreparation("<!-- release-preparation: none -->"), "none");
  assert.equal(orchestrator.parseReleasePreparation("<!-- release-preparation: 2140 -->"), 2140);
});

test("detecta cuando homologacion avanzó después del snapshot", () => {
  const stale = pull({
    head: {
      ref: "homologacion",
      sha: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      repo: { full_name: repositoryFullName },
    },
  });

  assert.equal(orchestrator.isReleaseSnapshotCurrent(stale), false);
});

test("solo habilita preparaciones internas con el prefijo controlado", () => {
  const preparation = pull({
    base: { ref: "homologacion" },
    head: {
      ref: "codex/predeploy-dev-main-20260729",
      repo: { full_name: repositoryFullName },
    },
    body: "<!-- release-final-pr: 2140 -->",
  });

  assert.equal(orchestrator.parsePreparationFinalNumber(preparation.body), 2140);
  assert.equal(
    orchestrator.isPreparationPullRequest(preparation, repositoryFullName),
    true,
  );
  assert.equal(
    orchestrator.isPreparationPullRequest(
      pull({
        base: { ref: "homologacion" },
        head: { ref: "feature/unsafe", repo: { full_name: repositoryFullName } },
        body: "<!-- release-final-pr: 2140 -->",
      }),
      repositoryFullName,
    ),
    false,
  );
});

test("clasifica checks faltantes, pendientes y fallidos", () => {
  const checks = [
    { name: "deploy_guard", status: "completed", conclusion: "success" },
    { name: "architecture_imports", status: "in_progress", conclusion: null },
    { name: "gitleaks", status: "completed", conclusion: "success" },
    { name: "sync_pr_artifacts", status: "completed", conclusion: "failure" },
  ];

  assert.deepEqual(orchestrator.requiredChecksState(checks), {
    pending: ["architecture_imports"],
    failed: ["sync_pr_artifacts (failure)"],
  });
});

test("ya no promueve desde development ni prepara sobre development", () => {
  const legacyFinal = pull({
    head: {
      ref: "development",
      sha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      repo: { full_name: repositoryFullName },
    },
  });
  const legacyPreparation = pull({
    base: { ref: "development" },
    head: {
      ref: "codex/predeploy-dev-main-20260729",
      repo: { full_name: repositoryFullName },
    },
    body: "<!-- release-final-pr: 2140 -->",
  });

  assert.equal(
    orchestrator.isScheduledFinalPullRequest(legacyFinal, repositoryFullName),
    false,
  );
  assert.equal(
    orchestrator.isPreparationPullRequest(legacyPreparation, repositoryFullName),
    false,
  );
});

test("la secuencia es opcional y conserva el primer tag", () => {
  assert.equal(orchestrator.parseReleaseSequence(pull().body), 1);
  assert.equal(orchestrator.parseReleaseSequence("<!-- release-sequence: 1 -->"), 1);
  assert.equal(orchestrator.parseReleaseSequence("<!-- release-sequence: 2 -->"), 2);
  assert.equal(orchestrator.stableTagName("2026-11-05", 1), "2026.11.05-stable");
  assert.equal(orchestrator.stableTagName("2026-11-05", 2), "2026.11.05-2-stable");
});

function scenario(sequence = "2", options = {}) {
  const calls = [];
  const checks = orchestrator.REQUIRED_CHECKS.map(name => ({
    name, status: "completed", conclusion: "success",
  }));
  const tags = new Map([["2026.07.29-stable", "old-main"]]);
  const releases = new Map();
  const tagObjects = new Map();
  const current = pull({
    number: 34, node_id: "PR_34", draft: false,
    base: { ref: "main", sha: "current-main" },
    head: { ...pull().head, sha: "a".repeat(40) },
    body: pull().body + (sequence === null ? "" : `\n<!-- release-sequence: ${sequence} -->`),
  });
  let main = current.base.sha;
  const missing = () => { throw Object.assign(new Error("Not found"), { status: 404 }); };
  const write = (name, args) => calls.push({ ...args, name });
  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: structuredClone(current) }),
        list: async () => ({ data: [structuredClone(current)] }),
      },
      checks: {
        listForRef: async () => ({ data: { check_runs: structuredClone(checks) } }),
        create: async args => {
          write("check.create", args);
          const check = { ...args, id: checks.length + 1 };
          checks.push(check);
          return { data: structuredClone(check) };
        },
        update: async args => {
          write("check.update", args);
          const check = checks.find(item => item.id === args.check_run_id);
          Object.assign(check, args);
          return { data: structuredClone(check) };
        },
      },
      repos: {
        compareCommits: async () => ({ data: { behind_by: 0 } }),
        getBranch: async () => ({ data: { commit: { sha: main } } }),
        getReleaseByTag: async ({ tag }) => releases.has(tag)
          ? { data: releases.get(tag) } : missing(),
        createRelease: async args => {
          write("release.create", args);
          const release = { html_url: `https://example.test/releases/${args.tag_name}` };
          releases.set(args.tag_name, release);
          if (options.race === "late-sequence") current.body = current.body.replace("sequence: 2", "sequence: 3");
          return { data: release };
        },
      },
      git: {
        getRef: async ({ ref }) => tags.has(ref.slice(5))
          ? { data: { object: { type: "commit", sha: tags.get(ref.slice(5)) } } } : missing(),
        createTag: async args => {
          write("tag.create", args);
          const sha = `tag-${tagObjects.size}`;
          tagObjects.set(sha, args.object);
          return { data: { sha } };
        },
        createRef: async args => {
          write("ref.create", args);
          tags.set(args.ref.slice(10), tagObjects.get(args.sha));
          if (options.race === "sequence") current.body = current.body.replace("sequence: 2", "sequence: 3");
          if (options.race === "main") main = "new-main";
          if (options.race === "head") current.head.sha = "b".repeat(40);
          return { data: {} };
        },
        deleteRef: async args => { write("ref.delete", args); tags.delete(args.ref.slice(5)); },
      },
      issues: {
        listComments: async () => ({ data: [] }),
        createComment: async args => { write("comment", args); return { data: {} }; },
      },
    },
    graphql: async query => { write("graphql", { query }); return {}; },
  };
  const context = { repo: { owner: "dsocial118", repo: "SISOC" }, eventName: "schedule", payload: {} };
  const core = { info() {}, warning() {} };
  return { calls, tags, checks, current, releases, context, run: () => orchestrator.run({ github, context, core }) };
}

for (const value of ["", "0", "-1", "1.5", "NaN", "9007199254740992", "2 -->\n<!-- release-sequence: 3", "2 --"]) {
  test(`secuencia explícita inválida ${JSON.stringify(value)} no escribe ni arma`, async () => {
    const state = scenario(value);
    assert.equal(orchestrator.isScheduledFinalPullRequest(state.current, repositoryFullName), false);
    await state.run();
    assert.deepEqual(state.calls, []);
  });
}

for (const sequence of [null, "1"]) {
  test(`primera promoción ${sequence ?? "sin marker"} conserva creación y formato`, async () => {
    const state = scenario(sequence);
    state.tags.clear();
    await state.run();
    assert.equal(state.tags.get("2026.07.29-stable"), "current-main");
    assert.equal(state.tags.size, 1);
    assert.equal(state.calls.filter(call => call.name === "tag.create").length, 1);
    assert.ok(state.calls.some(call => call.name === "check.update" && call.conclusion === "success"));
  });
}

test("segunda promoción conserva el primer tag, es idempotente y reporta el tag exacto", async () => {
  const state = scenario();
  await state.run();
  assert.equal(state.tags.get("2026.07.29-stable"), "old-main");
  assert.equal(state.tags.get("2026.07.29-2-stable"), "current-main");
  assert.equal(state.calls.filter(call => call.name === "tag.create").length, 1);
  assert.ok(state.calls.some(call => call.name === "check.update" && call.conclusion === "success"));
  await state.run();
  assert.equal(state.calls.filter(call => call.name === "tag.create").length, 1);
  state.context.eventName = "pull_request";
  state.context.payload.pull_request = { ...state.current, merged: true, merge_commit_sha: "merged" };
  await state.run();
  assert.match(state.calls.find(call => call.name === "comment").body, /2026\.07\.29-2-stable/);
});

test("tag existente con distinto baseline sigue rechazándose", async () => {
  const state = scenario();
  state.tags.set("2026.07.29-2-stable", "wrong-main");
  await assert.rejects(state.run(), /ya apunta/);
  assert.equal(state.tags.get("2026.07.29-2-stable"), "wrong-main");
  assert.equal(state.calls.some(call => call.name === "ref.delete"), false);
  assert.equal(state.calls.some(call => call.conclusion === "success"), false);
});

for (const race of ["sequence", "main", "head"]) {
  test(`cambio de ${race} durante creación nunca aprueba baseline`, async () => {
    const state = scenario("2", { race });
    await state.run();
    assert.equal(state.calls.some(call => call.conclusion === "success"), false);
    assert.equal(state.calls.some(call => call.name === "release.create"), false);
    assert.equal(state.tags.has("2026.07.29-2-stable"), false);
    assert.equal(state.tags.get("2026.07.29-stable"), "old-main");
  });
}

test("cambiar secuencia no reutiliza el check exitoso del mismo head y base", async () => {
  const state = scenario();
  await state.run();
  state.current.body = state.current.body.replace("sequence: 2", "sequence: 3");
  await state.run();
  const creates = state.calls.filter(call => call.name === "check.create");
  assert.equal(creates.length, 2);
  assert.notEqual(creates[0].external_id, creates[1].external_id);
  assert.equal(state.tags.get("2026.07.29-3-stable"), "current-main");
});

test("una rama directa a main sigue sin poder emitir baseline", async () => {
  const state = scenario();
  state.current.head.ref = "feat/direct-main";
  await state.run();
  assert.deepEqual(state.calls, []);
});

test("editar secuencia durante publicación del release no aprueba ni habilita auto-merge", async () => {
  const state = scenario("2", { race: "late-sequence" });
  await state.run();
  assert.equal(orchestrator.parseReleaseSequence(state.current.body), 3);
  assert.equal(state.calls.some(call => call.conclusion === "success"), false);
  assert.equal(state.calls.some(call => call.name === "graphql" && call.query.includes("EnableAutoMerge")), false);
  assert.equal(state.tags.get("2026.07.29-stable"), "old-main");
  assert.equal(state.tags.get("2026.07.29-2-stable"), "current-main");
  assert.equal(state.calls.some(call => call.name === "ref.delete"), false);
});

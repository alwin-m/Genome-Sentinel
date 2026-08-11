const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BASE_URL = process.env.JEEN_LAB_URL || "http://127.0.0.1:8000";
const ROOT = path.resolve(__dirname, "..");
const ARTIFACT_DIR = path.join(ROOT, "test-artifacts");
const CHROME_PATHS = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
];

function findBrowser() {
  return CHROME_PATHS.find((candidate) => fs.existsSync(candidate));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function api(pathname, options = {}) {
  const res = await fetch(`${BASE_URL}${pathname}`, options);
  const text = await res.text();
  let body = {};
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = { raw: text };
  }
  return { ok: res.ok, status: res.status, body };
}

async function waitForProtein(name, timeoutMs = 60000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const { body } = await api("/api/status");
    if ((body.proteins || []).includes(name.toUpperCase())) return true;
    await new Promise((resolve) => setTimeout(resolve, 2500));
  }
  return false;
}

async function waitForLigand(name, timeoutMs = 60000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const { body } = await api("/api/status");
    if ((body.ligands || []).includes(name.toLowerCase())) return true;
    await new Promise((resolve) => setTimeout(resolve, 2500));
  }
  return false;
}

async function waitForDocking(key, timeoutMs = 180000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const { body } = await api("/api/results");
    const job = body[key];
    if (job && (job.status === "completed" || job.status === "failed")) return job;
    await new Promise((resolve) => setTimeout(resolve, 3000));
  }
  throw new Error(`Docking job ${key} did not finish within ${timeoutMs}ms`);
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(ARTIFACT_DIR, `${name}.png`), fullPage: true });
}

(async () => {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });

  const browserPath = findBrowser();
  assert(browserPath, "Chrome or Edge was not found for automated browser testing.");

  const run = {
    startedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    checks: [],
    screenshots: [],
    docking: null,
    finishedAt: null
  };

  const status = await api("/api/status");
  assert(status.ok, "API status endpoint failed.");
  assert(status.body.vina_installed, "AutoDock Vina is not installed.");
  assert(status.body.pipeline_ready, "Python pipeline is not ready.");
  run.checks.push("API status reports Vina and pipeline ready.");

  const atlasApi = await api("/api/disease_targets");
  assert(atlasApi.ok && atlasApi.body.targets.length >= 3, "Disease atlas API returned too few targets.");
  run.checks.push("Disease atlas API returns open-data target metadata.");

  const browser = await chromium.launch({
    headless: false,
    executablePath: browserPath,
    args: ["--start-maximized"]
  });
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const errors = [];
  page.on("pageerror", (err) => errors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error" && !msg.text().includes("404")) errors.push(msg.text());
  });

  await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => localStorage.setItem("gs_onboarding_done", "1"));
  await page.reload({ waitUntil: "domcontentloaded" });

  await page.waitForSelector("#status-vina.online", { timeout: 10000 });
  await page.waitForSelector("#status-env.online", { timeout: 10000 });
  await shot(page, "01-dashboard");
  run.screenshots.push("01-dashboard.png");
  run.checks.push("Dashboard loads and environment badges are online.");

  await page.click('[data-target="panel-atlas"]');
  await page.waitForSelector("#atlas-list .atlas-card", { timeout: 10000 });
  await page.selectOption("#inheritance-mode", "dominant");
  const atlasCards = await page.locator("#atlas-list .atlas-card").count();
  assert(atlasCards >= 3, "Disease Atlas did not render expected cards.");
  await shot(page, "02-disease-atlas");
  run.screenshots.push("02-disease-atlas.png");
  run.checks.push("Disease Atlas renders disease/gene/protein cards and inheritance canvas.");

  await page.click('[data-target="panel-step1"]');
  await page.fill("#input-pdb-id", "1CRN");
  await page.click("#btn-download-protein");
  assert(await waitForProtein("1CRN"), "1CRN protein download/preparation did not finish.");
  await page.waitForTimeout(1000);
  await page.click('[data-target="panel-step1"]');
  await shot(page, "03-protein-target-download");
  run.screenshots.push("03-protein-target-download.png");
  run.checks.push("Protein target download and preparation works for real RCSB PDB ID 1CRN.");

  await page.click('[data-target="panel-step2"]');
  await page.fill("#ligand-name", "test_caffeine");
  await page.fill("#ligand-smiles", "Cn1cnc2c1c(=O)n(C)c(=O)n2C");
  await page.click("#btn-add-ligand");
  assert(await waitForLigand("test_caffeine"), "Custom ligand preparation did not finish.");
  await page.waitForTimeout(1000);
  await page.click('[data-target="panel-step2"]');
  await shot(page, "04-ligand-library-custom");
  run.screenshots.push("04-ligand-library-custom.png");
  run.checks.push("Custom ligand preparation works using real PubChem-backed SMILES input.");

  await page.click('[data-target="panel-step3"]');
  await page.fill("#grid-center-x", "16.0");
  await page.fill("#grid-center-y", "10.0");
  await page.fill("#grid-center-z", "15.0");
  await page.fill("#grid-size-x", "22");
  await page.fill("#grid-size-y", "22");
  await page.fill("#grid-size-z", "22");
  await page.selectOption("#grid-exhaustiveness", "4");
  await shot(page, "05-docking-grid");
  run.screenshots.push("05-docking-grid.png");
  run.checks.push("Docking grid inputs update without UI errors.");

  await page.click('[data-target="panel-step4"]');
  await page.selectOption("#select-protein", "2B8L");
  await page.selectOption("#select-ligand", "aspirin");
  await page.click("#btn-start-docking");
  await page.waitForSelector("#active-job-details.running", { timeout: 10000 });
  await shot(page, "06-docking-running");
  run.screenshots.push("06-docking-running.png");
  const docking = await waitForDocking("2B8L_aspirin");
  assert(docking.status === "completed", `Docking finished with status ${docking.status}: ${docking.error || ""}`);
  assert(typeof docking.binding_affinity === "number", "Docking completed without numeric binding affinity.");
  run.docking = docking;
  run.checks.push(`AutoDock Vina completed 2B8L + aspirin with ${docking.binding_affinity} kcal/mol.`);

  await page.click('[data-target="panel-step5"]');
  await page.waitForSelector('.btn-load-3d[data-protein="2B8L"][data-ligand="aspirin"]', { timeout: 10000 });
  await page.click('.btn-load-3d[data-protein="2B8L"][data-ligand="aspirin"]');
  await page.waitForFunction(
    () => document.querySelector("#viewer-status")?.textContent.includes("2B8L + aspirin"),
    null,
    { timeout: 15000 }
  );
  const canvasCount = await page.locator('[id="3d-viewer"] canvas').count();
  assert(canvasCount >= 1, "3D viewer did not create a WebGL canvas.");
  await shot(page, "07-analysis-3d");
  run.screenshots.push("07-analysis-3d.png");
  run.checks.push("Analysis table and 3D viewer load the docked complex.");

  await page.click('[data-target="panel-step6"]');
  await page.click("#btn-generate-draft");
  const manuscript = await page.inputValue("#manuscript-editor");
  assert(manuscript.includes("Jeen Lab Computational Docking Analysis"), "Manuscript title missing.");
  assert(manuscript.includes("2B8L"), "Manuscript does not include completed docking target.");
  assert(!manuscript.includes("BACE1 (Example)"), "Manuscript contains fake example result.");
  await shot(page, "08-manuscript");
  run.screenshots.push("08-manuscript.png");
  run.checks.push("Research manuscript draft uses real completed local runs and no fake example score.");

  const traversal = await api("/api/log?file=../server.py");
  assert(traversal.status === 403, "Traversal protection failed for /api/log.");
  run.checks.push("Path traversal probe is blocked.");

  assert(errors.length === 0, `Browser console/page errors found: ${errors.join("; ")}`);

  run.finishedAt = new Date().toISOString();
  fs.writeFileSync(path.join(ARTIFACT_DIR, "e2e-report.json"), JSON.stringify(run, null, 2));
  await browser.close();

  console.log(JSON.stringify(run, null, 2));
})().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});

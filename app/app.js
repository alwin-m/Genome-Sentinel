const GenomeSentinel = {
    state: {
        vinaInstalled: false,
        rdkitInstalled: false,
        meekoInstalled: false,
        pipelineReady: false,
        proteins: [],
        ligands: [],
        results: {},
        selectedPreset: null,
        activeTab: "panel-dashboard",
        currentJob: null,
        viewer3D: null,
        currentComplex: null,
        surfaceVisible: false,
        diseaseTargets: [],
        stepStatus: [true, false, false, false, false, false, false]
    },

    presets: {
        "2B8L": { name: "BACE1", disease: "Alzheimer's", x: 16.0, y: 10.0, z: 15.0, size: 22, desc: "Beta-secretase 1" },
        "1LD3": { name: "PfDHFR", disease: "Malaria", x: 32.5, y: 14.8, z: -3.2, size: 22, desc: "P. falciparum DHFR" },
        "2OQV": { name: "DPP4", disease: "Diabetes", x: 40.1, y: 38.5, z: 50.3, size: 22, desc: "Dipeptidyl peptidase 4" },
        "3PP0": { name: "HER2", disease: "Breast Cancer", x: 14.8, y: 17.5, z: 94.6, size: 22, desc: "HER2 receptor kinase" }
    },

    ligandPresets: [
        { name: "donepezil", smiles: "COC1=C(C=C2C(=C1)CC(C2=O)CC3CCN(CC3)CC4=CC=CC=C4)OC", context: "Alzheimer's (BACE1 inhibitor)" },
        { name: "chloroquine", smiles: "CCN(CC)CCCC(C)NC1=C2C=CC(=CC2=NC=C1)Cl", context: "Malaria (PfDHFR candidate)" },
        { name: "metformin", smiles: "CN(C)C(=N)N=C(N)N", context: "Diabetes (DPP-4 related pathway)" },
        { name: "lapatinib", smiles: "CS(=O)(=O)CCNCC1=CC=C(O1)C2=CC3=C(C=C2)N=CN=C3NC4=CC(=C(C=C4)OCC5=CC(=CC=C5)F)Cl", context: "Breast Cancer (HER2 inhibitor)" },
        { name: "aspirin", smiles: "CC(=O)OC1=CC=CC=C1C(=O)O", context: "Control ligand (Common anti-inflammatory)" },
        { name: "acetaminophen", smiles: "CC(=O)NC1=CC=C(O)C=C1", context: "Control ligand (Common analgesic)" },
        { name: "ibuprofen", smiles: "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", context: "Control ligand (Common NSAID)" }
    ],

    init() {
        this.bindNavigation();
        this.bindEvents();
        this.updateGridSummary();
        this.checkStatus();
        this.loadDiseaseAtlas();
        this.renderInheritance();
        this.fetchResults().then(d => this.updateResultsTable(d));
        this.handleOnboarding();
    },

    escapeHTML(value) {
        return String(value ?? "").replace(/[&<>"']/g, char => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        }[char]));
    },

    handleOnboarding() {
        const overlay = document.getElementById("onboarding-overlay");
        if (!localStorage.getItem("gs_onboarding_done")) {
            overlay.classList.remove("hidden");
        } else {
            overlay.classList.add("hidden");
        }
    },

    startTour() {
        document.getElementById("onboarding-overlay").classList.add("hidden");
        if (document.getElementById("onboarding-dont-show").checked) {
            localStorage.setItem("gs_onboarding_done", "1");
        }
    },

    // NAVIGATION
    bindNavigation() {
        document.querySelectorAll(".nav-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const target = btn.getAttribute("data-target");
                document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                document.querySelectorAll(".panel-section").forEach(p => p.classList.remove("active"));
                document.getElementById(target).classList.add("active");
                this.state.activeTab = target;
                this.updateHeader(target);
                this.updateStepProgress(target);
                if (target === "panel-step5") {
                    setTimeout(() => this.init3DViewer(), 100);
                }
            });
        });
    },

    updateHeader(tabId) {
        const titles = {
            "panel-dashboard": { title: "Dashboard", sub: "Overview of your drug discovery environment and local library." },
            "panel-atlas": { title: "Disease Atlas", sub: "Open-data disease targets, AlphaFold models, and inheritance visualization." },
            "panel-step1": { title: "1. Protein Target Selection", sub: "Choose or download a target protein structure for docking." },
            "panel-step2": { title: "2. Ligand Library Preparation", sub: "Generate 3D molecular structures from SMILES notation." },
            "panel-step3": { title: "3. Docking Grid Configuration", sub: "Define the search box around the protein active site." },
            "panel-step4": { title: "4. Run Docking Screen", sub: "Execute AutoDock Vina molecular docking simulations." },
            "panel-step5": { title: "5. Analysis & 3D Visualization", sub: "Review binding scores and visualize docked complexes." },
            "panel-step6": { title: "6. Research Manuscript Draft", sub: "Compile results into a formatted academic paper." }
        };
        const h = titles[tabId] || { title: "Dashboard", sub: "" };
        document.getElementById("panel-title").innerText = h.title;
        document.getElementById("panel-subtitle").innerText = h.sub;
    },

    updateStepProgress(tabId) {
        const stepMap = {
            "panel-dashboard": 0,
            "panel-atlas": 0,
            "panel-step1": 1,
            "panel-step2": 2,
            "panel-step3": 3,
            "panel-step4": 4,
            "panel-step5": 5,
            "panel-step6": 6
        };
        const currentStep = stepMap[tabId] || 0;
        const items = document.querySelectorAll(".step-progress-item");
        const connectors = document.querySelectorAll(".step-progress-connector");
        items.forEach((el, i) => {
            el.classList.remove("active", "completed");
            if (i < currentStep) {
                el.classList.add("completed");
                if (connectors[i - 1]) connectors[i - 1].classList.add("done");
            } else if (i === currentStep) {
                el.classList.add("active");
            }
            if (i >= currentStep && connectors[i - 1]) {
                connectors[i - 1].classList.remove("done");
            }
        });
        if (currentStep > 0 && connectors[currentStep - 1]) {
            connectors[currentStep - 1].classList.add("done");
        }
    },

    // 3D VIEWER
    init3DViewer() {
        const el = document.getElementById("3d-viewer");
        if (el && !this.state.viewer3D) {
            this.state.viewer3D = $3Dmol.createViewer(el, { backgroundColor: "#161b2b" });
            document.getElementById("viewer-empty-state").classList.remove("hidden");
        }
    },

    resetView() {
        const viewer = this.state.viewer3D;
        if (!viewer) return;
        const c = this.state.currentComplex;
        if (c && c.ligModel) {
            viewer.zoomTo({ model: c.ligModel });
        } else if (c && c.recModel) {
            viewer.zoomTo({ model: c.recModel });
        } else {
            viewer.zoomTo();
        }
        viewer.render();
    },

    toggleSurface() {
        const viewer = this.state.viewer3D;
        if (!viewer || !this.state.currentComplex) return;
        this.state.surfaceVisible = !this.state.surfaceVisible;
        if (this.state.surfaceVisible) {
            viewer.addSurface($3Dmol.SurfaceType.VDW, {
                opacity: 0.6,
                color: "spectrum",
                model: this.state.currentComplex.recModel
            }, { model: this.state.currentComplex.recModel });
        } else {
            viewer.removeAllSurfaces();
        }
        viewer.render();
    },

    // API: Status
    async checkStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();
            this.state.vinaInstalled = data.vina_installed;
            this.state.rdkitInstalled = data.rdkit_installed;
            this.state.meekoInstalled = data.meeko_installed;
            this.state.pipelineReady = data.pipeline_ready || false;
            this.state.proteins = data.proteins || [];
            this.state.ligands = data.ligands || [];
            this.updateStatusUI();
            this.updateDropdowns();
        } catch (err) {
            console.error("Status check error:", err);
        }
    },

    async loadDiseaseAtlas() {
        try {
            const res = await fetch("/api/disease_targets");
            const data = await res.json();
            this.state.diseaseTargets = data.targets || [];
            this.renderDiseaseAtlas(data.disclaimer || "");
        } catch (err) {
            console.error("Disease atlas error:", err);
            const el = document.getElementById("atlas-list");
            if (el) el.innerHTML = '<div class="empty-list">Could not load disease atlas.</div>';
        }
    },

    renderDiseaseAtlas(disclaimer) {
        const el = document.getElementById("atlas-list");
        if (!el) return;
        if (this.state.diseaseTargets.length === 0) {
            el.innerHTML = '<div class="empty-list">No disease targets loaded.</div>';
            return;
        }
        el.innerHTML = this.state.diseaseTargets.map(item => {
            const targetRows = (item.targets || []).map(target => {
                const afButton = target.uniprot ? `<button class="btn btn-secondary btn-sm btn-atlas-af" data-uniprot="${this.escapeHTML(target.uniprot)}" data-label="${this.escapeHTML((target.gene || target.uniprot).toLowerCase())}"><i class="fa-solid fa-database"></i> AlphaFold</button>` : "";
                const pdbText = target.pdb ? `<span class="pdb-tag">${this.escapeHTML(target.pdb)}</span>` : "";
                return `<div class="atlas-target">
                    <div><strong>${this.escapeHTML(target.gene)}</strong> ${pdbText}<br><span>${this.escapeHTML(target.protein)} &bull; ${this.escapeHTML(target.structure_source)}</span></div>
                    ${afButton}
                </div>`;
            }).join("");
            return `<article class="atlas-card">
                <div class="atlas-card-head">
                    <h4>${this.escapeHTML(item.disease)}</h4>
                    <span>${this.escapeHTML((item.genes || []).join(", "))}</span>
                </div>
                <p>${this.escapeHTML(item.inheritance)}</p>
                <div class="atlas-targets">${targetRows}</div>
                <small>${this.escapeHTML(item.research_note)}</small>
            </article>`;
        }).join("") + `<div class="info-alert warning-box atlas-disclaimer"><i class="fa-solid fa-triangle-exclamation"></i><span>${this.escapeHTML(disclaimer)}</span></div>`;

        document.querySelectorAll(".btn-atlas-af").forEach(btn => {
            btn.addEventListener("click", () => {
                document.getElementById("input-uniprot").value = btn.getAttribute("data-uniprot");
                document.getElementById("input-af-label").value = btn.getAttribute("data-label");
            });
        });
    },

    renderInheritance() {
        const canvas = document.getElementById("inheritance-canvas");
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const mode = document.getElementById("inheritance-mode")?.value || "recessive";
        const summary = document.getElementById("inheritance-summary");
        const cases = mode === "dominant"
            ? [
                { label: "Unaffected", genotype: "aa", pct: 50, color: "#10b981" },
                { label: "At-risk", genotype: "Aa", pct: 50, color: "#f59e0b" }
            ]
            : [
                { label: "Unaffected", genotype: "AA", pct: 25, color: "#10b981" },
                { label: "Carrier", genotype: "Aa", pct: 50, color: "#3b82f6" },
                { label: "Affected", genotype: "aa", pct: 25, color: "#ef4444" }
            ];

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "#0f172a";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.font = "600 16px Segoe UI";
        ctx.fillStyle = "#e5eefb";
        ctx.fillText(mode === "dominant" ? "Autosomal dominant model" : "Autosomal recessive carrier model", 24, 34);

        let x = 32;
        cases.forEach(item => {
            const width = Math.max(90, item.pct * 3.8);
            ctx.fillStyle = item.color;
            ctx.fillRect(x, 82, width, 92);
            ctx.fillStyle = "#ffffff";
            ctx.font = "700 24px Segoe UI";
            ctx.fillText(item.pct + "%", x + 16, 124);
            ctx.font = "600 14px Segoe UI";
            ctx.fillText(item.genotype, x + 16, 150);
            ctx.fillStyle = "#cbd5e1";
            ctx.font = "12px Segoe UI";
            ctx.fillText(item.label, x + 16, 198);
            x += width + 18;
        });

        ctx.strokeStyle = "#38bdf8";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(70, 260);
        ctx.bezierCurveTo(165, 220, 275, 292, 438, 238);
        ctx.stroke();
        ctx.fillStyle = "#94a3b8";
        ctx.font = "12px Segoe UI";
        ctx.fillText("Expected probability split per child, not a prediction for a specific person.", 24, 300);

        if (summary) {
            summary.innerText = mode === "dominant"
                ? "One affected heterozygous parent and one unaffected parent: about 50% at-risk and 50% unaffected per child."
                : "Two carrier parents: about 25% unaffected, 50% carrier, and 25% affected per child.";
        }
    },

    updateStatusUI() {
        const vinaEl = document.getElementById("status-vina");
        const envEl = document.getElementById("status-env");
        vinaEl.className = "status-badge " + (this.state.vinaInstalled ? "online" : "offline");
        vinaEl.innerHTML = `<span class="dot"></span> Vina: ${this.state.vinaInstalled ? "Ready" : "Missing"}`;
        const pyReady = this.state.pipelineReady;
        envEl.className = "status-badge " + (pyReady ? "online" : "offline");
        envEl.innerHTML = `<span class="dot"></span> Python: ${pyReady ? "Ready" : "Setup Required"}`;

        this.updateCheckItem("check-vina", this.state.vinaInstalled);
        this.updateCheckItem("check-rdkit", this.state.rdkitInstalled);
        this.updateCheckItem("check-meeko", this.state.pipelineReady);

        document.getElementById("stat-proteins-count").innerText = this.state.proteins.length;
        document.getElementById("stat-ligands-count").innerText = this.state.ligands.length;

        const hasProt = this.state.proteins.length > 0;
        const hasLig = this.state.ligands.length > 0;

        this.state.stepStatus[1] = hasProt;
        this.state.stepStatus[2] = hasLig;

        document.getElementById("progress-step1").innerText = hasProt ? "Ready" : "—";
        document.getElementById("progress-step2").innerText = hasLig ? "Ready" : "—";
        document.getElementById("protein-count-badge").innerText = this.state.proteins.length + " file" + (this.state.proteins.length !== 1 ? "s" : "");
        document.getElementById("ligand-count-badge").innerText = this.state.ligands.length + " file" + (this.state.ligands.length !== 1 ? "s" : "");

        const pList = document.getElementById("prepared-proteins-list");
        if (this.state.proteins.length === 0) {
            pList.innerHTML = '<li class="empty-list">No proteins prepared yet.</li>';
        } else {
            pList.innerHTML = this.state.proteins.map(p =>
                `<li><span><i class="fa-solid fa-circle-check" style="color:var(--color-success)"></i> <strong>${this.escapeHTML(p)}</strong> (PDBQT)</span>
                  <span class="actions"><i class="fa-solid fa-trash btn-delete-protein" data-id="${this.escapeHTML(p)}"></i></span></li>`
            ).join("");
        }

        this.renderPresetsTable();
        const lList = document.getElementById("prepared-ligands-list");
        if (this.state.ligands.length === 0) {
            lList.innerHTML = '<li class="empty-list">No ligands prepared yet.</li>';
        } else {
            lList.innerHTML = this.state.ligands.map(l =>
                `<li><span><i class="fa-solid fa-circle-check" style="color:var(--color-success)"></i> <strong>${this.escapeHTML(l)}</strong> (PDBQT)</span>
                  <span class="actions"><i class="fa-solid fa-trash btn-delete-ligand" data-id="${this.escapeHTML(l)}"></i></span></li>`
            ).join("");
        }
    },

    async deleteProtein(name) {
        if (!confirm(`Delete protein "${name}"?`)) return;
        await fetch("/api/delete_protein", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name })
        });
        this.checkStatus();
    },

    async deleteLigand(name) {
        if (!confirm(`Delete ligand "${name}"?`)) return;
        await fetch("/api/delete_ligand", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name })
        });
        this.checkStatus();
    },

    updateCheckItem(id, ok) {
        const el = document.getElementById(id);
        if (ok) {
            el.className = "check-item checked";
            el.querySelector("i").className = "fa-solid fa-circle-check check-icon";
        } else {
            el.className = "check-item failed";
            el.querySelector("i").className = "fa-solid fa-circle-xmark check-icon";
        }
    },

    renderPresetsTable() {
        const tbody = document.getElementById("presets-table-body");
        tbody.innerHTML = this.ligandPresets.map(l => {
            const ready = this.state.ligands.includes(l.name);
            return `<tr>
                <td><strong>${l.name.charAt(0).toUpperCase() + l.name.slice(1)}</strong></td>
                <td><code style="font-family:var(--font-mono);font-size:10px;color:var(--text-secondary)">${this.escapeHTML(l.smiles.substring(0, 28))}...</code></td>
                <td>${this.escapeHTML(l.context)}</td>
                <td>${ready ? '<span class="badge badge-success"><i class="fa-solid fa-check"></i> Ready</span>' : '<span class="badge badge-muted">Not Prepared</span>'}</td>
            </tr>`;
        }).join("");
    },

    updateDropdowns() {
        const selP = document.getElementById("select-protein");
        const selL = document.getElementById("select-ligand");
        const pv = selP.value, lv = selL.value;
        selP.innerHTML = '<option value="">-- Select Protein --</option>' +
            this.state.proteins.map(p => `<option value="${this.escapeHTML(p)}">${this.escapeHTML(p)}</option>`).join("");
        selL.innerHTML = '<option value="">-- Select Ligand --</option>' +
            this.state.ligands.map(l => `<option value="${this.escapeHTML(l)}">${this.escapeHTML(l.charAt(0).toUpperCase() + l.slice(1))}</option>`).join("");
        selP.value = this.state.proteins.includes(pv) ? pv : "";
        selL.value = this.state.ligands.includes(lv) ? lv : "";
    },

    // ELAPSED TIME COUNTER
    startElapsedTimer(elementId) {
        const el = document.getElementById(elementId);
        if (!el) return null;
        const start = Date.now();
        el.innerText = "0s";
        const interval = setInterval(() => {
            const secs = Math.floor((Date.now() - start) / 1000);
            if (secs < 60) {
                el.innerText = secs + "s";
            } else {
                const m = Math.floor(secs / 60);
                const s = secs % 60;
                el.innerText = m + "m " + s + "s";
            }
        }, 1000);
        return interval;
    },

    // POLLING HELPER
    pollUntil(conditionFn, intervalMs, maxChecks, onEach, onDone) {
        let count = 0;
        const id = setInterval(async () => {
            await onEach();
            count++;
            if (conditionFn() || count >= maxChecks) {
                clearInterval(id);
                onDone();
            }
        }, intervalMs);
        return id;
    },

    // EVENTS
    bindEvents() {
        // Help buttons
        document.getElementById("btn-show-help").addEventListener("click", () => {
            document.getElementById("onboarding-overlay").classList.remove("hidden");
        });
        document.getElementById("btn-quick-start").addEventListener("click", () => {
            document.getElementById("onboarding-overlay").classList.remove("hidden");
        });

        // Preset cards
        document.querySelectorAll(".preset-card").forEach(card => {
            card.addEventListener("click", () => {
                document.querySelectorAll(".preset-card").forEach(c => c.classList.remove("selected"));
                card.classList.add("selected");
                const pdb = card.getAttribute("data-pdb");
                document.getElementById("input-pdb-id").value = pdb;
                this.state.selectedPreset = pdb;
                const info = this.presets[pdb];
                if (info) {
                    document.getElementById("grid-center-x").value = info.x;
                    document.getElementById("grid-center-y").value = info.y;
                    document.getElementById("grid-center-z").value = info.z;
                    document.getElementById("grid-size-x").value = info.size;
                    document.getElementById("grid-size-y").value = info.size;
                    document.getElementById("grid-size-z").value = info.size;
                    this.updateGridSummary();
                }
            });
        });

        // Grid inputs
        ["grid-center-x","grid-center-y","grid-center-z","grid-size-x","grid-size-y","grid-size-z"].forEach(id => {
            document.getElementById(id).addEventListener("input", () => this.updateGridSummary());
        });

        // Setup
        document.getElementById("btn-run-setup").addEventListener("click", async () => {
            const btn = document.getElementById("btn-run-setup");
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Setting up...';
            try {
                await fetch("/api/setup", { method: "POST" });
                this.pollUntil(
                    () => this.state.vinaInstalled && this.state.pipelineReady,
                    8000, 15,
                    () => this.checkStatus(),
                    () => { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-download"></i> Initialize Environment'; }
                );
            } catch { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-download"></i> Initialize Environment'; }
        });

        // Check status
        document.getElementById("btn-check-status").addEventListener("click", () => this.checkStatus());
        document.getElementById("btn-load-atlas").addEventListener("click", () => this.loadDiseaseAtlas());
        document.getElementById("inheritance-mode").addEventListener("change", () => this.renderInheritance());
        document.getElementById("btn-download-alphafold").addEventListener("click", async () => {
            const uniprot = document.getElementById("input-uniprot").value.trim().toUpperCase();
            const label = document.getElementById("input-af-label").value.trim().toLowerCase();
            if (!uniprot || !label) { alert("Enter both a UniProt accession and local label."); return; }
            const res = await fetch("/api/download_alphafold", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ uniprot, label })
            });
            const data = await res.json();
            alert(data.success ? data.message : ("Failed: " + data.error));
            if (data.success) {
                this.pollUntil(
                    () => this.state.proteins.includes(label.toUpperCase()),
                    3000, 20,
                    () => this.checkStatus(),
                    () => this.checkStatus()
                );
            }
        });

        // Download protein
        document.getElementById("btn-download-protein").addEventListener("click", async () => {
            const pdbId = document.getElementById("input-pdb-id").value.trim().toUpperCase();
            if (pdbId.length !== 4) { alert("Please enter a valid 4-character PDB code."); return; }
            const btn = document.getElementById("btn-download-protein");
            const progBox = document.getElementById("download-progress");
            const progText = document.getElementById("download-progress-text");
            const barContainer = document.getElementById("download-progress-bar");
            btn.disabled = true;
            progBox.classList.remove("hidden");
            barContainer.classList.remove("hidden");
            progText.innerText = `Fetching ${pdbId} from RCSB Protein Data Bank...`;
            const timer = this.startElapsedTimer("download-elapsed");
            try {
                const res = await fetch("/api/download_protein", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ pdb_id: pdbId })
                });
                const data = await res.json();
                if (data.success) {
                    this.pollUntil(
                        () => this.state.proteins.includes(pdbId),
                        3000, 20,
                        () => this.checkStatus(),
                        () => {
                            clearInterval(timer);
                            progBox.classList.add("hidden");
                            barContainer.classList.add("hidden");
                            btn.disabled = false;
                            if (this.state.proteins.includes(pdbId)) {
                                this.state.stepStatus[1] = true;
                                document.getElementById("progress-step1").innerText = "Ready";
                                document.querySelector('[data-target="panel-step2"]').click();
                            } else {
                                alert(`Timeout: ${pdbId} preparation did not complete. Check server logs.`);
                            }
                        }
                    );
                } else {
                    alert("Failed: " + data.error);
                    clearInterval(timer);
                    progBox.classList.add("hidden");
                    barContainer.classList.add("hidden");
                    btn.disabled = false;
                }
            } catch (err) {
                alert("Error: " + err);
                clearInterval(timer);
                progBox.classList.add("hidden");
                barContainer.classList.add("hidden");
                btn.disabled = false;
            }
        });

        // Prepare presets
        document.getElementById("btn-prep-presets").addEventListener("click", async () => {
            const btn = document.getElementById("btn-prep-presets");
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Preparing...';
            try {
                const res = await fetch("/api/prep_presets", { method: "POST" });
                const data = await res.json();
                if (data.success) {
                    this.pollUntil(
                        () => this.ligandPresets.every(lp => this.state.ligands.includes(lp.name)),
                        5000, 20,
                        () => this.checkStatus(),
                        () => {
                            btn.disabled = false;
                            btn.innerHTML = '<i class="fa-solid fa-gears"></i> Prepare All Presets';
                            this.state.stepStatus[2] = true;
                            document.getElementById("progress-step2").innerText = "Ready";
                        }
                    );
                } else {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fa-solid fa-gears"></i> Prepare All Presets';
                }
            } catch {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-gears"></i> Prepare All Presets';
            }
        });

        // Custom ligand
        document.getElementById("form-custom-ligand").addEventListener("submit", async (e) => {
            e.preventDefault();
            const name = document.getElementById("ligand-name").value.trim().toLowerCase();
            const smiles = document.getElementById("ligand-smiles").value.trim();
            const btn = document.getElementById("btn-add-ligand");
            const progBox = document.getElementById("ligand-progress");
            const progText = document.getElementById("ligand-progress-text");
            const barContainer = document.getElementById("ligand-progress-bar");
            progBox.classList.remove("hidden");
            barContainer.classList.remove("hidden");
            progText.innerText = `Generating 3D structure for ${name} via PubChem API...`;
            btn.disabled = true;
            const timer = this.startElapsedTimer("ligand-elapsed");
            try {
                const res = await fetch("/api/prep_custom_ligand", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, smiles })
                });
                const data = await res.json();
                if (data.success) {
                    this.pollUntil(
                        () => this.state.ligands.includes(name),
                        3000, 20,
                        () => this.checkStatus(),
                        () => {
                            clearInterval(timer);
                            progBox.classList.add("hidden");
                            barContainer.classList.add("hidden");
                            btn.disabled = false;
                            document.getElementById("form-custom-ligand").reset();
                            if (this.state.ligands.includes(name)) {
                                this.state.stepStatus[2] = true;
                                document.getElementById("progress-step2").innerText = "Ready";
                            } else {
                                alert("Timeout or invalid SMILES.");
                            }
                        }
                    );
                } else {
                    alert("Failed: " + data.error);
                    clearInterval(timer);
                    progBox.classList.add("hidden");
                    barContainer.classList.add("hidden");
                    btn.disabled = false;
                }
            } catch (err) {
                alert("Error: " + err);
                clearInterval(timer);
                progBox.classList.add("hidden");
                barContainer.classList.add("hidden");
                btn.disabled = false;
            }
        });

        // Run docking
        document.getElementById("btn-start-docking").addEventListener("click", async () => {
            const protein = document.getElementById("select-protein").value;
            const ligand = document.getElementById("select-ligand").value;
            if (!protein || !ligand) { alert("Please select both a prepared protein and a ligand."); return; }
            const cx = parseFloat(document.getElementById("grid-center-x").value) || 0;
            const cy = parseFloat(document.getElementById("grid-center-y").value) || 0;
            const cz = parseFloat(document.getElementById("grid-center-z").value) || 0;
            const sx = parseInt(document.getElementById("grid-size-x").value) || 20;
            const sy = parseInt(document.getElementById("grid-size-y").value) || 20;
            const sz = parseInt(document.getElementById("grid-size-z").value) || 20;
            const exh = parseInt(document.getElementById("grid-exhaustiveness").value) || 8;

            const jobCard = document.getElementById("active-job-details");
            const btn = document.getElementById("btn-start-docking");
            const consoleStream = document.getElementById("console-stream");
            const barContainer = document.getElementById("docking-progress-bar");

            jobCard.className = "active-job-card running";
            jobCard.innerHTML = `<h4><i class="fa-solid fa-spinner fa-spin"></i> Simulation Running...</h4>
                <p class="subtext">Target: <strong>${this.escapeHTML(protein)}</strong> | Ligand: <strong>${this.escapeHTML(ligand)}</strong></p>
                <small>Search box at (${cx}, ${cy}, ${cz}) &mdash; ${sx}&times;${sy}&times;${sz} &Aring;</small>`;
            btn.disabled = true;
            barContainer.classList.remove("hidden");
            consoleStream.innerText = `Initializing Vina simulation...\nReceptor: ${protein}.pdbqt\nLigand: ${ligand}.pdbqt\nSearch space: (${cx}, ${cy}, ${cz}) size ${sx}x${sy}x${sz}\nExhaustiveness: ${exh}\n\nRunning docking calculations...`;

            const timer = this.startElapsedTimer("docking-elapsed");
            this.state.currentJob = { protein_id: protein, ligand_name: ligand, status: "running" };

            try {
                const res = await fetch("/api/run_docking", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ protein_id: protein, ligand_name: ligand, center_x: cx, center_y: cy, center_z: cz, size_x: sx, size_y: sy, size_z: sz, exhaustiveness: exh })
                });
                const data = await res.json();
                if (data.success) {
                    this.pollUntil(
                        () => {
                            const key = `${protein}_${ligand}`;
                            const job = this.state.results[key];
                            return job && (job.status === "completed" || job.status === "failed");
                        },
                        2000, 60,
                        async () => {
                            await this.fetchResults();
                            const key = `${protein}_${ligand}`;
                            const job = this.state.results[key];
                            if (job && job.log_file) {
                                const logRes = await fetch(`/api/log?file=${encodeURIComponent(job.log_file)}`);
                                const logData = await logRes.json();
                                if (logData.success && logData.content) {
                                    consoleStream.innerText = logData.content;
                                    consoleStream.scrollTop = consoleStream.scrollHeight;
                                }
                            }
                            this.updateResultsTable(this.state.results);
                        },
                        () => {
                            clearInterval(timer);
                            barContainer.classList.add("hidden");
                            btn.disabled = false;
                            const key = `${protein}_${ligand}`;
                            const job = this.state.results[key];
                            if (job && job.status === "completed") {
                                this.state.stepStatus[4] = true;
                                jobCard.className = "active-job-card";
                                jobCard.innerHTML = `<h4 style="color:var(--color-success)"><i class="fa-solid fa-circle-check"></i> Simulation Complete</h4>
                                    <p class="subtext">Binding Affinity: <strong>${job.binding_affinity} kcal/mol</strong></p>
                                    <button class="btn btn-secondary btn-sm mt-10" id="btn-view-pose"><i class="fa-solid fa-eye"></i> View in 3D</button>`;
                                document.getElementById("btn-view-pose").onclick = () => {
                                    document.querySelector('[data-target="panel-step5"]').click();
                                    this.load3DComplex(protein, ligand);
                                };
                            } else {
                                jobCard.className = "active-job-card";
                                jobCard.innerHTML = `<h4 style="color:var(--color-danger)"><i class="fa-solid fa-circle-xmark"></i> Simulation Failed</h4>
                                    <p class="subtext">${this.escapeHTML((job && job.error) || "Unknown error")}</p>`;
                            }
                            this.state.currentJob = null;
                        }
                    );
                } else {
                    alert("Failed to start: " + data.error);
                    clearInterval(timer);
                    barContainer.classList.add("hidden");
                    btn.disabled = false;
                    jobCard.className = "active-job-card";
                    jobCard.innerHTML = "<h4>Failed to Launch</h4>";
                }
            } catch (err) {
                alert("Request error: " + err);
                clearInterval(timer);
                barContainer.classList.add("hidden");
                btn.disabled = false;
                jobCard.className = "active-job-card";
            }
        });

        // Refresh results
        document.getElementById("btn-refresh-results").addEventListener("click", async () => {
            await this.fetchResults();
            this.updateResultsTable(this.state.results);
        });

        // Delete handlers (delegated)
        document.addEventListener("click", (e) => {
            const delProt = e.target.closest(".btn-delete-protein");
            if (delProt) this.deleteProtein(delProt.getAttribute("data-id"));
            const delLig = e.target.closest(".btn-delete-ligand");
            if (delLig) this.deleteLigand(delLig.getAttribute("data-id"));
        });

        // Reset 3D view
        document.getElementById("btn-reset-view").addEventListener("click", () => this.resetView());

        // Clear results
        document.getElementById("btn-clear-results").addEventListener("click", async () => {
            if (!confirm("Clear all docking results?")) return;
            await fetch("/api/clear_results", { method: "POST" });
            this.state.results = {};
            this.updateResultsTable({});
            this.checkStatus();
        });

        // Download manuscript
        document.getElementById("btn-download-manuscript").addEventListener("click", async () => {
            const text = document.getElementById("manuscript-editor").value;
            if (!text) { alert("Compile a draft first."); return; }
            const res = await fetch("/api/download_manuscript", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content: text, filename: "manuscript.md" })
            });
            const data = await res.json();
            if (data.success) {
                const a = document.createElement("a");
                a.href = data.url;
                a.download = "manuscript.md";
                a.click();
            } else {
                alert("Download failed: " + (data.error || "unknown"));
            }
        });

        // Generate paper
        document.getElementById("btn-generate-draft").addEventListener("click", () => this.generateManuscript());
        document.getElementById("btn-copy-manuscript").addEventListener("click", () => {
            const text = document.getElementById("manuscript-editor").value;
            if (!text) { alert("Compile a draft first."); return; }
            navigator.clipboard.writeText(text);
            alert("Copied to clipboard!");
        });

        // Auto-refresh results every 5s when on the results panel
        setInterval(() => {
            if (this.state.activeTab === "panel-step5") {
                this.fetchResults().then(d => this.updateResultsTable(d));
            }
        }, 5000);
    },

    updateGridSummary() {
        const cx = parseFloat(document.getElementById("grid-center-x").value) || 0;
        const cy = parseFloat(document.getElementById("grid-center-y").value) || 0;
        const cz = parseFloat(document.getElementById("grid-center-z").value) || 0;
        const sx = parseInt(document.getElementById("grid-size-x").value) || 20;
        const sy = parseInt(document.getElementById("grid-size-y").value) || 20;
        const sz = parseInt(document.getElementById("grid-size-z").value) || 20;
        document.getElementById("sum-center").innerText = `(${cx.toFixed(1)}, ${cy.toFixed(1)}, ${cz.toFixed(1)})`;
        document.getElementById("sum-dimensions").innerHTML = `${sx} x ${sy} x ${sz} &Aring;&sup3;`;
        document.getElementById("sum-volume").innerText = (sx * sy * sz).toLocaleString() + " &Aring;&sup3;";
    },

    // RESULTS
    async fetchResults() {
        try {
            const res = await fetch("/api/results");
            const data = await res.json();
            this.state.results = data;
            return data;
        } catch { return {}; }
    },

    updateResultsTable(results) {
        const tbody = document.getElementById("results-table-body");
        const keys = Object.keys(results);
        if (keys.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center" style="color:var(--text-muted);padding:24px">No simulation runs recorded yet.</td></tr>';
            document.getElementById("stat-docking-count").innerText = 0;
            this.state.stepStatus[5] = false;
            return;
        }
        const completed = keys.filter(k => results[k].status === "completed").length;
        document.getElementById("stat-docking-count").innerText = completed;
        this.state.stepStatus[5] = completed > 0;
        this.state.stepStatus[4] = completed > 0;

        tbody.innerHTML = keys.map(k => {
            const r = results[k];
            const strong = r.binding_affinity && r.binding_affinity <= -7.0;
            const proteinId = this.escapeHTML(r.protein_id);
            const ligandName = this.escapeHTML(r.ligand_name);
            const ligandLabel = this.escapeHTML(r.ligand_name.charAt(0).toUpperCase() + r.ligand_name.slice(1));
            const status = this.escapeHTML(r.status);
            return `<tr>
                <td><strong>${proteinId}</strong></td>
                <td>${ligandLabel}</td>
                <td${strong ? ' style="color:var(--color-success);font-weight:700"' : ''}>${r.binding_affinity !== null ? r.binding_affinity.toFixed(1) + " kcal/mol" : "N/A"}</td>
                <td><span class="badge ${r.status === 'completed' ? 'badge-success' : r.status === 'running' ? 'badge-warning' : 'badge-danger'}">${status}</span></td>
                <td>${r.status === 'completed' ? `<button class="btn btn-secondary btn-sm btn-load-3d" data-protein="${proteinId}" data-ligand="${ligandName}"><i class="fa-solid fa-cube"></i> 3D View</button>` : 'N/A'}</td>
            </tr>`;
        }).join("");

        document.querySelectorAll(".btn-load-3d").forEach(btn => {
            btn.addEventListener("click", () => {
                this.load3DComplex(btn.getAttribute("data-protein"), btn.getAttribute("data-ligand"));
            });
        });
    },

    // 3D VISUALIZER
    load3DComplex(proteinId, ligandName) {
        if (!this.state.viewer3D) {
            this.init3DViewer();
        }
        const viewer = this.state.viewer3D;
        if (!viewer) { alert("3D viewer could not initialize. Please try again from the Analysis tab."); return; }
        const loader = document.getElementById("loading-3d");
        const emptyState = document.getElementById("viewer-empty-state");
        const statusEl = document.getElementById("viewer-status");
        const surfaceToggle = document.getElementById("viewer-surface-toggle");
        const chkSurface = document.getElementById("chk-surface");

        loader.classList.remove("hidden");
        emptyState.classList.add("hidden");
        viewer.clear();
        if (this.state.surfaceVisible) {
            viewer.removeAllSurfaces();
            this.state.surfaceVisible = false;
            chkSurface.checked = false;
        }
        viewer.render();

        // Show binding affinity from results if available
        const key = `${proteinId}_${ligandName}`;
        const result = this.state.results[key];
        const affinity = result && result.binding_affinity ? result.binding_affinity.toFixed(1) + " kcal/mol" : "—";

        Promise.all([
            fetch(`/data/proteins/${proteinId.toLowerCase()}_clean.pdb`).then(r => r.ok ? r.text() : Promise.reject("Protein PDB not found")),
            fetch(`/data/results/${proteinId.toLowerCase()}_${ligandName.toLowerCase()}_out.pdbqt`).then(r => r.ok ? r.text() : Promise.reject("Docked ligand PDBQT not found"))
        ]).then(([proteinData, ligandData]) => {
            const recModel = viewer.addModel(proteinData, "pdb");
            this.applyProteinStyle(recModel, document.getElementById("vis-protein-style").value);
            const ligModel = viewer.addModel(ligandData, "pdbqt");
            this.applyLigandStyle(ligModel, document.getElementById("vis-ligand-style").value);

            this.state.currentComplex = { recModel, ligModel, proteinId, ligandName, affinity };

            viewer.zoomTo({ model: ligModel });
            viewer.render();

            statusEl.innerText = `${proteinId} + ${ligandName} — ${affinity}`;
            surfaceToggle.classList.remove("hidden");
            chkSurface.checked = false;

            document.getElementById("vis-protein-style").onchange = (e) => {
                this.applyProteinStyle(recModel, e.target.value);
                if (this.state.surfaceVisible) {
                    viewer.removeAllSurfaces();
                    viewer.addSurface($3Dmol.SurfaceType.VDW, {
                        opacity: 0.6, color: "spectrum", model: recModel
                    }, { model: recModel });
                }
                viewer.render();
            };
            document.getElementById("vis-ligand-style").onchange = (e) => {
                this.applyLigandStyle(ligModel, e.target.value);
                viewer.render();
            };
            chkSurface.onchange = () => this.toggleSurface();

            loader.classList.add("hidden");
        }).catch(err => {
            loader.classList.add("hidden");
            this.state.currentComplex = null;
            statusEl.innerText = "Error loading complex";
            alert("Error loading 3D: " + (err.message || err));
        });
    },

    applyProteinStyle(model, style) {
        model.setStyle({}, {});
        const styles = {
            cartoon: { cartoon: { color: "spectrum", opacity: 0.85 } },
            sphere: { sphere: { scale: 1.0, colorscheme: "chainHetatm" } },
            stick: { stick: { radius: 0.3 } },
            line: { line: {} }
        };
        if (styles[style]) model.setStyle({}, styles[style]);
    },

    applyLigandStyle(model, style) {
        model.setStyle({}, {});
        const styles = {
            stick: { stick: { colorscheme: "Jmol", radius: 0.4 } },
            sphere: { sphere: { scale: 0.9, colorscheme: "Jmol" } },
            line: { line: { colorscheme: "Jmol" } }
        };
        if (styles[style]) model.setStyle({}, styles[style]);
    },

    // MANUSCRIPT
    generateManuscript() {
        const author = document.getElementById("paper-author").value || "Student Researcher";
        const institution = document.getElementById("paper-institution").value || "High School Department of Science";
        const completedRuns = Object.values(this.state.results).filter(r => r.status === "completed");
        if (completedRuns.length === 0) {
            document.getElementById("manuscript-editor").value = [
                "# Jeen Lab Computational Screening Report",
                "",
                "No completed docking runs are available yet.",
                "",
                "Run at least one AutoDock Vina experiment before generating a manuscript. Jeen Lab does not insert example binding scores into research reports."
            ].join("\n");
            return;
        }
        completedRuns.sort((a, b) => (a.binding_affinity || 0) - (b.binding_affinity || 0));
        const targetNames = [...new Set(completedRuns.map(r => r.protein_id))];
        const primaryTarget = targetNames[0];
        const cx = document.getElementById("grid-center-x").value || "16.0";
        const cy = document.getElementById("grid-center-y").value || "10.0";
        const cz = document.getElementById("grid-center-z").value || "15.0";
        const sx = document.getElementById("grid-size-x").value || "22";

        let tableRows = "";
        completedRuns.forEach((r, idx) => {
            tableRows += `| ${idx + 1} | ${r.protein_id} | ${r.ligand_name.toUpperCase()} | ${r.binding_affinity.toFixed(1)} kcal/mol | ${r.binding_affinity <= -7.0 ? "Strong Binding" : "Moderate Interaction"} |\n`;
        });
        const template = `# Jeen Lab Computational Docking Analysis for Target ${primaryTarget}

**Author:** ${author}
**Affiliation:** ${institution}
**Date:** ${new Date().toLocaleDateString()}

---

## Abstract
Computer-aided drug design can prioritize hypotheses for laboratory follow-up. In this study, Jeen Lab used AutoDock Vina to simulate ligand binding against **${primaryTarget}**. The best observed computational score in this local run was **${completedRuns[0].ligand_name.toUpperCase()}** at **${completedRuns[0].binding_affinity.toFixed(1)} kcal/mol**. This is a screening result only and is not evidence of clinical efficacy, safety, prevention, or cure.

## Introduction
Diseases are driven by specific cellular proteins displaying abnormal functioning. Pharmacological agents act by binding into pockets, blocking active active sites, or modulating the receptor conformation. Prior to real-world laboratory biological assays, computational screening screens libraries to evaluate geometric and chemical complementarity.

Here, we explore the receptor protein **${primaryTarget}** which plays a major pathological role. Our objective is to evaluate a structural library of drugs to find candidates with high potential binding parameters.

## Methods
1. **Receptor Preparation**: The 3D coordinate model of **${primaryTarget}** was retrieved from the RCSB Protein Data Bank. Water molecules and buffer agents were stripped. Polar hydrogen atoms were added, and structures parameterised.
2. **Ligand Preparation**: Molecular geometries for ligand compounds were generated from canonical SMILES strings. Conformations were optimized. Conversion to PDBQT format was processed for AutoDock Vina compatibility.
3. **Simulation Protocol**: Rigid-receptor molecular docking was executed using AutoDock Vina 1.2.5. The grid box search volume was centered on the active pocket at coords: (${cx}, ${cy}, ${cz}) with dimensions of ${sx}A.

## Results
The virtual screening simulations yielded binding energies indicating the relative strength of the interactions (more negative energies imply stronger thermodynamic compatibility).

| Rank | Receptor | Compound | Binding Energy (kcal/mol) | Analysis |
| :--- | :--- | :--- | :--- | :--- |
${tableRows}
*Table 1: AutoDock Vina predicted binding energies.*

The compound **${completedRuns[0].ligand_name.toUpperCase()}** displayed the most favorable predicted binding affinity among completed local runs. Visual inspection should be used to check pocket placement, steric clashes, and whether the grid actually covers the intended active site.

## Discussion
This in-silico screen suggests which compounds may deserve deeper investigation against **${primaryTarget}**. Docking scores do not establish stable biological complexes, target engagement in cells, toxicity, pharmacokinetics, or disease modification.

**Limitations**: Docking calculations represent idealized, static approximations. Factors such as dynamic protein flexibility, solvent entropy, and cellular absorption parameters cannot be fully predicted by docking alone. In vitro cellular assays are required to confirm biological efficacy.

## References
1. Trott, O., & Olson, A. J. (2010). AutoDock Vina: improving the speed and accuracy of docking with a new scoring function, efficient optimization, and multithreading. *Journal of computational chemistry*, 31(2), 455-461.
2. Landrum, G. (2016). RDKit: Open-source cheminformatics. *Online*.
3. Apache / Meeko (Scripps Research Institute).`;
        document.getElementById("manuscript-editor").value = template;
        this.state.stepStatus[6] = true;
    }
};

window.GenomeSentinel = GenomeSentinel;
document.addEventListener("DOMContentLoaded", () => GenomeSentinel.init());

const tabs = document.querySelectorAll(".tool-tab");
const views = document.querySelectorAll(".tool-view");

tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
        tabs.forEach((item) => {
            const active = item === tab;
            item.classList.toggle("active", active);
            item.setAttribute("aria-selected", String(active));
        });
        views.forEach((view) => {
            const active = view.id === `view-${tab.dataset.view}`;
            view.classList.toggle("active", active);
            view.hidden = !active;
        });
    });
});

function formValues() {
    return {
        topic: document.getElementById("topic").value.trim(),
        content_type: document.getElementById("contentType").value,
        tone: document.getElementById("tone").value,
        audience: document.getElementById("audience").value.trim(),
        temperature: Number(document.getElementById("temperature").value),
        top_p: Number(document.getElementById("topP").value)
    };
}

async function postJSON(url, body) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The request could not be completed.");
    return data;
}

function setResult(element, content) {
    element.textContent = content;
    element.classList.remove("empty-state", "error-state");
}

async function runForm(form, button, status, action) {
    button.disabled = true;
    button.classList.add("is-loading");
    status.textContent = "WORKING...";
    try {
        await action();
        status.textContent = "COMPLETE";
    } catch (error) {
        status.textContent = "NEEDS ATTENTION";
        const output = form.closest(".workbench").querySelector(".result-body, .analysis-content");
        setResult(output, error.message);
        output.classList.add("error-state");
    } finally {
        button.disabled = false;
        button.classList.remove("is-loading");
    }
}

document.getElementById("contentForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type=submit]");
    const output = document.getElementById("createResult");
    const status = document.getElementById("createStatus");
    runForm(form, button, status, async () => {
        const data = await postJSON("/api/generate", formValues());
        setResult(output, data.content);
    });
});

document.getElementById("podcastForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type=submit]");
    const output = document.getElementById("podcastResult");
    const status = document.getElementById("podcastStatus");
    runForm(form, button, status, async () => {
        const data = await postJSON("/api/podcast", {
            topic: document.getElementById("podcastTopic").value.trim(),
            audience: document.getElementById("podcastAudience").value.trim()
        });
        setResult(output, data.plan);
    });
});

document.getElementById("analysisText").addEventListener("input", (event) => {
    document.getElementById("characterCount").textContent = event.currentTarget.value.length.toLocaleString();
});

document.getElementById("analysisForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type=submit]");
    const status = document.getElementById("analysisStatus");
    const output = document.getElementById("analysisResult");
    runForm(form, button, status, async () => {
        const data = await postJSON("/api/analyze", { text: document.getElementById("analysisText").value.trim() });
        const analysis = data.analysis;
        output.replaceChildren();
        output.classList.remove("empty-state", "error-state");
        const sentiment = document.createElement("span");
        sentiment.className = `sentiment sentiment-${analysis.sentiment.toLowerCase()}`;
        sentiment.textContent = analysis.sentiment;
        const summaryTitle = document.createElement("h3");
        summaryTitle.textContent = "Reading";
        const summary = document.createElement("p");
        summary.textContent = analysis.summary;
        const keywordTitle = document.createElement("h3");
        keywordTitle.textContent = "Key phrases";
        const keywords = document.createElement("div");
        keywords.className = "keyword-list";
        analysis.keywords.forEach((word) => {
            const item = document.createElement("span");
            item.className = "keyword";
            item.textContent = word;
            keywords.append(item);
        });
        output.append(sentiment, summaryTitle, summary, keywordTitle, keywords);
    });
});

const parameter = document.getElementById("compareParameter");
const valueA = document.getElementById("valueA");
const valueB = document.getElementById("valueB");

function updateComparisonControls() {
    const isTemperature = parameter.value === "temperature";
    const maximum = isTemperature ? "2" : "1";
    valueA.max = maximum;
    valueB.max = maximum;
    valueA.step = isTemperature ? "0.1" : "0.05";
    valueB.step = isTemperature ? "0.1" : "0.05";
    valueA.value = isTemperature ? "0.3" : "0.2";
    valueB.value = isTemperature ? "1.2" : "0.8";
    updateComparisonLabels();
}

function updateComparisonLabels(results) {
    document.getElementById("labelA").textContent = `Version A · ${results?.[0]?.value ?? valueA.value}`;
    document.getElementById("labelB").textContent = `Version B · ${results?.[1]?.value ?? valueB.value}`;
}

parameter.addEventListener("change", updateComparisonControls);
valueA.addEventListener("input", () => updateComparisonLabels());
valueB.addEventListener("input", () => updateComparisonLabels());

document.getElementById("compareButton").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const status = document.getElementById("compareStatus");
    button.disabled = true;
    button.classList.add("is-loading");
    status.textContent = "RUNNING BOTH VERSIONS...";
    try {
        const data = await postJSON("/api/compare", {
            ...formValues(),
            parameter: parameter.value,
            value_a: Number(valueA.value),
            value_b: Number(valueB.value)
        });
        setResult(document.getElementById("compareResultA"), data.results[0].content);
        setResult(document.getElementById("compareResultB"), data.results[1].content);
        updateComparisonLabels(data.results);
        status.textContent = "COMPARISON COMPLETE";
    } catch (error) {
        status.textContent = error.message;
    } finally {
        button.disabled = false;
        button.classList.remove("is-loading");
    }
});

document.getElementById("temperature").addEventListener("input", (event) => {
    document.getElementById("temperatureValue").value = Number(event.currentTarget.value).toFixed(1);
});

document.getElementById("topP").addEventListener("input", (event) => {
    document.getElementById("topPValue").value = Number(event.currentTarget.value).toFixed(2);
});

document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
        const text = document.getElementById(button.dataset.copy).textContent;
        if (!text || document.getElementById(button.dataset.copy).classList.contains("empty-state")) return;
        try {
            await navigator.clipboard.writeText(text);
            button.textContent = "Copied";
            window.setTimeout(() => { button.textContent = "Copy"; }, 1400);
        } catch {
            button.textContent = "Unavailable";
        }
    });
});
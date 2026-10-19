"use strict";

const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const messages = document.getElementById("chatMessages");
const status = document.getElementById("status");
const shortcuts = document.querySelectorAll("[data-question]");

const faqToggle = document.getElementById("faqToggle");
const settingsToggle = document.getElementById("settingsToggle");
const settingsPanel = document.getElementById("settingsPanel");
const settingsOverlay = document.getElementById("settingsOverlay");
const settingsClose = document.getElementById("settingsClose");
const faqEditForm = document.getElementById("faqEditForm");
const editQuestion = document.getElementById("editQuestion");
const editAnswer = document.getElementById("editAnswer");
const editCategory = document.getElementById("editCategory");
const editAlternatives = document.getElementById("editAlternatives");
const editingFaqId = document.getElementById("editingFaqId");
const faqEditStatus = document.getElementById("faqEditStatus");
const manageFaqList = document.getElementById("manageFaqList");
const manageFaqSearch = document.getElementById("manageFaqSearch");
const managedFaqCount = document.getElementById("managedFaqCount");
const saveFaqButton = document.getElementById("saveFaqButton");
const deleteFaqButton = document.getElementById("deleteFaqButton");
const cancelFaqButton = document.getElementById("cancelFaqButton");
const newFaqButton = document.getElementById("newFaqButton");
const exportFaqButton = document.getElementById("exportFaqButton");
const editFormTitle = document.getElementById("editFormTitle");
const trashSearch = document.getElementById("trashSearch");
const trashStatus = document.getElementById("trashStatus");
const trashCount = document.getElementById("trashCount");
const trashItems = document.getElementById("trashItems");
const refreshTrashButton = document.getElementById("refreshTrashButton");
let deletedFaqs = [];
let trashBusy = false;

const reviewLoggingToggle = document.getElementById("reviewLoggingToggle");
const reviewStatusFilter = document.getElementById("reviewStatusFilter");
const reviewRefresh = document.getElementById("reviewRefresh");
const reviewDeleteAll = document.getElementById("reviewDeleteAll");
const reviewCounts = document.getElementById("reviewCounts");
const reviewStatus = document.getElementById("reviewStatus");
const reviewItems = document.getElementById("reviewItems");
const reviewIncludeEmbedding = document.getElementById("reviewIncludeEmbedding");
const reviewEvaluate = document.getElementById("reviewEvaluate");
const reviewEvaluationResult = document.getElementById("reviewEvaluationResult");

const editSourceTitle = document.getElementById("editSourceTitle");
const editSourceUrl = document.getElementById("editSourceUrl");
const editValidUntil = document.getElementById("editValidUntil");
const editVerificationStatus = document.getElementById("editVerificationStatus");
const dupMethod = document.getElementById("dupMethod");
const dupModelPath = document.getElementById("dupModelPath");
let ownModelPathDefault = "";
let v2ModelPathDefault = "";
const dupMethodSave = document.getElementById("dupMethodSave");
const dupMethodStatus = document.getElementById("dupMethodStatus");
const dupThresholdRange = document.getElementById("dupThresholdRange");
const dupThresholdNumber = document.getElementById("dupThresholdNumber");
const dupThresholdLabel = document.getElementById("dupThresholdLabel");
const dupThresholdSave = document.getElementById("dupThresholdSave");
const dupScan = document.getElementById("dupScan");
const duplicateStatus = document.getElementById("duplicateStatus");
const duplicateCandidates = document.getElementById("duplicateCandidates");
let duplicateWorking = false;
const faqImportFile = document.getElementById("faqImportFile");
const previewFaqImportButton = document.getElementById("previewFaqImport");
const commitFaqImportButton = document.getElementById("commitFaqImport");
const faqImportStatus = document.getElementById("faqImportStatus");
const faqImportPreview = document.getElementById("faqImportPreview");
let previewReadyRecords = [];
const faqPanel = document.getElementById("faqPanel");
const faqOverlay = document.getElementById("faqOverlay");
const faqClose = document.getElementById("faqClose");
const faqSearch = document.getElementById("faqSearch");
const faqList = document.getElementById("faqList");
const faqTotal = document.getElementById("faqTotal");
const faqMeta = document.getElementById("faqMeta");
const categoryButtons = document.querySelectorAll("[data-category]");
const categoryNames = {
    kargo: "Kargo",
    iade: "İade",
    odeme: "Ödeme",
    hesap: "Hesap",
    siparis: "Sipariş",
    urun: "Ürün ve stok",
    kampanya: "Kampanya",
    destek: "Teknik destek"
};
const categoryOrder = ["kargo", "iade", "odeme", "hesap", "siparis", "urun", "kampanya", "destek"];

let busy = false;
let faqs = [];
let activeCategory = "all";
let faqsLoaded = false;
let previousFocus = null;

function addMessage(text, role, category, meta = null) {
    const row = document.createElement("div");
    row.className = "message-row " + role;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    const paragraph = document.createElement("p");
    // API çıktısını ve kullanıcı girdisini HTML olarak çalıştırma.
    paragraph.textContent = text;
    bubble.appendChild(paragraph);
    if (category) {
        const label = document.createElement("small");
        label.className = "category";
        label.textContent = "Kategori: " + (categoryNames[category] || category);
        bubble.appendChild(label);
    }
    if (meta && role === "bot") {
        const info = document.createElement("small");
        info.className = "source-information";
        const ver = {
            unverified: "Doğrulanmadı",
            review_needed: "İnceleme gerekli",
            verified: "Elle doğrulandı"
        };
        info.textContent = (ver[meta.verification_status] || "Doğrulanmadı") +
            (meta.valid_until ? " · Geçerlilik: " + meta.valid_until : " · Geçerlilik tarihi yok") +
            (meta.validity_status === "expired" ? " · SÜRESİ DOLDU" : "");
        bubble.appendChild(info);
        if (meta.source_url && /^https?:\/\//i.test(meta.source_url)) {
            const link = document.createElement("a");
            link.textContent = "Kaynak: " + (meta.source_title || meta.source_url);
            link.href = meta.source_url;
            link.rel = "noopener noreferrer";
            link.target = "_blank";
            link.className = "source-link";
            bubble.appendChild(link);
        } else if (meta.source_title) {
            const label = document.createElement("small");
            label.className = "source-information";
            label.textContent = "Kaynak: " + meta.source_title;
            bubble.appendChild(label);
        }
    }
    row.appendChild(bubble);
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
}

function setBusy(value) {
    busy = value;
    input.disabled = value;
    sendButton.disabled = value;
    sendButton.textContent = value ? "Bekleyin..." : "Gönder ↗";
    shortcuts.forEach((button) => { button.disabled = value; });
}

async function sendMessage(raw) {
    const message = raw.trim();
    if (!message || busy) return;
    addMessage(message, "user");
    input.value = "";
    setBusy(true);
    status.textContent = "Yanıt hazırlanıyor.";
    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message })
        });
        if (!response.ok) throw new Error("HTTP " + response.status);
        const data = await response.json();
        if (typeof data.answer !== "string") {
            throw new Error("Beklenmeyen API yanıtı");
        }
        const bubble = addMessage(data.answer, "bot", data.category, data);
        showAnswerTools(bubble, data, message);
        status.textContent = "Yanıt geldi.";
    } catch (error) {
        console.error("FAQBot bağlantı hatası:", error);
        addMessage("Şu anda yanıt alınamadı. Lütfen tekrar deneyin.", "bot");
        status.textContent = "Bağlantı hatası.";
    } finally {
        setBusy(false);
        input.focus();
    }
}

function notice(text) {
    const paragraph = document.createElement("p");
    paragraph.className = "faq-notice";
    paragraph.textContent = text;
    faqList.replaceChildren(paragraph);
}

function renderFaqs() {
    if (!faqsLoaded) return;
    const query = faqSearch.value.trim().toLocaleLowerCase("tr-TR");
    const visibleFaqs = faqs.filter((faq) => {
        const inCategory = activeCategory === "all" || faq.category === activeCategory;
        const combined = (faq.question + " " + faq.answer).toLocaleLowerCase("tr-TR");
        return inCategory && combined.includes(query);
    });
    if (visibleFaqs.length === 0) {
        notice("Bu filtrelere uygun soru bulunamadı.");
        return;
    }
    const fragment = document.createDocumentFragment();
    for (const category of categoryOrder) {
        const groupFaqs = visibleFaqs.filter((faq) => faq.category === category);
        if (groupFaqs.length === 0) continue;

        const group = document.createElement("section");
        group.className = "faq-group";
        const title = document.createElement("h3");
        title.textContent = (categoryNames[category] || category) + " (" + groupFaqs.length + ")";
        group.appendChild(title);

        for (const faq of groupFaqs) {
            const item = document.createElement("div");
            item.className = "faq-item";
            const askButton = document.createElement("button");
            askButton.type = "button";
            askButton.className = "faq-item-button";
            const questionText = document.createElement("span");
            questionText.textContent = faq.question;
            const arrow = document.createElement("span");
            arrow.textContent = "↗";
            arrow.setAttribute("aria-hidden", "true");
            askButton.append(questionText, arrow);
            askButton.addEventListener("click", () => {
                if (busy) return;
                closeFaqPanel();
                sendMessage(faq.question);
            });

            const details = document.createElement("details");
            details.className = "faq-answer";
            const summary = document.createElement("summary");
            summary.textContent = "Yanıtı önizle";
            const answer = document.createElement("p");
            answer.textContent = faq.answer;
            const source = document.createElement("small");
            source.className = "faq-provenance";
            source.textContent = (faq.verification_status === "verified" ? "Elle doğrulandı" :
                faq.verification_status === "review_needed" ? "İnceleme gerekli" : "Doğrulanmadı") +
                (faq.valid_until ? " · Bitiş: " + faq.valid_until : "") +
                (faq.validity_status === "expired" ? " · SÜRESİ DOLDU" : "") +
                (faq.source_title ? " · Kaynak: " + faq.source_title : "");
            details.appendChild(source);
            details.append(summary, answer);
            item.append(askButton, details);
            group.appendChild(item);
        }
        fragment.appendChild(group);
    }
    faqList.replaceChildren(fragment);
}

async function loadFaqs() {
    notice("Sorular yükleniyor...");
    try {
        const response = await fetch("/faqs");
        if (!response.ok) throw new Error("HTTP " + response.status);
        const data = await response.json();
        if (!Array.isArray(data.faqs)) throw new Error("SSS listesi geçersiz");
        faqs = data.faqs.filter((item) =>
            typeof item.question === "string" &&
            typeof item.answer === "string" &&
            typeof item.category === "string"
        );
        faqsLoaded = true;
        faqTotal.textContent = String(faqs.length);
        faqMeta.textContent = faqs.length + " soru · 8 kategori";
        renderFaqs();
        renderManageList();
    } catch (error) {
        console.error("SSS listesi yüklenemedi:", error);
        faqsLoaded = false;
        notice("Sorular yüklenemedi. Bağlantınızı kontrol edip listeyi yeniden açın.");
    }
}

function openFaqPanel() {
    previousFocus = document.activeElement;
    faqPanel.hidden = false;
    faqOverlay.hidden = false;
    faqToggle.setAttribute("aria-expanded", "true");
    document.body.classList.add("faq-open");
    faqSearch.focus();
    if (!faqsLoaded) loadFaqs();
}

function closeFaqPanel() {
    faqPanel.hidden = true;
    faqOverlay.hidden = true;
    faqToggle.setAttribute("aria-expanded", "false");
    document.body.classList.remove("faq-open");
    if (previousFocus && typeof previousFocus.focus === "function") {
        previousFocus.focus();
    }
}

form.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage(input.value);
});
shortcuts.forEach((button) => {
    button.addEventListener("click", () => sendMessage(button.dataset.question));
});

faqToggle.addEventListener("click", openFaqPanel);
faqClose.addEventListener("click", closeFaqPanel);
faqOverlay.addEventListener("click", closeFaqPanel);
faqSearch.addEventListener("input", renderFaqs);

categoryButtons.forEach((button) => {
    button.addEventListener("click", () => {
        activeCategory = button.dataset.category;
        categoryButtons.forEach((item) => {
            item.setAttribute("aria-pressed", String(item === button));
        });
        renderFaqs();
    });
});

document.addEventListener("keydown", (event) => {
    if (!settingsPanel.hidden) {
        handleDialogKeys(event, settingsPanel, closeSettings);
        return;
    }
    if (faqPanel.hidden) return;
    if (event.key === "Escape") {
        closeFaqPanel();
    } else if (event.key === "Tab") {
        const candidates = Array.from(
            faqPanel.querySelectorAll("button:not([disabled]), input:not([disabled]), summary")
        ).filter((item) => item.getClientRects().length > 0);
        if (candidates.length === 0) return;
        const first = candidates[0];
        const last = candidates[candidates.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }
});

// İlk sayfa açılışında soruları arka planda yükle; yüklenemezse panel tekrar dener.
loadFaqs();


/* Ayarlar / SSS yönetimi — herhangi bir dış kütüphane gerektirmez. */
let settingsBusy = false;

function editFeedback(message, isError = false) {
    faqEditStatus.textContent = message;
    faqEditStatus.classList.toggle("error", isError);
}

function resetFaqForm() {
    faqEditForm.reset();
    editingFaqId.value = "";
    editFormTitle.textContent = "Yeni soru ekle";
    saveFaqButton.textContent = "Yeni soru kaydet";
    deleteFaqButton.hidden = true;
    editFeedback("");
}

function editExistingFaq(faq) {
    editingFaqId.value = String(faq.id);
    editQuestion.value = faq.question;
    editAnswer.value = faq.answer;
    editCategory.value = faq.category;
    editAlternatives.value = faq.alternative_questions.join("\n");
    editSourceTitle.value = faq.source_title || "";
    editSourceUrl.value = faq.source_url || "";
    editValidUntil.value = faq.valid_until || "";
    editVerificationStatus.value = faq.verification_status || "unverified";
    editFormTitle.textContent = "Soruyu düzenle";
    saveFaqButton.textContent = "Değişiklikleri kaydet";
    deleteFaqButton.hidden = false;
    editFeedback("");
    editQuestion.focus();
    editQuestion.scrollIntoView({ block: "center", behavior: "instant" });
}

function renderManageList() {
    managedFaqCount.textContent = "(" + faqs.length + ")";
    const query = manageFaqSearch.value.trim().toLocaleLowerCase("tr-TR");
    const matches = faqs.filter((faq) =>
        (faq.question + " " + faq.answer).toLocaleLowerCase("tr-TR").includes(query)
    );
    const fragment = document.createDocumentFragment();
    if (matches.length === 0) {
        const notice = document.createElement("p");
        notice.className = "faq-notice";
        notice.textContent = faqsLoaded ? "Eşleşen soru bulunamadı." : "Sorular yükleniyor...";
        fragment.appendChild(notice);
    }
    for (const faq of matches) {
        const row = document.createElement("div");
        row.className = "manage-item";
        const copy = document.createElement("div");
        copy.className = "manage-copy";
        const name = document.createElement("strong");
        name.textContent = faq.question;
        const meta = document.createElement("small");
        const verification = {unverified:"Doğrulanmadı",review_needed:"İncele",verified:"Elle doğrulandı"};
        meta.textContent = (categoryNames[faq.category] || faq.category) + " · " +
            (verification[faq.verification_status] || "Doğrulanmadı") +
            (faq.validity_status === "expired" ? " · Süresi doldu" : "");
        copy.append(name, meta);
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "Düzenle";
        button.addEventListener("click", () => editExistingFaq(faq));
        const del = document.createElement("button");
        del.type = "button";
        del.className = "manage-delete";
        del.textContent = "Sil";
        del.setAttribute("aria-label", faq.question + " kaydını sil");
        del.addEventListener("click", () => deleteFaqRecord(faq.id));
        const actions = document.createElement("div");
        actions.className = "manage-item-actions";
        actions.append(button, del);
        row.append(copy, actions);
        fragment.appendChild(row);
    }
    manageFaqList.replaceChildren(fragment);
}

function openSettings() {
    if (!faqPanel.hidden) closeFaqPanel();
    previousFocus = document.activeElement;
    settingsPanel.hidden = false;
    settingsOverlay.hidden = false;
    settingsToggle.setAttribute("aria-expanded", "true");
    document.body.classList.add("faq-open");
    if (!faqsLoaded) loadFaqs();
    renderManageList();
    loadDuplicateThreshold();
    loadSemanticSettings();
    loadReviewSettings();
    loadReviewList();
    loadFaqTrash();
    editQuestion.focus();
}

function closeSettings() {
    settingsPanel.hidden = true;
    settingsOverlay.hidden = true;
    settingsToggle.setAttribute("aria-expanded", "false");
    document.body.classList.remove("faq-open");
    settingsToggle.focus();
}

function handleDialogKeys(event, panel, close) {
    if (event.key === "Escape") {
        event.preventDefault();
        close();
    } else if (event.key === "Tab") {
        const elements = Array.from(
            panel.querySelectorAll("button:not([disabled]):not([hidden]), input:not([disabled]):not([type=hidden]), textarea:not([disabled]), select:not([disabled])")
        ).filter((el) => el.getClientRects().length > 0);
        if (elements.length === 0) return;
        const first = elements[0];
        const last = elements[elements.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }
}

function setSettingsBusy(value) {
    settingsBusy = value;
    saveFaqButton.disabled = value;
    deleteFaqButton.disabled = value;
    exportFaqButton.disabled = value;
}

async function apiWrite(url, method, payload) {
    const response = await fetch(url, {
        method: method,
        headers: { "Content-Type": "application/json" },
        body: payload ? JSON.stringify(payload) : undefined
    });
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(
            typeof data.detail === "string"
                ? data.detail : "İşlem gerçekleştirilemedi (HTTP " + response.status + ")."
        );
    }
    return response.status === 204 ? null : response.json();
}

faqEditForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (settingsBusy) return;
    const alternatives = editAlternatives.value.split(/\r?\n/)
        .map((line) => line.trim()).filter(Boolean);
    if (alternatives.length > 15 || alternatives.some((line) => line.length > 250)) {
        editFeedback("En fazla 15 alternatif soru ekleyebilirsiniz; her biri 250 karakteri geçmemeli.", true);
        return;
    }
    const payload = {
        question: editQuestion.value.trim(),
        answer: editAnswer.value.trim(),
        category: editCategory.value,
        alternative_questions: alternatives,
        source_title: editSourceTitle.value.trim(),
        source_url: editSourceUrl.value.trim(),
        valid_until: editValidUntil.value || null,
        verification_status: editVerificationStatus.value
    };
    const id = editingFaqId.value;
    setSettingsBusy(true);
    editFeedback("Kaydediliyor...");
    try {
        await apiWrite(id ? "/faqs/" + encodeURIComponent(id) : "/faqs", id ? "PUT" : "POST", payload);
        await loadFaqs();
        resetFaqForm();
        editFeedback("Kayıt başarıyla kaydedildi.");
    } catch (error) {
        editFeedback(error.message, true);
    } finally {
        setSettingsBusy(false);
    }
});

async function deleteFaqRecord(id) {
    if (!id || settingsBusy) return;
    if (!window.confirm("Bu soruyu Çöp Kutusu’na taşımak istiyor musunuz? Gerekirse Ayarlar’dan geri yükleyebilirsiniz.")) return;
    setSettingsBusy(true);
    editFeedback("Siliniyor...");
    try {
        await apiWrite("/faqs/" + encodeURIComponent(id), "DELETE");
        await loadFaqs();
        if (editingFaqId.value === String(id)) resetFaqForm();
        editFeedback("Kayıt Çöp Kutusu’na taşındı.");
        await loadFaqTrash();
    } catch (error) {
        editFeedback(error.message, true);
    } finally {
        setSettingsBusy(false);
    }
}

deleteFaqButton.addEventListener("click", () => deleteFaqRecord(editingFaqId.value));

exportFaqButton.addEventListener("click", async () => {
    if (settingsBusy) return;
    setSettingsBusy(true);
    try {
        const response = await fetch("/faqs/export");
        if (!response.ok) throw new Error("JSON yedeği alınamadı.");
        const backup = await response.json();
        const blob = new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" });
        const href = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = href;
        link.download = "faqbot-sss-yedek.json";
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(href);
        editFeedback("JSON yedeği hazırlandı.");
    } catch (error) {
        editFeedback(error.message, true);
    } finally {
        setSettingsBusy(false);
    }
});

settingsToggle.addEventListener("click", openSettings);
settingsClose.addEventListener("click", closeSettings);
settingsOverlay.addEventListener("click", closeSettings);
newFaqButton.addEventListener("click", () => { resetFaqForm(); editQuestion.focus(); });
cancelFaqButton.addEventListener("click", resetFaqForm);
manageFaqSearch.addEventListener("input", renderManageList);


/* Toplu SSS aktarımı: sunucuda denetle, kullanıcı onayından sonra ekle. */
function resetImportPreview() {
    previewReadyRecords = [];
    commitFaqImportButton.disabled = true;
    faqImportPreview.replaceChildren();
    faqImportStatus.textContent = "";
    faqImportStatus.classList.remove("error");
}
function showImportMessage(message, error = false) {
    faqImportStatus.textContent = message;
    faqImportStatus.classList.toggle("error", error);
}
function showImportRows(result) {
    const fragment = document.createDocumentFragment();
    const heading = document.createElement("div");
    heading.className = "import-summary";
    heading.textContent = "Toplam " + result.total + " · Uygun " + result.ready +
        " · Çakışan " + result.duplicate + " · Hatalı " + result.invalid;
    fragment.appendChild(heading);
    const labels = {ready:"Eklenebilir",duplicate:"Çakışan",invalid:"Hatalı"};
    for (const item of result.rows) {
        const row = document.createElement("div");
        row.className = "import-row";
        row.dataset.state = item.status;
        const title = document.createElement("strong");
        title.textContent = "Satır " + item.row_number + " · " +
            (labels[item.status] || item.status) + " · " + (item.question || "Soru yok");
        row.appendChild(title);
        if (item.reason) {
            const reason = document.createElement("small");
            reason.textContent = item.reason;
            row.appendChild(reason);
        }
        fragment.appendChild(row);
    }
    faqImportPreview.replaceChildren(fragment);
}
faqImportFile.addEventListener("change", resetImportPreview);
previewFaqImportButton.addEventListener("click", async () => {
    const file = faqImportFile.files[0];
    resetImportPreview();
    if (!file) return showImportMessage("Önce dosya seçin.", true);
    if (file.size > 2 * 1024 * 1024) return showImportMessage("En fazla 2 MB dosya.", true);
    previewFaqImportButton.disabled = true;
    showImportMessage("Dosya kontrol ediliyor...");
    try {
        const body = new FormData();
        body.append("file", file);
        const response = await fetch("/faqs/import/preview", {method:"POST", body});
        const result = await response.json();
        if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Önizleme başarısız.");
        showImportRows(result);
        previewReadyRecords = result.rows.filter(item => item.status === "ready").map(item => item.data);
        commitFaqImportButton.disabled = previewReadyRecords.length === 0;
        showImportMessage(result.ready + " satır aktarılabilir. Onaylamak için aktar düğmesine basın.");
    } catch (error) {
        showImportMessage(error.message, true);
    } finally {
        previewFaqImportButton.disabled = false;
    }
});
commitFaqImportButton.addEventListener("click", async () => {
    if (!previewReadyRecords.length || settingsBusy) return;
    if (!window.confirm(previewReadyRecords.length + " yeni SSS kaydı eklensin mi? Eski kayıtlar korunacak.")) return;
    commitFaqImportButton.disabled = true;
    showImportMessage("Yeni kayıtlar ekleniyor...");
    try {
        const response = await fetch("/faqs/import/commit", {
            method:"POST", headers:{"Content-Type":"application/json"},
            body:JSON.stringify({records:previewReadyRecords})
        });
        const data = await response.json();
        if (!response.ok) {
            const message = typeof data.detail === "string" ? data.detail :
                data.detail?.message || "Aktarım başarısız.";
            throw new Error(message);
        }
        resetImportPreview();
        faqImportFile.value = "";
        await loadFaqs();
        showImportMessage(data.inserted + " yeni soru kaydedildi.");
    } catch (error) {
        showImportMessage(error.message + " Dosyayı yeniden önizleyebilirsiniz.", true);
    }
});


/* Ayarlar > Benzer Sorular. Yüzde eşiği sohbet motorundan bağımsızdır. */
function duplicateFeedback(message, isError = false) {
    duplicateStatus.textContent = message;
    duplicateStatus.classList.toggle("error", isError);
}

function setThresholdControls(value) {
    const percent = Math.min(95, Math.max(40, Math.round(Number(value))));
    dupThresholdRange.value = String(percent);
    dupThresholdNumber.value = String(percent);
    dupThresholdLabel.textContent = "%" + percent;
}

dupThresholdRange.addEventListener("input", () => {
    setThresholdControls(dupThresholdRange.value);
    duplicateCandidates.replaceChildren();
    duplicateFeedback("Eşik değişti. Kaydedin ve tekrar tarayın.");
});
dupThresholdNumber.addEventListener("input", () => {
    const n = Number(dupThresholdNumber.value);
    if (Number.isInteger(n) && n >= 40 && n <= 95) {
        dupThresholdRange.value = String(n);
        dupThresholdLabel.textContent = "%" + n;
        duplicateCandidates.replaceChildren();
        duplicateFeedback("Eşik değişti. Kaydedin ve tekrar tarayın.");
    }
});

async function loadDuplicateThreshold() {
    try {
        const res = await fetch("/settings/duplicates");
        if (!res.ok) throw new Error("Ayarlar okunamadı");
        const data = await res.json();
        setThresholdControls(data.threshold * 100);
    } catch (error) {
        duplicateFeedback(error.message, true);
    }
}

async function saveDuplicateThreshold() {
    if (duplicateWorking) return false;
    const percent = Number(dupThresholdNumber.value);
    if (!Number.isInteger(percent) || percent < 40 || percent > 95) {
        duplicateFeedback("Benzerlik eşiği %40 ile %95 arasında tam sayı olmalıdır.", true);
        return false;
    }
    duplicateWorking = true;
    dupThresholdSave.disabled = true;
    try {
        const res = await fetch("/settings/duplicates", {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({threshold: percent / 100})
        });
        if (!res.ok) throw new Error("Eşik kaydedilemedi (HTTP " + res.status + ").");
        const data = await res.json();
        setThresholdControls(data.threshold * 100);
        duplicateCandidates.replaceChildren();
        duplicateFeedback("Eşik %" + percent + " olarak kaydedildi. Tarama yapabilirsiniz.");
        return true;
    } catch(error) {
        duplicateFeedback(error.message, true);
        return false;
    } finally {
        duplicateWorking = false;
        dupThresholdSave.disabled = false;
    }
}

dupThresholdSave.addEventListener("click", saveDuplicateThreshold);

function makeDuplicateCard(item) {
    const card = document.createElement("article");
    card.className = "duplicate-card";
    const header = document.createElement("div");
    header.className = "duplicate-card-header";
    const score = document.createElement("strong");
    score.textContent = "%" + (item.score * 100).toFixed(1) + " benzerlik";
    const note = document.createElement("span");
    note.textContent = item.same_category ? "Aynı kategori" : "Farklı kategoriler · Birleştirme kapalı";
    header.append(score, note);
    card.appendChild(header);

    const details = document.createElement("div");
    details.className = "duplicate-compare";
    for (const [side, faq] of [["Sol", item.left], ["Sağ", item.right]]) {
        const column = document.createElement("div");
        column.className = "duplicate-record";
        const title = document.createElement("strong");
        title.textContent = side + " #" + faq.id + " · " + faq.category;
        const question = document.createElement("p");
        question.textContent = faq.question;
        const answerTitle = document.createElement("small");
        answerTitle.textContent = "Kayıtlı cevap";
        const answer = document.createElement("p");
        answer.className = "duplicate-answer";
        answer.textContent = faq.answer;
        const alternatives = document.createElement("small");
        alternatives.textContent = faq.alternative_questions.length + " alternatif ifade";
        column.append(title, question, answerTitle, answer, alternatives);
        details.appendChild(column);
    }
    card.appendChild(details);
    const example = document.createElement("p");
    example.className = "duplicate-example";
    example.textContent = "Eşleşen ifadeler: " + item.example_left + " / " + item.example_right;
    card.appendChild(example);
    if (item.answers_differ) {
        const warning = document.createElement("p");
        warning.className = "duplicate-warning";
        warning.textContent = "Cevaplar farklı. Birleştirirseniz seçtiğiniz tarafın cevabı korunacak; diğer cevap birleştirme arşivine kaydedilecek.";
        card.appendChild(warning);
    }
    const actions = document.createElement("div");
    actions.className = "duplicate-actions";
    for (const [keep, remove, keptSide] of [
        [item.left, item.right, "Sol"],
        [item.right, item.left, "Sağ"]
    ]) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "settings-secondary";
        button.textContent = keptSide + " kaydı tut";
        button.disabled = !item.can_merge;
        button.addEventListener("click", () => mergeDuplicatePair(item, keep, remove));
        actions.appendChild(button);
    }
    card.appendChild(actions);
    return card;
}

function renderDuplicateList(data) {
    const wrapper = document.createDocumentFragment();
    const intro = document.createElement("p");
    intro.className = "duplicate-result-count";
    intro.textContent = data.total + " aday çift · Kayıtlı eşik %" +
        Math.round(data.threshold * 100) + (data.truncated ? " · İlk 150 aday" : "");
    wrapper.appendChild(intro);
    if (!data.candidates.length) {
        const empty = document.createElement("p");
        empty.className = "faq-notice";
        empty.textContent = "Bu eşikte benzer soru adayı bulunamadı. Eşiği düşürüp yeniden tarayabilirsiniz.";
        wrapper.appendChild(empty);
    }
    for (const item of data.candidates) wrapper.appendChild(makeDuplicateCard(item));
    duplicateCandidates.replaceChildren(wrapper);
}

async function scanDuplicatePairs() {
    if (duplicateWorking) return;
    const percent = Number(dupThresholdNumber.value);
    if (!Number.isInteger(percent) || percent < 40 || percent > 95) {
        duplicateFeedback("Önce %40–95 arasında bir eşik girin.", true);
        return;
    }
    duplicateWorking = true;
    dupScan.disabled = true;
    duplicateFeedback("Kayıtlar karşılaştırılıyor...");
    try {
        const settings = await fetch("/settings/duplicates");
        if (!settings.ok) throw new Error("Kayıtlı eşik okunamadı.");
        const saved = await settings.json();
        const methodResponse = await fetch("/settings/semantic");
        if (!methodResponse.ok) throw new Error("Benzerlik yöntemi okunamadı.");
        const methodSettings = await methodResponse.json();
        if (dupMethod.value !== methodSettings.method ||
            dupModelPath.value.trim() !== methodSettings.model_path) {
            throw new Error("Benzerlik yöntemini veya model yolunu önce kaydedin.");
        }
        if (Math.round(saved.threshold * 100) !== percent) {
            duplicateCandidates.replaceChildren();
            throw new Error("Eşik henüz kaydedilmedi. Önce 'Eşiği kaydet' düğmesini kullanın.");
        }
        const res = await fetch("/faqs/duplicates");
        if (!res.ok) throw new Error("Benzer soru taraması başarısız.");
        const data = await res.json();
        renderDuplicateList(data);
        duplicateFeedback(data.total + " aday karşılaştırma incelemeye hazır.");
    } catch(error) {
        duplicateFeedback(error.message, true);
    } finally {
        dupScan.disabled = false;
        duplicateWorking = false;
    }
}

dupScan.addEventListener("click", scanDuplicatePairs);

async function mergeDuplicatePair(item, keep, remove) {
    if (duplicateWorking || !item.can_merge) return;
    const contentDiff = item.answers_differ ?
        "\n\nCevaplar farklı. Korunan cevabı seçtiğiniz taraf belirleyecek; diğer kayıt arşivlenecek." : "";
    const approved = window.confirm(
        "Birleştirme işlemini onaylıyor musunuz?\n\n" +
        "KORUNACAK: " + keep.question + "\n" +
        "AKTARILACAK: " + remove.question + "\n\n" +
        "Diğer soru, korunan kaydın alternatif ifadelerine eklenecek." +
        contentDiff + "\n\nBu işlem otomatik geri alınamaz."
    );
    if (!approved) return;
    duplicateWorking = true;
    duplicateFeedback("Birleştirme kontrol ediliyor...");
    try {
        const response = await fetch("/faqs/duplicates/merge", {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({
                keep_id: keep.id, remove_id: remove.id,
                expected_keep: keep.id === item.left.id ?
                    item.left_fingerprint : item.right_fingerprint,
                expected_remove: remove.id === item.left.id ?
                    item.left_fingerprint : item.right_fingerprint,
                confirm: true
            })
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(typeof result.detail === "string" ?
                result.detail : "Birleştirme başarısız oldu.");
        }
        await loadFaqs();
        duplicateWorking = false;
        await scanDuplicatePairs();
        duplicateFeedback("Birleştirme kaydedildi. Tutulan kayıt #" + result.kept.id +
            ", arşiv kaydı #" + result.archive_id + ". Adaylar yeniden tarandı.");
    } catch(error) {
        duplicateFeedback(error.message, true);
    } finally {
        duplicateWorking = false;
    }
}


/* Yalnızca yerel dosyadaki embedding modeli kullanılır, çevrimiçi API yok. */
async function loadSemanticSettings() {
    try {
        const response = await fetch("/settings/semantic");
        if (!response.ok) throw new Error("Model ayarları okunamadı.");
        const settings = await response.json();
        dupMethod.value = settings.method;
        dupModelPath.value = settings.model_path;
        ownModelPathDefault = settings.default_own_model_path || "";
        v2ModelPathDefault = settings.default_v2_model_path || "";
        dupMethodStatus.textContent = settings.ready_to_load
            ? "Yerel model dosyaları kullanıma hazır (ticari kabul ayrı)."
            : "Model hazır değil. TF-IDF kullanabilir veya isteğe bağlı modeli kurabilirsiniz.";
    } catch (error) {
        dupMethodStatus.textContent = error.message;
    }
}
dupMethod.addEventListener("change", () => {
    if (dupMethod.value === "faqvec_tr" && ownModelPathDefault) {
        dupModelPath.value = ownModelPathDefault;
    } else if (dupMethod.value === "faqvec_v2" && v2ModelPathDefault) {
        dupModelPath.value = v2ModelPathDefault;
    }
    dupMethodStatus.textContent = "Yöntemi kaydedip yeniden tarayın. FAQVec-TR için yerel eğitim gerekir.";
});

dupMethodSave.addEventListener("click", async () => {
    const response = await fetch("/settings/semantic", {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({method: dupMethod.value, model_path: dupModelPath.value.trim()})
    });
    const data = await response.json();
    if (!response.ok) {
        dupMethodStatus.textContent = typeof data.detail === "string" ? data.detail :
            "Model ayarları kaydedilemedi.";
        return;
    }
    duplicateCandidates.replaceChildren();
    dupMethodStatus.textContent = data.method === "faqvec_v2"
        ? "FAQVec-TR v0.2 seçildi; değerlendirmeyi bağımsız veriyle tamamlayın."
        : data.method === "faqvec_tr"
        ? "FAQVec-TR yerel model seçildi. Yeni embedding skorlarını gözle inceleyin."
        : data.method === "embedding"
        ? "MiniLM seçildi. Benzerleri tara düğmesine basın."
        : "TF-IDF yöntemi kaydedildi.";
});


/* Yerel ve isteğe bağlı eşleşme inceleme paneli */
function reviewMessage(text, error = false) {
    reviewStatus.textContent = text;
    reviewStatus.classList.toggle("error", error);
}

async function reviewFetchJson(path, options = {}) {
    const response = await fetch(path, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const detail = data.detail;
        throw new Error(typeof detail === "string" ? detail : "İstek başarısız: HTTP " + response.status);
    }
    return data;
}

async function loadReviewSettings() {
    try {
        const data = await reviewFetchJson("/reviews/settings");
        reviewLoggingToggle.checked = data.enabled;
    } catch (error) {
        reviewMessage(error.message, true);
    }
}

reviewLoggingToggle.addEventListener("change", async () => {
    const enabled = reviewLoggingToggle.checked;
    reviewLoggingToggle.disabled = true;
    try {
        const data = await reviewFetchJson("/reviews/settings", {
            method: "PUT", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({enabled})
        });
        reviewLoggingToggle.checked = data.enabled;
        reviewMessage(data.enabled
            ? "Yeni sohbetlerin yerel kayıtları açık. Kişisel bilgi içeren sorular sormayın."
            : "Sohbet günlüğüne yeni kayıt eklenmeyecek.");
    } catch (error) {
        reviewLoggingToggle.checked = !enabled;
        reviewMessage(error.message, true);
    } finally {
        reviewLoggingToggle.disabled = false;
    }
});

function buildReviewItem(item) {
    const box = document.createElement("article");
    box.className = "review-item";
    const h = document.createElement("strong");
    h.textContent = "#" + item.id + " · " + item.created_at + " · " +
        item.match_method.toUpperCase() + " · Skor: %" +
        (item.match_score * 100).toFixed(1);
    box.appendChild(h);
    for (const [label, value] of [
        ["Sorulan", item.question],
        ["Eşleşen SSS", item.matched_question || "Hiçbir soru eşleşmedi"],
        ["Verilen cevap", item.answer],
    ]) {
        const line = document.createElement("p");
        const title = document.createElement("b");
        title.textContent = label + ": ";
        line.append(title, document.createTextNode(value));
        box.appendChild(line);
    }
    const grid = document.createElement("div");
    grid.className = "review-edit-grid";
    const statusLabel = document.createElement("label");
    statusLabel.textContent = "İnceleme sonucu";
    const state = document.createElement("select");
    state.setAttribute("aria-label", "İnceleme sonucu");
    for (const [value, label] of [
        ["pending","Beklemede"],["correct","Doğru"],
        ["incorrect","Yanlış"],["unsure","Kararsız"],
    ]) {
        const opt = document.createElement("option");
        opt.value = value; opt.textContent = label;
        state.appendChild(opt);
    }
    state.value = item.review_status;
    const expectedLabel = document.createElement("label");
    expectedLabel.textContent = "Beklenen doğru cevap";
    const expected = document.createElement("select");
    expected.setAttribute("aria-label", "Beklenen doğru SSS");
    const fallback = document.createElement("option");
    fallback.value = ""; fallback.textContent = "Cevap verilmemeliydi (fallback)";
    expected.appendChild(fallback);
    for (const faq of faqs) {
        const option = document.createElement("option");
        option.value = String(faq.id);
        option.textContent = "#" + faq.id + " · " + faq.question;
        expected.appendChild(option);
    }
    expected.value = item.expected_faq_id === null ? "" : String(item.expected_faq_id);
    const noteLabel = document.createElement("label");
    noteLabel.textContent = "İnceleme notu";
    const note = document.createElement("textarea");
    note.rows = 2; note.maxLength = 500;
    note.value = item.review_note || "";
    const save = document.createElement("button");
    save.type = "button"; save.className = "settings-primary";
    save.textContent = "Değerlendirmeyi kaydet";
    const updateVisibility = () => {
        expected.disabled = state.value !== "incorrect";
        if (state.value === "correct") expected.value = item.matched_faq_id === null
            ? "" : String(item.matched_faq_id);
    };
    state.addEventListener("change", updateVisibility);
    updateVisibility();
    save.addEventListener("click", async () => {
        save.disabled = true;
        try {
            const data = await reviewFetchJson("/reviews/" + item.id, {
                method: "PATCH", headers: {"Content-Type":"application/json"},
                body: JSON.stringify({
                    status: state.value,
                    expected_faq_id: expected.value ? Number(expected.value) : null,
                    note: note.value.trim(),
                }),
            });
            reviewMessage("Kayıt #" + data.id + " değerlendirildi.");
            await loadReviewList();
        } catch (error) {
            reviewMessage(error.message, true);
            save.disabled = false;
        }
    });
    grid.append(statusLabel, state, expectedLabel, expected, noteLabel, note, save);
    box.appendChild(grid);
    return box;
}

async function loadReviewList() {
    reviewRefresh.disabled = true;
    try {
        if (!faqsLoaded) await loadFaqs();
        const data = await reviewFetchJson(
            "/reviews?status=" + encodeURIComponent(reviewStatusFilter.value) + "&limit=100"
        );
        const counts = data.counts;
        reviewCounts.textContent = "Toplam " + data.total +
            " · Bekleyen " + counts.pending + " · Doğru " + counts.correct +
            " · Yanlış " + counts.incorrect + " · Kararsız " + counts.unsure;
        const fragment = document.createDocumentFragment();
        if (data.rows.length === 0) {
            const p = document.createElement("p");
            p.className = "faq-notice";
            p.textContent = "Bu filtrede kayıt yok. Önce yerel günlüğü açıp sohbet edin.";
            fragment.appendChild(p);
        }
        for (const item of data.rows) fragment.appendChild(buildReviewItem(item));
        reviewItems.replaceChildren(fragment);
    } catch (error) {
        reviewMessage(error.message, true);
    } finally {
        reviewRefresh.disabled = false;
    }
}

reviewRefresh.addEventListener("click", loadReviewList);
reviewStatusFilter.addEventListener("change", loadReviewList);

reviewDeleteAll.addEventListener("click", async () => {
    if (!window.confirm("Tüm sohbet inceleme günlüğü kalıcı olarak silinsin mi?")) return;
    if (!window.confirm("Son onay: Bu işlem bütün etiketleri ve değerlendirme verilerini siler.")) return;
    reviewDeleteAll.disabled = true;
    try {
        const data = await reviewFetchJson("/reviews", {
            method: "DELETE", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({confirm:true})
        });
        await loadReviewList();
        reviewEvaluationResult.replaceChildren();
        reviewMessage(data.deleted + " inceleme kaydı silindi.");
    } catch (error) {
        reviewMessage(error.message, true);
    } finally {
        reviewDeleteAll.disabled = false;
    }
});

function makeMetric(label, entry) {
    const el = document.createElement("p");
    el.className = "review-metric";
    el.textContent = label + ": " +
        (entry && entry.status === "unavailable" ? "Kurulu değil: " + entry.reason :
        entry && entry.status === "not_requested" ? "Seçilmedi" :
        entry && entry.accuracy !== null ?
        "%" + (entry.accuracy * 100).toFixed(1) +
        " (" + entry.correct + "/" + entry.total + ", eşik %" +
        (entry.threshold * 100).toFixed(0) + ")" :
        "Yeterli insan etiketi yok");
    return el;
}

reviewEvaluate.addEventListener("click", async () => {
    reviewEvaluate.disabled = true;
    reviewMessage("İnsan etiketli sorular güncel SSS tabanında karşılaştırılıyor...");
    try {
        const result = await reviewFetchJson("/reviews/evaluate", {
            method: "POST", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({include_embedding:reviewIncludeEmbedding.checked})
        });
        const fragment = document.createDocumentFragment();
        const intro = document.createElement("p");
        intro.textContent = "İncelenen " + result.reviewed +
            " · Karşılaştırılan " + result.compared +
            " · Silinen hedef nedeniyle atlanan " + result.skipped_missing_faq;
        fragment.append(intro, makeMetric("TF-IDF", result.tfidf),
            makeMetric("Yerel embedding", result.embedding));
        const note = document.createElement("small");
        note.textContent = result.note;
        fragment.appendChild(note);
        reviewEvaluationResult.replaceChildren(fragment);
        reviewMessage("Değerlendirme hazır.");
    } catch (error) {
        reviewMessage(error.message, true);
    } finally {
        reviewEvaluate.disabled = false;
    }
});


/* v1.6: Silinen FAQ kayıtları, geri yükleme ve çakışma geri bildirimi */
function showTrashMessage(message, error = false) {
    trashStatus.textContent = message;
    trashStatus.classList.toggle("error", error);
}

function renderTrashItems() {
    const query = trashSearch.value.trim().toLocaleLowerCase("tr-TR");
    const matches = deletedFaqs.filter(faq =>
        (faq.question + " " + faq.answer).toLocaleLowerCase("tr-TR").includes(query)
    );
    trashCount.textContent = deletedFaqs.length + " silinmiş kayıt · " +
        matches.length + " görüntüleniyor";
    const nodes = document.createDocumentFragment();
    if (!matches.length) {
        const empty = document.createElement("p");
        empty.className = "faq-notice";
        empty.textContent = deletedFaqs.length === 0 ?
            "Çöp kutusu boş." : "Aramanıza uygun silinmiş soru bulunamadı.";
        nodes.appendChild(empty);
    }
    for (const faq of matches) {
        const card = document.createElement("article");
        card.className = "trash-item";
        const title = document.createElement("strong");
        title.textContent = "#" + faq.id + " · " + faq.question;
        const when = document.createElement("small");
        when.textContent = "Silinme zamanı (UTC): " + faq.deleted_at +
            " · Kategori: " + (categoryNames[faq.category] || faq.category);
        const answer = document.createElement("p");
        answer.textContent = faq.answer;
        const meta = document.createElement("small");
        meta.textContent = "Alternatif ifadeler: " + faq.alternative_questions.length +
            (faq.source_title ? " · Kaynak: " + faq.source_title : "") +
            " · Durum: " + faq.verification_status;
        const action = document.createElement("button");
        action.type = "button";
        action.className = "settings-primary";
        action.textContent = "Geri yükle";
        action.setAttribute("aria-label", faq.question + " kaydını geri yükle");
        action.addEventListener("click", () => restoreDeletedFaq(faq.id));
        card.append(title, when, answer, meta, action);
        nodes.appendChild(card);
    }
    trashItems.replaceChildren(nodes);
}

async function loadFaqTrash() {
    refreshTrashButton.disabled = true;
    try {
        const response = await fetch("/faqs/trash");
        const data = await response.json();
        if (!response.ok) throw new Error(
            typeof data.detail === "string" ? data.detail : "Çöp kutusu alınamadı."
        );
        deletedFaqs = data.faqs || [];
        renderTrashItems();
    } catch (error) {
        showTrashMessage(error.message, true);
    } finally {
        refreshTrashButton.disabled = false;
    }
}

async function restoreDeletedFaq(id) {
    if (trashBusy || settingsBusy) return;
    const candidate = deletedFaqs.find(faq => faq.id === id);
    if (!candidate) return;
    if (!window.confirm("Bu soruyu yeniden etkinleştirmek istiyor musunuz?\n\n" +
        candidate.question + "\n\nEski cevap, kaynak ve alternatif ifadeler korunacaktır.")) return;
    trashBusy = true;
    showTrashMessage("Çakışmalar kontrol ediliyor...");
    try {
        const response = await fetch("/faqs/trash/" + encodeURIComponent(id) + "/restore", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({confirm: true})
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(typeof data.detail === "string" ?
                data.detail : "Geri yükleme başarısız oldu.");
        }
        await loadFaqs();
        await loadFaqTrash();
        showTrashMessage("Kayıt #" + data.id + " geri yüklendi ve aktif SSS listesine eklendi.");
    } catch (error) {
        showTrashMessage(error.message, true);
    } finally {
        trashBusy = false;
    }
}

refreshTrashButton.addEventListener("click", loadFaqTrash);
trashSearch.addEventListener("input", renderTrashItems);



/* P1 / P2: yalnız localhost üzerinde çalışan yerel ürün prototipleri. */
const supportSection = document.getElementById("supportSection");
const supportForm = document.getElementById("supportForm");
const supportSubject = document.getElementById("supportSubject");
const supportDetail = document.getElementById("supportDetail");
const supportMessage = document.getElementById("supportMessage");
const supportTickets = document.getElementById("supportTickets");
const loadSupportTicketsButton = document.getElementById("loadSupportTickets");
const demoOrderForm = document.getElementById("demoOrderForm");
const demoOrderCode = document.getElementById("demoOrderCode");
const demoOrderResult = document.getElementById("demoOrderResult");
const demoReturnForm = document.getElementById("demoReturnForm");
const demoReturnReason = document.getElementById("demoReturnReason");
const demoOrderMessage = document.getElementById("demoOrderMessage");
const demoReturns = document.getElementById("demoReturns");
const loadDemoReturnsButton = document.getElementById("loadDemoReturns");

async function customerApi(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: { "Content-Type": "application/json", ...(options.headers || {}) }
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail :
            "İşlem gerçekleştirilemedi (" + response.status + ").");
    }
    return data;
}

function makeCustomerText(tagName, value, cssClass = "") {
    const item = document.createElement(tagName);
    item.textContent = value;
    if (cssClass) item.className = cssClass;
    return item;
}

function showAnswerTools(bubble, data, question) {
    const actions = document.createElement("div");
    actions.className = "answer-tools";
    if (Array.isArray(data.suggestions) && data.suggestions.length) {
        const title = makeCustomerText("small",
            "BUNU MU DEMEK İSTEDİNİZ?", "tool-notice");
        actions.appendChild(title);
        for (const item of data.suggestions) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "answer-suggestion";
            button.textContent = item.question;
            button.addEventListener("click", () => sendMessage(item.question));
            actions.appendChild(button);
        }
    }

    const controls = document.createElement("div");
    controls.className = "answer-actions";
    const helpful = makeCustomerText("span", "Bu yanıt faydalı mı?");
    controls.appendChild(helpful);
    for (const [good, label, accessible] of [[true, "👍 Like", "Beğendim"], [false, "👎 Dislike", "Beğenmedim"]]) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        button.className = "answer-action-button";
        button.setAttribute("aria-label", accessible);
        button.setAttribute("title", accessible);
        button.addEventListener("click", async () => {
            for (const b of controls.querySelectorAll("button")) b.disabled = true;
            try {
                await customerApi("/feedback", {
                    method: "POST",
                    body: JSON.stringify({
                        faq_id: Number.isInteger(data.faq_id) ? data.faq_id : null,
                        helpful: good
                    })
                });
                controls.replaceChildren(
                    makeCustomerText("span", "Geri bildiriminiz yerel olarak kaydedildi.")
                );
            } catch (error) {
                for (const b of controls.querySelectorAll("button")) b.disabled = false;
                status.textContent = error.message;
            }
        });
        controls.appendChild(button);
    }
    actions.appendChild(controls);

    if (data.match_type === "none") {
        const ticket = document.createElement("button");
        ticket.className = "answer-ticket-button";
        ticket.type = "button";
        ticket.textContent = "Sorunum çözülmedi — destek talebi oluştur";
        ticket.addEventListener("click", () => {
            supportSection.open = true;
            // Önceki mesajı otomatik kaydetme: kullanıcı yeni metni kendisi onaylar.
            supportSubject.value = "Sorum cevaplanmadı";
            supportMessage.textContent =
                "Bu talep yalnız bilgisayarınızda saklanır; gerçek bir temsilciye gönderilmez.";
            supportSubject.focus();
        });
        actions.appendChild(ticket);
    }
    bubble.appendChild(actions);
}

function createStatusSelector(value, choices, updateFn) {
    const select = document.createElement("select");
    select.setAttribute("aria-label", "Yerel demo durumunu değiştir");
    for (const [key, label] of choices) {
        const option = document.createElement("option");
        option.value = key; option.textContent = label;
        select.appendChild(option);
    }
    select.value = value;
    select.addEventListener("change", async () => {
        select.disabled = true;
        try {
            await updateFn(select.value);
        } catch (error) {
            status.textContent = error.message;
            select.value = value;
        } finally {
            select.disabled = false;
        }
    });
    return select;
}

const TICKET_STATUSES = [
    ["open", "Açık"], ["in_progress", "İnceleniyor"], ["resolved", "Çözüldü"]
];
const RETURN_STATUSES = [
    ["requested", "Talep alındı"], ["reviewing", "İnceleniyor"],
    ["approved", "Onaylandı"], ["rejected", "Reddedildi"]
];

function ticketState(value) {
    return TICKET_STATUSES.find(([key]) => key === value)?.[1] || value;
}
function returnState(value) {
    return RETURN_STATUSES.find(([key]) => key === value)?.[1] || value;
}

async function renderSupportTickets() {
    const data = await customerApi("/support/tickets");
    const frag = document.createDocumentFragment();
    if (!data.tickets.length) {
        frag.appendChild(makeCustomerText("p", "Henüz yerel destek talebi yok."));
    }
    for (const item of data.tickets) {
        const card = document.createElement("article");
        card.className = "customer-mini-card";
        card.appendChild(makeCustomerText("strong", item.ticket_code + " · " + item.subject));
        card.appendChild(makeCustomerText("small",
            "Durum: " + ticketState(item.status) + " · Oluşturulma: " +
            item.created_at.slice(0, 16).replace("T", " ") + " (UTC)"));
        if (item.detail) card.appendChild(makeCustomerText("p", item.detail));
        if (Array.isArray(item.history)) {
            const history = document.createElement("ol");
            history.className = "customer-history";
            for (const record of item.history) {
                history.appendChild(makeCustomerText("li",
                    ticketState(record.status) + " · " +
                    record.created_at.slice(0,16).replace("T", " ") + " UTC"));
            }
            card.appendChild(history);
        }
        card.appendChild(createStatusSelector(item.status, TICKET_STATUSES,
            async (newStatus) => {
                await customerApi("/support/tickets/" + item.id, {
                    method: "PATCH", body: JSON.stringify({ status: newStatus })
                });
                await renderSupportTickets();
            }));
        frag.appendChild(card);
    }
    supportTickets.replaceChildren(frag);
}

supportForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = supportForm.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
        const saved = await customerApi("/support/tickets", {
            method: "POST",
            body: JSON.stringify({
                subject: supportSubject.value.trim(),
                detail: supportDetail.value.trim()
            })
        });
        supportMessage.textContent = "Yerel destek bileti oluşturuldu: " +
            saved.ticket_code + ". Gerçek destek ekibine gönderilmedi.";
        supportForm.reset();
        await renderSupportTickets();
    } catch (error) {
        supportMessage.textContent = error.message;
    } finally {
        button.disabled = false;
    }
});

loadSupportTicketsButton.addEventListener("click", () =>
    renderSupportTickets().catch((error) => {
        supportMessage.textContent = error.message;
    })
);

demoOrderForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    demoReturnForm.hidden = true;
    demoOrderResult.replaceChildren();
    demoOrderMessage.textContent = "";
    try {
        const data = await customerApi("/demo/orders/" +
            encodeURIComponent(demoOrderCode.value));
        const card = document.createElement("article");
        card.className = "customer-mini-card";
        card.appendChild(makeCustomerText("strong",
            data.code + " — " + data.item + " (KURGUSAL)"));
        const orderLabels = {
            preparing: "Hazırlanıyor", shipped: "Kargoya verildi",
            delivered: "Teslim edildi"
        };
        const shipmentLabels = {
            not_shipped: "Henüz kargoya verilmedi",
            in_transit: "Kurgusal taşıma sürecinde",
            delivered: "Kurgusal teslim edildi"
        };
        card.appendChild(makeCustomerText("p",
            "Sipariş: " + (orderLabels[data.status] || data.status) +
            " · Kargo: " + (shipmentLabels[data.shipment] || data.shipment)));
        const metadata = data.shipment_metadata;
        const tracking = makeCustomerText("p",
            "Sipariş kodu: " + data.order_metadata.order_code +
            " · Ürün: " + data.order_metadata.product_code +
            " · Kargo takip: " + metadata.tracking_id);
        tracking.className = "customer-shipment-meta";
        card.appendChild(tracking);
        card.appendChild(makeCustomerText("small",
            "Taşıyıcı: " + metadata.carrier + " · Son olay: " +
            metadata.last_updated_at.replace("T", " ").slice(0, 16) + " UTC"));
        const header = makeCustomerText("strong", "Kargo zaman çizelgesi");
        card.appendChild(header);
        const list = document.createElement("ol");
        list.className = "shipment-timeline";
        for (const ev of data.events) {
            if (ev.order_code !== data.code ||
                    ev.tracking_id !== metadata.tracking_id) {
                throw new Error("Sipariş ve kargo metadatası eşleşmiyor.");
            }
            const event = document.createElement("li");
            event.appendChild(makeCustomerText("strong", ev.label));
            event.appendChild(makeCustomerText("small",
                ev.occurred_at.replace("T", " ").slice(0, 16) +
                " UTC · " + ev.event_id));
            list.appendChild(event);
        }
        card.appendChild(list);
        if (data.return_request) {
            card.appendChild(makeCustomerText("p",
                "Bu siparişe bağlı iade talebi #" + data.return_request.id +
                " · " + returnState(data.return_request.status)));
        }
        demoOrderResult.replaceChildren(card);
        demoReturnForm.hidden = data.status !== "delivered" ||
            Boolean(data.return_request);
    } catch (error) {
        demoOrderMessage.textContent = error.message;
    }
});

demoReturnForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = demoReturnForm.querySelector("button");
    button.disabled = true;
    try {
        const row = await customerApi("/demo/returns", {
            method: "POST",
            body: JSON.stringify({
                order_code: demoOrderCode.value,
                reason: demoReturnReason.value
            })
        });
        if (!row.order_ref || row.order_ref.order_code !== demoOrderCode.value) {
            throw new Error("İade ile sipariş referansı eşleşmedi.");
        }
        demoOrderMessage.textContent = row.return_code +
            " oluşturuldu. Sipariş: " + row.order_ref.order_code +
            " · Durum: " + returnState(row.status) + ".";
        demoReturnForm.hidden = true;
        await renderDemoReturns();
        demoOrderForm.requestSubmit();
    } catch (error) {
        demoOrderMessage.textContent = error.message;
    } finally {
        button.disabled = false;
    }
});

async function renderDemoReturns() {
    const data = await customerApi("/demo/returns");
    const frag = document.createDocumentFragment();
    if (!data.returns.length) {
        frag.appendChild(makeCustomerText("p", "Henüz demo iade talebi yok."));
    }
    for (const item of data.returns) {
        const card = document.createElement("article");
        card.className = "customer-mini-card";
        card.appendChild(makeCustomerText("strong",
            item.return_code + " · " + item.order_ref.product));
        card.appendChild(makeCustomerText("small",
            "Sipariş: " + item.order_ref.order_code +
            " · Kargo takip: " + item.order_ref.tracking_id +
            " · Durum: " + returnState(item.status) +
            " · Neden: " + item.reason));
        if (Array.isArray(item.history)) {
            const history = document.createElement("ol");
            history.className = "customer-history";
            for (const record of item.history) {
                history.appendChild(makeCustomerText("li",
                    returnState(record.status) + " · " +
                    record.created_at.slice(0,16).replace("T", " ") + " UTC"));
            }
            card.appendChild(history);
        }
        const viewOrder = document.createElement("button");
        viewOrder.type = "button";
        viewOrder.className = "settings-secondary";
        viewOrder.textContent = "Bağlı siparişi göster";
        viewOrder.addEventListener("click", () => {
            demoOrderCode.value = item.order_ref.order_code;
            demoOrderForm.requestSubmit();
        });
        card.appendChild(viewOrder);
        card.appendChild(createStatusSelector(item.status, RETURN_STATUSES,
            async (newStatus) => {
                await customerApi("/demo/returns/" + item.id, {
                    method: "PATCH", body: JSON.stringify({status: newStatus})
                });
                await renderDemoReturns();
            }));
        frag.appendChild(card);
    }
    demoReturns.replaceChildren(frag);
}

loadDemoReturnsButton.addEventListener("click", () =>
    renderDemoReturns().catch((error) => {
        demoOrderMessage.textContent = error.message;
    })
);

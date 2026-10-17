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

function addMessage(text, role, category) {
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
    row.appendChild(bubble);
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
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
        addMessage(data.answer, "bot", data.category);
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
        meta.textContent = categoryNames[faq.category] || faq.category;
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
        alternative_questions: alternatives
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
    if (!window.confirm("Bu soru ve cevap silinsin mi? (Geri yükleme daha sonraki aşamada eklenecek.)")) return;
    setSettingsBusy(true);
    editFeedback("Siliniyor...");
    try {
        await apiWrite("/faqs/" + encodeURIComponent(id), "DELETE");
        await loadFaqs();
        if (editingFaqId.value === String(id)) resetFaqForm();
        editFeedback("Kayıt silindi.");
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

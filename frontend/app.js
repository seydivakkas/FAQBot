"use strict";

const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const messages = document.getElementById("chatMessages");
const status = document.getElementById("status");
const shortcuts = document.querySelectorAll("[data-question]");

const faqToggle = document.getElementById("faqToggle");
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
    hesap: "Hesap / Sipariş"
};
const categoryOrder = ["kargo", "iade", "odeme", "hesap"];

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
        faqMeta.textContent = faqs.length + " soru · 4 kategori";
        renderFaqs();
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

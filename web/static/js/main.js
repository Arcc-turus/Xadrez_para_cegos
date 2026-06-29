(function () {
    "use strict";

    const socket = typeof io === "function" ? io() : null;

    const $ = (id) => document.getElementById(id);

    const phaseSelect = $("phaseSelect");
    const phaseFeed = $("phaseFeed");
    const cameraSelect = $("cameraSelect");
    const btnSelectCamera = $("btnSelectCamera");

    const videoFeed = $("videoFeed");
    const videoWrapper = $("videoWrapper");
    const overlay = $("overlay");
    const overlayContent = $("overlayContent");
    const overlayText = $("overlayText");
    const overlayHint = $("overlayHint");
    const crosshairCursor = $("crosshairCursor");
    const markersContainer = $("markersContainer");

    const maskFeed = $("maskFeed");
    const maskWrapper = $("maskWrapper");
    const btnToggleMask = $("btnToggleMask");

    const controlsPreCal = $("controlsPreCal");
    const controlsCalibrating = $("controlsCalibrating");
    const controlsPostCal = $("controlsPostCal");
    const controlsTracking = $("controlsTracking");

    const btnCalibrate = $("btnCalibrate");
    const calibrationStepInfo = $("calibrationStepInfo");
    const btnUndoPoint = $("btnUndoPoint");
    const btnResetCalibration = $("btnResetCalibration");
    const btnSaveRef = $("btnSaveRef");
    const btnCalibrateAgain = $("btnCalibrateAgain");
    const btnStopTrack = $("btnStopTrack");
    const btnVoice = $("btnVoice");
    const btnVoiceConfig = $("btnVoiceConfig");
    const btnUndoMove = $("btnUndoMove");
    const btnResetGame = $("btnResetGame");

    const calibrationModal = $("calibrationModal");
    const btnManual = $("btnManual");
    const btnAuto = $("btnAuto");
    const btnCancelModal = $("btnCancelModal");

    const voiceModal = $("voiceModal");
    const cbVoiceActive = $("cbVoiceActive");
    const cbPhonetic = $("cbPhonetic");
    const voiceSlider = $("voiceSlider");
    const voiceSpeedValue = $("voiceSpeedValue");
    const btnTestVoice = $("btnTestVoice");
    const btnCloseVoice = $("btnCloseVoice");

    const history = $("history");
    const historyList = $("historyList");
    const alertsDiv = $("alerts");
    const statusCamera = $("statusCamera");
    const statusCalibrated = $("statusCalibrated");
    const statusTracking = $("statusTracking");
    const statusVoice = $("statusVoice");
    const fenText = $("fenText");
    const turnText = $("turnText");

    let calibrating = false;
    let calibrationMode = "";
    let clickCount = 0;
    let tracking = false;
    let referenceSaved = false;
    let calibrated = false;
    let voiceActive = true;
    let voiceSpeed = 1.0;
    let phonetic = false;
    let historico = [];
    let markerPositions = [];
    let showMask = false;
    let selectedCamera = "Aguardando";
    let trackingStatusLabel = null;

    async function api(url, options) {
        const res = await fetch(url, options || {});
        let data = {};
        try {
            data = await res.json();
        } catch (_) {
            data = {};
        }
        if (!res.ok || data.ok === false) {
            throw new Error(data.error || "Não foi possível concluir a ação.");
        }
        return data;
    }

    async function loadCameras() {
        cameraSelect.innerHTML = '<option value="">Procurando câmeras...</option>';
        btnSelectCamera.disabled = true;
        try {
            const data = await api("/api/cameras");
            cameraSelect.innerHTML = "";

            if (!data.cameras || data.cameras.length === 0) {
                cameraSelect.innerHTML = '<option value="">Nenhuma câmera encontrada</option>';
                showAlert("Nenhuma câmera encontrada. Verifique a conexão e recarregue a página.", "error");
                return;
            }

            data.cameras.forEach(function (cam) {
                const opt = document.createElement("option");
                opt.value = cam.index;
                opt.textContent = `${cam.name || "Câmera " + cam.index} (${cam.width || "?"}x${cam.height || "?"})`;
                cameraSelect.appendChild(opt);
            });

            btnSelectCamera.disabled = false;
            showAlert(`${data.cameras.length} câmera(s) encontrada(s).`, "info");
        } catch (err) {
            cameraSelect.innerHTML = '<option value="">Erro ao carregar</option>';
            showAlert(err.message || "Erro ao carregar câmeras.", "error");
        }
    }

    btnSelectCamera.addEventListener("click", async function () {
        const idx = cameraSelect.value;
        if (idx === "") return;

        setButtonBusy(btnSelectCamera, true, "Abrindo...");
        try {
            const data = await api("/api/select_camera", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ index: parseInt(idx, 10) }),
            });
            selectedCamera = data.info && data.info.name ? data.info.name : `Câmera ${idx}`;
            phaseSelect.style.display = "none";
            phaseFeed.style.display = "grid";
            videoFeed.src = `/video_feed?t=${Date.now()}`;
            showPhase("preCal");
            showAlert(`${selectedCamera} ativa.`, "success");
            await loadStatus();
            await loadBoard();
        } catch (err) {
            showAlert(err.message, "error");
        } finally {
            setButtonBusy(btnSelectCamera, false, "Selecionar");
        }
    });

    function showPhase(phase) {
        controlsPreCal.style.display = phase === "preCal" ? "flex" : "none";
        controlsCalibrating.style.display = phase === "calibrating" ? "flex" : "none";
        controlsPostCal.style.display = phase === "postCal" ? "flex" : "none";
        controlsTracking.style.display = phase === "tracking" ? "flex" : "none";
        history.style.display = phase === "tracking" ? "" : "none";
        updateStatusCards();
    }

    btnCalibrate.addEventListener("click", function () {
        calibrationModal.style.display = "flex";
    });

    btnManual.addEventListener("click", function () {
        calibrationModal.style.display = "none";
        startCalibration("manual");
    });

    btnAuto.addEventListener("click", function () {
        calibrationModal.style.display = "none";
        startCalibration("auto");
    });

    btnCancelModal.addEventListener("click", function () {
        calibrationModal.style.display = "none";
    });

    async function startCalibration(modo) {
        calibrating = true;
        calibrationMode = modo;
        clickCount = 0;
        markerPositions = [];
        markersContainer.innerHTML = "";
        referenceSaved = false;

        overlay.classList.add("active");
        showPhase("calibrating");
        updateCalibrationInfo();

        if (modo === "manual") {
            overlayContent.style.display = "block";
            overlayText.textContent = "Calibração manual";
            overlayHint.textContent = "Clique nos quatro cantos do tabuleiro, em qualquer ordem.";
            crosshairCursor.style.display = "block";
        } else {
            overlayContent.style.display = "block";
            overlayText.textContent = "Calibração automática";
            overlayHint.textContent = "Tentando localizar o tabuleiro...";
            crosshairCursor.style.display = "none";
        }

        try {
            await api("/api/calibration/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ modo: modo }),
            });
            if (modo === "auto") {
                await doAutoCalibration();
            }
        } catch (err) {
            cancelCalibration(false);
            showAlert(err.message, "error");
        }
    }

    function updateCalibrationInfo() {
        calibrationStepInfo.textContent = `Ponto ${clickCount} de 4`;
    }

    videoWrapper.addEventListener("mousemove", function (e) {
        if (!calibrating || calibrationMode !== "manual") return;
        const feedRect = videoFeed.getBoundingClientRect();
        if (!isInside(e, feedRect)) {
            crosshairCursor.style.display = "none";
            return;
        }
        crosshairCursor.style.display = "block";
        crosshairCursor.style.left = `${e.clientX - feedRect.left}px`;
        crosshairCursor.style.top = `${e.clientY - feedRect.top}px`;
    });

    videoWrapper.addEventListener("mouseleave", function () {
        crosshairCursor.style.display = "none";
    });

    videoWrapper.addEventListener("click", async function (e) {
        if (!calibrating || calibrationMode !== "manual" || clickCount >= 4) return;
        const feedRect = videoFeed.getBoundingClientRect();
        if (!isInside(e, feedRect)) return;

        const clickX = e.clientX - feedRect.left;
        const clickY = e.clientY - feedRect.top;
        const naturalWidth = videoFeed.naturalWidth || feedRect.width;
        const naturalHeight = videoFeed.naturalHeight || feedRect.height;
        const realX = Math.round(clickX * (naturalWidth / feedRect.width));
        const realY = Math.round(clickY * (naturalHeight / feedRect.height));

        try {
            const data = await api("/api/calibration/manual_click", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ x: realX, y: realY }),
            });
            clickCount = data.count || clickCount + 1;
            markerPositions.push({ x: clickX, y: clickY });
            renderMarkers();
            updateCalibrationInfo();
            if (data.complete) {
                finishCalibration("Calibração concluída!", "success");
            }
        } catch (err) {
            showAlert(err.message, "error");
        }
    });

    function isInside(event, rect) {
        return event.clientX >= rect.left && event.clientX <= rect.right && event.clientY >= rect.top && event.clientY <= rect.bottom;
    }

    function renderMarkers() {
        markersContainer.innerHTML = "";
        markerPositions.forEach(function (pos, i) {
            addCrosshairMarker(pos.x, pos.y, i + 1);
        });
    }

    function addCrosshairMarker(x, y, num) {
        const marker = document.createElement("div");
        marker.className = "calibration-marker";
        marker.style.left = `${x}px`;
        marker.style.top = `${y}px`;
        marker.innerHTML = '<div class="line-h"></div><div class="line-v"></div><div class="dot"></div><div class="label">' + num + '</div>';
        markersContainer.appendChild(marker);
    }

    btnUndoPoint.addEventListener("click", async function () {
        if (!calibrating || clickCount === 0) return;
        try {
            const data = await api("/api/calibration/undo_point", { method: "POST" });
            clickCount = data.count || 0;
            markerPositions.pop();
            renderMarkers();
            updateCalibrationInfo();
        } catch (err) {
            showAlert(err.message, "error");
        }
    });

    btnResetCalibration.addEventListener("click", function () {
        cancelCalibration(true);
    });

    function finishCalibration(msg, type) {
        if (!calibrating && calibrated) return;
        overlay.classList.remove("active");
        overlayContent.style.display = "none";
        crosshairCursor.style.display = "none";
        calibrating = false;
        calibrated = true;
        markerPositions = [];
        markersContainer.innerHTML = "";
        showAlert(msg, type);
        showPhase("postCal");
        loadStatus();
    }

    async function cancelCalibration(callServer) {
        if (callServer) {
            try { await api("/api/calibration/cancel", { method: "POST" }); } catch (_) {}
        }
        overlay.classList.remove("active");
        overlayContent.style.display = "none";
        crosshairCursor.style.display = "none";
        calibrating = false;
        clickCount = 0;
        markerPositions = [];
        markersContainer.innerHTML = "";
        showPhase(calibrated ? "postCal" : "preCal");
    }

    async function doAutoCalibration() {
        try {
            const data = await api("/api/calibration/auto", { method: "POST" });
            if (data.ok) finishCalibration("Calibração automática concluída.", "success");
        } catch (err) {
            await cancelCalibration(true);
            showAlert(err.message || "Calibração automática falhou.", "error");
        }
    }

    btnSaveRef.addEventListener("click", async function () {
        setButtonBusy(btnSaveRef, true, "Salvando...");
        try {
            await api("/api/save_reference", { method: "POST" });
            showAlert("Rastreio iniciado. Mantenha o tabuleiro parado até a referência ser salva.", "info");
        } catch (err) {
            showAlert(err.message, "error");
        } finally {
            setButtonBusy(btnSaveRef, false, "Salvar referência");
        }
    });

    btnCalibrateAgain.addEventListener("click", async function () {
        try { await api("/api/calibration/reset_points", { method: "POST" }); } catch (_) {}
        calibrated = false;
        referenceSaved = false;
        tracking = false;
        showPhase("preCal");
        showAlert("Pronto para recalibrar.", "info");
    });

    btnToggleMask.addEventListener("click", function () {
        showMask = !showMask;
        maskWrapper.style.display = showMask ? "" : "none";
        btnToggleMask.textContent = showMask ? "Esconder máscara" : "Máscara";
        maskFeed.src = showMask ? `/video_feed/mask?t=${Date.now()}` : "";
    });

    btnStopTrack.addEventListener("click", async function () {
        try {
            await api("/api/tracking/stop", { method: "POST" });
        } catch (err) {
            showAlert(err.message, "error");
        }
    });

    btnVoice.addEventListener("click", async function () {
        try { await api("/api/voice/toggle", { method: "POST" }); } catch (err) { showAlert(err.message, "error"); }
    });

    btnVoiceConfig.addEventListener("click", function () {
        cbVoiceActive.checked = voiceActive;
        cbPhonetic.checked = phonetic;
        voiceSlider.value = voiceSpeed;
        voiceSpeedValue.textContent = Number(voiceSpeed).toFixed(1);
        voiceModal.style.display = "flex";
    });

    btnCloseVoice.addEventListener("click", function () {
        voiceModal.style.display = "none";
    });

    cbVoiceActive.addEventListener("change", function () {
        voiceActive = cbVoiceActive.checked;
        if (!voiceActive && "speechSynthesis" in window) window.speechSynthesis.cancel();
        sendVoiceConfig();
    });

    cbPhonetic.addEventListener("change", function () {
        phonetic = cbPhonetic.checked;
        sendVoiceConfig();
    });

    voiceSlider.addEventListener("input", function () {
        voiceSpeed = parseFloat(voiceSlider.value);
        voiceSpeedValue.textContent = voiceSpeed.toFixed(1);
        sendVoiceConfig();
    });

    async function sendVoiceConfig() {
        try {
            await api("/api/voice/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ativo: voiceActive, fonetica: phonetic, velocidade: voiceSpeed }),
            });
        } catch (err) {
            showAlert(err.message, "error");
        }
    }

    btnTestVoice.addEventListener("click", async function () {
        if (!voiceActive) {
            showAlert("Ative a voz primeiro.", "error");
            return;
        }
        speakText("Olá, este é um teste de voz.");
        try {
            await api("/api/voice/test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ frase: "Olá, este é um teste de voz." }),
            });
        } catch (_) {}
        showAlert("Teste de voz executado.", "success");
    });

    btnUndoMove.addEventListener("click", async function () {
        try { await api("/api/undo", { method: "POST" }); } catch (err) { showAlert(err.message, "error"); }
    });

    btnResetGame.addEventListener("click", async function () {
        try { await api("/api/reset", { method: "POST" }); } catch (err) { showAlert(err.message, "error"); }
    });

    function speakText(texto) {
        if (!("speechSynthesis" in window)) return;
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(texto);
        utterance.lang = "pt-BR";
        utterance.rate = Math.max(0.1, Math.min(10, voiceSpeed));
        utterance.volume = 1.0;
        window.speechSynthesis.speak(utterance);
    }

    function renderHistory() {
        if (!historico || historico.length === 0) {
            historyList.innerHTML = '<p class="history-empty">Nenhuma jogada ainda.</p>';
            return;
        }

        historyList.innerHTML = "";
        for (let i = 0; i < historico.length; i += 2) {
            const row = document.createElement("div");
            row.className = "history-row";
            row.innerHTML = `<span class="num">${Math.floor(i / 2) + 1}.</span><span>${historico[i].lance}</span><span>${historico[i + 1] ? historico[i + 1].lance : ""}</span>`;
            historyList.appendChild(row);
        }
        historyList.scrollTop = historyList.scrollHeight;
    }

    async function loadStatus() {
        try {
            const data = await api("/api/status");
            calibrated = Boolean(data.calibrated);
            referenceSaved = Boolean(data.reference_saved);
            tracking = Boolean(data.tracking);
            voiceActive = Boolean(data.voice_active);
            voiceSpeed = Number(data.voice_speed || 1.0);
            phonetic = Boolean(data.voice_fonetica);
            if (Array.isArray(data.historico)) {
                historico = data.historico;
                renderHistory();
            }
            syncVoiceControls();
            updateStatusCards();

            if (phaseFeed.style.display !== "none") {
                if (tracking) showPhase("tracking");
                else if (calibrated) showPhase("postCal");
                else showPhase("preCal");
            }
        } catch (_) {}
    }

    async function loadBoard() {
        try {
            const data = await api("/api/board");
            fenText.textContent = data.fen || "-";
            turnText.textContent = data.turn === "white" ? "Brancas" : "Pretas";
        } catch (_) {}
    }

    function syncVoiceControls() {
        btnVoice.textContent = voiceActive ? "Voz: ON" : "Voz: OFF";
        cbVoiceActive.checked = voiceActive;
        cbPhonetic.checked = phonetic;
        voiceSlider.value = voiceSpeed;
        voiceSpeedValue.textContent = voiceSpeed.toFixed(1);
    }

    function updateStatusCards() {
        statusCamera.textContent = selectedCamera;
        statusCalibrated.textContent = calibrated ? "OK" : "Pendente";
        statusTracking.textContent = tracking ? (trackingStatusLabel || (referenceSaved ? "Ativo" : "Preparando")) : "Parado";
        statusVoice.textContent = voiceActive ? "ON" : "OFF";
    }

    function showAlert(msg, type) {
        const el = document.createElement("div");
        el.className = `alert ${type || "info"}`;
        el.textContent = msg;
        alertsDiv.prepend(el);
        setTimeout(function () {
            el.style.opacity = "0";
            el.style.transition = "opacity 0.5s";
            setTimeout(function () { el.remove(); }, 500);
        }, 6500);
        while (alertsDiv.children.length > 5) alertsDiv.lastChild.remove();
    }

    function setButtonBusy(button, busy, text) {
        button.disabled = busy;
        button.textContent = text;
    }

    if (socket) {
        socket.on("connect", function () { showAlert("Interface conectada ao servidor.", "success"); });
        socket.on("disconnect", function () { showAlert("Conexão com o servidor perdida.", "error"); });
        socket.on("tracking_status", function (data) {
            if (data.status === "reference_saved") {
                referenceSaved = true;
                tracking = true;
                trackingStatusLabel = null;
                showAlert("Referência estável salva! Faça seu lance.", "success");
                showPhase("tracking");
            } else if (data.status === "waiting_stability") {
                referenceSaved = false;
                tracking = true;
                trackingStatusLabel = "Estabilizando";
            } else if (data.status === "movement_ignored") {
                tracking = true;
                showAlert("Movimento ignorado: parece vibração, sombra ou tabuleiro mexendo.", "info");
            } else if (data.status === "reference_needed") {
                referenceSaved = false;
                tracking = true;
                trackingStatusLabel = "Estabilizando";
                showAlert("Referência limpa. Mantenha o tabuleiro parado para salvar novamente.", "info");
            } else if (data.status === "started") {
                tracking = true;
                referenceSaved = false;
                trackingStatusLabel = "Estabilizando";
                showAlert("Rastreio iniciado. Mantenha o tabuleiro parado para salvar a referência.", "success");
                showPhase("tracking");
            } else if (data.status === "stopped") {
                tracking = false;
                trackingStatusLabel = null;
                showAlert("Rastreio parado.", "info");
                showPhase("postCal");
            }
            updateStatusCards();
        });

        socket.on("voice_toggled", function (data) {
            voiceActive = Boolean(data.ativo);
            syncVoiceControls();
            updateStatusCards();
            if (!voiceActive && "speechSynthesis" in window) window.speechSynthesis.cancel();
        });

        socket.on("voice_config_updated", function (data) {
            voiceActive = Boolean(data.ativo);
            voiceSpeed = Number(data.velocidade || 1.0);
            phonetic = Boolean(data.fonetica);
            syncVoiceControls();
            updateStatusCards();
        });

        socket.on("move_detected", function (data) {
            showAlert(`Lance: ${data.lance} — ${data.mensagem}`, "success");
            if (data.historico) {
                historico = data.historico;
                renderHistory();
            }
            if (data.voz && voiceActive) speakText(data.voz);
            loadBoard();
        });

        socket.on("move_alert", function (data) {
            showAlert(`Lance inválido: ${(data.casas || []).join(", ")}`, "error");
        });

        socket.on("move_undone", function (data) {
            showAlert(`Lance desfeito: ${data.lance}`, "info");
            if (historico.length > 0) historico.pop();
            renderHistory();
            loadBoard();
        });

        socket.on("game_reset", function () {
            showAlert("Partida reiniciada.", "info");
            historico = [];
            renderHistory();
            loadBoard();
        });

        socket.on("calibration_status", function (data) {
            if (data.status === "complete") finishCalibration("Calibração concluída!", "success");
            else if (data.status === "failed") {
                cancelCalibration(false);
                showAlert("Não foi possível detectar o tabuleiro.", "error");
            } else if (data.status === "cancelled") {
                cancelCalibration(false);
            }
        });
    } else {
        showAlert("Socket.IO não carregou. A página pode estar offline ou sem acesso ao servidor.", "error");
    }

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            calibrationModal.style.display = "none";
            voiceModal.style.display = "none";
        }
    });

    loadCameras();
    loadBoard();
    setInterval(function () {
        loadStatus();
        loadBoard();
    }, 3000);
})();

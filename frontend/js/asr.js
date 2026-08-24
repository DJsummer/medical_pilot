/**
 * ASR 控制器 — 服务端 Paraformer 录音 + 浏览器 Web Speech 实时听写
 */
(function (global) {
  const SpeechRecognition = global.SpeechRecognition || global.webkitSpeechRecognition;

  function createAsrController(options) {
    const {
      onUtterance,
      onInterim,
      onStatus,
      onError,
      serverAsrEnabled = false,
    } = options;

    let mode = serverAsrEnabled ? "server" : SpeechRecognition ? "browser" : "none";
    let mediaRecorder = null;
    let audioChunks = [];
    let mediaStream = null;
    let recognition = null;
    let browserListening = false;
    let recording = false;

    function setStatus(s) {
      if (onStatus) onStatus(s);
    }

    function setError(msg) {
      if (onError) onError(msg);
    }

    function emitUtterance(text) {
      const t = (text || "").trim();
      if (t && onUtterance) onUtterance(t);
    }

    async function startServerRecording() {
      if (recording) return;
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm";
        mediaRecorder = new MediaRecorder(mediaStream, { mimeType: mime });
        audioChunks = [];
        mediaRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) audioChunks.push(e.data);
        };
        mediaRecorder.onstop = async () => {
          const blob = new Blob(audioChunks, { type: mime.split(";")[0] });
          _releaseMedia();
          if (blob.size < 500) {
            setError("录音太短，请重新口述");
            setStatus("idle");
            recording = false;
            return;
          }
          setStatus("transcribing");
          if (onInterim) onInterim("");
          try {
            const fd = new FormData();
            fd.append("audio", blob, "recording.webm");
            const res = await fetch("/api/asr/transcribe", { method: "POST", body: fd });
            const raw = await res.text();
            let data;
            try {
              data = JSON.parse(raw);
            } catch {
              setError(`转写失败 HTTP ${res.status}: ${raw.slice(0, 80)}`);
              setStatus("idle");
              recording = false;
              return;
            }
            if (!data.ok) {
              setError(data.error || "转写失败");
            } else if (data.text) {
              emitUtterance(data.text);
            }
          } catch (e) {
            setError(String(e));
          }
          setStatus("idle");
          recording = false;
        };
        mediaRecorder.start(250);
        recording = true;
        if (onInterim) onInterim("");
        setStatus("recording");
      } catch (e) {
        setError("无法访问麦克风: " + e.message);
        _releaseMedia();
        recording = false;
        setStatus("idle");
      }
    }

    function stopServerRecording() {
      if (mediaRecorder && recording) {
        mediaRecorder.stop();
      }
    }

    function startBrowserListening() {
      if (!SpeechRecognition) {
        setError("当前浏览器不支持 Web Speech API，请使用 Chrome/Edge");
        return;
      }
      if (browserListening) return;

      recognition = new SpeechRecognition();
      recognition.lang = "zh-CN";
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onresult = (event) => {
        let interim = "";
        let finalText = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const res = event.results[i];
          if (res.isFinal) {
            finalText += res[0].transcript;
          } else {
            interim += res[0].transcript;
          }
        }
        if (onInterim) onInterim(interim.trim());
        if (finalText.trim()) {
          emitUtterance(finalText.trim());
          if (onInterim) onInterim("");
        }
      };

      recognition.onerror = (e) => {
        if (e.error !== "aborted" && e.error !== "no-speech") {
          setError("听写错误: " + e.error);
        }
      };

      recognition.onend = () => {
        if (browserListening) {
          try {
            recognition.start();
          } catch (_) {
            browserListening = false;
            setStatus("idle");
          }
        }
      };

      try {
        recognition.start();
        browserListening = true;
        setStatus("listening");
      } catch (e) {
        setError(String(e));
      }
    }

    function stopBrowserListening() {
      browserListening = false;
      if (recognition) {
        try {
          recognition.stop();
        } catch (_) {}
        recognition = null;
      }
      if (onInterim) onInterim("");
      setStatus("idle");
    }

    function _releaseMedia() {
      if (mediaStream) {
        mediaStream.getTracks().forEach((t) => t.stop());
        mediaStream = null;
      }
    }

    return {
      getMode: () => mode,
      setMode: (m) => {
        if (m === "server" && !serverAsrEnabled) return;
        if (m === "browser" && !SpeechRecognition) return;
        mode = m;
      },
      supportsBrowser: () => !!SpeechRecognition,
      supportsServer: () => serverAsrEnabled,
      isActive: () => recording || browserListening,
      toggle() {
        if (mode === "server") {
          if (recording) stopServerRecording();
          else startServerRecording();
        } else if (mode === "browser") {
          if (browserListening) stopBrowserListening();
          else startBrowserListening();
        } else {
          setError("请配置 ASR API Key 或使用 Chrome 浏览器");
        }
      },
      stop() {
        if (recording) stopServerRecording();
        if (browserListening) stopBrowserListening();
      },
      destroy() {
        this.stop();
        _releaseMedia();
      },
    };
  }

  global.MedicalASR = { createAsrController };
})(window);
